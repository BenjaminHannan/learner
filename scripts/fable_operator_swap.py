"""Additive end-to-end operator-swap scorer (audit note 5 / swap-v2 draft, 2026-09-20).

WHAT THIS IS.  Three predeclared pairings of already-trained, already-frozen pieces:

  pair 0   v3 rl-cost01 dispatcher seed 0   x   grow-blind operator seed 0
  pair 1   v3 rl-cost01 dispatcher seed 1   x   grow-blind operator seed 1
  pair 2   v3 rl-cost01 dispatcher seed 2   x   grow-blind operator seed 2

No retraining, no operator selection, no seed substitution.  The dispatcher policy,
its supplied features, full-vocabulary operator argmax, greedy (argmax) execution,
the evaluation cap of 16 calls and every failure semantic are exactly v3's: this
module never copies or edits `fable_dispatcher_v3`, it imports and calls it.

WHAT IT FIXES.  `fable_dispatcher_v3.score --operator X` does change the operator
that native execution actually calls, but it then copies `operator_chain_hits` out of
the panel file and `frozen_operator_on_true_chains` out of the panel manifest, both of
which were computed with the ORIGINAL hinted operator.  Those diagnostics do not steer
execution -- native answers are not corrupted by them -- but attributing them to the
replacement operator is wrong.  This module

  * never reads `panel['operator_chain_hits']` or `manifest['operator_audit']`
    (`strip_stale_diagnostics` removes both from the loaded panels before scoring, and
    `run_meta.json` records that it did),
  * recomputes every chain audit by calling the EXACT loaded operator
    (`operator_calls`, which also keeps each call's predicted token so a per-call error
    list is available), and
  * stores those audits in the new run directory, keyed by operator SHA-256, cell and
    side.  The registered panel directory is opened read-only and never written to.

REGISTERED READING.  All 25 existing v3 cells, 64 units each, scored as a DEVELOPMENT
REPLICATION (these panels are development benchmarks, not an untouched test set).  A
pairing passes a cell when, for that pairing,

    answers >= 58/64   AND   strict path >= 58/64   AND   unit pass >= 58/64

which is the originally registered 58/64 mark of `fable_dispatcher_v3.CELL_MARK`, not
the subsequently observed 59/64.  A pairing passes when it passes every cell.  The
oracle operator is run on the same inputs as a descriptive control, never as the
registered number.  Examples where the replacement operator is wrong are never
discarded.

    freeze     write the manifest of all six checkpoint SHA-256s + panel hashes
    run        score the pairings named by the frozen manifest
    report     print the table, and for a failing pairing the oracle control, the
               per-call operator errors and the native transcripts of failing units
    replicate  DEVELOPMENT-ONLY re-score of one dispatcher with an arbitrary operator,
               used to show this scorer reproduces the registered v3 numbers with the
               ORIGINAL operator.  Not part of the registered screen.

Everything is additive: nothing outside --out is written, and --out must not exist.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fable_dispatcher as V1                                               # noqa: E402
import fable_dispatcher_v3 as V3                                            # noqa: E402

A = V1.A
torch = V3.torch
sha = V3.sha
write_new = V3.write_new
fingerprint = V1.fingerprint

WORKTREE = Path(__file__).resolve().parent.parent
BASE = Path('/Users/ben-hannan/Desktop/projects/beautiful-model')

V3_RUN_ROOT = WORKTREE / 'artifacts/fable-dispatcher-v3-20260920'
DEFAULT_PANELS = V3_RUN_ROOT / 'panels'
DEFAULT_DISPATCHER_ROOT = V3_RUN_ROOT / 'rl-cost01'
DEFAULT_OPERATOR_ROOT = BASE / 'artifacts/fable-operator-grow-blind-20260920'
ORIGINAL_OPERATOR = (BASE / 'artifacts/astra-canonical-operator-screen-20260920'
                     / 'astra_canonical_operator_seed-1/final.pt')

PAIR_SEEDS = (0, 1, 2)
CELL_MARK = V3.CELL_MARK                         # 58 of 64, the ORIGINAL registered mark
EVAL_CAP = V3.EVAL_CAP                           # 16
MARKED = ('answers', 'strict', 'unit_pass')
REGISTERED_OPERATOR_LABEL = 'replacement_operator'
CONTROL_OPERATOR_LABEL = 'oracle_operator'


def dispatcher_dir(seed, root=None):
    return Path(root or DEFAULT_DISPATCHER_ROOT) / f'seed-{seed}'


def operator_path(seed, root=None):
    return Path(root or DEFAULT_OPERATOR_ROOT) / f'astra_canonical_operator_seed-{seed}/final.pt'


# --------------------------------------------------------------------------- panels


def strip_stale_diagnostics(panels):
    """Remove every operator diagnostic the ORIGINAL operator wrote into the panels.

    The panel files stay untouched on disk; this only drops the fields from the loaded
    copy, so a later `panel.get('operator_chain_hits')` cannot silently reappear in a
    score.  Returns the number of fields dropped, which `run_meta.json` records.
    """
    dropped = 0
    for panel in panels.values():
        if panel.pop('operator_chain_hits', None) is not None:
            dropped += 1
    return dropped


def load_panels_without_stale_diagnostics(panels_dir):
    manifest, panels, forbidden = V3.load_panels(panels_dir)
    dropped = strip_stale_diagnostics(panels)
    manifest = dict(manifest)
    manifest.pop('operator_audit', None)
    return manifest, panels, forbidden, dropped


# --------------------------------------------------------------------------- operator audit


@torch.no_grad()
def operator_calls(operator, units, side, block=32):
    """Every true-chain call of one side, with the EXACT loaded operator's own answer.

    `V3.operator_on_chains` returns only hit/miss; the swap report needs the predicted
    token too, so this keeps both.  Batching, canonical query construction and the
    packed inputs are v3's (`V3.pack_side` / `A.canonical_input`), so the operator sees
    byte-identical inputs to the ones the cached lookup table is built from.

    -> per unit: [dict(entity, operation, target, predicted, hit), ...]
    """
    per_unit = []
    for start in range(0, len(units), block):
        chunk = units[start:start + block]
        inputs, _ = V3.pack_side(chunk, side)
        entities, operations, indices, truth = [], [], [], []
        for i, unit in enumerate(chunk):
            for subject, op, target in unit[side]['chain']:
                entities.append(subject)
                operations.append(op)
                indices.append(i)
                truth.append(target)
        if isinstance(operator, V3.OracleOperator):
            predicted = list(truth)
        else:
            x = A.canonical_input(inputs, entities, operations, indices)
            predicted = operator.model(x).argmax(-1).tolist()
        cursor = 0
        for unit in chunk:
            n = len(unit[side]['chain'])
            per_unit.append([dict(entity=int(e), operation=int(o), target=int(t),
                                  predicted=int(p), hit=int(p == t))
                             for e, o, t, p in zip(entities[cursor:cursor + n],
                                                   operations[cursor:cursor + n],
                                                   truth[cursor:cursor + n],
                                                   predicted[cursor:cursor + n])])
            cursor += n
    return per_unit


def hits_of(per_unit):
    return [[stage['hit'] for stage in unit] for unit in per_unit]


def chain_audit(per_side_calls):
    """The manifest-shaped audit, recomputed for the operator actually loaded."""
    sides = list(per_side_calls)
    n = len(per_side_calls[sides[0]])
    stages = sum(len(unit) for side in sides for unit in per_side_calls[side])
    correct = sum(stage['hit'] for side in sides for unit in per_side_calls[side]
                  for stage in unit)
    all_steps = sum(all(stage['hit'] for side in sides
                        for stage in per_side_calls[side][i]) for i in range(n))
    return dict(stages=stages, stages_correct=correct, units=n, units_all_steps=all_steps,
                operator_perfect=bool(correct == stages))


# --------------------------------------------------------------------------- scoring


def cell_marks(counts, mark=CELL_MARK):
    return {key: bool(counts[key] >= mark) for key in MARKED}


def failing_units(scored, cfg, per_side_calls):
    """Every unit of one cell that did not pass, with everything the diagnosis needs.

    For each failing unit: the native transcript and pointer sequence under the
    replacement operator, that unit's per-call operator errors (recomputed, not
    copied), and the SAME unit's oracle-operator execution as the control.
    """
    sides = list(scored[REGISTERED_OPERATOR_LABEL])
    n = len(scored[REGISTERED_OPERATOR_LABEL][sides[0]])
    out = []
    for i in range(n):
        native = {s: scored[REGISTERED_OPERATOR_LABEL][s][i] for s in sides}
        oracle = {s: scored[CONTROL_OPERATOR_LABEL][s][i] for s in sides}
        correct = all(native[s]['correct'] for s in sides)
        strict = all(native[s]['strict_path'] for s in sides)
        identical = len({native[s]['answer'] for s in sides}) == 1
        passed = correct and strict and (identical or not cfg['invariant'])
        if passed:
            continue
        errors = {s: [stage for stage in per_side_calls[s][i] if not stage['hit']]
                  for s in sides}
        out.append(dict(
            index=native[sides[0]]['index'], answer_correct=int(correct),
            strict_path=int(strict), twins_identical=int(identical),
            operator_call_errors=errors,
            operator_calls_total=sum(len(per_side_calls[s][i]) for s in sides),
            operator_calls_wrong=sum(len(errors[s]) for s in sides),
            native={s: dict(answer=native[s]['answer'], target=native[s]['target'],
                            status=native[s]['status'], calls=native[s]['calls'],
                            transcript=native[s]['transcript'],
                            pointers=native[s]['pointers'],
                            truth_chain=native[s]['truth_chain']) for s in sides},
            oracle_control={s: dict(answer=oracle[s]['answer'], status=oracle[s]['status'],
                                    calls=oracle[s]['calls'],
                                    correct=oracle[s]['correct'],
                                    strict_path=oracle[s]['strict_path'],
                                    transcript=oracle[s]['transcript']) for s in sides}))
    return out


def load_dispatcher(run):
    run = Path(run)
    config_path = run / 'training.json'
    if not config_path.exists():
        config_path = run / 'failure.json'
    if not config_path.exists():
        raise SystemExit(f'no training.json or failure.json in {run}')
    config = json.loads(config_path.read_text())
    checkpoint = run / 'dispatcher.pt'
    if not checkpoint.exists():
        raise SystemExit(f'no dispatcher checkpoint in {run}')
    saved = torch.load(checkpoint, map_location='cpu', weights_only=False)
    model = V3.Dispatcher(width=saved['width'], absolute_positions=saved['absolute_positions'])
    model.load_state_dict(saved['state_dict'], strict=True)
    model.eval()
    flags = V3.FeatureFlags(**saved.get('ablations', {}))
    return model, config, saved, flags, checkpoint


def score_pairing(dispatcher_run, operator_spec, panels_dir, out, *, label='pairing',
                  cap=EVAL_CAP, mark=CELL_MARK, cells=None, block=32, verbose=True):
    """One (dispatcher, operator) pair over every cell.  Writes into `out`, nothing else.

    Returns the scores summary.  The chain audits are RECOMPUTED here for the exact
    loaded operator; nothing from the panel manifest's `operator_audit` is used.
    """
    V3.configure()
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    model, config, saved, flags, checkpoint = load_dispatcher(dispatcher_run)
    dispatcher_before = fingerprint(model)
    manifest, panels, _forbidden, dropped = load_panels_without_stale_diagnostics(panels_dir)
    operator = V3.make_operator(operator_spec)
    oracle = V3.OracleOperator()
    operator_before = operator.fingerprint
    operators = {REGISTERED_OPERATOR_LABEL: operator, CONTROL_OPERATOR_LABEL: oracle}
    tables = V3.TableCache(operators, block)
    order = [c for c in V3.CELL_ORDER if cells is None or c in cells]

    operator_key = operator.describe().get('sha256', operator.kind)
    summary = dict(
        scorer='fable_operator_swap', screen='development replication (reused v3 panels)',
        label=label, dispatcher_run=str(Path(dispatcher_run).resolve()),
        dispatcher_checkpoint_sha256=sha(checkpoint),
        dispatcher_fingerprint_before=dispatcher_before,
        dispatcher_parameters=model.parameters_count(), seed=config.get('seed'),
        arm=config.get('arm'), updates=config.get('updates'),
        train_cap=config.get('train_cap'), train_hops=config.get('train_hops'),
        train_people=config.get('train_people'), call_cost=config.get('call_cost'),
        historical_training_operator=config.get('operator'),
        replacement_operator=operator.describe(), eval_cap=cap, mark=mark,
        marked_metrics=list(MARKED), ablations=flags.as_dict(),
        policy='greedy (argmax) episodes, final fixed checkpoints only, no retries, no beam '
               'search, no forced actions, unchanged stopping',
        panels=str(Path(panels_dir).resolve()),
        panel_manifest_sha256=sha(Path(panels_dir) / 'manifest.json'),
        panel_files={cell: manifest['cells'][cell]['sha256'] for cell in order},
        stale_panel_diagnostics_dropped=dropped,
        stale_diagnostics_note=(
            'panel operator_chain_hits and manifest operator_audit were computed with the '
            'ORIGINAL hinted operator; both are removed from the loaded panels before any '
            'scoring and every chain audit below is recomputed with the operator named in '
            'replacement_operator.  The panel directory is not written to.'),
        strict_path='subjects, operations, stop point AND every returned token',
        cell_order=order, cells={})
    transcripts, audits, failures = {}, {}, {}
    for cell in order:
        cfg = V3.CELLS[cell]
        units = panels[cell]['units']
        sides = ['a'] + (['b'] if cfg['kind'] == 'pair' else [])
        calls = {s: operator_calls(operator, units, s, block) for s in sides}
        hits = {s: hits_of(calls[s]) for s in sides}
        scored = {label_: {s: V3.score_side(model, op, units, s, cap, flags,
                                            chain_hits=hits if label_ ==
                                            REGISTERED_OPERATOR_LABEL else None,
                                            prepared=tables.get(label_, cell, units, s))
                           for s in sides}
                  for label_, op in operators.items()}
        counts = dict(n=len(units), sides=len(sides), hops=cfg['hops'], people=cfg['people'],
                      terminal=cfg['terminal'], kind=cfg['kind'], title=cfg['title'])
        for label_, rows in scored.items():
            counts[label_] = V3.aggregate(rows, len(units), cfg)
        counts['marks'] = cell_marks(counts[REGISTERED_OPERATOR_LABEL], mark)
        counts['cell_pass'] = bool(all(counts['marks'].values()))
        counts['replacement_operator_on_true_chains'] = chain_audit(calls)
        counts['oracle_operator_on_true_chains'] = chain_audit(
            {s: operator_calls(oracle, units, s, block) for s in sides})
        summary['cells'][cell] = counts
        transcripts[cell] = scored
        audits[cell] = {s: calls[s] for s in sides}
        found = failing_units(scored, cfg, calls)
        if found:
            failures[cell] = found
        if verbose:
            print(json.dumps(dict(
                pairing=label, cell=cell, hops=cfg['hops'],
                answers=counts[REGISTERED_OPERATOR_LABEL]['answers'],
                strict=counts[REGISTERED_OPERATOR_LABEL]['strict'],
                unit_pass=counts[REGISTERED_OPERATOR_LABEL]['unit_pass'],
                over_cap=counts[REGISTERED_OPERATOR_LABEL]['over_cap'],
                oracle_answers=counts[CONTROL_OPERATOR_LABEL]['answers'],
                operator_stages_correct=counts['replacement_operator_on_true_chains'][
                    'stages_correct'],
                operator_stages=counts['replacement_operator_on_true_chains']['stages'],
                cell_pass=counts['cell_pass'])), flush=True)
    assert operator.fingerprint == operator_before, 'the operator changed during scoring'
    assert fingerprint(model) == dispatcher_before, 'the dispatcher changed during scoring'
    totals = dict(
        cells=len(order), cells_passed=sum(summary['cells'][c]['cell_pass'] for c in order),
        stages=sum(summary['cells'][c]['replacement_operator_on_true_chains']['stages']
                   for c in order),
        stages_correct=sum(
            summary['cells'][c]['replacement_operator_on_true_chains']['stages_correct']
            for c in order))
    summary.update(
        totals=totals, complete=bool(len(order) == len(V3.CELL_ORDER)),
        pairing_pass=bool(totals['cells_passed'] == len(order) and
                          len(order) == len(V3.CELL_ORDER)),
        failing_cells=[c for c in order if not summary['cells'][c]['cell_pass']],
        dispatcher_fingerprint_after=fingerprint(model),
        operator_fingerprint_before=operator_before,
        operator_fingerprint_after=operator.fingerprint,
        weights_unchanged=True, created_unix=time.time())
    write_new(out / 'scores.json', summary)
    write_new(out / 'transcripts.json', transcripts)
    write_new(out / 'operator_chain_audit.json',
              dict(operator=operator.describe(), operator_sha256=operator_key,
                   recomputed_for_this_checkpoint=True, copied_from_panels=False,
                   note='per cell, per side, per unit, per call: entity, operation, target, '
                        'the operator\'s own predicted token and hit/miss',
                   cells=audits))
    write_new(out / 'failures.json',
              dict(operator_sha256=operator_key, mark=mark, marked_metrics=list(MARKED),
                   cells=failures,
                   note='a unit is listed when answers, strict path or twin invariance failed; '
                        'each entry carries the native transcript, the recomputed per-call '
                        'operator errors and the oracle-operator control on the same input'))
    return summary


# --------------------------------------------------------------------------- freeze


def freeze(args):
    """Write the pre-scoring manifest: all six checkpoints, the panels and the sources."""
    V3.configure()
    out = Path(args.out)
    # the registration folder normally already holds PREREGISTRATION.md; `write_new`
    # still refuses to overwrite an existing manifest, so a freeze can never be repeated.
    out.mkdir(parents=True, exist_ok=True)
    panels = Path(args.panels)
    panel_manifest = json.loads((panels / 'manifest.json').read_text())
    pairs = {}
    for seed in [int(s) for s in str(args.seeds).split(',')]:
        run = dispatcher_dir(seed, args.dispatcher_root)
        checkpoint = run / 'dispatcher.pt'
        op = operator_path(seed, args.operator_root)
        config = json.loads((run / 'training.json').read_text())
        saved = torch.load(checkpoint, map_location='cpu', weights_only=False)
        frozen_operator = V3.FrozenOperator(op)
        pairs[str(seed)] = dict(
            pair=seed, dispatcher_seed=seed, operator_seed=seed,
            dispatcher_run=str(run.resolve()), dispatcher_checkpoint=str(checkpoint.resolve()),
            dispatcher_checkpoint_sha256=sha(checkpoint),
            dispatcher_architecture=dict(width=saved['width'],
                                         absolute_positions=bool(saved['absolute_positions']),
                                         ablations=saved.get('ablations', {})),
            dispatcher_updates=config.get('updates'), dispatcher_arm=config.get('arm'),
            dispatcher_call_cost=config.get('call_cost'),
            dispatcher_training_operator=config.get('operator'),
            operator_checkpoint=str(Path(op).resolve()), operator_sha256=sha(op),
            operator_architecture=frozen_operator.architecture,
            operator_fingerprint=frozen_operator.fingerprint)
    manifest = dict(
        created_unix=time.time(), screen='fable operator swap v2 (development replication)',
        registered_mark=args.mark, marked_metrics=list(MARKED), eval_cap=args.eval_cap,
        n_per_cell=panel_manifest['n'], cells=V3.CELL_ORDER,
        seed_substitution_allowed=False, retraining_allowed=False,
        operator_selection_allowed=False,
        policy='unchanged greedy policy, supplied v3 features, full-vocabulary operator '
               'argmax, cap 16, no retries, no beam search, no forced actions, unchanged '
               'stopping',
        panels=str(panels.resolve()),
        panel_manifest_sha256=sha(panels / 'manifest.json'),
        panel_files={cell: row['sha256'] for cell, row in panel_manifest['cells'].items()},
        panel_exclusion_sha256=panel_manifest.get('exclusion_sha256'),
        pairs=pairs,
        sources={'scripts/fable_operator_swap.py': sha(__file__),
                 'scripts/fable_dispatcher_v3.py': sha(V3.__file__),
                 'scripts/fable_dispatcher.py': sha(V1.__file__),
                 'scripts/fable_dispatcher_v2.py': sha(V3.V2.__file__)},
        stale_diagnostic_fix=('panel operator_chain_hits / manifest operator_audit are '
                              'dropped before scoring and every chain audit is recomputed '
                              'with the replacement operator'))
    write_new(out / 'manifest.json', manifest)
    print(json.dumps(dict(manifest=str((out / 'manifest.json').resolve()),
                          manifest_sha256=sha(out / 'manifest.json'),
                          pairs=sorted(pairs), mark=args.mark, eval_cap=args.eval_cap)),
          flush=True)
    return manifest


def verify_manifest(out):
    """Every frozen hash still matches what is on disk.  Any mismatch aborts the run."""
    manifest = json.loads((Path(out) / 'manifest.json').read_text())
    problems = []
    for name, expected in manifest['sources'].items():
        path = Path(__file__).resolve().parent / Path(name).name
        if not path.is_file() or sha(path) != expected:
            problems.append(f'source changed: {name}')
    if sha(Path(manifest['panels']) / 'manifest.json') != manifest['panel_manifest_sha256']:
        problems.append('panel manifest changed')
    for cell, expected in manifest['panel_files'].items():
        if sha(Path(manifest['panels']) / f'{cell}.json') != expected:
            problems.append(f'panel changed: {cell}')
    for key, row in manifest['pairs'].items():
        if sha(row['dispatcher_checkpoint']) != row['dispatcher_checkpoint_sha256']:
            problems.append(f'pair {key}: dispatcher checkpoint changed')
        if sha(row['operator_checkpoint']) != row['operator_sha256']:
            problems.append(f'pair {key}: operator checkpoint changed')
    return manifest, problems


def run(args):
    out = Path(args.out)
    manifest, problems = verify_manifest(out)
    if problems:
        raise SystemExit('integrity failure, refusing to score: ' + '; '.join(problems))
    wanted = sorted(manifest['pairs']) if args.pair is None else [str(args.pair)]
    results = {}
    started = time.monotonic()
    for key in wanted:
        row = manifest['pairs'][key]
        summary = score_pairing(row['dispatcher_run'], row['operator_checkpoint'],
                                manifest['panels'], out / f'pair-{key}',
                                label=f'pair-{key}', cap=manifest['eval_cap'],
                                mark=manifest['registered_mark'])
        if summary['dispatcher_checkpoint_sha256'] != row['dispatcher_checkpoint_sha256']:
            raise SystemExit(f'pair {key}: dispatcher hash drifted during scoring')
        if summary['replacement_operator']['sha256'] != row['operator_sha256']:
            raise SystemExit(f'pair {key}: operator hash drifted during scoring')
        results[key] = dict(pairing_pass=summary['pairing_pass'],
                            failing_cells=summary['failing_cells'],
                            cells_passed=summary['totals']['cells_passed'],
                            cells=summary['totals']['cells'])
        print(json.dumps(dict(pairing=key, **results[key])), flush=True)
    meta = dict(created_unix=time.time(), seconds=time.monotonic() - started,
                manifest_sha256=sha(out / 'manifest.json'), pairs_scored=wanted,
                results=results,
                screen_pass=bool(wanted == sorted(manifest['pairs'])
                                 and all(r['pairing_pass'] for r in results.values())),
                complete=bool(wanted == sorted(manifest['pairs'])),
                panel_diagnostics_recomputed=True, panels_written_to=False,
                note='a missing pair or cell means the registered screen did not pass')
    path = out / f'run_meta{"" if args.pair is None else f"-pair-{args.pair}"}.json'
    write_new(path, meta)
    print(json.dumps(dict(run_meta=str(path.resolve()), screen_pass=meta['screen_pass'],
                          seconds=round(meta['seconds'], 1))), flush=True)
    return meta


def replicate(args):
    """DEVELOPMENT-ONLY: re-score one v3 dispatcher with an arbitrary operator.

    Used to show that this scorer reproduces the registered v3 answers/strict counts
    exactly when handed the ORIGINAL operator checkpoint.  Not a registered reading.
    """
    summary = score_pairing(args.run, args.operator, args.panels, args.out,
                            label='replication', cap=args.eval_cap, mark=args.mark)
    registered = Path(args.run) / 'score/scores.json'
    compared = None
    if registered.exists():
        old = json.loads(registered.read_text())
        compared = {}
        for cell, row in summary['cells'].items():
            theirs = old['cells'][cell]['trained_operator']
            mine = row[REGISTERED_OPERATOR_LABEL]
            compared[cell] = {key: [theirs[key], mine[key]] for key in
                              ('answers', 'strict', 'loose', 'unit_pass', 'over_cap', 'invalid')
                              if theirs[key] != mine[key]}
        compared = {c: v for c, v in compared.items() if v}
    write_new(Path(args.out) / 'replication.json',
              dict(registered_scores=str(registered), differences=compared,
                   identical=bool(compared == {}), operator=args.operator))
    print(json.dumps(dict(identical=bool(compared == {}), differences=compared)), flush=True)
    return compared


# --------------------------------------------------------------------------- report


def _row(counts, mark):
    return f'{counts["answers"]}/{counts["strict"]}/{counts["unit_pass"]}' \
        + ('' if min(counts['answers'], counts['strict'], counts['unit_pass']) >= mark else ' *')


def report(args):
    out = Path(args.out)
    manifest = json.loads((out / 'manifest.json').read_text())
    summaries = {}
    for key in sorted(manifest['pairs']):
        path = out / f'pair-{key}/scores.json'
        if path.exists():
            summaries[key] = json.loads(path.read_text())
    if not summaries:
        raise SystemExit(f'no pair-*/scores.json under {out}')
    mark = manifest['registered_mark']
    keys = sorted(summaries)
    lines = [f'OPERATOR SWAP v2  (development replication on the reused v3 panels)',
             f'panels {manifest["panels"]}',
             f'panel manifest sha256 {manifest["panel_manifest_sha256"]}',
             f'mark {mark}/64 on answers, strict path and unit pass; eval cap '
             f'{manifest["eval_cap"]}']
    for key in keys:
        row = manifest['pairs'][key]
        lines.append(f'  pair {key}: dispatcher seed {row["dispatcher_seed"]} '
                     f'{row["dispatcher_checkpoint_sha256"][:12]}  x  grow-blind seed '
                     f'{row["operator_seed"]} {row["operator_sha256"][:12]}')
    width = 20
    head = f'{"cell":>18}{"n":>5}{"k":>4}' + ''.join(
        '{:>{w}}'.format(f'pair {k}', w=width) for k in keys)
    lines += ['', 'MAIN TABLE  (answers/strict/unit_pass, replacement operator)', head,
              '-' * len(head)]
    for cell in manifest['cells']:
        pieces, n, k = [], '?', '?'
        for key in keys:
            row = summaries[key]['cells'].get(cell)
            if row is None:
                pieces.append('{:>{w}}'.format('-', w=width))
                continue
            n, k = row['n'], row['hops']
            pieces.append('{:>{w}}'.format(_row(row[REGISTERED_OPERATOR_LABEL], mark), w=width))
        lines.append(f'{cell:>18}{n:>5}{k:>4}' + ''.join(pieces))
    lines.append(f'  "*" marks a cell below {mark}/64 on at least one marked metric.')
    lines += ['', 'REPLACEMENT OPERATOR ON THE TRUE CHAINS  (RECOMPUTED for this checkpoint)',
              f'{"cell":>18}' + ''.join('{:>{w}}'.format(f'pair {k}', w=width) for k in keys),
              '-' * (18 + width * len(keys))]
    for cell in manifest['cells']:
        pieces = []
        for key in keys:
            row = summaries[key]['cells'].get(cell)
            audit = None if row is None else row['replacement_operator_on_true_chains']
            pieces.append('{:>{w}}'.format(
                '-' if audit is None else f'{audit["stages_correct"]}/{audit["stages"]}',
                w=width))
        lines.append(f'{cell:>18}' + ''.join(pieces))
    lines.append('  these are NOT the panel manifest numbers: they are recomputed with the '
                 'exact replacement operator hash.')
    for key in keys:
        summary = summaries[key]
        status = ('PASS' if summary['pairing_pass']
                  else 'FAIL' if summary['failing_cells'] else 'INCOMPLETE')
        lines += ['', f'PAIR {key}: {status}'
                      f'  ({summary["totals"]["cells_passed"]}/{summary["totals"]["cells"]} '
                      f'cells scored and passed, of {len(manifest["cells"])} registered)']
        if not summary['complete']:
            lines.append('  not every registered cell was scored, so the screen did not pass')
        if not summary['failing_cells']:
            continue
        lines.append(f'  failing cells: {", ".join(summary["failing_cells"])}')
        lines += ['', f'  ORACLE CONTROL on the same inputs  [pair {key}]',
                  '  ' + f'{"cell":>18}{"native":>22}{"oracle":>22}'
                          f'{"operator stages":>20}']
        for cell in summary['failing_cells']:
            row = summary['cells'][cell]
            native, oracle = row[REGISTERED_OPERATOR_LABEL], row[CONTROL_OPERATOR_LABEL]
            audit = row['replacement_operator_on_true_chains']
            lines.append('  ' + f'{cell:>18}'
                         + '{:>22}'.format(f'{native["answers"]}/{native["strict"]}')
                         + '{:>22}'.format(f'{oracle["answers"]}/{oracle["strict"]}')
                         + '{:>20}'.format(f'{audit["stages_correct"]}/{audit["stages"]}'))
        lines.append('  native and oracle read answers/strict.  A cell whose oracle column '
                     'passes and whose native column fails is an OPERATOR failure;')
        lines.append('  a cell failing under both is a CONTROLLER failure.')
        failures = json.loads((out / f'pair-{key}/failures.json').read_text())['cells']
        lines += ['', f'  FAILING UNITS  [pair {key}]  (native transcripts + recomputed '
                      f'per-call operator errors)']
        for cell in summary['failing_cells']:
            for entry in failures.get(cell, [])[:args.units]:
                lines.append(f'    {cell}:{entry["index"]}  answer_correct='
                             f'{entry["answer_correct"]} strict={entry["strict_path"]} '
                             f'operator_calls_wrong={entry["operator_calls_wrong"]}/'
                             f'{entry["operator_calls_total"]}')
                for side, native in entry['native'].items():
                    lines.append(f'      {side} truth      {native["truth_chain"]}')
                    lines.append(f'      {side} native     {native["transcript"]} '
                                 f'[{native["status"]}]')
                    lines.append(f'      {side} oracle     '
                                 f'{entry["oracle_control"][side]["transcript"]} '
                                 f'[{entry["oracle_control"][side]["status"]}]')
                    for stage in entry['operator_call_errors'][side]:
                        lines.append(f'      {side} op error  entity {stage["entity"]} op '
                                     f'{stage["operation"]} -> {stage["predicted"]} '
                                     f'(true {stage["target"]})')
            more = max(0, len(failures.get(cell, [])) - args.units)
            if more:
                lines.append(f'    ... {more} further failing units of {cell} in '
                             f'pair-{key}/failures.json')
    text = '\n'.join(lines)
    print(text)
    if args.write:
        with (out / 'REPORT.txt').open('x') as handle:
            handle.write(text + '\n')
    return text


# --------------------------------------------------------------------------- CLI


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)

    p = sub.add_parser('freeze', help='freeze the six checkpoint hashes and the panels')
    p.add_argument('--out', required=True)
    p.add_argument('--panels', default=str(DEFAULT_PANELS))
    p.add_argument('--dispatcher-root', default=str(DEFAULT_DISPATCHER_ROOT))
    p.add_argument('--operator-root', default=str(DEFAULT_OPERATOR_ROOT))
    p.add_argument('--seeds', default=','.join(str(s) for s in PAIR_SEEDS))
    p.add_argument('--mark', type=int, default=CELL_MARK)
    p.add_argument('--eval-cap', type=int, default=EVAL_CAP)

    p = sub.add_parser('run', help='score the frozen pairings')
    p.add_argument('--out', required=True)
    p.add_argument('--pair', default=None, help='one pairing only (default: all)')

    p = sub.add_parser('report')
    p.add_argument('--out', required=True)
    p.add_argument('--units', type=int, default=8,
                   help='failing units printed per cell (the file holds all of them)')
    p.add_argument('--write', action='store_true')

    p = sub.add_parser('replicate', help='DEVELOPMENT re-score with an arbitrary operator')
    p.add_argument('--run', required=True)
    p.add_argument('--operator', default=str(ORIGINAL_OPERATOR))
    p.add_argument('--panels', default=str(DEFAULT_PANELS))
    p.add_argument('--out', required=True)
    p.add_argument('--eval-cap', type=int, default=EVAL_CAP)
    p.add_argument('--mark', type=int, default=CELL_MARK)

    args = parser.parse_args(argv)
    if args.command == 'freeze':
        freeze(args)
    elif args.command == 'run':
        run(args)
    elif args.command == 'report':
        report(args)
    else:
        replicate(args)


if __name__ == '__main__':
    main()
