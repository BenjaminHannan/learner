"""Length and vocabulary coverage of the logic format versus the parents' 200k-row curriculum. Writes length_coverage.json and curriculum_words.json"""
from common import *
lens = [len(r["prompt"]) for r in stream_jsonl(S + "/data/sk200k/train.jsonl")]
ll = [len(r["prompt"]) for i, r in enumerate(stream_jsonl(TRAIN["logic_train"])) if i < 30000]
pl = [len(r["prompt"]) for i, r in enumerate(stream_jsonl(TRAIN["placebo_train"])) if i < 30000]
out = {p: dict(curriculum=round(100 * sum(x > p for x in lens) / len(lens), 2), logic=round(100 * sum(x > p for x in ll) / len(ll), 2),
               placebo=round(100 * sum(x > p for x in pl) / len(pl), 2)) for p in [100, 130, 150, 170, 190, 200]}
c = Counter(r["family"] for r in stream_jsonl(S + "/data/sk200k/train.jsonl") if len(r["prompt"]) > 150)
json.dump(dict(pct_rows_longer_than_chars=out, families_over_150=c.most_common(10)), open(OUT + "/length_coverage.json", "w"), indent=1)
print(out)
rows = [r["prompt"] for r in stream_jsonl(S + "/data/sk200k/train.jsonl")]
pats = {"not": r"\bnot\b", "never": r"\bnever\b", "n't": r"n't", "non-": r"\bnon-", "unknown": r"\bunknown\b", "surely": r"\bsurely\b", "truly": r"\btruly\b",
        "quite": r"\bquite\b", "yes": r"\byes\b", "true": r"\btrue\b", "false": r"\bfalse\b", "options suffix (a/b/c)": r"\([a-z]+/[a-z]+/[a-z]+\)", "was": r"\bwas\b"}
cw = {k: sum(bool(re.search(p, x, re.I)) for x in rows) for k, p in pats.items()}
lg = [r["prompt"] for i, r in enumerate(stream_jsonl(TRAIN["logic_train"])) if i < 20000]
lw = {k: round(100 * sum(bool(re.search(p, x, re.I)) for x in lg) / len(lg), 1) for k, p in pats.items()}
fam = Counter()
for r in stream_jsonl(S + "/data/sk200k/train.jsonl"):
    if re.search(r"\bnot\b|n't|\bnever\b", r["prompt"], re.I): fam[r["family"]] += 1
json.dump(dict(curriculum_rows_with_word=cw, n_curriculum_rows=len(rows), pct_logic_rows_with_word=lw, families_with_negation_word=fam.most_common(8)), open(OUT + "/curriculum_words.json", "w"), indent=1)
print(cw, lw, fam.most_common(4))
