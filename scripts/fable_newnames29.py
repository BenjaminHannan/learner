"""Experiment 29 / M1-F10 -- Experiment 27 with four more flat-LR updates.

This is intentionally a thin coordinator over fable_newnames27. It never copies
Experiment 27's model, data, scorer, loss, optimiser, curriculum, or gate arithmetic.
Instead, every delegated call temporarily patches the globals that Experiment 27 reads at
call time (Python functions resolve module globals when they execute), then restores them.

The one recipe change is the learning-rate schedule for control/F/L:
  * steps 0..3999: Experiment 27 exactly;
  * steps 4000..7999: 1e-3;
  * steps 8000..9999: Experiment 27's schedule evaluated at step-4000.
F6 is Experiment 27's arm F for 6,000 updates with Experiment 27's unchanged schedule.
The curriculum, hint switch, story growth, world stream, optimiser, clipping, and loss all
continue to see the TRUE update number. Only V.lr_at is intercepted.

The coordinator's struck PASS-WITH-GAP proposal is NOT implemented. Verdicts are exactly
Experiment 27's: PASS requires 3/3 F seeds to satisfy both all ten cutoffs and every paired
mark; otherwise PARTIAL/FAIL (subject to INVALID/INCOMPLETE/VOID precedence).
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import math
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKTREE = HERE.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import fable_newnames27 as X                                              # noqa: E402


# ---------------------------------------------------------------- registration

OUT = WORKTREE/'artifacts/fable-newnames29-20260921'
POOL_SOURCE = X.POOL_SOURCE

SEEDS = (2106, 2107, 2108)
ARMS = ('control', 'F', 'L', 'F6')
CODE_ARMS = ('F', 'L', 'F6')
UPDATES = 10_000
F6_UPDATES = 6_000

CODE_SCALE = X.CODE_SCALE
TRAIN_CODE_NAMESPACE = 'newnames29/train-codes'
PANEL_CODE_NAMESPACE = 'newnames29/panel-codes'
PANEL_NAMESPACE = 'newnames29-operator-v1-20260921'
PANEL_SEED_BASE = 202609212900

CUTOFFS = X.CUTOFFS
PAIRED_SLACK = X.PAIRED_SLACK
PANEL_N = X.PANEL_N
TRACE_EVERY = X.TRACE_EVERY

# Saved before any monkey-patching. These are the exact Experiment-27 code paths.
_LR27 = X.V.lr_at
_X_SOURCE_FILES = X.source_files
_X_TRACE_ROW = X.trace_row
_X_TRAIN_RUN = X.train_run
_X_GATE_TABLE = X.gate_table
_X_WRITE_NEW = X.C.write_new
_X_SCORE_CELL = X.R.score_cell

_MISSING = object()
_ACTIVE = {
    'arm': None,
    'mode': None,
    'last_lr': None,
    'last_lr_step': None,
    'fingerprint_at_4000': None,
    'score_records': [],
}


# ------------------------------------------------------------- source identity

def source_files():
    """Experiment 27's complete fingerprint set plus this coordinator."""
    files = dict(_X_SOURCE_FILES())
    mine = str(Path(__file__).resolve())
    files[mine] = X.C.sha(mine)
    assert str(Path(X.__file__).resolve()) in files
    return {name: files[name] for name in sorted(files)}


def source_fingerprint(files=None):
    files = files if files is not None else source_files()
    payload = json.dumps(files, sort_keys=True, separators=(',', ':')).encode()
    return hashlib.sha256(payload).hexdigest()


def provenance():
    files = source_files()
    return dict(X.N.provenance(), source_fingerprint=source_fingerprint(files),
                source_files=files, experiment='29/M1-F10')


# -------------------------------------------------------------- LR schedules

def expected_updates(arm):
    if arm not in ARMS:
        raise AssertionError(arm)
    return F6_UPDATES if arm == 'F6' else UPDATES


