"""Record Crafter day+night training data (300+ step episodes) and sealed unseen test worlds.
CPU-only, zero GPU/MPS use. Enforces >=12 GiB free disk guard before and after recording.
Never modifies legacy data splits; keeps world IDs 100% disjoint from 0..159 and 1000..1015.
"""
import argparse
import hashlib
import json
import os
import shutil
import stat
import sys

import crafter
import numpy as np

MOVES = (1, 2, 3, 4)
OTHER = tuple(a for a in range(17) if a not in MOVES and a != 5)

# Disjoint world IDs:
#   Legacy train (untouched):   0..159
#   Legacy heldout/dev (untouched): 1000..1015
#   New sealed unseen test:     2000..2015 (16 worlds x 350 steps = 5,600 transitions)
#   New day+night train:        3000..3079 (80 worlds x 350 steps = 28,000 transitions)
TRAIN_DN_WORLDS = list(range(3000, 3080))
SEALED_TEST_WORLDS = list(range(2000, 2016))
PER_WORLD = 350
MAX_EPISODE = 350  # Exceeds Crafter's 300-step full day/night cycle
MIN_FREE_GIB = 12.0


def check_disk(path):
    target = path if os.path.exists(path) else os.path.dirname(os.path.abspath(path))
    while not os.path.exists(target):
        target = os.path.dirname(target)
    free_gib = shutil.disk_usage(target).free / (1024 ** 3)
    print(f"[DISK] {target}: {free_gib:.2f} GiB free (floor {MIN_FREE_GIB:.1f} GiB)", flush=True)
    if free_gib < MIN_FREE_GIB:
        sys.exit(f"ABORT: free disk {free_gib:.2f} GiB < {MIN_FREE_GIB:.1f} GiB floor")
    return free_gib


def pool(o):
    return o.reshape(16, 4, 16, 4, 3).mean((1, 3)).astype(np.float64) / 255.0


def get_daylight(env):
    w = getattr(env, "_world", None)
    if w is not None and hasattr(w, "daylight"):
        return float(w.daylight)
    return float("nan")


def policy_step(rng):
    r = rng.random()
    if r < 0.50:
        return int(rng.integers(1, 5)), int(rng.integers(1, 5))
    if r < 0.75:
        return 5, 1
    return int(OTHER[rng.integers(len(OTHER))]), 1


def record_world(world, n_transitions, rng, next_episode_id):
    frames, actions, episode_id, world_id, t_index, daylight = [], [], [], [], [], []
    got, ep_idx = 0, 0
    while got < n_transitions:
        env = crafter.Env(seed=world * 1000 + ep_idx)
        obs = env.reset()
        ep_frames = [pool(obs)]
        ep_actions = []
        ep_daylight = [get_daylight(env)]
        budget = min(MAX_EPISODE, n_transitions - got)
        done = False
        while len(ep_actions) < budget and not done:
            action, hold = policy_step(rng)
            for _ in range(hold):
                if len(ep_actions) >= budget:
                    break
                obs, _, done, _ = env.step(action)
                ep_frames.append(pool(obs))
                ep_actions.append(action)
                ep_daylight.append(get_daylight(env))
                if done:
                    break
        n = len(ep_actions)
        frames.append(np.stack(ep_frames))
        actions.append(np.asarray(ep_actions, dtype=np.int64))
        episode_id.append(np.full(n + 1, next_episode_id, dtype=np.int64))
        world_id.append(np.full(n + 1, world, dtype=np.int64))
        t_index.append(np.arange(n + 1, dtype=np.int64))
        daylight.append(np.asarray(ep_daylight, dtype=np.float32))
        got += n
        next_episode_id += 1
        ep_idx += 1
    return dict(
        frames=np.concatenate(frames).astype(np.float16),
        actions=np.concatenate(actions),
        episode_id=np.concatenate(episode_id),
        world_id=np.concatenate(world_id),
        t_index=np.concatenate(t_index),
        daylight=np.concatenate(daylight),
        next_episode_id=next_episode_id,
    )


