#!/usr/bin/env python3
"""Experiment 125 -- same-metric comparison table for the demo (Muse).

Borrowed SmolLM2-360M (exp 66 baseline) vs our joined-up agent, on BOTH
splits with ONE scorer (exp 113 scorer v2 + contains-gold column).

SmolLM2 arms (fresh model runs, same prompts / greedy decoding as exp 66):
  incontext: all taught sentences in the prompt, then the question.
  raglite:   exp 66 BM25 top-3 retrieval.
Fable-Edit-200 SmolLM2 rows: RE-SCORED from exp 66's saved answer strings
(scripts/fable_bench66_baselines.py model already ran them; no re-run).
4-hop split (SmolLM2 never run on it): fresh runs, model files already
downloaded, local_files_only=True (no downloads).

Loop arms (loop102 / loop113 / loop113b): READ from existing JSONs, NOT re-run.

Scorer v2 vendored from scripts/fable_bench113_run.py (classify_v2,
extract_answer, norm, ABSTAIN_PHRASES) -- identical logic, no edits there.

Run ONLY after PASSMARKS.md is sealed (Mac CPU, offline):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 HF_HUB_OFFLINE=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    --with transformers python -B scripts/fable_bench125_run.py --smoke
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    --with transformers python -B scripts/fable_bench125_run.py --run [--limit N]
"""

from __future__ import annotations

import argparse
import json
import re
import string
import sys
import time
from pathlib import Path

import numpy as np
import torch

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from fable_bench66_baselines import (  # noqa: E402 (prompt/decoding contract)
    MODEL_ID, bm25_top3, build_prompt, greedy_answer)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-bench125-20260922"
DATA_A = ROOT / "data" / "open" / "bench65" / "fable_edit_200.jsonl"
DATA_B = ROOT / "data" / "open" / "bench103" / "fable_edit103_s2fresh_4hop.jsonl"
BENCH66 = ROOT / "artifacts" / "fable-bench66-20260921" / "fable_bench66_results.json"
LOOP102_A = ROOT / "artifacts" / "fable-bench113-20260922" / "fable_bench113_loop102_fable_edit_200_rows.jsonl"
LOOP102_B = ROOT / "artifacts" / "fable-bench113-20260922" / "fable_bench113_loop102_s2fresh_4hop_rows.jsonl"
LOOP113_A = ROOT / "artifacts" / "fable-bench113-20260922" / "fable_bench113_loop113_fable_edit_200_rows.jsonl"
LOOP113_B = ROOT / "artifacts" / "fable-bench113-20260922" / "fable_bench113_loop113_s2fresh_4hop_rows.jsonl"
LOOP113B_A = ROOT / "artifacts" / "fable-bench113b-20260922" / "fable_bench113b_loop113b_fable_edit_200_rows.jsonl"
LOOP113B_B = ROOT / "artifacts" / "fable-bench113b-20260922" / "fable_bench113b_loop113b_s2fresh_4hop_rows.jsonl"

# ---- scorer v2 (verbatim logic from scripts/fable_bench113_run.py) ----
ABSTAIN_PHRASES = (
    "i don't know",
    "i dont know",
    "was that a question",
    "i didn't understand that",
    "i did not understand",
    "i didn't catch anything",
    "i can take one fact at a time",
    "could you split that",
    "do you know that yourself",
    "i only save facts you tell me directly",
    "i can only follow",
    "please say it like",
    "i can only handle one-word names",
    "i didn't get the value",
    "which is not someone i can look up",
    "i know more than one",
    "which one do you mean",
    "please answer with",
    "please answer yes or no",
    "i wasn't waiting for an answer",
    "i couldn't read that message",
    "do you want me to change it to",
)
_ABSTAIN_RES = [re.compile(r"\b" + re.escape(p) + r"\b")
                for p in ABSTAIN_PHRASES]


def norm(s) -> str:
    s = (s or "").lower().replace("\u2019", "'")
    s = "".join(ch for ch in s if ch not in string.punctuation)
    return " ".join(t for t in s.split() if t not in ("a", "an", "the"))


def extract_answer(reply: str) -> str:
    low = (reply or "").lower()
    hits = [low.rfind(" is "), low.rfind(" are ")]
    idx = max(hits)
    tail = reply[idx + 4:] if idx >= 0 else (reply or "")
    return tail.strip().rstrip(".").strip()


