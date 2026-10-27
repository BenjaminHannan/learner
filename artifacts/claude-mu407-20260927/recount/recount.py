#!/usr/bin/env python3
"""Independent recount of mu-407 from raw files. No repo scripts imported."""
import json, os
from collections import defaultdict, Counter

D = "/home/user/learner/artifacts/claude-mu407-20260927"

# ---------- load key ----------
with open(f"{D}/judge/keys/key.json") as f:
    key = json.load(f)  # pid -> {"arm","item_id"}
assert len(key) == 180, f"key has {len(key)} entries, expected 180"

# ---------- load items (panel) to know valid item ids (60 panel, excl smoke) ----------
panel_ids = []
with open(f"{D}/prep/panel/items.jsonl") as f:
    for line in f:
        row = json.loads(line)
        iid = row["item_id"]
        if iid.endswith("-s1") or iid.endswith("-s2") or iid.endswith("-s3"):
            continue
        panel_ids.append(iid)
panel_ids_set = set(panel_ids)
assert len(panel_ids) == 60, f"expected 60 panel items, got {len(panel_ids)}"

# sanity: every key item_id is in panel (should be, since smoke not judged)
for pid, v in key.items():
    assert v["item_id"] in panel_ids_set, f"key {pid} has non-panel item_id {v['item_id']}"

# ---------- load talk files per arm ----------
ARMS = ["N", "U0", "U1"]
TALK_FILES = {"N": "talk_N.jsonl", "U0": "talk_U0.jsonl", "U1": "talk_U1.jsonl"}

# talk[arm][item_id] = list of 5 rows sorted by turn_i, each row full dict
talk = {arm: defaultdict(dict) for arm in ARMS}
for arm in ARMS:
    path = f"{D}/run/{TALK_FILES[arm]}"
    with open(path) as f:
        for line in f:
            row = json.loads(line)
            assert row["arm"] == arm, f"{path}: row arm {row['arm']} != {arm}"
            iid = row["item_id"]
            ti = row["turn_i"]
            talk[arm][iid][ti] = row
    # check counts: 60 chats x 5 turns = 300
    n_chats = len(talk[arm])
    assert n_chats == 60, f"arm {arm}: {n_chats} chats, expected 60"
    for iid, turns in talk[arm].items():
        assert iid in panel_ids_set, f"arm {arm}: item_id {iid} not in panel 60"
        assert set(turns.keys()) == {0,1,2,3,4}, f"arm {arm} chat {iid}: turn_i set {sorted(turns.keys())}"
    total_rows = sum(len(v) for v in talk[arm].values())
    assert total_rows == 300, f"arm {arm}: total rows {total_rows}"

KIND_ORDER = ["smalltalk", "feelings", "advice", "followup", "ask"]
# verify kind order matches turn_i 0..4 consistently, and consistent across arms for same item (session2 kind sequence is shared)
for arm in ARMS:
    for iid, turns in talk[arm].items():
        kinds = [turns[i]["kind"] for i in range(5)]
        assert kinds == KIND_ORDER, f"arm {arm} chat {iid}: kind order {kinds}"

print("Sanity: talk files OK. 3 arms x 60 chats x 5 turns = 300 rows each.")

# ---------- load claims judges ----------
claims_files = [f"{D}/judge/out/claims_b{i}.jsonl" for i in range(1, 13)]
# pid -> list of flags-lists (one per judge file that had this pid)
claims_by_pid = defaultdict(list)
claims_row_count = 0
for path in claims_files:
    with open(path) as f:
        for line in f:
            row = json.loads(line)
            claims_row_count += 1
            pid = row["pid"]
            flags = row["flags"]
            assert len(flags) == 5, f"{path} pid {pid}: flags len {len(flags)}"
            assert all(x in (0,1) for x in flags), f"{path} pid {pid}: bad flag values {flags}"
            claims_by_pid[pid].append(flags)

