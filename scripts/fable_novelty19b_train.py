#!/usr/bin/env python3
"""novelty-19b -- U8 versus U5: the training side.

Experiment 19b is Astra's one next step after experiment 19 FAILED its registered rule
(design/v3/19-development-readout-and-next-step.md, "One next experiment" and
"Prospective marks").  D only.  Six continuations: arms U5 (control, uniform c=1..5) and
U8 (treatment, uniform c=1..8) from each of the three experiment-19 D awake finals.

-------------------------------------------------------------------------------
WHAT THIS MODULE IS
-------------------------------------------------------------------------------
An ADDITIVE module.  `scripts/fable_novelty19_train.py` is frozen (it is in experiment
19's freeze manifest) and is imported, never edited.  Everything that decides a number --
the model, the optimizer, the schedules, the rollout, the loss, the chunk/resume
machinery, the checkpoint binding, the caps check, the single-version fingerprint check,
the per-cell scoring and the failure-shape diagnostics -- is the frozen code, called.

What is genuinely new here, and only this:

  1. the EXP2 layout and the two arm names (one block, `# EXP2 layout` below);
  2. a per-update WORK LEDGER (Astra: "Record active calls and work"), written beside
     the run and derived from the row the frozen update already returns, so the training
     path itself is untouched;
  3. per-unit strict/answer flags in the score file, because condition 2 is a PAIRED
     contrast "on identical units" and the frozen score file records only cell totals;
  4. Astra's five development conditions, per seed, with no averaging.

-------------------------------------------------------------------------------
THE CAP / STOP BOUNDARY  (Astra: "verify this boundary on a disposable fixture")
-------------------------------------------------------------------------------
Astra requires: training cap eight, evaluation cap sixteen, STOP sampled AFTER the eighth
executed lookup so an eight-call answer can terminate normally, and a continuing episode
exhausted at the cap FAILS.

The frozen trainer already does exactly this and needs no override:

  * `fable_novelty19_train.D_TRAIN_CAP == 8` and `D_EVAL_CAP == 16` -- already the
    registered experiment-19 values, carried into 19b unchanged.
  * `fable_dispatcher_v4.rollout_v4` runs `for step in range(cap)`, and within ONE step
    it (a) picks subject and operation, (b) EXECUTES the lookup and appends the result,
    (c) computes `stop_logits(state)` on the post-lookup state and samples STOP.  So at
    `step == cap - 1` the cap-th lookup is executed and STOP is still sampled.
  * `status` is initialised to `'over_cap'` and is only ever overwritten by `'answered'`
    (STOP chosen) or `'invalid_action'`.  An episode still active when the loop ends
    therefore keeps `over_cap`, and `answer` keeps its initial 0, so it earns no reward.

Verified numerically by `python fable_novelty19b_train.py cap-probe` (disposable seed,
throwaway units, nothing written).  Measured at cap 8:

    never STOPs              STOP sampled at 8 steps  status=over_cap   calls=8
    STOPs after lookup 8     STOP sampled at 8 steps  status=answered   calls=8
    STOPs after lookup 7     STOP sampled at 7 steps  status=answered   calls=7

No minimal override was needed, so there is no modified loop to prove bit-identical:
the loop that runs 19b IS the frozen loop, byte for byte.

-------------------------------------------------------------------------------
WHAT IS DELIBERATELY NOT HERE
-------------------------------------------------------------------------------
No remaining-count feature, no gold path, no forced continuation, no new halting loss,
no success-adaptive schedule, no best-checkpoint or intermediate-panel selection, no seed
replacement, no extra budget.  Confirmation is NOT built: `confirmation_marks()` records
the scaled 512-unit marks for later and `score` refuses a confirmation suite outright.
"""
from __future__ import annotations

import argparse
import importlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fable_novelty19_train as TR                                          # noqa: E402

N19 = TR.N
V1, V3, V4 = TR.V1, TR.V3, TR.V4
torch = TR.torch
sha, write_new, configure = TR.sha, TR.write_new, TR.configure
MISSING = TR.MISSING
WRONG_CKPT = TR.WRONG_CKPT


# =========================================================================== EXP2 layout
# EVERY name the data builder owns lives in this block and nowhere else.  When builder A
# reports its final layout, only these lines change.

DATA_MODULE_NAME = 'fable_novelty19b_data'

# NOT `TR.BASE`: that is the main checkout, where the frozen trainer finds the canonical
# operator.  Every 19b and experiment-19 artifact lives in THIS worktree, which is the
# parent of this file's directory -- the same root the data module calls WORKTREE.
WORKTREE = Path(__file__).resolve().parent.parent

EXP2_DIRNAME = 'fable-novelty19b-u8-20260920'
EXP2 = WORKTREE / 'artifacts' / EXP2_DIRNAME

AWAKE_EXPERIMENT = WORKTREE / 'artifacts' / 'fable-novelty19-replay-20260920'
AWAKE_RUN = 'runs/awake-D-s{seed}'
AWAKE_FINAL = TR.checkpoint_name(TR.AWAKE_UPDATES)           # ckpt-006000.pt

DEV_PANELS = 'dev-panels'
BUFFERS_SEED = 'buffers-{seed}'                              # holds the two arms
RUN_DIR = 'runs/offline-D-s{seed}-{arm}'
AWAKE_SCORE = 'scores/awake-D-s{seed}.json'
OFFLINE_SCORE = 'scores/offline-D-s{seed}-{arm}.json'
WORK_LEDGER = 'work-{start:06d}-{stop:06d}.jsonl'

ARCH = 'D'
CONTROL_ARM, TREATMENT_ARM = 'U5', 'U8'
ARMS = (CONTROL_ARM, TREATMENT_ARM)
SEEDS = TR.REGISTERED_SEEDS                                  # (1900, 1901, 1902)

OFFLINE_UPDATES = 2000                                       # Astra: "exactly 2,000"
OFFLINE_CHUNK = TR.OFFLINE_CHUNK                             # 500, the registered ceiling
WORLDS_PER_UPDATE = 16
QUESTIONS_PER_WORLD = N19.BUFFER_QUESTIONS_PER_WORLD         # 4
EPISODES_PER_UPDATE = WORLDS_PER_UPDATE * QUESTIONS_PER_WORLD * TR.D_K   # 64 x 16 = 1024

TRAIN_CAP = TR.D_TRAIN_CAP                                   # 8
EVAL_CAP = TR.D_EVAL_CAP                                     # 16

# -- Astra's prospective marks, 64 units per cell ---------------------------------
BOUNDED_MARK = 58          # 1: >= 58/64 answers AND strict, N/P c=4/5 and the nine c=6..8
GAIN_MARK = 13             # 2: U8 strict - U5 strict >= 13/64 on identical units
GUARD_MARK = 58            # 3: >= 58/64 strict pair units in each c=5 and c=8 E cell
RETENTION_F_MARK = 61      # 4: >= 61/64 answers AND strict in all seven F cells
RETENTION_H_MARK = 58      # 4: >= 58/64 both metrics in all four H cells
H_LOSS_LIMIT = 7           # 4: no H-cell loss >= 7/64 from that seed's awake anchor
UNITS_PER_CELL = 64
CONFIRM_UNITS = 512


def confirmation_marks():
    """Astra's scaling for the LATER 512-unit confirmation.  Nothing here builds it."""
    return dict(units=CONFIRM_UNITS, bounded=464, retention_f=488, gain=104, h_loss=56,
                note='recorded so the numbers are not re-derived later; experiment 19b '
                     'builds NO confirmation suite and `score` refuses one')


# =========================================================================== data module


_DATA_OVERRIDE = None


def data_module():
    """The 38-cell data module, or a clear refusal naming what is missing.

    Tests inject a stub through `use_data_module`; nothing else may reach around this.
    """
    if _DATA_OVERRIDE is not None:
        return _DATA_OVERRIDE
    try:
        return importlib.import_module(DATA_MODULE_NAME)
    except ImportError as exc:
        raise SystemExit(
            f'experiment 19b needs {DATA_MODULE_NAME}.py (builder A owns it): {exc}.  '
            f'`offline` does not need it; `score`, `gates` and `report` do.') from None


class use_data_module:
    """Context manager: run a block against a given data module (tests, fixtures)."""

    def __init__(self, module):
        self.module = module

    def __enter__(self):
        global _DATA_OVERRIDE
        self.previous = _DATA_OVERRIDE
        _DATA_OVERRIDE = self.module
        return self.module

    def __exit__(self, *exc):
        global _DATA_OVERRIDE
        _DATA_OVERRIDE = self.previous
        return False


def cell_specs(module=None):
    """{name: cfg} for the 38 registered cells, from the data module that owns them."""
    module = module or data_module()
    cells = getattr(module, 'CELLS', None)
    if not isinstance(cells, dict) or not cells:
        raise SystemExit(f'{getattr(module, "__name__", module)} exposes no CELLS table')
    return cells


def cell_order(module=None):
    module = module or data_module()
    order = getattr(module, 'CELL_ORDER', None)
    return tuple(order) if order else tuple(sorted(cell_specs(module)))


