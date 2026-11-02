"""HF transformers + peft runner for K2-Horizon-3.7B: per-request adapter on / off, greedy decode with per-token log-probs.

Loads the base exactly as the sleep code does (backbone/train.load_model: bf16, trust_remote_code, pinned revision) and renders prompts with the
sleep code's own Lang (K2 chat format, thinking closed), so the key and read prompts are in the format the LoRA was trained on.
The backbone directory (Sleep-B code at the pinned commit) is found via $RR_BACKBONE or <repo>/backbone.
"""
from __future__ import annotations

import contextlib
import os
import sys
from argparse import Namespace
from pathlib import Path

from .arms import GenOut
from .world import K2_MODEL, K2_REVISION, REPO


def backbone_dir() -> Path:
    for c in (os.environ.get("RR_BACKBONE"), REPO / "backbone"):
        if c and (Path(c) / "train.py").exists():
            return Path(c)
    raise SystemExit("backbone/ (Sleep-B code at the pinned commit) not found: set RR_BACKBONE")


class Runner:
    def __init__(self, adapters: dict[str, str], model=K2_MODEL, revision=K2_REVISION, prompt_tokens_per_batch=14000, max_bs=16):
        import torch
        bb = backbone_dir()
        for p in (bb, bb / "sleep"):
            sys.path.insert(0, str(p))
        from sleep1 import Lang
        from train import load_model
        from peft import PeftModel
        self.torch = torch
        dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        lm, tok = load_model(Namespace(model=model, revision=revision, smoke=False, seed=0, moe=False), dev, torch.bfloat16)
        self.L = Lang(tok, False, dev, k2=True)
        self.tok, self.dev = tok, dev
        names = list(adapters)
        self.pm = PeftModel.from_pretrained(lm, adapters[names[0]], adapter_name=names[0]) if names else lm
        for n in names[1:]:
            self.pm.load_adapter(adapters[n], adapter_name=n)
        self.pm.eval()
        self.ptpb, self.max_bs = prompt_tokens_per_batch, max_bs

    def render(self, system, user):
        return self.L.render(system, user)

    def count_tokens(self, text):
        return len(self.L.ids(text))

    def gen(self, prompts, max_new, adapter=None):
        torch = self.torch
        outs = [None] * len(prompts)
        enc = [self.L.ids(p) for p in prompts]
        order = sorted(range(len(prompts)), key=lambda i: len(enc[i]))
        pad = self.tok.pad_token_id if self.tok.pad_token_id is not None else self.L.eos
        if adapter:
            self.pm.set_adapter(adapter)
        st = 0
        while st < len(order):
            bs = 1
            while bs < self.max_bs and st + bs < len(order) and (bs + 1) * len(enc[order[min(st + bs, len(order) - 1)]]) <= self.ptpb:
                bs += 1
            idx = order[st:st + bs]
            st += bs
            n = max(len(enc[i]) for i in idx)
            ids = torch.full((len(idx), n), pad, dtype=torch.long)
            mask = torch.zeros((len(idx), n), dtype=torch.long)
            for r, i in enumerate(idx):
                ids[r, n - len(enc[i]):] = torch.tensor(enc[i])
                mask[r, n - len(enc[i]):] = 1
            ctx = contextlib.nullcontext() if adapter else self.pm.disable_adapter()
            with torch.no_grad(), ctx:
                out = self.pm.generate(input_ids=ids.to(self.dev), attention_mask=mask.to(self.dev), max_new_tokens=max_new, pad_token_id=pad,
                                       eos_token_id=self.L.eos, do_sample=False, output_scores=True, return_dict_in_generate=True)
            lp = [torch.log_softmax(s.float(), -1) for s in out.scores]
            for r, i in enumerate(idx):
                toks, lps = [], []
                for t in range(out.sequences.shape[1] - n):
                    tid = int(out.sequences[r, n + t])
                    lps.append(float(lp[t][r, tid]))
                    toks.append(tid)
                    if tid == self.L.eos:
                        break
                n_new = len(toks)
                body = [t for t in toks if t != self.L.eos]
                pieces = [self.tok.decode([t], skip_special_tokens=True) for t in body]
                outs[i] = GenOut(text="".join(pieces).strip(), pieces=pieces, lps=lps[:len(body)], n_prompt=len(enc[i]), n_new=n_new)
            del out, lp
        return outs
