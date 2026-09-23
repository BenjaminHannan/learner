"""Correctness checks for the OPTIONAL `--evidence-aux` loss of
scripts/fable_baseline_transformer.py.

That script is hash-frozen (artifacts/fable-baseline-transformer-20260920/FREEZE.sha256)
and no registered arm uses `--evidence-aux`; the existing suite only smoke-tests that it
produces a finite number.  This file is additive and tests what it actually does.

Plain script.  Run it; it prints one line per check and ends with
`ALL N CHECKS PASSED` or raises.  It writes nothing and trains nothing: every check runs
on at most 8 questions with a width-8 / 2-layer toy model, or on hand-built attention
tensors fed straight to `B.evidence_loss`.

METHOD.  The targeting is probed, not read off the source.  A synthetic attention tensor
is built that places all of a position's mass on the flat story positions of ONE row,
where the row offsets are recomputed in this file from the raw row lengths (never from
`Story.flat_row`).  Because `evidence_loss` is `-log(mass on the gold row)`, a hypothesis
about "which position is scored against which row" is correct exactly when that synthetic
tensor drives the loss to 0, and any single-step perturbation of the hypothesis must make
it large.  That pins the mapping down in both directions.

WHAT THE IMPLEMENTATION MEANS BY "OUTPUT POSITION" (checked, and worth stating because
the wording in the build brief is ambiguous): the scored position for output token j is
`q_len + j - 1`, i.e. the position that PREDICTS that token, not the position that HOLDS
it.  For j = 0 that is the question's final ANSWER token.  The position holding the final
answer `y` -- the one that predicts END -- is NOT scored.
"""
from __future__ import annotations

import math
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

import fable_baseline_transformer as B                                      # noqa: E402

V3 = B.V3
torch = B.torch
F = B.F

WORLD, LINK = B.WORLD, B.LINK
TINY = dict(positions='line', width=8, layers=2, heads=2, hidden=16)

CHECKS = 0


def check(label, condition, detail=''):
    global CHECKS
    if not condition:
        raise AssertionError(f'{label} FAILED {detail}')
    CHECKS += 1
    print(f'  ok  {label}{(" -- " + detail) if detail else ""}')


def banner(text):
    print(f'\n{text}')


# --------------------------------------------------------------------------- helpers


def flat_span(rows, index):
    """The flat story positions of row `index`, recomputed from the raw row lengths.

    Independent of Story.flat_row / Story.source on purpose: those are what is under test.
    """
    start = sum(len(row) for row in rows[:index])
    return list(range(start, start + len(rows[index])))


def blank_weights(batch, heads=2):
    """[Q, H, U, S+U] attention with every position's mass parked on the LAST own-stream
    key, so no story row is credited anywhere until a check puts mass somewhere."""
    q, u = batch.seq.shape
    s = batch.story.flat.shape[1]
    weights = torch.zeros(q, heads, u, s + u)
    weights[:, :, :, s + u - 1] = 1.
    return weights


def place(weights, batch, stories, item_index, position, row_index, amount=1., head=None):
    """Move `amount` of one position's mass onto the flat span of one story row."""
    s = batch.story.flat.shape[1]
    span = flat_span(stories[int(batch.owner[item_index])], row_index)
    heads = range(weights.shape[1]) if head is None else [head]
    for h in heads:
        weights[item_index, h, position, s + weights.shape[2] - 1] -= amount
        for column in span:
            weights[item_index, h, position, column] += amount / len(span)


def gold_weights(batch, stories, items, heads=2):
    """All mass, at every scored position, on that step's gold supporting row."""
    weights = blank_weights(batch, heads)
    for i, item in enumerate(items):
        for j in range(len(item['chain'])):
            place(weights, batch, stories, i, int(batch.q_len[i]) + j - 1,
                  item['support'][j])
    return weights


def toy_batch(seed='evidence-aux', visits=2):
    rng = random.Random(seed)
    stories, items = B.training_items(rng, visits=visits, support=True)
    return stories, items, B.pack_batch(stories, items, 'steps', support=True)


def grads(model, closure):
    for parameter in model.parameters():
        parameter.grad = None
    loss = closure()
    loss.backward()
    return float(loss.detach()), {name: p.grad.detach().clone()
                                  for name, p in model.named_parameters() if p.grad is not None}


