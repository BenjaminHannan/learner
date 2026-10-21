#!/usr/bin/env python3
"""G0b: G0 with a probe trained on N_NAMES=512 training names (disjoint from the 8 test names).

Design and pass mark are fixed in G0B-CARD.md, committed before this was run. $0, CPU only.
Usage: python g0b_probe.py --out ../results/trial2/g0b.json [--steps 600]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "task"))
import torch  # noqa: E402
import torch.nn as nn  # noqa: E402
import torch.nn.functional as F  # noqa: E402
import toy  # noqa: E402

SEEDS = (110, 111, 112)
N_NAMES = 512
PASS_MEAN, PASS_MIN, C1_MIN, C2_MAX = 0.60, 0.50, 0.90, 0.20
N_TRAIN_VISITS, N_TEST_VISITS, BATCH_LINES = 4000, 1024, 512


class PositionProbe(nn.Module):
    """Sees one line's states [L, d] only; one logit per position."""

    def __init__(self, d: int, hidden: int = 64):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(2 * d, hidden), nn.GELU(), nn.Linear(hidden, 1))

    def forward(self, states):                          # [N, L, d]
        ctx = states.mean(dim=1, keepdim=True).expand_as(states)
        return self.net(torch.cat([states, ctx], dim=-1)).squeeze(-1)


def person_pos(roles):                                  # [N, L] -> [N]
    return (roles == 1).float().argmax(dim=-1)


def lines_and_labels(c, v, reader, n, novel, g):
    lines, roles, _, _ = toy.make_visits(c, v, n, novel=novel, g=g)
    with torch.no_grad():
        states = reader(lines)
    return states.flatten(0, 1), person_pos(roles.flatten(0, 1))


def train_probe(c, states, labels, steps, seed, shuffle_labels=False):
    torch.manual_seed(seed)
    if shuffle_labels:
        labels = labels[torch.randperm(len(labels))]
    probe = PositionProbe(c.d)
    opt = torch.optim.Adam(probe.parameters(), lr=3e-3)
    for _ in range(steps):
        idx = torch.randint(len(labels), (BATCH_LINES,))
        loss = F.cross_entropy(probe(states[idx]), labels[idx])
        opt.zero_grad()
        loss.backward()
        opt.step()
    return probe


def acc(probe, states, labels):
    with torch.no_grad():
        return float((probe(states).argmax(-1) == labels).float().mean())


def run_seed(seed: int, steps: int) -> dict:
    c = toy.ToyConfig(n_ent_train=N_NAMES)
    torch.manual_seed(seed)
    g = torch.Generator().manual_seed(10_000 + seed)
    v = toy.Vocab(c)
    reader = toy.FrozenReader(c, v.size, g)
    gd = torch.Generator().manual_seed(40_000 + seed)
    train_ids, test_ids = set(range(c.n_ent_train)), set(range(c.n_ent_train, c.n_ent_train + c.n_ent_novel))
    assert not (train_ids & test_ids) and len(train_ids) == N_NAMES and len(test_ids) == 8
    fam_tr = lines_and_labels(c, v, reader, N_TRAIN_VISITS, False, gd)
    fam_te = lines_and_labels(c, v, reader, N_TEST_VISITS, False, gd)
    nov_tr = lines_and_labels(c, v, reader, N_TRAIN_VISITS, True, gd)
    nov_te = lines_and_labels(c, v, reader, N_TEST_VISITS, True, gd)
    main = train_probe(c, *fam_tr, steps, seed)
    shuffled = train_probe(c, *fam_tr, steps, seed, shuffle_labels=True)
    upper = train_probe(c, *nov_tr, steps, seed)
    return {
        "seed": seed,
        "probe_numbers": sum(p.numel() for p in main.parameters()),
        "novel_pos_acc": acc(main, *nov_te),
        "train_lines_pos_acc": acc(main, *fam_tr),
        "c1_familiar_pos_acc": acc(main, *fam_te),
        "c2_shuffled_novel_pos_acc": acc(shuffled, *nov_te),
        "info_trained_on_novel_pos_acc": acc(upper, *nov_te),
    }


def verdict(rows: list[dict]) -> dict:
    mean = lambda k: sum(r[k] for r in rows) / len(rows)
    novel = [r["novel_pos_acc"] for r in rows]
    controls_ok = mean("c1_familiar_pos_acc") >= C1_MIN and mean("c2_shuffled_novel_pos_acc") <= C2_MAX
    passed = mean("novel_pos_acc") >= PASS_MEAN and min(novel) >= PASS_MIN
    return {"mean_novel": mean("novel_pos_acc"), "min_novel": min(novel),
            "mean_c1": mean("c1_familiar_pos_acc"), "mean_c2": mean("c2_shuffled_novel_pos_acc"),
            "mean_train_lines": mean("train_lines_pos_acc"),
            "controls_ok": controls_ok,
            "result": ("INVALID" if not controls_ok else "PASS" if passed else "FAIL")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE.parent / "results" / "trial2" / "g0b.json"))
    ap.add_argument("--steps", type=int, default=600)
    a = ap.parse_args()
    torch.set_num_threads(4)
    rows = [run_seed(s, a.steps) for s in SEEDS]
    out = {"steps": a.steps, "n_train_names": N_NAMES, "marks": {"mean": PASS_MEAN, "min": PASS_MIN, "c1_min": C1_MIN, "c2_max": C2_MAX},
           "rows": rows, "verdict": verdict(rows)}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=2))
    print(json.dumps(out["verdict"], indent=2))
    for r in rows:
        print(r)


if __name__ == "__main__":
    main()
