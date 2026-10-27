#!/usr/bin/env python3
"""Rank vast offers for the dir-h6 rental (kit sleeph6r; helper H7, 2026-09-28).

Reads `vastai search offers ... --raw` JSON on stdin and prints at most 3 lines, best TFLOPS per $/h first, one offer per host:
    id  $/h  cores  host  gpu  TFLOPS  GB  waves  est_hours
Usage: offers.py MAXDPH MINRAM_GB RUNS RUN_GB FREE_GB BASE_H TF5090 FIT CAP_STOP MINCPU

The vast query already filters on the server (compute_cap>=800, cuda_max_good>=12.8, reliability>=0.98, cores); the same limits
are checked here again on any of those fields the offer carries, so a stale or partial listing cannot slip a card past them.
Fit check: an offer is used only if est_hours x $/h <= FIT x CAP_STOP.
  est_hours = BASE_H x max(1, TF5090 / card TFLOPS) x (card waves / a 5090's waves), waves = ceil(RUNS / runs that fit at once).
"""
import json
import sys

maxdph, minram, runs, run_gb, free_gb, base_h, tf5090, fit, cap, mincpu = (float(x) for x in sys.argv[1:11])
runs = int(runs)
d = json.load(sys.stdin)
d = d.get("offers", d) if isinstance(d, dict) else d


def num(o, *keys):
    for k in keys:
        try:
            return float(o[k])
        except (KeyError, TypeError, ValueError):
            pass
    return None


def waves(gb):
    return -(-runs // min(runs, int((gb - free_gb) // run_gb) + 1))


w5090 = waves(32.6)


def est(o):
    return base_h * max(1.0, tf5090 / float(o["total_flops"])) * waves((o.get("gpu_ram") or 0) / 1000) / w5090


ok = []
for o in d:
    dph, tf, ram = num(o, "dph_total"), num(o, "total_flops"), num(o, "gpu_ram")
    if not dph or not tf or dph > maxdph or (ram or 0) < minram * 1000:
        continue
    cc, cu, rel = num(o, "compute_cap"), num(o, "cuda_max_good"), num(o, "reliability2", "reliability")
    cores = num(o, "cpu_cores_effective")
    if (cc is not None and cc < 800) or (cu is not None and cu < 12.8) or (rel is not None and rel < 0.98):
        continue
    if cores is not None and cores < mincpu:
        continue
    if est(o) * dph > fit * cap:
        continue
    ok.append(o)
ok.sort(key=lambda o: -float(o["total_flops"]) / float(o["dph_total"]))
seen, out = set(), []
for o in ok:
    if o.get("host_id") in seen:
        continue
    seen.add(o.get("host_id"))
    gb = (o.get("gpu_ram") or 0) / 1000
    out.append(" ".join(str(x) for x in (o["id"], round(float(o["dph_total"]), 3), o.get("cpu_cores_effective"), o.get("host_id"),
                                          str(o.get("gpu_name", "?")).replace(" ", "_"), round(float(o["total_flops"]), 1),
                                          round(gb), waves(gb), round(est(o), 2))))
print("\n".join(out[:3]))
