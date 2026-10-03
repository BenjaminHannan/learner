"""Cross-check: drive the REAL execute_integer_call (pipeline_code/calculator_tools.py, imported read-only)
with a uniform random policy, apply the single-token rule (0..UMAX), score with checkers written
independently from common.py (tree rebuilt from operand_references), and compare with exact values."""
import sys, random
sys.path.insert(0, "../pipeline_code")
from calculator_tools import execute_integer_call
from common import exact_random_strict

def literal_registry(values):
    reg, pos = [], 0
    for i, v in enumerate(values):
        s = str(v)
        reg.append({"id": "literal:%d" % i, "index": i, "value": v, "char_span": [pos, pos + len(s)],
                    "token_indices": [i], "source": "literal", "status": "OK"})
        pos += len(s) + 2
    return reg

def rollout(numbers, target, rnd, umax=99, pointer="distinct"):
    reg = literal_registry(list(numbers) + [target])  # target literal is in the question
    oks = []
    for call in range(1, 5):
        action = rnd.choice(["NONE", "ADD", "SUB"])
        refs = []
        if action != "NONE":
            n = len(reg)
            if pointer == "distinct":
                a, b = rnd.sample(range(n), 2)
            else:
                a, b = rnd.randrange(n), rnd.randrange(n)
            refs = [a, b]
        tr = execute_integer_call(action, refs, reg, call_index=call)
        if tr["status"] == "OK":
            v = tr["result"]["value"]
            if 0 <= v <= umax:             # one canonical numeric token (assumed range)
                reg.append(tr["result"]); oks.append(tr["result"])
    return oks

def leaves(rid, by_id):
    e = by_id[rid]
    if e["source"] == "literal":
        return [rid]
    return leaves(e["operand_references"][0], by_id) + leaves(e["operand_references"][1], by_id)

def check(numbers, target, oks):
    k = len(numbers)
    lits = ["literal:%d" % i for i in range(k)]
    by_id = {r["id"]: r for r in oks}
    for i in range(k + 1):
        by_id["literal:%d" % i] = {"source": "literal"}
    def strict_ok(calls):
        if len(calls) != k - 1 or calls[-1]["value"] != target:
            return False
        used = [x for c in calls for x in c["operand_references"]]
        res_ids = [c["id"] for c in calls]
        return (all(used.count(l) == 1 for l in lits) and ("literal:%d" % k) not in used and
                all(used.count(r) == 1 for r in res_ids[:-1]) and res_ids[-1] not in used)
    strict = strict_ok(oks)
    stop = strict_ok(oks[:k - 1]) if len(oks) >= k - 1 else False
    lenient = False
    for c in oks:
        if c["value"] == target:
            lv = leaves(c["id"], by_id)
            if ("literal:%d" % k) not in lv and len(lv) == len(set(lv)) and len(lv) >= 2:
                lenient = True
    return strict, stop, lenient

if __name__ == "__main__":
    rnd = random.Random(1)
    cases = [((7, 12), 19), ((30, 7), 23), ((7, 12, 30), 25), ((5, 9, 23, 31), 40), ((11, 4, 20), 27)]
    R = 60000
    for pointer in ("distinct", "independent"):
        for nums, t in cases:
            s = st = le = 0
            for _ in range(R):
                a, b, c = check(nums, t, rollout(nums, t, rnd, pointer=pointer))
                s += a; st += b; le += c
            ex, exs = exact_random_strict(list(nums), t, pointer=pointer)
            print("%-11s %-16s t=%-3d real-tool MC strict %.4f stop %.4f lenient %.4f | exact strict %.4f stop %.4f"
                  % (pointer, nums, t, s / R, st / R, le / R, ex, exs))
