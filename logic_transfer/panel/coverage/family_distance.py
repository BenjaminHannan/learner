"""Cross-sentence reference distance: parents' logic-flavoured families vs the logic/placebo rows.
metric = for each capitalised name / single-letter variable in the FINAL sentence (not its first word) that also occurs earlier,
chars between its nearest earlier occurrence (start) and its occurrence in the final sentence (start). Row value = median over its names.
Writes family_distance.json"""
from common import *
import statistics as st, random
random.seed(0)

def dist_row(prompt):
    p = SUFFIX_RE.sub("", prompt)
    ss = [m for m in re.finditer(r"[^.?!]+[.?!]?", p) if m.group().strip()]
    # last sentence = last chunk ending in ? (or last chunk)
    q = [m for m in ss if m.group().strip().endswith("?")]
    last = q[-1] if q else ss[-1]
    a0 = last.start()
    txt = p[a0:last.end()]
    toks = [(m.group(), a0 + m.start()) for m in re.finditer(r"\b[A-Z][a-z]*\b(?=[^a-z]|$)|\b[A-Z]\b", txt)]
    toks = [t for t in toks[1:] if t[0] not in ("I", "A", "Is", "Are", "Does", "Who", "What", "How", "Which", "Question", "Rule", "True", "False", "Check", "Claim", "Decide", "Can", "Then", "So")]
    ds = []
    for w, pos in toks:
        earlier = [m.start() for m in re.finditer(r"\b" + re.escape(w) + r"\b", p[:a0])]
        if earlier: ds.append(pos - earlier[-1])
    return st.median(ds) if ds else None

fam_rows = defaultdict(list)
for r in stream_jsonl(S + "/data/sk200k/train.jsonl"):
    if r["family"] in ("syllogism", "prop_eval", "kin_chain", "order_chain", "passage_qa", "object_track", "rule_apply", "verify_claim", "story_chain3", "state_update"):
        if len(fam_rows[r["family"]]) < 1500: fam_rows[r["family"]].append(r["prompt"])
out = {}
for fam, ps in fam_rows.items():
    v = [d for d in (dist_row(p) for p in ps) if d is not None]
    if not v:
        out[fam] = dict(n=0); continue
    out[fam] = dict(n=len(v), median_chars=st.median(v), p90=sorted(v)[int(.9 * len(v))], max=max(v), share_within_4=round(sum(x <= 4 for x in v) / len(v), 3))
for name, path in [("logic_train", TRAIN["logic_train"]), ("placebo_train", TRAIN["placebo_train"]), ("logic_gate", EVAL["logic_gate"]), ("placebo_dev", EVAL["placebo_dev"])]:
    v = [d for d in (dist_row(r["prompt"]) for r in read_jsonl(path, 3000)) if d is not None]
    out[name] = dict(n=len(v), median_chars=st.median(v), p90=sorted(v)[int(.9 * len(v))], max=max(v), share_within_4=round(sum(x <= 4 for x in v) / len(v), 3))
json.dump(out, open(OUT + "/family_distance.json", "w"), indent=1)
for k, v in out.items(): print("%-15s" % k, v)
