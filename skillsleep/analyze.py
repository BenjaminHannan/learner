"""Pass marks from out/summary.jsonl (runs locally on downloaded out/ too). PREREG.md (arms A0/A1/A2) or PREREG-2.md (A0 and C1-C3 with seeds s1, s2).
Usage: python3 analyze.py [path/to/summary.jsonl]     (train_info_*.json and data/build_stats.json are read from the same folder when present)
Rate = mean over tasks of the per-task mean pass (all trials of all seeds of the arm, tasks present in both arms of a comparison). Only real() sims count:
infra/429 failures are left out (per_task_real) and their number is reported. Test = two-sided paired sign-flip permutation on the per-task differences,
10,000 random flips, seed 0, p = (1 + #{|flipped mean| >= |observed|}) / (1 + 10000)."""
import json, os, re, sys
import numpy as np

path = sys.argv[1] if len(sys.argv) > 1 else "out/summary.jsonl"; DIR = os.path.dirname(os.path.abspath(path))
S = {}
for l in open(path):
    if l.strip():
        r = json.loads(l); S[(r["arm"], r["domain"])] = r  # a later line for the same arm+domain replaces an earlier one
f = lambda v, s="{:.1f}": "n/a" if v is None else s.format(v)
pct = lambda v: None if v is None else 100 * v


def tasks(arm, dom):  # {task: [0/1 per trial]} of real sims (run-1 lines without per_task_real: all sims)
    r = S.get((arm, dom))
    return {} if r is None else {t: v for t, v in (r.get("per_task_real") or r["per_task"]).items() if v}


def pooled(arms, dom):  # trials of all the arms' runs (seeds) joined per task
    out = {}
    for a in arms:
        for t, v in tasks(a, dom).items():
            out.setdefault(t, []).extend(v)
    return out


def rate(arms, dom):
    p = pooled(arms, dom)
    return None if not p else 100 * np.mean([np.mean(v) for v in p.values()])


def compare(a, b, dom):
    """arms-list A minus arms-list B (points) and p over tasks present in both; None if one side is missing."""
    x, y = pooled(a, dom), pooled(b, dom); ts = sorted(set(x) & set(y))
    if not ts:
        return None
    x = {t: np.mean(v) for t, v in x.items()}; y = {t: np.mean(v) for t, v in y.items()}
    d = np.array([x[t] - y[t] for t in ts]); rng = np.random.default_rng(0)
    flips = rng.choice([-1.0, 1.0], size=(10000, len(d))); obs = abs(d.mean())
    p = (1 + int((np.abs((flips * d).mean(1)) >= obs - 1e-12).sum())) / 10001
    return {"delta": 100 * d.mean(), "p": p, "n": len(ts)}


def counts(arm, dom):
    r = S.get((arm, dom)); return None if r is None else (sum(map(sum, tasks(arm, dom).values())), sum(map(len, tasks(arm, dom).values())), r.get("not_real", 0))


def verdict(name, ok_, txt):
    print(f"{name}: {'n/a (missing data)' if ok_ is None else ('PASS' if ok_ else 'FAIL')} - {txt}")


def day_lines():
    for k in [k for k in S if k[0] in ("day", "fix")]:
        r = S[k]; a = r.get("ask") or {}
        print(f"\n{k[0]} {k[1]}: {r['pass']}/{r['sims']} runs pass, {r.get('not_real', 0)} not real" +
              (f"; ask rate {f(pct(a.get('rate')))}% of {a.get('writes')} writes, {f(a.get('q_per_sim'), '{:.2f}')} agent questions per sim" if a else ""))
    for p in (os.path.join(DIR, "data", "build_stats.json"), os.path.join(DIR, "data_build_stats.json")):
        if os.path.exists(p):
            b = json.load(open(p)); print("night data:", {k: b[k] for k in b if k.startswith(("pos", "pairs", "negs", "sft_", "dropped", "pair_"))}); break


