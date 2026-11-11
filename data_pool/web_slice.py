"""Build the nested FineWeb-Edu slices for the data pool (stage 8b). CPU only.

  python3 web_slice.py --shards shard/000_00000.parquet [more.parquet ...] --index panels/all.npz --out out/ \
      [--fk-max 12] [--budgets rung10=5.7e6,rung30=117.4e6,rung100=503.4e6]

Rules (all fixed before any run; none reads an answer):
  * source: HuggingFaceFW/fineweb-edu sample-10BT shards, in file order (human-written web text, ODC-By; Ben OK 8:57 PM ET 10-06);
  * keep a document only if: language == en, language_score >= 0.9, int_score >= 3 (already true for this set),
    Flesch-Kincaid grade <= --fk-max, token_count is used as the size (within 1-2% of the LFM-tokenizer count, measured on 2,400 docs),
    and NO 13-gram / 8-12-word whole-text hit against the panel index (overlap13.py; any hit drops the whole document);
  * exact duplicate texts dropped (FineWeb is already MinHash-deduplicated per dump; this only catches repeats across shards);
  * slices are NESTED: documents are taken in file order and the rung-10 slice is the first part of the rung-30 slice, which is
    the first part of the rung-100 slice, so a bigger rung never swaps the text, it only adds to it (one change at a time).
Writes slice_<rung>.jsonl (id, text, token_count, fk), plain.jsonl marking docs with FK <= 10 (the plain-English subset for talker probe 4b),
and MANIFEST.json with counts, sha256 of every file and the drop reasons. Never prints document text.
"""
import argparse, hashlib, json, re, sys
from pathlib import Path
import pyarrow.parquet as pq
sys.path.insert(0, str(Path(__file__).resolve().parent))
import overlap13 as O


def fk_grade(text):
    sents = max(1, len(re.findall(r"[.!?]+(?:\s|$)", text)))
    ws = re.findall(r"[A-Za-z']+", text); n = max(1, len(ws))
    syl = sum(max(1, len(re.findall(r"[aeiouy]+", w.lower()))) for w in ws)
    return 0.39 * n / sents + 11.8 * syl / n - 15.59


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shards", nargs="+", required=True); ap.add_argument("--index", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--fk-max", type=float, default=12.0); ap.add_argument("--plain-fk", type=float, default=10.0)
    ap.add_argument("--budgets", default="rung10=5.7e6,rung30=117.4e6,rung100=503.4e6")
    a = ap.parse_args()
    budgets = [(k, float(v)) for k, v in (x.split("=") for x in a.budgets.split(","))]
    by_len, _ = O.load_index(a.index)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    files = {k: open(out / f"slice_{k}.jsonl", "w") for k, _ in budgets}
    plain = open(out / "plain.jsonl", "w")
    seen, drops, tot, ri = set(), {}, 0, 0
    def drop(why): drops[why] = drops.get(why, 0) + 1
    done = False
    for sh in a.shards:
        for b in pq.ParquetFile(sh).iter_batches(batch_size=1000, columns=["text", "id", "token_count", "language", "language_score", "int_score"]):
            for r in b.to_pylist():
                if r["language"] != "en" or r["language_score"] < 0.9 or r["int_score"] < 3: drop("quality"); continue
                g = fk_grade(r["text"])
                if g > a.fk_max: drop("too_hard"); continue
                hh = hashlib.blake2b(r["text"].encode(), digest_size=16).digest()
                if hh in seen: drop("duplicate"); continue
                if O.doc_hits(r["text"], by_len): drop("panel_overlap"); continue
                seen.add(hh)
                rec = json.dumps({"id": r["id"], "text": r["text"], "token_count": r["token_count"], "fk": round(g, 1)}) + "\n"
                while ri < len(budgets) and tot >= budgets[ri][1]: ri += 1
                if ri >= len(budgets): done = True; break
                # nested: a document goes to its rung and every bigger rung
                for k, _ in budgets[ri:]: files[k].write(rec)
                if g <= a.plain_fk: plain.write(rec)
                tot += r["token_count"]
            if done: break
        if done: break
    for f in list(files.values()) + [plain]: f.close()
    man = {"fk_max": a.fk_max, "plain_fk": a.plain_fk, "budgets": dict(budgets), "tokens_taken": tot, "drops": drops, "shards": a.shards,
           "sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.glob("*.jsonl"))}}
    (out / "MANIFEST.json").write_text(json.dumps(man, indent=1)); print(json.dumps({"tokens_taken": tot, "drops": drops}))


if __name__ == "__main__":
    main()
