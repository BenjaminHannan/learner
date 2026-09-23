"""Parity, gradient-routing and no-oracle tests for the two soft-read arms (Claude, 2026-09-19).

    PY -B tests/test_premonition_softread.py
    PY -B scripts/premonition_softread.py --self-check

All on CPU, all on real frozen validation batches. Checks:

  0  plumbing: the MRO puts the soft-insert copy under `CardBypassMini`; with BOTH switches off the copied
     `_insert` / `forward` reproduce the frozen losses exactly in gold, teacher and own mode; the state_dict
     is the baseline's tensor-for-tensor (so every existing eval script loads these checkpoints unchanged).

  A (--answer-grad)
  a1 forward parity: with the same seed and generator the losses and the per-question answer-correctness
     are EXACTLY the baseline's in all three modes -- the straight-through term is zero in the forward pass.
  a2 gradient routing: with weights ask = 0 (L_ans only), d(loss)/d(heads.query.weight) and
     d(loss)/d(writer.key.weight) are EXACTLY zero in the baseline and non-zero with --answer-grad; the same
     for kappa and the age bias.
  a3 one optimizer step on the L_ans-only loss (AdamW, no grad clipping -- clipping rescales by the total
     grad norm, which differs between the arms and would smear the change over every parameter) moves the
     retrieval-path parameters apart while every parameter the new gradient CANNOT reach -- decoder.*,
     heads.halt.*, heads.ask.* -- stays bit-identical. That is "differs only because of the new gradient",
     made checkable. NOTE the new gradient legitimately reaches most of the REST of the model: the ASK query
     is read off the register row THINK produces, so the straight-through term flows back through Think (its
     register and loop-step embeddings and its binder included), the reader and the embedding. Only the
     answer decoder and the HALT / ASK heads sit strictly downstream of the card row.
  a4 eval-mode outputs (R.own_fixed at K = 2, 3, 4 and model.answer) are identical to the baseline's for
     identical weights.

  B (--soft-no-oracle)
  b1 no gold label influences any gradient: perturbing batch.gold_lines (rolled, and blanked to -1) leaves
     the loss and EVERY parameter gradient bit-identical.
  b2 the answer loss gives a non-zero gradient on the query and card-key weights (retrieval is trainable
     from answers alone, whether or not it succeeds).
  b3 the arm's shape: L_ask is exactly zero, the curriculum is own-mode with p_own = 1.0 from step 0, the
     ASK logit is the forced constant, the inserted row really is the soft mixture (it differs from the hard
     row), and the argmax card is marked fetched.
  b4 the hard evaluation path runs and produces the SAME report schema as the baseline's, and the extra
     soft-read report has the by-hop schema too.

  C  launcher: a 12-step CPU run of each arm through scripts/premonition_softread.py (--skip-eval, into a
     temporary directory) finishes, records the arm in its checkpoint blob, round-trips through this
     module's `load_from` AND through the untouched `premonition_first_card_probe.load_from`, and reports
     steps/second.

  D  periodic checkpoints and --resume: an 8-step run and a 3-step run resumed for 5 more steps reach
     BIT-IDENTICAL parameters and bit-identical trainer state at every one of the 8 steps, across the
     gold -> teacher phase boundary; every intermediate checkpoint is kept, none is left as a .tmp, and each
     carries the model, the optimizer state and the trainer state. --resume with no checkpoint starts from
     scratch; --resume with a different --steps refuses (the FLOP budget, and therefore the curriculum
     clock, would not line up).

  E  the four-channel evidence-oracle table: all four channels on for the baseline and --answer-grad, all
     four off for --soft-no-oracle and for the no-store control, and ordinary answer supervision recorded
     separately as NOT an evidence label. The table in the result JSON matches the module's own table.
"""
from __future__ import annotations

from dataclasses import replace
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import premonition_ovn_ladder as L  # noqa: E402
import premonition_ovn_retrieval as R  # noqa: E402

ARM, SEED = "bypass-k1", 0
ANS_ONLY = {"lm": 0.0, "ask": 0.0, "ans": 1.0, "halt": 0.0}
RETRIEVAL = ("heads.query.weight", "writer.key.weight", "heads.log_kappa", "think.age_bias")
# Parameters the straight-through term cannot reach: they sit strictly downstream of the card row (the
# answer decoder and the two per-loop heads), so their gradient must be bit-identical to the baseline's.
# Everything else (Think's own embeddings, the binder, the reader, the embedding) feeds the register row the
# ASK query is read off, so the new gradient reaches it and SHOULD change.
UNREACHABLE = ("decoder.", "heads.halt.", "heads.ask.")


