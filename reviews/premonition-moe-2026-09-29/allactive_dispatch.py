"""Optional all-active SleepMoE dispatch; no edits to the shared implementation.

Run correctness only (including a small MPS check when available):
  uv run --offline --with torch python -B allactive_dispatch.py
Later, with all experiment jobs idle, append serial end-to-end timings:
  uv run --offline --with torch python -B allactive_dispatch.py --benchmark

install_allactive(model) opts in in place, preserving parameters, state_dict
keys, optimizer identities, and module hooks. Only ResidualBank E==k banks
qualify. remove_allactive(model) restores the original implementation.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import re
import statistics
import subprocess
import sys
import time

# Imports of shared files must not create files outside this worker's ownership.
sys.dont_write_bytecode = True
import torch
from torch.nn import functional as F
from sleep_moe import ResidualBank

HERE = Path(__file__).resolve().parent
ARM = "moe_local_manual_plastic_all2_anchor_replay"
RESULT = HERE / "allactive-dispatch-test.json"
NOTES = HERE / "allactive-dispatch-notes.md"


class AllActiveBank(ResidualBank):
    """Full-batch experts, original expert-order sum, lazy exact route metadata.

    No topk, row gather, nonzero, scatter, or index_add in the qualified forward.
    Accessing last_indices computes the ORIGINAL topk (including tied-logit
    ordering) once per forward. CapsuleMoE activity accounting does access it.
    Changing k after installation falls back to the original sparse forward.
    Typed banks only qualify for E=k=2, where both pools have one expert.
    """

    @property
    def last_indices(self):
        if getattr(self, "_route_pending", False):
            logits = self.last_logits.detach()
            if self.typed:
                i0 = logits[:, ::2].max(-1).indices
                i1 = logits[:, 1::2].max(-1).indices
                self._route_indices = torch.stack((2 * i0, 2 * i1 + 1), -1)
            else:
                # Capture the last forward's all-active E, even if a caller
                # changes active before reading the metadata.
                self._route_indices = logits.topk(logits.shape[-1], -1).indices
            self._route_pending = False
        return getattr(self, "_route_indices", None)

    @last_indices.setter
    def last_indices(self, value):
        self._route_indices = value
        self._route_pending = False

    def forward(self, x, input_e, geometry):
        count = len(self.experts)
        if self.active != count or (self.typed and count != 2) or x.shape[0] == 0:
            return super().forward(x, input_e, geometry)
        context = self.router_norm(torch.cat((x.mean(1), input_e.mean(1)), -1))
        logits = self.router(context).float()
        gates = logits.sigmoid().to(x.dtype) / self.active
        out = torch.zeros_like(x)
        mass = x.new_zeros(*x.shape[:2], 2) if self.count_lane else None
        # The source accumulates in expert index order, regardless of topk rank.
        for i, expert in enumerate(self.experts):
            gate = gates[:, i, None, None]
            if expert.kind == "relational":
                delta = expert(x, geometry, input_e=input_e)
                if mass is not None:
                    mass = mass + expert.last_mass * gate
            else:
                delta = expert(x, geometry)
            out = out + delta * gate
        self.last_logits = logits
        self._route_indices = None
        self._route_pending = True
        if mass is not None:
            self.mass_features = mass
        # All E experts occur exactly once per row: same detached fraction as
        # one_hot(topk_ids).float().mean((0,1)); retain the original operations.
        fraction = logits.new_full((count,), 1.0 / count)
        balance = count * (fraction * logits.softmax(-1).mean(0)).sum()
        self.aux = .001 * balance + .0001 * logits.logsumexp(-1).square().mean()
        return out


def install_allactive(model):
    """Opt in atomically; accepts a bank, SleepMoE, or enclosing CapsuleMoE."""
    banks = [m for m in model.modules() if isinstance(m, ResidualBank)]
    if not banks:
        raise ValueError("no ResidualBank found")
    for bank in banks:
        if type(bank) not in (ResidualBank, AllActiveBank):
            raise ValueError("custom ResidualBank subclasses require a separate audit")
        if type(bank.active) is not int or bank.active != len(bank.experts):
            raise ValueError("all-active dispatch requires integer E == k")
        if bank.router.out_features != len(bank.experts) or bank.active < 1:
            raise ValueError("invalid expert/router count")
        if bank.typed and bank.active != 2:
            raise ValueError("typed routing qualifies only for E == k == 2")
        if any(getattr(e, "kind", None) not in ("mlp", "local", "local_manual", "relational")
               for e in bank.experts):
            raise ValueError("unknown expert interface")
    for bank in banks:
        if type(bank) is ResidualBank:
            indices = bank.last_indices
            bank.__class__ = AllActiveBank
            bank.__dict__.pop("last_indices", None)
            bank.last_indices = indices
    return model


def remove_allactive(model):
    for bank in model.modules():
        if type(bank) is AllActiveBank:
            indices = bank.last_indices
            bank.__class__ = ResidualBank
            bank.__dict__.pop("_route_indices", None)
            bank.__dict__.pop("_route_pending", None)
            bank.last_indices = indices
    return model


def _close(a, b, device, *, atol=None, rtol=None):
    atol = atol if atol is not None else (3e-6 if device == "cpu" else 3e-5)
    rtol = rtol if rtol is not None else (3e-5 if device == "cpu" else 3e-4)
    torch.testing.assert_close(a, b, atol=atol, rtol=rtol)
    assert bool(torch.isfinite(a).all()) and bool(torch.isfinite(b).all())
    return float((a.detach() - b.detach()).abs().max().cpu())


def _parameter_grads(a, b, device):
    errors = {}
    for (ka, pa), (kb, pb) in zip(a.named_parameters(), b.named_parameters(), strict=True):
        assert ka == kb
        assert (pa.grad is None) == (pb.grad is None), ka
        if pa.grad is not None:
            errors[ka] = _close(pa.grad, pb.grad, device)
    return errors


def _bank_case(device, count, batch, geometry, *, tied=False, local="manual"):
    torch.manual_seed(74069000 + count + batch)
    base = ResidualBank(32, count, count, 12, 3, local).to(device)
    # Zero-initialized DeltaExpert outputs would make task/router parity vacuous.
    with torch.no_grad():
        for expert in base.experts:
            expert.up.weight.normal_(0, .12)
            expert.up.bias.normal_(0, .04)
        if tied:
            base.router.weight.zero_()
            base.router.bias.fill_(.25)
    fast = install_allactive(copy.deepcopy(base))
    n = geometry[0] * geometry[1]
    # Noncontiguous tokens are the actual local operator layout.
    x = torch.randn(batch, 32, n, device=device).transpose(1, 2).detach().requires_grad_()
    e = torch.randn_like(x).requires_grad_()
    xx = x.detach().clone().requires_grad_()
    ee = e.detach().clone().requires_grad_()
    seen = []
    hooks = [expert.register_forward_pre_hook(lambda m, args: seen.append(len(args[0])))
             for expert in fast.experts]
    y, yy = base(x, e, geometry), fast(xx, ee, geometry)
    for hook in hooks:
        hook.remove()
    assert seen == [batch] * count
    errors = {"forward": _close(y, yy, device),
              "logits": _close(base.last_logits, fast.last_logits, device),
              "aux": _close(base.aux, fast.aux, device)}
    if base.count_lane:
        errors["mass_features"] = _close(base.mass_features, fast.mass_features, device)
    assert fast._route_pending  # No eager route sorting.
    assert torch.equal(base.last_indices, fast.last_indices)
    # Isolate auxiliary-loss derivatives from task gradients.
    ra = torch.autograd.grad(base.aux, (x, e, *base.router.parameters(),
                                       *base.router_norm.parameters()), retain_graph=True)
    rb = torch.autograd.grad(fast.aux, (xx, ee, *fast.router.parameters(),
                                       *fast.router_norm.parameters()), retain_graph=True)
    errors["aux_grad_max"] = max(_close(a, b, device) for a, b in zip(ra, rb))
    upstream = torch.randn_like(y) / y.numel() ** .5
    loss = (y * upstream).sum() + y.square().mean() + base.aux
    fast_loss = (yy * upstream).sum() + yy.square().mean() + fast.aux
    if base.count_lane:
        loss = loss + .03 * base.mass_features.square().mean()
        fast_loss = fast_loss + .03 * fast.mass_features.square().mean()
    loss.backward()
    fast_loss.backward()
    errors["input_grad"] = _close(x.grad, xx.grad, device)
    errors["embedding_grad"] = _close(e.grad, ee.grad, device)
    grads = _parameter_grads(base, fast, device)
    errors["parameter_grad_max"] = max(grads.values())
    assert float(base.router.weight.grad.abs().sum()) > 0
    assert all(float(expert.up.weight.grad.abs().sum()) > 0 for expert in base.experts)
    assert list(base.state_dict()) == list(fast.state_dict())
    # Backwards and forwards strict checkpoint compatibility, including removal.
    fast.load_state_dict(base.state_dict(), strict=True)
    base.load_state_dict(fast.state_dict(), strict=True)
    identities = [id(p) for p in fast.parameters()]
    remove_allactive(fast)
    assert type(fast) is ResidualBank and identities == [id(p) for p in fast.parameters()]
    return dict(device=device, E=count, k=count, batch=batch, geometry=list(geometry),
                tied=tied, local=local, max_abs_errors=errors,
                parameter_gradients_checked=len(grads), expert_batches=seen, status="pass")


def bank_tests(device):
    shapes = [(2, 1, (1, 1)), (2, 2, (3, 5)), (2, 5, (5, 3)),
              (1, 3, (2, 4)), (3, 2, (3, 4)), (4, 1, (4, 2)), (7, 2, (2, 3))]
    if device == "mps":
        shapes = [(2, 1, (2, 3)), (2, 3, (3, 2)), (3, 2, (2, 2))]
    rows = [_bank_case(device, count, batch, geometry) for count, batch, geometry in shapes]
    for count in (2, 3):
        rows.append(_bank_case(device, count, 2, (2, 3), tied=True))
    if device == "cpu":
        for local in ("operators", "symbols", "counts"):
            rows.append(_bank_case(device, 2, 2, (2, 3), local=local))
    return rows


def api_tests():
    bank = ResidualBank(16, 2, 2, 8, 2, "manual")
    keys, identities = list(bank.state_dict()), [id(p) for p in bank.parameters()]
    install_allactive(bank)
    assert bank.last_indices is None
    assert identities == [id(p) for p in bank.parameters()] and keys == list(bank.state_dict())
    install_allactive(bank)  # Idempotent.
    x, e = torch.randn(2, 6, 16), torch.randn(2, 6, 16)
    bank(x, e, (2, 3))
    expected_indices = bank.last_logits.detach().topk(2, -1).indices
    # Runtime k change preserves the source sparse semantics, not full execution.
    bank.active = 1
    assert torch.equal(bank.last_indices, expected_indices)
    # Clear nonleaf diagnostic graphs before deepcopy, as with source banks.
    bank.last_logits = bank.aux = None
    original = copy.deepcopy(bank)
    remove_allactive(original)
    _close(bank(x, e, (2, 3)), original(x, e, (2, 3)), "cpu")
    assert torch.equal(bank.last_indices, original.last_indices)
    rejected = []
    for count, active, local in ((3, 2, "manual"), (4, 4, "symbols")):
        bad = ResidualBank(16, count, active, 8, 2, local)
        try:
            install_allactive(bad)
        except ValueError:
            rejected.append([count, active, local])
        else:
            raise AssertionError("invalid all-active bank accepted")
        assert type(bad) is ResidualBank
    atomic = torch.nn.ModuleList([ResidualBank(16, 2, 2, 8, 2), ResidualBank(16, 3, 2, 8, 2)])
    try:
        install_allactive(atomic)
    except ValueError:
        assert all(type(m) is ResidualBank for m in atomic)
    else:
        raise AssertionError("mixed eligibility should fail atomically")
    bank.active = 2
    # A profiler is used only as an operation-presence audit; no time is reported.
    with torch.profiler.profile(activities=[torch.profiler.ProfilerActivity.CPU]) as trace:
        bank(x, e, (2, 3))
    operations = sorted({entry.key for entry in trace.key_averages()})
    forbidden = {"aten::topk", "aten::nonzero", "aten::index", "aten::index_select", "aten::index_add", "aten::index_add_"}
    assert not forbidden.intersection(operations)
    return dict(status="pass", state_dict_keys_unchanged=True, parameter_identities_unchanged=True,
                runtime_sparse_fallback=True, rejected=rejected,
                eligibility_validation_atomic=True, route_metadata_survives_k_change=True,
                forward_forbidden_operations_absent=sorted(forbidden),
                lazy_diagnostic_topk=True)


def load_inputs_and_models():
    import real_screen as S
    import capsule_screen as C
    from capsule_moe import CapsuleMoE

    checkpoint = HERE / "cycles-all2-s0.night3.pt"
    checkpoint_bytes = checkpoint.read_bytes()
    digest = hashlib.sha256(checkpoint_bytes).hexdigest()
    cycle = json.loads((HERE / "cycles-all2-s0.json").read_text())
    night3 = cycle["cycles"][-1]
    assert night3["cycle"] == 3 and cycle["arm"] == ARM
    assert digest == night3["after_sleep"]["checkpoint_sha256"]
    body, source_path = S.load(ARM, 0, "cpu")
    state = torch.load(io.BytesIO(checkpoint_bytes), map_location="cpu", weights_only=True)
    body.load_state_dict(state, strict=True)
    fast = install_allactive(copy.deepcopy(body))
    # Adapter state loads strictly into the ORIGINAL SleepMoE implementation.
    body.load_state_dict(fast.state_dict(), strict=True)
    for name in state:
        assert torch.equal(state[name], fast.state_dict()[name])
    assert all(b.active == len(b.experts) == 2 for b in body.banks)
    assert all(b.experts[1].kind == "local_manual" for b in body.banks)
    proof_path = HERE / "capsule_screen.json"
    proof = json.loads(proof_path.read_text())
    assert hashlib.sha256(proof_path.read_bytes()).hexdigest() == cycle["router_proof_sha256"]
    assert hashlib.sha256(source_path.read_bytes()).hexdigest() == cycle["original_source_sha256"]
    historic, supports, _, support_digest = S.make_development(0, 64, "maze")
    assert support_digest == proof["train_memory"]["support_layout_sha256"]
    # EXACT 64-item generator order, then slice; generating n=16 changes RNG.
    fresh64 = C.fresh_panel(supports, historic, 64)
    full_digests = {key: C.input_digest(rows) for key, rows in fresh64.items()}
    assert full_digests == cycle["input_sha256"]
    assert full_digests == proof["fresh_development"]["input_sha256"]
    panel = {key: rows[:16 if key.startswith("mazes") else 8] for key, rows in fresh64.items()}
    source, _ = S.load("loop_legacy", 0, "cpu")
    capsule = CapsuleMoE(source, copy.deepcopy(body))
    capsule.router.load_state_dict({key: torch.tensor(value) for key, value in proof["router_state_dict"].items()}, strict=True)
    fast_capsule = install_allactive(copy.deepcopy(capsule))
    provenance = dict(checkpoint=str(checkpoint), checkpoint_sha256=digest,
                      strict_loading="pass", adapter_to_original_strict_loading="pass",
                      width=body.tok.embedding_dim, banks=len(body.banks), E=2, k=2,
                      stored_body_parameters=sum(p.numel() for p in body.parameters()),
                      source_core_parameters=sum(p.numel() for p in source.parameters()),
                      acquired_active_core_parameters_per_row=sum(p.numel() for p in body.parameters()),
                      microexpert_parameters_per_bank=[[sum(p.numel() for p in expert.parameters())
                                                       for expert in bank.experts] for bank in body.banks],
                      support_sha256=support_digest, full_fresh64_input_sha256=full_digests,
                      sliced_input_sha256={key: C.input_digest(rows) for key, rows in panel.items()},
                      generator="capsule_screen.fresh_panel(supports, historic, 64), THEN [:16]/[:8]",
                      source_sha256=cycle["original_source_sha256"],
                      router_proof_sha256=cycle["router_proof_sha256"])
    return body, fast, capsule, fast_capsule, panel, provenance


def real_backward(base, fast, items):
    """Two recurrent steps at real width, random objective, no query answers."""
    base, fast = copy.deepcopy(base).train(), copy.deepcopy(fast).train()
    base.requires_grad_(True)
    fast.requires_grad_(True)
    t = torch.tensor([row.tokens for row in items[:2]])
    s = torch.tensor([row.slot for row in items[:2]])
    a, b = base.loop_train(t, s, 0, 2), fast.loop_train(t, s, 0, 2)
    errors = []
    torch.manual_seed(74079000)
    la, lb = base.auxiliary(), fast.auxiliary()
    aux_error = _close(la, lb, "cpu")
    for (lg, q), (llg, qq) in zip(a, b):
        errors.extend((_close(lg, llg, "cpu", atol=2e-5, rtol=3e-5), _close(q, qq, "cpu")))
        probe = torch.randn_like(lg) / lg.numel() ** .5
        la = la + (lg * probe).sum() + q.square().mean() * .01
        lb = lb + (llg * probe).sum() + qq.square().mean() * .01
    la.backward()
    lb.backward()
    gradients = _parameter_grads(base, fast, "cpu")
    assert all(float(bank.router.weight.grad.abs().sum()) > 0 for bank in base.banks)
    return dict(status="pass", batch=len(t), geometry=list(t.shape[1:]), recurrent_steps=2,
                read_max_abs_error=max(errors), aux_max_abs_error=aux_error,
                parameter_grad_max_abs_error=max(gradients.values()),
                parameter_gradients_checked=len(gradients), query_targets_used=False)


@torch.no_grad()
def active_parity(base, fast, panel, device="cpu", batch=4, *, executor=None):
    from active_eval import active_execute
    execute = executor or active_execute
    base.to(device).requires_grad_(False).eval()
    fast.to(device).requires_grad_(False).eval()
    results = {}
    for name, items in panel.items():
        rows, stopped, sizes = [], [], []
        routes, microcounts = [], []
        for start in range(0, len(items), batch):
            chunk = items[start:start + batch]
            t = torch.tensor([item.tokens for item in chunk], device=device)
            s = torch.tensor([item.slot for item in chunk], device=device)
            if hasattr(base, "reset_activity"):
                base.reset_activity()
                fast.reset_activity()
            a, b = execute(base, t, s), execute(fast, t, s)
            assert torch.equal(a.predictions, b.predictions), (name, start, "prediction")
            assert torch.equal(a.rounds, b.rounds), (name, start, "round")
            assert torch.equal(a.stopped, b.stopped), (name, start, "stop")
            assert a.active_sizes == b.active_sizes
            assert a.row_rounds == int(a.rounds.sum())
            rows.extend(a.rounds.cpu().tolist())
            stopped.extend(a.stopped.cpu().tolist())
            sizes.append(list(a.active_sizes))
            if hasattr(base, "activity"):
                assert base.activity == fast.activity
                routes.append(base.last_routes.cpu().tolist())
                microcounts.append(copy.deepcopy(base.activity))
        results[name] = dict(n=len(items), status="pass", prediction_mismatches=0,
                             round_mismatches=0, stop_mismatches=0, active_size_mismatches=0,
                             selected_rounds=rows, stopped=stopped, active_sizes=sizes,
                             actually_executed_row_rounds=sum(rows), cap_hits=rows.count(48),
                             mean_rounds=statistics.mean(rows))
        if microcounts:
            results[name]["activity_parity"] = True
            results[name]["initial_macro_routes_by_batch"] = routes
            results[name]["activity_by_batch"] = microcounts
    return results


def controller_parity(base, fast, panel, provenance):
    """Read-only composition audit of the parent's fixed all_learned controller."""
    import stop_controller as K
    record_path = HERE / "stop-controller-cycles-s0.json"
    record_bytes = record_path.read_bytes()
    record = json.loads(record_bytes)
    info = record["models"]["all2"]
    assert info["body_checkpoint_sha256"] == provenance["checkpoint_sha256"]
    assert record["input_sha256"] == provenance["full_fresh64_input_sha256"]
    code_bytes = (HERE / "stop_controller.py").read_bytes()
    current_code_digest = hashlib.sha256(code_bytes).hexdigest()
    checkpoint = HERE / Path(info["controller_checkpoint"]).name
    snapshot = checkpoint.read_bytes()
    digest = hashlib.sha256(snapshot).hexdigest()
    assert digest == info["controller_checkpoint_sha256"]
    controller = K.StopController().eval().requires_grad_(False)
    controller.load_state_dict(torch.load(io.BytesIO(snapshot), map_location="cpu", weights_only=True), strict=True)
    before = K.state_hash(controller)
    # Parent controller execute currently constructs CPU control tensors.
    execute = lambda net, t, s: K.execute(net, controller, t, s, policy="all_learned", cap=48)
    parity = active_parity(base, fast, panel, executor=execute)
    for name, row in parity.items():
        expected = info["scores"]["all_learned"][name]["per_puzzle_rounds"][:len(panel[name])]
        assert row["selected_rounds"] == expected, (name, "parent controller rounds")
    assert before == K.state_hash(controller)
    assert snapshot == checkpoint.read_bytes() and code_bytes == (HERE / "stop_controller.py").read_bytes()
    assert record_bytes == record_path.read_bytes()
    return dict(status="pass", policy="all_learned", device="cpu", fit_or_training_executed=False,
                controller_parameters=sum(p.numel() for p in controller.parameters()),
                controller_checkpoint_sha256=digest, parent_record_sha256=hashlib.sha256(record_bytes).hexdigest(),
                parent_code_sha256=current_code_digest, recorded_parent_code_sha256=record["code_sha256"],
                parent_code_matches_record=current_code_digest == record["code_sha256"],
                provenance_limit="Current parent executor checked against stored round slices; code hash equality with the original controller fit run is reported separately.",
                controller_state_unchanged=True, parent_files_unchanged=True,
                prediction_round_stop_active_size_and_activity_parity=parity)


