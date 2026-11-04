"""Sleep for the sense ENCODERS: nightly LoRA on the top layers of the ear (Whisper-small encoder) and eye (SigLIP2-base vision
tower), trained together with the projector in text-anchored cross-sense sleep, under the same seatbelt (toy track T4b, 2026-11-04).

Ben's rule (2026-11-04): every neural net in Glim trains in sleep, encoders included. The base encoder weights stay frozen and
untouched; the adapter is a SEPARATE file per sense (encoder-lora/<sense>.safetensors) that can be switched off in
encoder-lora/state.json. With no adapter file (or switched off) the encoder is exactly the stock one.

What the Desk stores (contract, see ENCODER_LORA_PLAN.md): for clips whose text passed the logic check, the MID-LAYER state of the
encoder below the adapted layers (float16, e.g. Whisper-small layer 8 of 12: frames x 768; SigLIP2 layer 8: 256 x 768), in
states-<day>.bin, referenced from the night's manifest encpractice-<night>.json under "eye_states" / "ear_states"
(separate from the projector manifests, so a quarantine here never hides projector practice). Never raw pictures or audio.
These files are kept only for a short window (purge_states) because they are bigger than pooled features.

Why mid-layer states and not the usual pooled features: when the adapter changes, features computed by the OLD encoder are stale.
Mid-layer states sit BELOW the adapter, so they stay valid and are re-encoded through the current adapter at every training step.
Projector replay items that have only old pooled features (encVersion older than the current adapter) are dropped from replay
(stale_filter); the Desk's day-time pooled features are re-made by the day-time model with the new adapter from the next day on.

One night for one sense (run_night):
  1. back up projector + adapter bytes (sha256; a missing adapter is remembered as missing);
  2. score the fixed tests (V1 / A1 / VID1) on bf16 (and q8 if given), with the adapter on;
  3. train adapter + projector on tonight's anchored states + replay of earlier KEPT nights still inside the window;
  4. score again; any drop > 2 points, a missing score, a q8 drop, or a crash -> restore both files byte for byte (delete the adapter
     if there was none), quarantine the manifest, keep the adapter version;
  5. on keep: adapter version + 1 (state.json), so older pooled features are known to be stale; info score with the adapter off;
  6. append one line to sense-sleep/encoder-nights.jsonl.

Toy evidence (premonition-sleeplab-t4/encoders, NOT real-model evidence): see REPORT.md there. Pure Python: imports and unit tests
run without numpy or MLX. make_mlx_train_fn is lazy and was run only on a tiny fake encoder + fake loss (no real model loaded).
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
SENSES = ("eye", "ear")
MAX_STATE_VALUES = 1500 * 768          # one 30 s Whisper window at layer k
DEFAULT_WINDOW_DAYS = 2
DEFAULT_MAX_BYTES = 400 * 1024 * 1024  # per sense directory


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------- adapter store (separate, switchable) ----------------
class AdapterStore:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.state_path = self.root / "state.json"

    def path(self, sense: str) -> Path:
        if sense not in SENSES:
            raise ValueError(f"unknown sense {sense}")
        return self.root / f"{sense}.safetensors"

    def _state(self) -> dict:
        if self.state_path.exists():
            return json.loads(self.state_path.read_text())
        return {}

    def _write(self, st: dict):
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(st, indent=1, sort_keys=True))
        os.replace(tmp, self.state_path)

    def info(self, sense: str) -> dict:
        return {"enabled": True, "version": 0, **self._state().get(sense, {})}

    def enabled(self, sense: str) -> bool:
        return bool(self.info(sense)["enabled"])

    def version(self, sense: str) -> int:
        return int(self.info(sense)["version"])

    def set_enabled(self, sense: str, on: bool):
        st = self._state(); st.setdefault(sense, {"enabled": True, "version": 0})["enabled"] = bool(on); self._write(st)

    def bump(self, sense: str, sha: str) -> int:
        st = self._state(); e = st.setdefault(sense, {"enabled": True, "version": 0})
        e["version"] = int(e.get("version", 0)) + 1; e["sha"] = sha; self._write(st)
        return e["version"]

    def projector_before_path(self, sense: str) -> Path:
        """Copy of the projector taken just before this sense's FIRST adapter night. The projector co-adapts to the adapter (toy:
        adapter off at the end gave A1 ~60 vs ~63 at the start), so switching the adapter off must also bring this projector back."""
        return self.root / f"{sense}.projector-before-adapter.safetensors"

    def switch_off(self, sense: str, projector_path) -> dict:
        """Turn the encoder adapter off for a sense: disable it and restore the projector from before the adapter (if kept).
        The adapter file itself is kept (switch back on = set_enabled(sense, True) + the projector that matches it in *.prev)."""
        self.set_enabled(sense, False)
        pb = self.projector_before_path(sense)
        restored = False
        if pb.exists():
            cur = Path(projector_path)
            shutil.copyfile(cur, cur.with_name(cur.name + ".with-adapter"))
            shutil.copyfile(pb, cur)
            restored = True
        return {"sense": sense, "enabled": False, "projector_restored": restored}

    def active_path(self, sense: str) -> Optional[str]:
        """What the day-time model should load: the adapter file if it exists and is enabled, else None (stock encoder)."""
        p = self.path(sense)
        return str(p) if (p.exists() and self.enabled(sense)) else None


# ---------------- manifest + states ----------------
def read_manifest(path) -> dict:
    m = json.loads(Path(path).read_text())
    if m.get("dtype") != "float16":
        raise ValueError("manifest dtype must be float16")
    for sense in SENSES:
        for e in m.get(f"{sense}_states", []):
            for k in ("day", "off", "shape", "label", "layer"):
                if k not in e:
                    raise ValueError(f"{sense}_states entry missing {k}")
            shp = [int(x) for x in e["shape"]]
            if len(shp) != 2 or shp[0] <= 0 or shp[1] <= 0 or shp[0] * shp[1] > MAX_STATE_VALUES:
                raise ValueError("bad state shape")
            if str(e["label"]).strip().lower().startswith("maybe"):
                raise ValueError("a maybe never trains")
    return m


def load_state(states_dir, entry) -> Tuple[List[float], List[int]]:
    p = Path(states_dir) / f"states-{entry['day']}.bin"
    shp = [int(x) for x in entry["shape"]]
    n = shp[0] * shp[1]
    with open(p, "rb") as f:
        f.seek(int(entry["off"]))
        raw = f.read(2 * n)
    if len(raw) != 2 * n:
        raise ValueError(f"short read in {p.name}")
    return list(struct.unpack(f"<{n}e", raw)), shp


def purge_states(states_dir, today: str, keep_days: int = DEFAULT_WINDOW_DAYS, max_bytes: int = DEFAULT_MAX_BYTES,
                 clock_days: Optional[Callable[[str], int]] = None) -> List[str]:
    """Delete states-<day>.bin older than keep_days (by ISO date) and then the oldest files until the total is <= max_bytes.
    Mid-layer states are bigger than pooled features and are kept only for this short window."""
    import datetime as dt
    d = Path(states_dir)
    if not d.exists():
        return []
    to_day = clock_days or (lambda s: dt.date.fromisoformat(s).toordinal())
    files = sorted(d.glob("states-*.bin"), key=lambda p: p.stem[len("states-"):])
    t = to_day(today)
    gone = []
    for p in list(files):
        day = p.stem[len("states-"):]
        try:
            age = t - to_day(day)
        except ValueError:
            continue
        if age >= keep_days:
            p.unlink(); gone.append(p.name); files.remove(p)
    total = sum(p.stat().st_size for p in files)
    for p in list(files):
        if total <= max_bytes:
            break
        total -= p.stat().st_size; p.unlink(); gone.append(p.name); files.remove(p)
    return gone


def stale_filter(entries: Iterable[dict], current_version: int) -> Tuple[list, int]:
    """Projector replay entries made from POOLED features by an older adapter are stale: drop them (count returned).
    Entries without encVersion are from before any adapter (version 0)."""
    keep, dropped = [], 0
    for e in entries:
        if int(e.get("encVersion", 0)) == int(current_version):
            keep.append(e)
        else:
            dropped += 1
    return keep, dropped


def kept_nights(ledger_path, sense: str) -> List[str]:
    p = Path(ledger_path)
    if not p.exists():
        return []
    out = []
    for l in p.read_text().splitlines():
        if l.strip():
            j = json.loads(l)
            if j.get("kept") and j.get("trained") and j.get("sense") == sense:
                out.append(j["night"])
    return out


def practice_set(manifest: dict, sense: str, states_dir, replay: Iterable[dict] = ()) -> Tuple[list, list]:
    """(tonight, replay) lists of (state values, shape, label). Replay = earlier kept nights whose state files still exist."""
    def load(entries):
        out = []
        for e in entries:
            try:
                v, shp = load_state(states_dir, e)
            except FileNotFoundError:
                continue  # outside the window: purged
            out.append((v, shp, e["label"]))
        return out
    tonight = load(manifest.get(f"{sense}_states", []))
    old = []
    for m in replay:
        old.extend(load(m.get(f"{sense}_states", [])))
    return tonight, old


def mixed_batches(tonight: list, replay: list, batch: int, steps: int, seed: int = 0):
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
            drops[k] = None; why.append(f"{k} missing after"); continue
        drops[k] = round(before[k] - a, 3)
        if drops[k] > max_drop:
            why.append(f"{k} dropped {drops[k]}")
    return (not why), drops, ("; ".join(why) or "ok")


# ---------------- one night ----------------
def run_night(projector_path, manifest_path, store: AdapterStore, *, sense: str, train_fn: Callable, eval_fn: Callable,
              q8_eval_fn: Optional[Callable] = None, ledger_path=None, max_drop: float = SEAT_DROP,
              should_stop: Callable[[], bool] = lambda: False, clock: Callable[[], float] = time.time) -> dict:
    """train_fn(projector_path, adapter_path, tonight, replay) rewrites BOTH files (it creates the adapter if missing).
    eval_fn(projector_path, adapter_path_or_None) / q8_eval_fn(...) -> {"V1":.., "A1":.., "VID1":..} on the fixed tests (the
    test media are re-encoded through the current adapter every time). should_stop: benFirst -> no training, files untouched."""
    projector_path, manifest_path = Path(projector_path), Path(manifest_path)
    ledger_path = Path(ledger_path) if ledger_path else manifest_path.parent / "encoder-nights.jsonl"
    m = read_manifest(manifest_path)
    night = m.get("night") or manifest_path.stem.replace("encpractice-", "")
    states_dir = m.get("statesDir") or str(manifest_path.parent)
    adapter = store.path(sense)
    entry = {"night": night, "t": clock(), "sense": sense, "source": "sleepmlx", "kind": "encoder-lora",
             "enc_version_before": store.version(sense)}
    if not store.enabled(sense):
        entry.update(kept=True, trained=False, reason="adapter switched off")
        return _log(ledger_path, entry)
    replay = []
    for n in kept_nights(ledger_path, sense):
        p = manifest_path.parent / f"encpractice-{n}.json"
        if p.exists() and p != manifest_path:
            replay.append(read_manifest(p))
    tonight, old = practice_set(m, sense, states_dir, replay)
    entry.update(n_tonight=len(tonight), n_replay=len(old))
    if not tonight:
        entry.update(kept=True, trained=False, reason="nothing to practise")
        return _log(ledger_path, entry)
    if should_stop():
        entry.update(kept=True, trained=False, reason="stopped for Ben before training")
        return _log(ledger_path, entry)
    had_adapter = adapter.exists()
    if not had_adapter and not store.projector_before_path(sense).exists():
        shutil.copyfile(projector_path, store.projector_before_path(sense))
    pb = projector_path.with_name(projector_path.name + ".pre-night")
    ab = adapter.with_name(adapter.name + ".pre-night")
    shutil.copyfile(projector_path, pb)
    if had_adapter:
        shutil.copyfile(adapter, ab)
    sha_p, sha_a = sha256(projector_path), (sha256(adapter) if had_adapter else None)
    a_in = str(adapter) if had_adapter else None
    before = eval_fn(str(projector_path), a_in)
    q8_before = q8_eval_fn(str(projector_path), a_in) if q8_eval_fn else None
    err, after, q8_after = None, None, None
    try:
        train_fn(str(projector_path), str(adapter), tonight, old)
        if not adapter.exists():
            raise RuntimeError("train_fn wrote no adapter")
        after = eval_fn(str(projector_path), str(adapter))
        q8_after = q8_eval_fn(str(projector_path), str(adapter)) if q8_eval_fn else None
    except Exception as e:
        err = repr(e)[:300]
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
        shutil.copyfile(pb, projector_path)
        if had_adapter:
            shutil.copyfile(ab, adapter)
        elif adapter.exists():
            adapter.unlink()
        if sha256(projector_path) != sha_p or (had_adapter and sha256(adapter) != sha_a) or (not had_adapter and adapter.exists()):
            raise RuntimeError("rollback did not restore the exact weights")
        q = manifest_path.with_name(manifest_path.name.replace(".json", ".quarantined.json"))
        os.replace(manifest_path, q)
        quarantined = True
    else:
        entry["enc_version_after"] = store.bump(sense, sha256(adapter))
        try:
            entry["adapter_off"] = eval_fn(str(projector_path), None)  # info: how much of the score is the adapter
        except Exception as e:
            entry["adapter_off"] = {"error": repr(e)[:120]}
    entry.update(trained=True, before=before, after=after, q8_before=q8_before, q8_after=q8_after, kept=keep, drops=drops,
                 reason=reason, quarantined=quarantined, had_adapter=had_adapter,
                 sha_projector=sha256(projector_path), sha_adapter=(sha256(adapter) if adapter.exists() else None))
    os.replace(pb, projector_path.with_name(projector_path.name + ".prev"))
    if had_adapter:
        os.replace(ab, adapter.with_name(adapter.name + ".prev"))
    return _log(ledger_path, entry)


def _log(ledger_path: Path, entry: dict) -> dict:
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with open(ledger_path, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


# ---------------- MLX trainer (lazy; UNTESTED with a real model) ----------------
def adapter_key(name: str) -> str:
    """Layer names like 'blocks.8.attn.query' are stored as 'blocks__8__attn__query' (dots would nest in safetensors trees).
    File keys: layers.<adapter_key>.A (rank x in) and layers.<adapter_key>.B (out x rank)."""
    return name.replace(".", "__")


def make_mlx_train_fn(upper_fn: Callable, pool_fn: Callable, lm_loss: Callable, *, lora_shapes: Dict[str, Tuple[int, int]],
                      rank: int = 8, alpha: float = 16.0, steps: int = 200, lr_lora: float = 1e-3, lr_proj: float = 3e-4,
                      batch: int = 8, seed: int = 0, dtype: str = "bfloat16") -> Callable:
    """Joint adapter + projector trainer.
    upper_fn(states: mx.array (T, D), lora: dict name -> (A, B, scale)) -> last_hidden_state (T', D): the FROZEN top encoder
      layers (e.g. Whisper-small blocks 8..11 + final layer norm, SigLIP2 blocks 8..11 + post layernorm) with y = W x + scale*B(A x)
      added on each named linear (e.g. 'blocks.8.attn.query'). Supplied by the lead (model-specific wiring).
    pool_fn: mlx_projector.pool_whisper / pool_siglip. lm_loss(projector, media_tokens, caption) -> scalar (bf16 Nanbeige, frozen).
    lora_shapes: name -> (out_features, in_features). A ~ N(0, 1/in), B = 0, so a fresh adapter is a no-op."""
    def train(projector_path, adapter_path, tonight, replay):
        import mlx.core as mx
        import mlx.nn as nn
        import mlx.optimizers as optim
        from mlx.utils import tree_flatten, tree_unflatten
        w = mx.load(projector_path)
        enc_dim, d = w["fc1.weight"].shape[1], w["fc1.weight"].shape[0]

        class Projector(nn.Module):
            def __init__(self):
                super().__init__()
                self.fc1 = nn.Linear(enc_dim, d)
                self.fc2 = nn.Linear(d, d)

            def __call__(self, x):
                return self.fc2(nn.gelu(self.fc1(x)))

        class Lora(nn.Module):
            def __init__(self):
                super().__init__()
                mx.random.seed(seed)
                self.layers = {adapter_key(n): {"A": mx.random.normal((rank, i)) / (i ** 0.5), "B": mx.zeros((o, rank))}
                               for n, (o, i) in lora_shapes.items()}

        p, lo = Projector(), Lora()
        p.load_weights([(k, v.astype(mx.float32)) for k, v in w.items()], strict=True)
        if os.path.exists(adapter_path):
            aw = mx.load(adapter_path)
            lo.update(tree_unflatten([(k, v.astype(mx.float32)) for k, v in aw.items()]))
        scale = alpha / rank

        class Both(nn.Module):
            def __init__(self):
                super().__init__()
                self.p, self.lo = p, lo

        model = Both()
        opt = optim.MultiOptimizer([optim.AdamW(learning_rate=lr_lora, weight_decay=0.0),
                                    optim.AdamW(learning_rate=lr_proj, weight_decay=1e-4)],
                                   [lambda path, _: path.startswith("lo.")])

        def loss_fn(mdl, items):
            tot = 0.0
            for vals, shp, caption in items:
                x = mx.array(vals, dtype=mx.float32).reshape(*shp)
                lora = {n: (mdl.lo.layers[adapter_key(n)]["A"], mdl.lo.layers[adapter_key(n)]["B"], scale) for n in lora_shapes}
                h = pool_fn(upper_fn(x, lora)[None])[0]
                tot = tot + lm_loss(mdl.p, h, caption)
            return tot / len(items)

        vg = nn.value_and_grad(model, loss_fn)
        for items in mixed_batches(tonight, replay, batch, steps, seed):
            loss, grads = vg(model, items)
            opt.update(model, grads)
            mx.eval(model.parameters(), opt.state, loss)
        out_dtype = getattr(mx, dtype)
        for path, params in ((projector_path, p.parameters()), (adapter_path, lo.parameters())):
            tmp = path + ".tmp.safetensors"
            mx.save_safetensors(tmp, {k: v.astype(out_dtype) for k, v in tree_flatten(params)})
            os.replace(tmp, path)
    return train
