"""Compact Part 3 tables for the report: worst case over base rates 10/30/50
(false pass = max over bases at true gain 0; power = min over bases)."""
import json
r = json.load(open("part3_power.json")); P = {**r["greedy"], **r["pass8"]}
def g(tag, n, b, gain, s, S, M): return P["%s|n%d|b%d|g%d|s%d|S%d|M%d" % (tag, n, b, gain, s, S, M)]
for tag, S in (("greedy", 2), ("greedy", 3), ("pass8_bound", 2), ("pass8_beta1", 2)):
    print("\n#### %s, %d seeds per arm" % (tag, S))
    print("| n | M | SD 3: false pass | power +5 | +10 | +15 | SD 5: false pass | power +5 | +10 | +15 |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for n in (128, 192, 256, 384, 512):
        for M in (8, 10, 12):
            row = []
            for s in (3, 5):
                row.append(max(g(tag, n, b, 0, s, S, M) for b in (10, 30, 50)))
                row += [min(g(tag, n, b, gn, s, S, M) for b in (10, 30, 50)) for gn in (5, 10, 15)]
            print("| %d | %d | %.1f%% | %.0f%% | %.0f%% | %.0f%% | %.1f%% | %.0f%% | %.0f%% | %.0f%% |" % (n, M, *(100 * x for x in row)))
