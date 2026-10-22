"""Task 1: coverage table, train vs each eval file. Writes coverage.json and prints text tables."""
from common import *
import statistics as st, sys

def pct(a, n): return round(100.0 * a / n, 2) if n else None

def quant(xs):
    xs = sorted(xs); n = len(xs)
    q = lambda p: xs[min(n - 1, int(p * n))]
    return dict(mean=round(sum(xs) / n, 2), min=xs[0], p10=q(.1), p50=q(.5), p90=q(.9), max=xs[-1])

def summarize(path, limit=None):
    d = dict(n=0)
    dl = Counter(); tids = Counter(); rowtids = []
    sampler = Counter(); tset = Counter(); fam = Counter(); stage = Counter(); variant = Counter()
    nr = Counter(); nf = Counter(); nd = Counter(); nsent = Counter()
    chars = []; wds = []; ans_pos = Counter(); level_label = Counter()
    kinds_row = Counter(); roles = Counter(); qkind = Counter()
    progs = set()
    for i, r in enumerate(stream_jsonl(path)):
        if limit and i >= limit: break
        m = r["meta"]
        d["n"] += 1
        dl[(r["level"], m["label"])] += 1
        sampler[m["sampler"]] += 1; tset[m["template_set"]] += 1; fam[r["family"]] += 1
        stage[r["stage"]] += 1; variant[r["variant"]] += 1
        nr[m["n_rules"]] += 1; nf[m["n_facts"]] += 1; nd[m["n_distractors"]] += 1
        tl = m["template_ids"]; rowtids.append(tuple(tl)); tids.update(tl)
        nsent[len(tl)] += 1
        for t in set(kind_of_tid(x) for x in tl): kinds_row[t] += 1
        roles.update(kind_of_tid(x) for x in tl)
        body, opts = split_prompt(r["prompt"])
        chars.append(len(r["prompt"])); wds.append(len(r["prompt"].split()))
        ans_pos[opts.index(r["answer"]) if r["answer"] in opts else -1] += 1
        ctx = m["ctx"]
        progs.add("|".join(sorted(ctx.split("; "))) + "|Q " + m["query"])
    d.update(depth_label={f"{a}|{b}": c for (a, b), c in sorted(dl.items(), key=lambda x: (str(x[0][0]), x[0][1]))},
             sampler=dict(sampler), template_set=dict(tset), family=dict(fam), stage=dict(stage), variant=dict(variant),
             n_rules=dict(sorted(nr.items())), n_facts=dict(sorted(nf.items())), n_distractors=dict(sorted(nd.items())),
             n_sentences=dict(sorted(nsent.items())),
             chars=quant(chars), words=quant(wds), answer_pos_in_suffix=dict(sorted(ans_pos.items())),
             rows_with_kind={k: v for k, v in sorted(kinds_row.items())}, sentence_roles=dict(sorted(roles.items())))
    return d, tids, rowtids, progs

res = {}; all_tids = {}; all_rowtids = {}; all_progs = {}
for name, p in list(TRAIN.items()) + list(EVAL.items()):
    print("scanning", name, file=sys.stderr)
    d, t, rt, pg = summarize(p)
    res[name] = d; all_tids[name] = t; all_rowtids[name] = rt; all_progs[name] = pg

train_tids = set(all_tids["logic_train"]) | set(all_tids["placebo_train"])
train_by_kind = defaultdict(set)
for t in train_tids: train_by_kind[kind_of_tid(t)].add(t)
res["_train_tid_union_by_kind"] = {k: sorted(v, key=lambda x: int(x.split(":")[1])) for k, v in sorted(train_by_kind.items())}
# also: tids present in logic_train vs placebo_train individually
res["_tid_counts_logic_vs_placebo_train"] = {
    "only_logic": sorted(set(all_tids["logic_train"]) - set(all_tids["placebo_train"])),
    "only_placebo": sorted(set(all_tids["placebo_train"]) - set(all_tids["logic_train"]))}
from logicgen_templates_shim import TEMPLATES, heldout_ids, train_ids
declared_heldout = {f"{k}:{i}" for k in TEMPLATES for i in heldout_ids(k)}
declared_train = {f"{k}:{i}" for k in TEMPLATES for i in train_ids(k)}
res["_declared_heldout_tid_count"] = len(declared_heldout)
res["_declared_train_tid_count"] = len(declared_train)
res["_train_contains_declared_heldout"] = sorted(train_tids & declared_heldout)
res["_train_missing_declared_train"] = sorted(declared_train - train_tids)

# novelty of eval files vs train
train_prog = all_progs["logic_train"] | all_progs["placebo_train"]
for name in EVAL:
    rt = all_rowtids[name]; n = len(rt)
    unseen_row_any = sum(any(t not in train_tids for t in row) for row in rt)
    unseen_row_all = sum(all(t not in train_tids for t in row) for row in rt)
    sent_tot = sum(len(r) for r in rt); sent_un = sum(sum(t not in train_tids for t in r) for r in rt)
    # per kind
    pk = {}
    for k in ["R1", "R2", "R3", "R4", "R5", "FP", "FN", "Q"]:
        tot = sum(sum(kind_of_tid(t) == k for t in r) for r in rt)
        un = sum(sum(kind_of_tid(t) == k and t not in train_tids for t in r) for r in rt)
        pk[k] = dict(sentences=tot, unseen=un, pct_unseen=pct(un, tot))
    # whole-program overlap with train
    ov = len(all_progs[name] & train_prog)
    declared_h = sum(any(t in declared_heldout for t in r) for r in rt)
    res[name]["novelty_vs_train"] = dict(
        rows_any_tid_unseen_pct=pct(unseen_row_any, n), rows_all_tid_unseen_pct=pct(unseen_row_all, n),
        sentences_unseen_pct=pct(sent_un, sent_tot), per_kind=pk,
        rows_with_declared_heldout_tid_pct=pct(declared_h, n),
        program_duplicates_with_train=ov, n_unique_programs=len(all_progs[name]))
res["logic_train"]["n_unique_programs"] = len(all_progs["logic_train"])
res["placebo_train"]["n_unique_programs"] = len(all_progs["placebo_train"])
res["_logic_train_vs_placebo_train_same_context_programs"] = None
json.dump(res, open(OUT + "/coverage.json", "w"), indent=1)
print("wrote coverage.json")