def record_split(worlds, per_world, rng):
    parts, next_episode_id = [], 0
    for idx_w, world in enumerate(worlds):
        part = record_world(world, per_world, rng, next_episode_id)
        next_episode_id = part.pop("next_episode_id")
        parts.append(part)
        if (idx_w + 1) % 16 == 0 or idx_w == len(worlds) - 1:
            print(f"  recorded {idx_w+1}/{len(worlds)} worlds (last={world}, total_eps={next_episode_id})", flush=True)
    return {k: np.concatenate([p[k] for p in parts]) for k in parts[0]}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def split_stats(split):
    """Within-episode moved share + actual light-level & action exposure counts (Fixes Bug A13)."""
    eid = split["episode_id"]
    same_ep = eid[1:] == eid[:-1]
    fr = split["frames"].astype(np.float32)
    diff_sq = np.mean((fr[1:] - fr[:-1]) ** 2, axis=(1, 2, 3))
    moved_within = diff_sq[same_ep] > 1e-6
    # Start-frame brightness and daylight for each transition
    start_mask = np.r_[same_ep, False]
    bright = fr[start_mask].mean(axis=(1, 2, 3))
    dl = split["daylight"][start_mask]
    t_idx = split["t_index"][start_mask]
    acts = split["actions"]
    assert len(acts) == int(same_ep.sum()), f"action count mismatch: {len(acts)} vs {int(same_ep.sum())}"
    dl_valid = np.isfinite(dl)
    return {
        "n_worlds": int(len(np.unique(split["world_id"]))),
        "world_id_min": int(split["world_id"].min()),
        "world_id_max": int(split["world_id"].max()),
        "n_episodes": int(len(np.unique(eid))),
        "n_frames": int(len(fr)),
        "n_transitions": int(len(acts)),
        "moved_share_within_ep": float(moved_within.mean()),
        "t_lt125_n": int((t_idx < 125).sum()),
        "t_125_to_249_n": int(((t_idx >= 125) & (t_idx < 250)).sum()),
        "t_ge250_n": int((t_idx >= 250).sum()),
        "brightness_lt25_25to38_ge38": [
            int((bright < 0.25).sum()),
            int(((bright >= 0.25) & (bright < 0.38)).sum()),
            int((bright >= 0.38).sum()),
        ],
        "daylight_lt04_04to08_ge08": (
            [int((dl < 0.4).sum()), int(((dl >= 0.4) & (dl < 0.8)).sum()), int((dl >= 0.8).sum())]
            if dl_valid.all() else None
        ),
        "daylight_min_mean_max": (
            [float(dl.min()), float(dl.mean()), float(dl.max())] if dl_valid.all() else None
        ),
        "action_counts": {str(a): int((acts == a).sum()) for a in range(17)},
    }


def save_split(out_dir, name, split, readonly=False):
    path = os.path.join(out_dir, name + ".npz")
    if os.path.exists(path):
        sys.exit(f"REFUSING to overwrite existing split: {path}")
    np.savez(
        path,
        frames=split["frames"],
        actions=split["actions"],
        episode_id=split["episode_id"],
        world_id=split["world_id"],
        t_index=split["t_index"],
        daylight=split["daylight"],
    )
    if readonly:
        os.chmod(path, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    digest = sha256_file(path)
    st = split_stats(split)
    st["sha256"] = digest
    st["bytes"] = int(os.path.getsize(path))
    st["path"] = path
    st["readonly"] = readonly
    print(f"[SAVED] {name}: {st['n_worlds']} worlds ({st['world_id_min']}..{st['world_id_max']}), "
          f"{st['n_transitions']} transitions, moved={st['moved_share_within_ep']:.3f}, "
          f"bright_buckets={st['brightness_lt25_25to38_ge38']}, daylight={st['daylight_lt04_04to08_ge08']}, "
          f"bytes={st['bytes']}, sha256={digest}", flush=True)
    return st


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--train-seed", type=int, default=5001)
    ap.add_argument("--sealed-seed", type=int, default=5002)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    free_before = check_disk(args.out)

    # Sanity-assert disjointness from legacy 0..159 and 1000..1015
    legacy = set(range(160)) | set(range(1000, 1016))
    assert not (set(TRAIN_DN_WORLDS) & legacy), "train_dn overlaps legacy worlds"
    assert not (set(SEALED_TEST_WORLDS) & legacy), "sealed_test overlaps legacy worlds"
    assert not (set(TRAIN_DN_WORLDS) & set(SEALED_TEST_WORLDS)), "train_dn overlaps sealed_test"

    print(f"Recording train_dn: worlds {TRAIN_DN_WORLDS[0]}..{TRAIN_DN_WORLDS[-1]}, "
          f"{PER_WORLD}/world, max_ep={MAX_EPISODE}, rng_seed={args.train_seed}", flush=True)
    tr_split = record_split(TRAIN_DN_WORLDS, PER_WORLD, np.random.default_rng(args.train_seed))
    tr_meta = save_split(args.out, "train_dn", tr_split, readonly=False)
    check_disk(args.out)

    print(f"Recording sealed_test: worlds {SEALED_TEST_WORLDS[0]}..{SEALED_TEST_WORLDS[-1]}, "
          f"{PER_WORLD}/world, max_ep={MAX_EPISODE}, rng_seed={args.sealed_seed}", flush=True)
    se_split = record_split(SEALED_TEST_WORLDS, PER_WORLD, np.random.default_rng(args.sealed_seed))
    se_meta = save_split(args.out, "sealed_test", se_split, readonly=True)
    free_after = check_disk(args.out)

    manifest = {
        "per_world": PER_WORLD,
        "max_episode": MAX_EPISODE,
        "train_seed": args.train_seed,
        "sealed_seed": args.sealed_seed,
        "disk_free_gib_before": round(free_before, 3),
        "disk_free_gib_after": round(free_after, 3),
        "train_dn": tr_meta,
        "sealed_test": se_meta,
    }
    mpath = os.path.join(args.out, "MANIFEST.json")
    with open(mpath, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"[MANIFEST] wrote {mpath} (sha256={sha256_file(mpath)})", flush=True)


if __name__ == "__main__":
    main()