def check_layout_agrees(module=None):
    """Refuse to run if this module and the data module disagree about the experiment.

    Builder A owns the buffers, the panels and the cells; this module owns the training.
    They were written concurrently against the same specification, so every constant they
    BOTH name is a place they can silently drift apart.  Each one is compared here, and a
    mismatch is a refusal rather than a quietly different experiment.
    """
    module = module or data_module()
    name = getattr(module, '__name__', str(module))
    problems = []

    def same(label, mine, theirs):
        if theirs is not None and mine != theirs:
            problems.append(f'{label}: this module says {mine!r}, {name} says {theirs!r}')

    same('arms', ARMS, tuple(getattr(module, 'ARMS', ())) or None)
    same('control arm', CONTROL_ARM, getattr(module, 'CONTROL_ARM', None))
    same('treatment arm', TREATMENT_ARM, getattr(module, 'TREATMENT_ARM', None))
    same('seeds', tuple(int(s) for s in SEEDS),
         tuple(int(s) for s in getattr(module, 'SEEDS', ())) or None)
    same('offline updates', OFFLINE_UPDATES, getattr(module, 'OFFLINE_UPDATES', None))
    same('units per cell', UNITS_PER_CELL, getattr(module, 'DEV_N', None))
    same('confirmation units', CONFIRM_UNITS, getattr(module, 'CONFIRM_N', None))
    same('EXP2 root', EXP2.resolve(), Path(getattr(module, 'EXP2_DEFAULT', EXP2)).resolve())
    arm_calls = getattr(module, 'ARM_CALLS', None)
    if arm_calls:
        same('U5 length law', tuple(range(1, 6)), tuple(arm_calls.get(CONTROL_ARM, ())))
        same('U8 length law', tuple(range(1, 9)), tuple(arm_calls.get(TREATMENT_ARM, ())))
    marks = getattr(module, 'MARKS', None)
    if marks:
        same('bounded mark', BOUNDED_MARK, marks['bounded_competence'].get('dev'))
        same('gain mark', GAIN_MARK, marks['treatment_effect'].get('dev'))
        same('guard mark', GUARD_MARK, marks['guards'].get('dev'))
        same('F mark', RETENTION_F_MARK, marks['retention_f'].get('dev'))
        same('H mark', RETENTION_H_MARK, marks['retention_h'].get('dev'))
        same('H loss limit', H_LOSS_LIMIT,
             marks['retention_h'].get('max_loss_vs_awake_anchor', {}).get('dev'))
        scaled = confirmation_marks()
        same('confirmation bounded', scaled['bounded'], marks['bounded_competence'].get('confirm'))
        same('confirmation gain', scaled['gain'], marks['treatment_effect'].get('confirm'))
        same('confirmation F', scaled['retention_f'], marks['retention_f'].get('confirm'))
        same('confirmation H loss', scaled['h_loss'],
             marks['retention_h'].get('max_loss_vs_awake_anchor', {}).get('confirm'))
    cells = cell_specs(module)
    if len(cells) != 38:
        problems.append(f'cell count: {name} registers {len(cells)} cells, Astra specifies 38')
    if problems:
        raise SystemExit('experiment 19b is not one experiment -- the training and data '
                         'modules disagree:\n  ' + '\n  '.join(problems))
    return dict(data_module=name, data_module_sha256=sha(module.__file__),
                arms=list(ARMS), seeds=[int(s) for s in SEEDS], cells=len(cells),
                checked=['arms', 'seeds', 'updates', 'units', 'length laws', 'every mark',
                         'EXP2 root', 'cell count'])


def registered_cells(module=None):
    """The context manager that lends the new cell names to V3.CELLS while scoring."""
    module = module or data_module()
    return module.registered_cells()


# ---- cell GROUPS are selected by SPECIFICATION, never by name ---------------------
# Builder A owns the names; Astra's conditions are stated in terms of hops, world size,
# ending and pair-ness.  Selecting structurally means a name change cannot silently
# empty one of the five conditions.

def family_of(cell):
    return TR.family_of(cell)


def structural_groups(module=None):
    """Astra's cell groups, derived from the cell SPECIFICATIONS -- never from names.

    Astra states the conditions in terms of chain length, world size, ending and
    pair-ness, so that is what is matched on.  This is the independent derivation that
    `groups()` checks the data module's published lists against.
    """
    module = module or data_module()
    cells, order = cell_specs(module), cell_order(module)

    def pick(test):
        return tuple(c for c in order if test(c, cells[c]))

    long_cells = pick(lambda c, g: g['hops'] in (6, 7, 8) and int(g['people']) == 16
                      and g['kind'] == 'single')
    return dict(
        all=order,
        # 1: bounded competence -- every N/P cell at c=4/5, plus all nine c=6..8 cells
        bounded=pick(lambda c, g: family_of(c) in ('N', 'P')
                     and g['hops'] in (4, 5)) + long_cells,
        long=long_cells,
        # 2: the three held-out-ending long cells, r10 p16
        contrast=tuple(c for c in long_cells if cells[c]['fixed_terminal'] == 10),
        # 3: the E edit-pair guards at c=5 and c=8
        guards=pick(lambda c, g: g['kind'] == 'pair' and g['hops'] in (5, 8)),
        # 4: retention
        retention_f=pick(lambda c, g: family_of(c) == 'F'),
        retention_h=pick(lambda c, g: family_of(c) == 'H'))


GROUP_OF_MARK = dict(bounded='bounded_competence', contrast='treatment_effect',
                     guards='guards', retention_f='retention_f', retention_h='retention_h')


def groups(module=None):
    """The cell groups Astra's five conditions are read over.

    The data module PUBLISHES these lists in `MARKS`; this module DERIVES them from the
    cell specifications.  Both are used: the published list is authoritative, and a
    disagreement with the derivation is a refusal.  One of the two would have to be wrong
    in exactly the same way as the other for a mis-specified condition to get through.
    """
    module = module or data_module()
    derived = structural_groups(module)
    marks = getattr(module, 'MARKS', None)
    if not marks:
        return derived
    published, disagreements = {}, []
    for group, mark in GROUP_OF_MARK.items():
        listed = tuple(marks[mark].get('cells', ()))
        if not listed:
            continue
        published[group] = listed
        if set(listed) != set(derived[group]):
            disagreements.append(
                f'{group}: {getattr(module, "__name__", module)}.MARKS lists '
                f'{sorted(listed)}, the cell specifications give {sorted(derived[group])}')
    if disagreements:
        raise SystemExit('the published and derived cell groups disagree, so one of Astra\'s '
                         'conditions would be read over the wrong cells:\n  '
                         + '\n  '.join(disagreements))
    out = dict(derived)
    for group, listed in published.items():          # keep the data module's ORDER
        out[group] = listed
    return out


def expected_group_sizes():
    """What Astra's text says each group must contain; `report` checks the real ones.

    bounded = four N cells at c=4/5 x p6/p16, eight P cells at c=4/5 x r8/r9 x p6/p16,
    and the nine new c=6/7/8 x r=8/9/10 p16 cells.
    """
    return dict(all=38, bounded=4 + 8 + 9, long=9, contrast=3, guards=3 + 3,
                retention_f=7, retention_h=4)


# =========================================================================== work ledger


def work_row(update, row, episodes_per_update=EPISODES_PER_UPDATE):
    """Active calls and work for ONE update, from the row the frozen update returned.

    `mean_calls` is the mean number of EXECUTED lookups per episode, so the total work
    of an update is that mean times the episode count -- exact arithmetic on a recorded
    number, not a second measurement.  Astra: "equal updates are not equal useful
    computation", so the share of episodes that answered, hit the cap or acted illegally
    is carried alongside.
    """
    invalid = float(row.get('invalid_fraction') or 0.)
    over_cap = float(row.get('over_cap_fraction') or 0.)
    mean_calls = float(row['mean_calls'])
    return dict(update=int(update), episodes=int(episodes_per_update),
                mean_calls=mean_calls,
                active_calls=int(round(mean_calls * episodes_per_update)),
                answered_fraction=max(0., 1. - invalid - over_cap),
                invalid_fraction=invalid, over_cap_fraction=over_cap,
                mean_reward=float(row.get('mean_reward', 0.)),
                entropy=float(row.get('entropy', 0.)))


class work_ledger:
    """Records `work_row` for EVERY update, without touching the training path.

    The frozen `run_phase` writes its own jsonl only every 100 updates, and the episode
    tensors are gone by the time it returns, so the only place the per-update numbers
    exist is inside `dispatcher_update`.  This swaps that name in the frozen module for a
    wrapper that CALLS THE ORIGINAL and returns ITS EXACT OBJECT, unmodified -- the row
    that gets chained into `update_fingerprint` and written to the log is the same object
    the frozen function built, so the run is bit-identical with the ledger on or off.
    `tests/test_fable_novelty19b_train.py` checks that on a fixture.
    """

    def __init__(self, folder, *, enabled=True):
        self.folder = Path(folder)
        self.enabled = bool(enabled)
        self.rows = []
        self.handle = None
        self._original = None

    def __enter__(self):
        if not self.enabled:
            return self
        self._original = TR.dispatcher_update
        ledger = self

        def instrumented(model, flags, operator, optimizer, generator, record, update, total):
            row = ledger._original(model, flags, operator, optimizer, generator,
                                   record, update, total)
            ledger.note(row)
            return row                      # the ORIGINAL object, untouched

        TR.dispatcher_update = instrumented
        return self

    def __exit__(self, *exc):
        if self._original is not None:
            TR.dispatcher_update = self._original
            self._original = None
        self.close()
        return False

    def note(self, row):
        entry = work_row(row['update'], row)
        self.rows.append(entry)
        if self.handle is None:
            self.folder.mkdir(parents=True, exist_ok=True)
            start = entry['update']
            path = self.folder / WORK_LEDGER.format(start=start, stop=start)
            # the chunk's end is not known until it finishes; the file is renamed then
            self.path = path.with_suffix('.jsonl.partial')
            self.handle = self.path.open('a')
        self.handle.write(json.dumps(entry) + '\n')
        self.handle.flush()

    def close(self):
        if self.handle is not None:
            self.handle.close()
            self.handle = None
            if self.rows:
                final = self.folder / WORK_LEDGER.format(start=self.rows[0]['update'],
                                                         stop=self.rows[-1]['update'] + 1)
                if not final.exists():
                    self.path.rename(final)

    def summary(self):
        if not self.rows:
            return None
        calls = [r['active_calls'] for r in self.rows]
        return dict(updates=len(self.rows), active_calls_total=sum(calls),
                    active_calls_per_update=sum(calls) / len(self.rows),
                    mean_calls_first=self.rows[0]['mean_calls'],
                    mean_calls_last=self.rows[-1]['mean_calls'],
                    answered_fraction_last=self.rows[-1]['answered_fraction'],
                    episodes_per_update=EPISODES_PER_UPDATE,
                    note='active_calls = executed lookups; work per update, not updates')