def lr_at(step, arm='F'):
    """Declared Experiment-29 LR at zero-based optimiser update step."""
    step = int(step)
    if step < 0:
        raise ValueError(step)
    if arm == 'F6':
        return float(_LR27(step))
    if arm not in ('control', 'F', 'L'):
        raise AssertionError(arm)
    if step < 4000:
        return float(_LR27(step))
    if step < 8000:
        return 1e-3
    return float(_LR27(step - 4000))


def _lr_dispatch(step):
    """Function temporarily installed as V.lr_at during a delegated run."""
    arm = _ACTIVE['arm']
    value = lr_at(step, arm='F6' if arm == 'F6' else (arm or 'F'))
    _ACTIVE['last_lr'] = value
    _ACTIVE['last_lr_step'] = int(step)
    return value


def f6_schedule_matches_27():
    return all(lr_at(step, 'F6') == float(_LR27(step))
               for step in range(F6_UPDATES))


# -------------------------------------------------------------- inert logging

def _trace_row29(model, batch, updates):
    row = _X_TRACE_ROW(model, batch, updates)
    if _ACTIVE['last_lr'] is None:
        raise RuntimeError('trace requested before the optimiser used a learning rate')
    row['lr'] = float(_ACTIVE['last_lr'])
    row['lr_step'] = int(_ACTIVE['last_lr_step'])
    if updates == 4000 and _ACTIVE['arm'] in ('F', 'F6'):
        _ACTIVE['fingerprint_at_4000'] = X.C.fingerprint(model)
    return row


def _scalar(value):
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    try:
        if getattr(value, 'numel', lambda: 2)() == 1:
            return value.item()
    except Exception:                                                       # noqa: BLE001
        pass
    return _MISSING


def _compact_records(records, group):
    out = []
    if not isinstance(records, (list, tuple)):
        return out
    for i, record in enumerate(records):
        if isinstance(record, dict):
            compact = {'group': group, 'question_index': i}
            for key, value in record.items():
                scalar = _scalar(value)
                if scalar is not _MISSING:
                    compact[key] = scalar
            out.append(compact)
    return out


def _score_cell29(*args, **kwargs):
    """Observe scorer records without changing the scorer's return value."""
    result = _X_SCORE_CELL(*args, **kwargs)
    if isinstance(result, dict):
        records = result.get('records')
        if records:
            group = f'call-{len(_ACTIVE["score_records"])}'
            for key in ('cell', 'name', 'pool', 'split'):
                if key in result and _scalar(result[key]) is not _MISSING:
                    group += f':{key}={result[key]}'
            _ACTIVE['score_records'].extend(_compact_records(records, group))
    return result


def _walk_records(value, path='root'):
    """Recover scorer records retained inside a score payload."""
    found = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f'{path}/{key}'
            if key == 'records':
                found.extend(_compact_records(child, path))
            else:
                found.extend(_walk_records(child, child_path))
    elif isinstance(value, (list, tuple)):
        for i, child in enumerate(value):
            if isinstance(child, (dict, list, tuple)):
                found.extend(_walk_records(child, f'{path}/{i}'))
    return found


def _write_new29(path, payload):
    """Add observational fields before Experiment 27 performs its create-only write."""
    path = Path(path)
    if isinstance(payload, dict) and path.name == 'training.json' and _ACTIVE['mode'] == 'train':
        payload['fingerprint_at_4000'] = _ACTIVE['fingerprint_at_4000']
        payload['lr_schedule'] = ('experiment27-unchanged' if _ACTIVE['arm'] == 'F6'
                                  else 'm1-f10-flat-through-7999')
    elif isinstance(payload, dict) and _ACTIVE['mode'] == 'score':
        records = _walk_records(payload)
        if not records:
            records = list(_ACTIVE['score_records'])
        if records:
            payload.setdefault('per_question_records', records)
    return _X_WRITE_NEW(path, payload)


# ------------------------------------------------------- F6 equality adapter