def _losses(model, batch, mode, p_own, seed, weights=None):
    import torch
    gen = torch.Generator().manual_seed(seed)
    model.train()
    with torch.no_grad():
        out = model(batch, mode=mode, p_own=p_own, generator=gen, weights=weights)
    return {k: float(out[k]) for k in ("lm", "ask", "ans", "halt", "loss")}


def _grads(model, batch, mode, p_own, seed, weights=None):
    """{name: grad tensor or None} after one backward pass; the model is left with its grads populated."""
    import torch
    gen = torch.Generator().manual_seed(seed)
    model.zero_grad(set_to_none=True)
    model.train()
    out = model(batch, mode=mode, p_own=p_own, generator=gen, weights=weights)
    out["loss"].backward()
    return float(out["loss"]), {n: (None if p.grad is None else p.grad.detach().clone())
                                for n, p in model.named_parameters()}


def _maxabs(tensor):
    import torch
    return 0.0 if tensor is None else float(tensor.abs().max())


def _step_once(model, batch, mode, p_own, seed, weights=None, lr=1e-3):
    """One AdamW step WITHOUT gradient clipping (clipping rescales by the total grad norm, which differs
    between the arms and would smear the new gradient over every parameter)."""
    import torch
    opt = torch.optim.AdamW(model.parameters(), lr=lr)
    loss, _ = _grads(model, batch, mode, p_own, seed, weights=weights)
    opt.step()
    return loss