# =========================================================================== offline


def awake_source(seed):
    """The experiment-19 D awake final for `seed`.  READ ONLY -- never written to."""
    return AWAKE_EXPERIMENT / AWAKE_RUN.format(seed=int(seed)) / AWAKE_FINAL


def resolve_buffers(exp, seed, arm):
    """The buffer folder for one seed and arm, and the `--arm` key inside it.

    The data module builds v19's flat layout -- `buffers-<seed>/` holding buffer-U5.pt,
    buffer-U8.pt and ONE shared offline-order.json -- which is what Astra's "share the
    world-index order across arms" asks for in the strongest available form: the two arms
    do not merely follow equal orders, they read the same bytes.  The nested
    `buffers-<seed>/<arm>/` layout is still accepted so that a future split cannot
    silently score as a missing buffer.
    """
    root = Path(exp) / BUFFERS_SEED.format(seed=int(seed))
    nested = root / arm
    if (nested / 'manifest.json').is_file():
        return nested
    if (root / 'manifest.json').is_file():
        return root
    raise SystemExit(f'no buffer manifest for seed {seed} arm {arm}: tried '
                     f'{nested}/manifest.json and {root}/manifest.json')


def offline_order_digest(folder):
    """sha256 of the world-index order file a buffer folder follows."""
    path = Path(folder) / 'offline-order.json'
    if not path.is_file():
        return None
    return sha(path)


def shared_order(exp, seed):
    """Astra: "Share the world-index order ... across arms."  Checked, not assumed."""
    per_arm = {}
    for arm in ARMS:
        try:
            per_arm[arm] = offline_order_digest(resolve_buffers(exp, seed, arm))
        except SystemExit:
            per_arm[arm] = None
    values = list(per_arm.values())
    return dict(seed=int(seed), per_arm=per_arm,
                passed=(None if any(v is None for v in values)
                        else bool(len(set(values)) == 1)))


def verified_awake_start(seed):
    """The awake checkpoint, re-hashed against its OWN chunk record before anything loads.

    `TR.verify_recorded_sha` is the frozen must-fix-5 check: it finds the
    `chunk-*.json` / `completion.json` in the checkpoint's own run directory that names
    the file and compares the recorded sha256 to the bytes on disk, refusing an orphan or
    a changed checkpoint.  Astra: start from awake, never from an offline U checkpoint --
    the phase and seed are checked here and AGAIN inside the frozen `run_phase`.
    """
    path = awake_source(seed)
    if not path.is_file():
        raise SystemExit(f'no experiment-19 awake final at {path}; 19b starts from those '
                         f'checkpoints and builds none of its own')
    record = TR.verify_recorded_sha(path)
    saved = torch.load(path, map_location='cpu', weights_only=False)
    if saved.get('phase') != 'awake':
        raise SystemExit(f'{path} is a {saved.get("phase")!r} checkpoint; 19b restarts from '
                         f'AWAKE, never from an offline checkpoint')
    if saved.get('arch') != ARCH or int(saved.get('seed')) != int(seed):
        raise SystemExit(f'{path} holds {saved.get("arch")}/seed {saved.get("seed")}, '
                         f'asked for {ARCH}/seed {seed}')
    if int(saved.get('updates_done', -1)) != TR.AWAKE_UPDATES:
        raise SystemExit(f'{path} holds {saved.get("updates_done")} updates, not the awake '
                         f'final {TR.AWAKE_UPDATES}')
    record.update(phase='awake', arch=ARCH, seed=int(seed),
                  updates_done=int(saved['updates_done']),
                  final_weight_fingerprint=saved.get('final_weight_fingerprint'))
    return path, record


def offline(args):
    """One continuation: 2,000 offline updates from an experiment-19 awake final."""
    if args.arm not in ARMS:
        raise SystemExit(f'--arm must be one of {list(ARMS)}; 19b has no other arm')
    if int(args.updates) != OFFLINE_UPDATES:
        raise SystemExit(f'experiment 19b is exactly {OFFLINE_UPDATES} updates '
                         f'(Astra: "Both arms receive exactly 2,000 updates")')
    awake_ckpt, awake_record = verified_awake_start(args.seed)
    buffers = resolve_buffers(args.exp, args.seed, args.arm)
    manifest = json.loads((buffers / 'manifest.json').read_text())
    if int(manifest['seed']) != int(args.seed):
        raise SystemExit(f'{buffers} holds seed {manifest["seed"]}, asked for {args.seed}')
    if args.arm not in manifest['arms']:
        raise SystemExit(f'{buffers} has no arm {args.arm}; it holds {manifest["arms"]}')
    order = TR.read_offline_order(buffers)
    if int(order['seed']) != int(args.seed):
        raise SystemExit(f'{buffers}/offline-order.json holds a different seed')
    if int(order['updates']) < int(args.updates):
        raise SystemExit(f'offline-order.json holds {order["updates"]} updates, '
                         f'{args.updates} requested')
    buffer_record = N19.load_buffer(buffers, args.arm)

    inputs_record = dict(
        experiment='novelty19b', buffers=str(buffers.resolve()),
        buffers_manifest_sha256=sha(buffers / 'manifest.json'),
        buffer_file=f'buffer-{args.arm}.pt',
        buffer_sha256=manifest['files'][f'buffer-{args.arm}.pt'],
        buffer_audit_sha256=manifest.get('audit_sha256'),
        offline_order_sha256=sha(buffers / 'offline-order.json'),
        offline_order_namespace=order.get('namespace'),
        offline_order_digest=order.get('order_sha256'),
        worlds=len(buffer_record['stories']), questions=len(buffer_record['items']),
        awake_start=str(awake_ckpt), awake_start_record=awake_record,
        train_cap=TRAIN_CAP, eval_cap=EVAL_CAP,
        arm_note='U5 and U8 differ ONLY in the length law of the accepted practice buffer; '
                 'the world bytes, the world-index order, the awake start, the optimizer '
                 'reset, the policy RNG seeding, the schedules and every hyper-parameter '
                 'are the frozen experiment-19 ones',
        stop_boundary='train cap 8: rollout_v4 samples STOP after the 8th executed lookup, '
                      'so an 8-call answer is status="answered"; an episode still active '
                      'when the loop ends keeps status="over_cap" and answer 0')

    folder = Path(args.out)
    ledger = work_ledger(folder, enabled=not args.no_work_ledger)
    with ledger:
        result = TR.run_phase(
            out=folder, arch=ARCH, seed=args.seed, phase='offline',
            total=args.updates, chunk=args.chunk_updates, budget=args.budget_seconds,
            feed_factory=lambda lo, hi: TR.offline_feed(buffer_record, order, lo, hi),
            inputs_record=inputs_record, arm=args.arm, awake_ckpt=str(awake_ckpt),
            argv=sys.argv, progress=not args.quiet)
    summary = ledger.summary()
    if summary is not None:
        write_new(folder / f'work-summary-{int(time.time())}.json',
                  dict(kind='novelty19b-work', arch=ARCH, seed=int(args.seed), arm=args.arm,
                       **summary))
        if not args.quiet:
            print(json.dumps(dict(event='work', arm=args.arm, seed=int(args.seed), **summary)),
                  flush=True)
    return result


# =========================================================================== score


def unit_flags(native, units):
    """Per-unit answer/strict flags, so condition 2 can be a PAIRED contrast.

    `V3.aggregate` (which the frozen scorer stores) gives cell TOTALS only, and Astra's
    treatment effect is "on identical units", with paired wins and losses published.  A
    pair cell scores a unit only if BOTH twins succeed, exactly as `aggregate` does.
    """
    sides = list(native)
    index = [int(u['index']) for u in units]
    correct = [int(all(native[s][i]['correct'] for s in sides)) for i in range(len(units))]
    strict = [int(all(native[s][i]['strict_path'] for s in sides)) for i in range(len(units))]
    calls = [max(int(native[s][i]['calls']) for s in sides) for i in range(len(units))]
    return dict(unit_index=index, answers=correct, strict=strict, calls=calls,
                note='aligned lists; a pair cell counts a unit only when both twins pass')