# --------------------------------------------------------------------------- checks


def check_support_rows(stories, items, batch):
    banner('1. THE RECORDED SUPPORTING ROW IS THE TRUTH CHAIN\'S OWN ROW')
    kinds, unique, matched, ends, interpreted = True, True, True, True, True
    hops_seen = set()
    for i, item in enumerate(items):
        rows = stories[item['owner']]
        chain = V3.interpret(rows, [True] * len(rows), item['question'])
        interpreted &= chain == item['chain']
        k = len(chain)
        hops_seen.add(k)
        for j, (subject, op, result) in enumerate(chain):
            index = int(batch.support[i, j])
            matched &= index >= 0 and list(rows[index][:4]) == [WORLD, subject, op, result]
            # an intermediate step must be licensed by a LINK row, the last by the
            # terminal attribute row the question asked for
            kinds &= (op == LINK) if j < k - 1 else (op == item['question'][-2])
            kinds &= rows[index][2] == op
            unique &= sum(1 for row in rows if len(row) >= 4 and row[0] == WORLD
                          and row[1] == subject and row[2] == op) == 1
        ends &= all(int(batch.support[i, j]) == -1 for j in range(k, B.MAX_OUT))
    check('the chain used for supervision is the exact interpreter\'s chain', interpreted)
    check('every step\'s recorded row is the row [WORLD, subject, op, result]', matched,
          f'{len(items)} questions, hop counts {sorted(hops_seen)}')
    check('intermediate steps are licensed by LINK rows, the last by the terminal '
          'attribute row', kinds)
    check('no other row in the world could license the same (subject, op)', unique)
    check('slots past the chain (the END-predicting position and beyond) are -1', ends,
          f'columns k..{B.MAX_OUT - 1} of batch.support')


def check_targeting(stories, items, batch):
    banner('2. WHICH POSITION IS SCORED AGAINST WHICH ROW  (probed, not read off source)')
    gold = gold_weights(batch, stories, items)
    base = float(B.evidence_loss(batch, gold))
    check('all mass on every step\'s gold row drives the loss to 0', base < 1e-5,
          f'loss {base:.2e}')

    shifted = blank_weights(batch)
    for i, item in enumerate(items):
        for j in range(len(item['chain'])):
            place(shifted, batch, stories, i, int(batch.q_len[i]) + j, item['support'][j])
    check('shifting the same mass one position later collapses it',
          float(B.evidence_loss(batch, shifted)) > 15.,
          f'loss {float(B.evidence_loss(batch, shifted)):.2f}; so the scored position for '
          f'output token j is exactly q_len + j - 1 (the position that PREDICTS it)')

    multi = [i for i, item in enumerate(items) if len(item['chain']) >= 2]
    swapped = gold_weights(batch, stories, items)
    for i in multi:
        for j in range(len(items[i]['chain']) - 1):
            position = int(batch.q_len[i]) + j - 1
            place(swapped, batch, stories, i, position, items[i]['support'][j], amount=-1.)
            place(swapped, batch, stories, i, position, items[i]['support'][j + 1])
    check('pointing a step at the NEXT step\'s row collapses the loss',
          bool(multi) and float(B.evidence_loss(batch, swapped)) > 1.,
          f'{len(multi)} multi-hop questions, loss {float(B.evidence_loss(batch, swapped)):.2f}')

    free = gold_weights(batch, stories, items)
    for i, item in enumerate(items):
        end_position = int(batch.q_len[i]) + len(item['chain']) - 1
        place(free, batch, stories, i, end_position, 0)
        for extra in range(end_position + 1, batch.seq.shape[1]):
            place(free, batch, stories, i, extra, 0)
    check('scribbling on the END-predicting position (and every position after it) does '
          'not move the loss at all',
          float(B.evidence_loss(batch, free)) == base,
          'so END-predicting positions carry NO evidence target')

    answer_token = gold_weights(batch, stories, items)
    for i, item in enumerate(items):
        place(answer_token, batch, stories, i, int(batch.q_len[i]) - 1,
              item['support'][0], amount=-1.)
    # only step 0 of each question is scrubbed, and the loss is a mean pooled over every
    # live (question, step) pair, so the expected value is 20.72 x (questions / live steps)
    live = sum(len(item['chain']) for item in items)
    expected = 20.723 * len(items) / live
    got = float(B.evidence_loss(batch, answer_token))
    check('the question\'s final ANSWER token IS scored (it predicts output token 0)',
          abs(got - expected) < .01,
          f'loss {got:.3f}, expected {expected:.3f} = the -log(1e-9) floor on {len(items)} '
          f'of {live} live steps; "output position" means the PREDICTING position')
    check('the auxiliary loss is a mean pooled over live (question, step) pairs, not '
          'per question', abs(got * live - 20.723 * len(items)) < .1)


