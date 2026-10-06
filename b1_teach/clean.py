"""TEACH-clean: drop yes/no rows whose question the passage does not support, then balance Yes/No per kind.

Heuristic support test (suggested, not shown to be exact): content words = question words minus stop/auxiliary words, matched by 4-letter prefix
against the passage OR paraphrase text.
  Yes row: at least 2 content words and every one of them found (the question restates the passage).
  Both: the question must start with an auxiliary (Is/Was/Did/Can ...).
  No  row: at most 1 content word is missing AND at least 2 are found (one fact is swapped, the rest is anchored in the passage),
           or the passage contains a negation word (not, never, n't) and all content words are found.
Short-answer rows pass through unchanged. Then per kind Yes and No are cut to the smaller count.
Usage: python3 clean.py --inp out/teach_all.jsonl --out out/teach_clean_all.jsonl"""
import argparse, json, random, re
from collections import Counter, defaultdict
STOP = set("""a an the is are was were be been am do does did has have had can could will would shall should may might must of to in on at by for with from
and or but if so as it its it's he she they them his her their him who whom whose what which that this these those there here not no yes any some
than then too very just also one two up down out over into onto after before again once more most""".split())
NEG = re.compile(r"\b(not|never|no|cannot)\b|n't")


AUX = re.compile(r"^(is|are|was|were|do|does|did|can|could|will|would|has|have|had|must|should)\b", re.I)


def words(t):
    return [w[:4] for w in re.findall(r"[a-z']+", t.lower().replace("'s", "")) if w not in STOP and len(w) > 1]


def supported(r):
    if not AUX.match(r["question"]):
        return False                       # must read as a yes/no question ("Is/Was/Did/Can ...")
    q = set(words(r["question"]))
    if not q:
        return False
    have = set(words(r["source_text"])) | (set(words(r["paraphrase"])) if r["canonical_answer"] == "No" else set())   # a Yes must be restated by the passage itself
    found, missing = len(q & have), len(q - have)
    if r["canonical_answer"] == "Yes":
        return missing == 0 and found >= 2
    return (missing <= 1 and found >= 2) or (missing == 0 and bool(NEG.search((r["source_text"] + " " + r["paraphrase"]).lower())))


ap = argparse.ArgumentParser(); ap.add_argument("--inp", required=True); ap.add_argument("--out", required=True); a = ap.parse_args()
rows = [json.loads(l) for l in open(a.inp)]
keep, drops = [], Counter()
byk = defaultdict(lambda: {"Yes": [], "No": []})
for r in rows:
    if r["type"] == "short_answer":
        keep.append(r)
    elif supported(r):
        byk[r["kind"]][r["canonical_answer"]].append(r)
    else:
        drops["unsupported_" + r["canonical_answer"]] += 1
rng = random.Random(7)
for k, d in byk.items():
    n = min(len(d["Yes"]), len(d["No"]))
    for lab in ("Yes", "No"):
        rng.shuffle(d[lab]); keep += d[lab][:n]; drops["balance_cut_" + lab] += len(d[lab]) - n
rng.shuffle(keep)
with open(a.out, "w") as f:
    for r in keep:
        f.write(json.dumps(r) + "\n")
print(len(rows), "->", len(keep), dict(Counter(r["type"] if r["type"] == "short_answer" else r["canonical_answer"] for r in keep)), dict(drops))
