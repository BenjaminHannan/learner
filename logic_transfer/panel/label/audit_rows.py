"""Independent re-derivation of every gold label from the rendered prompt text.
   usage: PYTHONPATH=<wt/lt> python3 audit_rows.py        (writes perrow/<file>.jsonl)
   Does not import logicgen. Reads only the converted v2 row files (prompt, answer, meta)."""
import json, os, random, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rlib

ROWS = "/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/lt2/rows/"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "perrow")
FILES = [("logic_gate", "eval/logic_gate.jsonl"), ("logic_dev", "eval/logic_dev.jsonl"),
         ("logic_test_sampler", "eval/logic_test_sampler.jsonl"), ("logic_test_deeper", "eval/logic_test_deeper.jsonl"),
         ("placebo_dev", "eval/placebo_dev.jsonl"), ("placebo_test_wording", "eval/placebo_test_wording.jsonl"),
         ("logic_train", "logic_train.jsonl"), ("placebo_train", "placebo_train.jsonl")]
SAMPLE_IDX = set(random.Random(20261014).sample(range(130000), 20000))   # the 20k random sample of each train file


def audit(r):
    m = r["meta"]
    out = {"id": r["id"], "gold": r["answer"], "metalabel": m["label"], "lvl": r["level"], "depth": m.get("depth"),
           "fam": r["family"], "variant": r["variant"], "tset": m.get("template_set"), "sampler": m.get("sampler")}
    p = rlib.parse_prompt(r["prompt"])
    out["ok"] = p.ok
    if not p.ok:
        out["err"] = p.err
        return out
    # --- fidelity of the rendered text to the stored program (text -> structure)
    pf, pr, pq = rlib.read_program(m["program"])
    out["fid"] = (set(p.facts) == pf and rlib.norm_rules(p.rules) == rlib.norm_rules(pr) and p.query == pq)
    out["ids"] = p.ids
    out["ids_match"] = p.ids == m["template_ids"]
    # options suffix words should contain the gold answer
    body, opts = rlib.split_options(r["prompt"])
    out["ans_in_opts"] = r["answer"] in opts
    lab, contra, rd, gr = rlib.fwd(p.facts, p.rules, p.query)
    out["mine"] = lab
    out["contra"] = contra
    ml, dsize, dh = rlib.min_depth(p.facts, p.rules, p.query)
    out["dsize"], out["dheight"] = dsize, dh
    out["cls"] = rlib.classical(p.facts, p.rules, p.query)
    out["nf"], out["nr"] = len(p.facts), len(p.rules)
    out["qneg"] = p.query[0]
    out["ents"] = len(rlib.entities(p.facts, p.rules, p.query))
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    only = sys.argv[1:]
    for name, rel in FILES:
        if only and name not in only:
            continue
        t0 = time.time()
        n = 0
        with open(ROWS + rel) as f, open(f"{OUT}/{name}.jsonl", "w") as o:
            for i, line in enumerate(f):
                r = json.loads(line)
                a = audit(r)
                a["i"] = i
                a["sample"] = (i in SAMPLE_IDX) if name.endswith("_train") else True
                o.write(json.dumps(a) + "\n")
                n += 1
        print(name, n, f"{time.time()-t0:.1f}s", flush=True)


if __name__ == "__main__":
    main()