class _F6Arm(str):
    """Serialize/display as F6 while taking Experiment 27's arm-F branches."""

    def __new__(cls):
        return super().__new__(cls, 'F6')

    def __eq__(self, other):
        return str(other) in ('F', 'F6')

    def __ne__(self, other):
        return not self.__eq__(other)

    __hash__ = str.__hash__

    def __reduce_ex__(self, protocol):
        return (str, ('F6',))


def _x_arm(arm):
    return _F6Arm() if arm == 'F6' else arm


# ------------------------------------------------------------ patch boundary

@contextlib.contextmanager
def _patched_x(arm=None, mode=None):
    """Temporarily lend Experiment 27 Experiment-29 constants and hooks.

    Functions defined in fable_newnames27 resolve SEEDS, UPDATES, namespaces and source
    helpers from X's module globals at call time, so these bindings affect the delegated
    call without copying its implementation. Every binding is restored in finally.
    """
    expected = expected_updates(arm) if arm in ARMS else UPDATES
    replacements = {
        'OUT': OUT,
        'POOL_SOURCE': POOL_SOURCE,
        'SEEDS': SEEDS,
        'ARMS': ARMS,
        'CODE_ARMS': CODE_ARMS,
        'UPDATES': expected,
        'CODE_SCALE': CODE_SCALE,
        'TRAIN_CODE_NAMESPACE': TRAIN_CODE_NAMESPACE,
        'PANEL_CODE_NAMESPACE': PANEL_CODE_NAMESPACE,
        'PANEL_NAMESPACE': PANEL_NAMESPACE,
        'PANEL_SEED_BASE': PANEL_SEED_BASE,
        'source_files': source_files,
        'source_fingerprint': source_fingerprint,
        'provenance': provenance,
        'trace_row': _trace_row29,
        'run_integrity': run_integrity,
        'gate_table': gate_table,
    }
    old = {name: getattr(X, name, _MISSING) for name in replacements}
    old_lr = X.V.lr_at
    old_write = X.C.write_new
    old_score_cell = X.R.score_cell
    old_active = dict(_ACTIVE)
    try:
        for name, value in replacements.items():
            setattr(X, name, value)
        X.V.lr_at = _lr_dispatch
        X.C.write_new = _write_new29
        X.R.score_cell = _score_cell29
        _ACTIVE.update(arm=arm, mode=mode, last_lr=None, last_lr_step=None,
                       fingerprint_at_4000=None, score_records=[])
        yield
    finally:
        X.V.lr_at = old_lr
        X.C.write_new = old_write
        X.R.score_cell = old_score_cell
        for name, value in old.items():
            if value is _MISSING:
                delattr(X, name)
            else:
                setattr(X, name, value)
        _ACTIVE.clear()
        _ACTIVE.update(old_active)


# --------------------------------------------------------------- train/score

def train_run(arm, seed, exp, updates=None, out=None, wave_start=None,
              fixture_step0=0, pool=None, log_every=X.S.LOG_EVERY,
              trace_every=TRACE_EVERY, code_scale=None, code_namespace=None):
    """Delegate one run to Experiment 27 under the registered Experiment-29 globals."""
    if arm not in ARMS:
        raise AssertionError(arm)
    requested = expected_updates(arm) if updates is None else int(updates)
    with _patched_x(arm, mode='train'):
        return _X_TRAIN_RUN(
            _x_arm(arm), seed, exp, updates=requested, out=out, wave_start=wave_start,
            fixture_step0=fixture_step0, pool=pool, log_every=log_every,
            trace_every=trace_every, code_scale=code_scale, code_namespace=code_namespace)


def cmd_train(args):
    updates = expected_updates(args.arm) if args.updates is None else args.updates
    return train_run(args.arm, args.seed, Path(args.exp), updates=updates, out=args.out,
                     wave_start=args.wave_start, fixture_step0=args.fixture_step0,
                     trace_every=args.trace_every)


def cmd_score(args):
    clone = argparse.Namespace(**vars(args))
    clone.arm = _x_arm(args.arm) if args.arm else args.arm
    with _patched_x(args.arm, mode='score'):
        return X.cmd_score(clone)


