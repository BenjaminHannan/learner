#!/usr/bin/env python3
"""bm-398i, adapter bypass and isolation (benchmarks thread, 2026-09-26). Plan and marks:
artifacts/claude-bm398i-20260926/PLAN.md. Agreed with Month-end (12:50 UTC): Benchmarks builds the switch and this
test; Month-end owns the router (needs memory? needs calculation?) and later wires the adapter to the memory path.

The switch: each q/k/v/o projection of the plain MiniCPM5-1B is wrapped in a SwitchLoRA that holds bm-397t's LoRA
shape (rank 16, alpha 32, fp32 A and B, the same math as claude_blurt2.add_lora in eval mode) with an explicit
on/off flag. Off returns the base projection's own output untouched (the adapter is not added at all). The base
weights stay frozen and nothing is merged.

The test, one process, the same greedy settings as bm-390 (claude_bm390.generate):
  base  replies of the unwrapped model;
  off   the wrapped model with the adapter off;
  on    the wrapped model with the adapter on;
  mixed every item again in both modes, alternating on/off between requests in a seeded order.
Items: the first N_GSM of GSM8K-300 and N_MMLU of MMLU-300 (bm-390 prompts and token limits) and the first
N_LOCOMO of bm-398d's sample with E20's lines (bm-395 layout, 50 tokens). The adapter is a fixed-seed nonzero LoRA
(--adapter random) or a saved bm-397t adapter file (--adapter PATH), for the BensPC confirmation.

  python -B scripts/claude_bm398i_switch.py selftest
  python -B scripts/claude_bm398i_switch.py run --data DATA --e20 E20.jsonl --model BASE --out OUT [--adapter random|PATH] [--limit N]
OUT gets replies (benchmark text: keep it outside the repository) and result.json (counts only).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import claude_bm390 as B  # noqa: E402

RANK, ALPHA = 16, 32                 # bm-397t's LoRA
NAMES = ("q_proj", "k_proj", "v_proj", "o_proj")
ADAPTER_SEED, B_STD = 3989, 0.02     # the fixed-seed random adapter
MIX_SEED = 3988
N_GSM, N_MMLU, N_LOCOMO = 25, 40, 25
LOGIT_ITEMS = 3                      # per kind: last-position logits compared exactly


def wrap(model, r: int = RANK, alpha: int = ALPHA) -> int:
    """Replace each named nn.Linear with a SwitchLoRA (off). Returns the number wrapped."""
    import torch
    nn = torch.nn

    class SwitchLoRA(nn.Module):
        def __init__(self, base):
            super().__init__()
            self.base = base
            dev = base.weight.device
            self.A = nn.Parameter(torch.zeros(r, base.in_features, dtype=torch.float32, device=dev), requires_grad=False)
            self.B = nn.Parameter(torch.zeros(base.out_features, r, dtype=torch.float32, device=dev), requires_grad=False)
            self.scale = alpha / r
            self.on = False

        def forward(self, x):
            if not self.on:
                return self.base(x)
            up = (x.float() @ self.A.t() @ self.B.t()) * self.scale
            return self.base(x) + up.to(x.dtype)

    n = 0
    for _name, mod in list(model.named_modules()):
        for child, sub in list(mod.named_children()):
            if child in NAMES and isinstance(sub, nn.Linear):
                setattr(mod, child, SwitchLoRA(sub))
                n += 1
    return n


def switches(model) -> list:
    return [m for m in model.modules() if hasattr(m, "on") and hasattr(m, "A") and hasattr(m, "base")]


def set_on(model, on: bool) -> None:
    for m in switches(model):
        m.on = bool(on)


def random_init(model, seed: int = ADAPTER_SEED, std: float = B_STD) -> None:
    import math
    import torch
    g = torch.Generator().manual_seed(seed)
    with torch.no_grad():
        for m in switches(model):
            bound = 1 / math.sqrt(m.A.shape[1])          # kaiming_uniform(a=sqrt(5)), as claude_blurt2
            m.A.copy_((torch.rand(m.A.shape, generator=g) * 2 - 1) * bound)
            m.B.copy_(torch.randn(m.B.shape, generator=g) * std)


def load_adapter(model, path: str) -> dict:
    """Load a bm-397t adapter file (state-dict keys ending .A / .B). Every key must land, every switch filled."""
    import torch
    sd = torch.load(path, map_location="cpu")
    own = {k: v for k, v in model.state_dict().items() if k.endswith(".A") or k.endswith(".B")}
    missing = sorted(set(own) - set(sd))
    extra = sorted(set(sd) - set(own))
    if missing or extra:
        raise SystemExit(f"bm398i: adapter keys do not match (missing {len(missing)}, extra {len(extra)})")
    with torch.no_grad():
        for m_name, m in model.named_modules():
            if m in switches(model):
                m.A.copy_(sd[m_name + ".A"].to(m.A.dtype))
                m.B.copy_(sd[m_name + ".B"].to(m.B.dtype))
    return {"keys": len(sd)}


def adapter_sha(model) -> str:
    h = hashlib.sha256()
    for k, v in sorted(model.state_dict().items()):
        if k.endswith(".A") or k.endswith(".B"):
            h.update(k.encode())
            h.update(v.detach().cpu().float().numpy().tobytes())
    return h.hexdigest()


def items(data: Path, e20_path: str, limit: int) -> list[dict]:
    import claude_bm398d_evidence as D
    out = []
    for task, n in (("gsm8k", N_GSM), ("mmlu", N_MMLU)):
        rows = [json.loads(x) for x in (data / f"{task}300.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
        for it in rows[: limit or n]:
            out.append({"id": it["qid"], "kind": task, "system": B.GENERAL_SYSTEM,
                        "user": B.general_prompt(task, it), "max_new": B.MAX_NEW[task]})
    kept, info = D.sample(data)
    e20 = {json.loads(x)["qid"]: json.loads(x) for x in Path(e20_path).read_text(encoding="utf-8").splitlines()
           if x.strip()}
    for q in kept[: limit or N_LOCOMO]:
        conv, i, qa, _gold = info[q]
        user = D.context(conv, D.items_of(conv), e20[q]["turns"][:20]) + "\n\n" + \
            B.QA_PROMPT.format(B.question_text(conv["sample_id"], i, qa))
        out.append({"id": q, "kind": "locomo", "system": B.LOCOMO_SYSTEM, "user": user, "max_new": B.ANS_TOKENS})
    return out


def _last_logits(model_dir: str, it: dict):
    import torch
    tok, model, dev, _ = B.plain_model(model_dir)
    enc = B._ids(tok, it["system"], it["user"]).to(dev)
    with torch.no_grad():
        return model(**enc).logits[0, -1].float().cpu()


def run(a) -> int:
    t_all = time.time()
    its = items(Path(a.data), a.e20, a.limit)
    tok, model, _dev, _ = B.plain_model(a.model)
    logit_ids = [i for k in ("gsm8k", "mmlu", "locomo") for i in [j for j, x in enumerate(its) if x["kind"] == k][:LOGIT_ITEMS]]

    def gen(it):
        return B.generate(a.model, it["system"], it["user"], it["max_new"])[0]

    res = {"items": {k: sum(x["kind"] == k for x in its) for k in ("gsm8k", "mmlu", "locomo")}}
    base = [gen(it) for it in its]
    base_logits = {i: _last_logits(a.model, its[i]) for i in logit_ids}
    print(f"[bm398i] base done seconds={time.time() - t_all:.0f}", flush=True)

    res["wrapped"] = wrap(model)
    if a.adapter == "random":
        random_init(model)
        res["adapter"] = {"kind": "random", "seed": ADAPTER_SEED, "b_std": B_STD}
    else:
        res["adapter"] = {"kind": "file", **load_adapter(model, a.adapter)}
    res["adapter"]["sha256"] = adapter_sha(model)
    model.eval()

    set_on(model, False)
    off = [gen(it) for it in its]
    off_logits = {i: _last_logits(a.model, its[i]) for i in logit_ids}
    print(f"[bm398i] off done seconds={time.time() - t_all:.0f}", flush=True)
    set_on(model, True)
    on = [gen(it) for it in its]
    on_logits = {i: _last_logits(a.model, its[i]) for i in logit_ids}
    print(f"[bm398i] on done seconds={time.time() - t_all:.0f}", flush=True)

    rng = random.Random(MIX_SEED)
    ons, offs = list(range(len(its))), list(range(len(its)))
    rng.shuffle(ons)
    rng.shuffle(offs)
    seq = [x for pair in zip(ons, offs) for x in ((pair[0], True), (pair[1], False))]
    mixed_on, mixed_off = {}, {}
    for i, mode in seq:
        set_on(model, mode)
        (mixed_on if mode else mixed_off)[i] = gen(its[i])
    set_on(model, False)
    after_logits = {i: _last_logits(a.model, its[i]) for i in logit_ids}
    print(f"[bm398i] mixed done seconds={time.time() - t_all:.0f}", flush=True)

    def by_kind(pred) -> dict:
        d = {k: [0, 0] for k in ("gsm8k", "mmlu", "locomo")}
        for i, it in enumerate(its):
            d[it["kind"]][1] += 1
            d[it["kind"]][0] += int(pred(i))
        d["all"] = [sum(v[0] for v in d.values()), sum(v[1] for v in d.values())]
        return {k: f"{v[0]}/{v[1]}" for k, v in d.items()}

    res["I1_off_equals_base"] = by_kind(lambda i: off[i] == base[i])
    res["I1_off_logits_max_abs_diff"] = max(float((off_logits[i] - base_logits[i]).abs().max()) for i in logit_ids)
    res["I2_mixed_off_equals_base"] = by_kind(lambda i: mixed_off[i] == base[i])
    res["I2_mixed_on_equals_on"] = by_kind(lambda i: mixed_on[i] == on[i])
    res["I2_off_logits_after_mixing_max_abs_diff"] = max(float((after_logits[i] - base_logits[i]).abs().max())
                                                         for i in logit_ids)
    res["I3_on_differs_from_base"] = by_kind(lambda i: on[i] != base[i])
    res["on_logits_max_abs_diff"] = max(float((on_logits[i] - base_logits[i]).abs().max()) for i in logit_ids)
    res["switches_between_requests"] = sum(seq[j][1] != seq[j - 1][1] for j in range(1, len(seq)))

    def frac(s: str) -> tuple[int, int]:
        x, y = s.split("/")
        return int(x), int(y)

    i1 = frac(res["I1_off_equals_base"]["all"])
    i2a = frac(res["I2_mixed_off_equals_base"]["all"])
    i2b = frac(res["I2_mixed_on_equals_on"]["all"])
    i3 = frac(res["I3_on_differs_from_base"]["all"])
    res["I1"] = i1[0] == i1[1] and res["I1_off_logits_max_abs_diff"] == 0.0
    res["I2"] = i2a[0] == i2a[1] and i2b[0] == i2b[1] and res["I2_off_logits_after_mixing_max_abs_diff"] == 0.0
    res["I3"] = i3[0] >= 0.2 * i3[1]
    res["verdict"] = ("INCONCLUSIVE" if not res["I3"] else "PASS" if res["I1"] and res["I2"] else "FAIL")
    res["seconds"] = round(time.time() - t_all)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = [{"id": it["id"], "kind": it["kind"], "base": base[i], "off": off[i], "on": on[i],
             "mixed_on": mixed_on[i], "mixed_off": mixed_off[i]} for i, it in enumerate(its)]
    B._write(out / "replies398i.jsonl", rows)
    (out / "result.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res), flush=True)
    return 0


def selftest(_a) -> int:
    import tempfile
    import torch
    from transformers import AutoModelForCausalLM, LlamaConfig
    import claude_blurt2 as BL
    ok = {}
    torch.manual_seed(0)
    cfg = LlamaConfig(vocab_size=64, hidden_size=32, intermediate_size=64, num_hidden_layers=2, num_attention_heads=4,
                      num_key_value_heads=2, max_position_embeddings=64)
    m = AutoModelForCausalLM.from_config(cfg).eval()
    x = torch.randint(0, 64, (1, 12))
    with torch.no_grad():
        base = m(input_ids=x).logits
        ok["8 projections wrapped (q,k,v,o x 2)"] = wrap(m, r=4, alpha=8) == 8
        random_init(m, seed=1, std=0.05)
        set_on(m, False)
        ok["off equals the base exactly"] = torch.equal(m(input_ids=x).logits, base)
        set_on(m, True)
        on = m(input_ids=x).logits
        ok["on changes the output"] = (on - base).abs().max().item() > 1e-3
        set_on(m, False)
        ok["off after on equals the base exactly"] = torch.equal(m(input_ids=x).logits, base)
    # the same A and B in bm-397t's LoRALinear (eval mode) must give the switch's "on" output:
    # rebuild the same base (same seed), add bm-397t's LoRA, copy A and B in
    torch.manual_seed(0)
    ref = AutoModelForCausalLM.from_config(cfg).eval()
    BL.add_lora(ref, r=4, alpha=8, dropout=0.05)
    ref.eval()
    sd = {k: v for k, v in m.state_dict().items() if k.endswith(".A") or k.endswith(".B")}
    missing = [k for k in sd if k not in ref.state_dict()]
    ref.load_state_dict(sd, strict=False)
    with torch.no_grad():
        ok["bm-397t key names match"] = not missing
        ok["bm-397t's LoRA (eval) equals the switch on"] = (ref(input_ids=x).logits - on).abs().max().item() < 1e-5
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "adapter.pt"
        torch.save({k: v.detach().cpu() for k, v in ref.state_dict().items() if k.endswith(".A") or k.endswith(".B")}, p)
        torch.manual_seed(0)
        m2 = AutoModelForCausalLM.from_config(cfg).eval()
        wrap(m2, r=4, alpha=8)
        load_adapter(m2, str(p))
        set_on(m2, True)
        with torch.no_grad():
            ok["a saved bm-397t adapter loads into the switch"] = (m2(input_ids=x).logits - on).abs().max().item() < 1e-5
            set_on(m2, False)
            ok["loaded switch off equals the base exactly"] = torch.equal(m2(input_ids=x).logits, base)
        ok["adapter hash is stable"] = adapter_sha(m2) == adapter_sha(m)
    for name, v in ok.items():
        print(("PASS " if v else "FAIL ") + name)
    print("BM398I-SELFTEST " + ("PASS" if all(ok.values()) else "FAIL") + f" {sum(ok.values())}/{len(ok)}")
    return 0 if all(ok.values()) else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["selftest", "run"])
    ap.add_argument("--data", default="")
    ap.add_argument("--e20", default="")
    ap.add_argument("--model", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--adapter", default="random")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    return {"selftest": selftest, "run": run}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
