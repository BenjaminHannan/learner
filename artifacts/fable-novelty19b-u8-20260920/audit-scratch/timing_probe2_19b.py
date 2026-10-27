#!/usr/bin/env python3
"""Disposable timing probe v2: the cost of one update AT A FORCED NUMBER OF LOOKUPS.

Probe v1 showed that an untrained disposable model almost never calls the operator
(mean_calls ~= 0.09), so it measures only fixed overhead.  This probe replays the exact
body of the frozen `dispatcher_update` (train_table -> rollout_v4 -> policy_gradient_loss
-> backward -> step) at the registered batch shape, with a policy hook that forces every
episode to execute exactly `k` lookups.  k=5 stands for U5's typical length and k=8 for
U8's, so the ratio is the quantity the builder's 14-21 minute projection rests on.

Disposable model seed 9991, this folder's own rebuilt buffer copy, nothing written.

Usage: timing_probe2_19b.py <k> <updates>
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

K = int(sys.argv[1])
UPDATES = int(sys.argv[2])
SEED = 9991

TR.configure()
torch, V1, V3, V4 = TR.torch, TR.V1, TR.V3, TR.V4
buffers = HERE / 'buffers-1900'
record_store = N.load_buffer(buffers, 'U8')
order = TR.read_offline_order(buffers)
model, flags = TR.build_dispatcher(SEED)
optimizer = TR.dispatcher_optimizer(model)
generator = torch.Generator().manual_seed(TR.D_GENERATOR_BASE + SEED)
operator = TR.verified_operator()


def forcing(stop_after):
    def policy(step, tks, results, n_results):
        batch = tks.shape[0]
        everywhere = torch.ones(batch, dtype=torch.bool)
        want = 1 if step == stop_after - 1 else 0
        # position 1 is the subject and position 2 the first relation in EVERY question
        # of this grammar, so this forces a real lookup on every step
        return dict(subject=(torch.full((batch,), 1), everywhere),
                    operation=(torch.full((batch,), 2), everywhere),
                    stop=(torch.full((batch,), want), everywhere))
    return policy


feed = TR.offline_feed(record_store, order, 0, UPDATES)
times, calls = [], []
for i in range(UPDATES):
    rec = next(feed)
    began = time.monotonic()
    lr, beta = TR.dispatcher_schedule(i, TR.OFFLINE_UPDATES)
    for group in optimizer.param_groups:
        group['lr'] = lr
    items = rec['items']
    inputs = N.dispatcher_inputs(rec)
    questions = [it['question'] for it in items]
    owners = [it['owner'] for it in items]
    answers = torch.tensor([it['answer'] for it in items], dtype=torch.long)
    reps, visit_of = V1.representatives(owners)
    table = V3.train_table(operator, inputs, reps, TR.D_TRAIN_CAP)
    tokens, present = V1.pad_questions(questions)
    repeat = torch.arange(len(questions)).repeat_interleave(TR.D_K)
    episodes = V4.rollout_v4(model, tokens[repeat], present[repeat], table,
                             visit_of[repeat], TR.D_TRAIN_CAP, mode='sample',
                             generator=generator, flags=flags, policy=forcing(K))
    reward = (episodes.answer == answers[repeat]).float()
    loss, _shaped, _ent = V3.policy_gradient_loss(episodes, reward, TR.D_K,
                                                  TR.D_CALL_COST, beta)
    optimizer.zero_grad(set_to_none=True)
    loss.backward()
    torch.nn.utils.clip_grad_norm_(model.parameters(), TR.D_CLIP)
    optimizer.step()
    times.append(time.monotonic() - began)
    calls.append(float(sum(int(c) for c in episodes.calls)) / len(episodes.calls))

steady = times[1:] or times
print(json.dumps(dict(forced_lookups=K, updates=UPDATES,
                      episodes_per_update=len(episodes.calls),
                      mean_calls_measured=calls[-1],
                      seconds_per_update=sum(steady) / len(steady),
                      projected_2000_minutes=sum(steady) / len(steady) * 2000 / 60)),
      flush=True)