# --------------------------------------------------------------- integrity

def _trace_expected_lr(arm, training, trace_row):
    step = trace_row.get('lr_step')
    if step is None:
        step = int(training.get('base_step', 0)) + int(trace_row['updates']) - 1
    return step, lr_at(step, arm)


def run_integrity(exp):
    """Experiment-29 hard integrity gate, evaluated before missing/VOID/marks."""
    exp = Path(exp)
    rows, problems = {}, []
    current_source = source_fingerprint()
    fingerprints_4000 = {}

    for arm in ARMS:
        for seed in SEEDS:
            name = f'{arm}-{seed}'
            path = exp/'runs'/name/'training.json'
            failure = exp/'runs'/name/'failure.json'
            if failure.exists():
                try:
                    bad = json.loads(failure.read_text())
                except Exception:                                           # noqa: BLE001
                    bad = {}
                if bad.get('invalid'):
                    problems.append(f'{name}: frozen-buffer tamper failure')
            if not path.exists():
                continue
            row = json.loads(path.read_text())
            expected = expected_updates(arm)
            rows[name] = dict(updates=row.get('updates'),
                              source_fingerprint=row.get('source_fingerprint'),
                              overrides=row.get('overrides') or {},
                              fingerprint_at_4000=row.get('fingerprint_at_4000'))
            if row.get('updates') != expected:
                problems.append(f'{name}: {row.get("updates")} updates, not {expected}')
            if row.get('overrides'):
                problems.append(f'{name}: overrides {row["overrides"]}')
            if row.get('source_fingerprint') != current_source:
                problems.append(f'{name}: source fingerprint differs from registered 29')
            if arm in ('F', 'F6'):
                # float32 stores 1.2 as 1.2000000476837158, so compare with a tolerance
                if abs(float(row.get('code_scale_final') or 0.0) - CODE_SCALE) > 1e-6:
                    problems.append(
                        f'{name}: frozen code_scale {row.get("code_scale_final")} != {CODE_SCALE}')
                fp = row.get('fingerprint_at_4000')
                if not fp:
                    problems.append(f'{name}: missing fingerprint_at_4000')
                else:
                    fingerprints_4000[(arm, seed)] = fp

            for tr in row.get('trace') or ():
                if 'lr' not in tr:
                    problems.append(f'{name}: trace row {tr.get("updates")} has no lr')
                    continue
                step, declared = _trace_expected_lr(arm, row, tr)
                actual = float(tr['lr'])
                if not math.isclose(actual, declared, rel_tol=0.0, abs_tol=1e-15):
                    problems.append(
                        f'{name}: logged lr {actual:.17g} != {declared:.17g} at step {step}')

    prints = sorted({r['source_fingerprint'] for r in rows.values()
                     if r.get('source_fingerprint')})
    if len(prints) > 1:
        problems.append(f'the runs were produced by {len(prints)} source versions: {prints}')

    for seed in SEEDS:
        f = fingerprints_4000.get(('F', seed))
        f6 = fingerprints_4000.get(('F6', seed))
        if f is not None and f6 is not None and f != f6:
            problems.append(
                f'F/F6 fingerprint mismatch at update 4000 for seed {seed}: {f} != {f6}')

    return dict(
        runs=rows, source_fingerprints=prints, fingerprint_at_4000={
            f'{arm}-{seed}': fp for (arm, seed), fp in fingerprints_4000.items()},
        problems=problems,
        rule=('each scored run must have its arm-specific registered update count '
              '(10,000; F6 6,000), no overrides, the registered source fingerprint, '
              'declared LR at every logged row, frozen F/F6 scale 1.2, and matching '
              'F/F6 update-4000 fingerprints per seed'))


# ----------------------------------------------------- descriptive diagnostics

