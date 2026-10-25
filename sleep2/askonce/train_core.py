"""LoRA night training core (fp16 base + fp32 LoRA + dynamic loss scale on a T4; fp32 on CPU). Logits are computed only at loss positions
(K2 has a 250k untied vocab). SFT NLL + KL anchor + DPO (reference = the start-of-night adapter, log-probs precomputed once)."""
import math
import random
import time

import torch
import torch.nn.functional as F
from torch.utils.checkpoint import checkpoint

from .compute_ledger import REF, TRAIN
from .config import ANCHOR_W, BETA, CHUNK, LORA_ALPHA, LORA_R, LORA_TARGETS, MAX_SEQ


MAX_SKIP_FRAC = 0.2


def _finite(x, what):
    if not math.isfinite(x):
        raise FloatingPointError(f"non-finite {what}: {x} (fp16 overflow?)")


class LoRATrainer:
    def __init__(self, model, tok, seed, device, use_scaler):
        from peft import LoraConfig, get_peft_model
        self.tok, self.dev, self.seed = tok, device, seed
        model.config.use_cache = False
        if hasattr(model, "gradient_checkpointing_enable"):
            model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
        torch.manual_seed(seed)  # LoRA init depends on the arm seed
        self.pm = get_peft_model(model, LoraConfig(r=LORA_R, lora_alpha=LORA_ALPHA, lora_dropout=0.0, bias="none", target_modules=LORA_TARGETS))
        for p in self.pm.parameters():
            if p.requires_grad and p.dtype != torch.float32:
                p.data = p.data.float()
        self.inner = self.pm.base_model.model
        self.params = [p for p in self.pm.parameters() if p.requires_grad]
        self.scaler = torch.amp.GradScaler("cuda", enabled=bool(use_scaler and device.startswith("cuda")), init_scale=2.0 ** 12)

    # ------------------------------------------------------------------ encoding
    def encode(self, prompt, target):
        p = self.tok(prompt, add_special_tokens=False).input_ids
        t = self.tok(target, add_special_tokens=False).input_ids
        over = len(p) + len(t) - MAX_SEQ
        if over > 0:
            p = p[:1] + p[1 + over:]  # keep BOS, drop the oldest prompt tokens
        return {"ids": p + t, "mask": [0] * len(p) + [1] * len(t)}

    def length(self, prompt, target):
        return len(self.encode(prompt, target)["ids"])

    # ------------------------------------------------------------------ forward pieces (no full-sequence logits)
    def _T(self, x, dt=torch.long):
        return torch.tensor(x, dtype=dt, device=self.dev)

    def hidden(self, ids):
        return self.inner.model(input_ids=self._T([ids]), use_cache=False).last_hidden_state[0]

    @staticmethod
    def positions(mask):
        return [j for j, m in enumerate(mask) if m and j > 0]

    def _lp(self, hc, tc):
        return -F.cross_entropy(self.inner.lm_head(hc).float(), tc, reduction="none")

    def _kl(self, ht, hs):
        lt = F.log_softmax(self.inner.lm_head(ht).float(), -1)
        ls = F.log_softmax(self.inner.lm_head(hs).float(), -1)
        return (lt.exp() * (lt - ls)).sum(-1)

    def chunked(self, fn, *tensors):
        outs = []
        for i in range(0, len(tensors[0]), CHUNK):
            part = [t[i:i + CHUNK] for t in tensors]
            outs.append(checkpoint(fn, *part, use_reentrant=False) if torch.is_grad_enabled() else fn(*part))
        return torch.cat(outs)

    def tok_logps(self, ex):
        idx = self.positions(ex["mask"])
        h = self.hidden(ex["ids"])
        return self.chunked(self._lp, h[self._T([i - 1 for i in idx])], self._T([ex["ids"][i] for i in idx]))

    def seq_logp(self, ex, grad):
        if grad:
            return self.tok_logps(ex).sum()
        with torch.no_grad():
            return self.tok_logps(ex).sum().item()

    def anchor_kl(self, ex):
        idx = self._T([i - 1 for i in self.positions(ex["mask"])])
        with torch.no_grad(), self.pm.disable_adapter():
            ht = self.hidden(ex["ids"])[idx]
        return self.chunked(self._kl, ht, self.hidden(ex["ids"])[idx]).mean()

    # ------------------------------------------------------------------ one night
    def run_night(self, items, anchors, n_opt, lr, night, log=print, dpo_w=1.0):
        """items: dicts kind sft{prompt,target} | pair{prompt,chosen,rejected}. anchors: list of prompt strings (KL on prompt tokens).
        Returns stats incl. actual token-pass units, DPO margin / accuracy and mean anchor KL."""
        self.pm.train()
        rng = random.Random(self.seed * 7919 + night)
        items = list(items)
        rng.shuffle(items)
        enc = []
        for it in items:
            if it["kind"] == "sft":
                enc.append(("sft", self.encode(it["prompt"], it["target"])))
            else:
                enc.append(("pair", self.encode(it["prompt"], it["chosen"]), self.encode(it["prompt"], it["rejected"])))
        n_opt = max(1, min(n_opt, len(enc)))
        units = {"train": 0, "ref": 0}
        t0 = time.time()
        refs = {}
        for i, e in enumerate(enc):  # reference log-probs under the start-of-night adapter, computed once
            if e[0] == "pair":
                refs[i] = (self.seq_logp(e[1], False), self.seq_logp(e[2], False))
                units["ref"] += REF * (len(e[1]["ids"]) + len(e[2]["ids"]))
        opt = torch.optim.AdamW(self.params, lr=lr, weight_decay=0.0)
        sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: 0.5 * (1 + math.cos(math.pi * min(s, n_opt) / n_opt)))
        per = math.ceil(len(enc) / n_opt)
        stats = {"sft": [], "dpo": [], "margin": [], "dpo_acc": [], "kl": [], "gnorm": [], "skipped": 0, "steps": 0}
        for s in range(n_opt):
            lo = s * per
            grp = list(range(lo, min(len(enc), lo + per)))
            sc = 1.0 / max(1, len(grp))
            for i in grp:
                e = enc[i]
                if e[0] == "sft":
                    loss = -self.tok_logps(e[1]).mean()
                    units["train"] += TRAIN * len(e[1]["ids"])
                    _finite(loss.item(), f"night {night} SFT loss (item {i})")
                    stats["sft"].append(loss.item())
                else:
                    lc, lr_ = self.seq_logp(e[1], True), self.seq_logp(e[2], True)
                    z = BETA * ((lc - refs[i][0]) - (lr_ - refs[i][1]))
                    loss = -F.logsigmoid(z) * dpo_w
                    units["train"] += TRAIN * (len(e[1]["ids"]) + len(e[2]["ids"]))
                    _finite(loss.item(), f"night {night} DPO loss (item {i})")
                    stats["dpo"].append(loss.item())
                    stats["margin"].append(z.item())
                    stats["dpo_acc"].append(float(z.item() > 0))
                self.scaler.scale(loss * sc).backward()
            a = self.encode(anchors[(night * n_opt + s) % len(anchors)], "")
            a["mask"] = [0] + [1] * (len(a["ids"]) - 1)
            kl = self.anchor_kl(a)
            self.scaler.scale(ANCHOR_W * kl).backward()
            units["train"] += TRAIN * len(a["ids"])
            units["ref"] += REF * len(a["ids"])
            _finite(kl.item(), f"night {night} anchor KL (step {s})")
            stats["kl"].append(kl.item())
            self.scaler.unscale_(opt)
            gn = torch.nn.utils.clip_grad_norm_(self.params, 1.0).item()
            before = self.scaler.get_scale()
            self.scaler.step(opt)
            self.scaler.update()
            if self.scaler.is_enabled() and self.scaler.get_scale() < before:
                stats["skipped"] += 1
            sched.step()
            opt.zero_grad(set_to_none=True)
            stats["gnorm"].append(gn)
            stats["steps"] += 1
        self.pm.eval()
        if stats["skipped"] > MAX_SKIP_FRAC * stats["steps"]:
            raise FloatingPointError(f"night {night}: GradScaler skipped {stats['skipped']} of {stats['steps']} optimizer steps (> {MAX_SKIP_FRAC:.0%}); "
                                     "the adapter barely trained, so the arms would all be untrained base K2")
        mean = lambda v: round(sum(v) / len(v), 5) if v else None  # noqa: E731
        out = {"night": night, "n_items": len(enc), "units": units, "units_total": units["train"] + units["ref"], "seconds": round(time.time() - t0, 1),
               "sft_loss": mean(stats["sft"]), "dpo_loss": mean(stats["dpo"]), "dpo_margin": mean(stats["margin"]), "dpo_acc": mean(stats["dpo_acc"]),
               "anchor_kl": mean(stats["kl"]), "gnorm": mean(stats["gnorm"]), "skipped_steps": stats["skipped"], "opt_steps": stats["steps"],
               "loss_scale": self.scaler.get_scale() if self.scaler.is_enabled() else None}
        if self.dev.startswith("cuda"):
            out["peak_mem_gb"] = round(torch.cuda.max_memory_allocated() / 2 ** 30, 2)
        log(f"night {night}: {out}")
        return out

    def release(self):
        """Remove the adapter and return the clean base model (to start the next arm-seed)."""
        base = self.pm.unload()
        return base
