#!/usr/bin/env python3
"""Experiment 211 -- FAIR-PROMPT SmolLM ARM (benchmark fairness; no agent change).

Same model, splits, decoding and scorer as bench125's in-context arm
(imported, never re-implemented), but with a fair prompt:
  - facts numbered in teaching order:  "1. ...", "2. ...", ...
  - each edit entry (taught[].edit == true) annotated "(this replaces fact N)"
    where N is the earlier fact with the same (subject, relation); if no
    earlier fact matches, "(this is a new fact)".
  - system line says newer facts win and "say I don't know if the facts
    don't say", plus one abstain example.

Plus a scorer variant whose abstain markers match whole phrases only
(no bare "not" substring rule).

Marks:
  F1: fair arm beside bench125's old in-context arm on both splits
      (fable_edit_200, s2fresh_4hop), every item, right/wrong/abstain.
  F2: bench66's old in-context answers re-scored with the whole-phrase
      detector: how many old "abstains" were answers merely containing "not".
  F3: loop wrong-answer rate (bench125 loop arms, read from JSON) beside
      fair SmolLM's.

Run ONLY after PASSMARKS.md is sealed (Mac CPU, offline):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 HF_HUB_OFFLINE=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    --with transformers python -B scripts/fable_fairsmol211.py --smoke
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    --with transformers python -B scripts/fable_fairsmol211.py --run
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

import numpy as np
import torch

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

# Same model / decoding contract as bench125's in-context arm (imported).
from fable_bench66_baselines import MODEL_ID, greedy_answer  # noqa: E402
# Same scorer as bench125's in-context arm (imported verbatim logic).
from fable_bench125_run import (  # noqa: E402
    classify_v2,
    extract_answer,
    load_model,
    load_split,
    norm,
    summarize,
)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-fairsmol211-20260922"
DATA_A = ROOT / "data" / "open" / "bench65" / "fable_edit_200.jsonl"
DATA_B = ROOT / "data" / "open" / "bench103" / "fable_edit103_s2fresh_4hop.jsonl"
BENCH66 = ROOT / "artifacts" / "fable-bench66-20260921" / "fable_bench66_results.json"
BENCH125 = ROOT / "artifacts" / "fable-bench125-20260922" / "fable_bench125_summary.json"

SEED = 6601

FAIR_SYSTEM = (
    "Answer the question with a short phrase. "
    "The facts below are numbered in the order you learned them. "
    "A fact marked (this replaces fact N) replaces that older fact: "
    "newer facts win over older ones. "
    "Say I don't know if the facts don't say. "
    "Example: Facts: 1. The keeper of Grey Archive is Marisol Vega. "
    "Question: Who keeps the Red Archive? Answer: I don't know."
)


def replacement_of(taught: list[dict], k: int) -> int | None:
    """Index (1-based) of the earlier fact entry k replaces, or None.

    Match = same normalised (subject, relation) taught earlier.
    """
    cur = taught[k]
    subj = norm(str(cur.get("subject", "")))
    rel = norm(str(cur.get("relation", "")))
    if not subj or not rel:
        return None
    for j in range(k):
        if (norm(str(taught[j].get("subject", ""))) == subj
                and norm(str(taught[j].get("relation", ""))) == rel):
            return j + 1
    return None


def fair_lines(taught: list[dict]) -> list[str]:
    """Numbered fact lines in teaching order with replace annotations."""
    lines = []
    for k, t in enumerate(taught):
        s = str(t.get("sentence_en", "")).strip()
        if not s:
            continue
        tag = ""
        if t.get("edit") is True:
            n = replacement_of(taught, k)
            tag = (" (this replaces fact %d)" % n) if n else " (this is a new fact)"
        lines.append("%d. %s%s" % (k + 1, s, tag))
    return lines


def build_fair_prompt(tok, taught: list[dict], question: str) -> str:
    body = "Facts:\n" + "".join("- %s\n" % ln for ln in fair_lines(taught))
    body += "Question: %s" % question
    msgs = [
        {"role": "system", "content": FAIR_SYSTEM},
        {"role": "user", "content": body},
    ]
    try:
        return tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    except Exception:
        return "System: %s\nUser: %s\nAssistant:" % (FAIR_SYSTEM, body)


# ---- scorer variant: abstain markers match whole phrases only ----
PHRASE_MARKERS = ("unknown", "i don't know", "i dont know")
_PHRASE_RES = [re.compile(r"\b" + re.escape(p) + r"\b") for p in PHRASE_MARKERS]


def classify_phrase(answer: str, golds: list[str]) -> tuple[str, bool, bool]:
    """bench66 classify() shape, but markers are whole-phrase regexes only.

    No bare "not" substring rule: an answer counts as abstain only if a
    whole abstain phrase occurs AND no gold is contained.
    """
    na = norm(answer)
    ngs = [norm(g) for g in list(golds) if norm(g)]
    exact = na in ngs
    contains = any(g in na for g in ngs)
    if exact:
        return "correct", True, contains
    low = (answer or "").lower().replace("\u2019", "'")
    if (not contains) and any(rx.search(low) for rx in _PHRASE_RES):
        return "abstain", False, contains
    return "wrong", False, contains


def load_taught(path: Path) -> dict[str, list[dict]]:
    """id -> taught entries (for edit annotations)."""
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            out[str(r.get("id"))] = r.get("taught") or []
    return out


def cmd_smoke(_args) -> int:
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    try:
        torch.set_num_threads(1)
    except Exception:
        pass
    t0 = time.time()
    model, tok = load_model()
    print("model load s=%.1f" % (time.time() - t0), flush=True)
    # Prompt-builder unit checks (no model needed).
    taught = [
        {"subject": "Velnoria", "relation": "mayor_of",
         "sentence_en": "The mayor of Velnoria is Zara Quinn."},
        {"subject": "Velnoria", "relation": "mayor_of",
         "sentence_en": "The mayor of Velnoria is Theo Ansel.", "edit": True},
        {"subject": "Velnoria", "relation": "keeper_of",
         "sentence_en": "The keeper of Velnoria is Noor Fadil.", "edit": True},
    ]
    assert replacement_of(taught, 1) == 1, replacement_of(taught, 1)
    assert replacement_of(taught, 2) is None
    lines = fair_lines(taught)
    assert lines[1].endswith("(this replaces fact 1)"), lines
    assert lines[2].endswith("(this is a new fact)"), lines
    p = build_fair_prompt(tok, taught, "Who is the mayor of Velnoria?")
    assert "(this replaces fact 1)" in p and "newer facts win" in p.lower()
    assert "i don't know" in p.lower()
    # Scorer-variant unit checks.
    assert classify_phrase("I do not know the answer", ["Latvia"])[0] == "wrong"
    assert classify_phrase("I don't know", ["Latvia"])[0] == "abstain"
    assert classify_phrase("Unknown", ["Latvia"])[0] == "abstain"
    assert classify_phrase("Latvia is not far", ["Latvia"]) == ("wrong", False, True)
    assert classify_phrase("It is not Paris", ["Latvia"])[0] == "wrong"
    assert classify_v2("I don't know", ["Latvia"])[0] == "abstain"
    print("unit checks OK (prompt builder + phrase scorer + v2 import)", flush=True)
    items = load_split(DATA_B)[:5]
    taught_map = load_taught(DATA_B)
    t1 = time.time()
    for it in items:
        greedy_answer(model, tok, build_fair_prompt(tok, taught_map[it["id"]], it["question"]))
    dt = time.time() - t1
    print("smoke: 5 fair 4hop items gen s=%.1f (%.2fs/item); "
          "projected 400 fresh s=%.0f (<1500=%s)"
          % (dt, dt / 5, dt / 5 * 400, (dt / 5 * 400) < 1500), flush=True)
    return 0


def cmd_run(args) -> int:
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    try:
        torch.set_num_threads(1)
    except Exception:
        pass
    ART.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    out: dict = {"seconds": 0.0, "model": MODEL_ID, "seed": SEED,
                 "fair_system": FAIR_SYSTEM, "arms": {}}

    # --- F1: fair arm, fresh runs on BOTH splits (same model/decode/scorer) ---
    model, tok = load_model()
    fair_rows: dict[str, list[dict]] = {}
    for tag, path in (("fable_edit_200", DATA_A), ("s2fresh_4hop", DATA_B)):
        items = load_split(path)
        if args.limit:
            items = items[: args.limit]
            print("LIMIT %d (%s, subset, reported honestly)" % (args.limit, tag), flush=True)
        taught_map = load_taught(path)
        rows = []
        for i, it in enumerate(items):
            ans = greedy_answer(
                model, tok, build_fair_prompt(tok, taught_map[it["id"]], it["question"]))
            verdict, exact, contains = classify_v2(ans, it["golds"])
            pv, _, _ = classify_phrase(ans, it["golds"])
            rows.append({"id": it["id"], "type": it["type"],
                         "expected": it["expected"], "question": it["question"],
                         "golds": it["golds"], "answer": ans,
                         "verdict": verdict, "exact": bool(exact),
                         "contains_gold": bool(contains),
                         "extracted": extract_answer(ans),
                         "phrase_verdict": pv,
                         "prompt": "fair-numbered-replace-cue"})
            if (i + 1) % 20 == 0 or i + 1 == len(items):
                print("  fair %s %d/%d elapsed %.0fs"
                      % (tag, i + 1, len(items), time.time() - t0), flush=True)
        fair_rows[tag] = rows
        (ART / ("fable_fairsmol211_fair_smol_%s_rows.jsonl" % tag)).write_text(
            "\n".join(json.dumps(x, ensure_ascii=False, sort_keys=True)
                       for x in rows) + "\n", encoding="utf-8")
        out["arms"]["fair-smollm"] = out["arms"].get("fair-smollm", {})
        out["arms"]["fair-smollm"][tag] = summarize(rows)

    # --- old arm beside fair (bench125 in-context, read from JSON) ---
    b125 = json.loads(BENCH125.read_text(encoding="utf-8"))
    out["arms"]["smollm-incontext-b125"] = {
        tag: b125["arms"]["smollm-incontext"][tag]
        for tag in ("fable_edit_200", "s2fresh_4hop")}

    # --- F2: old bench66 in-context answers re-scored, old vs phrase ---
    b66 = json.loads(BENCH66.read_text(encoding="utf-8"))
    f2_rows = []
    n_old_abstain = 0
    n_phrase_abstain = 0
    n_old_abstain_with_not = 0
    n_old_abstain_only_not = 0
    for r in b66["rows"]:
        ans = r["arms"]["incontext"]["answer"]
        old_v = r["arms"]["incontext"]["verdict"]
        # NOTE: bench66 rows store golds at top level ("golds" key per row).
        golds = r.get("golds", [])
        pv, _, _ = classify_phrase(ans, golds)
        low = (ans or "").lower().replace("\u2019", "'")
        has_not_sub = "not" in norm(ans)
        has_phrase = bool(any(rx.search(low) for rx in _PHRASE_RES))
        if old_v == "abstain":
            n_old_abstain += 1
            n_old_abstain_with_not += int(has_not_sub)
            n_old_abstain_only_not += int(has_not_sub and not has_phrase)
        n_phrase_abstain += int(pv == "abstain")
        f2_rows.append({"id": r["id"], "type": r["type"], "answer": ans,
                        "old66_verdict": old_v, "phrase_verdict": pv,
                        "has_not_substring": bool(has_not_sub),
                        "has_whole_phrase": bool(has_phrase)})
    (ART / "fable_fairsmol211_f2_old66_rescored_rows.jsonl").write_text(
        "\n".join(json.dumps(x, ensure_ascii=False, sort_keys=True)
                   for x in f2_rows) + "\n", encoding="utf-8")
    out["F2"] = {"n": len(f2_rows),
                 "old66_incontext_abstain": n_old_abstain,
                 "phrase_incontext_abstain": n_phrase_abstain,
                 "old_abstains_containing_not": n_old_abstain_with_not,
                 "old_abstains_only_because_of_not": n_old_abstain_only_not}

    # --- F3: loop wrong-answer rates (bench125, read) beside fair ---
    out["arms"]["loops-b125"] = {
        arm: {tag: b125["arms"][arm][tag]
              for tag in ("fable_edit_200", "s2fresh_4hop")}
        for arm in ("loop102", "loop113", "loop113b")}
    out["F3_wrong_rate"] = {}
    for tag in ("fable_edit_200", "s2fresh_4hop"):
        f = out["arms"]["fair-smollm"][tag]
        out["F3_wrong_rate"][tag] = {
            "fair_smollm_wrong_rate": f["wrong"] / f["n"],
            **{"%s_wrong_rate" % arm: (b125["arms"][arm][tag]["wrong"]
                                       / b125["arms"][arm][tag]["n"])
               for arm in ("loop102", "loop113", "loop113b")}}

    out["limit"] = args.limit
    out["seconds"] = round(time.time() - t0, 1)
    (ART / "fable_fairsmol211_summary.json").write_text(
        json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "arms"}, indent=1)[:2000])
    print("FAIR: " + json.dumps(out["arms"]["fair-smollm"]))
    print("TOTAL seconds=%.1f (<1500=%s)"
          % (out["seconds"], out["seconds"] < 1500))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Exp 211 fair-prompt SmolLM")
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
