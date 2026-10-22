#!/usr/bin/env python3
"""Stage 2 clustering re-run (coordinator ruling 2026-10-22): the single 175-card Opus call was refused.

Fixed before running: chunks of 44 cards in id order (44,44,44,43), each clustered by claude-opus-5-5 with the SAME
system prompt as screen.py; a chunk whose reply is a refusal is re-sent ONCE with claude-sonnet-5-5 (never Opus again).
Then ONE merge call (same model rule) groups the chunk-families that are the same mechanism. No card is dropped: unparsed or
missing ids become their own family and are counted. Each card was already screened alone (stage2_real.json); a final family's
representative = member with the longest `mechanism`, and the family PASSES iff that representative's existing screen verdict
passes (same prompt and card as a fresh screen would use). G2 = >= 15 passing families, valid only if every call parsed.
Cost is booked to Stage 2 through GuardedClient (cap $4.00, stop $3.60; $0.213 already spent).
Usage: python recluster.py --fake | python recluster.py --go
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import screen  # noqa: E402
import ideate  # noqa: E402
from guarded import GuardedClient  # noqa: E402
from money import Guard, MoneyStop  # noqa: E402

CHUNK = 44
SONNET = ideate.MODELS["sonnet"]
MERGE_SYSTEM = (
    "You merge FAMILIES of idea cards for a small ML task. Each line is a family id and one card's core operation. "
    "Families that share the same underlying core mechanism (even if worded differently or taken from different fields) must be "
    "merged into one group; families with a different core operation stay apart. Every family id must appear in exactly one "
    'group. Reply with ONE JSON object and nothing after it: {"groups": [["f000", "f007"], ["f001"], ...]}.')


def call(gc, tag, params):
    """Opus first; on a refusal one re-send with Sonnet. Returns (response, model_used, refused_first)."""
    r = gc.create("2", tag, **params)
    if r.stop_reason != "refusal":
        return r, params["model"], False
    r2 = gc.create("2", tag + "-sonnet", **{**params, "model": SONNET})
    return r2, SONNET, True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--go", action="store_true")
    ap.add_argument("--fake", action="store_true")
    a = ap.parse_args()
    if not (a.go or a.fake):
        print("pass --fake or --go")
        return
    cards = screen.load_cards()
    by_id = {c["id"]: c for c in cards}
    prev = json.loads((screen.OUT / "stage2_real.json").read_text())
    verdict = {f["rep"]: f["screen"].get("verdict") for f in prev["families"]}
    assert set(verdict) == set(by_id), "every card must have its own screen verdict"
    guard = Guard(ledger=Path(tempfile.mkdtemp()) / "l.jsonl") if a.fake else Guard()
    if a.fake:
        import fake_screen_client
        gc = GuardedClient(fake_screen_client.FakeClient(), guard)
    else:
        import prosecute
        gc = prosecute.make_client(guard)

    log, stopped, chunk_fams, ok = [], None, [], True
    try:
        for n in range(0, len(cards), CHUNK):
            part = cards[n:n + CHUNK]
            r, model, refused = call(gc, f"s2-recluster-{n // CHUNK}", screen.cluster_params(part))
            obj = screen.last_json(screen.text_of(r), "families")
            fams = screen.build_families(obj, part)
            un = sum(1 for f in fams if f["name"].startswith("(unassigned)"))
            ok &= obj is not None and r.stop_reason != "max_tokens" and un == 0
            log.append({"chunk": n // CHUNK, "cards": len(part), "model": model, "refused_by_opus": refused,
                        "stop_reason": r.stop_reason, "parsed": obj is not None, "unassigned": un, "families": len(fams)})
            chunk_fams += fams
        lines = [f'f{i:03d}: {by_id[screen.representative(f, by_id)["id"]]["core_operation"]}' for i, f in enumerate(chunk_fams)]
        mp = {"model": ideate.MODELS["opus"], "max_tokens": screen.CLUSTER_TOKENS, "system": MERGE_SYSTEM,
              "messages": [{"role": "user", "content": "\n".join(lines)}], "output_config": {"effort": "medium"}}
        r, model, refused = call(gc, "s2-merge", mp)
        obj = screen.last_json(screen.text_of(r), "groups")
    except MoneyStop as e:
        stopped, obj, ok = str(e), None, False
        print("MONEY STOP:", e, flush=True)
    # union the merge groups (unknown/duplicate ids ignored; leftovers stay alone)
    groups, seen = [], set()
    if isinstance(obj, dict) and isinstance(obj.get("groups"), list):
        for g in obj["groups"]:
            if isinstance(g, list):
                ids = [x for x in g if isinstance(x, str) and x.startswith("f") and x[1:].isdigit()
                       and int(x[1:]) < len(chunk_fams) and x not in seen]
                seen.update(ids)
                if ids:
                    groups.append(ids)
    merge_ok = obj is not None and r.stop_reason != "max_tokens" if not stopped else False
    left = [f"f{i:03d}" for i in range(len(chunk_fams)) if f"f{i:03d}" not in seen]
    groups += [[x] for x in left]
    merge_ok = merge_ok and not left
    final = []
    for g in groups:
        members = [m for fid in g for m in chunk_fams[int(fid[1:])]["members"]]
        rep = screen.representative({"members": members}, by_id)
        final.append({"members": members, "rep": rep["id"], "passes": screen.passes(verdict[rep["id"]]),
                      "verdict": verdict[rep["id"]]})
    n_pass = sum(f["passes"] for f in final)
    covered = sorted(m for f in final for m in f["members"]) == sorted(by_id)
    summary = {"mode": "fake" if a.fake else "real", "money_stop": stopped, "stage2_spent_usd": guard.spent("2"),
               "chunks": log, "merge": {"model": model if not stopped else None, "stop_reason": None if stopped else r.stop_reason,
                                        "parsed": obj is not None, "left_unmerged": len(left), "refused_by_opus": refused if not stopped else None},
               "chunk_families": len(chunk_fams), "final_families": len(final), "families_passing": n_pass,
               "all_cards_covered_once": covered, "G2_min": screen.G2_MIN_FAMILIES,
               "G2_pass": bool(n_pass >= screen.G2_MIN_FAMILIES and ok and merge_ok and covered and stopped is None)}
    tag = "fake" if a.fake else "real"
    (screen.OUT / f"stage2_recluster_{tag}.json").write_text(json.dumps({"summary": summary, "families": final}, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
