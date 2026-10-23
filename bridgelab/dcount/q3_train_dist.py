"""Q2/Q3: answer distributions in village train data (jsonl banks) + do number words appear in story text. CPU, no model."""
import json, glob, collections, re, sys
ROOT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/claude-0/scratch/r0/root"
NUM = "zero one two three four five six seven eight nine ten".split()
out = {}
for split in ("train", "dev", "validation"):
    qt = collections.Counter(); ans_q5 = collections.Counter(); ans_bank = collections.defaultdict(collections.Counter)
    ans_all = collections.Counter(); nq = 0; unk_cnt = collections.Counter(); nvis = 0
    story_num = collections.Counter(); story_lines = 0
    for f in sorted(glob.glob(f"{ROOT}/{split}/shard-*.jsonl")):
        for l in open(f):
            r = json.loads(l)
            if r.get("kind") == "visit": nvis += 1
            if r.get("kind") != "question": continue
            nq += 1; qt[r["qtype"]] += 1; ans_all[r["answer"]] += 1
            if r["bank"] in ("q.count_at", "q.count_held"):
                if r["knowable"]:
                    ans_q5[r["answer"]] += 1; ans_bank[r["bank"]][r["answer"]] += 1
                else: unk_cnt[r["bank"]] += 1
        for l in open(f.replace(".jsonl", ".txt")):
            if l.startswith("[world]"):
                story_lines += 1
                for w in re.findall(r"[a-z]+", l.lower()):
                    if w in NUM: story_num[w] += 1
    tot5 = sum(ans_q5.values())
    out[split] = dict(visits=nvis, questions=nq, qtype_counts=dict(sorted(qt.items(), key=lambda x: int(x[0][1:]))),
                      q5_knowable=tot5, q5_share_of_all=tot5 / nq, q5_answer_hist={k: ans_q5[k] for k in NUM if ans_q5[k]},
                      q5_answer_frac={k: round(ans_q5[k] / tot5, 4) for k in NUM if ans_q5[k]},
                      q5_by_bank={b: {k: c[k] for k in NUM if c[k]} for b, c in ans_bank.items()},
                      count_banks_not_told=dict(unk_cnt),
                      top_answers_all=ans_all.most_common(12),
                      story_numberword_occurrences=dict(story_num), story_world_lines=story_lines,
                      answer_freq_number_words_all_banks={k: ans_all[k] for k in NUM if ans_all[k]})
json.dump(out, open(__file__.replace(".py", ".json"), "w"), indent=1)
print(json.dumps(out, indent=1))
