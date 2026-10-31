"""Stage-1 data build (deterministic). Usage: python3 backbone/build_data.py OUT_DIR [--workers 4] [--skip-tokens]

Uses the v1 generator settings (learnlab.village.shards, seed 0, 250 visits/shard) but builds only
  train       shards 0-39    (TRAIN, 10,000 visits)
  train       shards 380-399 (DEV pool, 5,000 visits)
  validation  all 4 shards   (1,000 visits)
The village `test` split is never generated or read.

Raw shards are written byte-for-byte as the full generator writes them (OUT/raw/<split>/shard-NNNNN.{txt,jsonl});
they are checked against v1's design/v1/data/village-SHA256SUMS.txt when that file is found (git show 71a6919e0:...).
Then QA rows are written to OUT/{train,dev,validation}.jsonl:
  {id, split, shard, visit_id, qtype, base_qtype, bank, template, style, rule_family, action, depth,
   long_range, visible, knowable, context, question, answer}
steps    = the evidence lines the oracle used, as text, in derivation (chain) order: a list of strings (see steps_src); [] if none
steps_src= "chain" (oracle path order) | "file_order" (path did not cover all its evidence: lines in file order) |
           "none_told" (depth 0, answer "not told") | "none_prior_visit" (some evidence lies in an earlier visit, so not in the row's context) | "none_no_lines"
           (long-range rows whose evidence is all in this visit keep their steps: build_data's context is the whole visit before the question)
context  = every text line of the visit before the question line (stream tags kept, "\n"-joined)
question = the question line up to (not including) " [answer] ", i.e. "[question] ..."
answer   = canonical answer. Prompt for the LM = context + "\n" + question + " [answer]", target = " " + answer.
dev      = fixed seed-0 sample of 4,000 questions from shards 380-399.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing
import random
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PER_SHARD, SEED = 250, 0
TRAIN_SHARDS = range(0, 40)
DEV_SHARDS = range(380, 400)
VAL_SHARDS = range(0, 4)
DEV_N = 4000
V1_COMMIT = "71a6919e0"
V1_SUMS = "design/v1/data/village-SHA256SUMS.txt"
ANSWER_TAG = " [answer] "


def config():
    from learnlab.village import shards as S
    return {"split": "", "n_visits": 0, "seed": SEED, "visits_per_shard": PER_SHARD, "generator": S.GENERATOR,
            "families": S.FAMILIES, "names": S.NAMES, "patterns": None, "tokenizer": None,
            "window_chars": S.WINDOW_CHARS, "audit_every": S.AUDIT_EVERY}


def make_shard(task):
    """Shard `shard` of `split`: exactly what write_shards writes for that index (same _make_shard)."""
    from learnlab.village import shards as S
    split, shard, directory = task
    Path(directory).mkdir(parents=True, exist_ok=True)
    if not all((Path(directory) / f"shard-{shard:05d}{ext}").exists() for ext in (".txt", ".paths.ndjson")):  # a shard from before the paths file is regenerated (same txt/jsonl bytes)
        start = shard * PER_SHARD
        S._make_shard((split, shard, start, start + PER_SHARD, str(directory)))
    return split, shard


def _init():
    from learnlab.village import shards as S
    S._setup(config())


def sha(path):
    h = hashlib.sha256()
    h.update(Path(path).read_bytes())
    return h.hexdigest()


def v1_sums():
    try:
        text = subprocess.run(["git", "show", f"{V1_COMMIT}:{V1_SUMS}"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    except Exception as e:  # git history missing: skip the check, say so
        print(f"[digest] cannot read v1 sums ({e}); check skipped")
        return {}
    return {rel: digest for digest, rel in (line.split(None, 1) for line in text.splitlines() if line.strip()) for rel in [rel.strip()]}


def check_digests(raw: Path, tasks):
    sums = v1_sums()
    bad = ok = 0
    for split, shard, _ in tasks:
        for ext in ("jsonl", "txt"):
            rel = f"{split}/shard-{shard:05d}.{ext}"
            if rel not in sums:
                continue
            if sha(raw / rel) == sums[rel]:
                ok += 1
            else:
                bad += 1
                print(f"[digest] MISMATCH {rel}")
    print(f"[digest] {ok} files match v1 SHA256SUMS, {bad} mismatches ({len(sums)} entries in v1 list)")
    return ok, bad


def steps_of(q, path, lines):
    """(steps, steps_src) of one question: the evidence lines as text in chain order. path = its .paths.ndjson row."""
    if not q["knowable"] or not q.get("depth"):
        return [], "none_told"
    if path["prior_lines"]:
        return [], "none_prior_visit"
    if not path["path_text_lines"] or any(t is None for t in q["evidence_text_lines"]):
        return [], "none_no_lines"
    if path["path_complete"]:
        return [lines[t] for t in path["path_text_lines"]], "chain"
    return [lines[t] for t in sorted(set(path["path_text_lines"]))], "file_order"


def shard_rows(split, shard, directory):
    """QA rows of one shard, parsed from the shard files."""
    base = Path(directory) / f"shard-{shard:05d}"
    lines = base.with_suffix(".txt").read_text(encoding="utf-8").split("\n")
    paths = {r["id"]: r for r in map(json.loads, base.with_suffix(".paths.ndjson").read_text(encoding="utf-8").splitlines())}
    visits, questions = {}, []
    for raw in base.with_suffix(".jsonl").read_text(encoding="utf-8").splitlines():
        row = json.loads(raw)
        if row["kind"] == "visit":
            visits[row["id"]] = row
        else:
            questions.append(row)
    out = []
    for q in questions:
        v = visits[q["visit"]]
        line = lines[q["text_line"]]
        head, sep, _ = line.partition(ANSWER_TAG)
        assert sep and head.startswith("[question] ") or sep, line
        context = "\n".join(lines[v["first_line"]:q["text_line"]])
        assert head.endswith(q["question"]) or q["question"] in head, (head, q["question"])
        steps, steps_src = steps_of(q, paths[q["id"]], lines)
        out.append({
            "id": q["id"], "split": split, "shard": shard, "visit_id": q["visit"], "qtype": q["qtype"],
            "base_qtype": q["base_qtype"], "bank": q["bank"], "template": q["template"], "style": q["style"] or "",
            "rule_family": "+".join(q["families"]) or "none", "action": q.get("action") or "", "depth": q.get("depth"),
            "long_range": bool(q["long_range"]), "visible": bool(q["visible"]), "knowable": bool(q["knowable"]),
            "context": context, "question": head, "answer": str(q["answer"]),
            "steps": steps, "steps_src": steps_src,
        })
    return out


def write_jsonl(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, sort_keys=True) + "\n")


def pct(xs, ps=(50, 90, 95, 99, 100)):
    xs = sorted(xs)
    return {f"p{p}": xs[min(len(xs) - 1, int(len(xs) * p / 100))] for p in ps}


def token_stats(out: Path, sets, log):
    try:
        from huggingface_hub import hf_hub_download
        from tokenizers import Tokenizer
        files = [hf_hub_download("Qwen/Qwen3.5-0.8B", "tokenizer.json")]
        tok = Tokenizer.from_file(files[0])
    except Exception as e:
        log(f"[tokens] tokenizer unavailable ({type(e).__name__}: {e}); token stats skipped")
        return {}
    stats = {}
    for name, rows in sets.items():
        sample = rows if len(rows) <= 4000 else random.Random(0).sample(rows, 4000)
        enc = tok.encode_batch([r["context"] + "\n" + r["question"] + " [answer]" for r in sample])
        lens = [len(e.ids) for e in enc]
        ans = [len(e.ids) for e in tok.encode_batch([" " + r["answer"] for r in sample])]
        stats[name] = {"n_sampled": len(sample), "prompt_tokens": pct(lens), "answer_tokens": pct(ans),
                       "frac_over_1024": sum(l > 1024 for l in lens) / len(lens),
                       "frac_over_2048": sum(l > 2048 for l in lens) / len(lens), "mean_prompt_tokens": sum(lens) / len(lens)}
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--skip-tokens", action="store_true")
    args = ap.parse_args()
    out = Path(args.out).resolve()
    raw = out / "raw"
    log = lambda s: print(s, flush=True)
    tasks = ([("train", s, raw / "train") for s in (*TRAIN_SHARDS, *DEV_SHARDS)]
             + [("validation", s, raw / "validation") for s in VAL_SHARDS])
    ctx = multiprocessing.get_context("spawn")
    with ctx.Pool(args.workers, initializer=_init) as pool:
        for i, (split, shard) in enumerate(pool.imap_unordered(make_shard, tasks)):
            if (i + 1) % 10 == 0 or i + 1 == len(tasks):
                log(f"[shards] {i + 1}/{len(tasks)} done")
    dig = check_digests(raw, tasks)

    by = {"train": [], "dev_pool": [], "validation": []}
    for split, shard, d in tasks:
        rows = shard_rows(split, shard, d)
        by["validation" if split == "validation" else ("train" if shard in TRAIN_SHARDS else "dev_pool")] += rows
    dev = random.Random(SEED).sample(by["dev_pool"], DEV_N)
    dev.sort(key=lambda r: r["id"])
    sets = {"train": by["train"], "dev": dev, "validation": by["validation"]}
    for name, rows in sets.items():
        write_jsonl(out / f"{name}.jsonl", rows)
    report = {"seed": SEED, "per_shard": PER_SHARD, "digest_ok": dig[0], "digest_bad": dig[1], "counts": {}}
    for name, rows in {**sets, "dev_pool": by["dev_pool"]}.items():
        qt = {}
        for r in rows:
            qt[r["qtype"]] = qt.get(r["qtype"], 0) + 1
        src = {}
        for r in rows:
            src[r["steps_src"]] = src.get(r["steps_src"], 0) + 1
        report["counts"][name] = {"steps_src": dict(sorted(src.items())), "steps_with_long_range": sum(bool(r["steps"]) and r["long_range"] for r in rows),
                                  "questions": len(rows), "visits": len({r["visit_id"] for r in rows}),
                                  "per_qtype": dict(sorted(qt.items())),
                                  "context_chars": pct([len(r["context"]) for r in rows])}
    if not args.skip_tokens:
        report["tokens"] = token_stats(out, sets, log)
    (out / "DATA_REPORT.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    log(json.dumps(report, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