BUSY_SCRIPTS = ("real_screen.py", "continual_cycles.py", "sleep_branch.py", "wake_sleep_meta.py",
                "claude_fewex_bench.py", "capsule_screen.py", "compare_capsule_baseline.py",
                "halt_calibrate.py", "stop_controller.py", "active_eval.py", "dispatch_benchmark.py", "fast_depthwise.py",
                "fast_adapters.py", "mac_pilot.py", "mac_qualified.py", "allactive_dispatch.py")


def timing_blockers(process_text=None):
    if process_text is None:
        process_text = subprocess.check_output(["ps", "-axo", "pid=,command="], text=True)
    busy = []
    for line in process_text.splitlines():
        fields = line.strip().split(maxsplit=1)
        if len(fields) != 2 or not fields[0].isdigit():
            continue
        pid, command = int(fields[0]), fields[1]
        if pid in (os.getpid(), os.getppid()):
            continue
        if re.search(r"(?:python[\d.]*\b|\buv\s+run\b)", command) and any(script in command for script in BUSY_SCRIPTS):
            busy.append(dict(pid=pid, command=command))
    return busy


def require_idle():
    busy = timing_blockers()
    if busy:
        raise RuntimeError("isolated CPU/MPS timing refused; competing jobs: " + json.dumps(busy))


