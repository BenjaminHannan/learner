"""Step 10b: grading, back in the container after the GPU outputs are pulled.
ACT: exact tool-arg match (already computed by code in eval_moves; recomputed here from the raw text).
ASK: a Haiku grader (Message Batches) maps the question to one of the 60 persona slot ids (or 'none'); a Sonnet regrade of 60 ASKs gives Cohen's kappa.
  python -m sleep2.askonce.grade RESULTS_DIR EVAL_INPUTS.jsonl OUT_DIR [--no-api]     (--no-api: rule mapper only, for tests / dry runs)
"""
import json
import random
import re
import sys
from pathlib import Path

from .config import HAIKU, SONNET, DATA, jdump, jl_read, jload, norm
from .requests_gen import label_name
from .tools_mock import check_action, parse_reply
from .world import Persona

KAPPA_N = 60


def catalogue(persona):
    lines = []
    for s in persona.slots.values():
        if s["kind"] in ("contact", "meeting", "file"):
            opts = "; ".join(label_name(c["label"]) for c in s["candidates"])
        elif s["kind"] == "duration":
            opts = "which length in minutes"
        else:
            opts = "send now or save as draft"
        lines.append(f"{s['slot_id']} | reference: '{s['ref']}' | {s['kind']} | {opts}")
    return "\n".join(lines)


def rule_map(question, persona):
    """Cheap exact-ish mapper (reference word or candidate name/value in the question). Used for tests and as a sanity cross-check."""
    q = norm(question)
    best, score = "none", 0
    for s in persona.slots.values():
        sc = 0
        if re.search(rf"(?<![a-z0-9]){re.escape(norm(s['key_token']))}", q):
            sc += 2
        if norm(s["ref"]) in q:
            sc += 3
        for c in s["candidates"]:
            if s["kind"] in ("contact", "meeting", "file") and (norm(c["value"]) in q or (len(label_name(c["label"])) > 3 and norm(label_name(c["label"])) in q)):
                sc += 2
        if sc > score:
            best, score = s["slot_id"], sc
    return best


def grader_prompt(items, persona):
    body = "\n".join(json.dumps({"i": i, "request": it["text"], "question": it["question"]}, ensure_ascii=False) for i, it in enumerate(items))
    return ("A personal assistant was asked to do the request below but asked Ben a clarifying question instead. Decide which ONE slot (from the catalogue) "
            "the question is asking Ben to resolve. Answer 'none' if the question is about something else or is too vague to tell.\n\nSlot catalogue:\n"
            + catalogue(persona) + "\n\nReturn ONLY JSON [{\"i\": n, \"slot_id\": \"<id or none>\"}] for these items:\n" + body)


def api_map(items, persona, model, label, chunk=25, rounds=3):
    """Map each (text, question) to a slot id. A chunk whose JSON does not parse is re-requested (up to `rounds` batches); if it still fails we raise,
    because silently mapping it to 'none' would grade those ASKs as wrong."""
    from .batches import parse_json, req, run_batch
    plan = {f"{label}-{ci // chunk}": list(range(ci, min(len(items), ci + chunk))) for ci in range(0, len(items), chunk)}
    res, pending = {}, dict(plan)
    for rnd in range(rounds):
        if not pending:
            break
        reqs = [req(cid if rnd == 0 else f"{cid}-r{rnd}", model, grader_prompt([items[i] for i in idxs], persona), 6000) for cid, idxs in pending.items()]
        out, _ = run_batch(reqs, label if rnd == 0 else f"{label}-retry{rnd}")
        failed = {}
        for cid, idxs in pending.items():
            try:
                got = {int(x["i"]): x["slot_id"] for x in parse_json(out[cid if rnd == 0 else f"{cid}-r{rnd}"])}
                if not all(local in got for local in range(len(idxs))):
                    raise ValueError(f"missing {len(idxs) - len(got)} of {len(idxs)} answers")
            except Exception as e:
                print("grader parse failed", cid, "round", rnd, e, file=sys.stderr)
                failed[cid] = idxs
                continue
            for local, gi in enumerate(idxs):
                res[gi] = got[local]
        pending = failed
    if pending:
        raise RuntimeError(f"grader: {len(pending)} chunk(s) of {label} still unparseable after {rounds} rounds: {sorted(pending)}")
    return res


def cohen_kappa(a, b):
    n = len(a)
    if n == 0:
        return None
    po = sum(x == y for x, y in zip(a, b)) / n
    labs = set(a) | set(b)
    pe = sum((a.count(l) / n) * (b.count(l) / n) for l in labs)
    return 1.0 if pe == 1 else round((po - pe) / (1 - pe), 4)


def right_move(split, row, item, asked_slot):
    """The prereg's definition of 'right move' per subset."""
    act_ok = row["move"] == "ACT" and row["act_ok"]
    if split.endswith("_new"):
        return row["move"] == "ASK" and asked_slot == item["slots"][0]
    if split == "silent":
        return act_ok or (row["move"] == "ASK" and asked_slot == item["slots"][0])
    return act_ok  # knowable and fully specified: act with the exact args


def grade_all(results_dir, eval_inputs_path, out_dir, persona=None, use_api=True, seed=0):
    persona = persona or Persona.load()
    items = {r["req_id"]: r for r in jl_read(eval_inputs_path)}
    files = sorted(Path(results_dir).glob("*_*.json"))
    asks = {}
    for f in files:
        for row in jload(f)["eval"]["moves"]:
            if row["move"] == "ASK":
                asks[(row["req_id"], row.get("question", ""))] = None
    keys = sorted(asks)
    todo = [{"text": items[k[0]]["text"], "question": k[1]} for k in keys]
    agree = {}
    if use_api and todo:
        hk = api_map(todo, persona, HAIKU, "grade-haiku")
        for i, k in enumerate(keys):
            asks[k] = hk[i]
        rng = random.Random(seed)
        pick = rng.sample(range(len(keys)), min(KAPPA_N, len(keys)))
        sn = api_map([todo[i] for i in pick], persona, SONNET, "grade-sonnet-regrade")
        a, b = [hk[i] for i in pick], [sn[j] for j in range(len(pick))]
        agree = {"n": len(pick), "kappa": cohen_kappa(a, b), "raw_agreement": round(sum(x == y for x, y in zip(a, b)) / max(1, len(pick)), 3),
                 "suspect": bool((cohen_kappa(a, b) or 0) < 0.7)}
    else:
        for i, k in enumerate(keys):
            asks[k] = rule_map(k[1], persona)
        agree = {"n": 0, "kappa": None, "note": "rule mapper only (no API)"}
    graded = {}
    for f in files:
        d = jload(f)
        rows = []
        for row in d["eval"]["moves"]:
            it = items[row["req_id"]]
            asked = asks.get((row["req_id"], row.get("question", ""))) if row["move"] == "ASK" else None
            rows.append({"req_id": row["req_id"], "split": row["split"], "move": row["move"], "act_ok": row["act_ok"], "asked_slot": asked,
                         "right": bool(right_move(row["split"], row, it, asked)), "slot": it["slots"][0] if it["slots"] else None,
                         "knowable_effective": it["knowable_effective"]})
        graded[f.stem] = rows
        jdump(Path(out_dir) / "graded" / f"{f.stem}.json", rows)
    jdump(Path(out_dir) / "grader_agreement.json", agree)
    return graded, agree


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    g, ag = grade_all(a[0], a[1], a[2], use_api="--no-api" not in sys.argv)
    print(json.dumps(ag))
