"""TEACH-verified: a second look at the yes/no rows with an 'Unknown' option (the first self-check forced Yes or No, so it could not see unanswerable questions).

For every yes/no row of teach_200k.jsonl (the 171,940 file) the 1.2B reads the passage, then the paraphrase, and answers Yes / No / Unknown ("Unknown" if the text does not say).
A row is kept only when BOTH answers equal its label. Short-answer rows pass through unchanged. Then Yes/No are balanced per kind.
Resumable: stage 1 appends to <out>/verify_yn.jsonl, stage 2 (--finalize) writes <out>/teach_verified_all.jsonl.
Usage: python3 verify.py --inp teach_200k.jsonl --out DIR [--batch 192]  ;  python3 verify.py --inp ... --out DIR --finalize"""
import argparse, json, random
from pathlib import Path
from collections import Counter, defaultdict

ap = argparse.ArgumentParser()
ap.add_argument("--inp", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--batch", type=int, default=192); ap.add_argument("--backend", default="hf"); ap.add_argument("--finalize", action="store_true")
a = ap.parse_args()
out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
rows = [json.loads(l) for l in open(a.inp)]
vp = out / "verify_yn.jsonl"
done = {json.loads(l)["id"]: json.loads(l) for l in open(vp)} if vp.exists() else {}
SUF = "\nAnswer Yes, No, or Unknown (Unknown if the text does not say). Answer with one word only."


def msg(text, q):
    return [{"role": "user", "content": f"{text}\n{q}{SUF}"}]


def label(x):
    x = x.strip().lower().split()[0].strip(".,!") if x.strip() else ""
    return x if x in ("yes", "no", "unknown") else "other"


if not a.finalize:
    from teach import Backend
    be = Backend(a.backend, a.batch)
    todo = [r for r in rows if r["type"] == "yes_no" and r["id"] not in done]
    print(len(todo), "yes/no rows to check", flush=True)
    for s in range(0, len(todo), 4096):
        ch = todo[s:s + 4096]
        m = [msg(r["source_text"], r["question"]) for r in ch] + [msg(r["paraphrase"], r["question"]) for r in ch]
        o = be.chat(m, max_new=4, temperature=0.0)
        with open(vp, "a") as f:
            for i, r in enumerate(ch):
                f.write(json.dumps({"id": r["id"], "p": label(o[i]), "q": label(o[len(ch) + i])}) + "\n")
        print(f"  {s + len(ch)}/{len(todo)}", flush=True)
else:
    keep, drop = [], Counter()
    byk = defaultdict(lambda: {"Yes": [], "No": []})
    for r in rows:
        if r["type"] == "short_answer":
            keep.append(r); continue
        v, lab = done.get(r["id"]), r["canonical_answer"].lower()
        if v and v["p"] == lab and v["q"] == lab:
            byk[r["kind"]][r["canonical_answer"]].append(r)
        else:
            drop["fail_" + (("unknown" if "unknown" in (v["p"], v["q"]) else "disagree") if v else "unchecked")] += 1
    rng = random.Random(11)
    for d in byk.values():
        n = min(len(d["Yes"]), len(d["No"]))
        for l in ("Yes", "No"):
            rng.shuffle(d[l]); keep += d[l][:n]; drop["balance_cut_" + l] += len(d[l]) - n
    rng.shuffle(keep)
    with open(out / "teach_verified_all.jsonl", "w") as f:
        for r in keep:
            f.write(json.dumps(r) + "\n")
    print(len(keep), dict(Counter(r["type"] if r["type"] == "short_answer" else r["canonical_answer"] for r in keep)), dict(drop))
