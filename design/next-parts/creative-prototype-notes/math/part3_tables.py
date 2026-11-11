"""Print Part 3 tables and the (n, M, seeds) search from part3_power.json."""
import json, sys
r = json.load(open("part3_power.json"))
P = {**r["greedy"], **r["pass8"]}
def g(tag, n, b, gain, s, S, M): return P["%s|n%d|b%d|g%d|s%d|S%d|M%d" % (tag, n, b, gain, s, S, M)]
for tag in ("greedy", "pass8_bound", "pass8_beta1", "pass8_beta4"):
    for S in (2, 3):
        for s in (3, 5):
            print("\n### %s, %d seeds per arm, between-seed SD %d points" % (tag, S, s))
            print("| n | M | false pass b10 | b30 | b50 | power +15 b10 | b30 | b50 | power +10 worst | power +5 worst |")
            print("|---|---|---|---|---|---|---|---|---|---|")
            for n in (128, 192, 256, 384, 512):
                for M in (8, 10, 12):
                    fp = [g(tag, n, b, 0, s, S, M) for b in (10, 30, 50)]
                    pw = [g(tag, n, b, 15, s, S, M) for b in (10, 30, 50)]
                    p10 = min(g(tag, n, b, 10, s, S, M) for b in (10, 30, 50))
                    p5 = min(g(tag, n, b, 5, s, S, M) for b in (10, 30, 50))
                    ok = max(fp) <= 0.05 and min(pw) >= 0.80
                    print("| %d | %d | %.1f%% | %.1f%% | %.1f%% | %.0f%% | %.0f%% | %.0f%% | %.0f%% | %.0f%% |%s" % (
                        n, M, *(100 * x for x in fp), *(100 * x for x in pw), 100 * p10, 100 * p5, " OK" if ok else ""))
print("\nshortcut checks", json.dumps(r["pass8_shortcut_checks"]))
print("variance", json.dumps(r["pass8_variance_vs_bound"]))
