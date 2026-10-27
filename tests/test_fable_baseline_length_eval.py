"""Checks for scripts/fable_baseline_length_eval.py.

Plain script.  Run it; it prints one line per check and ends with
`ALL N CHECKS PASSED` or raises.  Nothing here trains anything, nothing here touches a
registered artifact directory, and every model built here is a TINY UNTRAINED one on a
development seed.  Everything written lands in a temporary directory.

The load-bearing ones:

  CHECK GROUP "panels"        -- all 25 frozen v3 development cells load through
      `V3.load_panels` (which re-hashes every file against the manifest), and both
      twins of every pair cell are present.
  CHECK GROUP "gold"          -- for EVERY unit of EVERY cell the gold steps sequence
      this scorer compares against, `B.output_tokens(chain, 'steps')`, ends in END,
      carries the panel's own recorded answer immediately before END, and agrees with
      the INDEPENDENT v3 evaluator `V3.interpret` re-derived from the visible rows.
      If that is wrong, every `strict` number below is meaningless.
  CHECK GROUP "first wrong"   -- the histogram logic on hand-made emissions: a wrong
      middle step, an early END after a correct prefix, an over-long emission, a
      cap that ran out, and a wrong first step.
  CHECK GROUP "unscorable"    -- a cap or a prompt that would CLAMP against a fixed
      position table is DETECTED and refused rather than silently truncated, and the
      registered configuration's real cells are all scorable.
  CHECK GROUP "end to end"    -- an untrained tiny model scores a 25-cell panel
      directory (including the 8-hop cell) through the real `score` subcommand without
      crashing, and writes both output files.
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

import fable_baseline_transformer as B                                      # noqa: E402
import fable_baseline_transformer_v2 as B2                                  # noqa: E402
import fable_baseline_length_eval as L                                      # noqa: E402

V3 = B.V3
torch = B.torch

PANELS = ROOT / 'artifacts' / 'fable-dispatcher-v3-20260920' / 'panels'
DEV_SEED = 990140
MODE = 'steps'

CHECKS = 0


def check(label, condition, detail=''):
    global CHECKS
    if not condition:
        raise AssertionError(f'{label} FAILED {detail}')
    CHECKS += 1
    print(f'  ok  {label}{(" -- " + detail) if detail else ""}')


def banner(text):
    print(f'\n{text}')


def tiny_model():
    """An UNTRAINED 2-layer/16-wide model with the registered position package."""
    torch.manual_seed(DEV_SEED)
    return B.BaselineTransformer(positions='line', width=16, layers=2, heads=2, hidden=32)


# --------------------------------------------------------------------------- panels


def check_panels():
    banner('CHECK GROUP "panels": the 25 frozen v3 development cells')
    manifest, panels, forbidden = V3.load_panels(PANELS)
    check('V3.load_panels accepted the manifest and every cell file hash',
          set(panels) == set(V3.CELLS) and len(panels) == 25,
          f'{len(panels)} cells')
    check('the scorer walks the report\'s cell order',
          list(V3.CELL_ORDER) == list(manifest['cell_order']) and len(V3.CELL_ORDER) == 25)
    hops = {c: V3.CELLS[c]['hops'] for c in V3.CELL_ORDER}
    check('hop counts run 1..8 at 16 people, 1..3 at 6 people, 5 for the pairs',
          max(hops.values()) == 8 and hops['k8-held'] == 8 and hops['p6-k3-prac'] == 3
          and hops['pair-link'] == 5)
    for cell in V3.CELL_ORDER:
        units = panels[cell]['units']
        sides = ['a'] + (['b'] if V3.CELLS[cell]['kind'] == 'pair' else [])
        if len(units) != 64 or not all(all(s in u for s in sides) for u in units):
            raise AssertionError(f'{cell}: bad units')
    check('every cell has 64 units and every pair cell has both twins', True)
    loaded = {}
    for cell in V3.CELL_ORDER:
        sides = ['a'] + (['b'] if V3.CELLS[cell]['kind'] == 'pair' else [])
        loaded[cell] = {s: B.side_items(panels[cell]['units'], s) for s in sides}
    check('B.side_items builds stories and items for every cell and side',
          all(len(items) == 64 and len(stories) == 64
              for cell in loaded for stories, items in loaded[cell].values()))
    check('the manifest sha256 is v1\'s registered panel manifest',
          B.sha(PANELS / 'manifest.json') == B.PANEL_MANIFEST_SHA256)
    return panels, loaded


# --------------------------------------------------------------------------- gold


def check_gold(panels, loaded):
    banner('CHECK GROUP "gold": the gold steps sequence vs the v3 evaluator, every unit')
    units_seen = 0
    for cell in V3.CELL_ORDER:
        for side, (stories, items) in loaded[cell].items():
            for index, item in enumerate(items):
                unit_side = panels[cell]['units'][index][side]
                gold = B.output_tokens(item['chain'], MODE)
                if gold[-1] != B.END:
                    raise AssertionError(f'{cell}/{side}/{index}: gold does not end in END')
                if len(gold) != V3.CELLS[cell]['hops'] + 1:
                    raise AssertionError(f'{cell}/{side}/{index}: gold length != hops+1')
                if gold[-2] != unit_side['answer'] or gold[-2] != item['answer']:
                    raise AssertionError(f'{cell}/{side}/{index}: gold answer mismatch')
                if gold[:-1] != [int(step[2]) for step in unit_side['chain']]:
                    raise AssertionError(f'{cell}/{side}/{index}: gold steps mismatch')
                got = V3.interpret(unit_side['memory'], V3.side_eligible(unit_side),
                                   unit_side['question'])
                if [list(s) for s in got] != [list(s) for s in unit_side['chain']]:
                    raise AssertionError(f'{cell}/{side}/{index}: V3.interpret disagrees')
                if [int(s[2]) for s in got] + [B.END] != gold:
                    raise AssertionError(f'{cell}/{side}/{index}: interpreter vs gold')
                units_seen += 1
    check('gold steps sequence == the independent v3 interpreter\'s chain, every unit',
          units_seen == 64 * 28, f'{units_seen} unit-sides')
    oracle = B.oracle_emitter(MODE)
    summary, _ = B.score_panels(oracle, panels, MODE, cells=['k8-held', 'pair-link'])
    check('an oracle that writes the gold sequence scores 64/64 answers AND strict at 8 hops',
          summary['k8-held']['answers'] == 64 and summary['k8-held']['strict'] == 64)
    check('...and 64/64 on a two-sided pair cell',
          summary['pair-link']['answers'] == 64 and summary['pair-link']['strict'] == 64)


# --------------------------------------------------------------------------- first wrong


def check_first_wrong():
    banner('CHECK GROUP "first wrong": the histogram logic on hand-made emissions')
    gold = [53, 54, 20, B.END]
    cases = [(list(gold), None, 'exact'),
             ([53, 99, 20, B.END], 1, 'wrong middle step'),
             ([99, 54, 20, B.END], 0, 'wrong first step'),
             ([53, 54, B.END], 2, 'early END after 2 correct steps'),
             ([53, 54, 20, 77, B.END], 3, 'one token too many'),
             ([53, 54], 2, 'cap ran out on a correct prefix')]
    for emitted, want, label in cases:
        got = L.first_wrong_step(emitted, gold)
        check(f'first_wrong_step: {label}', got == want, f'got {got!r} want {want!r}')

    chain = [[52, 11, 53], [53, 11, 54], [54, 8, 20]]
    item = dict(owner=0, question=[4, 52, 11, 11, 8, 5], chain=chain, answer=20, hops=3)
    check('the hand-made gold is what the scorer will compare against',
          B.output_tokens(chain, MODE) == gold)
    emissions = [list(gold),                      # correct
                 [53, 54, 99, B.END],             # right length, wrong answer
                 [53, 54, B.END],                 # stopped early after 2 correct steps
                 [53, 54, 20, 77, B.END],         # stopped late, answer now 77
                 [53, 54, 20, 77, 88, 99],        # never stopped
                 [99, 54, 21, B.END]]             # wrong from step 0
    items = [dict(item) for _ in emissions]
    results = B.evaluate_side(items, emissions, MODE)
    check('B.evaluate_side marks exactly the first emission correct',
          [r['correct'] for r in results] == [1, 0, 0, 0, 0, 0])
    got = L.wrong_breakdown({'a': items}, {'a': results}, MODE, 3, 7)
    check('rows and wrong rows are counted', got['rows'] == 6 and got['rows_wrong'] == 5)
    check('the first-wrong-step histogram is exactly the hand-computed one',
          got['first_wrong_step'] == {'2': 2, '3': 2, '0': 1}, json.dumps(got['first_wrong_step']))
    check('"stopped too early" is the early-END row only', got['stopped_early'] == 1)
    check('the early-END row is recorded as 2 correct steps then END',
          got['early_end_after_correct_steps'] == {'2': 1})
    check('"stopped too late" is the over-long row only', got['stopped_late'] == 1)
    check('the capless row is counted as no_end and not as early or late',
          got['no_end'] == 1)
    check('right-length-but-wrong-tokens picks up the remaining two rows',
          got['right_length_wrong_tokens'] == 2)
    check('"none" never appears: an exact sequence is never a wrong answer',
          'none' not in got['first_wrong_step'])
    check('mean emitted steps counts non-END tokens',
          abs(got['mean_emitted_steps'] - (3 + 3 + 2 + 4 + 6 + 3) / 6) < 1e-9,
          str(got['mean_emitted_steps']))


# --------------------------------------------------------------------------- unscorable


def check_unscorable(loaded):
    banner('CHECK GROUP "unscorable": clamping is detected, never silently truncated')
    model = tiny_model()
    trained = L.trained_ranges(dict(train_hops=[1, 2, 3], train_people=6))
    check('the decode cap is hops+1+margin',
          L.decode_cap(1) == 5 and L.decode_cap(8) == 12 and L.decode_cap(5) == 9)
    check('the 8-hop cap is exactly v1\'s MAX_OUT', L.decode_cap(8) == B.MAX_OUT)
    check('--max-steps overrides the cap', L.decode_cap(8, override=9) == 9)

    good = 0
    for cell in V3.CELL_ORDER:
        hops = V3.CELLS[cell]['hops']
        limits = L.cell_limits(model, loaded[cell], L.decode_cap(hops), trained, hops)
        if limits['unscorable_reason'] is not None:
            raise AssertionError(f'{cell} unexpectedly unscorable: {limits["unscorable_reason"]}')
        good += 1
    check('every real cell is scorable at line positions with the chosen caps', good == 25)

    k8 = L.cell_limits(model, loaded['k8-held'], L.decode_cap(8), trained, 8)
    check('the 8-hop cell needs 9 output tokens but training only ever wrote 4',
          k8['needed_output_len'] == 9 and k8['max_trained_output_len'] == 4
          and k8['output_len_beyond_training'] is True)
    check('the untrained output-step rows the 8-hop cell reaches are listed',
          k8['untrained_output_step_indices'] == [4, 5, 6, 7, 8],
          json.dumps(k8['untrained_output_step_indices']))
    check('the 8-hop question is 11 tokens, past the 6-token longest training question',
          k8['max_question_tokens'] == 11 and k8['max_trained_question_len'] == 6
          and k8['row_position_beyond_training'] is True)
    check('...and that is still DECODED, not refused', k8['unscorable_reason'] is None)

    k1 = L.cell_limits(model, loaded['p6-k1-prac'], L.decode_cap(1), trained, 1)
    check('a trained-regime cell is flagged as inside the trained output range',
          k1['output_len_beyond_training'] is False and k1['untrained_row_position_indices'] == [])

    over = L.cell_limits(model, loaded['k8-held'], B.OUT_STEP_SLOTS + 1, trained, 8)
    check('a cap past OUT_STEP_SLOTS is refused and the limit is named',
          over['unscorable_reason'] is not None
          and 'OUT_STEP_SLOTS' in over['unscorable_reason'], str(over['unscorable_reason']))
    short = L.cell_limits(model, loaded['k8-held'], 5, trained, 8)
    check('a cap too small for the gold chain is refused',
          short['unscorable_reason'] is not None
          and 'decode cap 5' in short['unscorable_reason'], str(short['unscorable_reason']))

    torch.manual_seed(DEV_SEED)
    absolute = B.BaselineTransformer(positions='absolute', width=16, layers=2, heads=2, hidden=32)
    abs_limits = L.cell_limits(absolute, loaded['k8-held'], L.decode_cap(8), trained, 8)
    check('an absolute-position model is measured against ABSOLUTE_SLOTS instead',
          abs_limits['needed_absolute_index'] == abs_limits['max_story_flat_tokens'] + 11 + 11)
    fake = {'a': ([[[3, 1, 2, 3, 7]] * 4096], [dict(owner=0, question=[4, 52, 8, 5],
                                                    chain=[[52, 8, 20]], answer=20, hops=1)])}
    blown = L.cell_limits(absolute, fake, L.decode_cap(1), trained, 1)
    check('a sequence past ABSOLUTE_SLOTS is refused and the limit is named',
          blown['unscorable_reason'] is not None
          and 'ABSOLUTE_SLOTS' in blown['unscorable_reason'], str(blown['unscorable_reason']))


# --------------------------------------------------------------------------- end to end


def tiny_panels(folder, panels, units=2):
    """A 25-cell panel directory with the SAME structure and a correct manifest, cut to
    `units` units per cell so an untrained model can be decoded end to end cheaply."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    source = json.loads((PANELS / 'manifest.json').read_text())
    manifest = dict(source)
    manifest['cells'] = {}
    manifest['n'] = units
    for cell in V3.CELL_ORDER:
        body = dict(panels[cell])
        body['units'] = body['units'][:units]
        body['n'] = units
        path = folder / f'{cell}.json'
        B.write_new(path, body)
        manifest['cells'][cell] = dict(source['cells'][cell], sha256=B.sha(path), n=units)
    shutil.copy(PANELS / 'forbidden-semantics.json', folder / 'forbidden-semantics.json')
    manifest['exclusion_sha256'] = B.sha(folder / 'forbidden-semantics.json')
    B.write_new(folder / 'manifest.json', manifest)
    return folder


