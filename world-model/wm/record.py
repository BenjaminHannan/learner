"""Record real Crafter transitions for the world-model harness (CPU, numpy)."""
import argparse
import os

import crafter
import numpy as np

MOVES = (1, 2, 3, 4)
OTHER = tuple(a for a in range(17) if a not in MOVES and a != 5)
TRAIN_WORLDS = list(range(160))
HELDOUT_WORLDS = list(range(1000, 1016))
TRAIN_PER_WORLD = 125
HELDOUT_PER_WORLD = 313
MAX_EPISODE = 250


def pool(o):
    return o.reshape(16, 4, 16, 4, 3).mean((1, 3)).astype(np.float64) / 255.0


def policy_step(rng):
    r = rng.random()
    if r < 0.50:
        return int(rng.integers(1, 5)), int(rng.integers(1, 5))
    if r < 0.75:
        return 5, 1
    return int(OTHER[rng.integers(len(OTHER))]), 1


def record_world(world, n_transitions, rng, next_episode_id):
    frames, actions, episode_id, world_id, t_index = [], [], [], [], []
    got, ep_idx = 0, 0
    while got < n_transitions:
        env = crafter.Env(seed=world * 1000 + ep_idx)
        obs = env.reset()
        ep_frames, ep_actions = [pool(obs)], []
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
                if done:
                    break
        n = len(ep_actions)
        frames.append(np.stack(ep_frames))
        actions.append(np.asarray(ep_actions, dtype=np.int64))
        episode_id.append(np.full(n + 1, next_episode_id, dtype=np.int64))
        world_id.append(np.full(n + 1, world, dtype=np.int64))
        t_index.append(np.arange(n + 1, dtype=np.int64))
        got += n
        next_episode_id += 1
        ep_idx += 1
    return dict(
        frames=np.concatenate(frames).astype(np.float16),
        actions=np.concatenate(actions),
        episode_id=np.concatenate(episode_id),
        world_id=np.concatenate(world_id),
        t_index=np.concatenate(t_index),
        next_episode_id=next_episode_id,
    )


def record_split(worlds, per_world, rng):
    parts, next_episode_id = [], 0
    for world in worlds:
        part = record_world(world, per_world, rng, next_episode_id)
        next_episode_id = part.pop("next_episode_id")
        parts.append(part)
        print(f"  world {world}: {len(part['actions'])} transitions, "
              f"{len(np.unique(part['episode_id']))} episodes")
    return {k: np.concatenate([p[k] for p in parts]) for k in parts[0]}


def save_split(out_dir, name, split):
    path = os.path.join(out_dir, name + ".npz")
    np.savez(path, frames=split["frames"], actions=split["actions"],
             episode_id=split["episode_id"], world_id=split["world_id"],
             t_index=split["t_index"])
    frames = split["frames"].astype(np.float32)
    moved = np.mean((frames[1:] - frames[:-1]) ** 2, axis=(1, 2, 3)) > 1e-6
    print(f"{name}: {len(np.unique(split['world_id']))} worlds, "
          f"{len(np.unique(split['episode_id']))} episodes, "
          f"{len(frames)} frames, {len(split['actions'])} transitions, "
          f"moved share {moved.mean():.3f} -> {path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data")
    ap.add_argument("--seed", type=int, default=1234)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    rng = np.random.default_rng(args.seed)
    print("train")
    train = record_split(TRAIN_WORLDS, TRAIN_PER_WORLD, rng)
    print("heldout")
    heldout = record_split(HELDOUT_WORLDS, HELDOUT_PER_WORLD, rng)
    save_split(args.out, "train", train)
    save_split(args.out, "heldout", heldout)


if __name__ == "__main__":
    main()