def _correct(scoring, cell):
    item = scoring.get(cell) if isinstance(scoring, dict) else None
    if isinstance(item, bool):
        return int(item)
    if isinstance(item, int):
        return item
    if isinstance(item, float):
        return int(round(item * PANEL_N)) if 0 <= item <= 1 else int(round(item))
    if isinstance(item, dict):
        for key in ('correct', 'n_correct', 'score'):
            if key in item and isinstance(item[key], (int, float)):
                value = item[key]
                return int(round(value * PANEL_N)) if 0 <= value <= 1 and key == 'score' else int(value)
        if 'accuracy' in item and isinstance(item['accuracy'], (int, float)):
            return int(round(float(item['accuracy']) * PANEL_N))
    return None


def _cell_marks(reserved, trained):
    cells = {}
    for cell, cutoff in CUTOFFS.items():
        r, t = _correct(reserved, cell), _correct(trained, cell)
        cutoff_ok = r is not None and r >= cutoff
        paired_ok = r is not None and t is not None and r - t >= -PAIRED_SLACK
        cells[cell] = dict(reserved=r, trained=t, cutoff=cutoff,
                           cutoff_ok=cutoff_ok, paired_ok=paired_ok,
                           difference=None if r is None or t is None else r-t)
    return cells


def _diagnostic_tags(reserved, trained):
    cells = _cell_marks(reserved, trained)
    all_cutoffs = all(v['cutoff_ok'] for v in cells.values())
    all_paired = all(v['paired_ok'] for v in cells.values())
    misses = [c for c, v in cells.items() if not (v['cutoff_ok'] and v['paired_ok'])]
    six_cells = ('c1', 'c2', 'c3', 'c4', 'c5', 'c6', 's3')
    six_good = all(c in cells and cells[c]['cutoff_ok'] and cells[c]['paired_ok']
                   for c in six_cells)
    crowding_only = bool(misses) and six_good and all(c.startswith('p12-') for c in misses)
    return dict(
        cutoffs_met_paired_missed=bool(all_cutoffs and not all_paired),
        straddle=bool(all_cutoffs and not all_paired),
        crowding_only=crowding_only,
        cells=cells)


def _window_mean_link(row, lo, hi):
    values = [float(t['link_accuracy']) for t in row.get('trace') or ()
              if lo <= int(t.get('updates', -1)) <= hi and t.get('link_accuracy') is not None]
    return statistics.mean(values) if values else None


def _first_link_mistake_rate(score):
    records = score.get('per_question_records') or []
    chosen = []
    for rec in records:
        group = str(rec.get('group', '')).lower()
        if 'reserved' not in group or not ('p12-2' in group or 'p12-3' in group):
            continue
        value = _MISSING
        for key in ('first_link_correct', 'first_step_correct', 'link_correct'):
            if key in rec:
                value = rec[key]
                break
        if value is not _MISSING:
            chosen.append(bool(value))
    if not chosen:
        return None
    return 1.0 - sum(chosen)/len(chosen)


