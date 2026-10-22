"""Alpha-renamed LOGIC STRUCTURE overlap (names and predicate words renamed by first appearance in the stored program, wording ignored).
   Which share of each eval file's problems has a train problem with the identical structure (and the same label)?   -> structure.json"""
import json, os, re, hashlib, collections as C
B = "/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/lt2/rows/"
H = lambda s: hashlib.blake2b(s.encode(), digest_size=8).digest()
def canon(prog):
    names = {}
    def sub(m):
        w = m.group(0)
        if w in ("F", "R", "Q", "x"): return w
        return names.setdefault(w, f"w{len(names)}")
    return re.sub(r"[a-z][a-z0-9_]*", sub, prog)
def canon_sorted(prog):
    # order-insensitive: rename by first appearance, but sort items by renamed text after a first pass (stable enough for tiny problems)
    items = [i.strip() for i in prog.split(";")]
    q = [i for i in items if i.startswith("Q")]; rest = sorted(i for i in items if not i.startswith("Q"))
    return canon("; ".join(rest + q))
train = {}
for tn in ("logic_train", "placebo_train"):
    s, l = set(), {}
    for line in open(B + tn + ".jsonl"):
        r = json.loads(line); c = canon(r["meta"]["program"]); h = H(c); s.add(h); l.setdefault(h, set()).add(r["answer"])
    train[tn] = (s, l)
res = {}
for en in ["logic_gate", "logic_dev", "logic_test_sampler", "logic_test_deeper", "placebo_dev", "placebo_test_wording"]:
    rows = [json.loads(x) for x in open(B + f"eval/{en}.jsonl")]
    d = {}
    for tn, (s, l) in train.items():
        hit = [r for r in rows if H(canon(r["meta"]["program"])) in s]
        agree = sum(r["answer"] in l[H(canon(r["meta"]["program"]))] for r in hit)
        byl = C.Counter(r["level"] for r in hit); tot = C.Counter(r["level"] for r in rows)
        d[tn] = dict(n=len(rows), same_structure_in_train=len(hit), label_present_in_train_group=agree, by_level={str(k): [byl[k], tot[k]] for k in sorted(tot)})
    res[en] = d
    print(en, json.dumps(d))
json.dump(res, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "structure.json"), "w"), indent=1)
