"""13-gram overlap check: keep sealed / held-out panel text out of the training pool.

Two steps, so the owner of a protected panel never has to hand its text to anyone:
  index : read panels, keep ONLY the text fields named in the spec (never an answer field), write hashed word n-grams.
  scan  : drop every pool document that shares a hashed n-gram with any panel; write a clean file and a report.

What counts as a hit (all on lower-cased words, punctuation dropped, numbers kept):
  * a panel text with >= 13 words contributes every 13-word window; a pool text hits if any window matches;
  * a panel text with 8..12 words contributes its whole word sequence (one window of that length);
  * a panel text with < 8 words is ignored (too generic to mean anything; recorded in the index stats).
The report and the index hold hashes, counts and document ids only. They never contain panel text or answers.
Protected panels (GOLD-PRIVATE*, reserved*, blind*) are refused by `index`; their owner runs `index` on their own
side with the same spec format and hands over only the .npz of hashes (`--panel-hash-only` files are merged by `merge`).

  python3 overlap13.py index --spec panels.json --out panels.npz
  python3 overlap13.py index --owner-hash-only --out theirs.npz PATH [PATH ...]   # protected panels, run by their owner only
  python3 overlap13.py scan  --index panels.npz --input pool.jsonl --text-field text --id-field id --out clean.jsonl --report report.json
  python3 overlap13.py merge --out all.npz a.npz b.npz
"""
import argparse, glob, hashlib, json, re, sys, unicodedata
from pathlib import Path
import numpy as np

N = 13
MIN_SHORT = 8
PROTECTED = re.compile(r"gold-private|reserved|blind", re.I)
WORD = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")


def words(text):
    return WORD.findall(unicodedata.normalize("NFKC", text).lower().replace("’", "'"))


def h(ws):
    return int.from_bytes(hashlib.blake2b(" ".join(ws).encode(), digest_size=8).digest(), "little")


def panel_hashes(text):
    """-> (set of (length, hash)), ignored? for one panel text."""
    ws = words(text)
    if len(ws) >= N:
        return {(N, h(ws[i:i + N])) for i in range(len(ws) - N + 1)}, False
    if len(ws) >= MIN_SHORT:
        return {(len(ws), h(ws))}, False
    return set(), True


def get_path(obj, path):
    """'questions[].question' style: dotted keys, '[]' fans out over a list."""
    cur = [obj]
    for part in path.split("."):
        fan = part.endswith("[]")
        key = part[:-2] if fan else part
        nxt = []
        for c in cur:
            if isinstance(c, dict) and key in c:
                v = c[key]
                nxt.extend(v if fan and isinstance(v, list) else [v])
        cur = nxt
    return [c for c in cur if isinstance(c, str)]


def load_records(path, fmt):
    if fmt == "json_examples":
        yield from json.load(open(path))["examples"]
    elif fmt == "whole_json":
        yield json.load(open(path))
    elif fmt == "jsonl":
        for line in open(path):
            if line.strip():
                yield json.loads(line)
    else:
        raise SystemExit(f"unknown format {fmt}")


def all_strings(o):
    """Every string anywhere in a JSON value (keys are not read). Used only by --owner-hash-only."""
    if isinstance(o, dict):
        for v in o.values(): yield from all_strings(v)
    elif isinstance(o, list):
        for v in o: yield from all_strings(v)
    elif isinstance(o, str):
        yield o


def pack(pairs):
    arr = np.array(sorted(pairs), dtype=np.uint64) if pairs else np.zeros((0, 2), dtype=np.uint64)
    return arr


def cmd_owner_hash_only(a):
    """The panel's OWNER runs this on their own machine. No spec, no field names: every string in every .json/.jsonl under the paths is
    hashed (answers included, which only makes the check stricter). Prints counts only; writes only the .npz of hashes."""
    files = []
    for p in a.paths:
        pp = Path(p)
        files += sorted(str(f) for f in pp.rglob("*") if f.suffix in (".json", ".jsonl")) if pp.is_dir() else [str(pp)]
    allp, per = set(), []
    for f in files:
        texts = ign = 0
        try:
            recs = list(load_records(f, "jsonl" if f.endswith(".jsonl") else "whole_json"))
        except Exception as e:
            per.append({"file_sha8": hashlib.sha256(f.encode()).hexdigest()[:8], "error": type(e).__name__}); continue
        for rec in recs:
            for t in all_strings(rec):
                s, skipped = panel_hashes(t); texts += 1; ign += skipped; allp |= s
        per.append({"file_sha8": hashlib.sha256(f.encode()).hexdigest()[:8], "texts": texts, "ignored_short": ign})
    arr = np.array([(L, x) for L, x in sorted(allp)], dtype=np.uint64).reshape(-1, 2)
    np.savez(a.out, grams=arr, stats=np.array(json.dumps(per)))
    print(json.dumps({"files": len(files), "hashes": int(len(arr)), "per_file": per}))