def check_monotone(stories, items, batch):
    banner('3. GOLD ROW vs WRONG ROW')
    losses = {}
    for share in (.9, .5, .1):
        weights = blank_weights(batch)
        for i, item in enumerate(items):
            rows = stories[item['owner']]
            for j in range(len(item['chain'])):
                wrong = next(index for index, row in enumerate(rows)
                             if len(row) >= 4 and row[0] == WORLD and index != item['support'][j])
                position = int(batch.q_len[i]) + j - 1
                place(weights, batch, stories, i, position, item['support'][j], amount=share)
                place(weights, batch, stories, i, position, wrong, amount=1. - share)
        losses[share] = float(B.evidence_loss(batch, weights))
    check('more mass on the gold row is always a lower loss',
          losses[.9] < losses[.5] < losses[.1],
          ' < '.join(f'{losses[s]:.3f} (gold share {s})' for s in (.9, .5, .1)))
    check('the loss is exactly -log(mass on the gold row)',
          all(abs(losses[s] + math.log(s)) < 1e-4 for s in (.9, .5, .1)),
          f'{losses[.5]:.5f} vs {-math.log(.5):.5f}')

    split = blank_weights(batch)
    for i, item in enumerate(items):
        rows = stories[item['owner']]
        for j in range(len(item['chain'])):
            wrong = next(index for index, row in enumerate(rows)
                         if len(row) >= 4 and row[0] == WORLD and index != item['support'][j])
            position = int(batch.q_len[i]) + j - 1
            place(split, batch, stories, i, position, item['support'][j], head=0)
            place(split, batch, stories, i, position, wrong, head=1)
    check('the loss is taken on the HEAD-MEAN attention, not per head',
          abs(float(B.evidence_loss(batch, split)) + math.log(.5)) < 1e-4,
          'one head fully right + one fully wrong == half the mass')


def check_padding_guard():
    banner('4. PADDED STORY POSITIONS CANNOT BE CREDITED  (row index 0 is a real row)')
    short = [[WORLD, 52, LINK, 53, 7], [WORLD, 53, 8, 12, 7], [WORLD, 52, 8, 13, 7]]
    long = [[WORLD, 54 + i % 8, 9, 14, 7, 7] for i in range(12)]
    items = [dict(owner=0, question=[4, 52, LINK, 8, 5],
                  chain=[[52, LINK, 53], [53, 8, 12]], answer=12, hops=2, support=[0, 1])]
    batch = B.pack_batch([short, long], items, 'steps', support=True)
    s = batch.story.flat.shape[1]
    real = int(batch.story.lens[0])
    check('the short story really does have padded flat slots', s > real, f'{real} of {s} real')
    check('those padded slots carry row index 0, which is also a REAL row index',
          int(batch.story.flat_row[0, real]) == 0 and int(batch.support[0, 0]) == 0)
    weights = blank_weights(batch)
    weights[0, :, int(batch.q_len[0]) - 1, :] = 0.
    weights[0, :, int(batch.q_len[0]) - 1, real:s] = 1. / (s - real)
    weights[0, :, int(batch.q_len[0]) - 1, s + weights.shape[2] - 1] = 0.
    loss = float(B.evidence_loss(batch, weights))
    check('mass parked entirely on padding earns no credit for row 0', loss > 15.,
          f'loss {loss:.2f} (= -log(1e-9) floor), so the `* flat_valid` guard holds')
    gold = blank_weights(batch)
    place(gold, batch, [short, long], 0, int(batch.q_len[0]) - 1, 0)
    place(gold, batch, [short, long], 0, int(batch.q_len[0]), 1)
    check('the same batch scores 0 when the mass is on the real row 0 tokens',
          float(B.evidence_loss(batch, gold)) < 1e-5)


