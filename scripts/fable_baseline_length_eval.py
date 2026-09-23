"""Does a FIT-QUALIFIED baseline-v2 checkpoint LENGTH-GENERALISE?

WHAT THIS ASKS
--------------
`scripts/fable_baseline_transformer_v2.py` trains the plain decoder-only baseline in
`steps` mode with `line` positions on 6-person worlds and 1-3 hop questions, and its
`fit` subcommand shows the registered I1-H1 seeds score 512/512 on all four fit cells
(1, 1-held, 2 and 3 hops, 6 people).

That is FIT, not LENGTH.  This file takes exactly those checkpoints and scores them,
unchanged, on the 25 frozen v3 DEVELOPMENT panel cells -- 1..8 hops at 16 people, 1..3
hops at 6 people, and the three 5-hop twin-pair cells -- with the display mark the v3
report uses, 58/64 per cell.

ADDITIVE ONLY.  Nothing here edits, monkey-patches or re-trains anything.  Everything
load-bearing is IMPORTED and reused:

  V3.load_panels            panel loading WITH the manifest sha256 check per file
  V3.CELLS, V3.CELL_ORDER, V3.CELL_MARK
  B.BaselineTransformer, B.side_items, B.output_tokens, B.evaluate_side,
  B.score_panels, B.aggregate, B.model_emitter, B.MAX_OUT, B.ROW_POS_SLOTS,
  B.OUT_STEP_SLOTS, B.ABSOLUTE_SLOTS, B.sha, B.write_new, B.configure
  B2.REGISTERED_SEEDS

so the prompt format, the greedy decode, the END convention, the answer extraction
("the token immediately before END; no END is a failure") and the pair-cell
aggregation are v1's, bit for bit, and cannot drift from the numbers they produced.

THE DECODE CAP
--------------
`B.BaselineTransformer.generate` defaults to `MAX_OUT` = 12 emitted tokens.  A `steps`
output for a k-hop question is `e_1 .. e_{k-1} y END`, i.e. k+1 tokens, so an 8-hop
chain needs 9.  Rather than reuse one global cap this scorer sets a PER-CELL cap

    cap = hops + 1 + margin          (margin defaults to 3)

which is 5 at one hop and exactly 12 -- v1's `MAX_OUT` -- at eight, and records it as
`decode_max_out` in every cell's row.  The margin exists so that "emitted too many
steps and then stopped" stays distinguishable from "never stopped".

THE POSITIONAL CAVEAT, MADE EXPLICIT
------------------------------------
The baseline's position tables are FIXED-SIZE and its embedding lookups CLAMP:

    line      `row_position` has ROW_POS_SLOTS = 16 rows, indexed by position within a
              story row AND by position within the question; `output_step` has
              OUT_STEP_SLOTS = 16 rows, indexed by the emitted-token index.
    absolute  `absolute` has ABSOLUTE_SLOTS = 640 rows over the whole flat sequence.

A clamp is a SILENT TRUNCATION: two different positions would share one embedding and
the run would still produce numbers.  So before decoding a cell this file measures what
that cell actually needs, and if any hard limit would be hit it does NOT decode: it
writes `unscorable_reason` naming the exact limit and counts the cell as 0 passed.

Separately -- and this is NOT a reason to refuse to decode -- the checkpoint's
TRAINED range is smaller than its table.  With `train_hops` (1, 2, 3) the longest
training output is 4 tokens, so `output_step` rows 4..15 never received a gradient, and
the longest training question is 6 tokens while a k=8 question is 11, so
`row_position` rows above the training maximum are only ever reached here.  Those are
the model's problem, not the harness's, so the cell IS decoded and every cell records
`max_trained_output_len` / `needed_output_len` and the same pair for row positions.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fable_baseline_transformer as B                                      # noqa: E402
import fable_baseline_transformer_v2 as B2                                  # noqa: E402

V3 = B.V3
torch = B.torch
sha, write_new, configure = B.sha, B.write_new, B.configure

MARK = V3.CELL_MARK                    # 58/64, the v3 report's display mark
DEFAULT_MARGIN = 3                     # cap = hops + 1 + margin; == B.MAX_OUT at 8 hops
TRANSCRIPT_UNITS = 16                  # units kept per cell per side in transcripts.json

# the row grammar is IDENTICAL in training and in the panels (`V3.render`): an attribute
# or link row is [3, e, rel, val] + 0..2 fillers + [7] and a filler row is [3] + 3..8
# fillers + [7], so the longest row is 10 tokens at ANY people count.  Only the QUESTION
# grows with hops: `V3.question_tokens` gives k + 3 tokens.
STORY_ROW_MAX_TOKENS = 10


# --------------------------------------------------------------------------- decode cap


class CappedModel:
    """A thin proxy that binds `max_out` on `generate` and delegates everything else to
    the real model, so `B.model_emitter` -- the emitter that produced v1's numbers -- is
    reused verbatim instead of being re-implemented with a different cap."""

    def __init__(self, model, max_out):
        self._model, self._max_out = model, int(max_out)

    @property
    def max_out(self):
        return self._max_out

    def generate(self, *args, **kwargs):
        kwargs.setdefault('max_out', self._max_out)
        return self._model.generate(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._model, name)


def decode_cap(hops, margin=DEFAULT_MARGIN, override=None):
    """`e_1 .. e_{k-1} y END` is k+1 tokens; the margin leaves room to emit too many."""
    return int(override) if override else int(hops) + 1 + int(margin)


# --------------------------------------------------------------------------- limits


def trained_ranges(config):
    """What the checkpoint's TRAINING actually exercised, from its own training.json."""
    hops = list(config.get('train_hops') or B.TRAIN_HOPS)
    max_hops = max(hops)
    return dict(
        train_hops=hops,
        train_people=config.get('train_people'),
        max_trained_output_len=max_hops + 1,
        max_trained_output_step_index=max_hops,
        max_trained_question_len=max_hops + 3,
        story_row_max_tokens=STORY_ROW_MAX_TOKENS,
        # `row_position` is shared by story rows and question tokens
        max_trained_row_position_index=max(STORY_ROW_MAX_TOKENS - 1, max_hops + 2),
        note=('a steps output for k hops is k+1 tokens and a k-hop question is k+3 '
              'tokens; the row grammar (and so the 10-token longest row) is the same in '
              'training and in the panels, so only the question and the output grow'))


