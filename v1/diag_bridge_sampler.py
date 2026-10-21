"""DIAGNOSTIC ONLY (DEV, never sealed; cannot open the seal). Marks fixed by the coordinator before the run:
re-score FULL's W2.pt on creative DEV through Ledger.generate (the training-time path, bridge ON): first-try >= 12% => the sampler/bridge
mismatch is SHOWN; < 6% => REFUTED; 6-12% => inconclusive. Controls: same path with the bridge OFF, and the sampler path (the 3.9% in final_dev.json)."""
import json, sys
import torch
from creative import sleep, c2_stones, rules_real as R
from creative.c2b import DATA
from custom_io.data import Dataset, collate, to_device
from v1.joint import Bridge

arm_dir, device = sys.argv[1], "cpu"
saved = torch.load(f"{arm_dir}/D-final.pt", map_location="cpu", weights_only=False)
b = Bridge(128, 256)
b.load_state_dict({k: v for k, v in saved["bridge"].items() if not k.startswith(("_d.", "_c."))}, strict=True)
b.frozen_ctx = True
m, vocab, _ = sleep.load_parent(f"{arm_dir}/creative/W2.pt", device)
b.attach_creative(m)
m.eval()
rows = c2_stones._with_nums(R.load_split(DATA, "dev"))


def first_try(enabled):
    b.enabled = enabled
    hit = {}
    with torch.no_grad():
        for s in range(0, len(rows), 64):
            chunk = rows[s:s + 64]
            ds = Dataset(chunk, vocab, strict=False)
            batch = to_device(collate([ds[i] for i in range(len(chunk))]), device)
            out = m.generate(batch)
            for r, a in zip(chunk, out):
                k = r["kind"]
                h = hit.setdefault(k, [0, 0])
                h[0] += str(a).strip() in [str(x).strip() for x in r["accepted"]]
                h[1] += 1
    tot = sum(v[0] for v in hit.values()) / sum(v[1] for v in hit.values())
    return tot, {k: v[0] / v[1] for k, v in hit.items()}


on, on_k = first_try(True)
off, off_k = first_try(False)
res = {"bridge_on_generate_first_try": on, "by_kind_on": on_k, "bridge_off_generate_first_try": off, "by_kind_off": off_k,
       "p_dc_weight_norm": float(b.p_dc.weight.norm()), "p_dc_bias_norm": float(b.p_dc.bias.norm()),
       "verdict": "SHOWN" if on >= 0.12 else ("REFUTED" if on < 0.06 else "INCONCLUSIVE"), "marks": ">=0.12 SHOWN; <0.06 REFUTED; else inconclusive"}
print(json.dumps(res, indent=1))