def classify_v2(reply: str, golds: list[str]) -> tuple[str, bool, bool]:
    value = extract_answer(reply)
    nv = norm(value)
    ngs = [norm(g) for g in golds if norm(g)]
    exact = bool(nv) and nv in ngs
    if exact:
        return "correct", True, True
    contains = any(g in norm(reply) for g in ngs)
    low = (reply or "").lower()
    if any(rx.search(low) for rx in _ABSTAIN_RES):
        return "abstain", False, bool(contains)
    return "wrong", False, bool(contains)


# ---- data helpers ----
def load_split(path: Path) -> list[dict]:
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines()
            if l.strip()]
    items = []
    for r in rows:
        taught = r.get("taught") or []
        sents = [str(t.get("sentence_en", "")).strip() for t in taught
                 if isinstance(t, dict) and t.get("sentence_en")]
        golds = [str(g) for g in (r.get("gold") or [])]
        golds += [str(g) for g in (r.get("gold_aliases") or [])]
        items.append({"id": str(r.get("id")), "type": str(r.get("type")),
                      "expected": str(r.get("expected", "")),
                      "sentences": sents,
                      "question": str(r.get("question", "")),
                      "golds": golds})
    return items


def load_model():
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(MODEL_ID, local_files_only=True,
                                        trust_remote_code=False)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    try:
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_ID, dtype=torch.float32, trust_remote_code=False,
            local_files_only=True)
    except TypeError:
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_ID, torch_dtype=torch.float32, trust_remote_code=False,
            local_files_only=True)
    model.to("cpu")
    model.eval()
    return model, tok


def summarize(rows: list[dict]) -> dict:
    tot = {"n": 0, "correct": 0, "abstain": 0, "wrong": 0, "contains_gold": 0}
    for r in rows:
        tot["n"] += 1
        tot[r["verdict"]] += 1
        tot["contains_gold"] += int(r["contains_gold"])
    return tot


def pick_examples(rows: list[dict]) -> list[dict]:
    """2 correct, 2 wrong, 1 abstain where they exist (verbatim)."""
    out = []
    for want, k in (("correct", 2), ("wrong", 2), ("abstain", 1)):
        got = [r for r in rows if r["verdict"] == want][:k]
        out += [(want, r) for r in got]
    if not [r for r in rows if r["verdict"] == "abstain"]:
        extra = [r for r in rows if r["verdict"] == "wrong"][2:3]
        out += [("wrong(substitute-for-missing-abstain)", r) for r in extra]
    trimmed = [{"slot": s, "id": r["id"], "question": r["question"],
                "golds": r["golds"][:3], "answer": r["answer"],
                "verdict": r["verdict"]} for s, r in out]
    return trimmed


def cmd_smoke(_args) -> int:
    torch.manual_seed(6601)
    np.random.seed(6601)
    try:
        torch.set_num_threads(1)
    except Exception:
        pass
    t0 = time.time()
    model, tok = load_model()
    print(f"model load s={time.time()-t0:.1f}", flush=True)
    items = load_split(DATA_B)[:10]
    t1 = time.time()
    for it in items:
        greedy_answer(model, tok, build_prompt(tok, it["sentences"], it["question"]))
    dt = time.time() - t1
    print(f"smoke: 10 incontext 4hop items gen s={dt:.1f} "
          f"({dt/10:.2f}s/item)", flush=True)
    t2 = time.time()
    for it in items:
        greedy_answer(model, tok,
                      build_prompt(tok, bm25_top3(it["sentences"], it["question"], 3),
                                   it["question"]))
    dt2 = time.time() - t2
    print(f"smoke: 10 raglite 4hop items gen s={dt2:.1f} "
          f"({dt2/10:.2f}s/item)", flush=True)
    proj = (dt + dt2) / 20 * 400
    print(f"projected 400 fresh 4hop generations s={proj:.0f} "
          f"(<1800={proj < 1800})", flush=True)
    return 0