print(f"claims rows total: {claims_row_count} (expect 360)")
assert claims_row_count == 360

# ---------- load fit judges ----------
fit_files = [f"{D}/judge/out/fit_b{i}.jsonl" for i in range(1, 13)]
fit_by_pid = defaultdict(list)
fit_row_count = 0
for path in fit_files:
    with open(path) as f:
        for line in f:
            row = json.loads(line)
            fit_row_count += 1
            pid = row["pid"]
            on_turn = row["on_turn"]
            answer = row["answer"]
            assert len(on_turn) == 5, f"{path} pid {pid}: on_turn len {len(on_turn)}"
            assert all(x in (0,1) for x in on_turn), f"{path} pid {pid}: bad on_turn values {on_turn}"
            assert answer in (0,1), f"{path} pid {pid}: bad answer value {answer}"
            fit_by_pid[pid].append({"on_turn": on_turn, "answer": answer})

print(f"fit rows total: {fit_row_count} (expect 360)")
assert fit_row_count == 360

# ---------- check: every pid in key has exactly 2 claims judgements and 2 fit judgements ----------
bad_rows = 0
issues = []
all_pids = set(key.keys())
claims_pids = set(claims_by_pid.keys())
fit_pids = set(fit_by_pid.keys())

if claims_pids != all_pids:
    issues.append(f"claims pid set mismatch: missing={all_pids-claims_pids}, extra={claims_pids-all_pids}")
if fit_pids != all_pids:
    issues.append(f"fit pid set mismatch: missing={all_pids-fit_pids}, extra={fit_pids-all_pids}")

for pid in sorted(all_pids):
    nc = len(claims_by_pid.get(pid, []))
    nf = len(fit_by_pid.get(pid, []))
    if nc != 2:
        issues.append(f"pid {pid}: {nc} claims judgements (expect 2)")
        bad_rows += 1
    if nf != 2:
        issues.append(f"pid {pid}: {nf} fit judgements (expect 2)")
        bad_rows += 1

# check every (arm, chat) has exactly 2 claims and 2 fit judgements
arm_chat_claims = defaultdict(int)
arm_chat_fit = defaultdict(int)
for pid, v in key.items():
    ac = (v["arm"], v["item_id"])
    arm_chat_claims[ac] += len(claims_by_pid.get(pid, []))
    arm_chat_fit[ac] += len(fit_by_pid.get(pid, []))

expected_ac = set()
for arm in ARMS:
    for iid in panel_ids:
        expected_ac.add((arm, iid))
assert len(expected_ac) == 180

missing_ac = expected_ac - set(v["arm"] and (v["arm"], v["item_id"]) for v in key.values())
# Actually check pid coverage: each (arm,item) should appear exactly once as a pid in key
ac_pid_count = defaultdict(int)
for pid, v in key.items():
    ac_pid_count[(v["arm"], v["item_id"])] += 1
for ac in expected_ac:
    c = ac_pid_count.get(ac, 0)
    if c != 1:
        issues.append(f"(arm,chat) {ac}: appears as {c} pids in key (expect 1)")
missing_key_ac = expected_ac - set(ac_pid_count.keys())
extra_key_ac = set(ac_pid_count.keys()) - expected_ac
if missing_key_ac:
    issues.append(f"missing (arm,chat) combos in key: {missing_key_ac}")
if extra_key_ac:
    issues.append(f"extra (arm,chat) combos in key: {extra_key_ac}")

for ac, c in arm_chat_claims.items():
    if c != 2:
        issues.append(f"(arm,chat) {ac}: {c} claims judgements total (expect 2)")
for ac, c in arm_chat_fit.items():
    if c != 2:
        issues.append(f"(arm,chat) {ac}: {c} fit judgements total (expect 2)")

bad_rows = len(issues)
print(f"Coverage check issues: {bad_rows}")
for i in issues:
    print("  ISSUE:", i)

