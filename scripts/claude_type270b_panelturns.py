#!/usr/bin/env python3
"""Exp 270b POST-SEAL panel turns builder (new file, disclosed D3).

First opening of the blind panel happens HERE (after the 270b seal).
Strict loader mirroring the writer's make_panel.py self-checks:
  100 lines; ids u270-001..u270-100 in family-block order
  (casual 40 / casual_q 15 / lower_trap 15 / clean 30);
  keys {id,family,turn,gold,clear,notes}; TEACH keys
  {act,subject,relation,relation_aliases,value}; ASK keys
  {act,subject,relation,chain,relation_aliases,chain_aliases};
  casual-family turns all lowercase; clean turns capitalised;
  casual/clean gold non-empty TEACH; casual_q gold non-empty ASK;
  traps gold [] with a trap word; panel sha verified against the panel's
  own SEAL.sha256.txt (checked OK from the repo root).
Any deviation prints SCHEMA-MISMATCH and exits 3 (VOID, never scored).
A sha mismatch exits 4.

Converts rows to dev-jsonl shape (gold relation -> [name], aliases ->
[flat list]) so the sealed qbuild/devscore path runs unchanged, and writes
the BensPC turns file (raw + normalised per item) + norm manifest with the
sealed normaliser (per-item seen-names from setup; panel items have none).
Asserts clean passthrough (exit 2 otherwise).

Usage: python -B scripts/claude_type270b_panelturns.py --panel P --seal S --rows ROWS.jsonl --turns TURNS.json --normmanifest NORM.json
"""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_type270b_normalise as N  # noqa: E402 (sealed, read-only use)

FAMS = {"casual": 40, "casual_q": 15, "lower_trap": 15, "clean": 30}
KEYS = {"id", "family", "turn", "gold", "clear", "notes"}
TEACH_KEYS = {"act", "subject", "relation", "relation_aliases", "value"}
ASK_KEYS = {"act", "subject", "relation", "chain", "relation_aliases",
            "chain_aliases"}
TRAP_WORDS = ["april", "rose", "will", "bill", "june", "hunter", "mark",
              "frank", "ruby", "iris", "grace", "chase", "may", "reed",
              "pearl", "hope"]


def mismatch(msg):
    print(f"SCHEMA-MISMATCH: {msg}", flush=True)
    sys.exit(3)


def expect_sha(seal_path):
    for ln in Path(seal_path).read_text(encoding="utf-8").splitlines():
        parts = ln.strip().split()
        if len(parts) == 2 and parts[1].endswith("panel.jsonl"):
            return parts[0]
    print(f"no panel.jsonl line in seal {seal_path}", flush=True)
    sys.exit(4)


