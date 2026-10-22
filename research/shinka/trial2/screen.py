#!/usr/bin/env python3
"""Stage 2 (TRIAL2-PLAN-OPUS.md section 4): dedupe at $0, one Opus clustering call, Haiku screen per family.

Stage 2 cap $4.00, stop $3.60 (pricing.json); every call goes through GuardedClient. Gate G2: >= 15 distinct
families pass the screen. The planted-card calibration listed under Stage 2 in the plan runs through the Stage 3
prosecutor/judge, which is parked and unfunded, so it is NOT done here (reported, not hidden).
Rules fixed before any paid call: free dedupe = word-set Jaccard >= 0.80 on core_operation against an earlier kept
card (earlier = file order); a family's representative = the member with the longest `mechanism` (ties: file order);
a family PASSES iff Haiku says implementable AND names no known item AND says it is not a direct combination of two.

Usage: python screen.py            # $0 dedupe + dry run: prints counts and worst-case holds, sends nothing
       python screen.py --fake     # whole pipeline on a fake client, temp ledger
       python screen.py --go       # the real run (needs ANTHROPIC_API_KEY)
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ideate  # noqa: E402
from guarded import GuardedClient  # noqa: E402
from money import Guard, MoneyStop  # noqa: E402

OUT = ideate.OUT
CARDS = OUT / "stage1_cards_final_real.jsonl"
STAGE = "2"
DUP_JACCARD = 0.80
G2_MIN_FAMILIES = 15
CLUSTER_MODEL, SCREEN_MODEL = ideate.MODELS["opus"], "claude-haiku-5-5"
CLUSTER_TOKENS, SCREEN_TOKENS = 20000, 1500    # direct (non-streaming) calls: SDK refuses > ~21k max_tokens

CLUSTER_SYSTEM = (
    "You group idea cards for a small ML task into FAMILIES. Two cards are in the same family iff their core operation "
    "is the same underlying mechanism, even if worded differently or taken from a different field. Cards with a "
    "different core operation go in different families. Every card id must appear in exactly one family. "
    'Reply with ONE JSON object and nothing after it: {"families": [{"name": "<short name>", "members": ["c000", ...]}, ...]}.'
)


def screen_system() -> str:
    return (ideate.TASK + "\nKNOWN ITEMS:\n" + ideate.known_text() + "\n\n"
            "You screen ONE idea card. Answer three questions strictly. (1) implementable: can it be written as a per-line "
            "function of the 10x32 reader states (no token ids, no other lines), at most 20,000 numbers, trained only by "
            "answer-only cross-entropy? (2) known_item: does its core operation equal an item on the KNOWN list? Name the item "
            "or say none. (3) combination: is it a direct combination of two KNOWN items (true/false)? "
            'Reply with ONE JSON object and nothing after it: {"implementable": true|false, "known_item": "<item or none>", '
            '"combination": true|false, "reason": "<one sentence>"}.')


def words(s: str) -> set[str]:
    return ideate.words(s)


def dedupe(cards: list[dict]) -> tuple[list[dict], list[dict]]:
    kept, dropped = [], []
    for c in cards:
        w = words(c["core_operation"])
        twin = next((k for k in kept if len(w & k["_w"]) / max(1, len(w | k["_w"])) >= DUP_JACCARD), None)
        if twin:
            dropped.append({"id": c["id"], "duplicate_of": twin["id"]})
        else:
            kept.append({**c, "_w": w})
    return [{k: v for k, v in c.items() if k != "_w"} for c in kept], dropped


def last_json(text: str, key: str):
    dec, found, i = json.JSONDecoder(), None, text.find("{")
    while i != -1:
        try:
            obj, end = dec.raw_decode(text, i)
        except json.JSONDecodeError:
            i = text.find("{", i + 1)
            continue
        if isinstance(obj, dict) and key in obj:
            found = obj
        i = text.find("{", end)
    return found


def text_of(resp) -> str:
    return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")


def cluster_params(cards: list[dict]) -> dict:
    listing = "\n".join(f'{c["id"]}: {c["core_operation"]}' for c in cards)
    return {"model": CLUSTER_MODEL, "max_tokens": CLUSTER_TOKENS, "system": CLUSTER_SYSTEM,
            "messages": [{"role": "user", "content": listing}], "output_config": {"effort": "medium"}}


def screen_params(card: dict) -> dict:
    body = json.dumps({k: card[k] for k in ideate.FIELDS}, indent=2)
    return {"model": SCREEN_MODEL, "max_tokens": SCREEN_TOKENS, "system": screen_system(),
            "messages": [{"role": "user", "content": body}]}


def build_families(obj, cards: list[dict]) -> list[dict]:
    """Families from the model's JSON: unknown ids are ignored, a repeated id keeps its first family,
    and any card left out becomes its own family (so nothing is silently dropped)."""
    ids = {c["id"] for c in cards}
    seen, fams = set(), []
    for f in (obj or {}).get("families", []) if isinstance(obj, dict) else []:
        if not isinstance(f, dict) or not isinstance(f.get("members"), list):
            continue
        mem = [m for m in f["members"] if isinstance(m, str) and m in ids and m not in seen]
        seen.update(mem)
        if mem:
            fams.append({"name": str(f.get("name", ""))[:80], "members": mem})
    for c in cards:
        if c["id"] not in seen:
            fams.append({"name": "(unassigned) " + c["id"], "members": [c["id"]]})
    return fams


def representative(fam: dict, by_id: dict) -> dict:
    return max((by_id[m] for m in fam["members"]), key=lambda c: (len(c["mechanism"]), -int(c["id"][1:])))


def passes(v) -> bool:
    return (isinstance(v, dict) and v.get("implementable") is True and v.get("combination") is False
            and str(v.get("known_item", "")).strip().lower() in ("none", "", "n/a", "no"))


def load_cards() -> list[dict]:
    rows = [json.loads(x) for x in CARDS.read_text().splitlines() if x.strip()]
    return [{**r, "id": f"c{i:03d}"} for i, r in enumerate(rows)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--go", action="store_true")
    ap.add_argument("--fake", action="store_true")
    a = ap.parse_args()

    cards = load_cards()
    kept, dropped = dedupe(cards)
    guard = Guard(ledger=Path(tempfile.mkdtemp()) / "l.jsonl") if a.fake else Guard()
    probe = GuardedClient(None, guard)
    w_cluster, w_screen = probe.worst(cluster_params(kept)), probe.worst(screen_params(kept[0]))
    print(f"cards {len(cards)}; free dedupe drops {len(dropped)} -> {len(kept)} kept (Jaccard >= {DUP_JACCARD})")
    print(f"worst case: cluster call ${w_cluster:.4f}; one screen call ${w_screen:.4f}; "
          f"all screens if every kept card were its own family ${w_screen * len(kept):.3f}; "
          f"stage 2 cap ${guard.stage_cap(STAGE):.2f}, stop ${guard.stage_stop(STAGE):.2f}, spent+held ${guard.spent(STAGE):.4f}")
    if not (a.go or a.fake):
        print("dry run: nothing sent. Re-run with --go to launch.")
        return
    if a.fake:
        import fake_screen_client
        gc = GuardedClient(fake_screen_client.FakeClient(), guard)
    else:
        import prosecute
        gc = prosecute.make_client(guard)

    by_id = {c["id"]: c for c in kept}
    stopped, fams, results = None, [], {}
    try:
        resp = gc.create(STAGE, "s2-cluster", **cluster_params(kept))
        obj = last_json(text_of(resp), "families")
        fams = build_families(obj, kept)
        for n, fam in enumerate(fams):
            rep = representative(fam, by_id)
            r = gc.create(STAGE, f"s2-screen-{n:03d}", **screen_params(rep))
            v = last_json(text_of(r), "implementable")
            results[n] = {"rep": rep["id"], "verdict": v, "stop_reason": r.stop_reason, "passes": passes(v)}
    except MoneyStop as e:
        stopped = str(e)
        print("MONEY STOP:", e, flush=True)
    tag = "fake" if a.fake else "real"
    n_pass = sum(1 for r in results.values() if r["passes"])
    summary = {"mode": tag, "money_stop": stopped, "stage2_spent_usd": guard.spent(STAGE), "cards": len(cards),
               "deduped_away": len(dropped), "kept": len(kept), "families": len(fams),
               "screened": len(results), "unparsed_verdicts": sum(1 for r in results.values() if r["verdict"] is None),
               "families_passing": n_pass, "G2_min": G2_MIN_FAMILIES, "G2_pass": n_pass >= G2_MIN_FAMILIES and stopped is None}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"stage2_{tag}.json").write_text(json.dumps({
        "summary": summary, "dropped_duplicates": dropped,
        "families": [{**f, "rep": results.get(n, {}).get("rep"), "screen": results.get(n, {})} for n, f in enumerate(fams)]}, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