def gate_table(exp, wave=1):
    """Experiment 27's verdict plus Experiment-29 integrity and descriptive tags."""
    # CLI callers are already inside _patched_x; direct unit-test/library callers are not.
    # Re-enter once so Experiment 27's base gate sees 29's seeds/arms/namespaces too.
    if X.SEEDS != SEEDS or X.ARMS != ARMS:
        with _patched_x():
            return gate_table(exp, wave=wave)
    exp = Path(exp)
    table = _X_GATE_TABLE(exp, wave=wave)

    integrity = run_integrity(exp)
    table['integrity'] = integrity
    if integrity['problems']:
        table['verdict'] = 'INVALID'
        table['reason'] = (
            'a run violates Experiment-29 integrity: ' + '; '.join(integrity['problems']))

    scores = X.collect_scores(exp)
    descriptive = {}
    for arm in ('F', 'L', 'F6'):
        for seed in SEEDS:
            row = scores.get((arm, seed))
            if not row:
                continue
            reserved = row['scorings']['reserved']
            trained = row['scorings']['train']
            descriptive[f'{arm}-{seed}'] = _diagnostic_tags(reserved, trained)

    f6 = {}
    for seed in SEEDS:
        row = scores.get(('F6', seed))
        if row:
            f6[str(seed)] = X.seed_verdict(
                'F', row['scorings']['reserved'], reference=row['scorings']['train'])
    table['F6'] = f6
    table['descriptive_labels'] = descriptive

    late = {}
    for arm in ARMS:
        for seed in SEEDS:
            p = exp/'runs'/f'{arm}-{seed}'/'training.json'
            if not p.exists():
                continue
            row = json.loads(p.read_text())
            early = _window_mean_link(row, 5000, 6000)
            late_mean = _window_mean_link(row, 9000, 10000)
            if early is not None and late_mean is not None and late_mean < early - .02:
                late[f'{arm}-{seed}'] = dict(
                    late_instability=True, link_5000_6000=early,
                    link_9000_10000=late_mean, drop=early-late_mean)

    for seed_s, verdict in table.get('control', {}).items():
        if not verdict.get('passed'):
            late.setdefault(f'control-{seed_s}', {})['late_instability'] = True
            late[f'control-{seed_s}']['reason'] = 'control seed missed a cutoff'
    table['late_instability'] = late

    f_rates, f6_rates = {}, {}
    for seed in SEEDS:
        row = scores.get(('F', seed))
        if row:
            f_rates[str(seed)] = _first_link_mistake_rate(row)
        row6 = scores.get(('F6', seed))
        if row6:
            f6_rates[str(seed)] = _first_link_mistake_rate(row6)
    known = [v for v in f_rates.values() if v is not None]
    if len(known) == len(SEEDS) and all(v <= .025 for v in known):
        undertraining = 'undertraining_supported'
    elif len(known) == len(SEEDS) and statistics.median(known) >= .032:
        undertraining = 'undertraining_refuted'
    else:
        undertraining = 'undertraining_unclear'
    table['undertraining'] = dict(
        label=undertraining, F_first_step_mistake_rate=f_rates,
        F6_first_step_mistake_rate=f6_rates)

    table.setdefault('rules', {})['pass_with_gap'] = (
        'STRUCK: no PASS-WITH-GAP tier; cutoffs_met_paired_missed is descriptive only')
    return table


# -------------------------------------------------------------- delegated CLI

def _delegate(name, args, arm=None, mode=None):
    with _patched_x(arm, mode=mode):
        return getattr(X, name)(args)


def cmd_pool(args):
    return _delegate('cmd_pool', args)


def cmd_panels(args):
    return _delegate('cmd_panels', args)


def cmd_control_equivalence(args):
    return _delegate('cmd_control_equivalence', args)


def cmd_treatment_equivalence(args):
    return _delegate('cmd_treatment_equivalence', args)


def cmd_inertness(args):
    return _delegate('cmd_inertness', args)


def cmd_gates(args):
    return _delegate('cmd_gates', args)


def cmd_report(args):
    return _delegate('cmd_report', args)


def cmd_readouts(args):
    return _delegate('cmd_readouts', args, arm=args.arm)


def cmd_fingerprint(args):
    return _delegate('cmd_fingerprint', args)


def build_parser():
    with _patched_x():
        parser = X.build_parser()
    parser.description = __doc__.split('\n\n')[0]
    subparsers = next(a for a in parser._actions
                      if isinstance(a, argparse._SubParsersAction))
    train_parser = subparsers.choices['train']
    for action in train_parser._actions:
        if action.dest == 'updates':
            action.default = None
            action.help = 'fixture override; registered default is 10000 (F6: 6000)'
            break
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    X.configure_once()
    commands = {
        'pool': cmd_pool,
        'panels': cmd_panels,
        'train': cmd_train,
        'control-equivalence': cmd_control_equivalence,
        'treatment-equivalence': cmd_treatment_equivalence,
        'inertness': cmd_inertness,
        'score': cmd_score,
        'gates': cmd_gates,
        'report': cmd_report,
        'readouts': cmd_readouts,
        'fingerprint': cmd_fingerprint,
    }
    return commands[args.command](args)


if __name__ == '__main__':
    main()