def cell_limits(model, sides, max_out, trained, hops):
    """Everything the model's fixed position tables are asked for by THIS cell, the
    hard limits, and -- separately -- what training actually covered.

    `sides`: {side: (stories, items)} as `B.side_items` returns them.
    """
    row_tokens = max(len(row) for stories, _ in sides.values()
                     for story in stories for row in story)
    question_len = max(len(it['question']) for _, items in sides.values() for it in items)
    story_flat = max(sum(len(row) for row in story)
                     for stories, _ in sides.values() for story in stories)
    needed_output_len = int(hops) + 1
    limits = dict(
        positions=model.positions,
        max_story_row_tokens=row_tokens,
        max_question_tokens=question_len,
        max_story_flat_tokens=story_flat,
        decode_max_out=int(max_out),
        needed_output_len=needed_output_len,
        needed_row_position_index=max(row_tokens, question_len) - 1,
        needed_output_step_index=int(max_out) - 1,
        needed_absolute_index=story_flat + question_len + int(max_out) - 1,
        row_position_slots=B.ROW_POS_SLOTS,
        output_step_slots=B.OUT_STEP_SLOTS,
        absolute_slots=B.ABSOLUTE_SLOTS,
        default_max_out=B.MAX_OUT,
        max_trained_output_len=trained['max_trained_output_len'],
        max_trained_question_len=trained['max_trained_question_len'],
        max_trained_row_position_index=trained['max_trained_row_position_index'],
        max_trained_output_step_index=trained['max_trained_output_step_index'])
    limits['output_len_beyond_training'] = bool(
        needed_output_len > trained['max_trained_output_len'])
    limits['row_position_beyond_training'] = bool(
        limits['needed_row_position_index'] > trained['max_trained_row_position_index'])
    limits['untrained_output_step_indices'] = [
        i for i in range(trained['max_trained_output_step_index'] + 1, needed_output_len)]
    limits['untrained_row_position_indices'] = [
        i for i in range(trained['max_trained_row_position_index'] + 1,
                         limits['needed_row_position_index'] + 1)]
    reasons = []
    if needed_output_len > int(max_out):
        reasons.append(f'decode cap {max_out} is smaller than the {needed_output_len} tokens a '
                       f'{hops}-hop steps output needs')
    if model.positions == 'line':
        if limits['needed_row_position_index'] >= B.ROW_POS_SLOTS:
            reasons.append(f'row/question position index {limits["needed_row_position_index"]} '
                           f'>= ROW_POS_SLOTS={B.ROW_POS_SLOTS}: '
                           f'BaselineTransformer.embed_story/embed_stream would CLAMP it')
        if limits['needed_output_step_index'] >= B.OUT_STEP_SLOTS:
            reasons.append(f'output step index {limits["needed_output_step_index"]} '
                           f'>= OUT_STEP_SLOTS={B.OUT_STEP_SLOTS}: '
                           f'BaselineTransformer.embed_stream would CLAMP it')
    elif model.positions == 'absolute':
        if limits['needed_absolute_index'] >= B.ABSOLUTE_SLOTS:
            reasons.append(f'absolute position index {limits["needed_absolute_index"]} '
                           f'>= ABSOLUTE_SLOTS={B.ABSOLUTE_SLOTS}: '
                           f'BaselineTransformer.embed_story/embed_stream would CLAMP it')
    limits['unscorable_reason'] = '; '.join(reasons) if reasons else None
    return limits