# ---------------- Skill-Sleep 1 ----------------
def report_v1():
    print("| arm | retail test | airline test | ARC-Easy |\n|---|---|---|---|")
    for arm in ("A0", "A1", "A2"):
        cells = []
        for dom in ("retail_test", "airline_test", "arc_easy"):
            c = counts(arm, dom); cells.append("n/a" if c is None else f"{rate([arm], dom):.1f}% ({c[0]}/{c[1]}" + (f", {c[2]} excluded)" if c[2] else ")"))
        print(f"| {arm} | " + " | ".join(cells) + " |")
    day_lines()
    C = {n: compare([a], [b], d) for n, (a, b, d) in {"r20": ("A2", "A0", "retail_test"), "r21": ("A2", "A1", "retail_test"), "r10": ("A1", "A0", "retail_test"),
                                                     "a20": ("A2", "A0", "airline_test"), "c20": ("A2", "A0", "arc_easy")}.items()}
    print("\n| comparison | delta (points) | p | tasks |\n|---|---|---|---|")
    for n, lab in [("r20", "retail A2 - A0"), ("r21", "retail A2 - A1"), ("r10", "retail A1 - A0"), ("a20", "airline A2 - A0"), ("c20", "ARC-Easy A2 - A0")]:
        c = C[n]; print(f"| {lab} | " + ("n/a | n/a | n/a" if c is None else f"{c['delta']:+.1f} | {c['p']:.4f} | {c['n']}") + " |")
    c = C["r20"]; verdict("P1 sleep teaches skill", None if c is None else (c["delta"] >= 6 and c["p"] < 0.05), "A2 retail test >= A0 + 6 points and p < 0.05")
    c = C["r21"]
    if c is None:
        verdict("P2 bad examples add something", None, "A2 >= A1 + 4 points and p < 0.05")
    else:
        verdict("P2 bad examples add something", c["delta"] >= 4 and c["p"] < 0.05, "A2 >= A1 + 4 points and p < 0.05")
        if c["delta"] >= 4 and c["p"] >= 0.05:
            print("   (gap >= 4 with p >= 0.05: suggested, not shown)")
    c = C["a20"]; verdict("P3 skills carry over (label only)", None if c is None else c["delta"] >= 0, "A2 airline test >= A0")
    a, k = C["a20"], C["c20"]
    verdict("P4 no harm", None if a is None or k is None else (a["delta"] >= -7.5 - 1e-9 and k["delta"] >= -2 - 1e-9), "A2 airline >= A0 - 7.5 points and ARC-Easy >= A0 - 2 points")
    if C["r20"] is not None and C["r21"] is not None:
        print("Wrong if A2 <= A0 on retail test:", "YES (sleep on skills does nothing)" if C["r20"]["delta"] <= 0 else "no")
        print("Wrong if A2 < A1 - 4:", "YES (bad examples hurt)" if C["r21"]["delta"] < -4 else "no")
    r = rate(["A0"], "retail_test")
    if r is not None:
        print(f"Day-1 sanity: A0 retail test {r:.1f}% vs Swap-1 64% -> gap {r - 64:+.1f} points" + ("  > 15: stack changed, report with caveat" if abs(r - 64) > 15 else "  (within 15)"))


# ---------------- Skill-Sleep 2 ----------------
def seeds(c):
    return sorted(a for a in {k[0] for k in S} if re.fullmatch(c + r"s\d+", a))


def ask(arm, dom="retail_test"):
    a = (S.get((arm, dom)) or {}).get("ask"); return a


def ask_rate(arms, dom="retail_test"):  # pooled over the arm's seeds
    xs = [ask(a, dom) for a in arms]; xs = [x for x in xs if x]; w = sum(x["writes"] for x in xs)
    return None if not w else sum(x["asked"] for x in xs) / w


def train_info(arm):
    p = os.path.join(DIR, f"train_info_{arm}.json"); return json.load(open(p)) if os.path.exists(p) else None