def guard_test():
    from unittest.mock import patch
    fake = "\n".join(f"{900001+i} python /a/{name} --seed 1" for i, name in enumerate(BUSY_SCRIPTS))
    fake += "\n990001 uv run --offline --with torch python /a/continual_cycles.py\n990002 rg real_screen.py"
    assert len(timing_blockers(fake)) == len(BUSY_SCRIPTS) + 1
    with patch.object(subprocess, "check_output", return_value=fake):
        try:
            require_idle()
        except RuntimeError as error:
            assert "isolated CPU/MPS timing refused" in str(error)
        else:
            raise AssertionError("guard allowed known experiment jobs")
    return dict(status="pass", recognized_scripts=list(BUSY_SCRIPTS),
                simulated_busy_refusal=True,
                live_blockers_observed=timing_blockers(), timing_executed=False)


def _sync(device):
    if device == "mps":
        torch.mps.synchronize()


@torch.no_grad()
def benchmark_pair(base, fast, panel, device, *, batch=4, warmup=1, repeats=3, executor=None):
    """Callable guarded end-to-end active executor bench; no isolated kernel claim.

    Serial variants, alternating order, synchronization around each sample.
    Includes embed/step/read/stop/compaction and capsule activity accounting;
    excludes load/copy, tensorization, query scoring, and parity verification.
    """
    from active_eval import active_execute
    execute = executor or active_execute
    if device not in ("cpu", "mps") or batch < 1 or warmup < 1 or repeats < 3:
        raise ValueError("device cpu/mps; batch>=1, warmup>=1, repeats>=3 required")
    if torch.get_num_threads() != 2 or torch.get_num_interop_threads() != 1:
        raise ValueError("benchmark requires 2 intraop/1 interop threads")
    require_idle()
    active_parity(base, fast, panel, device, batch, executor=execute)
    batches = [(torch.tensor([it.tokens for it in items[start:start + batch]], device=device),
                torch.tensor([it.slot for it in items[start:start + batch]], device=device))
               for items in panel.values() for start in range(0, len(items), batch)]
    models = {"original": base, "allactive": fast}

    def lane(name):
        for t, s in batches:
            model = models[name]
            if hasattr(model, "reset_activity"):
                model.reset_activity()
            execute(model, t, s)

    for _ in range(warmup):
        for name in models:
            require_idle()
            lane(name)
            _sync(device)
    samples = {key: [] for key in models}
    for repeat in range(repeats):
        for name in (("original", "allactive") if repeat % 2 == 0 else ("allactive", "original")):
            require_idle()
            _sync(device)
            start = time.perf_counter()
            lane(name)
            _sync(device)
            samples[name].append(time.perf_counter() - start)
            require_idle()
    medians = {key: statistics.median(values) for key, values in samples.items()}
    return dict(device=device, batch=batch, warmup=warmup, repeats=repeats,
                seconds=samples, median_seconds=medians,
                original_over_allactive=medians["original"] / medians["allactive"],
                scope=f"{sum(map(len, panel.values()))}-puzzle development subset, complete active inference",
                broad_2x_claim=False)