def score(args):
    configure()
    module = data_module()
    layout = check_layout_agrees(module)
    if args.eval_cap != EVAL_CAP:
        raise SystemExit(f'--eval-cap is the registered {EVAL_CAP}; 19b refuses to produce a '
                         f'score file at another cap (the frozen caps check would reject it)')
    kind, namespace, panel_manifest = TR.panel_kind(args.panels)
    # ALLOW-LIST, not a block-list: exactly 19b's own development namespace scores here.
    if kind == 'confirmation' or namespace == module.NS_CONFIRM:
        raise SystemExit(f'{args.panels} is a CONFIRMATION suite.  Experiment 19b builds and '
                         f'scores no confirmation; see confirmation_marks() for the scaled '
                         f'marks that apply only after development passes and is sealed.')
    if (kind, namespace, panel_manifest.get('experiment')) != ('development', module.NS_DEV, '19b'):
        raise SystemExit(f'{args.panels} is kind={kind!r} namespace={namespace!r} '
                         f'experiment={panel_manifest.get("experiment")!r}; 19b scores only its '
                         f'own fresh development suite '
                         f'(development/{module.NS_DEV}/19b).  Experiment 19\'s panels are not '
                         f'fresh for 19b and its cells are not these 38.')

    saved, model, flags = TR.load_run_checkpoint(args.ckpt, ARCH)
    phase, arm = saved.get('phase'), saved.get('arm')
    if phase == 'offline' and arm not in ARMS:
        raise SystemExit(f'{args.ckpt} is an offline checkpoint of arm {arm!r}; 19b scores only '
                         f'its own arms {list(ARMS)} and the awake anchors')
    manifest, panels, _forbidden = module.load_dev_panels(args.panels)
    expected_n = int(manifest['n'])
    order = [c for c in cell_order(module) if c in panels]
    if args.cells:
        wanted = [c for c in args.cells.split(',') if c]
        unknown = [c for c in wanted if c not in panels]
        if unknown:
            raise SystemExit(f'unknown cell(s): {unknown}')
        order = [c for c in order if c in wanted]

    operator = TR.verified_operator(args.operator)
    if operator.fingerprint != saved.get('operator_fingerprint', operator.fingerprint):
        raise SystemExit('this checkpoint was trained with a different frozen operator')
    oracle = None if args.no_oracle else V1.OracleOperator()
    operators = dict(trained_operator=operator)
    if oracle is not None:
        operators['oracle_operator'] = oracle
    tables = V3.TableCache(operators)
    operator_before = operator.fingerprint

    began = time.monotonic()
    specs = cell_specs(module)
    cells, per_unit, transcripts = {}, {}, {}
    with registered_cells(module):
        for cell in order:
            cfg = dict(specs[cell], name=cell)
            # the data module's own accessor, which refuses a prefix or subset: the answer
            # of unit i is a function of i, so a partial cell is a biased sub-cell and not
            # a smaller version of the same measurement
            units = module.whole_cell(panels[cell])
            row, native = TR.score_dispatcher_cell(model, flags, operator, oracle, units, cfg,
                                                   args.eval_cap, tables)
            row.update(cell=cell, family=family_of(cell), n=len(units),
                       sides=1 + int(cfg['kind'] == 'pair'), hops=cfg['hops'],
                       people=cfg['people'], terminal=cfg['terminal'],
                       fixed_terminal=cfg['fixed_terminal'], kind=cfg['kind'],
                       invariant=cfg['invariant'], title=cfg.get('title'))
            cells[cell] = row
            per_unit[cell] = unit_flags(native, units)
            transcripts[cell] = native
            print(json.dumps(dict(cell=cell, hops=cfg['hops'], answers=row['answers'],
                                  strict=row['strict'],
                                  mean_calls=round(row['mean_calls'], 3),
                                  over_cap=row['over_cap'])), flush=True)
    if operator.fingerprint != operator_before:
        raise RuntimeError('the frozen operator changed during scoring')

    out = Path(args.out)
    report_payload = dict(
        kind='novelty19b-score', experiment='novelty19b', arch=ARCH,
        seed=int(saved['seed']), phase=phase, arm=arm,
        updates_done=saved.get('updates_done'), total_updates=saved.get('total_updates'),
        checkpoint=str(Path(args.ckpt).resolve()), checkpoint_sha256=sha(Path(args.ckpt)),
        checkpoint_verified_before_load=saved.get('_verified_on_disk'),
        final_weight_fingerprint=saved.get('final_weight_fingerprint'),
        data_fingerprint=saved.get('data_fingerprint'),
        update_fingerprint=saved.get('update_fingerprint'),
        panels=str(Path(args.panels).resolve()),
        panel_manifest_sha256=sha(Path(args.panels) / 'manifest.json'),
        panel_kind=kind, panel_namespace=namespace,
        panel_experiment=panel_manifest.get('experiment'),
        panel_guard=dict(is_confirmation=False, allow_listed=True,
                         note='19b scores development panels only, and only its own: the '
                              'suite must be kind=development, namespace=' + module.NS_DEV
                              + ', experiment=19b, checked before a unit is loaded'),
        layout_agreement=layout,
        n_per_cell=expected_n, cell_order=order, cells_scored=len(order),
        cells=cells, unit_flags=per_unit,
        eval_cap=args.eval_cap, train_cap=TRAIN_CAP,
        registered_eval_cap=EVAL_CAP, registered_caps=bool(args.eval_cap == EVAL_CAP),
        run_dir=str(Path(args.ckpt).resolve().parent),
        expected_updates=TR.AWAKE_UPDATES if phase == 'awake' else OFFLINE_UPDATES,
        is_final_checkpoint=bool(saved.get('updates_done') is not None
                                 and saved.get('updates_done') == saved.get('total_updates')),
        oracle_operator_diagnostic=bool(oracle is not None),
        operator=operator.describe(),
        scoring=('D: greedy (argmax) native episodes at evaluation cap %d; strict = correct '
                 'subject, operation and returned token at every call, in order, with STOP '
                 'immediately after the requested terminal lookup' % args.eval_cap),
        marks=dict(bounded=BOUNDED_MARK, gain=GAIN_MARK, guard=GUARD_MARK,
                   retention_f=RETENTION_F_MARK, retention_h=RETENTION_H_MARK,
                   h_loss_limit=H_LOSS_LIMIT),
        scoring_seconds=time.monotonic() - began, peak_rss_bytes=TR.peak_rss_bytes(),
        host=TR.host_profile(), source_fingerprint=source_fingerprint(),
        argv=list(sys.argv), created_unix=time.time())
    out.parent.mkdir(parents=True, exist_ok=True)
    write_new(out, report_payload)
    if args.transcripts:
        Path(args.transcripts).parent.mkdir(parents=True, exist_ok=True)
        write_new(Path(args.transcripts), transcripts)
    print(json.dumps(dict(event='scored', arch=ARCH, seed=report_payload['seed'], phase=phase,
                          arm=arm, cells=len(order),
                          seconds=round(report_payload['scoring_seconds'], 1),
                          out=str(out.resolve()))), flush=True)
    return report_payload


def source_fingerprint():
    """The frozen trainer's fingerprint plus THIS module and the 19b data module."""
    out = dict(TR.source_fingerprint())
    out['novelty19b_train'] = sha(__file__)
    if _DATA_OVERRIDE is None:
        try:
            module = importlib.import_module(DATA_MODULE_NAME)
            out['novelty19b_data'] = sha(module.__file__)
        except ImportError:
            out['novelty19b_data'] = None
    else:
        out['novelty19b_data'] = sha(getattr(_DATA_OVERRIDE, '__file__', __file__))
    return out


# =========================================================================== collection


def run_key(seed, phase, arm):
    return f'{phase}-D-s{int(seed)}' + (f'-{arm}' if arm else '')


def endpoints(seeds=SEEDS):
    """Every endpoint 19b must have: three awake anchors plus six continuations."""
    out = [run_key(s, 'awake', None) for s in seeds]
    out += [run_key(s, 'offline', a) for s in seeds for a in ARMS]
    return tuple(out)


def collect_scores(exp, *, seeds=SEEDS):
    """Merge the score files, binding each to its run exactly as the frozen report does."""
    folder = Path(exp) / 'scores'
    runs, files, conflicts, rejected, rejected_runs = {}, [], [], [], []
    for path in sorted(folder.glob('*.json')) if folder.is_dir() else []:
        try:
            payload = json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            rejected.append(dict(path=str(path), reason=f'does not parse: {exc}'))
            continue
        if payload.get('kind') != 'novelty19b-score':
            rejected.append(dict(path=str(path), reason=f'kind {payload.get("kind")!r}'))
            continue
        if int(payload.get('seed', -1)) not in [int(s) for s in seeds]:
            rejected.append(dict(path=str(path), reason=f'seed {payload.get("seed")} not asked for'))
            continue
        if not payload.get('registered_caps'):
            rejected.append(dict(path=str(path),
                                 reason=f'eval cap {payload.get("eval_cap")} is not the '
                                        f'registered {EVAL_CAP}'))
            continue
        key = run_key(payload['seed'], payload.get('phase'), payload.get('arm'))
        problems = TR.checkpoint_binding(payload)
        if problems:
            rejected.append(dict(path=str(path), run=key, reason=WRONG_CKPT, problems=problems))
            rejected_runs.append(key)
            continue
        entry = runs.setdefault(key, dict(
            run=key, seed=int(payload['seed']), phase=payload.get('phase'),
            arm=payload.get('arm'), cells={}, unit_flags={},
            checkpoint=payload.get('checkpoint'),
            checkpoint_sha256=payload.get('checkpoint_sha256'),
            panels=payload.get('panels'),
            panel_manifest_sha256=payload.get('panel_manifest_sha256'),
            source_fingerprint=payload.get('source_fingerprint'),
            n_per_cell=payload.get('n_per_cell'), files=[]))
        if entry['panel_manifest_sha256'] != payload.get('panel_manifest_sha256'):
            conflicts.append(dict(run=key, path=str(path), reason='two panel suites for one run'))
            continue
        if entry['source_fingerprint'] != payload.get('source_fingerprint'):
            conflicts.append(dict(run=key, path=str(path), reason='two script versions for one run'))
            continue
        if entry['checkpoint_sha256'] != payload.get('checkpoint_sha256'):
            conflicts.append(dict(run=key, path=str(path), reason='two checkpoints for one run'))
            continue
        overlap = sorted(set(entry['cells']) & set(payload.get('cells', {})))
        if overlap:
            conflicts.append(dict(run=key, path=str(path),
                                  reason=f'cells scored twice: {overlap[:6]}'))
            continue
        entry['cells'].update(payload.get('cells', {}))
        entry['unit_flags'].update(payload.get('unit_flags', {}))
        entry['files'].append(str(path))
        files.append(str(path))
    required = endpoints(seeds)
    missing = [k for k in required if k not in runs]
    return dict(runs=runs, files=files, conflicts=conflicts, rejected=rejected,
                rejected_runs=sorted(set(rejected_runs)), missing=missing, required=list(required))


