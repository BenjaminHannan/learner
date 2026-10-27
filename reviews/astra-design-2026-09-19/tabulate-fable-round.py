"""Analysis only: standard-library tabulation of saved JSON and exact power arithmetic.

No project imports, model/checkpoint/tensor reads, tests, training, or network.
Creates one new evidence file exclusively; refuses to overwrite it.
"""
import collections
import functools
import hashlib
import json
import math
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).with_name("fable-round-evidence.json")
SUITE = ROOT / "artifacts/claude-pairsuite-20260919"
inputs = {}


def read(path):
    data = path.read_bytes()
    inputs[str(path.relative_to(ROOT))] = hashlib.sha256(data).hexdigest()
    return data.decode()


rows = [json.loads(line) for line in read(SUITE / "rows.jsonl").splitlines()]
manifest = json.loads(read(SUITE / "manifest.json"))
read(SUITE / "table.txt")
cells = list(manifest["cells"])
groups = collections.defaultdict(list)
runs = {}
for row in rows:
    group = str(Path(row["dir"]).relative_to(ROOT)).removesuffix("/ckpt")
    groups[group].append(row)
    path = Path(row["dir"]).parent / "runs" / (row["name"] + ".json")
    runs[row["ckpt"]] = json.loads(read(path))


def causal(row):
    return min(row["counts"][cells[3]], row["counts"][cells[4]]) / 1024


def learned(row):
    return row["counts"][cells[0]] >= 1536


def tail(n, k, p):
    return sum(math.comb(n, j) * p**j * (1-p)**(n-j) for j in range(k, n+1))


@functools.lru_cache(None)
def critical(d):
    # Integer comparison implements an exact one-sided alpha=1/20 test.
    return next((g for g in range(d+1)
                 if 20 * sum(math.comb(d, j) for j in range(g, d+1)) <= 2**d), d+1)


def power(n, gain, loss):
    # Exact finite-binomial summation, evaluated in double precision.
    discordance = gain + loss
    if discordance == 0:
        return 0.0
    return sum(math.comb(n, d) * discordance**d * (1-discordance)**(n-d)
               * tail(d, max(critical(d), math.ceil((d + n/10 - 1e-10)/2)),
                      gain/discordance) for d in range(n+1))


summary = {}
for group, rs in groups.items():
    js = [runs[r["ckpt"]] for r in rs]
    result = {
        "n": len(rs), "G": sum(r["G"] for r in rs),
        "fresh_stuck_c1_lt_1536": sum(not learned(r) for r in rs),
        "old_stuck_onehop_lt_384": sum(j["validation"]["fixed_K4"]["one_hop"]["correct"] < 384 for j in js),
        "causal_3pp_headroom": sum(causal(r) <= .97 for r in rs),
        "causal_high_ge_90_low_le_20_middle": [sum(causal(r) >= .9 for r in rs),
            sum(causal(r) <= .2 for r in rs), sum(.2 < causal(r) < .9 for r in rs)],
        "fresh_onehop_mean": statistics.mean(r["counts"][cells[0]]/2048 for r in rs),
        "old_READS_mean": statistics.mean(j["validation"]["gold_read_K2_no_fetch"]["two_hop_trained_rel"]["correct"]/341 for j in js),
        "hardware": [list(x) for x in sorted(set((j.get("gpu_name"), j.get("torch_version"), j.get("autocast")) for j in js))],
        "train_flops_range": [min(j["train_report"]["flops"] for j in js), max(j["train_report"]["flops"] for j in js)],
        "strata": {},
    }
    for label, subset in [("learned", [r for r in rs if learned(r)]),
                          ("learned_fail_G", [r for r in rs if learned(r) and not r["G"]])]:
        s = {"n_seeds": len(subset), "denominator_per_request": 2048*len(subset)}
        s["practised_median"] = statistics.median(r["counts"][cells[1]]/2048 for r in subset) if subset else None
        for request in ["request1", "request2", "request3"]:
            counts = collections.Counter()
            for r in subset:
                counts.update(r["cells"][cells[2]]["diagnostics"]["by_request"][request]["classes"])
            s[request] = {"counts": dict(counts), "rates_all_questions":
                {k: v/(2048*len(subset)) for k, v in counts.items()} if subset else {}}
        result["strata"][label] = s
    summary[group] = result

