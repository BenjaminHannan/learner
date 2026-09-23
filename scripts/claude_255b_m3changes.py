#!/usr/bin/env python3
"""Exp 255b M3: changes file, 255b panel transcripts vs 138m panel transcripts.

Reads two transcript .jsonl files written by scripts/claude_convpanel239_run.py
(rows: id, turn, user, intent, expect, reply, error, triples) and writes
  <out>.jsonl  one row per CHANGED turn: id, turn, user, reply_138m,
               reply_255b, templates (claude_fix255b_text ids that explain the
               change, [] if unexplained), explained, triples_same
  <out>.md     the same as a readable table, plus counts
Also counts store changes (triples differ after any turn) over ALL turns.
Does NOT grade; grading is the director's (M3 bars).

usage: claude_255b_m3changes.py <138m.jsonl> <255b.jsonl> <out-without-ext>
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_fix255b_text as T  # noqa: E402


def load(p):
    return {(r["id"], r["turn"]): r
            for r in (json.loads(x) for x in open(p, encoding="utf-8")
                      if x.strip())}


def explain(old, new):
    if not isinstance(old, str) or not isinstance(new, str):
        return []
    lines, tids = [], []
    for line in old.split("\n"):
        n, t = T.rewrite255b(line)
        lines.append(n)
        if t:
            tids.append(t)
    if "\n".join(lines) == new and tids:
        return tids
    # the daemon joins a turn's reply lines with one space
    nn, t = T.rewrite255b(old)
    return [t] if t and nn == new else []


def main(argv) -> int:
    base, new, out = load(argv[0]), load(argv[1]), Path(argv[2])
    keys = sorted(set(base) | set(new), key=lambda k: (k[0], k[1]))
    changes, store_changes, missing = [], [], []
    for k in keys:
        b, n = base.get(k), new.get(k)
        if b is None or n is None:
            missing.append(list(k))
            continue
        same_trip = b.get("triples") == n.get("triples")
        if not same_trip:
            store_changes.append({"id": k[0], "turn": k[1],
                                  "triples_138m": b.get("triples"),
                                  "triples_255b": n.get("triples")})
        if b.get("reply") != n.get("reply") or b.get("error") != n.get("error"):
            tids = explain(b.get("reply"), n.get("reply"))
            changes.append({"id": k[0], "turn": k[1], "user": n.get("user"),
                            "intent": n.get("intent"),
                            "reply_138m": b.get("reply"),
                            "reply_255b": n.get("reply"),
                            "templates": tids, "explained": bool(tids),
                            "triples_same": same_trip})
    with open(str(out) + ".jsonl", "w", encoding="utf-8") as fh:
        for c in changes:
            fh.write(json.dumps(c, ensure_ascii=False) + "\n")
    n_unexpl = sum(not c["explained"] for c in changes)
    md = ["# Exp 255b M3 -- changed turns, 239 panel, 138m vs 255b", "",
          f"Turns compared: {len(keys) - len(missing)}. Changed turns: "
          f"{len(changes)}. Unexplained by a 255b template: {n_unexpl}. "
          f"Turns with a store change: {len(store_changes)}. Missing turns: "
          f"{len(missing)}.", "",
          "Ungraded. The director grades these rows (M3 bars).", "",
          "| # | conv | turn | user | 138m reply | 255b reply | template |",
          "|---|---|---|---|---|---|---|"]
    esc = lambda s: str(s).replace("|", "\\|").replace("\n", " / ")  # noqa
    for i, c in enumerate(changes, 1):
        md.append(f"| {i} | {c['id']} | {c['turn'] + 1} | {esc(c['user'])} | "
                  f"{esc(c['reply_138m'])} | {esc(c['reply_255b'])} | "
                  f"{', '.join(c['templates']) or 'UNEXPLAINED'} |")
    if store_changes:
        md += ["", "## Store changes", ""]
        md += [f"- {s['id']} turn {s['turn'] + 1}: {s['triples_138m']} -> "
               f"{s['triples_255b']}" for s in store_changes]
    Path(str(out) + ".md").write_text("\n".join(md) + "\n", encoding="utf-8")
    summ = {"turns_compared": len(keys) - len(missing),
            "changed_turns": len(changes), "unexplained": n_unexpl,
            "store_changes": len(store_changes), "missing": missing}
    Path(str(out) + "-summary.json").write_text(json.dumps(summ, indent=1))
    print(json.dumps(summ))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