def complete_runs(collected, wanted_cells):
    """Runs that scored every cell of the group under test."""
    incomplete = {}
    for key, entry in collected['runs'].items():
        absent = [c for c in wanted_cells if c not in entry['cells']]
        if absent:
            incomplete[key] = absent
    return incomplete


def trainer_version(collected):
    """The frozen single-version check, over 19b's own run entries."""
    return TR.trainer_version(collected, seeds=SEEDS)


# =========================================================================== conditions


def _counts(entry, cell):
    row = (entry or {}).get('cells', {}).get(cell)
    if row is None:
        return None
    return dict(answers=int(row['answers']), strict=int(row['strict']), n=int(row['n']),
                mean_calls=row.get('mean_calls'), over_cap=row.get('over_cap'),
                failure_shapes=row.get('failure_shapes'),
                oracle_operator=row.get('oracle_operator'))


def condition_bounded(entry, cells, mark=BOUNDED_MARK):
    """1: >= mark answers AND strict in every cell of the bounded group."""
    per_cell = {}
    for cell in cells:
        got = _counts(entry, cell)
        per_cell[cell] = dict(need=mark, present=got is not None,
                              answers=None if got is None else got['answers'],
                              strict=None if got is None else got['strict'],
                              passed=(None if got is None
                                      else bool(got['answers'] >= mark and got['strict'] >= mark)))
    return _fold(per_cell, 'section 1: >= %d/64 answers AND strict in every N/P cell at c=4/5 '
                           'and all nine c=6..8 cells' % mark)


def condition_contrast(treatment, control, cells, mark=GAIN_MARK):
    """2: U8 strict exceeds U5 by >= mark ON IDENTICAL UNITS, with paired wins and losses."""
    per_cell = {}
    for cell in cells:
        t_flags = (treatment or {}).get('unit_flags', {}).get(cell)
        c_flags = (control or {}).get('unit_flags', {}).get(cell)
        row = dict(need=mark, present=bool(t_flags and c_flags))
        if not row['present']:
            row.update(passed=None, difference=None, wins=None, losses=None,
                       reason='one arm has not been scored on this cell')
            per_cell[cell] = row
            continue
        paired = paired_strict(t_flags, c_flags)
        row.update(paired)
        row['passed'] = (None if paired['difference'] is None
                         else bool(paired['difference'] >= mark))
        per_cell[cell] = row
    return _fold(per_cell, 'section 2: U8 strict exceeds U5 by >= %d/64 on IDENTICAL units in '
                           'each of the three c=6/7/8 r10 p16 cells' % mark)


def paired_strict(treatment_flags, control_flags):
    """Wins, losses, ties and the difference, matched unit by unit."""
    t_index = list(treatment_flags['unit_index'])
    c_index = list(control_flags['unit_index'])
    if t_index != c_index:
        return dict(difference=None, wins=None, losses=None, ties=None,
                    units=None, reason='the two arms were scored on different units')
    t = list(treatment_flags['strict'])
    c = list(control_flags['strict'])
    wins = sum(1 for a, b in zip(t, c) if a and not b)
    losses = sum(1 for a, b in zip(t, c) if b and not a)
    return dict(difference=sum(t) - sum(c), treatment_strict=sum(t), control_strict=sum(c),
                wins=wins, losses=losses, ties=len(t) - wins - losses, units=len(t),
                reason=None)


def condition_guards(entry, cells, mark=GUARD_MARK):
    """3: >= mark strict PAIR units in each c=5 and c=8 E cell; both branches must succeed."""
    per_cell = {}
    for cell in cells:
        got = _counts(entry, cell)
        per_cell[cell] = dict(need=mark, present=got is not None,
                              strict_pair_units=None if got is None else got['strict'],
                              passed=None if got is None else bool(got['strict'] >= mark),
                              note='a pair unit counts only when BOTH twins are strict, which '
                                   'is how V3.aggregate already scores an invariant cell')
    return _fold(per_cell, 'section 3: >= %d/64 strict pair units in each c=5 and c=8 E cell'
                           % mark)


def condition_retention(entry, anchor, f_cells, h_cells):
    """4: F cells at >= 61 both metrics; H cells at >= 58 both AND no loss >= 7 vs awake."""
    per_cell = {}
    for cell in f_cells:
        got = _counts(entry, cell)
        per_cell[cell] = dict(need=RETENTION_F_MARK, present=got is not None,
                              answers=None if got is None else got['answers'],
                              strict=None if got is None else got['strict'],
                              passed=(None if got is None else
                                      bool(got['answers'] >= RETENTION_F_MARK
                                           and got['strict'] >= RETENTION_F_MARK)))
    for cell in h_cells:
        got = _counts(entry, cell)
        base = _counts(anchor, cell)
        row = dict(need=RETENTION_H_MARK, loss_limit=H_LOSS_LIMIT,
                   present=got is not None, anchor_present=base is not None,
                   answers=None if got is None else got['answers'],
                   strict=None if got is None else got['strict'],
                   anchor_answers=None if base is None else base['answers'],
                   anchor_strict=None if base is None else base['strict'])
        if got is None or base is None:
            row.update(passed=None, answers_loss=None, strict_loss=None)
        else:
            row['answers_loss'] = base['answers'] - got['answers']
            row['strict_loss'] = base['strict'] - got['strict']
            row['passed'] = bool(got['answers'] >= RETENTION_H_MARK
                                 and got['strict'] >= RETENTION_H_MARK
                                 and row['answers_loss'] < H_LOSS_LIMIT
                                 and row['strict_loss'] < H_LOSS_LIMIT)
        per_cell[cell] = row
    return _fold(per_cell, 'section 4: >= %d/64 answers AND strict in all seven F cells; '
                           '>= %d/64 both metrics in all four H cells with no H-cell loss '
                           '>= %d/64 from that seed\'s awake anchor on the same units'
                           % (RETENTION_F_MARK, RETENTION_H_MARK, H_LOSS_LIMIT))


def _fold(per_cell, required):
    verdicts = [row['passed'] for row in per_cell.values()]
    passed = (None if not verdicts else
              (False if any(v is False for v in verdicts)
               else (None if any(v is None for v in verdicts) else True)))
    return dict(required=required, cells=per_cell, passed=passed,
                failed_cells=[c for c, r in per_cell.items() if r['passed'] is False],
                absent_cells=[c for c, r in per_cell.items() if r['passed'] is None])


def condition_provenance(collected, exp, *, seeds=SEEDS, module=None):
    """5: complete provenance, zero composite-r10 training exposure, every endpoint, one
    frozen script version."""
    version = trainer_version(collected)
    orders = {int(s): shared_order(exp, s) for s in seeds}
    exposure = composite_exposure(exp, seeds=seeds, module=module)
    parts = dict(
        every_endpoint=dict(
            required='three awake anchors plus six continuations, all scored',
            missing=collected['missing'],
            # an endpoint that was never scored is UNDETERMINED, not failed: nothing has
            # been observed about it.  None never unlocks anything, so this is the honest
            # reading and not a weaker one.
            passed=(True if not collected['missing'] else None)),
        one_panel_suite=dict(
            required='every merged run scored on ONE panel suite at the registered cap',
            suites=sorted({e['panel_manifest_sha256'] for e in collected['runs'].values()
                           if e['panel_manifest_sha256']}),
            passed=bool(len({e['panel_manifest_sha256'] for e in collected['runs'].values()}) <= 1)
            if collected['runs'] else None),
        one_script_version=dict(
            required='every merged run produced by ONE frozen script version',
            distinct=version['distinct'], offending_runs=version['offending_runs'],
            runs_without_a_fingerprint=version['runs_without_a_fingerprint'],
            differing_fields=version['differing_fields'], passed=version['passed']),
        shared_world_order=dict(
            required='U5 and U8 follow the SAME world-index order in every seed',
            per_seed=orders,
            passed=(False if any(v['passed'] is False for v in orders.values())
                    else (None if any(v['passed'] is None for v in orders.values()) else True))),
        zero_composite_r10_exposure=exposure,
        no_conflicts=dict(required='no conflicting and no rejected score files',
                          conflicts=len(collected['conflicts']),
                          rejected=len(collected['rejected']),
                          rejected_runs=collected['rejected_runs'],
                          passed=bool(not collected['conflicts'] and not collected['rejected'])))
    verdicts = [p['passed'] for p in parts.values()]
    passed = (False if any(v is False for v in verdicts)
              else (None if any(v is None for v in verdicts) else True))
    return dict(required='section 5: complete provenance, zero composite-r10 training exposure, '
                         'every required endpoint present, one frozen script version',
                parts=parts, passed=passed)