# ---------- Build per-arm, per-chat, per-turn-index claim flag sums (both judges) ----------
# claims: 2 lists of 5 flags per pid -> sum elementwise -> per-turn 0,1,2 (both judges count)
results = {}
for arm in ARMS:
    C_two_judges = 0
    flagged_both = 0
    flagged_either = 0
    claims_by_kind = Counter()
    for iid in panel_ids:
        # find pid for (arm, iid)
        pid = None
        for p, v in key.items():
            if v["arm"] == arm and v["item_id"] == iid:
                pid = p
                break
        assert pid is not None, f"no pid for {arm},{iid}"
        judge_flags = claims_by_pid[pid]  # list of 2 lists of 5
        j1, j2 = judge_flags[0], judge_flags[1]
        for ti in range(5):
            f1, f2 = j1[ti], j2[ti]
            s = f1 + f2
            C_two_judges += s
            if f1 == 1 and f2 == 1:
                flagged_both += 1
            if f1 == 1 or f2 == 1:
                flagged_either += 1
            kind = KIND_ORDER[ti]
            claims_by_kind[kind] += s
    results[arm] = {
        "C_two_judges": C_two_judges,
        "flagged_by_both": flagged_both,
        "flagged_by_either": flagged_either,
        "claims_by_kind": dict(claims_by_kind),
    }

# ---------- Build pid -> (arm, item_id) reverse and index by (arm,item_id)->pid ----------
pid_for = {}
for p, v in key.items():
    pid_for[(v["arm"], v["item_id"])] = p

# ---------- Real answers per arm: ask turn (turn_i=4) BOTH fit judges answer=1 ----------
for arm in ARMS:
    real_answers = 0
    for iid in panel_ids:
        pid = pid_for[(arm, iid)]
        j1, j2 = fit_by_pid[pid]
        if j1["answer"] == 1 and j2["answer"] == 1:
            real_answers += 1
    results[arm]["real_answers_both_judges"] = real_answers

# ---------- On-turn per arm: non-ask replies (turn_i 0-3) BOTH fit judges on_turn=1 ----------
for arm in ARMS:
    on_turn_total = 0
    on_turn_by_kind = Counter()
    for iid in panel_ids:
        pid = pid_for[(arm, iid)]
        j1, j2 = fit_by_pid[pid]
        for ti in range(4):  # non-ask: turn_i 0,1,2,3
            o1, o2 = j1["on_turn"][ti], j2["on_turn"][ti]
            if o1 == 1 and o2 == 1:
                on_turn_total += 1
                on_turn_by_kind[KIND_ORDER[ti]] += 1
    results[arm]["on_turn_non_ask_both_judges"] = on_turn_total
    results[arm]["on_turn_by_kind_nonask"] = dict(on_turn_by_kind)

# also compute on_turn for ask turn (both judges) as extra info (not part of on_turn_non_ask, but for "on_turn by kind" report)
for arm in ARMS:
    ask_on_turn_both = 0
    for iid in panel_ids:
        pid = pid_for[(arm, iid)]
        j1, j2 = fit_by_pid[pid]
        o1, o2 = j1["on_turn"][4], j2["on_turn"][4]
        if o1 == 1 and o2 == 1:
            ask_on_turn_both += 1
    results[arm]["on_turn_ask_both_judges"] = ask_on_turn_both
    # full on_turn_by_kind including ask
    full = dict(results[arm]["on_turn_by_kind_nonask"])
    full["ask"] = ask_on_turn_both
    results[arm]["on_turn_by_kind"] = full

# ---------- Sign test: per chat compare U1 summed flags vs U0 summed flags ----------
def per_chat_sum(arm):
    out = {}
    for iid in panel_ids:
        pid = pid_for[(arm, iid)]
        j1, j2 = claims_by_pid[pid]
        s = sum(j1) + sum(j2)
        out[iid] = s
    return out

