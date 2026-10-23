"""Replay candidates through the acceptance pipeline, split by template, instantiate, write corpus + MANIFEST.

Usage: python build_corpus.py --work DIR --out /mnt/project-files/data/wordprob-v1/ [--per-template 100]
"""
import argparse, collections, hashlib, json, os, random, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core
from gen_templates import load_old

SALT = "wordprob-v1-split-salt"
MIN_INSTANCES = 30


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def assign_splits(templates, salt=SALT, seed=7):
    """Return ({id: split}, structural_topics). 4-step templates of 2 topics -> heldout_structure only."""
    by_topic = collections.Counter(t["topic"] for t in templates if t["n_steps"] == 4)
    eligible = sorted(k for k, v in by_topic.items() if v >= 8)
    struct_topics = sorted(random.Random(seed).sample(eligible, 2)) if len(eligible) >= 2 else []
    out = {}
    for t in templates:
        if t["n_steps"] == 4 and t["topic"] in struct_topics:
            out[t["id"]] = "heldout_structure"
        else:
            out[t["id"]] = core.split_of(t["id"], salt)
    return out, struct_topics


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--per-template", type=int, default=100)
    a = ap.parse_args()
    acc = core.Acceptor(load_old())
    n_cand = 0
    for line in open(os.path.join(a.work, "candidates.jsonl")):
        n_cand += 1
        acc.add(json.loads(line)["t"])
    templates = list(acc.accepted.values())
    rej = dict(acc.rejections)
    splits, struct_topics = assign_splits(templates)
    stage = os.path.join(a.work, "stage")
    shutil.rmtree(stage, ignore_errors=True)
    os.makedirs(stage)
    files = {k: open(os.path.join(stage, k + ".jsonl"), "w") for k in
             ["train", "dev", "heldout_template", "heldout_structure"]}
    tf = open(os.path.join(stage, "templates.jsonl"), "w")
    counts = {"templates": collections.Counter(), "problems": collections.Counter(),
              "problems_by_steps": collections.defaultdict(collections.Counter),
              "problems_by_topic": collections.Counter(), "templates_by_steps": collections.Counter(),
              "templates_by_topic": collections.Counter()}
    kept = 0
    for t in templates:
        insts = core.make_instances(t, a.per_template, SALT)
        if len(insts) < MIN_INSTANCES:
            rej["small_space"] = rej.get("small_space", 0) + 1
            continue
        sp = splits[t["id"]]
        kept += 1
        row_t = dict(t, split=sp, n_instances=len(insts))
        tf.write(json.dumps(row_t) + "\n")
        counts["templates"][sp] += 1
        counts["templates_by_steps"][t["n_steps"]] += 1
        counts["templates_by_topic"][t["topic"]] += 1
        for i, ins in enumerate(insts):
            row = {"id": "%s-%03d" % (t["id"], i), "template_id": t["id"], "question": ins["question"],
                   "answer": ins["answer"], "scratchpad": ins["scratchpad"], "steps": ins["steps"],
                   "topic": t["topic"], "n_steps": t["n_steps"]}
            files[sp].write(json.dumps(row) + "\n")
            counts["problems"][sp] += 1
            counts["problems_by_steps"][sp][t["n_steps"]] += 1
            counts["problems_by_topic"][t["topic"]] += 1
    for f in list(files.values()) + [tf]:
        f.close()
    spend = json.load(open(os.path.join(a.work, "spend.json")))
    # copy to destination and re-read to verify
    os.makedirs(a.out, exist_ok=True)
    names = ["templates.jsonl"] + [k + ".jsonl" for k in files]
    sums = {}
    for n in names:
        shutil.copyfile(os.path.join(stage, n), os.path.join(a.out, n))
        s_local, s_remote = sha256(os.path.join(stage, n)), sha256(os.path.join(a.out, n))
        assert s_local == s_remote, "copy mismatch " + n
        sums[n] = s_local
    manifest = {
        "version": "wordprob-v1", "generator": "scripts/wordprob/", "template_model": core_model(),
        "split_salt": SALT, "structural_holdout_topics": struct_topics,
        "sha256": sums, "counts": {k: (dict(v) if not isinstance(v, collections.defaultdict) else {s: dict(c) for s, c in v.items()}) for k, v in counts.items()},
        "n_templates_total": kept, "n_problems_total": sum(counts["problems"].values()),
        "candidates_seen": n_cand, "template_rejections": rej,
        "api_spend": {"usd": spend["usd"], "input_tokens": spend["input_tokens"], "output_tokens": spend["output_tokens"],
                      "calls": spend["calls"], "assumed_price_per_m_in_out": [spend["price_in_per_m"], spend["price_out_per_m"]]},
        "scratchpad_format": "'37 + 46 = 83. 83 - 9 = 74. Answer: 74' ('/' denotes exact integer division)",
        "answers_from": "python ast-whitelisted evaluator; never from the LLM",
    }
    with open(os.path.join(a.out, "MANIFEST.json"), "w") as f:
        json.dump(manifest, f, indent=1, sort_keys=True)
    print(json.dumps({k: manifest[k] for k in ["n_templates_total", "n_problems_total", "counts", "template_rejections", "api_spend", "structural_holdout_topics"]}, indent=1, default=str))


def core_model():
    from gen_templates import MODEL
    return MODEL


if __name__ == "__main__":
    main()
