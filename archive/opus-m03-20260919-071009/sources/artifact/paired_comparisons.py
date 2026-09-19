"""Milestone 3: paired writer differences from the saved per-question bits (no model is loaded or run).

DESCRIPTIVE: the predeclaration fixed no decision rule for writer-vs-writer differences (only the H1 gate and the
H1 paired rule). Same questions, same order; visit-clustered (ladder) or triplet-clustered one-sided 99% bounds,
10,000 resamples, via the harness's own bootstrap. Clusters are rebuilt from the frozen evaluation data exactly as
the harness readouts build them (visit = q_visit + item_index * visits_per_item, masked by hop/held-out).
Run: $PY -B artifacts/opus-m03-20260919-071009/paired_comparisons.py
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import premonition_pool_controls as H  # noqa: E402

started = time.perf_counter()
H.bootstrap()
import torch  # noqa: E402

HERE = Path(__file__).resolve().parent
PAIRS = {"answer": [("mean", "original")],
         "retrieval": [("mean", "original"), ("two", "original"), ("two", "mean")]}
METRICS = {
    "answer": ["ladder/read:one_hop", "ladder/choose:one_hop", "ladder/combine:two_hop_trained_rel",
               "ladder/combine:two_hop_heldout_rel", "triplets/relevant_both_correct",
               "triplets/invariant_both_correct"],
    "retrieval": ["own_fixed_K4/one_hop", "own_fixed_K4/two_hop_trained_rel", "own_fixed_K4/two_hop_heldout_rel",
                  "own_fixed_K4/one_hop/all_gold_fetched", "own_fixed_K4/two_hop_trained_rel/all_gold_fetched",
                  "gold_read_K2_no_fetch/one_hop", "second_fetch/practised/right_person_relation",
                  "second_fetch/heldout/right_relation"],
}


def clusters(split: str) -> dict:
    hops, held, visits = [], [], []
    for i, item in enumerate(H.L.load_split(split)):
        hops.append(item[2])
        held.append(item[0].slices["heldout"])
        visits.append(item[0].q_visit + i * int(item[0].tokens.shape[0]))
    hop, held, visit = (torch.cat(x) for x in (hops, held, visits))
    ladder = {"one_hop": visit[hop == 1], "two_hop_trained_rel": visit[(hop == 2) & ~held],
              "two_hop_heldout_rel": visit[(hop == 2) & held]}
    ladder["practised"], ladder["heldout"] = ladder["two_hop_trained_rel"], ladder["two_hop_heldout_rel"]
    return ladder


def lookup(scores: dict, metric: str):
    node = scores
    for part in metric.split("/"):
        node = node[part]
    return H.unbits(node["bits"])


def cluster_of(metric: str, ladder: dict):
    if metric.startswith("triplets/"):
        return None
    for key in ("one_hop", "two_hop_trained_rel", "two_hop_heldout_rel", "practised", "heldout"):
        if f"/{key}" in metric or f":{key}" in metric:
            return ladder[key]
    raise KeyError(metric)


out = {"note": __doc__.strip().splitlines()[2], "splits": {}}
for split, folder in (("validation", "eval"), ("test", "tests")):
    ladder = clusters(split)
    rows = []
    for kind, pairs in PAIRS.items():
        seeds = (0, 1) if kind == "answer" else (0,)
        for seed in seeds:
            for left, right in pairs:
                a = json.loads((HERE / folder / f"{kind}-{left}-s{seed}.json").read_text())["scores"]
                b = json.loads((HERE / folder / f"{kind}-{right}-s{seed}.json").read_text())["scores"]
                for metric in METRICS[kind]:
                    x, y = lookup(a, metric), lookup(b, metric)
                    group = cluster_of(metric, ladder)
                    group = torch.arange(len(x)) if group is None else group
                    if len(group) != len(x):
                        raise SystemExit(f"cluster/bit length mismatch for {metric} ({len(group)} vs {len(x)})")
                    boot = H.paired_bootstrap(x.float(), y.float(), group, resamples=10000, alpha=0.01)
                    rows.append({"kind": kind, "seed": seed, "compare": f"{left} - {right}", "metric": metric,
                                 "left": int(x.sum()), "right": int(y.sum()), "n": len(x),
                                 "identical_bits": bool(torch.equal(x, y)), **boot})
    out["splits"][split] = rows
seconds = time.perf_counter() - started
(HERE / "paired.json").write_text(json.dumps(out, indent=1))
H.ledger_add("analysis", "paired writer differences (bits only, no model)", seconds,
             script=str(Path(__file__).relative_to(ROOT)))
for split, rows in out["splits"].items():
    print(f"== {split}")
    for r in rows:
        flag = " SAME" if r["identical_bits"] else ""
        print(f"{r['kind']:9} s{r['seed']} {r['compare']:17} {r['metric']:48} {r['left']:4}-{r['right']:4}/{r['n']:3}"
              f"  {r['point']:+.4f} [{r['lower']:+.4f}, {r['upper']:+.4f}]{flag}")
print(f"({seconds:.1f} s)")