# --------------------------------------------------------------------------- diagnostics


def first_wrong_step(emitted, gold):
    """The index of the FIRST emitted token that is not the gold token at that index.

    `gold` in steps mode is `[r_1, .., r_k, END]`, so index j < k is hop j+1's result
    and index k is the END slot.  `None` means the emission equals the gold sequence.
    If the emission is a strict PREFIX of the gold sequence (the decode cap ran out with
    everything so far right) the answer is `len(emitted)` -- the first index the model
    never reached.
    """
    for j, token in enumerate(emitted):
        if j >= len(gold) or token != gold[j]:
            return j
    return None if len(emitted) == len(gold) else len(emitted)


def emitted_steps(row):
    """Non-END tokens emitted.  A row without END kept all `max_out` of them."""
    return len(row['emitted']) - 1 if row['end_emitted'] else len(row['emitted'])


def wrong_breakdown(items_by_side, results_by_side, mode, hops, max_out):
    """Where the chain first went wrong, and whether it stopped too early or too late.

    Computed over every scored ROW (both twins of a pair cell) whose FINAL ANSWER is
    wrong -- i.e. the rows that cost the cell its `answers` score.
    """
    hist, early_after, steps_hist = {}, {}, {}
    wrong = stopped_early = stopped_late = right_length = no_end = 0
    total_steps = 0
    for side, items in items_by_side.items():
        for item, row in zip(items, results_by_side[side]):
            gold = B.output_tokens(item['chain'], mode)
            steps = emitted_steps(row)
            total_steps += steps
            if row['correct']:
                continue
            wrong += 1
            index = first_wrong_step(list(row['emitted']), gold)
            key = 'none' if index is None else str(index)
            hist[key] = hist.get(key, 0) + 1
            steps_hist[str(steps)] = steps_hist.get(str(steps), 0) + 1
            if not row['end_emitted']:
                no_end += 1
            elif steps < hops:
                stopped_early += 1
                # a correct prefix followed by an early END: `index` is then the END slot
                if index == steps:
                    early_after[str(steps)] = early_after.get(str(steps), 0) + 1
            elif steps > hops:
                stopped_late += 1
            else:
                right_length += 1
    rows = sum(len(v) for v in results_by_side.values())
    return dict(
        rows=rows, rows_wrong=wrong, hops=int(hops), decode_max_out=int(max_out),
        first_wrong_step=hist,
        emitted_steps_histogram=steps_hist,
        early_end_after_correct_steps=early_after,
        stopped_early=stopped_early, stopped_late=stopped_late,
        right_length_wrong_tokens=right_length, no_end=no_end,
        mean_emitted_steps=total_steps / max(1, rows),
        index_note=('first_wrong_step is an index into the gold steps output '
                    '[r_1 .. r_k END]: j < k is hop j+1\'s result, j == k is the END '
                    'slot, and j == len(emitted) means the cap ran out on a correct '
                    'prefix.  "none" means the sequence was exact but the answer was '
                    'still scored wrong, which cannot happen and is reported if it does.'),
        early_end_note=('early_end_after_correct_steps[m] = wrong rows that emitted m '
                        'CORRECT step results and then END, with m < hops'))


# --------------------------------------------------------------------------- scoring