def report_v2():
    arms = {"A0": ["A0"], **{c: seeds(c) for c in ("C1", "C2", "C3")}}
    print("| arm | retail test | airline test | ARC-Easy | ask rate (retail) | agent questions / sim | excluded sims (retail, airline) |\n|---|---|---|---|---|---|---|")
    for arm in ["A0"] + [a for c in ("C1", "C2", "C3") for a in seeds(c)]:
        cells = []
        for dom in ("retail_test", "airline_test", "arc_easy"):
            c = counts(arm, dom); cells.append("n/a" if c is None else f"{rate([arm], dom):.1f}% ({c[0]}/{c[1]})")
        a = ask(arm) or {}; ex = [(counts(arm, d) or (0, 0, "?"))[2] for d in ("retail_test", "airline_test")]
        print(f"| {arm} | " + " | ".join(cells) + f" | {f(pct(a.get('rate')))}% ({a.get('asked')}/{a.get('writes')} writes) | {f(a.get('q_per_sim'), '{:.2f}')} | {ex[0]}, {ex[1]} |")
    print("\nPooled over seeds (per-task means over seeds and trials):")
    print("| arm | seeds | retail test | per seed |\n|---|---|---|---|")
    for c, a in arms.items():
        print(f"| {c} | {len(a)} | {f(rate(a, 'retail_test'))}% | " + ", ".join(f"{x}: {f(rate([x], 'retail_test'))}" for x in a) + " |")
    day_lines()

    def cmp(name, a, b, dom="retail_test"):
        c = compare(arms[a], arms[b], dom)
        if c is None:
            return None
        per = []  # same-seed deltas (A0 has one run, so every seed is compared with it)
        for x in arms[a]:
            ref = [b] if b == "A0" else [b + x[len(a):]]
            r = compare([x], ref, dom); per.append(None if r is None else r["delta"])
        c["per_seed"] = per; c["both"] = len(per) >= 2 and all(d is not None and d > 0 for d in per)
        print(f"| {name} | {c['delta']:+.1f} | {c['p']:.4f} | {c['n']} | " + ", ".join(f(d, "{:+.1f}") for d in per) + f" | {'yes' if c['both'] else 'NO' if len(per) >= 2 else 'n/a (<2 seeds)'} |")
        return c
    print("\n| comparison (retail test) | delta (points) | p | tasks | per-seed deltas | both seeds > 0 |\n|---|---|---|---|---|---|")
    q1, q2, q3 = cmp("C2 - A0", "C2", "A0"), cmp("C2 - C1", "C2", "C1"), cmp("C3 - C2", "C3", "C2")
    cmp("C1 - A0", "C1", "A0"); cmp("C3 - A0", "C3", "A0")

    def q(name, c, need, txt, suggest=False):
        if c is None:
            return verdict(name, None, txt)
        good = c["delta"] >= need and c["p"] < 0.05
        verdict(name, good and c["both"], txt + ("" if c["both"] else "; not in both seeds" if good else ""))
        if suggest and c["delta"] >= need and c["p"] >= 0.05:
            print("   (gap >= 4 with p >= 0.05: suggested, not shown)")
    print()
    q("Q1 longer night helps", q1, 6, "C2 >= A0 + 6 points, p < 0.05, both seeds")
    q("Q2 bad examples help at dose", q2, 4, "C2 >= C1 + 4 points, p < 0.05, both seeds", True)
    q("Q3 near-miss pairs help", q3, 4, "C3 >= C2 + 4 points, p < 0.05, both seeds", True)
    for a in seeds("C3"):
        t = train_info(a)
        if t is None:
            print(f"Q4 {a}: n/a (no train_info)"); continue
        sat = t.get("dpo_sat_step"); half = t["opt_steps"] / 2
        print(f"Q4 pairs not saturated ({a}, label only): " + ("n/a" if "dpo_sat_step" not in t else
              f"{'NOT saturated in the first half' if sat is None or sat > half else 'SATURATED early'} (first 10-step run at acc >= 0.95 " + ("never happened" if sat is None else f"starts at step {sat}") + f", half = {half:.0f}; "
              f"{t.get('fork_pairs')} fork pairs + {t.get('pairs')} plain pairs)"))
    print("\nHarm checks (each trained arm-seed): airline >= A0 - 7.5, ARC-Easy >= A0 - 2, ask rate (retail) >= half of A0's")
    print("| arm | airline vs A0 | ARC vs A0 | ask rate vs A0 | result |\n|---|---|---|---|---|")
    a0 = ask_rate(["A0"]); harm = {}
    for c in ("C1", "C2", "C3"):
        for x in seeds(c):
            al, ar = compare([x], ["A0"], "airline_test"), compare([x], ["A0"], "arc_easy"); r = ask_rate([x])
            ok_ = [al is None or al["delta"] >= -7.5 - 1e-9, ar is None or ar["delta"] >= -2 - 1e-9, r is None or a0 is None or r >= a0 / 2 - 1e-12]
            miss = al is None or ar is None or r is None or a0 is None
            harm[x] = all(ok_) and (None if miss else True) if all(ok_) else False
            print(f"| {x} | {f(al and al['delta'], '{:+.1f}')} | {f(ar and ar['delta'], '{:+.1f}')} | {f(pct(r))}% vs {f(pct(a0))}% | "
                  f"{'ok' if all(ok_) else 'HARM: ' + ', '.join(n for n, g in zip(('airline', 'ARC', 'ask'), ok_) if not g)}{' (incomplete data)' if miss else ''} |")
    for c in ("C1", "C2", "C3"):
        if seeds(c):
            h = [harm[x] for x in seeds(c)]
            verdict(f"No harm {c}", False if False in h else None if None in h else True, "every seed passes the three harm checks (n/a: a check had no data)")
    if q1 is not None:
        print("Wrong if C2 <= A0 (a longer night does nothing):", "YES" if q1["delta"] <= 0 else "no")
    if q3 is not None:
        print("Wrong if C3 < C2 - 4 (fork pairs hurt):", "YES" if q3["delta"] < -4 else "no")
    r = rate(["A0"], "retail_test")
    if r is not None:
        print(f"Day-1 sanity: A0 retail test {r:.1f}% vs Skill-Sleep 1 A0 63.7% -> gap {r - 63.7:+.1f} points" + ("  > 15: stack changed, report with caveat" if abs(r - 63.7) > 15 else "  (within 15)"))


if any(a.startswith("C") for a, _ in S):
    report_v2()
else:
    report_v1()