def composite_exposure(exp, *, seeds=SEEDS, module=None):
    """Astra: "Keep composite r10 excluded globally."  Read from the buffers' own audit."""
    per_seed = {}
    for seed in seeds:
        for arm in ARMS:
            key = f's{int(seed)}-{arm}'
            try:
                folder = resolve_buffers(exp, seed, arm)
            except SystemExit:
                per_seed[key] = dict(present=False, zero_exposure=None)
                continue
            audit = folder / 'audit.json'
            if not audit.is_file():
                per_seed[key] = dict(present=False, zero_exposure=None)
                continue
            row = json.loads(audit.read_text()).get('composite_r10_exposure')
            per_seed[key] = dict(present=True, zero_exposure=None if row is None
                                 else bool(row.get('zero_exposure')), detail=row)
    values = [v['zero_exposure'] for v in per_seed.values()]
    return dict(required='zero composite-r10 exposure in every training buffer',
                per_buffer=per_seed,
                passed=(None if not values or any(v is None for v in values)
                        else all(values)))


def seed_verdict(collected, exp, seed, group_names, *, module=None):
    """Astra's four per-seed conditions for ONE seed, in U8, with U5 as the control."""
    runs = collected['runs']
    treatment = runs.get(run_key(seed, 'offline', TREATMENT_ARM))
    control = runs.get(run_key(seed, 'offline', CONTROL_ARM))
    anchor = runs.get(run_key(seed, 'awake', None))
    parts = dict(
        bounded_competence=condition_bounded(treatment, group_names['bounded']),
        treatment_effect=condition_contrast(treatment, control, group_names['contrast']),
        guards=condition_guards(treatment, group_names['guards']),
        retention=condition_retention(treatment, anchor, group_names['retention_f'],
                                      group_names['retention_h']))
    verdicts = [p['passed'] for p in parts.values()]
    passed = (False if any(v is False for v in verdicts)
              else (None if any(v is None for v in verdicts) else True))
    # the control arm's own bounded competence, for Astra's interpretive case
    control_bounded = condition_bounded(control, group_names['bounded'])
    return dict(seed=int(seed), arm=TREATMENT_ARM, control_arm=CONTROL_ARM, parts=parts,
                passed=passed, control_bounded_competence=control_bounded,
                treatment_present=treatment is not None, control_present=control is not None,
                anchor_present=anchor is not None)


def split_long_cells(group_names, module=None):
    """The nine long cells, split into PRACTISED and HELD-OUT endings.

    U8 practises r=8/9 at c>=2 (and r=8/9/10 at c=1), with composite r10 excluded
    globally, so among the nine c=6/7/8 x r=8/9/10 x p16 cells the r=10 ones are the
    held-out ending and the r=8/9 ones are practised.  This is read from the cells'
    `fixed_terminal`, not from their names.
    """
    cells = cell_specs(module)
    long_cells = group_names['long']
    practised = tuple(c for c in long_cells if cells[c]['fixed_terminal'] in (8, 9))
    held_out = tuple(c for c in long_cells if cells[c]['fixed_terminal'] == 10)
    return practised, held_out


def interpretive_cases(per_seed, group_names, module=None):
    """Astra's three readings, printed whatever the verdict says."""
    def every(test):
        values = [test(v) for v in per_seed.values()]
        return (None if any(v is None for v in values)
                else (all(values) if values else None))
    competent = every(lambda v: v['parts']['bounded_competence']['passed'])
    gain = every(lambda v: v['parts']['treatment_effect']['passed'])
    control_competent = every(lambda v: v['control_bounded_competence']['passed'])

    practised_cells, held_cells = split_long_cells(group_names, module)

    def ending_split(verdict):
        rows = verdict['parts']['bounded_competence']['cells']
        practised = [rows[c]['passed'] for c in practised_cells if c in rows]
        held = [rows[c]['passed'] for c in held_cells if c in rows]
        if (not practised or not held or any(v is None for v in practised)
                or any(v is None for v in held)):
            return None
        return bool(all(practised) and not any(held))

    practised_only = every(ending_split)
    return dict(
        u5_also_competent=dict(
            holds=bool(control_competent and gain is False),
            says='both recipes may be competent, but a benefit of widening the practice mix '
                 'is UNESTABLISHED; that is not evidence that widening does not help',
            control_bounded_competence=control_competent, gain_mark_met=gain),
        only_practised_endings_succeed=dict(
            holds=practised_only,
            says='if the practised-ending long cells pass and the held-out-ending (r10) ones '
                 'do not, the continuation problem has improved while held-out-ending '
                 'transfer has FAILED',
            practised_ending_cells=list(practised_cells),
            held_out_ending_cells=list(held_cells)),
        extra_calls_are_not_a_pass=dict(
            holds=True,
            says='a higher mean call count is not a result.  strict requires the complete '
                 'correct call sequence and native STOP immediately after the terminal '
                 'lookup, and a cap hit is a failure even when the last token happens to '
                 'equal the answer'),
        bounded_competence_all_seeds=competent, treatment_effect_all_seeds=gain)


# =========================================================================== gates / report


def development_rule(collected, exp, *, seeds=SEEDS, module=None):
    """Astra: every condition, separately in EACH of the three seeds.  No averaging."""
    group_names = groups(module)
    sizes = {k: len(v) for k, v in group_names.items()}
    expected = expected_group_sizes()
    shape = {k: dict(found=sizes.get(k), expected=expected[k],
                     passed=bool(sizes.get(k) == expected[k])) for k in expected}
    per_seed = {int(s): seed_verdict(collected, exp, s, group_names, module=module)
                for s in seeds}
    provenance = condition_provenance(collected, exp, seeds=seeds, module=module)
    verdicts = [v['passed'] for v in per_seed.values()] + [provenance['passed']]
    if not all(row['passed'] for row in shape.values()):
        passed = None
    elif any(v is False for v in verdicts):
        passed = False
    elif any(v is None for v in verdicts):
        passed = None
    else:
        passed = True
    return dict(experiment='novelty19b', architecture=ARCH, arm=TREATMENT_ARM,
                control_arm=CONTROL_ARM, seeds=[int(s) for s in seeds],
                cell_groups={k: list(v) for k, v in group_names.items()},
                cell_group_shape=shape, per_seed=per_seed, provenance=provenance,
                interpretive_cases=interpretive_cases(per_seed, group_names, module),
                passed=passed,
                note='an all-seed development pass requires every condition in U8 separately '
                     'in each of the three seeds; no averaging rescues a failing cell or seed')


def _state(value):
    return MISSING if value is None else ('PASS' if value else 'FAIL')


def print_condition(name, part, out):
    out(f'    {name:<22} {_state(part["passed"]):<9} {part["required"]}')
    if part.get('failed_cells'):
        out(f'        failed: {part["failed_cells"]}')
    if part.get('absent_cells'):
        out(f'        absent: {part["absent_cells"]}')


def print_cell_table(entry, cells, out, *, anchor=None, control=None):
    header = f'    {"cell":<20}{"ans":>6}{"str":>6}{"calls":>8}{"ovc":>6}'
    if control is not None:
        header += f'{"U5 str":>8}{"diff":>7}{"win":>5}{"loss":>6}'
    if anchor is not None:
        header += f'{"vs awake":>10}'
    out(header)
    for cell in cells:
        got = _counts(entry, cell)
        if got is None:
            out(f'    {cell:<20}{MISSING:>26}')
            continue
        line = (f'    {cell:<20}{got["answers"]:>6}{got["strict"]:>6}'
                f'{got["mean_calls"]:>8.2f}{got["over_cap"]:>6}')
        if control is not None:
            t_flags = (entry or {}).get('unit_flags', {}).get(cell)
            c_flags = (control or {}).get('unit_flags', {}).get(cell)
            if t_flags and c_flags:
                paired = paired_strict(t_flags, c_flags)
                if paired['difference'] is None:
                    line += f'{MISSING:>26}'
                else:
                    line += (f'{paired["control_strict"]:>8}{TR.signed(paired["difference"]):>7}'
                             f'{paired["wins"]:>5}{paired["losses"]:>6}')
            else:
                line += f'{MISSING:>26}'
        if anchor is not None:
            base = _counts(anchor, cell)
            line += (f'{MISSING:>10}' if base is None
                     else f'{TR.signed(got["strict"] - base["strict"]):>10}')
        out(line)


def print_failure_shapes(entry, cells, out):
    out('    failure shapes (calls histogram / first wrong call / stopped early|late / '
        'oracle-operator errors on the true chain)')
    for cell in cells:
        got = _counts(entry, cell)
        if got is None or not got.get('failure_shapes'):
            out(f'        {cell:<20}{MISSING}')
            continue
        shapes = got['failure_shapes']
        oracle = got.get('oracle_operator') or {}
        out(f'        {cell:<20}calls={_compact(shapes["calls_histogram"])}  '
            f'first_wrong={_compact(shapes["first_wrong_call"])}  '
            f'early={shapes["stopped_early"]} late={shapes["stopped_late"]}  '
            f'over_cap={shapes["over_cap"]} invalid={shapes["invalid_action"]}  '
            f'op_wrong={shapes["frozen_operator_wrong_on_true_chain"]}  '
            f'oracle_strict={oracle.get("strict", MISSING)}')


def _compact(counter):
    return '{' + ','.join(f'{k}:{v}' for k, v in sorted(counter.items(),
                                                        key=lambda kv: str(kv[0]))) + '}'


