#!/usr/bin/env python3
"""
Independent recounter for gate g406b-L.
Written from scratch per task instructions -- does NOT import
scripts/claude_g406_count.py or scripts/claude_g406l_luna.py.
"""
import json
import collections

REPO = "/home/user/learner"

BEST_B = f"{REPO}/artifacts/claude-g406l-20260927/run2/best_b.jsonl"
RUN1_BEST_B = f"{REPO}/artifacts/claude-g406l-20260927/run/best_b.jsonl"
KEY = f"{REPO}/artifacts/claude-mu405b-20260926/judge/keys/claims_key.json"
JUDGE_OUT_TMPL = f"{REPO}/artifacts/claude-mu405b-20260926/judge/out/claims_j{{}}.jsonl"
JUDGE_PKT_TMPL = f"{REPO}/artifacts/claude-mu405b-20260926/judge/packets/claims_j{{}}.jsonl"


def load_jsonl(path):
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def main():
    # ---------- Load Luna (labeller) rows ----------
    luna_rows = load_jsonl(BEST_B)
    luna_by_pid = {}
    dup_pids = []
    for r in luna_rows:
        if r["pid"] in luna_by_pid:
            dup_pids.append(r["pid"])
        luna_by_pid[r["pid"]] = r
    assert not dup_pids, f"duplicate pids in best_b: {dup_pids}"

    total_packets_luna = len(luna_rows)

    # ---------- Load truth: judge packets (for turn counts) ----------
    packet_turns = {}  # pid -> n turns
    packet_seen_files = collections.defaultdict(list)
    for i in range(1, 9):
        for row in load_jsonl(JUDGE_PKT_TMPL.format(i)):
            pid = row["pid"]
            n = len(row["conversation"])
            if pid in packet_turns and packet_turns[pid] != n:
                raise AssertionError(f"packet turn mismatch for {pid}")
            packet_turns[pid] = n
            packet_seen_files[pid].append(i)

    # ---------- Load truth: judge output flags (two rows per pid) ----------
    judge_flags = collections.defaultdict(list)  # pid -> list of flags-lists (should end up length 2)
    for i in range(1, 9):
        for row in load_jsonl(JUDGE_OUT_TMPL.format(i)):
            pid = row["pid"]
            judge_flags[pid].append(row["flags"])

    # sanity: every pid has exactly two judge rows
    bad_judge_counts = {pid: len(v) for pid, v in judge_flags.items() if len(v) != 2}
    assert not bad_judge_counts, f"pids without exactly 2 judge rows: {bad_judge_counts}"

    # sanity: judge pid set == packet pid set == key pid set == luna pid set
    key = json.load(open(KEY))
    key_pids = set(key.keys())
    judge_pids = set(judge_flags.keys())
    packet_pids = set(packet_turns.keys())
    luna_pids = set(luna_by_pid.keys())
    assert key_pids == judge_pids == packet_pids, (
        "pid set mismatch across key/judge/packets",
        key_pids ^ judge_pids, key_pids ^ packet_pids,
    )
    assert luna_pids == key_pids, ("luna pid set differs from key/judge/packets pid set",
                                    luna_pids ^ key_pids)

    # sanity: judge flags length == packet turn count for each pid, for both judge rows
    for pid, flag_lists in judge_flags.items():
        for fl in flag_lists:
            assert len(fl) == packet_turns[pid], f"judge flags len mismatch {pid}"

    # ---------- usable packets ----------
    # "A packet counts as usable when ok is true and flags has as many entries
    #  as the packet's conversation has turns."
    usable_pids = []
    unusable = []
    for pid, r in luna_by_pid.items():
        n_turns = packet_turns[pid]
        ok = r.get("ok") is True
        flags_len_match = len(r.get("flags", [])) == n_turns
        if ok and flags_len_match:
            usable_pids.append(pid)
        else:
            unusable.append((pid, ok, len(r.get("flags", [])), n_turns))

    usable_packets = len(usable_pids)

    # ---------- replies: sum of turns over ALL packets (not just usable) ----------
    total_replies = sum(packet_turns[pid] for pid in luna_by_pid.keys())
    # should equal sum over all 240 known packets too
    total_replies_all_key = sum(packet_turns[pid] for pid in key_pids)

    # ---------- judges' both/either per reply, over ALL packets (truth is independent of Luna's usability) ----------
    both_flagged = 0
    either_flagged = 0
    per_reply_judge = {}  # pid -> list of (j1flag, j2flag) per turn index
    for pid in key_pids:
        fl_a, fl_b = judge_flags[pid]
        n = packet_turns[pid]
        per_turn = []
        for idx in range(n):
            a = fl_a[idx]
            b = fl_b[idx]
            both = 1 if (a == 1 and b == 1) else 0
            either = 1 if (a == 1 or b == 1) else 0
            both_flagged += both
            either_flagged += either
            per_turn.append((a, b, both, either))
        per_reply_judge[pid] = per_turn

    base_either_rate = either_flagged / total_replies

    # ---------- Luna flags (only counted where Luna has a flag for that reply -- i.e. over usable packets,
    # since only usable packets have flags arrays that line up with turns) ----------
    # For G1/G2/G3 and everything "Luna flags ..." -- these are about replies Luna actually labelled,
    # i.e. usable packets' replies (1200 replies exist in truth, but Luna's usable set may be fewer).
    luna_total_flags = 0
    luna_replies_considered = 0  # replies within usable Luna packets
    for pid in usable_pids:
        r = luna_by_pid[pid]
        for f_ in r["flags"]:
            luna_replies_considered += 1
            if f_ == 1:
                luna_total_flags += 1

    # Luna flags among both-flagged replies (G1 numerator/denominator), restricted to usable packets
    both_flagged_usable = 0
    luna_catches_of_both = 0
    either_flagged_usable = 0
    luna_catches_of_either = 0  # not directly asked but useful
    clean_luna_replies = 0  # Luna calls clean (flag==0)
    either_among_luna_clean = 0  # of Luna-clean replies, how many judges' either flagged
    only_one_judge_flagged_usable = 0
    luna_flags_on_only_one = 0
    luna_flagged_replies_either_count = 0  # among Luna-flagged replies, how many are judges' either-flagged (for "proved wrong" check)

    for pid in usable_pids:
        r = luna_by_pid[pid]
        turns = per_reply_judge[pid]
        for idx, (a, b, both, either) in enumerate(turns):
            luna_flag = r["flags"][idx]
            if both:
                both_flagged_usable += 1
                if luna_flag == 1:
                    luna_catches_of_both += 1
            if either:
                either_flagged_usable += 1
                if luna_flag == 1:
                    luna_catches_of_either += 1
            only_one = 1 if (either and not both) else 0
            if only_one:
                only_one_judge_flagged_usable += 1
                if luna_flag == 1:
                    luna_flags_on_only_one += 1
            if luna_flag == 0:
                clean_luna_replies += 1
                if either:
                    either_among_luna_clean += 1
            if luna_flag == 1:
                if either:
                    luna_flagged_replies_either_count += 1

    replies_usable = luna_replies_considered  # == sum turns over usable packets

    G1 = (luna_catches_of_both / both_flagged_usable) if both_flagged_usable else None
    G2 = (either_among_luna_clean / clean_luna_replies) if clean_luna_replies else None
    G3 = clean_luna_replies / replies_usable if replies_usable else None
    either_rate_among_luna_flagged = (luna_flagged_replies_either_count / luna_total_flags) if luna_total_flags else None

    V = usable_packets >= 228

    G1_pass = G1 is not None and G1 >= 0.70
    G2_pass = G2 is not None and G2 <= 0.07
    G3_pass = G3 is not None and G3 >= 0.50
    PASS = V and G1_pass and G2_pass and G3_pass
    proved_wrong = either_rate_among_luna_flagged is not None and either_rate_among_luna_flagged <= 0.14

    # ---------- Per-arm breakdown ----------
    arms = ["N", "W", "U", "H"]
    arm_stats = {a: {
        "replies": 0,
        "luna_flags": 0,
        "judge_either": 0,
        "judge_both": 0,
        "luna_catches_of_both": 0,
        "only_one_judge_flagged": 0,
        "luna_flags_on_only_one": 0,
    } for a in arms}

    for pid in usable_pids:
        arm = key[pid]["arm"]
        r = luna_by_pid[pid]
        turns = per_reply_judge[pid]
        st = arm_stats[arm]
        for idx, (a, b, both, either) in enumerate(turns):
            luna_flag = r["flags"][idx]
            st["replies"] += 1
            if luna_flag == 1:
                st["luna_flags"] += 1
            if either:
                st["judge_either"] += 1
            if both:
                st["judge_both"] += 1
                if luna_flag == 1:
                    st["luna_catches_of_both"] += 1
            only_one = 1 if (either and not both) else 0
            if only_one:
                st["only_one_judge_flagged"] += 1
                if luna_flag == 1:
                    st["luna_flags_on_only_one"] += 1

    # ---------- print everything ----------
    print("=" * 70)
    print("SECTION 1: base numbers (over ALL 240 packets / 1200 truth replies)")
    print("=" * 70)
    print(f"packets total (key/judge/packets union):      {len(key_pids)}")
    print(f"packets total (luna best_b rows):              {total_packets_luna}")
    print(f"usable packets (Luna ok & flags-len matches):   {usable_packets}")
    if unusable:
        print(f"  unusable pids: {unusable}")
    print(f"replies (sum turns, all packets, truth side):  {total_replies_all_key}")
    print(f"replies both judges flagged (all packets):     {both_flagged}")
    print(f"replies either judge flagged (all packets):    {either_flagged}")
    print(f"base either-rate (all packets):                 {base_either_rate:.6f}  ({either_flagged}/{total_replies_all_key})")

    print()
    print("=" * 70)
    print("SECTION 2: Luna marks, restricted to USABLE packets")
    print("=" * 70)
    print(f"replies in usable packets:                      {replies_usable}")
    print(f"Luna flags (usable packets):                    {luna_total_flags}")
    print(f"both-flagged replies (usable packets):          {both_flagged_usable}")
    print(f"Luna catches of both-flagged (numerator G1):    {luna_catches_of_both}")
    print(f"G1 = catches/both-flagged:                      {G1}")
    print(f"Luna-clean replies (flag==0, usable packets):   {clean_luna_replies}")
    print(f"  of those, either-flagged by judges:           {either_among_luna_clean}")
    print(f"G2 = either-among-clean / clean:                {G2}")
    print(f"G3 = clean / all usable replies:                {G3}")
    print(f"V = usable_packets >= 228:                      {V}  (usable_packets={usable_packets})")
    print(f"either-rate among Luna-flagged replies:         {either_rate_among_luna_flagged}")
    print(f"  proved wrong (<=0.14)?                        {proved_wrong}")
    print(f"only-one-judge-flagged replies (usable):        {only_one_judge_flagged_usable}")
    print(f"  of those, Luna flags:                         {luna_flags_on_only_one}")

    print()
    print("=" * 70)
    print("SECTION 3: per-arm (usable packets only)")
    print("=" * 70)
    for a in arms:
        st = arm_stats[a]
        print(f"Arm {a}: replies={st['replies']} luna_flags={st['luna_flags']} "
              f"judge_either={st['judge_either']} judge_both={st['judge_both']} "
              f"luna_catches_of_both={st['luna_catches_of_both']} "
              f"only_one_judge_flagged={st['only_one_judge_flagged']} "
              f"luna_flags_on_only_one={st['luna_flags_on_only_one']}")

    print()
    print("=" * 70)
    print("SECTION 4: verdict")
    print("=" * 70)
    print(f"V:  {V}")
    print(f"G1 pass (>=0.70): {G1_pass}  (G1={G1})")
    print(f"G2 pass (<=0.07): {G2_pass}  (G2={G2})")
    print(f"G3 pass (>=0.50): {G3_pass}  (G3={G3})")
    print(f"PASS = V and G1 and G2 and G3:  {PASS}")
    print(f"proved wrong (either-rate among Luna-flagged <= 0.14): {proved_wrong}  (rate={either_rate_among_luna_flagged})")

    # ---------- compare run/best_b.jsonl (220 partial) to run2/best_b.jsonl matching rows ----------
    print()
    print("=" * 70)
    print("SECTION 5: run vs run2 partial comparison")
    print("=" * 70)
    run1_rows = {row["pid"]: row for row in load_jsonl(RUN1_BEST_B)}
    print(f"run/best_b.jsonl row count: {len(run1_rows)}")
    mismatches = []
    missing_from_run2 = []
    for pid, r1 in run1_rows.items():
        if pid not in luna_by_pid:
            missing_from_run2.append(pid)
            continue
        r2 = luna_by_pid[pid]
        if r1 != r2:
            mismatches.append((pid, r1, r2))
    print(f"pids in run/ missing from run2/: {missing_from_run2}")
    print(f"rows differing between run/ and run2/ (matching pids): {len(mismatches)}")
    for m in mismatches[:20]:
        print("  DIFF:", m)
    print(f"CONCLUSION: run/'s {len(run1_rows)} rows {'EQUAL' if not mismatches and not missing_from_run2 else 'DO NOT ALL EQUAL'} the matching rows of run2/")

    # dump machine-readable summary for later comparison against run2/verdict_b.json and arms_b.json
    summary = {
        "packets_total": len(key_pids),
        "usable_packets": usable_packets,
        "replies_all": total_replies_all_key,
        "replies_usable": replies_usable,
        "both_flagged_all": both_flagged,
        "either_flagged_all": either_flagged,
        "base_either_rate_all": base_either_rate,
        "luna_flags_usable": luna_total_flags,
        "both_flagged_usable": both_flagged_usable,
        "luna_catches_of_both_usable": luna_catches_of_both,
        "G1": G1,
        "clean_luna_replies": clean_luna_replies,
        "either_among_luna_clean": either_among_luna_clean,
        "G2": G2,
        "G3": G3,
        "V": V,
        "either_rate_among_luna_flagged": either_rate_among_luna_flagged,
        "proved_wrong": proved_wrong,
        "PASS": PASS,
        "arms": arm_stats,
        "only_one_judge_flagged_usable": only_one_judge_flagged_usable,
        "luna_flags_on_only_one_usable": luna_flags_on_only_one,
    }
    with open("/tmp/claude-0/-home-user-learner/4d3f42a5-cfd2-59d7-9fb6-803bbe0862d0/scratchpad/recount406l/my_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print()
    print("Wrote my_summary.json")


if __name__ == "__main__":
    main()