def load_panel(panel_path, seal_path):
    raw = Path(panel_path).read_bytes()
    want = expect_sha(seal_path)
    if hashlib.sha256(raw).hexdigest() != want:
        print("PANEL-SHA-MISMATCH", flush=True)
        sys.exit(4)
    items = [json.loads(x) for x in raw.decode("utf-8").splitlines()
             if x.strip()]
    if len(items) != 100:
        mismatch(f"panel has {len(items)} items, want 100")
    want_ids = [f"u270-{i:03d}" for i in range(1, 101)]
    if [it.get("id") for it in items] != want_ids:
        mismatch("ids are not u270-001..u270-100 in order")
    fams = {}
    for it in items:
        if not isinstance(it, dict) or set(it) != KEYS:
            mismatch(f"keys {sorted(it) if isinstance(it, dict) else it}")
        fams[it["family"]] = fams.get(it["family"], 0) + 1
        if not isinstance(it["turn"], str) or not it["turn"]:
            mismatch(f"{it['id']} bad turn")
        if not isinstance(it["clear"], bool):
            mismatch(f"{it['id']} clear not bool")
        if not isinstance(it["notes"], str) or not it["notes"]:
            mismatch(f"{it['id']} notes not str")
        if not isinstance(it["gold"], list):
            mismatch(f"{it['id']} gold not list")
        for g in it["gold"]:
            if g.get("act") == "TEACH":
                if set(g) != TEACH_KEYS:
                    mismatch(f"{it['id']} TEACH keys {sorted(g)}")
            elif g.get("act") == "ASK":
                if set(g) != ASK_KEYS:
                    mismatch(f"{it['id']} ASK keys {sorted(g)}")
            else:
                mismatch(f"{it['id']} bad act {g}")
    if fams != FAMS:
        mismatch(f"family counts {fams} != {FAMS}")
    for n, it in enumerate(items):
        fam, t = it["family"], it["turn"]
        blk = "casual" if n < 40 else ("casual_q" if n < 55
                                       else ("lower_trap" if n < 70
                                             else "clean"))
        if fam != blk or it["id"] != want_ids[n]:
            mismatch(f"block order at line {n + 1}")
        if fam in ("casual", "casual_q", "lower_trap"):
            if t != t.lower():
                mismatch(f"{it['id']} not lowercase")
        else:
            if t == t.lower():
                mismatch(f"{it['id']} clean has no capitals")
        if fam in ("casual", "clean"):
            if not it["gold"] or any(g["act"] != "TEACH"
                                     for g in it["gold"]):
                mismatch(f"{it['id']} {fam} gold not TEACH")
        elif fam == "casual_q":
            if not it["gold"] or any(g["act"] != "ASK"
                                     for g in it["gold"]):
                mismatch(f"{it['id']} casual_q gold not ASK")
        else:
            if it["gold"] != []:
                mismatch(f"{it['id']} trap gold not empty")
            if not any(w in t.lower() for w in TRAP_WORDS):
                mismatch(f"{it['id']} trap w/o trap word")
    print("SCHEMA OK (100 items u270-001..100, 40/15/15/30)", flush=True)
    return items


def conv_gold(g):
    if g["act"] == "TEACH":
        return {"act": "TEACH", "subject": str(g["subject"]),
                "relation": [str(g["relation"])],
                "aliases": [[str(x) for x in g["relation_aliases"]]],
                "value": str(g["value"])}
    return {"act": "ASK", "subject": str(g["subject"]),
            "relation": [str(g["relation"])],
            "aliases": [[str(x) for x in g["relation_aliases"]]]}


def main(argv):
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", required=True)
    ap.add_argument("--seal", required=True)
    ap.add_argument("--rows", required=True)
    ap.add_argument("--turns", required=True)
    ap.add_argument("--normmanifest", required=True)
    a = ap.parse_args(argv[1:])
    items = load_panel(a.panel, a.seal)
    rows, turns, manif = [], [], {}
    for it in items:
        fixed, reason, ms = N.normalise270b(it["turn"], {})
        rows.append({"id": it["id"], "family": it["family"], "setup": [],
                     "turn": it["turn"],
                     "gold": [conv_gold(g) for g in it["gold"]],
                     "note": it["notes"]})
        turns.append({"id": it["id"] + "-raw", "turn": it["turn"]})
        turns.append({"id": it["id"] + "-norm", "turn": fixed})
        manif[it["id"]] = {"raw": it["turn"], "fixed": fixed,
                           "reason": reason, "norm_ms": ms,
                           "setup_seen": {}, "fired": fixed != it["turn"]}
        if it["family"] == "clean" and fixed != it["turn"]:
            print(f"CLEAN-FIRED (forbidden): {it['id']}", flush=True)
            sys.exit(2)
    Path(a.rows).write_text("".join(json.dumps(r) + "\n" for r in rows),
                            encoding="utf-8")
    Path(a.turns).write_text(json.dumps(turns, indent=1), encoding="utf-8")
    Path(a.normmanifest).write_text(json.dumps(manif, indent=1),
                                    encoding="utf-8")
    fired = sum(1 for v in manif.values() if v["fired"])
    print(f"100 items -> 200 turns, fired {fired}")
    for fam in ("casual", "casual_q", "lower_trap", "clean"):
        ff = sum(1 for r in rows if r["family"] == fam
                 and manif[r["id"]]["fired"])
        nn = sum(1 for r in rows if r["family"] == fam)
        print(f"  {fam}: fired {ff}/{nn}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
