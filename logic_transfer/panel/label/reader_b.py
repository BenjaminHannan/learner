"""Reader B: a template-FREE keyword reader (no sentence inventory). Cues only: negation words, quantifier 'no/none/nothing',
conditional markers, position of capitalised entity, order of content words. Used to cross-check parser A's reading of what each
sentence MEANS. usage: python3 reader_b.py  -> readerb.json"""
import json, os, re, sys, random, collections as C
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rlib
FUNC = set("""every all any each if what those a anything being no none nothing not non when whenever should given once provided both fact note we
it is are was be then and plus gives means makes must never things thing ones one too yes true false unknown surely quite truly know the
can tell does follow that claim check decide so or isn't""".split())
COND = {"if", "when", "whenever", "should", "given", "once", "provided", "being", "makes"}


def read_sentence(s, last=False):
    s = s.strip().rstrip(".?")
    s = s.replace("isn't", "is not").replace("Non-", "Not ").replace("non-", "not ")
    toks = re.findall(r"[A-Za-z]+", s)
    low = [t.lower() for t in toks]
    low = ["not" if t == "never" else t for t in low]
    ent = None
    for i, t in enumerate(toks):
        if t[0].isupper():
            if i > 0 and t.lower() not in FUNC:
                ent = t.lower()
            elif i == 0 and t.lower() not in FUNC and len(low) > 1 and low[1] in ("is", "was", "being"):
                ent = t.lower()
    cw = [i for i, t in enumerate(low) if t not in FUNC and t != ent]
    # entity first-word case: the entity token itself is excluded, others are content words
    neg = lambda i: i > 0 and low[i - 1] == "not"
    if last:
        assert len(cw) == 1 and ent, s
        return ("Q", (neg(cw[0]), low[cw[0]], ent))
    if ent and not (set(low) & COND):
        assert len(cw) == 1, s
        return ("F", (neg(cw[0]), low[cw[0]], ent))
    if ent:
        assert len(cw) == 2, s
        a, b = cw
        if toks[0].lower() == ent and ("if" in low or "when" in low):   # "E is B if E is A"
            a, b = b, a
        return ("R", (((neg(a), low[a]),), (neg(b), low[b]), ent))
    quant_no = bool(set(low) & {"no", "none", "nothing"})
    cps = [(neg(i), low[i]) for i in cw]
    if len(cps) == 2:
        return ("R", ((cps[0],), (cps[1][0] or quant_no, cps[1][1]), None))
    assert len(cps) == 3, s
    return ("R", ((cps[0], cps[1]), cps[2], None))


def read_prompt(prompt):
    body, _ = rlib.split_options(prompt)
    ss = rlib.sentences(body)
    facts, rules, q = [], [], None
    for k, s in enumerate(ss):
        kind, obj = read_sentence(s, last=(k == len(ss) - 1))
        if kind == "F": facts.append(obj)
        elif kind == "R": rules.append(obj)
        else: q = obj
    return facts, rules, q


if __name__ == "__main__":
    ROWS = "/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/lt2/rows/"
    FILES = [("logic_gate", "eval/logic_gate.jsonl"), ("logic_dev", "eval/logic_dev.jsonl"), ("logic_test_sampler", "eval/logic_test_sampler.jsonl"),
             ("logic_test_deeper", "eval/logic_test_deeper.jsonl"), ("placebo_dev", "eval/placebo_dev.jsonl"),
             ("placebo_test_wording", "eval/placebo_test_wording.jsonl"), ("logic_train", "logic_train.jsonl"), ("placebo_train", "placebo_train.jsonl")]
    SAMPLE = set(random.Random(20261014).sample(range(130000), 20000))
    out = {}
    badtpl = C.Counter()
    for name, rel in FILES:
        tr = name.endswith("_train")
        n = same = fail = lab_ok = 0
        for i, line in enumerate(open(ROWS + rel)):
            if tr and i not in SAMPLE: continue
            r = json.loads(line); n += 1
            p = rlib.parse_prompt(r["prompt"])
            try:
                f, ru, q = read_prompt(r["prompt"])
            except Exception as e:
                fail += 1; continue
            a = (set(p.facts), rlib.norm_rules(p.rules), p.query)
            b = (set(f), rlib.norm_rules(ru), q)
            if a == b:
                same += 1
                lab_ok += rlib.fwd(f, ru, q)[0] == r["answer"]
            else:
                # which template ids disagree?
                for sid in p.ids: badtpl[sid] += 1
        out[name] = dict(n=n, reader_failed=fail, same_as_parser_A=same, label_agree_via_B=lab_ok)
        print(name, out[name], flush=True)
    out["templates_in_disagreeing_rows"] = badtpl.most_common(12)
    json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "readerb.json"), "w"), indent=1)