comparisons = {}
for family in ["claude-keypool-20260919", "claude-keypool-relcut-20260919"]:
    a = {r["train_seed"]: r for r in groups["artifacts/" + family + "/control"]}
    b = {r["train_seed"]: r for r in groups["artifacts/" + family + "/keypool"]}
    rules = {
        "G_gains": lambda x, y: not x["G"] and y["G"],
        "G_losses": lambda x, y: x["G"] and not y["G"],
        "fresh_stuck_rescued_to_G": lambda x, y: not learned(x) and y["G"],
        "c4_3pp_wins": lambda x, y: y["counts"][cells[3]]-x["counts"][cells[3]] >= 31,
        "c4_3pp_losses": lambda x, y: x["counts"][cells[3]]-y["counts"][cells[3]] >= 31,
        "causal_3pp_wins": lambda x, y: causal(y)-causal(x) >= .03,
        "causal_3pp_losses": lambda x, y: causal(x)-causal(y) >= .03,
    }
    result = {k: [s for s in sorted(a) if fn(a[s], b[s])] for k, fn in rules.items()}
    g, l = len(result["G_gains"]), len(result["G_losses"])
    result["descriptive_paired_G_p"] = tail(g+l, g, .5) if g+l else 1.0
    result["paired_seeds"] = sorted(a.keys() & b.keys())
    comparisons[family] = result

cross = {}
for old, new in [("claude-long-20260919", "claude-keypool-20260919"),
                 ("claude-relcut-long-20260919", "claude-keypool-relcut-20260919")]:
    a = {r["train_seed"]: r for r in groups["artifacts/" + old]}
    b = {r["train_seed"]: r for r in groups["artifacts/" + new + "/control"]}
    cross[old] = {"G_flips": [s for s in sorted(a) if a[s]["G"] != b[s]["G"]],
        "fresh_stuck_flips": [s for s in sorted(a) if learned(a[s]) != learned(b[s])],
        "causal_examples": {s: [causal(a[s]), causal(b[s])] for s in [0, 1]}}

source_audit = {}
for name, digest in manifest["generator_sources"].items():
    path = ROOT / name if not name.startswith("frozen/") else ROOT / "archive/opus-ovn-20260918-235851" / name
    read(path)
    actual = inputs[str(path.relative_to(ROOT))]
    source_audit[name] = {"manifest": digest, "current": actual, "matches": actual == digest}
for path in sorted((ROOT / "design/v3").glob("*.md")):
    read(path)

scenarios = {}
for name, gain, loss in [("55_to_85_monotone", .30, 0), ("55_to_85_independent", .3825, .0825),
                         ("55_to_75_independent", .3375, .1375)]:
    scenarios[name] = {"gain_probability": gain, "loss_probability": loss,
        "power_primary_only": {n: power(n, gain, loss) for n in [16, 32, 34, 40, 64, 79, 80]},
        "first_n_at_least_80pct": next(n for n in range(5, 151) if power(n, gain, loss) >= .8)}

evidence = {
    "status": "shown: tabulation of saved records and mathematical arithmetic, not new model evidence",
    "limits": ["No checkpoints or tensor datasets read; integrity flags are saved assertions.",
               "Historical shared data/evaluation panels are not the proposed independent-seed certificate.",
               "Current first-card helper source does not match generator manifest.",
               "Power assumes independent seed pairs and stated joint gain/loss probabilities; excludes safeguards."],
    "n_rows": len(rows), "duplicate_ckpt_rows": len(rows)-len({r["ckpt"] for r in rows}),
    "row_manifest_hash_mismatches": sum(r["manifest_sha256"] != inputs["artifacts/claude-pairsuite-20260919/manifest.json"] for r in rows),
    "recomputed_G_disagreements": sum(r["G"] != all(r["counts"][c] >= manifest["cells"][c]["cutoff"] for c in cells) for r in rows),
    "count_cell_disagreements": sum(r["counts"][c] != r["cells"][c]["count"] for r in rows for c in cells),
    "saved_integrity_pass_counts": {k: sum(bool(r["integrity"][k]["pass"]) for r in rows)
                                   for k in ["own_fixed_parity", "label_perturbation", "world_isolation"]},
    "saved_weights_unchanged": sum(r["integrity"]["weights_unchanged"] for r in rows),
    "run_json_checkpoint_hash_matches": sum(r["sha256"] == runs[r["ckpt"]].get("ckpt_sha256") for r in rows),
    "source_audit": source_audit, "groups": summary, "comparisons": comparisons, "cross_environment": cross,
    "statistics": {"rule": "one-sided exact paired G test p<=.05 AND (g-l)/n>=.10",
                   "size_bound": .05, "critical_gains_by_discordances_at_16": {d: critical(d) for d in range(17)},
                   "old_rule_power_at_p3825": tail(16, 12, .3825), "scenarios": scenarios},
    "per_seed": [{k: r[k] for k in ["dir", "name", "train_seed", "counts", "G", "relation_shortcut", "key_pool"]} for r in rows],
    "input_sha256": inputs,
}
with OUT.open("x") as f:
    json.dump(evidence, f, indent=2, sort_keys=True)
    f.write("\n")
print(json.dumps({"created": str(OUT), "rows": len(rows), "G_disagreements": evidence["recomputed_G_disagreements"],
                  "duplicates": evidence["duplicate_ckpt_rows"], "sources": source_audit, "power": scenarios}, indent=2))