def gates(args):
    """The prerequisites, as a machine-readable verdict.  Refuses a mixed script version."""
    collected = collect_scores(args.exp, seeds=args.seed_list)
    module = data_module()
    layout = check_layout_agrees(module)
    group_names = groups(module)
    verdict = dict(
        kind='novelty19b-gates', experiment='novelty19b', exp=str(Path(args.exp).resolve()),
        seeds=[int(s) for s in args.seed_list], arms=list(ARMS),
        endpoints_required=list(endpoints(args.seed_list)),
        endpoints_missing=collected['missing'],
        cell_group_sizes={k: len(v) for k, v in group_names.items()},
        expected_cell_group_sizes=expected_group_sizes(),
        incomplete_runs=complete_runs(collected, group_names['all']),
        conflicts=collected['conflicts'], rejected=collected['rejected'],
        single_trainer_version=trainer_version(collected),
        shared_world_order={int(s): shared_order(args.exp, s) for s in args.seed_list},
        composite_r10_exposure=composite_exposure(args.exp, seeds=args.seed_list, module=module),
        layout_agreement=layout,
        source_fingerprint=source_fingerprint(), argv=list(sys.argv), created_unix=time.time())
    print(json.dumps({k: v for k, v in verdict.items()
                      if k not in ('argv', 'source_fingerprint')}, indent=2), flush=True)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        write_new(Path(args.out), verdict)
    version = verdict['single_trainer_version']
    if version['passed'] is False:
        raise SystemExit(
            f'the merged runs were not produced by one frozen script version '
            f'({version["distinct"]} distinct, differing in {version["differing_fields"]}; '
            f'{len(version["runs_without_a_fingerprint"])} without a fingerprint).  '
            f'Offending runs: {version["offending_runs"]}')
    return verdict


def report(args):
    exp = Path(args.exp)
    seeds = [int(s) for s in args.seed_list]
    module = data_module()
    layout = check_layout_agrees(module)
    collected = collect_scores(exp, seeds=seeds)
    group_names = groups(module)
    lines = []

    def out(text=''):
        lines.append(text)
        print(text, flush=True)

    out('=' * 96)
    out(f'experiment 19b -- U8 versus U5, D only, {OFFLINE_UPDATES} offline updates from the '
        f'experiment-19 awake finals')
    out(f'{exp}')
    out(f'seeds {seeds}   arms {list(ARMS)}   train cap {TRAIN_CAP}   eval cap {EVAL_CAP}   '
        f'{UNITS_PER_CELL} units/cell')
    sizes = {k: len(v) for k, v in group_names.items() if k != 'all'}
    out(f'cells: {len(group_names["all"])} ({sizes})')

    rule = development_rule(collected, exp, seeds=seeds, module=module)
    for name, row in rule['cell_group_shape'].items():
        if not row['passed']:
            out(f'    CELL-GROUP SHAPE {name}: found {row["found"]}, Astra specifies '
                f'{row["expected"]} -- the conditions below cannot be read as registered')

    for seed in seeds:
        treatment = collected['runs'].get(run_key(seed, 'offline', TREATMENT_ARM))
        control = collected['runs'].get(run_key(seed, 'offline', CONTROL_ARM))
        anchor = collected['runs'].get(run_key(seed, 'awake', None))
        out('\n' + '=' * 96)
        out(f'seed {seed}: bounded competence ({TREATMENT_ARM}), mark {BOUNDED_MARK}/64 '
            f'answers AND strict')
        print_cell_table(treatment, group_names['bounded'], out)
        out('')
        out(f'seed {seed}: the treatment contrast, reported SEPARATELY -- '
            f'{TREATMENT_ARM} strict minus {CONTROL_ARM} strict on identical units, '
            f'mark +{GAIN_MARK}/64')
        # `or {}`, never None: an absent arm must print "(missing)" in its column rather
        # than silently removing the column and leaving a table that looks complete.
        print_cell_table(treatment, group_names['contrast'], out, control=control or {})
        out('')
        out(f'seed {seed}: guards (strict pair units, mark {GUARD_MARK}/64)')
        print_cell_table(treatment, group_names['guards'], out)
        out('')
        out(f'seed {seed}: retention -- F at {RETENTION_F_MARK}/64, H at '
            f'{RETENTION_H_MARK}/64 with no loss >= {H_LOSS_LIMIT}/64 from the awake anchor')
        print_cell_table(treatment, list(group_names['retention_f'])
                         + list(group_names['retention_h']), out, anchor=anchor or {})
        out('')
        print_failure_shapes(treatment, group_names['bounded'], out)

    out('\n' + '=' * 96)
    out('Astra\'s five conditions, separately in each seed (no averaging)')
    for seed in seeds:
        verdict = rule['per_seed'][int(seed)]
        out(f'  seed {seed}: {_state(verdict["passed"])}')
        for name, part in verdict['parts'].items():
            print_condition(name, part, out)
        # NOT printed as PASS/FAIL: Astra reports U5's own competence, and it is never a
        # condition U8 has to meet.  A verdict word here would read as a failing gate.
        control_competent = verdict['control_bounded_competence']['passed']
        out(f'    {"(U5 also competent?)":<22} '
            f'{ {True: "yes", False: "no", None: MISSING}[control_competent]:<9} '
            f'reported for interpretation only; never a pass condition')
    out(f'  provenance: {_state(rule["provenance"]["passed"])}')
    for name, part in rule['provenance']['parts'].items():
        out(f'    {name:<28} {_state(part["passed"]):<9} {part["required"]}')

    out('\n' + '=' * 96)
    out('interpretive cases (Astra)')
    for name, case in rule['interpretive_cases'].items():
        if isinstance(case, dict) and 'says' in case:
            out(f'    {name}: holds={case["holds"]}')
            out(f'        {case["says"]}')

    out('\n' + '=' * 96)
    out(f'registered development rule (19b, {ARCH}-{TREATMENT_ARM}): '
        f'{_state(rule["passed"])}')

    payload = dict(
        kind='novelty19b-report', experiment='novelty19b', exp=str(exp.resolve()),
        seeds=seeds, arms=list(ARMS), units_per_cell=UNITS_PER_CELL,
        marks=dict(bounded=BOUNDED_MARK, gain=GAIN_MARK, guard=GUARD_MARK,
                   retention_f=RETENTION_F_MARK, retention_h=RETENTION_H_MARK,
                   h_loss_limit=H_LOSS_LIMIT),
        confirmation_marks=confirmation_marks(),
        development_rule=rule, single_trainer_version=trainer_version(collected),
        runs={k: {kk: vv for kk, vv in v.items() if kk not in ('cells', 'unit_flags')}
              for k, v in collected['runs'].items()},
        cells_by_run={k: v['cells'] for k, v in collected['runs'].items()},
        unit_flags_by_run={k: v['unit_flags'] for k, v in collected['runs'].items()},
        missing_runs=collected['missing'], rejected_score_files=collected['rejected'],
        rejected_runs=collected['rejected_runs'], conflicts=collected['conflicts'],
        score_files=collected['files'], text='\n'.join(lines), layout_agreement=layout,
        source_fingerprint=source_fingerprint(), host=TR.host_profile(),
        argv=list(sys.argv), created_unix=time.time())
    target = Path(args.out) if args.out else exp / 'report.json'
    if target.exists() and args.overwrite:
        stamp = time.strftime('%Y%m%dT%H%M%S', time.gmtime())
        target = target.with_name(f'{target.stem}-{stamp}{target.suffix}')
    target.parent.mkdir(parents=True, exist_ok=True)
    write_new(target, payload)
    out(f'\nwrote {target}')

    flag = exp / 'DEV-PASSED.json'
    payload['dev_passed'], payload['dev_passed_problems'] = None, []
    if rule['passed'] is True:
        unlock, problems = dev_passed_payload(exp, collected, rule, target, seeds=seeds,
                                              module=module)
        payload['dev_passed_problems'] = list(problems)
        if flag.exists():
            out(f'{flag} already exists; leaving it untouched')
        elif problems:
            out(f'NOT writing {flag}: the rule passed on the seeds given, but the unlock '
                f'record cannot be issued')
            for problem in problems:
                out(f'        {problem}')
        else:
            write_new(flag, unlock)
            # the file is only a pass if the lockout it exists for accepts it
            try:
                record = module.validate_dev_passed(exp, seeds=tuple(int(s) for s in seeds))
            except SystemExit as exc:
                flag.unlink()
                raise SystemExit(f'the 19b development rule passed, but the unlock record '
                                 f'this module wrote was REJECTED by '
                                 f'{DATA_MODULE_NAME}.validate_dev_passed: {exc}.  The file '
                                 f'has been removed; the report stands at {target}.') from None
            out(f'wrote {flag} (sha {record["sha256"]}, accepted by '
                f'{DATA_MODULE_NAME}.validate_dev_passed)')
            payload['dev_passed'] = str(flag)
            payload['dev_passed_record'] = record
    else:
        out(f'not writing {flag}: the 19b development rule is '
            f'{"undetermined" if rule["passed"] is None else "not met"}')

    version = payload['single_trainer_version']
    if version['passed'] is False:
        raise SystemExit(f'the merged runs were not produced by one frozen script version '
                         f'({version["distinct"]} distinct).  Offending runs: '
                         f'{version["offending_runs"]}.  The report was still written to {target}')
    return payload


