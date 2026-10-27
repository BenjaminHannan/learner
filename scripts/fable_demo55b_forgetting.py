#!/usr/bin/env python3
"""55b — Q11 forgetting arm with teeth (Mac CPU, $0, additive only).

After demo55's Q11 fine-tune arm got only 1 gradient step (a stunt — do not
repeat it), this script registers a third arm with a fixed wall-clock budget:

  * BASELINE: the QA-drilled variant from demo55's dev notes (the one that
    tied 20/20 on Q10: trained on story+question->gold rows, modes54's
    supervised rule — dev seeds 5591/5592/5593, disclosed in demo55 RESULTS).
    Here it is the registered protocol: QA-supervised training on the 20 Q10
    pairs, then fine-tuned on the 5 new teaching lines for a FIXED 60 seconds
    wall-clock (same optimiser/lr as its training: fresh Adam lr 1e-3,
    grad-clip 1.0), then asked (a) the 5 new questions and (b) the original
    20 Q10 questions again, seeds 5401/5402/5403 reported separately.
  * NOTEBOOK: teaches the same 120 Q10 facts, answers the 20 Q10 questions,
    then teaches the same 5 new facts and re-answers the 20 old + 5 new.
    Old must stay 20/20, new 5/5, wrong writes 0.

Everything demo55/modes54 owns is IMPORTED, never edited:
  fable_demo55_advantage (Q10/Q11 lines+items, STORY10/STORY11, MAX_LEN,
    build_vocab, make_rows, train_loop, encode_lm, decode_preds, score),
  fable_modes54_demo (norm, tokenize, detok, TinyTransformer, greedy_decode,
    TRAIN_LR), fable_modes54_scheduler, fable_listening_m1,
  fable_notebook_contract.

Frozen choices (also sealed in PASSMARKS.md before the registered run):
  QA training = exactly 250 fixed full-batch updates (Adam lr 1e-3,
    grad-clip 1.0) on the 20 Q10 story+question->gold rows. Dev-seed pilot
    (5591, pre-seal): 200 updates -> 18/20, 300 -> 20/20; 250 balances a
    strong starting point against the <600 s total budget. NO performance
    bar on the baseline (mark B4 = numbers reported, no mark).
  Fine-tune = fresh Adam lr 1e-3, full-batch next-token LM on the 5 new
    teaching lines, fixed 60 s wall-clock per seed (steps counted).
  Eval prompts are IDENTICAL before/after per question set: old Q10 always
    with the STORY10 prefix (same prefix as QA training, so only weights
    change), new Q11 always with the STORY11 prefix (as in demo55) — so the
    before/after gap isolates the weight change, not a prompt change.
  Greedy decode <= 8 tokens, exact match after word normalization.

    export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
    uv run --offline --no-project --python 3.12 --with torch --with numpy \
      python -B scripts/fable_demo55b_forgetting.py --out artifacts/fable-demo55b-20260921
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_notebook_contract as C  # noqa: E402
import fable_listening_m1 as L  # noqa: E402
from fable_modes54_scheduler import ModeScheduler  # noqa: E402
import fable_modes54_demo as D  # noqa: E402  (reused, never edited)
import fable_demo55_advantage as A55  # noqa: E402  (reused, never edited)

QA_UPDATES = 250
FT_SECONDS = 60.0
B5_SECONDS = 600


# ------------------------------------------------- notebook side (LISTENING path)
def run_notebook_55b(state_dir: str) -> dict:
    """Teach Q10, ask Q10 (before), teach 5 new, re-ask 20 old + 5 new.

    Wrong-write rule is byte-for-byte demo55's (mark B3): a teach/correct
    line must save exactly one fact whose stored ``raw`` equals the line;
    every other line must save none.
    """
    nb = C.Notebook(state_dir)
    ear = L.Listening(nb)
    sched = ModeScheduler(turn_handler=ear.hear, sleep_threshold=100_000)
    transcript: list[dict] = []
    wrong_writes: list[dict] = []
    before: dict[str, str] = {}
    after: dict[str, str] = {}
    after_new: dict[str, str] = {}

    def say(line: str, tag: str, bucket: dict | None = None,
            qid: str | None = None) -> str:
        before_ids = set(nb.facts)
        sched.submit(line)
        event = sched.step()
        reply = event["detail"].get("reply", "")
        new_ids = sorted(set(nb.facts) - before_ids, key=lambda x: int(x[1:]))
        act = line.split()[0] if line.split() else ""
        if act in ("teach", "correct"):
            ok = (len(new_ids) == 1
                  and nb.facts[new_ids[0]].get("raw") == line)
        else:
            ok = not new_ids
        if not ok:
            wrong_writes.append({
                "tag": tag, "line": line, "new_fact_ids": new_ids,
                "raws": [nb.facts[f].get("raw") for f in new_ids]})
        transcript.append({"tag": tag, "ben": line, "fable": reply,
                           "mode": event["mode"]})
        if bucket is not None and qid is not None:
            bucket[qid] = reply
        return reply

    for i, line in enumerate(A55.Q10_LINES):
        say(line, f"q10teach[{i}]")
    for item in A55.Q10_ITEMS:
        say(item["nb"], "q10ask_before", before, item["qid"])
    for i, line in enumerate(A55.Q11_LINES):
        say(line, f"q11teach[{i}]")
    for item in A55.Q11_ITEMS:
        say(item["nb"], "q11ask", after_new, item["qid"])
    for item in A55.Q10_ITEMS:
        say(item["nb"], "q10ask_after", after, item["qid"])

    heard_q10 = [r["ben"] for r in transcript
                 if r["tag"].startswith("q10teach")]
    heard_q11 = [r["ben"] for r in transcript
                 if r["tag"].startswith("q11teach")]
    return {"nb": nb, "sched": sched, "transcript": transcript,
            "before": before, "after": after, "after_new": after_new,
            "wrong_writes": wrong_writes, "heard_q10": heard_q10,
            "heard_q11": heard_q11}


# ------------------------------------------------------------ baseline side
def encode_qa_batch(model, rows: list[dict], pad_id: int):
    """modes54's supervised batch format (story+question->gold rows).

    Adapted from fable_modes54_demo.run_baseline's encode_batch (labels -100
    except on answer positions; A55.train_loop's CE shift pairs logits[t]
    with labels[t+1]). Only the row contents differ (Q10 pairs here).
    """
    torch = model.torch
    width = max(len(r["full"]) for r in rows)
    ids = torch.full((len(rows), width), pad_id, dtype=torch.long)
    labels = torch.full((len(rows), width), -100, dtype=torch.long)
    for i, row in enumerate(rows):
        ids[i, :len(row["full"])] = torch.tensor(row["full"])
        for t in range(row["ans_start"], len(row["full"])):
            labels[i, t] = row["full"][t]
    return ids, labels


def run_baseline_qa(seeds: tuple[int, ...]) -> dict:
    import torch
    vocab, inv, pad_id, sep_id, eos_id, unk_id = A55.build_vocab()
    rows10, oov10 = A55.make_rows(A55.Q10_ITEMS, A55.STORY10, vocab,
                                  sep_id, eos_id, unk_id)
    rows11, oov11 = A55.make_rows(A55.Q11_ITEMS, A55.STORY11, vocab,
                                  sep_id, eos_id, unk_id)
    lm_q11_lines = [vocab.get(t, unk_id)
                    for t in D.tokenize("\n".join(A55.Q11_LINES))]

    per_seed = {}
    for seed in seeds:
        t_seed = time.monotonic()
        torch.manual_seed(seed)
        model = D.TinyTransformer(len(vocab), max_len=A55.MAX_LEN)
        n_params = sum(p.numel() for p in model.parameters())

        # ---- QA-drilled training: 250 fixed updates on the 20 Q10 pairs ----
        t0 = time.monotonic()
        qa_ids, qa_labels = encode_qa_batch(model, rows10, pad_id)
        qa_loss = A55.train_loop(model, qa_ids, qa_labels, QA_UPDATES,
                                 D.TRAIN_LR, pad_id)
        train_s = time.monotonic() - t0
        preds10b, cross10b = A55.decode_preds(model, rows10, inv,
                                              eos_id, pad_id)
        correct10b = {
            it["qid"]: int(D.norm(preds10b[it["qid"]]) == D.norm(it["gold"]))
            for it in A55.Q10_ITEMS}
        preds11b, cross11b = A55.decode_preds(model, rows11, inv,
                                              eos_id, pad_id)
        correct11b = {
            it["qid"]: int(D.norm(preds11b[it["qid"]]) == D.norm(it["gold"]))
            for it in A55.Q11_ITEMS}

        # ---- Forgetting arm: fresh Adam lr 1e-3, LM on the 5 new teaching
        #      lines, FIXED 60 s wall-clock ----
        optim = torch.optim.Adam(model.parameters(), lr=D.TRAIN_LR)
        ft_ids, ft_labels = A55.encode_lm(model, lm_q11_lines, pad_id)
        ft_t0 = time.monotonic()
        ft_steps = 0
        ft_loss = None
        while time.monotonic() - ft_t0 < FT_SECONDS:
            loss = model.forward_loss(ft_ids, ft_labels, pad_id)
            optim.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optim.step()
            ft_loss = float(loss.detach())
            ft_steps += 1
        ft_s = time.monotonic() - ft_t0
        preds11a, cross11a = A55.decode_preds(model, rows11, inv,
                                              eos_id, pad_id)
        correct11a = {
            it["qid"]: int(D.norm(preds11a[it["qid"]]) == D.norm(it["gold"]))
            for it in A55.Q11_ITEMS}
        preds10a, cross10a = A55.decode_preds(model, rows10, inv,
                                              eos_id, pad_id)
        correct10a = {
            it["qid"]: int(D.norm(preds10a[it["qid"]]) == D.norm(it["gold"]))
            for it in A55.Q10_ITEMS}

        per_seed[str(seed)] = {
            "parameters": n_params,
            "qa_train": {"updates": QA_UPDATES,
                         "seconds": round(train_s, 2),
                         "final_loss": round(qa_loss, 6)},
            "q10_before": {"predictions": preds10b, "correct": correct10b,
                           "total": sum(correct10b.values())},
            "q11_before": {"predictions": preds11b, "correct": correct11b,
                           "total": sum(correct11b.values())},
            "fine_tune": {"seconds_budget": FT_SECONDS,
                          "seconds": round(ft_s, 2), "steps": ft_steps,
                          "final_loss": (round(ft_loss, 6)
                                         if ft_loss is not None else None)},
            "q11_after": {"predictions": preds11a, "correct": correct11a,
                          "total": sum(correct11a.values())},
            "q10_after": {"predictions": preds10a, "correct": correct10a,
                          "total": sum(correct10a.values())},
            "decode_crosscheck": bool(cross10b and cross11b
                                      and cross11a and cross10a),
            "seed_seconds": round(time.monotonic() - t_seed, 2),
        }
        row = per_seed[str(seed)]
        print(f"baseline seed {seed}: QA {QA_UPDATES} updates "
              f"{row['qa_train']['seconds']}s (loss "
              f"{row['qa_train']['final_loss']}), Q10 before "
              f"{row['q10_before']['total']}/20, Q11 before "
              f"{row['q11_before']['total']}/5, fine-tune {ft_steps} steps "
              f"{row['fine_tune']['seconds']}s, Q11 after "
              f"{row['q11_after']['total']}/5, Q10 after "
              f"{row['q10_after']['total']}/20", flush=True)

    return {"seeds": list(seeds), "vocab_size": len(vocab),
            "oov_hits": oov10 + oov11, "qa_updates": QA_UPDATES,
            "lr": D.TRAIN_LR, "ft_seconds": FT_SECONDS,
            "max_len": A55.MAX_LEN, "per_seed": per_seed,
            "trained_on": "QA-supervised on the 20 Q10 story+question->gold "
                          "rows (STORY10 prefix; modes54's supervised rule); "
                          "eval prompts identical before/after (Q10 with "
                          "STORY10, Q11 with STORY11)"}


# ------------------------------------------------------------------- main
def main(argv=None) -> int:
    t_start = time.monotonic()
    parser = argparse.ArgumentParser(
        description="55b forgetting arm: QA-drilled baseline + 60 s fine-tune")
    parser.add_argument("--out", default="artifacts/fable-demo55b-20260921")
    parser.add_argument("--state-dir", default=None)
    parser.add_argument("--skip-baseline", action="store_true")
    parser.add_argument("--seeds", default="5401,5402,5403")
    args = parser.parse_args(argv)
    seeds = tuple(int(s) for s in args.seeds.split(","))

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    state = Path(args.state_dir) if args.state_dir else out / "demo55b-notebook"
    if state.exists():
        shutil.rmtree(state)

    print("=" * 72, flush=True)
    print("FABLE DEMO 55b — Q11 forgetting arm (QA-drilled baseline, 60 s "
          "fine-tune)", flush=True)
    print("=" * 72, flush=True)

    run = run_notebook_55b(str(state))
    identity10 = run["heard_q10"] == A55.Q10_LINES
    identity11 = run["heard_q11"] == A55.Q11_LINES
    nb10b = A55.score(run["before"], A55.Q10_ITEMS)
    nb10a = A55.score(run["after"], A55.Q10_ITEMS)
    nb11 = A55.score(run["after_new"], A55.Q11_ITEMS)
    wrong_writes = run["wrong_writes"]
    print(f"\nnotebook Q10 before {nb10b['total']}/20, Q10 after "
          f"{nb10a['total']}/20, Q11 new {nb11['total']}/5, wrong writes "
          f"{len(wrong_writes)}, identity Q10={identity10} Q11={identity11}",
          flush=True)

    baseline = None
    if not args.skip_baseline:
        print("\n--- baseline: QA-drilled, then 60 s fine-tune per seed ---",
              flush=True)
        baseline = run_baseline_qa(seeds)

    # ---------------------------------------------------------------- marks
    b1 = nb10a["total"] == 20
    b2 = nb11["total"] == 5
    b3 = len(wrong_writes) == 0
    b4 = bool(baseline) and set(baseline["per_seed"]) == {
        str(s) for s in seeds} and all(
        len(r["q10_before"]["correct"]) == 20
        and len(r["q10_after"]["correct"]) == 20
        and len(r["q11_before"]["correct"]) == 5
        and len(r["q11_after"]["correct"]) == 5
        and r["decode_crosscheck"]
        for r in baseline["per_seed"].values())
    elapsed = time.monotonic() - t_start
    b5 = elapsed < B5_SECONDS
    marks = {
        "B1_notebook_old_20_of_20_after": {
            "pass": b1, "value": f"{nb10a['total']}/20"},
        "B2_notebook_new_5_of_5": {"pass": b2, "value": f"{nb11['total']}/5"},
        "B3_wrong_writes_zero": {"pass": b3, "value": str(len(wrong_writes))},
        "B4_baseline_reported_per_seed": {
            "pass": b4,
            "value": ("3/3 seeds x (20+5+5+20) integers, decode cross-check "
                      "ok" if b4 else "incomplete report or cross-check "
                      "failed")},
        "B5_under_10_minutes": {"pass": b5, "value": f"{elapsed:.1f}s"},
    }

    report = {
        "beats": ["Q10 before", "Q11 60 s forgetting arm", "Q10 after"],
        "q10_items": A55.Q10_ITEMS, "q11_items": A55.Q11_ITEMS,
        "q10_lines": A55.Q10_LINES, "q11_lines": A55.Q11_LINES,
        "qa_updates": QA_UPDATES, "ft_seconds": FT_SECONDS,
        "notebook": {"q10_before": nb10b, "q10_after": nb10a,
                     "q11": nb11, "wrong_writes": wrong_writes,
                     "identity_q10": identity10,
                     "identity_q11": identity11,
                     "modes_seen": sorted(
                         {e["to"] for e in run["sched"].mode_log})},
        "baseline": baseline,
        "marks": marks,
        "elapsed_seconds": round(elapsed, 1),
        "seeds": list(seeds),
        "registered": not args.skip_baseline,
    }
    (out / "demo55b-results.json").write_text(json.dumps(report, indent=1))
    (out / "demo55b-transcript.txt").write_text(
        "\n".join(f"[{r['mode']}] {r['ben']}\n    -> {r['fable']}"
                  for r in run["transcript"]))

    print("\n" + "=" * 72, flush=True)
    print("SCOREBOARD — new facts /5 and old Q10 /20 before+after "
          "(never averaged)", flush=True)
    print("=" * 72, flush=True)
    print(f"notebook: Q10 before {nb10b['total']}/20, Q11 new "
          f"{nb11['total']}/5, Q10 after {nb10a['total']}/20", flush=True)
    if baseline:
        for s in seeds:
            cell = baseline["per_seed"][str(s)]
            print(f"baseline {s}: Q11 new {cell['q11_before']['total']}/5 -> "
                  f"{cell['q11_after']['total']}/5 "
                  f"({cell['fine_tune']['steps']} steps, "
                  f"{cell['fine_tune']['seconds']}s); Q10 old "
                  f"{cell['q10_before']['total']}/20 -> "
                  f"{cell['q10_after']['total']}/20", flush=True)

    print("\nPASS MARKS (sealed in PASSMARKS.md before this registered run)",
          flush=True)
    for key in sorted(marks):
        m = marks[key]
        print(f"  {key:<32} {'PASS' if m['pass'] else 'FAIL':<5} {m['value']}",
              flush=True)
    print(f"story identity Q10={identity10} Q11={identity11}; wrong writes "
          f"counted={len(wrong_writes)}", flush=True)
    if wrong_writes:
        for w in wrong_writes:
            print(f"  WRONG WRITE: {w}", flush=True)
    print(f"wrote {out / 'demo55b-results.json'}", flush=True)
    print(f"TOTAL_ELAPSED_SECONDS {elapsed:.1f}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
