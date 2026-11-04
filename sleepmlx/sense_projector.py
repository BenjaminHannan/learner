"""Sleep for the senses: nightly projector practice with a seatbelt (design section 9; toy track T4, 2026-11-04).

The Desk (desk/src/sense-sleep.js) stores ENCODER FEATURES from watching and listening (float16, never raw pictures or audio)
and writes one practice manifest per night (sense-sleep/practice-<night>.json): text-anchored examples that passed the logic
check, by reference into the day feature files. This module, run by the sleep app at night:

  1. backs up the projector weights (exact bytes + sha256);
  2. scores the fixed projector tests (V1 / A1 / VID1) before training, on the bf16 model and, if given, on the q8 day-time model;
  3. trains the projector on tonight's practice + replay of earlier KEPT nights (half and half), against the bf16 copy;
  4. scores the fixed tests again; if ANY score drops by more than 2 points (bf16 or q8), or a score is missing, or training
     crashes, the weights are restored byte for byte and the night's manifest is quarantined so it is never replayed;
  5. appends one line to sense-sleep/nights.jsonl (the Desk's NightLedger reads the same file).

Toy evidence (T4 repo premonition-sleeplab-t4, NOT real-model evidence): text-anchored practice raised the weak sense 3/3 seeds
(+14.6..+20.8 points) without hurting the strong one; the echo guard held; the seatbelt rolled back 3/3 poisoned nights exactly.
The 2-of-3 rule and multi-frame video practice were NOT proven in the toy; this module trains whatever the manifest holds, and
the Desk only puts 2-of-3 examples there when its `twoOfThree` switch is on (off by default).

Pure Python: imports and unit tests run without numpy or MLX. The MLX trainer (make_mlx_train_fn) is imported lazily and has only
been run on a tiny fake loss (no real model was loaded); wiring it to Nanbeige bf16 needs an `lm_loss` from the lead (see
make_mlx_train_fn).
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import shutil
import struct
import time
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Tuple

SEAT_DROP = 2.0
TESTS = ("V1", "A1", "VID1")
MAX_FEATURES = 64 * 1024


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_manifest(path) -> dict:
    m = json.loads(Path(path).read_text())
    if m.get("dtype") != "float16":
        raise ValueError("manifest dtype must be float16")
    for sense in ("eye", "ear"):
        for e in m.get(sense, []):
            for k in ("day", "off", "len", "label"):
                if k not in e:
                    raise ValueError(f"{sense} entry missing {k}")
            if not (0 < int(e["len"]) <= MAX_FEATURES):
                raise ValueError("bad feature length")
            if str(e["label"]).strip().lower().startswith("maybe"):
                raise ValueError("a maybe never trains")
    return m


def load_features(feature_dir, entry) -> List[float]:
    """float16 little-endian vector from features-<day>.bin at entry['off']."""
    p = Path(feature_dir) / f"features-{entry['day']}.bin"
    n = int(entry["len"])
    with open(p, "rb") as f:
        f.seek(int(entry["off"]))
        raw = f.read(2 * n)
    if len(raw) != 2 * n:
        raise ValueError(f"short read in {p.name}")
    return list(struct.unpack(f"<{n}e", raw))


def kept_nights(ledger_path) -> List[str]:
    try:
        lines = Path(ledger_path).read_text().splitlines()
    except FileNotFoundError:
        return []
    return [json.loads(l)["night"] for l in lines if l.strip() and json.loads(l).get("kept")]


def fresh_entries(entries: Iterable[dict], enc_version: Optional[int]) -> list:
    """Encoder LoRA (sense_encoder_lora): pooled features made by an OLDER encoder adapter are stale and never train the
    projector. enc_version None = no encoder adapter in use (keep everything). Entries without encVersion count as version 0."""
    if enc_version is None:
        return list(entries)
    return [e for e in entries if int(e.get("encVersion", 0)) == int(enc_version)]


def practice_set(manifest: dict, sense: str, feature_dir, replay: Iterable[dict] = (),
                 enc_version: Optional[int] = None) -> Tuple[list, list]:
    """(tonight, replay) lists of (features, shape, label) for one sense. Only text-anchored (and, if the Desk switched it on,
    gated 2-of-3) examples are in a manifest; quarantined nights are never in `replay`."""
    def load(entries):
        return [(load_features(feature_dir, e), e.get("shape") or [int(e["len"])], e["label"])
                for e in fresh_entries(entries, enc_version)]
    tonight = load(manifest.get(sense, []))
    old = []
    for m in replay:
        old.extend(load(m.get(sense, [])))
    return tonight, old


def mixed_batches(tonight: list, replay: list, batch: int, steps: int, seed: int = 0):
    """Half tonight, half replay (all tonight when there is nothing to replay), like the toy nights."""
    rng = random.Random(seed)
    for _ in range(steps):
        if tonight and replay:
            b = [rng.choice(tonight) for _ in range(batch // 2)] + [rng.choice(replay) for _ in range(batch - batch // 2)]
        elif tonight or replay:
            src = tonight or replay
            b = [rng.choice(src) for _ in range(batch)]
        else:
            return
        yield b


def seatbelt(before: Dict[str, float], after: Optional[Dict[str, float]], max_drop: float = SEAT_DROP,
             tests: Iterable[str] = TESTS) -> Tuple[bool, dict, str]:
    drops, why = {}, []
    for k in tests:
        if not before or before.get(k) is None:
            continue
        a = (after or {}).get(k)
        if a is None or a != a:
            drops[k] = None
            why.append(f"{k} missing after")
            continue
        drops[k] = round(before[k] - a, 3)
        if drops[k] > max_drop:
            why.append(f"{k} dropped {drops[k]}")
    return (not why), drops, ("; ".join(why) or "ok")


def run_night(weights_path, manifest_path, *, train_fn: Callable, eval_fn: Callable, q8_eval_fn: Optional[Callable] = None,
              ledger_path=None, max_drop: float = SEAT_DROP, sense: str = "eye", should_stop: Callable[[], bool] = lambda: False,
              clock: Callable[[], float] = time.time, enc_version: Optional[int] = None) -> dict:
    """One sense's projector night. enc_version: current encoder-adapter version for this sense (AdapterStore.version) when an
    encoder adapter is in use; stale pooled features (older versions) are left out of tonight and replay. train_fn(weights_path, tonight, replay) updates the weights file in place.
    eval_fn(weights_path) / q8_eval_fn(weights_path) -> {"V1": .., "A1": .., "VID1": ..} on the fixed tests.
    should_stop: Ben's chat comes first (benFirst) -> stop before training and leave the weights untouched."""
    weights_path, manifest_path = Path(weights_path), Path(manifest_path)
    ledger_path = Path(ledger_path) if ledger_path else manifest_path.parent / "nights.jsonl"
    m = read_manifest(manifest_path)
    night = m.get("night") or manifest_path.stem.replace("practice-", "")
    feature_dir = m.get("featureDir") or str(manifest_path.parent)
    replay = []
    for n in kept_nights(ledger_path):
        p = manifest_path.parent / f"practice-{n}.json"
        if p.exists() and p != manifest_path:
            replay.append(read_manifest(p))
    tonight, old = practice_set(m, sense, feature_dir, replay, enc_version=enc_version)
    entry = {"night": night, "t": clock(), "sense": sense, "n_tonight": len(tonight), "n_replay": len(old), "source": "sleepmlx"}
    if not tonight:
        entry.update(kept=True, reason="nothing to practise", trained=False)
        return _log(ledger_path, entry)
    if should_stop():
        entry.update(kept=True, reason="stopped for Ben before training", trained=False)
        return _log(ledger_path, entry)
    backup = weights_path.with_name(weights_path.name + ".pre-night")
    shutil.copyfile(weights_path, backup)
    sha_before = sha256(weights_path)
    before = eval_fn(str(weights_path))
    q8_before = q8_eval_fn(str(weights_path)) if q8_eval_fn else None
    err = None
    try:
        train_fn(str(weights_path), tonight, old)
        after = eval_fn(str(weights_path))
        q8_after = q8_eval_fn(str(weights_path)) if q8_eval_fn else None
    except Exception as e:  # a crash undoes the night like a failed seatbelt
        err, after, q8_after = repr(e)[:300], None, None
    keep, drops, reason = seatbelt(before, after, max_drop)
    if keep and q8_eval_fn:
        k8, d8, r8 = seatbelt(q8_before, q8_after, max_drop)
        drops = {**drops, **{"q8_" + k: v for k, v in d8.items()}}
        if not k8:
            keep, reason = False, "q8: " + r8
    if err:
        keep, reason = False, "training failed: " + err
    quarantined = False
    if not keep:
        shutil.copyfile(backup, weights_path)
        if sha256(weights_path) != sha_before:
            raise RuntimeError("rollback did not restore the exact weights")
        q = manifest_path.with_name(manifest_path.name.replace(".json", ".quarantined.json"))
        os.replace(manifest_path, q)
        quarantined = True
    entry.update(trained=True, before=before, after=after, q8_before=q8_before, q8_after=q8_after, kept=keep, drops=drops,
                 reason=reason, quarantined=quarantined, sha_before=sha_before, sha_after=sha256(weights_path))
    os.replace(backup, weights_path.with_name(weights_path.name + ".prev"))  # one generation kept for a manual undo
    return _log(ledger_path, entry)


