#!/usr/bin/env python3
"""Bounded software/throughput checks authorized by pushed AR1 marks; no optimizer update."""
import json
import os
import platform
import random
import time
from collections import Counter

import torch

from auto_model import AutoNet, E, M, R
from run_experiment import generate_item, scheduled_kind, integrity_controls, encode, source_hashes, utc, HERE, write_json


def main():
    start_utc = utc()
    counts = {}
    expected = {
        "baseline": ((2500, 0, 0), (250, 2250, 0), (75, 75, 1350)),
        "late_replay": ((2500, 0, 0), (125, 2375, 0), (200, 75, 1225)),
    }
    for arm in expected:
        counts[arm] = {}
        for phase, n, want in zip(("A", "B", "C"), (2500, 2500, 1500), expected[arm]):
            got = Counter(scheduled_kind(arm, phase, step) for step in range(1, n + 1))
            assert tuple(got[k] for k in ("grids", "sums", "mazes")) == want
            counts[arm][phase] = dict(got)
            if arm == "baseline":
                for step in range(1, n + 1):
                    old = "grids" if phase == "A" else "sums" if phase == "B" else "mazes"
                    if phase != "A" and step % 10 == 0:
                        old = "grids" if phase == "B" else ("grids", "sums")[(step // 10) % 2]
                    assert scheduled_kind(arm, phase, step) == old
    torch.set_num_threads(4)
    torch.manual_seed(901)
    net = AutoNet().to("mps")
    rng = random.Random(902)
    rows = [encode(generate_item(rng, kind, size)) for kind, size in (("grids", 5), ("sums", 4), ("mazes", 7)) for _ in range(2)]
    controls = integrity_controls(net, rows)
    assert controls["pass"], controls
    timings = {}
    for kind, size in (("grids", 5), ("sums", 4), ("mazes", 7)):
        items = [generate_item(rng, kind, size) for _ in range(64)]
        t, s, y = [torch.tensor([getattr(it, field) for it in items], dtype=torch.long, device="mps")
                   for field in ("tokens", "slot", "target")]
        torch.mps.synchronize()
        start = time.monotonic()
        outputs = net.train_rounds(t, s, 4, 4)
        loss = torch.stack([R.ce_and_exact(logits, s, y)[0] + .5 * torch.nn.functional.binary_cross_entropy_with_logits(q.float(), R.ce_and_exact(logits, s, y)[1]) for logits, q in outputs]).mean()
        net.zero_grad(set_to_none=True)
        loss.backward()
        torch.mps.synchronize()
        timings[kind] = time.monotonic() - start
        assert torch.isfinite(loss)
        assert net.contexts.weight.grad is not None and net.contexts.weight.grad.abs().sum() > 0
        for block in net.blocks:
            assert any(p.grad is not None and p.grad.abs().sum() > 0 for p in block.parameters())
    result = dict(start_utc=start_utc, utc=utc(), pid=os.getpid(), machine=platform.node(),
                  pass_all=True, optimizer_updates=0, device="mps", counts=counts,
                  controls=controls, forward_backward_seconds=timings, source_hashes=source_hashes())
    path = HERE / "preflight-final.json"
    assert not path.exists(), "refuse overwrite"
    write_json(path, result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