def main() -> int:
    L.bootstrap()
    import torch
    import premonition_softread as S
    import premonition_first_card_probe as P
    torch.set_num_threads(2)
    failures = []

    def check(name, ok, detail=""):
        print(("PASS " if ok else "FAIL ") + name + ((" :: " + detail) if detail else ""), flush=True)
        if not ok:
            failures.append(name)

    items = L.load_split("validation")
    batch = items[0][0]

    # ---- 0. plumbing ---------------------------------------------------------------
    names = [c.__name__ for c in S.softread_class().__mro__]
    check("MRO delegates the bypass insert to the copied _insert",
          names[:4] == ["SoftReadCardBypassMini", "CardBypassMini", "SoftInsertMixin", "PremonitionMini"],
          " -> ".join(names))

    base = R.build(ARM, SEED)
    off = S.build(ARM, SEED)
    bsd, osd = base.state_dict(), off.state_dict()
    check("state_dict is the baseline's, key for key", sorted(bsd) == sorted(osd),
          f"{len(bsd)} vs {len(osd)} tensors")
    check("state_dict is the baseline's, value for value",
          all(torch.equal(bsd[k], osd[k]) for k in bsd))
    for mode, p_own in (("gold", 0.0), ("teacher", 0.0), ("own", 0.75)):
        a, b = _losses(base, batch, mode, p_own, 7), _losses(off, batch, mode, p_own, 7)
        check(f"both switches off: {mode}-mode losses are the frozen ones", a == b, f"{a} vs {b}")

    # ---- A. --answer-grad ---------------------------------------------------------
    grad_model = S.build(ARM, SEED, answer_grad=True)
    check("answer-grad model carries no extra parameters",
          sorted(grad_model.state_dict()) == sorted(bsd)
          and grad_model.num_parameters() == base.num_parameters(),
          f"{grad_model.num_parameters()} parameters")
    for mode, p_own in (("gold", 0.0), ("teacher", 0.0), ("own", 0.75)):
        a, b = _losses(base, batch, mode, p_own, 7), _losses(grad_model, batch, mode, p_own, 7)
        check(f"a1 --answer-grad {mode}-mode losses equal the baseline exactly", a == b, f"{a} vs {b}")

    b_loss, b_grads = _grads(base, batch, "own", 0.75, 7, weights=ANS_ONLY)
    g_loss, g_grads = _grads(grad_model, batch, "own", 0.75, 7, weights=ANS_ONLY)
    check("a2 the L_ans-only loss itself is unchanged", b_loss == g_loss, f"{b_loss} vs {g_loss}")
    check("a2 baseline: d(L_ans)/d(query, card key, kappa, age bias) is EXACTLY zero",
          all(_maxabs(b_grads[n]) == 0.0 for n in RETRIEVAL),
          json.dumps({n: _maxabs(b_grads[n]) for n in RETRIEVAL}))
    check("a2 --answer-grad: the same gradients are non-zero",
          all(_maxabs(g_grads[n]) > 0.0 for n in RETRIEVAL),
          json.dumps({n: round(_maxabs(g_grads[n]), 9) for n in RETRIEVAL}))
    unreachable = [n for n in b_grads if n.startswith(UNREACHABLE)]
    same = [n for n in unreachable
            if (b_grads[n] is None and g_grads[n] is None)
            or (b_grads[n] is not None and torch.equal(b_grads[n], g_grads[n]))]
    check("a2 gradients of the answer decoder and the HALT / ASK heads are bit-identical",
          len(same) == len(unreachable) and unreachable,
          f"{len(same)}/{len(unreachable)} identical; differing: "
          f"{[n for n in unreachable if n not in same][:4]}")

    after_base = R.build(ARM, SEED)
    after_grad = S.build(ARM, SEED, answer_grad=True)
    l1 = _step_once(after_base, batch, "own", 0.75, 7, weights=ANS_ONLY)
    l2 = _step_once(after_grad, batch, "own", 0.75, 7, weights=ANS_ONLY)
    bsd2, gsd2 = after_base.state_dict(), after_grad.state_dict()
    moved = [n for n in bsd2 if not torch.equal(bsd2[n], gsd2[n])]
    frozen_all = [n for n in bsd2 if n.startswith(UNREACHABLE)]
    frozen_same = [n for n in frozen_all if torch.equal(bsd2[n], gsd2[n])]
    check("a3 the loss of the optimized step was identical", l1 == l2, f"{l1} vs {l2}")
    check("a3 one L_ans-only step moves the whole retrieval path apart",
          all(n in moved for n in RETRIEVAL),
          f"{len(moved)} of {len(bsd2)} tensors differ; unmoved retrieval tensors: "
          f"{[n for n in RETRIEVAL if n not in moved]}")
    check("a3 one step leaves every parameter the new gradient cannot reach bit-identical",
          len(frozen_same) == len(frozen_all) and frozen_all,
          f"{len(frozen_same)}/{len(frozen_all)}")

    with torch.no_grad():
        eb = R.build(ARM, SEED)
        eg = S.build(ARM, SEED, answer_grad=True)
        eb.eval()
        eg.eval()
        ok = True
        detail = []
        for k in (2, 3, 4):
            a_ok, a_gold = R.own_fixed(eb, batch, k)
            b_ok, b_gold = R.own_fixed(eg, batch, k)
            ok &= bool(torch.equal(a_ok, b_ok) and torch.equal(a_gold, b_gold))
            detail.append(f"K{k}={int(a_ok.sum())}")
        ans_a, ans_b = eb.answer(batch), eg.answer(batch)
        ok &= bool(torch.equal(ans_a.tokens, ans_b.tokens) and torch.equal(ans_a.loops, ans_b.loops))
    check("a4 eval-mode outputs are identical to the baseline's", ok, " ".join(detail))

    # ---- B. --soft-no-oracle ------------------------------------------------------
    soft = S.build(ARM, SEED, 1.0, soft_no_oracle=True)
    check("b3 the arm forces the ASK decision on", soft.force_ask is True)
    from premonition.train import Curriculum
    plan = Curriculum(**S.SOFT_CURRICULUM).plan(0.0)
    check("b3 the curriculum is own mode with p_own = 1.0 from step 0",
          plan.mode == "own" and plan.p_own == 1.0, f"{plan.mode} p_own={plan.p_own}")
    out_soft = _losses(soft, batch, "own", 1.0, 7)
    check("b3 L_ask is exactly zero (no evidence-label loss)", out_soft["ask"] == 0.0,
          json.dumps(out_soft))

    s_loss, s_grads = _grads(soft, batch, "own", 1.0, 7, weights=ANS_ONLY)
    check("b2 the answer loss reaches the query and card-key weights",
          _maxabs(s_grads["heads.query.weight"]) > 0.0 and _maxabs(s_grads["writer.key.weight"]) > 0.0,
          json.dumps({n: round(_maxabs(s_grads[n]), 9) for n in RETRIEVAL}))

    ref_loss, ref_grads = _grads(soft, batch, "own", 1.0, 7)
    for label, gold_lines in (("rolled", batch.gold_lines.roll(1, 0)),
                              ("blanked", torch.full_like(batch.gold_lines, -1)),
                              ("shifted", torch.where(batch.gold_lines >= 0,
                                                      batch.gold_lines.clamp_min(0) // 2 + 1,
                                                      batch.gold_lines))):
        perturbed = replace(batch, gold_lines=gold_lines)
        p_loss, p_grads = _grads(soft, perturbed, "own", 1.0, 7)
        same_loss = p_loss == ref_loss
        bad = [n for n in ref_grads
               if not ((ref_grads[n] is None and p_grads[n] is None)
                       or (ref_grads[n] is not None and torch.equal(ref_grads[n], p_grads[n])))]
        check(f"b1 gold_lines {label}: the loss is unchanged", same_loss, f"{ref_loss} vs {p_loss}")
        check(f"b1 gold_lines {label}: every parameter gradient is unchanged", not bad,
              f"{len(bad)} differ, e.g. {bad[:4]}")
    check("b1 the perturbations really changed the labels",
          not torch.equal(batch.gold_lines, batch.gold_lines.roll(1, 0)))

    # the inserted row is the mixture, and the argmax is marked fetched
    with torch.no_grad():
        soft.eval()
        hidden = soft.read(batch)
        store = soft.build_store(hidden, batch)
        mentions = soft._mentions(batch)
        everyone = torch.arange(batch.q_visit.shape[0])
        rows_seen = {}
        for mode in ("hard", "soft"):
            ep = soft._start(batch, hidden, store, mentions)
            _, _, ask, scores = soft._step(ep, everyone, 0, store)
            cards = store.top(scores, 1)
            soft.insert_with(ep, store, everyone, cards, scores, mode)
            rows_seen[mode] = ep.x[:, soft._card_base].clone()
            if mode == "soft":
                argmax_fetched = bool(ep.fetched.gather(1, cards.clamp_min(0)).all())
                bound = ep.valid[:, soft.config.question_rows:
                                 soft.config.question_rows + soft.config.slots].clone()
        check("b3 the ASK logit is the forced constant",
              bool((ask == S.FORCED_ASK_LOGIT).all()), f"min {float(ask.min())}")
        check("b3 the soft row differs from the hard row",
              not torch.equal(rows_seen["hard"], rows_seen["soft"]),
              "max |soft - hard| = {:.4f}".format(float((rows_seen["soft"] - rows_seen["hard"]).abs().max())))
        check("b3 the argmax card is marked fetched", argmax_fetched)
        check("b3 a soft insert leaves the entity slots as the question found them",
              bool(torch.equal(bound, soft._start(batch, hidden, store, mentions).valid[
                  :, soft.config.question_rows:soft.config.question_rows + soft.config.slots])))

    def schema(node):
        if isinstance(node, dict):
            return {k: schema(v) for k, v in sorted(node.items())}
        return type(node).__name__

    one = items[:1]
    base_report = R.evaluate(R.build(ARM, SEED), one)
    soft_report = R.evaluate(soft, one)           # the HARD path, with the ASK decision forced on
    check("b4 the hard evaluation report has the baseline schema",
          sorted(base_report) == sorted(soft_report)
          and all(schema(base_report[k]) == schema(soft_report[k]) for k in base_report
                  if k != "learned_halting"),
          f"{sorted(soft_report)}")
    sr = S.soft_read_report(soft, one)
    check("b4 the soft-read report has the by-hop schema",
          sorted(sr) == ["fixed_K2", "fixed_K3", "fixed_K4"]
          and schema(sr["fixed_K3"]) == schema(base_report["fixed_K3"]),
          json.dumps({k: v["one_hop"]["correct"] for k, v in sr.items()}))

    # ---- C. the launcher ----------------------------------------------------------
    for flag, tag in (("--answer-grad", "answer-grad"), ("--soft-no-oracle", "soft-no-oracle")):
        smoke = Path(tempfile.mkdtemp(prefix="softread-smoke-"))
        try:
            name = "smoke-" + tag
            cmd = [sys.executable, "-u", "-B", str(ROOT / "scripts" / "premonition_softread.py"),
                   "--arm", ARM, "--seed", "0", "--steps", "12", "--threads", "2", "--log-every", "6",
                   "--device", "cpu", "--autocast", "off", "--skip-eval", flag,
                   "--name", name, "--out", str(smoke)]
            proc = subprocess.run(cmd, cwd=str(ROOT), env=dict(os.environ), capture_output=True, text=True)
            blob_path = smoke / "ckpt" / (name + ".pt")
            if proc.returncode != 0 or not blob_path.exists():
                check(f"C 12-step {tag} launcher run finishes", False,
                      (proc.stdout + proc.stderr)[-1500:])
                continue
            run = json.loads((smoke / "runs" / (name + ".json")).read_text())
            check(f"C 12-step {tag} launcher run finishes", True,
                  "{} steps, {:.3f} steps/s".format(run["steps_done"], run["steps_per_second"]))
            blob = torch.load(blob_path, weights_only=False)
            key = "answer_grad" if tag == "answer-grad" else "soft_no_oracle"
            check(f"C {tag} checkpoint records the arm",
                  blob.get(key) is True and run.get(key) is True
                  and blob.get("force_ask") is (tag == "soft-no-oracle"),
                  f"force_ask={blob.get('force_ask')}, curriculum={blob.get('curriculum')}")
            check(f"C {tag} reports steps/second", isinstance(run.get("steps_per_second"), float)
                  and run["steps_per_second"] > 0)
            reloaded, rblob = S.load_from(name, smoke / "ckpt")
            check(f"C {tag} round-trips through premonition_softread.load_from",
                  type(reloaded).__name__ == "SoftReadCardBypassMini"
                  and reloaded.force_ask is (tag == "soft-no-oracle"))
            plain, _ = P.load_from(name, smoke / "ckpt")
            with torch.no_grad():
                a_ok, _ = R.own_fixed(reloaded, batch, 3)
                plain.eval()
                b_ok, _ = R.own_fixed(plain, batch, 3)
            check(f"C {tag} checkpoint also loads in the UNTOUCHED first-card probe loader",
                  type(plain).__name__ == "CardBypassMini"
                  and all(torch.equal(plain.state_dict()[k], reloaded.state_dict()[k])
                          for k in plain.state_dict()),
                  "hard-path one-hop {} (variant loader) vs {} (plain loader)".format(
                      int(a_ok.sum()), int(b_ok.sum())))
        finally:
            shutil.rmtree(smoke, ignore_errors=True)

    # ---- D. periodic checkpoints and --resume -------------------------------------
    def launch(out, name, *extra, expect_ok=True):
        cmd = [sys.executable, "-u", "-B", str(ROOT / "scripts" / "premonition_softread.py"),
               "--arm", ARM, "--seed", "0", "--answer-grad", "--steps", "40", "--threads", "2",
               "--log-every", "100", "--device", "cpu", "--autocast", "off", "--skip-eval",
               "--name", name, "--out", str(out), *extra]
        proc = subprocess.run(cmd, cwd=str(ROOT), env=dict(os.environ), capture_output=True, text=True)
        if expect_ok and proc.returncode != 0:
            raise AssertionError((proc.stdout + proc.stderr)[-1500:])
        return proc

    resume_dir = Path(tempfile.mkdtemp(prefix="softread-resume-"))
    try:
        launch(resume_dir, "ref", "--max-steps", "8", "--ckpt-every", "1")
        launch(resume_dir, "res", "--max-steps", "3", "--ckpt-every", "1")
        again = launch(resume_dir, "res", "--max-steps", "5", "--ckpt-every", "1", "--resume")
        check("d1 the resumed run reports where it restarted", "resumed res at step 3" in again.stdout,
              again.stdout.strip().splitlines()[0] if again.stdout.strip() else "")
        worst, bad_steps, phase_seen = 0.0, [], set()
        for step in range(1, 9):
            a = torch.load(resume_dir / "ckpt" / f"ref-step{step:06d}.pt", weights_only=False)
            b = torch.load(resume_dir / "ckpt" / f"res-step{step:06d}.pt", weights_only=False)
            asd, bsd = a["state_dict"], b["state_dict"]
            if any(not torch.equal(asd[n], bsd[n]) for n in asd):
                bad_steps.append(step)
                worst = max(worst, max(float((asd[n] - bsd[n]).abs().max()) for n in asd))
            ta, tb = a["trainer_state"], b["trainer_state"]
            if any(not (torch.equal(ta[k], tb[k]) if k == "generator" else ta[k] == tb[k]) for k in ta):
                bad_steps.append(-step)
            phase_seen.add(round(ta["flops"], 6))
        check("d1 resume reproduces the uninterrupted run bit-for-bit at every step",
              not bad_steps, f"steps differing: {bad_steps} (worst |dw| = {worst:.3e})")
        check("d1 the resume crossed the gold -> teacher boundary", len(phase_seen) == 8,
              f"{len(phase_seen)} distinct FLOP counts over 8 steps")
        kept = sorted(p.name for p in (resume_dir / "ckpt").glob("res-step*.pt"))
        check("d2 every intermediate checkpoint is kept",
              kept == [f"res-step{s:06d}.pt" for s in range(1, 9)], str(kept))
        check("d2 no partial .tmp file is left behind",
              not list((resume_dir / "ckpt").glob("*.tmp*")))
        blob = torch.load(resume_dir / "ckpt" / "res-step000003.pt", weights_only=False)
        check("d2 a periodic checkpoint carries model, optimizer and trainer state",
              all(k in blob for k in ("state_dict", "optimizer_state", "trainer_state", "step",
                                      "steps_requested", "oracle_use"))
              and blob["kind"] == "periodic" and blob["step"] == 3,
              f"keys: {sorted(k for k in blob if k != 'state_dict')}")
        fresh = Path(tempfile.mkdtemp(prefix="softread-resume-fresh-"))
        try:
            proc = launch(fresh, "cold", "--max-steps", "2", "--ckpt-every", "1", "--resume")
            check("d3 --resume with no checkpoint starts from scratch",
                  "starting from scratch" in proc.stdout)
        finally:
            shutil.rmtree(fresh, ignore_errors=True)
        bad = subprocess.run(
            [sys.executable, "-u", "-B", str(ROOT / "scripts" / "premonition_softread.py"),
             "--arm", ARM, "--seed", "0", "--answer-grad", "--steps", "41", "--max-steps", "2",
             "--ckpt-every", "1", "--resume", "--threads", "2", "--skip-eval",
             "--name", "res", "--out", str(resume_dir)],
            cwd=str(ROOT), env=dict(os.environ), capture_output=True, text=True)
        check("d3 --resume refuses a different --steps (the FLOP budget would not line up)",
              bad.returncode != 0 and "same --steps" in (bad.stdout + bad.stderr),
              (bad.stdout + bad.stderr).strip().splitlines()[-1:] and
              (bad.stdout + bad.stderr).strip().splitlines()[-1])
        ref_run = json.loads((resume_dir / "runs" / "ref.json").read_text())
        check("E the result JSON carries the evidence-oracle table",
              ref_run["oracle_use"]["channels"] == dict.fromkeys(S.ORACLE_CHANNELS, True)
              and ref_run["oracle_use"]["any_evidence_label"] is True
              and ref_run["oracle_use"]["answer_supervision_is_an_evidence_label"] is False,
              json.dumps(ref_run["oracle_use"]["channels"]))
    finally:
        shutil.rmtree(resume_dir, ignore_errors=True)

    # ---- E. the evidence-oracle table --------------------------------------------
    check("E four channels, named",
          S.ORACLE_CHANNELS == ("ask_set_target", "teacher_insertions", "early_ans_weighting",
                                "should_search_bce"), str(S.ORACLE_CHANNELS))
    for tag, expect_any in (("baseline", True), ("answer-grad", True), ("soft-no-oracle", False)):
        table = S.oracle_use(tag, True)
        check(f"E {tag}: all four channels are {'on' if expect_any else 'off'}",
              all(v is expect_any for v in table["channels"].values())
              and table["any_evidence_label"] is expect_any
              and set(table["channels"]) == set(S.ORACLE_CHANNELS),
              json.dumps(table["channels"]))
        check(f"E {tag}: answer supervision is recorded, and NOT as an evidence label",
              table["answer_supervision"] is True
              and table["answer_supervision_is_an_evidence_label"] is False)
    nostore = S.oracle_use("baseline", False)
    check("E the no-store control has no evidence channel at all",
          not any(nostore["channels"].values()) and "no card store" in nostore["note"])

    print(("\nALL CHECKS PASSED" if not failures else "\nFAILURES: " + ", ".join(failures)), flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
