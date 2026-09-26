"""Independent recount of mu-402 counts and marks. Reads raw files only; prints integers, never reply text."""
import json, math, os
from collections import defaultdict, Counter

R = "/home/user/learner/artifacts/claude-mu402-20260926"
ARMS = ["A", "B", "T"]


def jl(p):
    with open(p) as f:
        return [json.loads(l) for l in f if l.strip()]


problems = []

# ---- panel
items = jl(f"{R}/devchat/items.jsonl")
panel = {}
for it in items:
    if it["item_id"] in panel:
        problems.append(f"duplicate panel item {it['item_id']}")
    panel[it["item_id"]] = [t["kind"] for t in it["turns"]]
n_turns_total = sum(len(v) for v in panel.values())
print("panel conversations", len(panel), "turns", n_turns_total)
print("panel turns by kind", dict(sorted(Counter(k for v in panel.values() for k in v).items())))

# ---- replies
replies = {}
for a in ARMS:
    rows = jl(f"{R}/run/chat_{a}.jsonl")
    d = {}
    for r in rows:
        key = (r["item_id"], r["turn_i"])
        if key in d:
            problems.append(f"{a}: duplicate row {key}")
        d[key] = r
        if r["item_id"] not in panel:
            problems.append(f"{a}: row for unknown item {r['item_id']}")
        elif r["turn_i"] >= len(panel[r["item_id"]]):
            problems.append(f"{a}: turn index beyond panel {key}")
        elif panel[r["item_id"]][r["turn_i"]] != r["kind"]:
            problems.append(f"{a}: kind mismatch {key}")
    for iid, kinds in panel.items():
        for ti in range(len(kinds)):
            if (iid, ti) not in d:
                problems.append(f"{a}: missing reply {iid} turn {ti}")
    empty = sum(1 for r in rows if not (r.get("reply") or "").strip())
    print(f"arm {a}: rows {len(rows)} empty replies {empty}")
    replies[a] = d

# ---- claims judges
ckey = json.load(open(f"{R}/judge/keys/claims_key.json"))
print("claims key packets", len(ckey), "by arm", dict(Counter(v["arm"] for v in ckey.values())))
key_pairs = Counter((v["arm"], v["item_id"]) for v in ckey.values())
dup_key = {k: c for k, c in key_pairs.items() if c != 1}
if dup_key:
    problems.append(f"claims key: (arm,item) not mapped exactly once: {dup_key}")
for a in ARMS:
    for iid in panel:
        if (a, iid) not in key_pairs:
            problems.append(f"claims key: missing packet for {a} {iid}")

# judgements[(arm,item)] = list of (judge, flags)
judgements = defaultdict(list)
bad_len = []
unknown_pid = []
same_judge_twice = []
nonbinary = []
for j in range(1, 9):
    rows = jl(f"{R}/judge/out/claims_j{j}.jsonl")
    seen = Counter(r["pid"] for r in rows)
    for pid, c in seen.items():
        if c > 1:
            same_judge_twice.append((j, pid, c))
    for r in rows:
        pid = r["pid"]
        if pid not in ckey:
            unknown_pid.append((j, pid))
            continue
        arm, iid = ckey[pid]["arm"], ckey[pid]["item_id"]
        fl = r["flags"]
        if any(x not in (0, 1) for x in fl):
            nonbinary.append((j, pid))
        if len(fl) != len(panel[iid]):
            bad_len.append((j, pid, arm, iid, len(fl), len(panel[iid])))
        judgements[(arm, iid)].append((j, fl))
    print(f"judge j{j}: rows {len(rows)}")
print("unknown pids", unknown_pid)
print("pid judged twice by same judge", same_judge_twice)
print("non-0/1 flags", nonbinary)
print("flags length mismatches", bad_len)
judges_per_pid = Counter()
for (arm, iid), js in judgements.items():
    judges_per_pid[len(js)] += 1
    if len({j for j, _ in js}) != len(js):
        problems.append(f"same judge twice on {arm} {iid}")

