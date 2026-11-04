"""Sense sleep, wired (track I1, 2026-11-04): the eye projector's night, run by the sleep worker after the brain's night.

Off by default: SLEEPMLX_SENSE_SLEEP=1 turns it on (the lead flips it after the real-app check). Ears stay off (the sound projector
failed A1), and the encoder LoRA (sense_encoder_lora, T4b) stays off: only the eye projector trains.

What one sense night does (run_all):
  1. finds the Desk's unslept practice manifests (userData/sense-sleep/practice-<day>.json, written by src/eyes.js nightly());
  2. the trained projector lives in userData/sense-sleep/vision_projector.safetensors (a copy of the published v1 file, made on the
     first night; the published file is never written). The model server loads this copy when it exists;
  3. for each manifest: sense_projector.run_night with
       - train_fn: the projector learns the manifest's anchored captions against the FROZEN day-time Nanbeige **q8** (no bf16 copy:
         there is no disk room for one; gradients flow through MLX's quantized matmuls to the projector; tiny-model test in
         tests/test_sense_night.py);
       - eval_fn: the fixed seat test V1 (top-1 of 10, caption log-likelihood) on the q8 model = the model the app uses by day;
       - the seatbelt: a drop > 2 points, a missing score or a crash -> exact byte rollback (sha256) + quarantine (sense_projector);
       - benFirst: should_stop is checked before training and between steps; a stop mid-training counts as a failed night (rolled back).
  4. returns a summary for the worker's output; any exception skips the sense night and never ends the brain's night (run_safely).

The seat set (userData/sense-sleep/seat/vision_seat.safetensors + vision_seat.json): pooled SigLIP2 features (N, 64, 768) float16
+ captions + the fixed 10-candidate lists. No seat set -> the night is skipped ("no seat set"), never run without a seatbelt.
"""
from __future__ import annotations

import json
import os
import shutil
import time
import traceback
from pathlib import Path
from typing import Callable, Optional

from . import sense_projector as SP

EYE_ID = "siglip2-base-patch16-256/pool2x2/v1"
PUBLISHED = os.path.expanduser("~/learner-ops/premonition-projectors/weights/vision_projector.safetensors")
DEFAULT_MODEL = os.path.expanduser("~/learner-ops/models/nanbeige42-3b-mlx-8bit")
PROMPT = "Describe this image."
MEDIA = "<<MEDIA>>"
MAX_CAP = 160


class Stopped(RuntimeError):
    """Ben came back (benFirst) during training."""


def enabled(env=os.environ) -> bool:
    return str(env.get("SLEEPMLX_SENSE_SLEEP", "")).lower() in ("1", "on", "true", "yes")


def sense_dir(userdata) -> Path:
    return Path(userdata) / "sense-sleep"


def pending_manifests(userdata) -> list:
    """Unslept eye manifests, oldest first: no ledger line for that night, not quarantined."""
    d = sense_dir(userdata)
    done = set()
    try:
        for l in (d / "nights.jsonl").read_text().splitlines():
            if l.strip():
                done.add(json.loads(l).get("night"))
    except FileNotFoundError:
        pass
    out = []
    for p in sorted(d.glob("practice-*.json")):
        if p.name.endswith(".quarantined.json"):
            continue
        night = p.stem.replace("practice-", "")
        if night not in done:
            out.append(p)
    return out


def projector_copy(userdata, published=PUBLISHED) -> Path:
    p = sense_dir(userdata) / "vision_projector.safetensors"
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_name(p.name + ".tmp")
        shutil.copyfile(published, tmp)
        os.replace(tmp, p)
    return p


def seat_paths(userdata):
    d = sense_dir(userdata) / "seat"
    return d / "vision_seat.safetensors", d / "vision_seat.json"


