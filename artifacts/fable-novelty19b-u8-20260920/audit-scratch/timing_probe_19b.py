#!/usr/bin/env python3
"""Disposable timing probe: seconds per offline update for one arm.

Uses a DISPOSABLE-SEED model (9991), reads only this audit folder's own rebuilt buffer
copy, writes no checkpoint, no run directory and no registered artifact.  This is a
benchmark of the frozen update, not a run of the registered experiment.

Usage: timing_probe_19b.py <arm> <updates>
"""
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))

import fable_novelty19_train as TR      # noqa: E402
import fable_novelty19_data as N        # noqa: E402

arm = sys.argv[1]
updates = int(sys.argv[2])
SEED = 9991                              # disposable model seed, never a registered one

TR.configure()
buffers = HERE / 'buffers-1900'
record = N.load_buffer(buffers, arm)
order = TR.read_offline_order(buffers)
model, flags = TR.build_dispatcher(SEED)
optimizer = TR.dispatcher_optimizer(model)
generator = TR.torch.Generator().manual_seed(TR.D_GENERATOR_BASE + SEED)
operator = TR.verified_operator()

feed = TR.offline_feed(record, order, 0, updates)
times, calls = [], []
for i in range(updates):
    row_in = next(feed)
    began = time.monotonic()
    row = TR.dispatcher_update(model, flags, operator, optimizer, generator, row_in,
                               i, TR.OFFLINE_UPDATES)
    times.append(time.monotonic() - began)
    calls.append(float(row['mean_calls']))

steady = times[1:] or times
out = dict(arm=arm, updates=updates, seed=SEED,
           seconds_per_update=sum(steady) / len(steady),
           first_update_seconds=times[0],
           mean_calls_first=calls[0], mean_calls_last=calls[-1],
           projected_2000_minutes=sum(steady) / len(steady) * 2000 / 60)
print(json.dumps(out), flush=True)
