#!/usr/bin/env python3
"""Exp 255 M2 checker: 255 suite rows vs 138m base rows, field by field.

For every row (matched by id; sessions152 by session#turn) and every field:
  - "seconds" is ignored (timing);
  - a text field (str, or list of str) that differs must equal the base
    text with every line passed through claude_fix255_text.rewrite255
    (a "reply-only move", tagged with the template ids that fired);
  - any other difference (verdict, stored, statuses, fact_writes, ...) is
    an UNEXPLAINED change and fails the mark.
The move list is (suite, row id); with --pred it must equal the sealed
predicted list exactly.

usage: claude_255_m2check.py <base_rows_dir> <new_rows_dir> <out.json>
                             [--pred predicted_moves255.json]
       (--write-pred <file> writes the observed list as a prediction file)
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_fix255_text as T  # noqa: E402

FILES = {
    "rt136": ("redteam136-rows.json", "rt136-rows.json"),
    "rt143": ("redteam143-rows.json", "rt143-rows.json"),
    "sessions152": ("sessions152-rows.json", "sessions152-rows.json"),
    "bench-bench132_4hop": ("bench-bench132_4hop-rows.jsonl",) * 2,
    "bench-edit200": ("bench-edit200-rows.jsonl",) * 2,
    "bench-new_121_4hop": ("bench-new_121_4hop-rows.jsonl",) * 2,
    "bench-old_s2fresh_4hop": ("bench-old_s2fresh_4hop-rows.jsonl",) * 2,
}
IGNORE = {"seconds"}


def load(p: Path):
    t = p.read_text(encoding="utf-8").strip()
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        return [json.loads(x) for x in t.splitlines() if x.strip()]


def rows_by_id(suite: str, d) -> dict:
    if suite == "sessions152":
        return {f"{s}#{r['n']}": r for s, rs in d.items() for r in rs}
    if isinstance(d, dict) and "rows" in d:
        d = d["rows"]
    return {r["id"]: r for r in d}


def rw_text(s: str):
    out, tids = [], []
    for line in s.split("\n"):
        n, t = T.rewrite255(line)
        out.append(n)
        if t:
            tids.append(t)
    return "\n".join(out), tids


def row_lines(row) -> dict:
    """old line -> (new line, tid) for every template line in the row's
    string fields (a field such as rt143 "reasons" quotes the reply)."""
    m = {}

    def walk(v):
        if isinstance(v, str):
            for line in v.split("\n"):
                n, t = T.rewrite255(line)
                if t:
                    m[line] = (n, t)
        elif isinstance(v, list):
            for x in v:
                walk(x)
    for v in row.values():
        walk(v)
    return m


def text_move(b, n, lines=None):  # noqa: C901
    """(ok, tids) if n is exactly the rewrite of b: each line rewritten,
    or (for a field that quotes a reply) each quoted template line
    replaced by its rewrite."""
    if isinstance(b, str) and isinstance(n, str):
        nn, tids = rw_text(b)
        if nn == n and tids:
            return True, tids
        if lines:
            q, tids = b, []
            for old, (new, t) in sorted(lines.items(),
                                        key=lambda kv: -len(kv[0])):
                if old in q:
                    q = q.replace(old, new)
                    tids.append(t)
            # harness text fields ("why") are cut at a fixed width, so a
            # longer rewrite may be cut earlier than the base was
            ok = bool(tids) and (q == n or (len(n) >= 60 and len(n) < len(q)
                                            and q.startswith(n)))
            if ok:
                return True, tids
            # the base quote itself was cut: base = P + (start of an old
            # line); the new text must be P + the new line, cut the same way
            for old, (new, t) in lines.items():
                for cut in range(len(old), 19, -1):
                    if b.endswith(old[:cut]):
                        pre = b[:len(b) - cut]
                        full = pre + new
                        if n == full or (len(n) >= 60 and full.startswith(n)):
                            return True, [t]
                        break
        return False, []
    if (isinstance(b, list) and isinstance(n, list) and len(b) == len(n)
            and all(isinstance(x, str) for x in b + n)):
        tids = []
        for x, y in zip(b, n):
            if x == y:
                continue
            ok, t = text_move(x, y, lines)
            if not ok:
                return False, []
            tids += t
        return True, tids
    return False, []


def nogate(argv) -> int:
    """--nogate <138m rt143nogate-m.json> <255 json> <out.json>: same
    field-by-field rule on the verifier-method rt143 rows (no verdict
    field there; triples must be identical)."""
    b = {r["id"]: r for r in load(Path(argv[0]))}
    n = {r["id"]: r for r in load(Path(argv[1]))}
    moves, bad = [], []
    if set(b) != set(n):
        bad.append({"problem": "row ids differ"})
    for rid in sorted(set(b) & set(n)):
        tids = []
        for k in sorted(set(b[rid]) | set(n[rid])):
            if k in IGNORE or b[rid].get(k) == n[rid].get(k):
                continue
            ok, t = text_move(b[rid].get(k), n[rid].get(k),
                              row_lines(b[rid]))
            if ok and t:
                tids += t
            else:
                bad.append({"id": rid, "field": k, "base": b[rid].get(k),
                            "new": n[rid].get(k)})
        if tids:
            moves.append({"id": rid, "templates": sorted(set(tids))})
    Path(argv[2]).write_text(json.dumps(
        {"rows": len(b), "n_moves": len(moves), "n_unexplained": len(bad),
         "moves": moves, "unexplained": bad}, indent=1, ensure_ascii=False))
    print(f"rt143nogate: rows={len(b)} reply-only moves={len(moves)} "
          f"unexplained={len(bad)}")
    return 0 if not bad else 1


def main(argv) -> int:
    if argv and argv[0] == "--nogate":
        return nogate(argv[1:])
    base_dir, new_dir, out = Path(argv[0]), Path(argv[1]), Path(argv[2])
    pred = wpred = None
    if "--pred" in argv:
        pred = json.loads(Path(argv[argv.index("--pred") + 1]).read_text())
    if "--write-pred" in argv:
        wpred = Path(argv[argv.index("--write-pred") + 1])
    moves, bad, counts = [], [], {}
    for suite, (bf, nf) in FILES.items():
        b = rows_by_id(suite, load(base_dir / bf))
        n = rows_by_id(suite, load(new_dir / nf))
        if set(b) != set(n):
            bad.append({"suite": suite, "problem": "row ids differ",
                        "only_base": sorted(set(b) - set(n))[:20],
                        "only_new": sorted(set(n) - set(b))[:20]})
        nrows = 0
        for rid in sorted(set(b) & set(n)):
            br, nr = b[rid], n[rid]
            nrows += 1
            tids, fields = [], []
            for k in sorted(set(br) | set(nr)):
                if k in IGNORE or br.get(k) == nr.get(k):
                    continue
                ok, t = text_move(br.get(k), nr.get(k), row_lines(br))
                if ok and t:
                    tids += t
                    fields.append(k)
                else:
                    bad.append({"suite": suite, "id": rid, "field": k,
                                "base": br.get(k), "new": nr.get(k)})
            if fields:
                moves.append({"suite": suite, "id": rid, "fields": fields,
                              "templates": sorted(set(tids))})
        counts[suite] = {"rows": nrows,
                         "moves": sum(m["suite"] == suite for m in moves)}
    keys = sorted(f"{m['suite']}/{m['id']}" for m in moves)
    res = {"counts": counts, "n_moves": len(moves), "n_unexplained": len(bad),
           "unexplained": bad, "moves": moves}
    if pred is not None:
        pk = sorted(pred["moves"])
        res["missing_predicted"] = sorted(set(pk) - set(keys))
        res["unpredicted"] = sorted(set(keys) - set(pk))
        res["matches_prediction"] = (keys == pk)
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False))
    if wpred is not None:
        wpred.write_text(json.dumps({"moves": keys}, indent=1))
    for s, c in counts.items():
        print(f"{s}: rows={c['rows']} reply-only moves={c['moves']}")
    print(f"moves={len(moves)} unexplained={len(bad)}"
          + (f" matches_prediction={res['matches_prediction']} "
             f"missing={len(res['missing_predicted'])} "
             f"unpredicted={len(res['unpredicted'])}" if pred else ""))
    ok = not bad and (pred is None or res["matches_prediction"])
    print("M2", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