def dev_passed_payload(exp, collected, rule, report_path, *, seeds=SEEDS, module=None):
    """The 19b unlock record, in the ONE shape the data module's validator accepts.

    Every field here is required by `fable_novelty19b_data.validate_dev_passed`, which is
    the lockout the confirmation build runs through: the schema string, the seed list, the
    report hash, the dev-panel manifest hash, and the checkpoint rosters under exactly the
    keys `checkpoint_keys()` names (`D-<seed>` awake, `D-<arm>-<seed>` offline).  The
    record is written and then FED BACK THROUGH that validator, so a file this module
    cannot itself unlock is never left on disk claiming to be a pass.

    The panel binding is must-fix M-1 in the other direction: the suite records the hash
    of the verdict that unlocked it, and the verdict records the hash of the suite it was
    earned on, so neither can be swapped for a different-but-valid one.
    """
    module = module or data_module()
    problems = []
    given = tuple(int(s) for s in seeds)
    if given != tuple(int(s) for s in SEEDS):
        problems.append(f'the seed set is {list(given)}; the 19b development rule is over '
                        f'exactly {list(map(int, SEEDS))}')
    suites = sorted({e['panel_manifest_sha256'] for e in collected['runs'].values()
                     if e['panel_manifest_sha256']})
    if len(suites) != 1:
        problems.append(f'{len(suites)} panel suites among the merged runs; the unlock must '
                        f'name exactly one')
    panel_paths = sorted({e['panels'] for e in collected['runs'].values() if e.get('panels')})
    if len(panel_paths) != 1:
        problems.append(f'{len(panel_paths)} panel folders among the merged runs')

    by_key = {}
    for key, entry in collected['runs'].items():
        if entry['phase'] == 'awake':
            by_key[f'{ARCH}-{entry["seed"]}'] = entry['checkpoint_sha256']
        else:
            by_key[f'{ARCH}-{entry["arm"]}-{entry["seed"]}'] = entry['checkpoint_sha256']
    awake_keys = module.checkpoint_keys('awake', tuple(int(s) for s in seeds))
    offline_keys = module.checkpoint_keys('offline', tuple(int(s) for s in seeds))
    for key in tuple(awake_keys) + tuple(offline_keys):
        if not TR.HEX64.match(str(by_key.get(key))):
            problems.append(f'no valid checkpoint hash for {key}')
    if problems:
        return None, problems
    folder = Path(panel_paths[0])
    try:
        relative = str(folder.resolve().relative_to(Path(exp).resolve()))
    except ValueError:
        relative = str(folder.resolve())
    return dict(schema=module.DEV_PASSED_SCHEMA, experiment='19b',
                seeds=[int(s) for s in seeds], arms=list(ARMS), architecture=ARCH,
                report_sha256=sha(Path(report_path)),
                dev_panels=dict(path=relative, manifest_sha256=suites[0]),
                awake_checkpoints={k: by_key[k] for k in awake_keys},
                offline_checkpoints={k: by_key[k] for k in offline_keys},
                marks=dict(bounded=BOUNDED_MARK, gain=GAIN_MARK, guard=GUARD_MARK,
                           retention_f=RETENTION_F_MARK, retention_h=RETENTION_H_MARK,
                           h_loss_limit=H_LOSS_LIMIT),
                confirmation_marks=confirmation_marks(),
                source_fingerprint=source_fingerprint(), created_unix=time.time()), []


# =========================================================================== cap probe


def cap_probe(args):
    """Astra: "Verify this boundary on a disposable fixture before freezing."

    Disposable seed, throwaway units, nothing written.  Forces the STOP decision so the
    boundary is exercised directly instead of being hoped for.
    """
    configure()
    model, flags = TR.build_dispatcher(args.seed)
    model.eval()
    operator = TR.verified_operator()
    units = [V4.throwaway_unit(args.cell, i) for i in range(args.units)]
    _inputs, questions, table = V3.prepare_side(operator, units, 'a')[0]
    tokens, present = V1.pad_questions(questions)
    subjects = [i for i in range(tokens.shape[1])
                if all(V1.ENTITY_MIN <= int(t) < V1.ENTITY_MAX for t in tokens[:, i])]
    operations = [i for i in range(tokens.shape[1])
                  if all(int(V1.OP_INDEX[int(t)]) >= 0 for t in tokens[:, i])]
    if not subjects or not operations:
        raise SystemExit(f'cell {args.cell} has no constant entity/operation question position; '
                         f'pick another fixture cell')
    subject_at, operation_at = subjects[0], operations[0]

    def forcing(stop_after):
        def policy(step, tks, results, n_results):
            batch = tks.shape[0]
            everywhere = torch.ones(batch, dtype=torch.bool)
            want = 1 if (stop_after is not None and step == stop_after - 1) else 0
            return dict(subject=(torch.full((batch,), subject_at), everywhere),
                        operation=(torch.full((batch,), operation_at), everywhere),
                        stop=(torch.full((batch,), want), everywhere))
        return policy

    rows = []
    for cap in (TRAIN_CAP, EVAL_CAP):
        for label, stop_after in ((f'never STOPs', None),
                                  (f'STOPs after lookup {cap}', cap),
                                  (f'STOPs after lookup {cap - 1}', cap - 1)):
            record = []
            with torch.no_grad():
                episodes = V4.rollout_v4(model, tokens, present, table,
                                         torch.arange(len(units)), cap, mode='greedy',
                                         policy=forcing(stop_after), flags=flags, record=record)
            rows.append(dict(cap=cap, case=label, stop_samples=len(record),
                             status=sorted(set(episodes.status)),
                             calls=sorted({int(c) for c in episodes.calls}),
                             transcript_lengths=sorted({len(t) for t in episodes.transcripts})))
            print(json.dumps(rows[-1]), flush=True)

    by_case = {(r['cap'], r['case']): r for r in rows}
    exhausted = by_case[(TRAIN_CAP, 'never STOPs')]
    at_cap = by_case[(TRAIN_CAP, f'STOPs after lookup {TRAIN_CAP}')]
    verdict = dict(
        kind='novelty19b-cap-probe', train_cap=TRAIN_CAP, eval_cap=EVAL_CAP,
        stop_sampled_after_the_last_lookup=bool(exhausted['stop_samples'] == TRAIN_CAP),
        cap_length_answer_terminates_normally=bool(at_cap['status'] == ['answered']
                                                   and at_cap['calls'] == [TRAIN_CAP]),
        exhausted_episode_fails=bool(exhausted['status'] == ['over_cap']
                                     and exhausted['calls'] == [TRAIN_CAP]),
        rows=rows, override_needed=False,
        note='the frozen rollout already samples STOP after the cap-th executed lookup, so '
             '19b needs no modified loop and the training path is the frozen one byte for byte',
        source_fingerprint=source_fingerprint())
    verdict['passed'] = bool(verdict['stop_sampled_after_the_last_lookup']
                             and verdict['cap_length_answer_terminates_normally']
                             and verdict['exhausted_episode_fails'])
    print(json.dumps({k: v for k, v in verdict.items() if k != 'rows'}, indent=2), flush=True)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        write_new(Path(args.out), verdict)
    if not verdict['passed']:
        raise SystemExit('the cap/STOP boundary is NOT what the preregistration requires')
    return verdict


# =========================================================================== command line


def build_parser():
    parser = argparse.ArgumentParser(
        prog='fable_novelty19b_train.py',
        description='experiment 19b -- U8 versus U5, the training side',
        formatter_class=argparse.RawDescriptionHelpFormatter)
    subs = parser.add_subparsers(dest='command', required=True)

    o = subs.add_parser('offline', help='one 2,000-update continuation from an awake final')
    o.add_argument('--seed', required=True, type=int)
    o.add_argument('--arm', required=True, choices=list(ARMS))
    o.add_argument('--exp', default=str(EXP2), help='EXP2 root holding buffers-<seed>')
    o.add_argument('--out', required=True, help='run directory (created; append-only)')
    o.add_argument('--updates', type=int, default=OFFLINE_UPDATES)
    o.add_argument('--chunk-updates', type=TR.bounded('--chunk-updates', OFFLINE_CHUNK),
                   default=OFFLINE_CHUNK, help=f'registered ceiling {OFFLINE_CHUNK}')
    o.add_argument('--budget-seconds', type=TR.budget_seconds, default=TR.CHUNK_SECONDS,
                   help=f'stop at the next chunk boundary; ceiling {TR.WAVE_DEADLINE}')
    o.add_argument('--no-work-ledger', action='store_true',
                   help='skip the per-update work ledger (the training path is identical '
                        'either way; this exists so a test can prove that)')
    o.add_argument('--quiet', action='store_true')
    o.set_defaults(handler=offline)

    s = subs.add_parser('score', help='native scoring of the 38 fresh cells')
    s.add_argument('--ckpt', required=True, help='an awake anchor or an offline final')
    s.add_argument('--panels', required=True)
    s.add_argument('--out', required=True)
    s.add_argument('--cells', default=None, help='comma-separated subset; cells are whole')
    s.add_argument('--eval-cap', type=int, default=EVAL_CAP)
    s.add_argument('--operator', default=None, help='override only for a fixture test')
    s.add_argument('--no-oracle', action='store_true')
    s.add_argument('--transcripts', default=None)
    s.set_defaults(handler=score)

    g = subs.add_parser('gates', help='prerequisites and provenance')
    g.add_argument('--exp', default=str(EXP2))
    g.add_argument('--seeds', dest='seed_list', type=TR.seed_list, default=SEEDS)
    g.add_argument('--out', default=None)
    g.set_defaults(handler=gates)

    r = subs.add_parser('report', help="Astra's five conditions, per seed, no averaging")
    r.add_argument('--exp', default=str(EXP2))
    r.add_argument('--seeds', dest='seed_list', type=TR.seed_list, default=SEEDS)
    r.add_argument('--out', default=None, help='default EXP/report.json')
    r.add_argument('--overwrite', action='store_true')
    r.set_defaults(handler=report)

    c = subs.add_parser('cap-probe', help='verify the training-cap / STOP boundary')
    c.add_argument('--seed', type=int, default=9990, help='disposable; never a registered seed')
    c.add_argument('--cell', default='k1-prac', help='a THROWAWAY v4 cell, never a panel')
    c.add_argument('--units', type=int, default=8)
    c.add_argument('--out', default=None)
    c.set_defaults(handler=cap_probe)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    args.handler(args)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
