"""exact prompt-body overlap between logic_train and placebo_train (and shared question-less contexts)."""
import json, hashlib, re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rlib
B = "/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/lt2/rows/"
H = lambda s: hashlib.blake2b(s.encode(), digest_size=8).digest()
bodies, ctxs = {}, {}
for tn in ("logic_train", "placebo_train"):
    b, c = set(), set()
    for line in open(B + tn + ".jsonl"):
        r = json.loads(line); body = rlib.split_options(r["prompt"])[0]
        b.add(H(body)); c.add(H(" ".join(rlib.sentences(body)[:-1])))
    bodies[tn], ctxs[tn] = b, c
res = dict(exact_body_overlap=len(bodies["logic_train"] & bodies["placebo_train"]), same_context_text_overlap=len(ctxs["logic_train"] & ctxs["placebo_train"]),
           distinct_contexts_logic=len(ctxs["logic_train"]), distinct_contexts_placebo=len(ctxs["placebo_train"]))
print(res); json.dump(res, open("train_cross.json", "w"))
