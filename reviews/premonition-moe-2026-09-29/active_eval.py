"""Bounded, label-free active stopping; DEVELOPMENT-only sidecar.

No training, calibration, official panels, or parent-file changes. Correctness
uses small batches by default. Timing is an explicit, isolated CPU mode.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import statistics
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

import torch

import real_screen as S

MAX_ROUNDS = 48
VOCAB = 125


@dataclass
class ActiveResult:
    predictions: torch.Tensor       # [B, cells], in original input order
    rounds: torch.Tensor            # [B], one-based
    stopped: torch.Tensor           # learned rule fired (including at cap)
    active_sizes: tuple[int, ...]   # actual batch sent to step/read each round

    @property
    def row_rounds(self):
        return sum(self.active_sizes)


def _validate(net, tokens, slots, cap):
    if not isinstance(cap, int) or isinstance(cap, bool) or not 1 <= cap <= MAX_ROUNDS:
        raise ValueError("cap must be an integer in [1, 48]")
    if tokens.ndim != 3 or tokens.shape != slots.shape or tokens.numel() == 0:
        raise ValueError("tokens and slots must be matching nonempty [B,H,W] grids")
    if tokens.device != slots.device:
        raise ValueError("tokens and slots must share a device")
    if getattr(net, "arm", "loop") != "loop":
        raise ValueError("active stopping requires a recurrent loop model")
    if getattr(net, "output_token_ids", None) is not None:
        raise ValueError("restricted-alphabet decoding changes original stopping semantics")


def _read(net, h):
    logits, q = net.read(h)
    if logits.shape != (*h.shape[:2], VOCAB) or q is None or q.shape != h.shape[:1]:
        raise ValueError("read must return [B,cells,125] logits and [B] halt logits")
    # Preserve the original float32 sigmoid, strict threshold and full argmax.
    return logits.argmax(-1), q.float().sigmoid()


@torch.no_grad()
def active_execute(net, tokens, slots, cap=MAX_ROUNDS):
    """Actually remove completed rows; never accepts targets or a slot mask.

    Models must have row-independent inference and shared dr/dc geometry (as
    the dense loop and SleepMoE do). Batch-dependent routing/normalization would
    require a separate equivalence audit. Model diagnostic aux buffers may be
    overwritten; model parameters and recurrent geometry are not changed.
    """
    _validate(net, tokens, slots, cap)
    net.eval()
    e, (dr, dc) = net.embed(tokens, slots)
    h = torch.zeros_like(e)
    b, cells = e.shape[:2]
    live = torch.arange(b, device=tokens.device)
    predictions = torch.empty((b, cells), dtype=torch.long, device=tokens.device)
    rounds = torch.empty(b, dtype=torch.long, device=tokens.device)
    stopped = torch.zeros(b, dtype=torch.bool, device=tokens.device)
    previous = None
    stable_run = torch.zeros(b, dtype=torch.long, device=tokens.device)
    sizes = []
    for r in range(1, cap + 1):
        sizes.append(len(live))
        h = net.step(h, e, dr, dc)
        pred, q = _read(net, h)
        if previous is None:
            stable_run.fill_(1)
        else:
            same = (pred == previous).all(-1)  # ALL cells, not just fill slots
            stable_run = torch.where(same, stable_run + 1, 1)
        fire = (stable_run >= 3) & (q > .5) if r >= 3 else torch.zeros_like(stopped[live])
        done = torch.ones_like(fire) if r == cap else fire
        if bool(done.any()):
            ids = live[done]
            predictions[ids] = pred[done]
            rounds[ids] = r
            stopped[ids] = fire[done]
            keep = (~done).nonzero(as_tuple=True)[0]
            if keep.numel() == 0:
                break
            # Keep the EXACT state and embedding for the surviving identities,
            # including any appended persistent route/control channels.
            # Offsets/geometry depend only on H,W and have no batch dimension.
            live = live[keep]
            h, e = h[keep], e[keep]
            stable_run, previous = stable_run[keep], pred[keep]
        else:
            previous = pred
    return ActiveResult(predictions, rounds, stopped, tuple(sizes))


def offline_select(ps, qs):
    """Original offline rule, applied after every capped round has executed."""
    if ps.ndim != 3 or qs.shape != ps.shape[:2] or not 1 <= ps.shape[1] <= MAX_ROUNDS:
        raise ValueError("expected [B,cap,cells] predictions and [B,cap] probabilities")
    b, cap = ps.shape[:2]
    rounds = torch.full((b,), cap, dtype=torch.long, device=ps.device)
    stopped = torch.zeros(b, dtype=torch.bool, device=ps.device)
    if cap >= 3:
        stable = (ps[:, 2:] == ps[:, 1:-1]).all(-1) & (ps[:, 1:-1] == ps[:, :-2]).all(-1)
        fire = stable & (qs[:, 2:] > .5)
        stopped = fire.any(1)
        rounds = torch.where(stopped, fire.long().argmax(1) + 3, rounds)
    picked = ps[torch.arange(b, device=ps.device), rounds - 1]
    return picked, rounds, stopped


@torch.no_grad()
def offline_execute(net, tokens, slots, cap=MAX_ROUNDS):
    _validate(net, tokens, slots, cap)
    net.eval()
    return offline_select(*net.loop_rounds(tokens, slots, cap))


@torch.no_grad()
def original_fixed48(net, tokens, slots):
    """Original loop_rounds: step/read/argmax/sigmoid on all rows for all 48.

    Keep this control authentic, including trajectory allocation; a last-read
    optimized fixed executor would be a distinct control.
    """
    _validate(net, tokens, slots, MAX_ROUNDS)
    net.eval()
    return net.loop_rounds(tokens, slots, MAX_ROUNDS)[0][:, -1]


def _score(name, items, pred):
    # Query targets/checkers are used only AFTER both executors have returned.
    t, slots, targets = S.N.tensors(items)
    pred = pred.cpu()
    mask = slots.flatten(1).bool()
    targets = targets.flatten(1)
    if name == "sums4":
        exact = sum(int(S.E.check(it, row)) for it, row in zip(items, pred.reshape_as(t).tolist()))
    else:
        exact = int(((pred == targets) | ~mask).all(1).sum())
    return exact, int(((pred == targets) & mask).sum()), int(mask.sum())


@torch.no_grad()
def compare_development(net, panels, *, batch=4, cap=MAX_ROUNDS):
    """Require exact prediction AND selected-round parity on identical weights."""
    if batch < 1:
        raise ValueError("batch must be positive")
    net.eval()
    result = {}
    for name, items in panels.items():
        if not items:
            raise ValueError("development panels must be nonempty")
        record = dict(n=len(items), prediction_mismatches=0, round_mismatches=0,
                      stop_mismatches=0, learned=0, fixed48=0, cap_hits=0,
                      row_rounds=0, offline_row_rounds=cap * len(items),
                      selected_rounds=[], active_sizes=[])
        cell_hits = cell_n = 0
        for begin in range(0, len(items), batch):
            chunk = items[begin:begin + batch]
            # Inference tensors are constructed without reading query targets.
            t = torch.tensor([it.tokens for it in chunk])
            slots = torch.tensor([it.slot for it in chunk])
            ps, qs = net.loop_rounds(t, slots, cap)
            picked, rr, fired = offline_select(ps, qs)
            active = active_execute(net, t, slots, cap)
            pm = int((active.predictions != picked).any(1).sum())
            rm = int((active.rounds != rr).sum())
            sm = int((active.stopped != fired).sum())
            record["prediction_mismatches"] += pm
            record["round_mismatches"] += rm
            record["stop_mismatches"] += sm
            if pm or rm or sm:
                raise AssertionError(f"{name}[{begin}]: active/offline mismatches predictions={pm}, rounds={rm}, stops={sm}")
            assert active.row_rounds == int(active.rounds.sum())
            assert all(a >= b for a, b in zip(active.active_sizes, active.active_sizes[1:]))
            record["row_rounds"] += active.row_rounds
            record["selected_rounds"].extend(active.rounds.tolist())
            record["active_sizes"].append(list(active.active_sizes))
            record["cap_hits"] += int((active.rounds == cap).sum())
            right, ch, cn = _score(name, chunk, active.predictions)
            record["learned"] += right
            cell_hits += ch
            cell_n += cn
            fixed = ps[:, -1] if cap == MAX_ROUNDS else original_fixed48(net, t, slots)
            record["fixed48"] += _score(name, chunk, fixed)[0]
        record["mean_rounds"] = record["row_rounds"] / len(items)
        record["cell_accuracy"] = cell_hits / cell_n if cell_n else None
        record["round_work_ratio"] = record["offline_row_rounds"] / record["row_rounds"]
        record["wall_clock_speed_claim"] = False
        result[name] = record
    if cap == MAX_ROUNDS:
        # Independent check against the existing parent's offline evaluator,
        # including its checker, cap-hit convention and cell scoring.
        parent = S.evaluate(net, panels, "cpu", batch=batch, cap=cap)
        for name, record in result.items():
            for key in ("n", "learned", "fixed48", "cap_hits", "mean_rounds", "cell_accuracy"):
                assert record[key] == parent[name][key], (name, key, record[key], parent[name][key])
            record["parent_offline_verified"] = True
    return result


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_frozen(arm, seed, checkpoint):
    # Capture bytes once so the reported digest identifies the exact loaded
    # snapshot even if the parent later replaces a checkpoint at this path.
    checkpoint = Path(checkpoint).resolve()
    data = checkpoint.read_bytes()
    state = torch.load(io.BytesIO(data), map_location="cpu", weights_only=True)
    net, _ = S.load(arm, seed, "cpu")
    net.load_state_dict(state.get("state", state), strict=True)
    net.requires_grad_(False).eval()
    if net.tok.embedding_dim != 256 or net.head.out_features != VOCAB:
        raise ValueError("this sidecar requires real width 256 and all 125 output tokens")
    return net, dict(arm=arm, checkpoint=str(checkpoint),
                     checkpoint_sha256=hashlib.sha256(data).hexdigest(),
                     width=256, vocab=VOCAB, stored=net.weight_count(),
                     trainable=sum(p.numel() for p in net.parameters() if p.requires_grad))


def require_idle_cpu():
    """Timing must not run beside the parent's known experiment/training jobs."""
    output = subprocess.check_output(["ps", "-axo", "pid=,command="], text=True)
    busy = []
    for line in output.splitlines():
        fields = line.strip().split(maxsplit=1)
        if len(fields) != 2 or int(fields[0]) == os.getpid():
            continue
        command = fields[1]
        experiment = any(x in command for x in ("real_screen.py", "sleep_branch.py", "claude_fewex_bench.py"))
        competing_eval = "active_eval.py" in command
        if (experiment or competing_eval) and any(x in command for x in ("python", "uv run")):
            # Exclude this process's uv launcher. Other evaluator modes also
            # consume CPU and therefore invalidate isolated timing.
            if int(fields[0]) != os.getppid():
                busy.append(fields[0])
    if busy:
        raise RuntimeError("isolated timing refused: experiment/timing processes active: " + ", ".join(busy))


