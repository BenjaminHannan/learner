"""Check which integers are ONE canonical token of the public LFM2.5-1.2B-Instruct tokenizer.
Mirrors CalculatorPath._numeric_value: encode(str(n), add_special_tokens=False) has length 1,
the id is not bos/eos/pad, and decode(ids) == str(n)."""
import json
from tokenizers import Tokenizer
tok = Tokenizer.from_file("tok/tokenizer.json")
special = {t["id"] for t in json.load(open("tok/tokenizer.json"))["added_tokens"] if t.get("special")}
def single(n):
    s = str(n)
    ids = tok.encode(s, add_special_tokens=False).ids
    return len(ids) == 1 and ids[0] not in special and tok.decode(ids, skip_special_tokens=False) == s
ok = [n for n in range(-200, 2001) if single(n)]
print("single-token integers in -200..2000:", len(ok))
neg = [n for n in ok if n < 0]
print("negatives single:", neg[:10])
# contiguous ranges
rng = []
for n in ok:
    if rng and n == rng[-1][1] + 1: rng[-1][1] = n
    else: rng.append([n, n])
print("ranges:", rng[:20])
print("examples:", {s: tok.encode(s, add_special_tokens=False).tokens for s in ["7","25","99","100","123","-5","1000"]})
print("pre_tokenizer:", json.dumps(json.load(open("tok/tokenizer.json"))["pre_tokenizer"])[:600])