# ---- MLX pieces (lazy imports; tested on a tiny random Nanbeige, never loaded a real model in tests) -------------------------------
class LM:
    """A frozen mlx_lm model + tokenizer with the training prompt layout (premonition-projectors mm.template_ids)."""

    def __init__(self, model, tok):
        import mlx.core as mx
        self.mx, self.model, self.tok = mx, model, tok
        model.freeze()
        t = tok.apply_chat_template([{"role": "user", "content": MEDIA + "\n" + PROMPT}], tokenize=False,
                                    add_generation_prompt=True, enable_thinking=False)
        pre, post = t.split(MEDIA)
        self.pre = tok.encode(pre, add_special_tokens=False)
        self.post = tok.encode(post, add_special_tokens=False)
        end = tok.convert_tokens_to_ids("<|im_end|>") if hasattr(tok, "convert_tokens_to_ids") else None
        self.end = end if isinstance(end, int) and end >= 0 else None
        emb = model.model.embed_tokens
        self.dtype = emb(mx.array([0])).dtype

    def caption_ids(self, text):
        ids = self.tok.encode(str(text).strip(), add_special_tokens=False)[:MAX_CAP]
        return ids + [self.end] if self.end is not None and len(ids) < MAX_CAP else ids

    def caption_logprob(self, media, cap_ids):
        """Sum of log p(caption | prompt with media spliced in). media: (64, d) mx array. Differentiable w.r.t. media."""
        mx = self.mx
        emb = self.model.model.embed_tokens
        n_media = media.shape[0]
        ids = self.pre + [0] * n_media + self.post + list(cap_ids)
        h = mx.concatenate([emb(mx.array(self.pre)), media.astype(self.dtype), emb(mx.array(self.post + list(cap_ids)))])[None]
        logits = self.model(mx.array([ids]), input_embeddings=h)[0].astype(mx.float32)
        n0 = len(self.pre) + n_media + len(self.post)
        lg = logits[n0 - 1:-1]
        lp = lg - mx.logsumexp(lg, axis=-1, keepdims=True)
        return mx.take_along_axis(lp, mx.array(list(cap_ids))[:, None], axis=-1).sum()


    def score_candidates(self, media, cap_id_lists):
        """log p(caption | media prompt) for several captions: the media prompt runs once and its KV cache is reused (trimmed back
        after each caption). Equal to caption_logprob per caption (test_sense_night checks it)."""
        mx = self.mx
        from mlx_lm.models.cache import make_prompt_cache
        emb = self.model.model.embed_tokens
        ids = self.pre + [0] * media.shape[0] + self.post
        h = mx.concatenate([emb(mx.array(self.pre)), media.astype(self.dtype), emb(mx.array(self.post))])[None]
        cache = make_prompt_cache(self.model)
        last = self.model(mx.array([ids]), cache=cache, input_embeddings=h)[0, -1].astype(mx.float32)
        out = []
        for cid in cap_id_lists:
            cid = list(cid)
            if len(cid) > 1:
                lg = mx.concatenate([last[None], self.model(mx.array([cid[:-1]]), cache=cache)[0].astype(mx.float32)])
            else:
                lg = last[None]
            lp = lg - mx.logsumexp(lg, axis=-1, keepdims=True)
            v = mx.take_along_axis(lp, mx.array(cid)[:, None], axis=-1).sum()
            mx.eval(v)
            out.append(float(v))
            if len(cid) > 1:
                for c in cache:
                    c.trim(len(cid) - 1)
        return out


def load_lm(model_dir=DEFAULT_MODEL):
    from mlx_lm import load
    import importlib.util
    import sys
    model, tok = load(model_dir)
    # the server's make_seeing gives Nanbeige an input_embeddings argument; reuse it (desk/tools/glim_mlx_server.py)
    tools = Path(__file__).resolve().parent.parent / "desk" / "tools"
    if str(tools) not in sys.path:
        sys.path.insert(0, str(tools))
    import glim_mlx_server as W
    W.make_seeing(model)
    return LM(model, tok)


def load_projector_module(path):
    import mlx.core as mx
    import mlx.nn as nn
    w = mx.load(str(path))

    class Projector(nn.Module):
        def __init__(self, enc_dim, d):
            super().__init__()
            self.fc1, self.fc2 = nn.Linear(enc_dim, d), nn.Linear(d, d)

        def __call__(self, x):
            return self.fc2(nn.gelu(self.fc1(x)))

    p = Projector(w["fc1.weight"].shape[1], w["fc1.weight"].shape[0])
    p.load_weights([(k, v.astype(mx.float32)) for k, v in w.items()], strict=True)
    mx.eval(p.parameters())
    return p, {k: v.dtype for k, v in w.items()}


def make_eval_fn(lm: LM, seat_features, seat_captions, cands):
    """V1 on the seat set: top-1 of the candidate list by caption log-likelihood (percent). seat_features: (N, 64, 768)."""
    mx = lm.mx
    cap_ids = [lm.caption_ids(c) for c in seat_captions]

    def eval_fn(weights_path):
        p, _ = load_projector_module(weights_path)
        hit = 0
        for i, cl in enumerate(cands):
            media = p(mx.array(seat_features[i]).astype(mx.float32))
            scores = lm.score_candidates(media, [cap_ids[j] for j in cl])
            hit += int(max(range(len(cl)), key=lambda k: scores[k]) == 0)
        return {"V1": round(100.0 * hit / max(1, len(cands)), 3)}
    return eval_fn