def cmd_run(args) -> int:
    torch.manual_seed(6601)
    np.random.seed(6601)
    try:
        torch.set_num_threads(1)
    except Exception:
        pass
    ART.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    out: dict = {"seconds": 0.0, "scorer": "v2+contains-gold",
                 "model": MODEL_ID, "arms": {}}

    # --- SmolLM2 on Fable-Edit-200: RE-SCORE saved exp66 answers (no re-run)
    b66 = json.loads(BENCH66.read_text(encoding="utf-8"))
    edit_items = {it["id"]: it for it in load_split(DATA_A)}
    rescore_rows: dict[str, list[dict]] = {}
    for arm66 in ("incontext", "raglite"):
        rows = []
        for r in b66["rows"]:
            it = edit_items[r["id"]]
            ans = r["arms"][arm66]["answer"]
            verdict, exact, contains = classify_v2(ans, it["golds"])
            rows.append({"id": r["id"], "type": it["type"],
                         "expected": it["expected"], "question": it["question"],
                         "golds": it["golds"], "answer": ans,
                         "verdict": verdict, "exact": bool(exact),
                         "contains_gold": bool(contains),
                         "extracted": extract_answer(ans),
                         "old66_verdict": r["arms"][arm66]["verdict"]})
        rescore_rows[arm66] = rows
        (ART / f"fable_bench125_smollm_{arm66}_fable_edit_200_rows.jsonl").write_text(
            "\n".join(json.dumps(x, ensure_ascii=False, sort_keys=True)
                       for x in rows) + "\n", encoding="utf-8")
        out["arms"][f"smollm-{arm66}"] = {
            "fable_edit_200": summarize(rows)}

    # --- SmolLM2 on fresh 4-hop: FRESH runs (never run before)
    model, tok = load_model()
    hop_items = load_split(DATA_B)
    if args.limit:
        hop_items = hop_items[:args.limit]
        print(f"LIMIT {args.limit}/200 (subset, reported honestly)", flush=True)
    fresh: dict[str, list[dict]] = {}
    for arm, use_rag in (("incontext", False), ("raglite", True)):
        rows = []
        for i, it in enumerate(hop_items):
            sents = (bm25_top3(it["sentences"], it["question"], 3) if use_rag
                     else it["sentences"])
            ans = greedy_answer(model, tok, build_prompt(tok, sents, it["question"]))
            verdict, exact, contains = classify_v2(ans, it["golds"])
            rows.append({"id": it["id"], "type": it["type"],
                         "expected": it["expected"], "question": it["question"],
                         "golds": it["golds"], "answer": ans,
                         "verdict": verdict, "exact": bool(exact),
                         "contains_gold": bool(contains),
                         "extracted": extract_answer(ans)})
            if (i + 1) % 20 == 0 or i + 1 == len(hop_items):
                print(f"  smollm-{arm} 4hop {i+1}/{len(hop_items)} "
                      f"elapsed {time.time()-t0:.0f}s", flush=True)
        fresh[arm] = rows
        (ART / f"fable_bench125_smollm_{arm}_s2fresh_4hop_rows.jsonl").write_text(
            "\n".join(json.dumps(x, ensure_ascii=False, sort_keys=True)
                       for x in rows) + "\n", encoding="utf-8")
        out["arms"][f"smollm-{arm}"]["s2fresh_4hop"] = summarize(rows)
        out["arms"][f"smollm-{arm}"]["s2fresh_4hop_examples"] = pick_examples(rows)

    # --- loop arms: READ existing JSONs, NOT re-run
    for arm, pa, pb in (("loop102", LOOP102_A, LOOP102_B),
                        ("loop113", LOOP113_A, LOOP113_B),
                        ("loop113b", LOOP113B_A, LOOP113B_B)):
        out["arms"][arm] = {}
        for tag, path in (("fable_edit_200", pa), ("s2fresh_4hop", pb)):
            rows = [json.loads(l) for l in path.read_text(
                encoding="utf-8").splitlines() if l.strip()]
            slim = [{"id": r["id"], "type": r["type"], "verdict": r["verdict"],
                     "contains_gold": bool(r["contains_gold"])} for r in rows]
            out["arms"][arm][tag] = summarize(slim)

    # --- C1 sanity: v2-correct on exp66 incontext ANSWER items vs old contains
    ans_rows = [r for r in rescore_rows["incontext"]
                if r["expected"] == "answer"]
    v2c = sum(1 for r in ans_rows if r["verdict"] == "correct")
    old_contains = sum(1 for r in b66["rows"] if r["expected"] == "answer"
                       for a in [r["arms"]["incontext"]]
                       if a["contains_gold"])
    out["C1"] = {"v2_correct_answer_items": v2c,
                 "exp66_contains_gold_answer_items": old_contains,
                 "diff": v2c - old_contains,
                 "pass_within_3": abs(v2c - old_contains) <= 3}
    out["limit"] = args.limit
    out["seconds"] = round(time.time() - t0, 1)
    (ART / "fable_bench125_summary.json").write_text(
        json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1)[:3000])
    print(f"TOTAL seconds={out['seconds']} C2_pass(<1800)={out['seconds'] < 1800}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Exp 125 same-metric bench")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()
    if args.smoke:
        return cmd_smoke(args)
    if args.run:
        return cmd_run(args)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
