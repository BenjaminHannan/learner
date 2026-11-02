"""Loss-position-only logits for mlx-lm LoRA training (drop-in for mlx_lm.tuner.trainer.default_loss).

Stock default_loss runs lm_head on every position: [B,T,V] logits (V=250,624 for K2-Horizon-3.7B: 2560x250k MACs per token and a
huge fp32 CE temp), then masks. Here: run the body, gather hidden states at the loss positions (prompt tokens are masked out),
apply lm_head (and any final norm / softcap passed in `head`) only there. Exact up to float summation order.

Use:  from loss_logits import make_loss;  train(model, optimizer, train_set, loss=make_loss())      # mlx_lm.tuner.trainer.train(loss=...)
      make_loss(chunk_rows=4096) also recomputes logits per 4096-row chunk in backward (mx.checkpoint), so [N,V] is never held.
Models: any mlx-lm model with .model(inputs)->final-normed hidden and .lm_head (or tied embed_tokens.as_linear), e.g. llama, qwen3.
Others (gemma softcap, k2 remote class): pass body=/head=/head_owner= (module whose params the head uses; needed for chunk_rows).
Opt-in: nothing imports this unless the training script does.
"""
import mlx.core as mx
import mlx.nn as nn
import numpy as np


def default_body(model, inputs):
    return model.model(inputs)  # [B,T,D], final norm already applied (mlx-lm llama/qwen3/...)


def default_head(model):  # (callable h->logits, module owning its params, for checkpointing)
    if getattr(model.args, "tie_word_embeddings", False) or not hasattr(model, "lm_head"):
        return model.model.embed_tokens.as_linear, model.model.embed_tokens
    return model.lm_head, model.lm_head  # softcap models: head=lambda h: cap*mx.tanh(model.lm_head(h)/cap), head_owner=model.lm_head


def _ce_sum(head, h, t):  # sum of CE over rows, fp32
    return nn.losses.cross_entropy(head(h), t).astype(mx.float32).sum()


def make_loss(body=None, head=None, head_owner=None, chunk_rows=None):
    """Returns loss(model, batch, lengths) -> (mean CE over target tokens, ntoks), same contract as default_loss."""
    def loss(model, batch, lengths):
        inputs, targets = batch[:, :-1], batch[:, 1:]
        h = (body or default_body)(model, inputs)
        steps = mx.arange(1, targets.shape[1] + 1)
        mask = mx.logical_and(steps >= lengths[:, 0:1], steps <= lengths[:, 1:])
        idx = mx.array(np.nonzero(np.array(mask).reshape(-1))[0].astype(np.int32))  # tiny host sync (bool mask only); shapes are dynamic
        ntoks = mask.sum()
        hs = h.reshape(-1, h.shape[-1])[idx]  # [N,D], N = #target tokens
        ts = targets.reshape(-1)[idx]
        hd, owner = (head, head_owner) if head else default_head(model)
        if chunk_rows and hs.shape[0] > chunk_rows:
            def part(i):  # targets closed over (int inputs can't go through checkpoint's VJP)
                tc = ts[i:i + chunk_rows]
                fn = lambda hc: _ce_sum(hd, hc, tc)
                return (nn.utils.checkpoint(owner, fn) if owner is not None else fn)(hs[i:i + chunk_rows])
            ce = sum(part(i) for i in range(0, hs.shape[0], chunk_rows))
        else:
            ce = _ce_sum(hd, hs, ts)
        return ce / ntoks, ntoks
    return loss