res = {}
for a in ARMS:
    C = 0
    both = either = 0
    by_kind = Counter()
    by_kind_both = Counter()
    exactly2 = 0
    per_conv = {}
    judge_flags = Counter()
    for iid, kinds in panel.items():
        js = judgements.get((a, iid), [])
        if len(js) == 2:
            exactly2 += 1
        conv = 0
        for ti, kind in enumerate(kinds):
            n = sum(fl[ti] for _, fl in js if ti < len(fl))
            C += n
            conv += n
            by_kind[kind] += n
            if n >= 1:
                either += 1
            if n == 2:
                both += 1
        per_conv[iid] = conv
    res[a] = dict(C=C, both=both, either=either, by_kind=dict(sorted(by_kind.items())),
                  exactly2=exactly2, per_conv=per_conv)
    print(f"arm {a}: C={C} both={both} either={either} convs_with_exactly_2_judgements={exactly2}")
    print(f"   flags by kind {dict(sorted(by_kind.items()))}")
    # judge agreement (report only): replies where the two judges agree
    agree = 0
    tot = 0
    for iid, kinds in panel.items():
        js = judgements.get((a, iid), [])
        if len(js) == 2:
            for ti in range(len(kinds)):
                tot += 1
                agree += js[0][1][ti] == js[1][1][ti]
    print(f"   judge agreement {agree}/{tot}")

# ---- marks
CA, CB, CT = res["A"]["C"], res["B"]["C"], res["T"]["C"]
m1 = (CA - CB >= 10) and (CB <= 0.67 * CA)
print(f"\nM1: C_A={CA} C_B={CB} C_T={CT} diff={CA-CB} 0.67*C_A={0.67*CA:.2f} pass={m1}")

more = sum(1 for i in panel if res["A"]["per_conv"][i] > res["B"]["per_conv"][i])
fewer = sum(1 for i in panel if res["A"]["per_conv"][i] < res["B"]["per_conv"][i])
equal = len(panel) - more - fewer
n = more + fewer
p = sum(math.comb(n, k) for k in range(more, n + 1)) / 2 ** n if n else 1.0
m2 = p <= 0.05
print(f"M2: A>B {more} A<B {fewer} equal {equal} n={n} one-sided p={p:.6g} pass={m2}")

wins = losses = ties = 0
per_judge = {}
for pj in (1, 2):
    pkey = json.load(open(f"{R}/judge/keys/pair_key_p{pj}.json"))
    rows = jl(f"{R}/judge/out/pair_p{pj}.jsonl")
    seen_items = Counter()
    w = l = t = 0
    for r in rows:
        k = pkey[r["pid"]]
        seen_items[k["item_id"]] += 1
        if sorted([k["1"], k["2"]]) != ["A", "B"]:
            problems.append(f"pair key p{pj} {r['pid']} arms {k['1']},{k['2']}")
        win = r["winner"]
        if win == "tie":
            t += 1
        elif win in ("1", "2"):
            if k[win] == "B":
                w += 1
            else:
                l += 1
        else:
            problems.append(f"pair p{pj} bad winner {win!r}")
    missing = [i for i in panel if seen_items[i] != 1]
    print(f"pair p{pj}: rows {len(rows)} B wins {w} B losses {l} ties {t} items not judged exactly once {len(missing)}"
          f" key B-in-slot1 {sum(1 for v in pkey.values() if v['1']=='B')}")
    per_judge[pj] = (w, l, t)
    wins += w; losses += l; ties += t
m3 = losses - wins <= 16
print(f"M3: B wins {wins} B losses {losses} ties {ties} losses-wins={losses-wins} pass={m3}")

differ = sum(1 for k in replies["A"] if replies["A"][k]["reply"] != replies["B"].get(k, {}).get("reply"))
v2 = differ >= len(replies["A"]) / 2
print(f"V2: A vs B replies differ {differ}/{len(replies['A'])} pass={v2}")
differ_strip = sum(1 for k in replies["A"] if replies["A"][k]["reply"].strip() != replies["B"].get(k, {}).get("reply", "").strip())
print(f"    (after whitespace strip: {differ_strip})")

proved_wrong = CB >= CA
print(f"proved wrong (C_B >= C_A): {proved_wrong}")
verdict = "PASS" if (m1 and m2 and m3) else "FAIL"
print("verdict (before V1):", verdict)
print("\nproblems:", problems if problems else "none")

json.dump(dict(C_A=CA, C_B=CB, C_T=CT, res={a: {k: v for k, v in res[a].items() if k != 'per_conv'} for a in ARMS},
               more=more, fewer=fewer, equal=equal, p=p, wins=wins, losses=losses, ties=ties, per_judge=per_judge,
               differ=differ, m1=m1, m2=m2, m3=m3, v2=v2, proved_wrong=proved_wrong, verdict=verdict),
          open(os.path.join(os.path.dirname(__file__), "mine.json"), "w"), indent=1)