def make_train_fn(lm: LM, *, steps=40, batch=4, lr=3e-4, seed=0, should_stop: Callable[[], bool] = lambda: False, log=print):
    """Projector training against the frozen q8 model: mean caption NLL per token, AdamW, half tonight / half replay.
    Writes the weights back in their original dtype (bf16), atomically. Checks should_stop between steps (raises Stopped)."""
    def train(weights_path, tonight, replay):
        import mlx.core as mx
        import mlx.nn as nn
        import mlx.optimizers as optim
        from mlx.utils import tree_flatten
        p, dtypes = load_projector_module(weights_path)
        opt = optim.AdamW(learning_rate=lr, weight_decay=0.0)

        def loss_fn(model, items):
            tot, n = 0.0, 0
            for feats, shape, caption in items:
                x = mx.array(feats, dtype=mx.float32).reshape(*(shape if len(shape) == 2 else (1, len(feats))))
                ids = lm.caption_ids(caption)
                tot = tot - lm.caption_logprob(model(x), ids)
                n += len(ids)
            return tot / max(1, n)

        vg = nn.value_and_grad(p, loss_fn)
        losses = []
        for k, items in enumerate(SP.mixed_batches(tonight, replay, batch, steps, seed)):
            if should_stop():
                raise Stopped("Ben came back during training (step %d)" % k)
            loss, grads = vg(p, items)
            opt.update(p, grads)
            mx.eval(p.parameters(), opt.state, loss)
            losses.append(float(loss))
        tmp = weights_path + ".tmp.safetensors"
        mx.save_safetensors(tmp, {k: v.astype(dtypes.get(k, mx.bfloat16)) for k, v in tree_flatten(p.parameters())})
        os.replace(tmp, weights_path)
        log("[sense-night] trained %d steps, loss %.3f -> %.3f" % (len(losses), losses[0] if losses else 0, losses[-1] if losses else 0))
    return train


def read_seat(userdata):
    st, js = seat_paths(userdata)
    if not st.exists() or not js.exists():
        return None
    import mlx.core as mx
    import numpy as np
    f = np.array(mx.load(str(st))["features"].astype(mx.float32))
    meta = json.loads(js.read_text())
    if meta.get("eye") not in (None, EYE_ID):
        raise ValueError("seat set made with another encoder: %s" % meta.get("eye"))
    return f, meta["captions"], meta["cands"]


# ---- the night ---------------------------------------------------------------------------------------------------------------
def run_all(userdata, *, lm_factory: Callable = None, should_stop: Callable[[], bool] = lambda: False, log=print,
            published=PUBLISHED, train_kw=None, seat=None) -> dict:
    """All pending eye manifests, oldest first. -> {"nights": [...ledger entries], "skipped": reason?}"""
    pend = pending_manifests(userdata)
    if not pend:
        return {"nights": [], "skipped": "nothing to practise"}
    seat = seat if seat is not None else read_seat(userdata)
    if seat is None:
        return {"nights": [], "skipped": "no seat set (sense-sleep/seat/vision_seat.*): the projector never trains without its seatbelt"}
    if should_stop():
        return {"nights": [], "skipped": "stopped for Ben"}
    weights = projector_copy(userdata, published)
    lm = (lm_factory or load_lm)()
    eval_fn = make_eval_fn(lm, *seat)
    train_fn = make_train_fn(lm, should_stop=should_stop, log=log, **(train_kw or {}))
    out = []
    for m in pend:
        if should_stop():
            break
        e = SP.run_night(weights, m, train_fn=train_fn, eval_fn=eval_fn, sense="eye", should_stop=should_stop)
        log("[sense-night] %s: kept=%s %s" % (e.get("night"), e.get("kept"), e.get("reason")))
        out.append({k: e.get(k) for k in ("night", "kept", "reason", "trained", "before", "after", "n_tonight", "n_replay", "quarantined")})
    return {"nights": out}


def run_safely(userdata, **kw) -> dict:
    """The worker's entry: never raises (an exception skips the sense night; the brain's night is already done)."""
    t0 = time.time()
    log = kw.get("log", print)
    try:
        r = run_all(userdata, **kw)
    except Exception as e:  # noqa: BLE001 - crash-safe by contract
        log("[sense-night] skipped after an error: %s" % e)
        r = {"nights": [], "skipped": "error: %s: %s" % (type(e).__name__, str(e)[:200]), "trace": traceback.format_exc()[-800:]}
    r["elapsed_s"] = round(time.time() - t0, 1)
    return r