def _log(ledger_path: Path, entry: dict) -> dict:
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with open(ledger_path, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def make_mlx_train_fn(lm_loss: Callable, *, steps: int = 200, lr: float = 3e-4, batch: int = 8, seed: int = 0,
                      dtype: str = "bfloat16") -> Callable:
    """MLX trainer for a LLaVA-style projector file (fc1/fc2, GELU; premonition-projectors/mlx_projector.py).
    lm_loss(projector, media_embeds_input: mx.array (T, enc), caption: str) -> scalar mx.array: the caption's next-token loss
    from the bf16 Nanbeige copy with the projector output spliced in (mlx_projector.splice). Nanbeige stays frozen; only the
    projector trains. The weights file is rewritten in bf16; the day-time app loads it next to the q8 Nanbeige.
    Defaults mirror the toy night (lr 3e-4, half tonight / half replay). UNTESTED with a real model."""
    def train(weights_path, tonight, replay):
        import mlx.core as mx
        import mlx.nn as nn
        import mlx.optimizers as optim
        from mlx.utils import tree_flatten
        w = mx.load(weights_path)
        enc_dim, d = w["fc1.weight"].shape[1], w["fc1.weight"].shape[0]

        class Projector(nn.Module):
            def __init__(self):
                super().__init__()
                self.fc1 = nn.Linear(enc_dim, d)
                self.fc2 = nn.Linear(d, d)

            def __call__(self, x):
                return self.fc2(nn.gelu(self.fc1(x)))

        p = Projector()
        p.load_weights([(k, v.astype(mx.float32)) for k, v in w.items()], strict=True)
        opt = optim.AdamW(learning_rate=lr, weight_decay=1e-4)

        def loss_fn(model, items):
            tot = 0.0
            for feats, shape, caption in items:
                x = mx.array(feats, dtype=mx.float32).reshape(*(shape if len(shape) == 2 else (1, len(feats))))
                tot = tot + lm_loss(model, x, caption)
            return tot / len(items)

        vg = nn.value_and_grad(p, loss_fn)
        for items in mixed_batches(tonight, replay, batch, steps, seed):
            loss, grads = vg(p, items)
            opt.update(p, grads)
            mx.eval(p.parameters(), opt.state, loss)
        out_dtype = getattr(mx, dtype)
        tmp = weights_path + ".tmp.safetensors"
        mx.save_safetensors(tmp, {k: v.astype(out_dtype) for k, v in tree_flatten(p.parameters())})
        os.replace(tmp, weights_path)
    return train


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Validate a sense-sleep practice manifest (no training, no model).")
    ap.add_argument("manifest")
    a = ap.parse_args()
    mm = read_manifest(a.manifest)
    print(json.dumps({"night": mm.get("night"), "eye": len(mm.get("eye", [])), "ear": len(mm.get("ear", [])),
                      "replay": mm.get("replay", [])}))