def load_run(run):
    """The checkpoint and its own training record, the way v2's `fit` loads them."""
    run = Path(run)
    config_path = next((run / name for name in ('training.json', 'incomplete.json', 'failure.json')
                        if (run / name).exists()), None)
    if config_path is None:
        raise SystemExit(f'no training.json / incomplete.json / failure.json in {run}')
    config = json.loads(config_path.read_text())
    checkpoint = run / 'baseline.pt'
    if not checkpoint.exists():
        raise SystemExit(f'no baseline checkpoint in {run}')
    saved = torch.load(checkpoint, map_location='cpu', weights_only=False)
    model = B.BaselineTransformer(**saved['config'])
    model.load_state_dict(saved['state_dict'], strict=True)
    model.eval()
    return model, saved, config, config_path, checkpoint


def score(args):
    configure()
    model, saved, config, config_path, checkpoint = load_run(args.run)
    mode = saved['mode']
    # V3.load_panels re-hashes EVERY panel file against the manifest and the exclusion
    # file, and raises if any byte moved.
    manifest, panels, _ = V3.load_panels(args.panels)
    manifest_path = Path(args.panels) / 'manifest.json'
    manifest_sha = sha(manifest_path)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    trained = trained_ranges(config)
    started = time.monotonic()
    cells, transcripts = {}, {}
    for cell in V3.CELL_ORDER:
        cfg = V3.CELLS[cell]
        units = panels[cell]['units']
        sides = ['a'] + (['b'] if cfg['kind'] == 'pair' else [])
        loaded = {side: B.side_items(units, side) for side in sides}
        hops = cfg['hops']
        max_out = decode_cap(hops, args.margin, args.max_steps)
        limits = cell_limits(model, loaded, max_out, trained, hops)
        row = dict(n=len(units), sides=len(sides), hops=hops, people=cfg['people'],
                   terminal=cfg['terminal'], kind=cfg['kind'], title=cfg['title'],
                   need=MARK, decode_max_out=max_out,
                   needed_output_len=limits['needed_output_len'],
                   max_trained_output_len=limits['max_trained_output_len'],
                   limits=limits, unscorable_reason=limits['unscorable_reason'])
        if limits['unscorable_reason'] is not None:
            row.update(answers=None, strict=None, no_end=None, rows=None,
                       mean_output_tokens=None, identical_twin_answers=None, unit_pass=None,
                       passed=False, strict_passed=False, scorable=False, wrong=None)
            cells[cell] = row
            transcripts[cell] = dict(unscorable_reason=limits['unscorable_reason'])
            print(json.dumps(dict(cell=cell, hops=hops,
                                  unscorable_reason=limits['unscorable_reason'])), flush=True)
            continue
        emit = B.model_emitter(CappedModel(model, max_out), args.block)
        summary, cell_transcripts = B.score_panels(emit, panels, mode, cells=[cell])
        per_side = cell_transcripts[cell]
        row.update({k: v for k, v in summary[cell].items() if k not in row})
        row.update(answers=summary[cell]['answers'], strict=summary[cell]['strict'],
                   no_end=summary[cell]['no_end'], rows=summary[cell]['rows'],
                   mean_output_tokens=summary[cell]['mean_output_tokens'],
                   identical_twin_answers=summary[cell]['identical_twin_answers'],
                   unit_pass=summary[cell]['unit_pass'], scorable=True,
                   passed=bool(summary[cell]['answers'] >= MARK),
                   strict_passed=bool(summary[cell]['strict'] >= MARK),
                   wrong=wrong_breakdown({s: loaded[s][1] for s in sides}, per_side, mode,
                                         hops, max_out))
        cells[cell] = row
        transcripts[cell] = {
            side: [dict(emitted=list(r['emitted']), target=r['target'], correct=r['correct'],
                        strict_path=r['strict_path'], end_emitted=r['end_emitted'],
                        hops=r['hops'], output_tokens=r['output_tokens'],
                        gold=B.output_tokens(loaded[side][1][i]['chain'], mode))
                   for i, r in enumerate(per_side[side][:TRANSCRIPT_UNITS])]
            for side in sides}
        print(json.dumps(dict(cell=cell, hops=hops, n=row['n'], need=MARK,
                              decode_max_out=max_out, answers=row['answers'],
                              strict=row['strict'], no_end=row['no_end'],
                              passed=row['passed'])), flush=True)
    seconds = time.monotonic() - started
    unscorable = [c for c in V3.CELL_ORDER if cells[c]['unscorable_reason'] is not None]
    report = dict(
        evaluation='fable-baseline-transformer-v2 checkpoint, greedy (argmax) decoding, '
                   'FINAL checkpoint only, no selection, scored on the 25 frozen v3 '
                   'DEVELOPMENT panel cells',
        question='does a checkpoint that fits 1-3 hops at 6 people LENGTH-GENERALISE?',
        run=str(Path(args.run).resolve()), run_config_file=config_path.name,
        arm=saved.get('arm'), init=saved.get('init'), evidence_aux=saved.get('evidence_aux'),
        seed=saved.get('seed'),
        registered_seed=bool(saved.get('seed') in B2.REGISTERED_SEEDS),
        train_namespace=saved.get('train_namespace'),
        updates=config.get('updates'), complete=config.get('complete'),
        time_capped=config.get('time_capped'),
        training_seconds=config.get('seconds'), training_flops=config.get('training_flops'),
        mode=mode, positions=saved['config']['positions'], model_config=saved['config'],
        parameters=model.parameters_count(),
        checkpoint=str(checkpoint.resolve()), checkpoint_sha256=sha(checkpoint),
        panels=str(Path(args.panels).resolve()),
        panel_namespace=manifest.get('namespace'),
        panel_manifest_sha256=manifest_sha,
        panel_manifest_is_registered=bool(manifest_sha == B.PANEL_MANIFEST_SHA256),
        registered_panel_manifest_sha256=B.PANEL_MANIFEST_SHA256,
        panel_files_verified='V3.load_panels re-hashed every cell file and '
                             'forbidden-semantics.json against manifest.json',
        answer='the token emitted immediately before END; no END is a failure',
        strict_path='every emitted token equals the gold steps sequence and END is emitted '
                    'immediately after the answer',
        pair_rule='a pair cell scores a unit only when BOTH twins are correct '
                  '(fable_baseline_transformer.aggregate, unchanged)',
        mark=MARK, cell_order=list(V3.CELL_ORDER), cells=cells,
        cells_passed=sum(1 for c in V3.CELL_ORDER if cells[c]['passed']),
        cells_strict_passed=sum(1 for c in V3.CELL_ORDER if cells[c]['strict_passed']),
        cells_scored=sum(1 for c in V3.CELL_ORDER if cells[c]['scorable']),
        cells_unscorable=unscorable,
        unscorable_rule='a cell whose prompt or output would CLAMP against a fixed position '
                        'table is not decoded at all; it records unscorable_reason and counts '
                        'as 0 passed',
        decode=dict(rule='max_out = hops + 1 + margin', margin=args.margin,
                    max_steps_override=args.max_steps, block=args.block,
                    default_max_out=B.MAX_OUT,
                    note='hops+1+3 is 5 at one hop and exactly MAX_OUT=12 at eight hops'),
        trained_ranges=trained,
        scoring_seconds=seconds,
        source_sha256=sha(__file__), v1_source_sha256=sha(B.__file__),
        v2_source_sha256=sha(B2.__file__), v3_source_sha256=sha(V3.__file__),
        created_unix=time.time())
    write_new(out / 'length.json', report)
    write_new(out / 'transcripts.json',
              dict(units_per_cell=TRANSCRIPT_UNITS, cell_order=list(V3.CELL_ORDER),
                   cells=transcripts))
    print(json.dumps(dict(event='done', seed=saved.get('seed'), arm=saved.get('arm'),
                          mark=MARK, cells_passed=report['cells_passed'],
                          cells_strict_passed=report['cells_strict_passed'],
                          cells_unscorable=len(unscorable),
                          scoring_seconds=round(seconds, 1))), flush=True)
    return report


# --------------------------------------------------------------------------- CLI


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)

    p = sub.add_parser('score')
    p.add_argument('--run', required=True, help='a baseline-v2 seed directory')
    p.add_argument('--panels', required=True, help='the v3 development panels directory')
    p.add_argument('--out', required=True)
    p.add_argument('--block', type=int, default=32)
    p.add_argument('--max-steps', type=int, default=None,
                   help='override the per-cell decode cap with one fixed value')
    p.add_argument('--margin', type=int, default=DEFAULT_MARGIN,
                   help='extra emitted tokens allowed beyond the gold hops+1')

    args = parser.parse_args(argv)
    score(args)


if __name__ == '__main__':
    main()
