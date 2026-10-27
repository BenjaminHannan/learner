#!/usr/bin/env python3
"""Registered AR2 software checks on an untrained model; zero optimizer updates."""
import io
import json
import os
import platform
import random
import subprocess
import time
from collections import Counter

import torch
import run_experiment as X


class TraceRandom(random.Random):
    def __init__(self, seed):
        super().__init__(seed)
        self.first_choice = None

    def choice(self, seq):
        value = super().choice(seq)
        if self.first_choice is None:
            self.first_choice = (list(seq), value)
        return value


def sampler_checks():
    observations = []
    grid_seeds = [next(s for s in range(901, 951)
                       if random.Random(s).choice([4, 5]) == size) for size in (4, 5)]
    cases = [(phase, "grids", seed) for phase in X.PHASES for seed in grid_seeds]
    cases += [("B", "sums", 907), ("C", "sums", 908), ("C", "mazes", 909)]
    for phase, kind, seed in cases:
        batches = {}
        for arm in X.ARMS:
            rng = TraceRandom(seed)
            sizes = Counter({key: 0 for key in X.SIZE_KEYS})
            rejects = Counter({key: 0 for key in X.KINDS})
            batch = X.training_batch(rng, kind, None, set(), rejects,
                                     arm=arm, phase=phase, size_batches=sizes)
            choices, drawn = rng.first_choice
            assert choices == {"grids": [4, 5], "sums": [1, 2, 3, 4],
                               "mazes": [5, 7]}[kind]
            expected = 5 if arm == "hard_grid_replay" and phase in ("B", "C") and kind == "grids" else drawn
            assert sizes[f"{kind}{expected}"] == 1 and sum(sizes.values()) == 1
            assert not any(rejects.values()) and batch[0].shape[0] == 64
            if kind == "grids":
                # The sealed 358g encoding appends a separator and symbol legend.
                assert tuple(batch[0].shape[1:]) == (expected + 2, expected)
            observations.append(dict(arm=arm, phase=phase, kind=kind,
                                     drawn=drawn, used=expected, size_batches=dict(sizes)))
            batches[arm] = batch
        if phase == "A" or kind != "grids":
            assert all(torch.equal(a, b) for a, b in zip(batches["baseline"], batches["hard_grid_replay"]))

    # Force rejection of the first valid grid5 item after an ordinary size-4 draw.
    seed = grid_seeds[0]
    probe = random.Random(seed)
    assert probe.choice([4, 5]) == 4
    first = X.generate_item(probe, "grids", 5)
    sizes = Counter({key: 0 for key in X.SIZE_KEYS})
    rejects = Counter({key: 0 for key in X.KINDS})
    batch = X.training_batch(random.Random(seed), "grids", None,
                             {X.fingerprint(first.tokens, first.slot)}, rejects,
                             arm="hard_grid_replay", phase="B", size_batches=sizes)
    assert rejects["grids"] >= 1 and sizes["grids5"] == 1 and sum(sizes.values()) == 1
    assert tuple(batch[0].shape) == (64, 7, 5)
    return dict(cases=observations, forced_rejection_counts=dict(rejects))


def main():
    assert X.REGISTRATION != "PENDING_REGISTRATION", "push and fill registration first"
    registered = subprocess.check_output(
        ["git", "show", f"{X.REGISTRATION}:artifacts/codex-autoroute-20260927/hard_replay/PASSMARKS.md"],
        cwd=X.REPO)
    assert registered == (X.HERE / "PASSMARKS.md").read_bytes()
    assert torch.backends.mps.is_available()
    torch.set_num_threads(4)
    start_utc = X.utc()
    counts = {}
    expected = ((2500, 0, 0), (250, 2250, 0), (75, 75, 1350))
    for arm in X.ARMS:
        counts[arm] = {}
        for phase, n, want in zip(X.PHASES, X.STEPS, expected):
            got = Counter(X.scheduled_kind(arm, phase, step) for step in range(1, n + 1))
            assert tuple(got[k] for k in X.KINDS) == want
            counts[arm][phase] = dict(got)
            for step in range(1, n + 1):
                old = "grids" if phase == "A" else "sums" if phase == "B" else "mazes"
                if phase != "A" and step % 10 == 0:
                    old = "grids" if phase == "B" else ("grids", "sums")[(step // 10) % 2]
                assert X.scheduled_kind(arm, phase, step) == old
    sampler = sampler_checks()
    torch.manual_seed(901)
    net = X.AutoNet().to("mps")
    rng = random.Random(902)
    rows = [X.encode(X.generate_item(rng, kind, size))
            for kind, size in (("grids", 5), ("sums", 4), ("mazes", 7)) for _ in range(2)]
    snapshot = io.BytesIO()
    torch.save(net.state_dict(), snapshot)
    snapshot.seek(0)
    controls = X.integrity_controls(net, rows, snapshot)
    assert controls["pass"], controls
    timings = {}
    for kind, size in (("grids", 5), ("sums", 4), ("mazes", 7)):
        items = [X.generate_item(rng, kind, size) for _ in range(64)]
        t, s, y = [torch.tensor([getattr(it, field) for it in items], dtype=torch.long, device="mps")
                   for field in ("tokens", "slot", "target")]
        torch.mps.synchronize()
        started = time.monotonic()
        outputs = net.train_rounds(t, s, 4, 4)
        losses = []
        for logits, q in outputs:
            ce, exact = X.R.ce_and_exact(logits, s, y)
            losses.append(ce + .5 * torch.nn.functional.binary_cross_entropy_with_logits(q.float(), exact))
        loss = torch.stack(losses).mean()
        net.zero_grad(set_to_none=True)
        loss.backward()
        torch.mps.synchronize()
        timings[kind] = time.monotonic() - started
        assert torch.isfinite(loss)
        assert net.contexts.weight.grad is not None and net.contexts.weight.grad.abs().sum() > 0
        for block in net.blocks:
            assert any(p.grad is not None and p.grad.abs().sum() > 0 for p in block.parameters())
    result = dict(start_utc=start_utc, utc=X.utc(), pid=os.getpid(), machine=platform.node(),
                  pass_all=True, optimizer_updates=0, device="mps", cpu_threads=4,
                  counts=counts, sampler=sampler, controls=controls,
                  forward_backward_seconds=timings, source_hashes=X.source_hashes())
    path = X.HERE / "preflight-final.json"
    assert not path.exists(), "refuse overwrite"
    X.write_json(path, result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
