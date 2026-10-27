#!/usr/bin/env python3
"""Experiment 210 -- registered run: TRUE reversal split, two arms.

Arms:
  loop138i: one FRESH Loop138iDaemon per item (bench132 driver shape);
    teach the ONE taught sentence verbatim, then ask the question.
    Records teach reply (ACCEPTED/REJECTED), stored FACT triples from
    events.jsonl (must be taught-only: no inverse fact may be stored),
    and scorer-v2 verdict (right/wrong/abstain, none dropped).
  smollm-incontext: bench125 arm (build_prompt + greedy_answer from
    scripts/fable_bench66_baselines.py) with the item's taught sentence
    in context; scorer v2.

The plain transformer baseline (artifacts/fable-baseline-transformer-
v2-20260920) cannot run on this split: it is a synthetic token-story
lookup model with its own closed vocab, not an English QA model; see doc.

Run ONLY after PASSMARKS.md is sealed (Mac CPU, offline):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 HF_HUB_OFFLINE=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    --with transformers python -B scripts/fable_reversal210_run.py --run
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import shutil
import string
import sys
import time
from pathlib import Path

import numpy as np
import torch

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from fable_loop138i_agent import (  # noqa: E402
    DEFAULT_CONFIG138I, Loop138iDaemon)
from fable_bench66_baselines import (  # noqa: E402
    build_prompt, greedy_answer)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-reversal210-20260922"
DATA = ROOT / "data" / "open" / "reversal210" / "fable_reversal210.jsonl"

DUP_ACK = "I already have that."

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
        return "right", True, True
    contains = any(g in norm(reply) for g in ngs)
    low = (reply or "").lower()
    if any(rx.search(low) for rx in _ABSTAIN_RES):
        return "abstain", False, bool(contains)
    return "wrong", False, bool(contains)


def teach_accepted(reply: str) -> bool:
    r = (reply or "").strip()
    return r.startswith("Saved:") or r == DUP_ACK


def stored_triples(ddir: Path) -> list[list[str]]:
    """(subject, relation, object, source) FACTs from events.jsonl."""
    ev = ddir / "notebook" / "events.jsonl"
    if not ev.exists():
        return []
    names: dict[str, str] = {}
    facts: list[list[str]] = []
    for line in ev.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            d = json.loads(line)
        except Exception:
            continue
        if d.get("kind") == "ENTITY":
            names[str(d.get("entity_id"))] = str(d.get("name", ""))
        elif d.get("kind") == "FACT":
            val = d.get("value")
            obj = ""
            if isinstance(val, dict):
                obj = str(val.get("entity_id") or val.get("entity")
                          or val.get("value") or val.get("name") or "")
                if obj in names:
                    obj = names[obj]
            else:
                obj = str(val or "")
            facts.append([names.get(str(d.get("subject")), "?"),
                          str(d.get("relation", "")),
                          obj if obj not in names else names[obj],
                          str(d.get("source", ""))])
    return facts


def run_loop_item(item: dict, workroot: Path) -> dict:
    ddir = workroot / "loop138i" / item["id"]
    if ddir.exists():
        shutil.rmtree(ddir)
    ddir.mkdir(parents=True)
    daemon = Loop138iDaemon(str(ddir),
                            cfg=dict(copy.deepcopy(DEFAULT_CONFIG138I)))
    teach_replies: list[str] = []
    n_reject = 0
    n = 0
    for t in item["taught"]:
        n += 1
        name = f"t{n:03d}.txt"
        (ddir / "inbox" / name).write_text(
            str(t["sentence_en"]) + "\n", encoding="utf-8")
        daemon.process_file(ddir / "inbox" / name)
        reply = (ddir / "outbox" / name).read_text(
            encoding="utf-8").strip()
        teach_replies.append(reply)
        n_reject += 0 if teach_accepted(reply) else 1
    n += 1
    qname = f"t{n:03d}.txt"
    (ddir / "inbox" / qname).write_text(str(item["question"]) + "\n",
                                        encoding="utf-8")
    daemon.process_file(ddir / "inbox" / qname)
    reply = (ddir / "outbox" / qname).read_text(encoding="utf-8").strip()
    golds = [str(g) for g in list(item.get("gold", []))
             + list(item.get("gold_aliases", []))]
    verdict, exact, contains = classify_v2(reply, golds)
    triples = stored_triples(ddir)
    # inverse check: a stored FACT with subject/object swapped vs taught
    taught = item["taught"][0]
    inv = [t for t in triples
           if norm(t[0]) == norm(str(taught["object"]))
           and norm(t[2]) == norm(str(taught["subject"]))]
    return {"id": item["id"], "type": str(item.get("type", "?")),
            "taught_dir": str(item.get("taught_dir", "?")),
            "asked": str(item.get("asked", "?")),
            "verdict": verdict, "exact": bool(exact),
            "contains_gold": bool(contains),
            "extracted": extract_answer(reply),
            "n_teach": len(teach_replies), "n_teach_reject": n_reject,
            "teach_replies": teach_replies,
            "stored_triples": triples,
            "n_inverse_stored": len(inv),
            "reply": reply}


def load_model():
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from fable_bench66_baselines import MODEL_ID
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
    tot: dict[str, dict] = {}
    for r in rows:
        cell = tot.setdefault(r["type"], {"n": 0, "right": 0,
                                          "abstain": 0, "wrong": 0,
                                          "contains_gold": 0})
        cell["n"] += 1
        cell[r["verdict"]] += 1
        cell["contains_gold"] += int(r["contains_gold"])
    return tot


def cmd_run(_args) -> int:
    torch.manual_seed(210)
    np.random.seed(210)
    try:
        torch.set_num_threads(1)
    except Exception:
        pass
    ART.mkdir(parents=True, exist_ok=True)
    (ART / "loop138i-config.json").write_text(
        json.dumps(copy.deepcopy(DEFAULT_CONFIG138I), indent=1),
        encoding="utf-8")
    workroot = ART / "scratch210"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    t0 = time.time()
    items = [json.loads(l) for l in DATA.read_text(
        encoding="utf-8").splitlines() if l.strip()]
    out: dict = {"seconds": 0.0, "scorer": "v2-right/wrong/abstain",
                 "n": len(items), "arms": {}}
    # --- loop138i arm
    loop_rows = [run_loop_item(it, workroot) for it in items]
    (ART / "fable_reversal210_loop138i_rows.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                   for r in loop_rows) + "\n", encoding="utf-8")
    out["arms"]["loop138i"] = {
        "table": summarize(loop_rows),
        "teach_rejects": sum(r["n_teach_reject"] for r in loop_rows),
        "items_with_inverse_stored": sum(
            1 for r in loop_rows if r["n_inverse_stored"]),
    }
    # --- smollm in-context arm
    model, tok = load_model()
    sm_rows = []
    for it in items:
        sents = [str(t["sentence_en"]) for t in it["taught"]]
        ans = greedy_answer(model, tok,
                            build_prompt(tok, sents, it["question"]))
        golds = [str(g) for g in list(it.get("gold", []))
                 + list(it.get("gold_aliases", []))]
        verdict, exact, contains = classify_v2(ans, golds)
        sm_rows.append({"id": it["id"], "type": str(it.get("type", "?")),
                        "taught_dir": str(it.get("taught_dir", "?")),
                        "asked": str(it.get("asked", "?")),
                        "question": it["question"], "golds": golds,
                        "answer": ans, "verdict": verdict,
                        "exact": bool(exact),
                        "contains_gold": bool(contains),
                        "extracted": extract_answer(ans)})
    (ART / "fable_reversal210_smollm_incontext_rows.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                   for r in sm_rows) + "\n", encoding="utf-8")
    out["arms"]["smollm-incontext"] = {"table": summarize(sm_rows)}
    # --- coverage: every item reported for every arm
    for arm_rows, tag in ((loop_rows, "loop138i"),
                           (sm_rows, "smollm-incontext")):
        ids = sorted(r["id"] for r in arm_rows)
        want = sorted(it["id"] for it in items)
        out["arms"][tag]["coverage_all_reported"] = (ids == want)
    out["seconds"] = round(time.time() - t0, 1)
    (ART / "fable_reversal210_summary.json").write_text(
        json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out["arms"], indent=1)[:2500])
    print(f"TOTAL seconds={out['seconds']}")
    shutil.rmtree(workroot, ignore_errors=True)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Exp 210 registered run")
    ap.add_argument("--run", action="store_true")
    args = ap.parse_args()
    if args.run:
        return cmd_run(args)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