sum_U0 = per_chat_sum("U0")
sum_U1 = per_chat_sum("U1")
sum_N = per_chat_sum("N")

fewer = 0  # U1 < U0
more = 0   # U1 > U0
ties = 0
for iid in panel_ids:
    a, b = sum_U1[iid], sum_U0[iid]
    if a < b:
        fewer += 1
    elif a > b:
        more += 1
    else:
        ties += 1

# Binomial sign test: p = P(X >= fewer) for X ~ Binomial(n=fewer+more, 0.5)
from math import comb
def binom_sf_ge(k, n, p=0.5):
    # P(X >= k)
    return sum(comb(n, i) * (p**i) * ((1-p)**(n-i)) for i in range(k, n+1))

n_sign = fewer + more
p_sign = binom_sf_ge(fewer, n_sign, 0.5) if n_sign > 0 else float('nan')

print(f"\nSign test U1 vs U0: fewer={fewer}, more={more}, ties={ties}, n={n_sign}, p={p_sign:.4f}")

# report-only: U1 vs N claims sign test (as in marks.json 'report' section)
fewer_N = 0
more_N = 0
ties_N = 0
for iid in panel_ids:
    a, b = sum_U1[iid], sum_N[iid]
    if a < b:
        fewer_N += 1
    elif a > b:
        more_N += 1
    else:
        ties_N += 1
n_sign_N = fewer_N + more_N
p_sign_N = binom_sf_ge(fewer_N, n_sign_N, 0.5) if n_sign_N > 0 else float('nan')
print(f"Sign test U1 vs N claims (report only): fewer={fewer_N}, more={more_N}, ties={ties_N}, n={n_sign_N}, p={p_sign_N:.4f}")

# ---------- Report only: repeats ----------
# replies byte-identical to an EARLIER reply in the SAME chat (same arm, same item_id)
# For each arm, for each chat (item_id), walk turns 0..4 in order; a turn's reply is a "repeat"
# if it equals (byte-for-byte) some earlier turn's reply IN THE SAME CHAT.
for arm in ARMS:
    repeat_count = 0
    claims_on_repeats = 0  # sum of both-judges flags on repeat replies
    repeats_by_turn_detail = []
    for iid in panel_ids:
        turns = talk[arm][iid]
        seen_replies = []
        pid = pid_for[(arm, iid)]
        j1, j2 = claims_by_pid[pid]
        for ti in range(5):
            reply = turns[ti]["reply"]
            if reply in seen_replies:
                repeat_count += 1
                claims_on_repeats += j1[ti] + j2[ti]
            seen_replies.append(reply)
    results[arm]["repeat_replies_report"] = repeat_count
    results[arm]["claims_on_repeat_replies_report"] = claims_on_repeats

# claims by kind report already computed above (results[arm]["claims_by_kind"])

# ---------- mu-405 substring count per arm (ask_substring_report) ----------
# This checks the ask-turn reply for a literal substring match of the true fact value,
# as a crude "did it literally include the right words" check independent of judges.
# We need the true values from session1 for each item. mu-405's method: check if the
# ask-turn reply contains (case-insensitively) the substance of what was asked.
# Since PASSMARKS.md just says "mu-405's substring count per arm, kept for comparison"
# without giving exact algorithm here, and we don't have access to claude_mu405 script details,
# we will do a reasonable-effort substring check: does the ask-turn reply contain a substring
# match against ANY of the 3 session1 facts' key content (imprecise), OR skip this metric
# since we cannot verify the exact mu-405 algorithm without importing repo code.
# We will read the fit judge markdown "answer" field for comparison instead. For a *safe*
# recount, we skip inventing an unspecified substring algorithm; we'll flag this as N/A
# and rely on comparing against marks.json's reported ask_substring_report separately,
# noting we could not independently derive it without the exact algorithm.

print("\n=== RESULTS PER ARM ===")
for arm in ARMS:
    print(f"\n--- {arm} ---")
    for k, v in results[arm].items():
        print(f"  {k}: {v}")