@torch.no_grad()
def time_development(net, panels, *, batch=4, warmup=2, repeats=5):
    """Serial CPU/2-thread medians; loading, tensorization, scoring excluded.

    Includes embedding, all executed steps/reads and active compaction. Rotate
    lane order between repeats; report samples, not round-based speed guesses.
    """
    if batch < 1 or warmup < 1 or repeats < 3:
        raise ValueError("timing needs batch>=1, warmup>=1 and repeats>=3")
    if torch.get_num_threads() != 2 or torch.get_num_interop_threads() != 1:
        raise ValueError("timing requires CPU 2 intraop / 1 interop threads")
    if any(p.device.type != "cpu" for p in net.parameters()):
        raise ValueError("timing supports CPU only")
    require_idle_cpu()
    net.eval()
    lanes = ("active", "original48fixed", "offline_learned48")
    result = {}
    for name, items in panels.items():
        if not items:
            raise ValueError("development panels must be nonempty")
        batches = [(torch.tensor([it.tokens for it in items[i:i + batch]]),
                    torch.tensor([it.slot for it in items[i:i + batch]]))
                   for i in range(0, len(items), batch)]

        def run_lane(lane):
            for t, slots in batches:
                if lane == "active":
                    active_execute(net, t, slots)
                elif lane == "original48fixed":
                    original_fixed48(net, t, slots)
                else:
                    offline_execute(net, t, slots)

        for _ in range(warmup):
            for lane in lanes:
                run_lane(lane)
        samples = {lane: [] for lane in lanes}
        for repeat in range(repeats):
            require_idle_cpu()
            for offset in range(len(lanes)):
                lane = lanes[(repeat + offset) % len(lanes)]
                started = time.perf_counter()
                run_lane(lane)
                samples[lane].append(time.perf_counter() - started)
            require_idle_cpu()
        medians = {lane: statistics.median(values) for lane, values in samples.items()}
        result[name] = dict(n=len(items), batch=batch, warmup=warmup, repeats=repeats,
                            seconds=samples, median_seconds=medians,
                            fixed48_over_active=medians["original48fixed"] / medians["active"],
                            offline48_over_active=medians["offline_learned48"] / medians["active"])
    return result


