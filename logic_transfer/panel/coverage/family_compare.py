"""Task 2c: parents' normal families (sk200k/train.jsonl) vs the logic/placebo format. Writes family_compare.json."""
from common import *
import statistics as st, re

RES = REPO + "/custom_io/results/70-vast-t1sdr/70-t1sdr-s200/T1SDR_s200/RESULT.json"
fe = json.load(open(RES))["final_eval"]
def acc(split, fam):
    c = fe.get(split, {}).get("by_family", {}).get(fam)
    return None if not c else round(100 * c["correct"] / c["n"], 1)

rows = read_jsonl(S + "/data/sk200k/train.jsonl")
by = defaultdict(list)
for r in rows: by[r["family"]].append(r)
charfreq = Counter()
for r in rows: charfreq.update(r["prompt"])
nsent = lambda p: len([s for s in re.split(r"(?<=[.?!:])\s+", p.strip()) if s])
out = {}
for fam, rs in sorted(by.items()):
    ch = [len(r["prompt"]) for r in rs]
    wd = [len(r["prompt"].split()) for r in rs]
    ns = [nsent(r["prompt"]) for r in rs]
    ans = Counter(r["answer"] for r in rs)
    isnum = sum(bool(re.fullmatch(r"-?\d+", r["answer"])) for r in rs) / len(rs)
    inprompt = sum(bool(re.search(r"(?<![A-Za-z0-9])" + re.escape(r["answer"]) + r"(?![A-Za-z0-9])", r["prompt"])) for r in rs) / len(rs)
    out[fam] = dict(n=len(rs), chars_mean=round(st.mean(ch), 1), chars_p90=sorted(ch)[int(.9 * len(ch))], chars_max=max(ch),
                    words_mean=round(st.mean(wd), 1), sentences_mean=round(st.mean(ns), 1),
                    distinct_answers=len(ans), top_answers=ans.most_common(5), frac_numeric=round(isnum, 3),
                    frac_answer_is_prompt_token=round(inprompt, 3),
                    parent_s200_in_dist=acc("in_dist", fam), parent_s200_frame=acc("frame", fam),
                    parent_s200_vocab=acc("vocab", fam), parent_s200_variant=acc("variant", fam))
# answer words overall
allans = Counter(r["answer"] for r in rows)
wordset = {w: allans[w] for w in ["yes", "no", "true", "false", "unknown", "maybe", "cannot tell"] }
fam_with_unknown = sorted({r["family"] for r in rows if r["answer"] == "unknown"})
fam_with_tf = sorted({r["family"] for r in rows if r["answer"] in ("true", "false")})
fam_with_yn = sorted({r["family"] for r in rows if r["answer"] in ("yes", "no")})
# prompts containing the words unknown/true/false anywhere
kw = {w: sum(bool(re.search(r"\b" + w + r"\b", r["prompt"])) for r in rows) for w in ["unknown", "true", "false"]}
# chars of logic rows
lchars = Counter()
for name in ["logic_train", "placebo_train"]:
    for i, r in enumerate(stream_jsonl(TRAIN[name])):
        if i >= 20000: break
        lchars.update(r["prompt"])
for p in EVAL.values():
    for r in stream_jsonl(p): lchars.update(r["prompt"])
chars_report = {c: dict(logic=lchars[c], sk200k=charfreq.get(c, 0)) for c in sorted(lchars)}
rare = {c: v for c, v in chars_report.items() if v["sk200k"] < 2000}
tot_sk = sum(charfreq.values())
res = dict(families=out, answer_word_counts=wordset, families_with_unknown_answer=fam_with_unknown,
           families_with_true_false_answer=fam_with_tf, families_with_yes_no_answer=fam_with_yn,
           prompts_containing_word=kw, n_rows=len(rows),
           chars_in_logic_but_rare_in_sk200k=rare,
           chars_not_in_sk200k=[c for c in lchars if charfreq.get(c, 0) == 0],
           sk200k_char_total=tot_sk, sk200k_distinct_chars=len(charfreq),
           sk200k_prompt_chars_overall=dict(mean=round(st.mean(len(r["prompt"]) for r in rows), 1),
                                            p90=sorted(len(r["prompt"]) for r in rows)[int(.9 * len(rows))],
                                            max=max(len(r["prompt"]) for r in rows)))
json.dump(res, open(OUT + "/family_compare.json", "w"), indent=1)
print("%-20s %5s %6s %6s %5s %5s %6s %6s | %6s %6s %6s %6s" % ("family", "n", "chars", "p90", "words", "sent", "numrc", "inprmp", "indist", "frame", "vocab", "varnt"))
for fam, v in out.items():
    print("%-20s %5d %6.1f %6d %5.1f %5.1f %6.2f %6.2f | %6s %6s %6s %6s %s" % (fam, v["n"], v["chars_mean"], v["chars_p90"], v["words_mean"], v["sentences_mean"], v["frac_numeric"], v["frac_answer_is_prompt_token"], v["parent_s200_in_dist"], v["parent_s200_frame"], v["parent_s200_vocab"], v["parent_s200_variant"], v["top_answers"][:3] if v["distinct_answers"] <= 12 else ""))
print({k: res[k] for k in ["answer_word_counts", "families_with_unknown_answer", "families_with_true_false_answer", "families_with_yes_no_answer", "prompts_containing_word", "chars_not_in_sk200k", "sk200k_prompt_chars_overall"]})
print("rare chars:", rare)