def cmd_index(a):
    if a.owner_hash_only:
        return cmd_owner_hash_only(a)
    spec = json.load(open(a.spec))
    base = Path(a.spec).resolve().parent
    allp, stats = set(), []
    for p in spec["panels"]:
        for f in sorted(glob.glob(str(base / p["path"]))):
            if PROTECTED.search(f) or PROTECTED.search(p["name"]):
                raise SystemExit(f"REFUSED: {f} looks like a protected panel (gold-private / reserved / blind). "
                                 "Its owner must run `index` on their side and share only the hash file.")
            texts = ign = 0
            for rec in load_records(f, p["format"]):
                for fld in p["text_fields"]:
                    for t in get_path(rec, fld):
                        s, skipped = panel_hashes(t)
                        texts += 1; ign += skipped; allp |= {(L, x) for L, x in s}
            stats.append({"panel": p["name"], "file": Path(f).name, "texts": texts, "ignored_short": ign})
    arr = np.array([(L, x) for L, x in sorted(allp)], dtype=np.uint64).reshape(-1, 2)
    np.savez(a.out, grams=arr, stats=np.array(json.dumps(stats)))
    print(json.dumps({"hashes": int(len(arr)), "panels": stats}, indent=1))


def load_index(path):
    z = np.load(path, allow_pickle=False)
    g = z["grams"]
    by_len = {}
    for L in np.unique(g[:, 0]):
        by_len[int(L)] = set(g[g[:, 0] == L][:, 1].tolist())
    return by_len, json.loads(str(z["stats"]))


def doc_hits(text, by_len):
    ws = words(text)
    n = 0
    for L, S in by_len.items():
        if len(ws) < L:
            continue
        for i in range(len(ws) - L + 1):
            if h(ws[i:i + L]) in S:
                n += 1
    return n


def cmd_scan(a):
    by_len, stats = load_index(a.index)
    kept = dropped = hit_windows = 0
    hit_ids = []
    out = open(a.out, "w") if a.out else None
    for i, line in enumerate(open(a.input)):
        if not line.strip():
            continue
        rec = json.loads(line)
        texts = get_path(rec, a.text_field)
        n = sum(doc_hits(t, by_len) for t in texts)
        if n:
            dropped += 1; hit_windows += n; hit_ids.append(rec.get(a.id_field, i))
        else:
            kept += 1
            if out: out.write(line if line.endswith("\n") else line + "\n")
    rep = {"input": a.input, "kept": kept, "dropped": dropped, "hit_windows": hit_windows, "dropped_ids": hit_ids[:1000],
           "index_stats": stats, "n": N, "min_short": MIN_SHORT}
    if a.report: json.dump(rep, open(a.report, "w"), indent=1)
    print(json.dumps({k: rep[k] for k in ("kept", "dropped", "hit_windows")}))


def cmd_merge(a):
    parts = [np.load(f)["grams"] for f in a.inputs]
    g = np.unique(np.concatenate(parts), axis=0)
    np.savez(a.out, grams=g, stats=np.array(json.dumps([{"merged_from": [Path(f).name for f in a.inputs]}])))
    print(len(g), "hashes")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="c", required=True)
    i = sp.add_parser("index"); i.add_argument("--spec"); i.add_argument("--out", required=True)
    i.add_argument("--owner-hash-only", action="store_true", help="for protected panels, run by their owner: hash every string, print counts only")
    i.add_argument("paths", nargs="*"); i.set_defaults(f=cmd_index)
    s = sp.add_parser("scan"); s.add_argument("--index", required=True); s.add_argument("--input", required=True)
    s.add_argument("--text-field", default="text"); s.add_argument("--id-field", default="id"); s.add_argument("--out"); s.add_argument("--report")
    s.set_defaults(f=cmd_scan)
    m = sp.add_parser("merge"); m.add_argument("--out", required=True); m.add_argument("inputs", nargs="+"); m.set_defaults(f=cmd_merge)
    a = ap.parse_args(); a.f(a)