def selftest():
    """Tiny scripted trajectories exercise compaction without a training job."""
    class Scripted(torch.nn.Module):
        arm = "loop"

        def __init__(self):
            super().__init__()
            self.sizes = []
            self.fire_at_cap = False
            self.change_after_stop = False

        def embed(self, t, slots):
            # Identity in e, accumulated round in h; preserving BOTH is needed.
            e = torch.zeros((len(t), 2, 2))
            e[:, :, 0] = t[:, 0, 0, None]
            return e, (None, None)

        def step(self, h, e, dr, dc):
            self.sizes.append(len(h))
            if bool((h[:, :, 0] != e[:, :, 0]).any()) and bool((h[:, :, 1] != 0).any()):
                raise AssertionError("state/embedding identity lost")
            out = h.clone()
            out[:, :, 0] = e[:, :, 0]
            out[:, :, 1] += 1
            return out

        def read(self, h):
            ids, r = h[:, 0, 0].long(), h[:, 0, 1].long()
            pred = torch.full((len(h), 2), 124, dtype=torch.long)
            # Row 1 stabilizes from round 4 (earliest stop 6). Its fill-slot
            # prediction is constant: non-slot changes MUST delay stopping.
            pred[:, 1] = torch.where((ids == 1) & (r < 4), r % 2, 124)
            if self.change_after_stop:
                pred[(ids == 0) & (r > 3)] = 123
            # Row 2 stays stable with q==.5 through round 7; row 3 never fires.
            q = torch.where((ids == 3) | ((ids == 2) & (r < 8)), 0., 20.)
            q[(ids == 0) & (r < 3)] = -20.  # only CURRENT q is required
            q[(ids == 2) & (r == 6)] = 1e-9  # fp32 sigmoid rounds to .5
            q[(ids == 2) & (r == 7)] = float("nan")
            if self.fire_at_cap:
                q[(ids == 3) & (r == 48)] = 20.
            lg = torch.full((len(h), 2, VOCAB), -10.)
            lg.scatter_(-1, pred.unsqueeze(-1), 10.)
            return lg, q

        def loop_rounds(self, t, slots, n):
            e, (dr, dc) = self.embed(t, slots)
            h = torch.zeros_like(e)
            ps, qs = [], []
            for _ in range(n):
                h = self.step(h, e, dr, dc)
                pred, q = _read(self, h)
                ps.append(pred)
                qs.append(q)
            return torch.stack(ps, 1), torch.stack(qs, 1)

    t = torch.arange(4).reshape(4, 1, 1).expand(4, 1, 2).clone()
    slots = torch.tensor([[[1, 0]]] * 4)
    net = Scripted()
    for cap in (1, 2, 3, 8, 48):
        expected = offline_execute(net, t, slots, cap)
        net.sizes.clear()
        actual = active_execute(net, t, slots, cap)
        assert torch.equal(actual.predictions, expected[0])
        assert torch.equal(actual.rounds, expected[1])
        assert torch.equal(actual.stopped, expected[2])
        assert actual.row_rounds == int(actual.rounds.sum())
        assert tuple(net.sizes) == actual.active_sizes
        if cap == 48:
            assert actual.rounds.tolist() == [3, 6, 8, 48]
            assert actual.stopped.tolist() == [True, True, True, False]
            assert actual.active_sizes == (4,) * 3 + (3,) * 3 + (2,) * 2 + (1,) * 40
            assert actual.row_rounds == 65
    # All stop at round 3: no call at round 4. Also verify B=1 and input order.
    a = active_execute(net, t[:1].expand(4, 1, 2), slots)
    assert a.active_sizes == (4, 4, 4)
    for row in range(4):
        a = active_execute(net, t[row:row + 1], slots[row:row + 1])
        assert a.rounds.item() == (3, 6, 8, 48)[row]
    permutation = torch.tensor([3, 0, 2, 1])
    a = active_execute(net, t[permutation], slots[permutation])
    assert a.rounds.tolist() == [48, 3, 8, 6]
    net.fire_at_cap = True
    a = active_execute(net, t, slots)
    assert a.rounds[-1].item() == 48 and bool(a.stopped[-1])
    assert torch.equal(a.stopped, offline_execute(net, t, slots)[2])
    net.fire_at_cap = False
    net.change_after_stop = True
    a = active_execute(net, t[:1], slots[:1])
    assert (a.predictions == 124).all() and a.rounds.item() == 3
    assert (original_fixed48(net, t[:1], slots[:1]) == 123).all()
    for cap in (0, 49, True):
        try:
            active_execute(net, t, slots, cap)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid cap accepted")
    net.output_token_ids = (2, 3)
    try:
        active_execute(net, t, slots)
    except ValueError:
        pass
    else:
        raise AssertionError("restricted decoding accepted")
    return dict(passed=True, mixed_rounds=[3, 6, 8, 48], actual_row_rounds=65,
                offline_row_rounds=192, checks=["min3", "strict_q_gt_half", "full125_argmax",
                "all_cell_stability", "h_e_history_compaction", "cap1_2_3_8_48",
                "all_stop_no_extra_call", "single_row", "original_row_order", "invalid_caps",
                "restricted_alphabet_rejected", "nan_and_fp32_half_continue", "current_q_only",
                "fire_at_cap", "fixed48_continues_after_learned_stop"], training_launched=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("selftest", "correctness", "timing"), default="correctness")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--family", choices=("maze", "graph", "rank"), default="maze")
    parser.add_argument("--candidate", nargs=3, action="append", default=[], metavar=("NAME", "ARM", "CHECKPOINT"))
    parser.add_argument("--panel", type=int, default=4, help="generated DEVELOPMENT items per panel")
    parser.add_argument("--panels", nargs="+", help="subset of generated DEVELOPMENT panel names")
    parser.add_argument("--batch", type=int, default=4)
    parser.add_argument("--cap", type=int, default=48)
    parser.add_argument("--warmup", type=int, default=2)
    parser.add_argument("--repeats", type=int, default=5)
    args = parser.parse_args()
    if args.panel < 1 or args.batch < 1 or not 1 <= args.cap <= 48:
        parser.error("positive panel/batch sizes and cap in [1,48] required")
    if args.mode == "timing" and (args.cap != 48 or args.warmup < 1 or args.repeats < 3):
        parser.error("timing requires cap48, at least one warmup and three repeats")
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    if args.mode == "selftest":
        print(json.dumps(selftest(), indent=2))
        return
    if args.mode == "timing":
        require_idle_cpu()  # fail before any model forwards while parent runs
    panels, _, _, _ = S.make_development(args.seed, args.panel, args.family)
    if args.panels:
        unknown = set(args.panels) - panels.keys()
        if unknown:
            parser.error("unknown development panels: " + ", ".join(sorted(unknown)))
        panels = {name: panels[name] for name in args.panels}
    source = S.ROOT / f"artifacts/claude-fewex-20260927/runs/qual-loop-s{args.seed}/source.pt"
    specs = [("source", "loop_legacy", source)] + args.candidate
    if len({x[0] for x in specs}) != len(specs):
        parser.error("model names must be unique (source is reserved)")
    result = dict(mode=args.mode, development_only=True, official_holdout_opened=False,
                  device="cpu", threads=2, interop_threads=1, batch=args.batch, cap=args.cap,
                  family=args.family, seed=args.seed, torch_version=torch.__version__,
                  calibration_used=False, calibration_status="not implemented or tested",
                  training_launched=False, code_sha256={p.name: _sha(p) for p in
                  (Path(__file__), Path(S.__file__), S.ROOT / "scripts/claude_fewex_net.py",
                   S.ROOT / "scripts/claude_fewex_bench.py", S.HERE / "sleep_moe.py",
                   S.HERE / "fast_depthwise.py", S.HERE / "fast_adapters.py", S.HERE / "gated_relation.py")},
                  panel_sha256=hashlib.sha256(json.dumps({name: [dict(tokens=it.tokens, slot=it.slot)
                  for it in items] for name, items in panels.items()}, sort_keys=True).encode()).hexdigest(),
                  models={})
    for name, arm, path in specs:  # strictly serial; one frozen model at a time
        net, identity = load_frozen(arm, args.seed, path)
        before = {key: value.clone() for key, value in net.state_dict().items()}
        record = dict(identity=identity, correctness=compare_development(net, panels, batch=args.batch, cap=args.cap))
        if args.mode == "timing":
            record["timing"] = time_development(net, panels, batch=args.batch, warmup=args.warmup, repeats=args.repeats)
        assert all(torch.equal(value, before[key]) for key, value in net.state_dict().items())
        assert all(not p.requires_grad and p.grad is None for p in net.parameters())
        record["frozen_state_unchanged"] = True
        result["models"][name] = record
        print(json.dumps(dict(phase="model_done", name=name, **record)), flush=True)
        del net, before
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