def check_zero_aux_identity(batch):
    banner('5. evidence_aux = 0 IS THE NO-AUX PATH, BIT FOR BIT')
    torch.manual_seed(4)
    model = B.BaselineTransformer(**TINY)

    def plain():
        logits, _ = model(batch)
        return F.cross_entropy(logits.reshape(-1, logits.shape[-1]),
                               batch.target.reshape(-1), ignore_index=-100)

    reference_loss, reference_grads = grads(model, plain)
    zero_loss, zero_grads = grads(model, lambda: B.teacher_forced_loss(model, batch,
                                                                      evidence_aux=0.)[0])
    default_loss, default_grads = grads(model, lambda: B.teacher_forced_loss(model, batch)[0])
    check('evidence_aux=0. gives the same loss as a hand-written cross entropy',
          zero_loss == reference_loss == default_loss, f'{zero_loss!r}')
    check('every gradient is bitwise identical',
          all(torch.equal(zero_grads[n], reference_grads[n]) for n in reference_grads)
          and all(torch.equal(default_grads[n], reference_grads[n]) for n in reference_grads),
          f'{len(reference_grads)} parameter tensors')

    with torch.no_grad():
        traced, weights = model(batch, trace=True)
        untraced, none = model(batch, trace=False)
    check('asking for the attention trace does not change the logits',
          torch.equal(traced, untraced) and none is None)
    check('the traced weights are a proper distribution over (story ++ own stream)',
          weights.shape[-1] == batch.story.flat.shape[1] + batch.seq.shape[1]
          and bool((weights.sum(-1) - 1).abs().max() < 1e-5),
          f'shape {tuple(weights.shape)}')


def check_weighting(batch):
    banner('6. THE AUXILIARY TERM ENTERS AT WEIGHT 0.5')
    torch.manual_seed(5)
    model = B.BaselineTransformer(**TINY)
    with torch.no_grad():
        plain_loss, _, _, _ = B.teacher_forced_loss(model, batch)
        aux_loss, _, _, aux = B.teacher_forced_loss(model, batch, evidence_aux=.5)
        other, _, _, aux2 = B.teacher_forced_loss(model, batch, evidence_aux=2.)
    check('loss(with aux) - loss(plain) == 0.5 x the reported auxiliary term',
          abs(float(aux_loss) - float(plain_loss) - .5 * aux) < 1e-5,
          f'plain {float(plain_loss):.5f}, aux term {aux:.5f}, total {float(aux_loss):.5f}')
    check('the reported auxiliary term does not depend on its own weight',
          abs(aux - aux2) < 1e-6 and abs(float(other) - float(plain_loss) - 2. * aux) < 1e-5)
    check('the auxiliary term is a live part of the graph, not a detached number',
          B.evidence_loss(batch, model(batch, trace=True)[1]).requires_grad)


def check_no_live_steps():
    banner('7. DEGENERATE INPUTS')
    short = [[WORLD, 52, LINK, 53, 7], [WORLD, 53, 8, 12, 7]]
    items = [dict(owner=0, question=[4, 52, LINK, 8, 5],
                  chain=[[52, LINK, 53], [53, 8, 12]], answer=12, hops=2)]
    batch = B.pack_batch([short], items, 'steps', support=True)
    check('an item with no `support` key yields an all -1 support table',
          bool(batch.support.eq(-1).all()))
    value = B.evidence_loss(batch, blank_weights(batch))
    check('with no live step the auxiliary loss is exactly 0 and contributes nothing',
          float(value) == 0.)
    raised = False
    try:
        B.evidence_loss(B.pack_batch([short], items, 'steps'), blank_weights(batch))
    except ValueError:
        raised = True
    check('a batch packed without support= raises instead of silently scoring nothing', raised)


def main():
    stories, items, batch = toy_batch()
    check_support_rows(stories, items, batch)
    check_targeting(stories, items, batch)
    check_monotone(stories, items, batch)
    check_padding_guard()
    check_zero_aux_identity(batch)
    check_weighting(batch)
    check_no_live_steps()
    print(f'\nALL {CHECKS} CHECKS PASSED')


if __name__ == '__main__':
    B.configure()
    main()