def _write_notes(result):
    banks = result["cpu_bank_parity"]
    grad_max = max(row["max_abs_errors"]["parameter_grad_max"] for row in banks)
    lines = ["# Optional all-active dispatch", "",
             "Only allactive_dispatch.py, allactive-dispatch-test.json and this note are owned by this worker. Shared code and checkpoints were read only. No optimizer steps, query training, calibration, or official holdout access occurred.", "",
             "install_allactive(net) converts only ordinary ResidualBank instances with integer E == k. It preserves module/parameter identities, hooks, state_dict keys, and requires_grad flags. remove_allactive(net) reverses it. Subsequent k changes use the original sparse forward. Untyped E==k is supported generally; typed banks qualify only at E=k=2. Real checkpoint testing covers two MLP/manual-local experts per block.", "",
             "Each expert sees the full batch. Gates are the original logits.float().sigmoid().to(x.dtype)/k; additions retain the original expert index order. The detached selected fraction is exactly uniform 1/E, with the original softmax balance and logsumexp-squared z-loss operations retained. Neither auxiliary loss nor router task gradients are removed. Nonzero randomized expert outputs prevent a zero-initialization parity test from passing vacuously.", "",
             "Exact original last_indices order (including ties) is produced lazily using the original backend topk, or typed pool max. Direct bank forward avoids topk/nonzero/row gathers/index_add. Consumers that read last_indices incur the diagnostic sorting cost. CapsuleMoE reads it EVERY step for activity accounting, so capsule execution still pays that cost plus macro dispatch, histograms, host synchronization, reads and active compaction. The adapter does not change capsule accounting.", "",
             "E=k=2 still runs both experts per selected acquired-body row, every block and recurrent round. Stored/trainable/active parameter counts do not decrease. Direct summation avoids dispatch copies and scatter overhead; it still retains expert activations for autograd and creates weighted deltas/sum tensors. It is equivalent within tested floating point tolerances, not a bitwise or arbitrary-custom-expert guarantee.", "",
             f"Stored acquired body / active core per acquired row: {result['provenance']['stored_body_parameters']:,} parameters. Source core per source row: {result['provenance']['source_core_parameters']:,}. Both microexperts are active in all {result['provenance']['banks']} acquired blocks; per-bank expert parameter sizes are {result['provenance']['microexpert_parameters_per_bank']}. Capsule macro router/controller and routing/control work are additional overhead.", "",
             f"CPU bank forward/backward, separate auxiliary gradients, input/embedding gradients, router/expert/norm gradients and route order passed {len(banks)} cases. B=1/2/3/5; rectangular geometries and 1x1; E=k=1/2/3/4/7; tied logits for E=2/3. Additional E2 operators/symbols/counts cases cover relational input dispatch, typed ordering and mass-feature forward/backward parity. CPU tolerances: atol=3e-6, rtol=3e-5. Largest bank parameter-gradient absolute error: {grad_max:.9g}.", "",
             f"Small MPS bank checks: {result['mps_bank_parity']['status']}; tolerances atol=3e-5, rtol=3e-4. MPS covers small E=k=2/3 shapes and ties only; full authentic trajectories run on CPU.", "",
             "The authentic cycles-all2-s0.night3.pt checkpoint loaded strictly, matched the cycle record SHA256, and strictly round-tripped the adapter state into original SleepMoE. Two recurrent backward steps at width 256 were checked on actual development input geometries, using random read objectives without query targets. Real read tolerances allow atol=2e-5; gradients retain the CPU bank tolerances.", "",
             "The exact capsule generator was run with n=64 and original 64 training supports/historical exclusion panel, then sliced to 16 mazes9 + 16 mazes11 + 8 sums4 + 8 grids5 (48 total). Full 64-panel hashes match BOTH capsule_screen.json and cycles-all2-s0.json. Bare-body and frozen, reconstructed CapsuleMoE active_execute comparisons at cap 48/batch 4 have exact prediction, selected-round, stop-flag and active-size parity. Capsule macro routing and full activity dictionaries also match. No targets enter executor inputs or these comparisons.", ""]
    for model in ("bare", "capsule"):
        for name, row in result["active_parity"][model].items():
            lines.append(f"- {model}/{name}: n={row['n']}, row-rounds={row['actually_executed_row_rounds']}, mean={row['mean_rounds']:.3f}, cap hits={row['cap_hits']}; all parity mismatches 0.")
    lines.extend(["", f"Checkpoint SHA256: `{result['provenance']['checkpoint_sha256']}`.", "",
                  "No isolated speed benchmark was run. The process guard was tested with synthetic real_screen/continual_cycles and other known jobs, and observed live jobs are recorded in JSON. No kernel-derived 2x or end-to-end speed claim is made.", "",
                  "From this directory, correctness: `uv run --offline --with torch python -B allactive_dispatch.py`. Later, when parent jobs are idle: `uv run --offline --with torch python -B allactive_dispatch.py --benchmark`. The latter appends timings to the owned JSON only. Callable benchmark_pair supports serial CPU or MPS pairs; CLI runs CPU (48 puzzles) then MPS (2 per family, 8 puzzles), one device/model pair at a time. It checks idleness before load, warmups and each sample, tests exact parity before timing, uses CPU 2 intraop/1 interop threads, MPS synchronization, alternating lane order, 1 warmup/3 repeats, and complete active inference. Checkpoint loading, tensorization, parity and scoring are excluded. The guard recognizes known experiment commands, not all possible system contention, and cannot eliminate process-start races."])
    if "controller_composition_parity" in result:
        lines.extend(["", "Parent controller handoff: install_allactive(body) before CapsuleMoE(source, body), or install_allactive(capsule) after reconstruction. Then call stop_controller.execute(capsule, frozen_controller, tokens, slots, policy='all_learned'). The adapter preserves all bank state_dict keys and parameter identities. The parent controller remains unchanged and no controller fitting was invoked.", "",
                      "Read-only CPU composition testing passed on the same 48 sliced puzzles with the authentic 16,705-parameter all2 controller: exact predictions, rounds, stops, active sizes and capsule activity match original-bank execution; rounds also match the parent's stored all_learned record slices. Controller state, checkpoint bytes, parent script and JSON remained unchanged. The current parent execute creates CPU control tensors; controller/MPS composition needs its own device audit.", "",
                      "benchmark_pair(..., executor=lambda net,t,s: stop_controller.execute(net, frozen_controller,t,s, policy='all_learned')) is available for a later serial CPU pair. The CLI default still benchmarks original active_eval stopping. Quality comparisons against original dense and learned-controller dense belong to the parent's end-to-end composition; no timing or 2x inference is taken from round reduction here."])
        if not result["controller_composition_parity"]["parent_code_matches_record"]:
            lines.extend(["", "Controller provenance limitation: the current parent script SHA256 differs from the hash in its result record. Both hashes are reported in JSON. The loaded controller checkpoint matches the recorded hash and the current executor reproduces the requested stored round slices; this cannot establish byte-identical code provenance for the earlier controller fit run."])
    if "benchmark" in result:
        lines.extend(["", "A later explicitly requested guarded benchmark has been appended to JSON; its samples are development-subset timings only and do not establish a broad 2x claim."])
    NOTES.write_text("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", action="store_true", help="later only: require idle jobs, append end-to-end CPU then small-panel MPS timings")
    args = parser.parse_args()
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    if args.benchmark:
        require_idle()  # Fail before model loading, verification or timing.
        if not RESULT.exists():
            raise RuntimeError("run correctness first")
        result = json.loads(RESULT.read_text())
        if result["code_sha256"] != hashlib.sha256(Path(__file__).read_bytes()).hexdigest():
            raise RuntimeError("code changed; rerun correctness first")
        body, fast, capsule, fast_capsule, panel, provenance = load_inputs_and_models()
        if provenance != result["provenance"]:
            raise RuntimeError("provenance changed; rerun correctness first")
        timing = {}
        devices = ["cpu"] + (["mps"] if torch.backends.mps.is_available() else [])
        for device in devices:
            timing[device] = {}
            for name, a, b in (("bare", body, fast), ("capsule", capsule, fast_capsule)):
                device_panel = panel if device == "cpu" else {key: items[:2] for key, items in panel.items()}
                timing[device][name] = benchmark_pair(a, b, device_panel, device)
                a.cpu()
                b.cpu()
                if device == "mps":
                    torch.mps.empty_cache()
        result["benchmark"] = timing
        result["isolated_speed_benchmark_executed"] = True
    else:
        result = dict(status="pass", development_only=True, official_holdout_opened=False,
                      query_training_updates=0, optimizer_steps=0, query_targets_used=False,
                      torch_version=torch.__version__, cpu_threads=2, cpu_interop_threads=1,
                      code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                      isolated_speed_benchmark_executed=False, speed_claim=False,
                      broad_2x_claim=False)
        result["guard"] = guard_test()
        result["cpu_bank_parity"] = bank_tests("cpu")
        result["api"] = api_tests()
        print("CPU banks/API/guard passed", flush=True)
        if torch.backends.mps.is_available():
            result["mps_bank_parity"] = dict(status="pass", cases=bank_tests("mps"))
        else:
            result["mps_bank_parity"] = dict(status="unavailable", cases=[])
        print("Small MPS checks finished", flush=True)
        body, fast, capsule, fast_capsule, panel, result["provenance"] = load_inputs_and_models()
        result["real_width_backward"] = [real_backward(body, fast, panel[key]) for key in ("grids5", "mazes9")]
        print("Authentic checkpoint / real-width recurrent backward passed", flush=True)
        result["active_parity"] = {"bare": active_parity(body, fast, panel),
                                   "capsule": active_parity(capsule, fast_capsule, panel)}
        if (HERE / "stop-controller-cycles-s0.json").exists():
            result["controller_composition_parity"] = controller_parity(capsule, fast_capsule, panel, result["provenance"])
        # No checkpoint or shared-file writes. Inference weights stayed frozen.
        result["active_parameters_frozen"] = all(not p.requires_grad and p.grad is None
                                                for m in (body, fast, capsule, fast_capsule) for p in m.parameters())
        assert result["active_parameters_frozen"]
    RESULT.write_text(json.dumps(result, indent=2) + "\n")
    _write_notes(result)
    print(json.dumps({"status": "pass", "result": str(RESULT), "notes": str(NOTES),
                      "isolated_speed_benchmark_executed": result["isolated_speed_benchmark_executed"]}), flush=True)


if __name__ == "__main__":
    main()
