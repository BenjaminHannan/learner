"""Checks for scripts/fable_baseline_transformer.py.

Plain script.  Run it; it prints one line per check and ends with
`ALL N CHECKS PASSED` or raises.  Nothing here trains, and nothing here writes
outside a temporary directory.

The load-bearing one is CHECK 11: an independent, test-only DENSE reference that
builds the whole `story ++ question ++ output` sequence, applies the variant's mask
explicitly and runs the blocks with no memory cache at all.  The production model
encodes the story once per world (and, for `line`, as a batch of independent rows)
and serves it to the questions as a key/value cache -- that is an exact re-ordering
of the same computation, and the reference is what proves it.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import random
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

import fable_baseline_transformer as B                                      # noqa: E402

V3 = B.V3
torch = B.torch
F = B.F

PANELS = ROOT / 'artifacts' / 'fable-dispatcher-v3-20260920' / 'panels'

CHECKS = 0


def check(label, condition, detail=''):
    global CHECKS
    if not condition:
        raise AssertionError(f'{label} FAILED {detail}')
    CHECKS += 1
    print(f'  ok  {label}{(" -- " + detail) if detail else ""}')


def banner(text):
    print(f'\n{text}')


# --------------------------------------------------------------------------- reference


def reference_logits(model, rows, question, output):
    """A test-only dense forward over one flat `story ++ question ++ output` sequence.

    No cache, no row batching: the mask is written out in full and every position
    attends through it.  `line` blocks story tokens to their own row; `absolute` and
    `none` use a plain causal mask over everything.
    """
    story = [t for row in rows for t in row]
    row_of = [index for index, row in enumerate(rows) for _ in row]
    within = [position for row in rows for position in range(len(row))]
    seq = story + list(question) + list(output)
    n, s = len(seq), len(story)
    ids = torch.tensor(seq, dtype=torch.long)[None]
    x = model.embedding(ids)
    if model.positions == 'line':
        pos = torch.zeros(n, dtype=torch.long)
        segment = torch.zeros(n, dtype=torch.long)
        step = torch.zeros(n, dtype=torch.long)
        is_output = torch.zeros(n, dtype=torch.bool)
        for i in range(n):
            if i < s:
                pos[i], segment[i] = min(within[i], B.ROW_POS_SLOTS - 1), B.STORY
            elif i < s + len(question):
                pos[i], segment[i] = min(i - s, B.ROW_POS_SLOTS - 1), B.QSEG
            else:
                segment[i], is_output[i] = B.OSEG, True
                step[i] = min(i - s - len(question), B.OUT_STEP_SLOTS - 1)
        x = x + model.row_position(pos)[None] * (~is_output)[None, :, None]
        x = x + model.segment(segment)[None]
        x = x + model.output_step(step)[None] * is_output[None, :, None]
    elif model.positions == 'absolute':
        index = torch.arange(n).clamp(max=B.ABSOLUTE_SLOTS - 1)
        x = x + model.absolute(index)[None]
    mask = torch.ones(n, n, dtype=torch.bool).tril()
    if model.positions == 'line':
        for i in range(s):
            for j in range(s):
                if row_of[i] != row_of[j]:
                    mask[i, j] = False
    for block in model.blocks:
        x, _, _ = block(x, mask[None])
    x = model.final_norm(x)
    return F.linear(x, model.embedding.weight, model.output_bias)[0]


def one_batch(mode='steps', visits=3, seed='reference'):
    rng = random.Random(seed)
    stories, items = B.training_items(rng, visits=visits, support=True)
    return stories, items, B.pack_batch(stories, items, mode, support=True)


# --------------------------------------------------------------------------- checks


def check_parameters():
    banner('1. PARAMETER COUNT')
    counts = {}
    for positions in ('line', 'absolute', 'none'):
        counts[positions] = B.BaselineTransformer(positions=positions).parameters_count()
    ratio = counts['line'] / B.TARGET_PARAMETERS
    check('primary `line` variant within +-3% of S\'s 94,838',
          abs(ratio - 1) <= B.PARAMETER_TOLERANCE,
          f'{counts["line"]} parameters, ratio {ratio:.4f}')
    check('`none` variant also within +-3%',
          abs(counts['none'] / B.TARGET_PARAMETERS - 1) <= B.PARAMETER_TOLERANCE,
          f'{counts["none"]} parameters')
    over = counts['absolute'] - counts['none']
    check('`absolute` differs from `none` by exactly its position table',
          over == B.ABSOLUTE_SLOTS * B.WIDTH,
          f'{counts["absolute"]} parameters, +{over} = {B.ABSOLUTE_SLOTS}x{B.WIDTH} '
          f'(ratio {counts["absolute"] / B.TARGET_PARAMETERS:.3f}: this arm is NOT matched '
          f'and has MORE capacity, which is stated, not hidden)')


def check_causal():
    banner('2. CAUSAL MASK')
    torch.manual_seed(0)
    model = B.BaselineTransformer(positions='line')
    _stories, _items, batch = one_batch()
    with torch.no_grad():
        before, _ = model(batch)
        changed = B.Batch(story=batch.story, owner=batch.owner, seq=batch.seq.clone(),
                          seq_valid=batch.seq_valid, q_len=batch.q_len, target=batch.target)
        last = int(batch.seq_valid[0].sum()) - 1
        changed.seq[0, last] = 53 if int(batch.seq[0, last]) != 53 else 54
        after, _ = model(changed)
    check('editing the final token leaves every earlier position\'s logits bitwise equal',
          torch.equal(before[0, :last], after[0, :last]))
    check('editing the final token does change that position\'s own logits',
          not torch.allclose(before[0, last], after[0, last]))
    check('editing row 0 leaves the other rows untouched',
          torch.equal(before[1:], after[1:]))
    # a story row cannot see a later story row under `line`
    with torch.no_grad():
        model_none = B.BaselineTransformer(positions='none')
        rows = [[3, 52, 8, 12, 7], [3, 53, 11, 54, 7], [3, 54, 9, 13, 7]]
        question, output = [4, 52, 8, 5], [12, B.END]
        base = reference_logits(model_none, rows, question, output)
        edited = reference_logits(model_none, [rows[0], [3, 53, 11, 55, 7], rows[2]],
                                  question, output)
    check('under a plain causal mask, editing a LATER story row leaves earlier story '
          'positions identical', torch.allclose(base[:5], edited[:5], atol=1e-6))


def check_loss_positions():
    banner('3. LOSS ON THE OUTPUT PART ONLY')
    stories, items, batch = one_batch()
    scored = batch.target.ne(-100)
    expected = sum(len(B.output_tokens(it['chain'], 'steps')) for it in items)
    check('exactly one scored position per output token', int(scored.sum()) == expected,
          f'{int(scored.sum())} scored positions, {expected} output tokens')
    ok = True
    for i, it in enumerate(items):
        q = len(it['question'])
        out = B.output_tokens(it['chain'], 'steps')
        ok &= all(int(batch.target[i, q - 1 + j]) == out[j] for j in range(len(out)))
        ok &= all(int(batch.target[i, j]) == -100 for j in range(q - 1))
        ok &= all(int(batch.target[i, j]) == -100
                  for j in range(q - 1 + len(out), batch.target.shape[1]))
    check('the scored positions are exactly (last question token .. last output token - 1)', ok)
    torch.manual_seed(1)
    model = B.BaselineTransformer(positions='line')
    loss, _, _, _ = B.teacher_forced_loss(model, batch)
    with torch.no_grad():
        logits, _ = model(batch)
        manual = []
        for i, it in enumerate(items):
            q = len(it['question'])
            for j, token in enumerate(B.output_tokens(it['chain'], 'steps')):
                manual.append(F.cross_entropy(logits[i, q - 1 + j][None],
                                              torch.tensor([token])))
    got, want = float(loss.detach()), float(torch.stack(manual).mean())
    check('the loss equals the mean cross entropy over exactly those positions',
          abs(got - want) < 1e-5, f'{got:.6f} vs {want:.6f}')


def check_training_stream():
    banner('4. TRAINING STREAM MATCHES S\'S REGIME')
    rng = random.Random(f'{B.TRAIN_NAMESPACE}:990001')
    hops_seen, terminals = {}, set()
    heldout_multi = 0
    people_ok = True
    total = 0
    for _ in range(40):
        stories, items = B.training_items(rng, visits=4)
        for it in items:
            total += 1
            hops_seen[it['hops']] = hops_seen.get(it['hops'], 0) + 1
            terminals.add((it['hops'], it['terminal']))
            if it['hops'] >= 2 and it['terminal'] == B.HELDOUT_REL:
                heldout_multi += 1
            if it['hops'] >= 2:
                people_ok &= len({step[0] for step in it['chain']}) == it['hops']
        for story in stories:
            entities = {row[1] for row in story if len(row) >= 4 and 52 <= row[1] < 68}
            people_ok &= len(entities) == B.TRAIN_PEOPLE
    check('relation 10 is NEVER the terminal relation at k >= 2', heldout_multi == 0,
          f'{total} training questions inspected')
    check('only 1, 2 and 3 hops appear', set(hops_seen) == {1, 2, 3}, str(hops_seen))
    check('relation 10 DOES appear as a one-hop terminal',
          (1, B.HELDOUT_REL) in terminals)
    check('both practised relations appear at k >= 2',
          all((k, r) in terminals for k in (2, 3) for r in B.PRACTISED_RELS))
    check('multi-hop chains are pairwise distinct and worlds have 6 people', people_ok)
    spread = min(hops_seen.values()) / max(hops_seen.values())
    check('the hop count is close to uniform', spread > .9, f'{hops_seen}, ratio {spread:.3f}')


def check_targets_match_interpreter():
    banner('5. TEACHER-FORCED TARGETS == THE EXACT INTERPRETER\'S TRUTH CHAIN')
    rng = random.Random(f'{B.TRAIN_NAMESPACE}:990002')
    stories, items = B.training_items(rng, visits=6)
    batch = B.pack_batch(stories, items, 'steps')
    ok_steps = ok_answer = True
    for i, it in enumerate(items):
        rows = stories[it['owner']]
        truth = V3.interpret(rows, [True] * len(rows), it['question'])
        also = V3.walk(V3.fact_table(rows, [True] * len(rows)), it['question'])
        q = len(it['question'])
        emitted = [int(batch.target[i, q - 1 + j]) for j in range(len(truth) + 1)]
        ok_steps &= (truth == also == it['chain'])
        ok_steps &= emitted == [step[2] for step in truth] + [B.END]
        ok_answer &= int(batch.target[i, q - 1 + len(truth) - 1]) == truth[-1][2]
    check('steps-mode targets are the interpreter\'s intermediate entities then END', ok_steps)
    check('the token before END is the interpreter\'s answer', ok_answer)
    answer_only = B.pack_batch(stories, items, 'answer-only')
    ok = all(int(answer_only.target[i, len(it['question']) - 1]) == it['chain'][-1][2]
             and int(answer_only.target[i, len(it['question'])]) == B.END
             for i, it in enumerate(items))
    check('answer-only mode targets are exactly `y END`', ok)


class ScriptedModel(B.BaselineTransformer):
    """A model whose greedy choice is a fixed script, to test the stop rule alone."""

    script = ()

    def stream(self, seq, seq_valid, q_len, owner, memory, story_valid, story_len, *,
               trace=False):
        n, width = seq.shape
        logits = torch.zeros(n, width, self.vocab)
        for i in range(n):
            start = int(q_len[i]) - 1
            for j, token in enumerate(self.script):
                if start + j < width:
                    logits[i, start + j, token] = 50.
        return logits, None


def check_decode_stops():
    banner('6. GREEDY DECODING STOPS AT END')
    torch.manual_seed(2)
    stories, items = B.training_items(random.Random(f'{B.TRAIN_NAMESPACE}:990003'), visits=2)
    story = B.pack_stories(stories)
    owner = torch.tensor([it['owner'] for it in items])
    width = max(len(it['question']) for it in items)
    question = torch.zeros(len(items), width, dtype=torch.long)
    for i, it in enumerate(items):
        question[i, :len(it['question'])] = torch.tensor(it['question'])
    q_len = torch.tensor([len(it['question']) for it in items])

    scripted = ScriptedModel(positions='line')
    scripted.script = (52, 53, B.END, 54, 55)
    got = scripted.generate(story, owner, question, q_len)
    check('a scripted emitter returns exactly the tokens up to and including the first END',
          all(row == [52, 53, B.END] for row in got), str(got[0]))

    scripted.script = tuple([52] * (B.MAX_OUT + 4))
    got = scripted.generate(story, owner, question, q_len)
    check('a model that never emits END returns exactly MAX_OUT tokens and no END',
          all(len(row) == B.MAX_OUT and B.END not in row for row in got))
    rows = B.evaluate_side(items, got, 'steps')
    check('no END is scored as a failure', all(r['end_emitted'] == 0 and r['correct'] == 0
                                               for r in rows))

    scripted.script = (B.END,)
    got = scripted.generate(story, owner, question, q_len)
    check('an immediate END stops after one step and answers nothing',
          all(row == [B.END] for row in got)
          and all(r['correct'] == 0 for r in B.evaluate_side(items, got, 'steps')))

    torch.manual_seed(3)
    untrained = B.BaselineTransformer(positions='line')
    got = untrained.generate(story, owner, question, q_len)
    check('an untrained model never emits anything after its first END',
          all(B.END not in row[:-1] for row in got))


def check_scorer_sufficiency():
    banner('7. SCORER SUFFICIENCY -- A HAND-BUILT ORACLE EMITTER SCORES 64/64')
    check('the panel manifest is the registered one',
          B.sha(PANELS / 'manifest.json') == B.PANEL_MANIFEST_SHA256,
          B.PANEL_MANIFEST_SHA256[:16] + '...')
    _manifest, panels, _forbidden = V3.load_panels(PANELS)
    summary, _ = B.score_panels(B.oracle_emitter('steps'), panels, 'steps')
    bad = {cell: row for cell, row in summary.items()
           if not (row['answers'] == row['strict'] == row['unit_pass'] == row['n'] == 64
                   and row['no_end'] == 0)}
    check('every one of the 25 cells scores 64/64 answers AND 64/64 strict paths',
          not bad, f'{len(summary)} cells; worst {min(r["strict"] for r in summary.values())}/64')
    answer_only, _ = B.score_panels(B.oracle_emitter('answer-only'), panels, 'answer-only')
    check('the answer-only oracle also scores 64/64 on every cell',
          all(r['answers'] == 64 and r['strict'] == 64 for r in answer_only.values()))
    wrong = B.oracle_emitter('steps')
    mixed, _ = B.score_panels(lambda s, i: [[52, B.END] for _ in i], panels, 'steps',
                              cells=['k3-prac'])
    check('a constant wrong emitter scores near zero, so the scorer is not vacuous',
          mixed['k3-prac']['answers'] <= 8 and mixed['k3-prac']['strict'] == 0,
          f'{mixed["k3-prac"]["answers"]}/64 answers by luck')
    del wrong


def check_row_permutation():
    banner('8. ROW-PERMUTATION INVARIANCE OF THE `line` VARIANT')
    rng = random.Random(f'{B.TRAIN_NAMESPACE}:990004')
    stories, items = B.training_items(rng, visits=2)
    order = list(range(len(stories[0])))
    shuffler = random.Random(7)
    shuffler.shuffle(order)
    shuffled = [[stories[0][i] for i in order]] + stories[1:]
    results = {}
    for positions in ('line', 'absolute', 'none'):
        torch.manual_seed(5)
        model = B.BaselineTransformer(positions=positions)
        with torch.no_grad():
            a, _ = model(B.pack_batch(stories, items, 'steps'))
            b, _ = model(B.pack_batch(shuffled, items, 'steps'))
        results[positions] = float((a - b).abs().max())
    check('`line` logits are invariant to permuting story rows', results['line'] < 1e-5,
          f'max |delta| {results["line"]:.2e}')
    check('`absolute` logits are NOT invariant', results['absolute'] > 1e-3,
          f'max |delta| {results["absolute"]:.2e}')
    check('`none` logits are NOT invariant either (the causal mask alone orders the rows)',
          results['none'] > 1e-3, f'max |delta| {results["none"]:.2e}')


def check_pair_scoring():
    banner('9. PAIR SCORING')
    cfg_changing = V3.CELLS['pair-link']
    cfg_invariant = V3.CELLS['pair-irrelevant']

    def side(correct, answer, strict=1):
        return [dict(correct=int(correct), strict_path=int(strict), answer=answer,
                     end_emitted=1, output_tokens=4)]

    both = dict(a=side(True, 12), b=side(True, 13))
    one = dict(a=side(True, 12), b=side(False, 99))
    check('a changed-answer pair counts only when BOTH twins are correct',
          B.aggregate(both, 1, cfg_changing)['answers'] == 1
          and B.aggregate(one, 1, cfg_changing)['answers'] == 0)
    same = dict(a=side(True, 12), b=side(True, 12))
    differ = dict(a=side(True, 12), b=side(False, 13))
    check('an irrelevant-edit pair also requires identical twin answers',
          B.aggregate(same, 1, cfg_invariant)['unit_pass'] == 1
          and B.aggregate(differ, 1, cfg_invariant)['unit_pass'] == 0)
    loose = dict(a=side(True, 12, strict=1), b=side(True, 13, strict=0))
    check('strict requires both twins strict', B.aggregate(loose, 1, cfg_changing)['strict'] == 0)
    check('a single-side cell aggregates one row per unit',
          B.aggregate(dict(a=side(True, 12)), 1, V3.CELLS['k3-prac'])['rows'] == 1)


def check_flops():
    banner('10. FLOP COUNTER')
    width, layers, heads, hidden, vocab = 8, 2, 2, 16, B.VOCAB
    rows = [[[3, 52, 8, 12, 7], [3, 53, 11, 54, 7]], [[3, 54, 9, 13, 7], [3, 52, 11, 53]]]
    story = B.pack_stories(rows)
    w, r, t = story.rows.shape
    s = story.flat.shape[1]
    linear = 4 * width * width + 2 * width * hidden
    for positions, tokens, span in (('line', w * r * t, t), ('none', w * s, s)):
        model = B.BaselineTransformer(positions=positions, width=width, layers=layers,
                                      heads=heads, hidden=hidden)
        manual = 2 * layers * tokens * (linear + 2 * span * width)
        check(f'`{positions}` story FLOPs match a hand count',
              model.story_flops(story, backward=False) == manual, f'{manual}')
        check(f'`{positions}` backward multiplies the story count by exactly 3',
              model.story_flops(story, backward=True) == 3 * manual)
        q, u = 5, 9
        manual_stream = 2 * (layers * q * u * (linear + 2 * (s + u) * width)
                             + q * u * width * vocab)
        check(f'`{positions}` stream FLOPs match a hand count',
              model.stream_flops(s, q, u, backward=False) == manual_stream, f'{manual_stream}')
        check(f'`{positions}` flops() is story + stream',
              model.flops(story, (q, u), backward=True)
              == 3 * manual + 3 * manual_stream)
    model = B.BaselineTransformer(positions='line', width=width, layers=layers, heads=heads,
                                  hidden=hidden)
    check('the convention matches premonition_token_memory (6 x MACs per trained token)',
          model.story_flops(story, backward=True)
          == 6 * layers * w * r * t * (4 * width * width + 2 * width * hidden
                                       + 2 * t * width),
          '48*n*d*d there = 6 x (4d^2 attention + 4d^2 ff) MACs; here the MLP is 2*d*hidden')


def check_reference_equivalence():
    banner('11. THE CACHED/ROW-BATCHED PATH EQUALS A DENSE-MASK REFERENCE')
    rng = random.Random(f'{B.TRAIN_NAMESPACE}:990005')
    stories, items = B.training_items(rng, visits=3)
    batch = B.pack_batch(stories, items, 'steps')
    for positions in ('line', 'absolute', 'none'):
        torch.manual_seed(11)
        model = B.BaselineTransformer(positions=positions)
        with torch.no_grad():
            logits, _ = model(batch)
        worst = 0.
        for i in range(0, len(items), 5):
            it = items[i]
            out = B.output_tokens(it['chain'], 'steps')
            want = reference_logits(model, stories[it['owner']], it['question'], out)
            q, s = len(it['question']), sum(len(row) for row in stories[it['owner']])
            for j in range(len(out)):
                worst = max(worst, float((logits[i, q - 1 + j]
                                          - want[s + q - 1 + j]).abs().max()))
        check(f'`{positions}` production logits equal the dense reference', worst < 2e-5,
              f'max |delta| {worst:.2e}')


def check_end_to_end():
    banner('12. TRAIN + SCORE END TO END (2 updates, dev seed, one cell)')
    with tempfile.TemporaryDirectory() as folder:
        out = Path(folder) / 'run'
        B.main(['train', '--mode', 'steps', '--positions', 'line', '--seed', '990006',
                '--updates', '2', '--visits', '2', '--out', str(out), '--log-every', '1',
                '--panels', str(PANELS)])
        check('training writes training.json and a final checkpoint',
              (out / 'training.json').is_file() and (out / 'baseline.pt').is_file())
        raised = False
        try:
            B.main(['train', '--seed', '990006', '--updates', '1', '--out', str(out)])
        except SystemExit:
            raised = True
        check('a second train into the same directory is refused', raised)
        aux_out = Path(folder) / 'aux'
        B.main(['train', '--seed', '990007', '--updates', '2', '--visits', '2',
                '--evidence-aux', '0.5', '--out', str(aux_out), '--log-every', '1'])
        aux = [json.loads(line) for line in (aux_out / 'train_log.jsonl').read_text().split('\n')
               if line]
        check('the optional --evidence-aux path runs and reports a finite, positive loss',
              all(math.isfinite(r['evidence']) and r['evidence'] > 0 for r in aux)
              and all(math.isfinite(r['loss']) for r in aux),
              f'evidence {aux[-1]["evidence"]:.3f} (SMOKE ONLY: nothing asserts that this '
              f'auxiliary loss points at the right row)')
        saved = torch.load(out / 'baseline.pt', map_location='cpu', weights_only=False)
        model = B.BaselineTransformer(**saved['config'])
        model.load_state_dict(saved['state_dict'], strict=True)
        model.eval()
        _manifest, panels, _ = V3.load_panels(PANELS)
        summary, _ = B.score_panels(B.model_emitter(model), panels, 'steps', cells=['p6-k1-prac'])
        row = summary['p6-k1-prac']
        check('an almost-untrained model runs through the real scorer',
              row['n'] == 64 and row['rows'] == 64 and 0 <= row['answers'] <= 64,
              f'{row["answers"]}/64 answers, {row["no_end"]} rows with no END')


def main():
    check_parameters()
    check_causal()
    check_loss_positions()
    check_training_stream()
    check_targets_match_interpreter()
    check_decode_stops()
    check_scorer_sufficiency()
    check_row_permutation()
    check_pair_scoring()
    check_flops()
    check_reference_equivalence()
    check_end_to_end()
    print(f'\nALL {CHECKS} CHECKS PASSED')


if __name__ == '__main__':
    B.configure()
    main()