def tiny_run(folder):
    """A run directory shaped like a baseline-v2 seed directory, holding an UNTRAINED
    tiny checkpoint on a development seed."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    model = tiny_model()
    torch.save(dict(state_dict=model.state_dict(), config=model.config(), mode=MODE,
                    seed=DEV_SEED, updates=0, arm=None, init='default', evidence_aux=0.,
                    train_namespace='development-untrained'), folder / 'baseline.pt')
    B.write_new(folder / 'training.json',
                dict(baseline='development-untrained', train_hops=[1, 2, 3], train_people=6,
                     updates=0, complete=False, time_capped=False, seconds=0.))
    return folder, model


def check_end_to_end(panels):
    banner('CHECK GROUP "end to end": an untrained tiny model through the real subcommand')
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        panel_dir = tiny_panels(tmp / 'panels', panels, units=2)
        run, _ = tiny_run(tmp / 'run')
        out = tmp / 'out'
        L.main(['score', '--run', str(run), '--panels', str(panel_dir), '--out', str(out),
                '--block', '4'])
        report = json.loads((out / 'length.json').read_text())
        transcripts = json.loads((out / 'transcripts.json').read_text())
        check('both output files are written',
              (out / 'length.json').exists() and (out / 'transcripts.json').exists())
        check('all 25 cells are reported in the report\'s cell order',
              report['cell_order'] == list(V3.CELL_ORDER) and len(report['cells']) == 25)
        check('the 8-hop cell was decoded, not skipped',
              report['cells']['k8-held']['scorable'] is True
              and report['cells']['k8-held']['unscorable_reason'] is None)
        check('the 8-hop cell recorded its decode cap and what the chain needs',
              report['cells']['k8-held']['decode_max_out'] == 12
              and report['cells']['k8-held']['needed_output_len'] == 9
              and report['cells']['k8-held']['max_trained_output_len'] == 4)
        check('the mark is 58 and cells_passed counts cells at or above it',
              report['mark'] == 58
              and report['cells_passed'] == sum(1 for c in V3.CELL_ORDER
                                                if report['cells'][c]['passed']))
        check('an untrained model passes no cell', report['cells_passed'] == 0)
        check('every scored cell carries answers, strict, no_end and the wrong breakdown',
              all(all(k in report['cells'][c] for k in
                      ('answers', 'strict', 'no_end', 'mean_output_tokens', 'wrong'))
                  for c in V3.CELL_ORDER))
        check('every wrong-row breakdown accounts for its rows',
              all(report['cells'][c]['wrong']['rows_wrong']
                  == sum(report['cells'][c]['wrong']['first_wrong_step'].values())
                  for c in V3.CELL_ORDER))
        check('early/late/no-end/right-length partition the wrong rows',
              all(report['cells'][c]['wrong']['rows_wrong']
                  == (report['cells'][c]['wrong']['stopped_early']
                      + report['cells'][c]['wrong']['stopped_late']
                      + report['cells'][c]['wrong']['no_end']
                      + report['cells'][c]['wrong']['right_length_wrong_tokens'])
                  for c in V3.CELL_ORDER))
        check('the pair cells report both sides and both twins in the transcripts',
              all(set(transcripts['cells'][c]) == {'a', 'b'}
                  for c in ('pair-link', 'pair-value', 'pair-irrelevant')))
        check('single cells report one side', set(transcripts['cells']['k4-prac']) == {'a'})
        check('transcripts carry emitted tokens, the target and correctness',
              all(set(('emitted', 'target', 'correct', 'gold'))
                  <= set(transcripts['cells']['k8-held']['a'][0]) for _ in (0,)))
        check('the checkpoint, panel manifest and script hashes are recorded',
              len(report['checkpoint_sha256']) == 64 and len(report['source_sha256']) == 64
              and report['panel_manifest_sha256'] == B.sha(panel_dir / 'manifest.json'))
        check('this cut-down panel directory is NOT the registered manifest',
              report['panel_manifest_is_registered'] is False)
        check('the decode rule is written down',
              report['decode']['rule'] == 'max_out = hops + 1 + margin'
              and report['decode']['margin'] == L.DEFAULT_MARGIN)
        refused = False
        try:
            L.main(['score', '--run', str(run), '--panels', str(panel_dir), '--out', str(out)])
        except FileExistsError:
            refused = True
        check('the scorer refuses to overwrite an existing output directory', refused)

        # and the unscorable path, end to end, by forcing a cap past OUT_STEP_SLOTS
        out2 = tmp / 'out-unscorable'
        L.main(['score', '--run', str(run), '--panels', str(panel_dir), '--out', str(out2),
                '--block', '4', '--max-steps', str(B.OUT_STEP_SLOTS + 1)])
        bad = json.loads((out2 / 'length.json').read_text())
        check('forcing a clamping cap makes every cell unscorable, none passed',
              len(bad['cells_unscorable']) == 25 and bad['cells_passed'] == 0
              and bad['cells_scored'] == 0)
        check('an unscorable cell names the limit it hit and carries no scores',
              'OUT_STEP_SLOTS' in bad['cells']['k8-held']['unscorable_reason']
              and bad['cells']['k8-held']['answers'] is None)


def main():
    panels, loaded = check_panels()
    check_gold(panels, loaded)
    check_first_wrong()
    check_unscorable(loaded)
    check_end_to_end(panels)
    print(f'\nALL {CHECKS} CHECKS PASSED')


if __name__ == '__main__':
    B.configure()
    main()
