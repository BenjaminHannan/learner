#!/usr/bin/env python3
"""Cheapest-good-enough Vast offer picker, shared by every launcher (the agent proxy adds the Vast key; this never reads it).

Ranks rentable single-GPU offers by speed per dollar after hard floors for the job:
  score = speed / (dph_total + disk_gb * storage_cost / 730)      speed = dlperf (Vast's DL benchmark, default) or total_flops (TFLOPS)
Floors: --min-vram GB, --min-dlperf / --min-tflops (fast enough for the job), --min-cc (80 = bf16 + flash kernels), reliability,
download speed and disk. Hosts in China (Hugging Face is blocked there) and California (stuck 'loading' on Oct 24) are skipped by default.

  python tools/vast_pick.py --min-vram 24 --min-dlperf 40               # table, best deal first
  python tools/vast_pick.py --min-vram 40 --hours 2 --json --n 1        # best offer as JSON, for scripts
  from vast_pick import pick; best = pick(min_vram=24, min_dlperf=40)[0]
"""
from __future__ import annotations

import argparse, json, urllib.request

API = "https://console.vast.ai/api/v0"
SKIP_GEO = ("CN", "California")


def offers(min_vram=24, min_cc=80, min_rel=0.97, min_down=300, disk=80, max_dph=2.0, limit=400):
    q = {"num_gpus": {"eq": 1}, "rentable": {"eq": True}, "rented": {"eq": False}, "reliability2": {"gte": min_rel},
         "gpu_ram": {"gte": min_vram * 1000}, "compute_cap": {"gte": min_cc}, "inet_down": {"gte": min_down},
         "disk_space": {"gte": disk}, "dph_total": {"lte": max_dph}, "cuda_max_good": {"gte": 12.8},
         "order": [["dlperf_per_dphtotal", "desc"]], "type": "on-demand", "limit": limit}
    req = urllib.request.Request(API + "/bundles/", data=json.dumps(q).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode()).get("offers") or []


def pick(min_vram=24, min_dlperf=0.0, min_tflops=0.0, by="dlperf", disk=80, hours=1.0, skip_geo=SKIP_GEO, **kw):
    """Offers passing every floor, best speed per dollar first; each gets usd_h (GPU + storage) and est_usd for `hours`."""
    out = []
    for o in offers(min_vram=min_vram, disk=disk, **kw):
        geo = o.get("geolocation") or ""
        if any(g in geo for g in skip_geo) or (o.get("dlperf") or 0) < min_dlperf or (o.get("total_flops") or 0) < min_tflops:
            continue
        usd_h = o["dph_total"] + disk * (o.get("storage_cost") or 0) / 730
        speed = o.get("dlperf") if by == "dlperf" else o.get("total_flops")
        out.append(dict(id=o["id"], gpu=o["gpu_name"], vram_gb=round(o["gpu_ram"] / 1000), usd_h=round(usd_h, 3), est_usd=round(usd_h * hours, 2),
                        dlperf=round(o.get("dlperf") or 0, 1), tflops=round(o.get("total_flops") or 0, 1), per_usd=round((speed or 0) / usd_h, 1),
                        rel=round(o.get("reliability2") or 0, 3), down=round(o.get("inet_down") or 0), geo=geo, verified=o.get("verification")))
    return sorted(out, key=lambda x: -x["per_usd"])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--min-vram", type=float, default=24, help="GB")
    ap.add_argument("--min-dlperf", type=float, default=0, help="speed floor (Vast DLPerf; RTX 3090 ~ 25-35, A100 ~ 60-90, RTX 5090 ~ 200)")
    ap.add_argument("--min-tflops", type=float, default=0)
    ap.add_argument("--min-cc", type=int, default=80, help="compute capability x10; 80+ for bf16")
    ap.add_argument("--by", choices=["dlperf", "tflops"], default="dlperf")
    ap.add_argument("--disk", type=int, default=80)
    ap.add_argument("--hours", type=float, default=1.0)
    ap.add_argument("--max-dph", type=float, default=2.0)
    ap.add_argument("--allow-geo", action="store_true", help="do not skip China / California hosts")
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    rows = pick(min_vram=a.min_vram, min_dlperf=a.min_dlperf, min_tflops=a.min_tflops, by=a.by, disk=a.disk, hours=a.hours,
                skip_geo=() if a.allow_geo else SKIP_GEO, min_cc=a.min_cc, max_dph=a.max_dph)[:a.n]
    if a.json:
        print(json.dumps(rows if a.n != 1 else (rows[0] if rows else None)))
        return
    for r in rows:
        print(f"{r['id']:>9} {r['gpu']:<22} {r['vram_gb']:>3}GB ${r['usd_h']:.3f}/h est ${r['est_usd']:.2f} dlperf {r['dlperf']:>6} "
              f"tflops {r['tflops']:>6} {a.by}/$ {r['per_usd']:>6} rel {r['rel']} down {r['down']} {r['geo']}")


if __name__ == "__main__":
    main()