# ---------- Marks ----------
C_N = results["N"]["C_two_judges"]
C_U0 = results["U0"]["C_two_judges"]
C_U1 = results["U1"]["C_two_judges"]

V_pass = C_U0 >= C_N + 10

L1_ratio_pass = C_U1 <= 0.5 * C_U0
L1_sign_pass = p_sign <= 0.05
L1_pass = L1_ratio_pass and L1_sign_pass

answer_U0 = results["U0"]["real_answers_both_judges"]
answer_U1 = results["U1"]["real_answers_both_judges"]
L2_pass = answer_U1 >= answer_U0

on_turn_U0 = results["U0"]["on_turn_non_ask_both_judges"]
on_turn_U1 = results["U1"]["on_turn_non_ask_both_judges"]
L3_pass = (on_turn_U1 >= on_turn_U0) and (on_turn_U1 >= 192)

PASS = V_pass and L1_pass and L2_pass and L3_pass
proved_wrong = C_U1 >= C_U0

if not V_pass:
    verdict = "INCONCLUSIVE"
elif PASS:
    verdict = "PASS"
elif proved_wrong:
    verdict = "proved wrong"
else:
    verdict = "FAIL"

print("\n=== MARKS ===")
print(f"V: C_U0={C_U0} >= C_N+10={C_N+10} -> {V_pass}")
print(f"L1: C_U1={C_U1} <= 0.5*C_U0={0.5*C_U0} -> ratio {L1_ratio_pass}; sign p={p_sign:.4f} <= 0.05 -> {L1_sign_pass}; L1={L1_pass}")
print(f"    sign test: fewer={fewer}, more={more}, ties={ties}")
print(f"L2: answer_U1={answer_U1} >= answer_U0={answer_U0} -> {L2_pass}")
print(f"L3: on_turn_U1={on_turn_U1} >= on_turn_U0={on_turn_U0} and >=192 -> {L3_pass}")
print(f"PASS = {PASS}")
print(f"proved_wrong (C_U1 >= C_U0) = {proved_wrong}")
print(f"VERDICT = {verdict}")

# ---------- answer goal of 30 (report only) ----------
print("\n=== Report: real answers vs goal of 30 ===")
for arm in ARMS:
    ra = results[arm]["real_answers_both_judges"]
    print(f"  {arm}: {ra} (>=30? {ra>=30})")

# Save full results to json for comparison
out = {
    "bad_rows": bad_rows,
    "arms": {},
    "marks": {
        "V": {"C_U0": C_U0, "C_N": C_N, "pass": V_pass},
        "L1": {
            "C_U1": C_U1, "C_U0": C_U0,
            "sign": {"U1_fewer": fewer, "U1_more": more, "p_one_sided": round(p_sign,4), "pass": L1_sign_pass},
            "ratio_pass": L1_ratio_pass,
            "pass": L1_pass,
        },
        "L2": {"answer_U1": answer_U1, "answer_U0": answer_U0, "pass": L2_pass},
        "L3": {"on_turn_U1": on_turn_U1, "on_turn_U0": on_turn_U0, "min": 192, "pass": L3_pass},
        "proved_wrong": proved_wrong,
        "verdict": verdict,
    },
    "report": {
        "U1_vs_N_claims_sign": {"U1_fewer": fewer_N, "U1_more": more_N, "p_one_sided": round(p_sign_N,4)},
        "answer_goal_30": {arm: results[arm]["real_answers_both_judges"] >= 30 for arm in ARMS},
    },
}
for arm in ARMS:
    out["arms"][arm] = results[arm]

with open("/tmp/claude-0/-home-user-learner/4d3f42a5-cfd2-59d7-9fb6-803bbe0862d0/scratchpad/recount407/my_results.json", "w") as f:
    json.dump(out, f, indent=1)

print("\nSaved my_results.json")
