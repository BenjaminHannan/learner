"""Experiment 27 / milestone M1-F -- "new names" with the name scale FROZEN at 1.2.

Design of record: `design/v3/27-new-names-followup-design-fable-review.md`
(sha256 63d2bb51c412336fd54bdcc5d012a7da9ac01ae4d01ff2b52497a95052c5d990), section 4.
Parent experiment: `scripts/fable_newnames21.py` (closed; FAIL 0/3, control 3/3).  That file
is imported, never copied and never edited: every recipe object, the model, the pool, the
panel generator, the scorer and the gate arithmetic come from it.

THE ONE CHANGE (design 4.1).  In arm F, experiment 21's learned scalar `code_scale` stops
being a parameter and becomes a constant BUFFER equal to 1.2.  It is a buffer, not a
parameter excluded from the optimiser, because a parameter with a gradient would still
enter `clip_grad_norm_` and so change every other parameter's update.  Nothing else about
experiment 21's treatment changes.

ARMS (seeds 2103, 2104, 2105; design 4.2).
  control  experiment 21's control recipe, byte for byte, on the new seeds.  Gated only by
           the VOID rule.  `control-equivalence` proves it twice over: against the
           registered functions called directly, and against `fable_newnames21`'s own
           control path with the same seed and the same exclusion set, compared tensor for
           tensor after every update.
  F        re-drawn codes, `code_scale` a constant buffer at 1.2.  THE VERDICT ARM.
           78,533 trainable parameters (one fewer than experiment 21's treatment).
  L        re-drawn codes, `code_scale` still learned but started at 1.2.  DESCRIPTIVE:
           it tests the diagnosis, not the milestone, and no verdict depends on it.

DATA (design 4.3).
  pool     the experiment-21 pool is REUSED, not re-drawn: `pool` writes a hash-checked
           reference to `artifacts/fable-newnames21-20260920/pool/pool.json` and every
           later command re-verifies the file hash and all three tensor hashes before a
           code is drawn.  The reserved 1,024 have still never been trained on.
  panels   a FRESH ten-cell suite (c1-c6, p12-1..3, s3; 512 units each) in a new namespace
           and a new seed base, from the same generator; panel codes in a new namespace and
           seed-independent, so the reserved-vs-training-pool comparison stays paired.
  worlds   `random.Random(1101)`, shared by arms and seeds, exactly as experiment 21.
  codes    new namespace `newnames27/train-codes:<seed>`, re-drawn every visit of every
           update.
  forbidden  the union of the registered screen exclusion and THIS experiment's fresh panel
           semantics, checked at every one of the 6,000 updates.

MARKS (design 4.4; experiment 21's, unchanged).  Reserved-code scoring >= 487/512 on
c1, c2, p12-1, p12-2 and >= 461/512 on the other six; paired reserved-minus-training-pool
>= -13/512 on every cell (with a two-sided WARNING line at |difference| > 13); the control
must meet the same ten cutoffs in >= 2/3 seeds or the verdict is VOID; PASS = 3/3 F seeds,
2/3 = PARTIAL and no claim, otherwise FAIL.  Final checkpoint only, no selection, run once.

PRE-NAMED FAILURE SIGNATURES (design 4.5), all computed mechanically from the JSON:
`scale_collapsed` (arm L only), `name_blind` with its `bias_exit` / `gain_exit` /
`unexplained` sub-label, `never_started`, `copy_side_failure`, `reserved_gap`, `unnamed`.
For arm F a changed buffer is not a signature but a BUG: the run is INVALID.

LOGGING (design 4.6).  Every 100 updates, for arms F and L only, under `torch.no_grad()`,
on the batch just trained on, consuming no random number: `code_scale`,
`entity_output_bias`, mean answer-vector length, effective name scale, the `answer_norm`
gain RMS, the mean length of the sixteen value rows, the answer loss, LINK and attribute
accuracy on the batch, and the probability mass on names for LINK and for value questions.
`inertness` proves the logging changes no computation.

SUBCOMMANDS
  pool                  freeze a hash-checked reference to experiment 21's code pool
  panels                the fresh ten-cell suite and the data audit
  control-equivalence   the two control proofs (design 4.3, last bullet)
  treatment-equivalence arm L at 0.13856 against experiment 21's treatment, 50 updates
  inertness             the 100-update trace on and off, fingerprint for fingerprint
  train                 one run:  --arm {control,F,L} --seed S
  score                 one final checkpoint against the frozen panels (F/L: both pools)
  gates                 the marks, the verdict and the failure signatures
  report                human-readable tables
  readouts              the two DESCRIPTIVE read-outs of design 4.6 (no verdict effect)
  fingerprint           sha256 of this file and of every frozen module it imports

Nothing is overwritten: folders are created with `exist_ok=False` and files with
`premonition_memnn_compare.write_new`.  No checkpoint named `test.pt` is ever loaded.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKTREE = HERE.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import argparse                                                            # noqa: E402
import contextlib                                                          # noqa: E402
import gc                                                                  # noqa: E402
import hashlib                                                             # noqa: E402
import json                                                                # noqa: E402
import random                                                              # noqa: E402
import resource                                                            # noqa: E402
import tempfile                                                            # noqa: E402
import time                                                                # noqa: E402
import traceback                                                           # noqa: E402

# `fable_newnames21` prepends BASE and BASE/scripts to sys.path and binds every frozen
# module.  Importing it is the only path-setup this file does.
import fable_newnames21 as N                                               # noqa: E402

torch, nn = N.torch, N.nn
A, R, P, S, V, C, I, FC = N.A, N.R, N.P, N.S, N.V, N.C, N.I, N.FC
data, T, E = N.data, N.T, N.E

QUESTION, ANSWER, WORLD, LINK = N.QUESTION, N.ANSWER, N.WORLD, N.LINK
ENTITY_MIN, ENTITY_MAX, ENTITIES = N.ENTITY_MIN, N.ENTITY_MAX, N.ENTITIES

# ----------------------------------------------------------------------- registration

OUT = WORKTREE/'artifacts/fable-newnames27-20260921'
POOL_SOURCE = WORKTREE/'artifacts/fable-newnames21-20260920'

VARIANT = N.VARIANT                                 # 'grow-blind'
SEEDS = (2103, 2104, 2105)
ARMS = ('control', 'F', 'L')
CODE_ARMS = ('F', 'L')                              # the arms that use re-drawn codes
POOLS = N.POOLS                                     # ('train', 'reserved')
UPDATES = N.UPDATES                                 # 6,000
VISITS = N.VISITS                                   # 16

WIDTH, VOCAB = N.WIDTH, N.VOCAB

# THE NUMBER.  1.2 is where the control's own name rows finish (nine finished control runs:
# 1.19, 1.16, 1.29, 1.17, 1.22, 1.36, 0.98, 1.20, 1.39; mean 1.22).  Declared in the design
# before anything was built and NOT re-tuned after any outcome (design 4.7).
CODE_SCALE = 1.2
# Arm L's start value is the same number; only its `requires_grad` differs.
L_CODE_SCALE_START = CODE_SCALE
# Experiment 21's start value, used only by `treatment-equivalence`.
EXP21_CODE_SCALE = N.CODE_SCALE_INIT                # 0.02 * sqrt(48) = 0.13856...

TRAIN_CODE_NAMESPACE = 'newnames27/train-codes'
PANEL_CODE_NAMESPACE = 'newnames27/panel-codes'
PANEL_NAMESPACE = 'newnames27-operator-v1-20260921'
PANEL_SEED_BASE = 202609212700

CELL_ORDER = N.CELL_ORDER                           # c1..c6, p12-1..3, s3
CUTOFFS = N.CUTOFFS
PAIRED_SLACK = N.PAIRED_SLACK                       # 13/512, one-sided mark
PANEL_N = N.PANEL_N                                 # 512

TRACE_EVERY = 100                                   # design 4.6 (21 logged every 500)
TRACE_KEYS = ('updates', 'code_scale', 'entity_output_bias', 'mean_answer_length',
              'effective_name_scale', 'answer_norm_gain_rms', 'value_row_mean_length',
              'answer_loss', 'link_accuracy', 'attribute_accuracy', 'name_mass_link',
              'name_mass_value')

# Value tokens: `LadderSpec.value(v)` = FIRST_FREE(8) + relations(3) + 1 + v, i.e. 12..27,
# sixteen of them; 28..51 are the fillers and 52.. are the people.  Checked against the
# frozen generator by `tests/test_fable_newnames27.py`.
VALUE_MIN = LINK+1
VALUE_COUNT = 16
assert VALUE_MIN == 12 and VALUE_MIN+VALUE_COUNT <= ENTITY_MIN, (VALUE_MIN, ENTITY_MIN)

# Watchdog caps.  NOT part of the recipe: a cap only ever aborts a run (as in 21).
TRAINING_SECONDS = N.TRAINING_SECONDS
WORK_SECONDS = N.WORK_SECONDS

CHANCE = N.CHANCE                                   # 1/16
NEVER_STARTED_AT = N.NEVER_STARTED_AT               # 2x chance, on c1 and c2
LINK_CHANCE_AT = N.LINK_CHANCE_AT                   # 0.125
ATTRIBUTES_FINE_AT = N.ATTRIBUTES_FINE_AT           # 0.90
SCALE_COLLAPSED_AT = .05                            # design 4.5, arm L only
SCALE_COLLAPSED_FROM = 500                          # "at any logged point from update 500"
BIAS_EXIT_AT = -3.0                                 # design 4.5, name_blind sub-label
GAIN_EXIT_AT = 3.5                                  # "< 3.5, half its start"

REGISTERED_EXCLUSION = N.REGISTERED_EXCLUSION
REGISTERED_GROW_BLIND = N.REGISTERED_GROW_BLIND


# ============================================================== source fingerprint

def source_files():
    """Experiment 21's fingerprint set plus this file."""
    files = dict(N.source_files())
    mine = str(Path(__file__).resolve())
    files[mine] = C.sha(mine)
    return {name: files[name] for name in sorted(files)}


def source_fingerprint(files=None):
    files = files if files is not None else source_files()
    payload = json.dumps(files, sort_keys=True, separators=(',', ':')).encode()
    return hashlib.sha256(payload).hexdigest()


def provenance():
    files = source_files()
    return dict(N.provenance(), source_fingerprint=source_fingerprint(files),
                source_files=files, experiment='27/M1-F')


refuse_existing = N.refuse_existing
tensor_sha = N.tensor_sha
configure_once = N.configure_once


@contextlib.contextmanager
def replay_seeds():
    """Lend `fable_newnames21.panel_audit` THIS experiment's seeds for its replay.

    The audit replays the training stream to look for panel collisions, and the stream's
    blind-curriculum RNG is seeded per run (`fable-startup-grow-blind:<seed>`), so the
    replay must use experiment 27's first seed, not experiment 21's.  Rebinding the module
    constant runs the REGISTERED audit code -- the same code object, not a copy -- and the
    original tuple is restored even on an exception.  It is used for the audit only;
    nothing that decides a number for a model ever runs inside it.
    """
    old = N.SEEDS
    try:
        N.SEEDS = SEEDS
        yield
    finally:
        N.SEEDS = old
        assert N.SEEDS == (2100, 2101, 2102), N.SEEDS


# ====================================================== the reused code pool

def cmd_pool(args):
    """Freeze a hash-checked REFERENCE to experiment 21's pool.  Nothing is re-drawn."""
    folder = refuse_existing(Path(args.out)/'pool')
    source = Path(args.source)
    summary = json.loads((source/'pool/pool.json').read_text())
    pool = N.load_pool(source)                      # verifies file and tensor hashes
    reference = dict(provenance(), source=str(source.resolve()),
                     pool_json=str((source/'pool/pool.json').resolve()),
                     pool_json_sha256=C.sha(source/'pool/pool.json'),
                     pool_pt=summary['path'], pool_pt_sha256=summary['sha256'],
                     codes_sha256=summary['codes_sha256'],
                     train_index_sha256=summary['train_index_sha256'],
                     reserved_index_sha256=summary['reserved_index_sha256'],
                     namespace=summary['namespace'],
                     split_namespace=summary['split_namespace'],
                     registered_source=summary.get('registered'),
                     size=summary['size'], width=summary['width'],
                     train_size=summary['train_size'],
                     reserved_size=summary['reserved_size'],
                     distribution=summary['distribution'],
                     verified_codes_sha256=tensor_sha(pool['codes']),
                     verified_train_index_sha256=tensor_sha(pool['train_index']),
                     verified_reserved_index_sha256=tensor_sha(pool['reserved_index']),
                     code_scale=CODE_SCALE,
                     code_scale_rule='FROZEN at 1.2 in arm F (constant buffer) and the '
                                     'START value in arm L; declared in design 27 section '
                                     '4.1 and never re-tuned')
    folder.mkdir(parents=True, exist_ok=False)
    C.write_new(folder/'pool-ref.json', reference)
    print(json.dumps({k: v for k, v in reference.items()
                      if k not in ('source_files',)}), flush=True)
    return reference


def load_pool(exp):
    """Read experiment 21's frozen pool through this experiment's reference, re-verified."""
    reference = json.loads((Path(exp)/'pool/pool-ref.json').read_text())
    source = Path(reference['source'])
    if C.sha(source/'pool/pool.json') != reference['pool_json_sha256']:
        raise RuntimeError(f'the referenced pool summary changed on disk: {source}')
    pool = N.load_pool(source)
    for key, field in (('codes', 'codes_sha256'), ('train_index', 'train_index_sha256'),
                       ('reserved_index', 'reserved_index_sha256')):
        if tensor_sha(pool[key]) != reference[field]:
            raise RuntimeError(f'the referenced pool tensor changed: {key}')
    pool['reference'] = reference
    return pool


pool_subset = N.pool_subset
assign_codes = N.assign_codes


# ============================================================ the models

class FrozenScaleViolation(RuntimeError):
    """The arm-F buffer moved.  This is a bug, not a result: the run is INVALID."""


class FrozenScaleOperator(N.NewNamesOperator):
    """Experiment 21's treatment with `code_scale` demoted from parameter to buffer.

    `NewNamesOperator.__init__` builds the whole model first (so the random draw for a seed
    is bit-identical to arm L's), and the two lines below then move the one scalar out of
    `_parameters` and register it as a persistent buffer.  A buffer:
      * receives no gradient, so it cannot be moved by AdamW or by weight decay;
      * is NOT in `model.parameters()`, so it never enters `clip_grad_norm_` and therefore
        changes no other parameter's update (design 4.1's reason for a buffer rather than a
        parameter left out of the optimiser);
      * is in `state_dict()`, so a reload is exact and the fingerprint covers it.
    """

    def __init__(self, vocab=VOCAB, width=WIDTH, heads=4, steps=3, entity_min=ENTITY_MIN,
                 code_scale=CODE_SCALE):
        super().__init__(vocab=vocab, width=width, heads=heads, steps=steps,
                         entity_min=entity_min, code_scale=code_scale)
        value = self.code_scale.detach().clone()
        del self._parameters['code_scale']
        self.register_buffer('code_scale', value)
        self.frozen_code_scale = float(value)

    def check_frozen(self, where=''):
        """Any change at all -- the run is INVALID (design 4.5)."""
        if 'code_scale' in dict(self.named_parameters()):
            raise FrozenScaleViolation(f'code_scale is a parameter again {where}')
        if self.code_scale.requires_grad:
            raise FrozenScaleViolation(f'code_scale requires grad {where}')
        actual = float(self.code_scale)
        if actual != self.frozen_code_scale:
            raise FrozenScaleViolation(
                f'code_scale moved from {self.frozen_code_scale!r} to {actual!r} {where}')
        return actual


def new_control_model(seed):
    return N.new_control_model(seed)


def new_F_model(seed, code_scale=CODE_SCALE):
    """The same construction stream as experiment 21's treatment: seed, build, rescale."""
    torch.manual_seed(seed)
    model = FrozenScaleOperator(code_scale=code_scale)
    I.rescale(model)
    model.check_frozen('at construction')
    return model


def new_L_model(seed, code_scale=L_CODE_SCALE_START):
    """Experiment 21's treatment model with ONE number changed: the start value."""
    return N.new_treatment_model(seed, code_scale=code_scale)


def new_model_for(arm, seed, code_scale=None):
    assert arm in ARMS, arm
    if arm == 'control':
        assert code_scale is None, 'the control has no code scale'
        return new_control_model(seed)
    if arm == 'F':
        return new_F_model(seed, CODE_SCALE if code_scale is None else code_scale)
    return new_L_model(seed, L_CODE_SCALE_START if code_scale is None else code_scale)


def trainable_parameters(model):
    return N.trainable_parameters(model)


def load_checkpoint(path):
    """Read-only.  Hashed BEFORE it is loaded; the stored fingerprint is re-derived."""
    path = Path(path)
    if path.name == 'test.pt':
        raise ValueError('test.pt is prohibited')
    sha = C.sha(path)
    saved = P.load(path)
    arm = saved['arm']
    assert arm in ARMS, arm
    if arm == 'control':
        model = A.CanonicalOperator(**saved['architecture'])
    elif arm == 'F':
        # AUDIT-27 MINOR-8: build arm F at the REGISTERED 1.2, not at the number the
        # checkpoint happens to record, so `check_frozen` below compares the loaded buffer
        # against the design's value instead of against the file's own claim.
        architecture = dict(saved['architecture'])
        recorded = float(architecture.pop('code_scale'))
        assert abs(recorded-CODE_SCALE) <= 1e-6, \
            f'{path} records code_scale {recorded!r}, not the registered {CODE_SCALE}'
        model = FrozenScaleOperator(code_scale=CODE_SCALE, **architecture)
    else:
        model = N.NewNamesOperator(**saved['architecture'])
    model.load_state_dict(saved['state_dict'], strict=True)
    model.eval()
    if C.fingerprint(model) != saved['final_fingerprint']:
        raise RuntimeError(f'checkpoint fingerprint mismatch: {path}')
    if arm == 'F':
        model.check_frozen('in the reloaded checkpoint')
    return model, sha, saved


# ====================================================================== panels

def cmd_panels(args):
    """The fresh ten-cell suite and the data audit.  No 64-person cells: design 27 does
    not ask for them, and the two descriptive read-outs of 4.6 replace them."""
    exp = Path(args.out)
    folder = refuse_existing(exp/'panels')
    started = time.monotonic()
    namespace, seed_base = args.namespace, args.seed_base
    if (namespace, seed_base) != (PANEL_NAMESPACE, PANEL_SEED_BASE):
        print(json.dumps(dict(warning='FIXTURE PANELS: not the registered namespace/seed',
                              namespace=namespace, seed_base=seed_base)), flush=True)
    manifest = FC.build_operator_suite(folder, n=args.n, namespace=namespace,
                                       seed_base=seed_base)
    with replay_seeds():
        audit = N.panel_audit(exp, folder, manifest, updates=args.audit_updates,
                              dev_sources=not args.skip_dev_audit)
    top = dict(provenance(), n=args.n, namespace=namespace, seed_base=seed_base,
               registered=(namespace, seed_base) == (PANEL_NAMESPACE, PANEL_SEED_BASE),
               cell_order=list(CELL_ORDER), cutoffs=CUTOFFS, paired_slack=PAIRED_SLACK,
               replay_seed=SEEDS[0],
               operator_manifest_sha256=C.sha(folder/'manifest.json'),
               exclusion_path=manifest['exclusion_path'],
               exclusion_sha256=manifest['exclusion_sha256'],
               exclusion_count=manifest['exclusion_count'],
               audit=audit, seconds=round(time.monotonic()-started, 1))
    C.write_new(folder/'newnames27-panels.json', top)
    print(json.dumps(dict(cells=list(CELL_ORDER), exclusion_count=top['exclusion_count'],
                          audit_clear=audit['all_clear'], failures=audit['failures'],
                          seconds=top['seconds'])), flush=True)
    return top


panel_paths = N.panel_paths
load_panel = N.load_panel
training_exclusion = N.training_exclusion


# ====================================================================== training

def configure_recipe(seed):
    """The registered grow-blind recipe, exactly as experiment 21 configures it."""
    return N.configure_recipe(seed)


def answer_state(model, inputs, trace=False):
    """The frozen forward's answer vector (the tied head is the identity, see 21)."""
    codes = model.codes_for(inputs.memory)
    previous = (model._codes, model._lines, model._owner)
    model._codes, model._lines, model._owner = codes, inputs.memory.shape[1], inputs.owner
    try:
        with torch.no_grad():
            return A.CanonicalOperator.forward(model, inputs, trace=trace)
    finally:
        model._codes, model._lines, model._owner = previous


def _mass_and_accuracy(logits, targets):
    """(name-mass, accuracy) split by whether the ANSWER is a name or a value."""
    probability = logits.softmax(-1)
    name_mass = probability[:, ENTITY_MIN:].sum(-1)
    predicted = logits.argmax(-1)
    correct = predicted.eq(targets)
    is_name = targets.ge(ENTITY_MIN)
    out = {}
    for label, mask in (('link', is_name), ('value', ~is_name)):
        n = int(mask.sum())
        out[label] = dict(n=n,
                          name_mass=float(name_mass[mask].mean()) if n else None,
                          accuracy=float(correct[mask].float().mean()) if n else None)
    return out


def trace_row(model, batch, updates):
    """Design 4.6.  `torch.no_grad()`, the batch just trained on, no random number used.

    Proven inert by the `inertness` subcommand: the 50-update fingerprint is identical
    with the trace on and off.  It reads parameters and runs three extra forwards; it
    writes nothing, draws nothing and touches no optimiser state.
    """
    was = model.training
    model.eval()
    try:
        with torch.no_grad():
            logits = model(batch.canonical)
            targets = batch.canonical_targets.answer
            split = _mass_and_accuracy(logits, targets)
            answer = answer_state(model, batch.canonical)
            lengths = answer.norm(dim=-1)
            loss = float(.75*V._answer_ce(model, batch.canonical, batch.canonical_targets)
                         + .25*V._answer_ce(model, batch.monolithic,
                                            batch.monolithic_targets))
            scale = float(model.code_scale.detach())
            mean_length = float(lengths.mean())
            row = dict(updates=int(updates), code_scale=scale,
                       entity_output_bias=float(model.entity_output_bias.detach()),
                       mean_answer_length=mean_length,
                       effective_name_scale=scale*mean_length,
                       answer_norm_gain_rms=float(
                           model.answer_norm.weight.detach().pow(2).mean().sqrt()),
                       value_row_mean_length=float(
                           model.base_embedding.detach()[VALUE_MIN:VALUE_MIN+VALUE_COUNT]
                           .norm(dim=1).mean()),
                       answer_loss=loss,
                       link_accuracy=split['link']['accuracy'],
                       attribute_accuracy=split['value']['accuracy'],
                       name_mass_link=split['link']['name_mass'],
                       name_mass_value=split['value']['name_mass'])
    finally:
        model.train(was)
    assert tuple(row) == TRACE_KEYS, tuple(row)
    return row


def trace_summary(trace, arm):
    """The few numbers the gates and the signatures read, derived from the trace only."""
    if not trace:
        return None
    late = [row for row in trace if row['updates'] >= SCALE_COLLAPSED_FROM]
    final = trace[-1]
    scales = [abs(row['code_scale']) for row in late]
    return dict(rows=len(trace), first_update=trace[0]['updates'],
                final_update=final['updates'],
                min_abs_code_scale_from_500=min(scales) if scales else None,
                final_code_scale=final['code_scale'],
                final_entity_output_bias=final['entity_output_bias'],
                final_mean_answer_length=final['mean_answer_length'],
                final_effective_name_scale=final['effective_name_scale'],
                final_link_accuracy=final['link_accuracy'],
                final_attribute_accuracy=final['attribute_accuracy'],
                scale_collapsed=bool(arm == 'L' and scales
                                     and min(scales) < SCALE_COLLAPSED_AT),
                scale_collapsed_rule=f'arm L only: |code_scale| < {SCALE_COLLAPSED_AT} at '
                                     f'any logged point from update {SCALE_COLLAPSED_FROM}')


def train_run(arm, seed, exp, updates=UPDATES, out=None, wave_start=None,
              fixture_step0=0, pool=None, log_every=S.LOG_EVERY,
              trace_every=TRACE_EVERY, code_scale=None, code_namespace=None):
    """One run.  The loop is `astra_canonical_operator_run.worker`'s loop, call for call;
    arms F and L add binding this update's codes, and F and L add the inert trace."""
    assert arm in ARMS, arm
    # AUDIT-27 §2.1: `updates` is refused on the registered seeds too.  A short run writes
    # a `completion.json` that says "complete" and is otherwise indistinguishable from a
    # full one, which is the one escape that could report a partial set as finished.
    overrides = dict(code_scale=code_scale, code_namespace=code_namespace,
                     trace_every=None if trace_every == TRACE_EVERY else trace_every,
                     updates=None if updates == UPDATES else updates)
    if seed in SEEDS:
        assert not any(v is not None for v in overrides.values()), \
            f'the registered seeds refuse every override: {overrides}'
        assert not fixture_step0, 'fixture-step0 is refused for the registered seeds'
    namespace = code_namespace or TRAIN_CODE_NAMESPACE
    started = time.monotonic()
    folder = refuse_existing(Path(out) if out else Path(exp)/'runs'/f'{arm}-{seed}')
    folder.mkdir(parents=True, exist_ok=False)
    updates_done, invalid = 0, None
    try:
        params = configure_recipe(seed)
        forbidden, exclusion = training_exclusion(exp)
        model = new_model_for(arm, seed, code_scale=code_scale)
        initial = C.fingerprint(model)
        optimizer = A.T.optimizer_for(model)
        rng = random.Random(1101)
        codes_meta, trace = None, []
        if arm in CODE_ARMS:
            pool = pool if pool is not None else load_pool(exp)
            subset = pool_subset(pool, 'train')
            code_rng_key = f'{namespace}:{seed}'
            code_generator = random.Random(code_rng_key)
            codes_meta = dict(pool_sha256=pool['reference']['pool_pt_sha256'],
                              pool_source=pool['reference']['source'],
                              code_namespace=code_rng_key, pool='train',
                              train_size=pool['reference']['train_size'],
                              reserved_size=pool['reference']['reserved_size'],
                              code_scale=float(model.code_scale.detach()),
                              code_scale_frozen=arm == 'F', people=ENTITIES)
        if fixture_step0:
            S.STATE['step'] = int(fixture_step0)
        base_step = S.STATE['step']
        training_start = time.monotonic()
        flops, intervals = 0, []
        for step in range(base_step, base_step+updates):
            if wave_start is not None:
                R.deadline(wave_start, WORK_SECONDS)
            if time.monotonic()-training_start >= TRAINING_SECONDS:
                raise TimeoutError('training time cap')
            tick = time.monotonic()
            batch = A.training_batch(rng, VISITS, forbidden)
            flops += A.training_flops(batch, model)
            if arm in CODE_ARMS:
                # The ONE extra call: this update's names.  The batch never saw the model,
                # so all three arms consume identical world streams.
                codes, _index = assign_codes(
                    subset, f'{code_rng_key}:{step}:{code_generator.randrange(1 << 30)}',
                    VISITS, ENTITIES)
                model.bind_batch(batch, codes)
            A.training_step(model, optimizer, batch, step)
            updates_done += 1
            if arm == 'F':
                model.check_frozen(f'after update {updates_done}')
            if arm in CODE_ARMS and trace_every and updates_done % trace_every == 0:
                trace.append(trace_row(model, batch, updates_done))
            if arm in CODE_ARMS:
                model.clear_bindings()
            intervals.append(time.monotonic()-tick)
            if updates_done % 500 == 0:
                beat = dict(arm=arm, seed=seed, updates=updates_done,
                            training_seconds=time.monotonic()-training_start)
                if trace:
                    beat.update({k: trace[-1][k] for k in
                                 ('code_scale', 'entity_output_bias', 'link_accuracy',
                                  'attribute_accuracy')})
                if log_every:
                    print(json.dumps(beat), flush=True)
        train_seconds = time.monotonic()-training_start
        if arm == 'F':
            model.check_frozen('at the end of training')
        final = C.fingerprint(model)
        scale_now = float(model.code_scale.detach()) if arm in CODE_ARMS else None
        architecture = (dict(vocab=VOCAB, width=WIDTH, heads=4, steps=3) if arm == 'control'
                        else dict(vocab=VOCAB, width=WIDTH, heads=4, steps=3,
                                  entity_min=ENTITY_MIN, code_scale=scale_now))
        checkpoint = folder/'final.pt'
        torch.save(dict(state_dict=model.state_dict(), seed=seed, arm=arm,
                        updates=updates_done, final_fingerprint=final,
                        architecture=architecture, codes=codes_meta,
                        source_fingerprint=source_fingerprint()), checkpoint)
        training = dict(provenance(), arm=arm, seed=seed, variant=VARIANT,
                        registered_params=params, updates=updates_done,
                        base_step=base_step, fixture_step0=int(fixture_step0),
                        overrides={k: v for k, v in overrides.items() if v is not None},
                        seconds=train_seconds,
                        seconds_per_update=train_seconds/max(1, updates_done),
                        tail_seconds_per_update=(sum(intervals[-40:])/min(40, len(intervals))
                                                 if intervals else None),
                        flops=flops, initial_fingerprint=initial, final_fingerprint=final,
                        checkpoint_sha256=C.sha(checkpoint),
                        parameters=model.parameters_count(),
                        trainable_parameters=trainable_parameters(model),
                        code_scale_is_buffer=arm == 'F', code_scale_final=scale_now,
                        trace_every=trace_every if arm in CODE_ARMS else None,
                        trace=trace if arm in CODE_ARMS else None,
                        trace_summary=trace_summary(trace, arm),
                        exclusion=exclusion, codes=codes_meta,
                        peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        C.write_new(folder/'training.json', training)
        C.write_new(folder/'completion.json',
                    dict(arm=arm, seed=seed, complete=True, updates=updates_done,
                         seconds=time.monotonic()-started, final_checkpoint_only=True,
                         checkpoint_sha256=training['checkpoint_sha256']))
        print(json.dumps({k: training[k] for k in
                          ('arm', 'seed', 'updates', 'seconds', 'seconds_per_update',
                           'trainable_parameters', 'code_scale_final',
                           'final_fingerprint')}), flush=True)
        return training
    except BaseException as exc:                                          # noqa: BLE001
        invalid = isinstance(exc, FrozenScaleViolation)
        C.write_new(folder/'failure.json',
                    dict(arm=arm, seed=seed, complete=False, invalid=bool(invalid),
                         reason=('the frozen code_scale changed; the run is INVALID'
                                 if invalid else 'run failed'),
                         updates=updates_done, seconds=time.monotonic()-started,
                         error=repr(exc), traceback=traceback.format_exc()))
        raise


# ------------------------------------------------------------ control equivalence

def control_path_updates(seed, exp, updates):
    """`updates` updates driven by THIS file's control path, measured as 21 measures it."""
    configure_recipe(seed)
    forbidden, _exclusion = training_exclusion(exp)
    model = new_model_for('control', seed)
    optimizer = A.T.optimizer_for(model)
    rng = random.Random(1101)
    fingerprints, losses = [C.fingerprint(model)], []
    for step in range(updates):
        batch = A.training_batch(rng, VISITS, forbidden)
        A.training_flops(batch, model)
        with torch.no_grad():
            was = model.training
            model.eval()
            losses.append(float(.75*V._answer_ce(model, batch.canonical,
                                                 batch.canonical_targets)
                                + .25*V._answer_ce(model, batch.monolithic,
                                                   batch.monolithic_targets)))
            model.train(was)
        A.training_step(model, optimizer, batch, step)
        fingerprints.append(C.fingerprint(model))
    return fingerprints, losses, model


def _state_dict_equal(a, b):
    """Bit-identical tensor comparison, key by key."""
    if sorted(a) != sorted(b):
        return False, sorted(set(a) ^ set(b)), 0
    mismatched = [key for key in sorted(a) if not torch.equal(a[key], b[key])]
    return not mismatched, mismatched, len(a)


def control_equivalence(seed, exp, updates=50, out=None, scratch=None):
    """Two proofs that the control arm is experiment 21's control (design 4.3).

    (A) against the REGISTERED functions called directly (`N.reference_updates`), the
        parameter fingerprint after every update and the answer loss before every update;
    (B) against `fable_newnames21`'s own `train_run('control', ...)` -- the real training
        path of the parent experiment -- with the same seed, the same pool and the same
        exclusion set, compared by initial and final fingerprint and then TENSOR FOR
        TENSOR over the whole final state dict.
    """
    mine, my_losses, my_model = control_path_updates(seed, exp, updates)
    theirs, their_losses = N.reference_updates(seed, exp, updates)
    first_difference = next((i for i, (a, b) in enumerate(zip(mine, theirs)) if a != b),
                            None)
    registered = None
    path = REGISTERED_GROW_BLIND/f'astra_canonical_operator_seed-{seed}/training.json'
    if path.exists():
        row = json.loads(path.read_text())
        rebuilt = C.fingerprint(A.new_model(seed))
        registered = dict(path=str(path), registered_initial=row['initial_fingerprint'],
                          rebuilt_initial=rebuilt,
                          initial_matches=rebuilt == row['initial_fingerprint'],
                          registered_final=row['final_fingerprint'],
                          registered_updates=row['updates'])
    with contextlib.ExitStack() as stack:
        root = Path(scratch) if scratch else Path(
            stack.enter_context(tempfile.TemporaryDirectory()))
        root.mkdir(parents=True, exist_ok=True)
        pool = load_pool(exp)
        ours = train_run('control', seed, exp, updates=updates, out=root/'exp27-control',
                         pool=pool, log_every=0)
        parent = N.train_run('control', seed, exp, updates=updates,
                             out=root/'exp21-control', pool=pool, log_every=0)
        ours_state = P.load(root/'exp27-control/final.pt')['state_dict']
        parent_state = P.load(root/'exp21-control/final.pt')['state_dict']
    equal, mismatched, count = _state_dict_equal(ours_state, parent_state)
    result = dict(provenance(), seed=seed, updates=updates,
                  fingerprints_equal=mine == theirs,
                  first_differing_update=first_difference,
                  max_abs_loss_difference=max((abs(a-b) for a, b in
                                               zip(my_losses, their_losses)), default=0.),
                  losses_equal=my_losses == their_losses,
                  control_path_losses=my_losses,
                  control_path_final_fingerprint=mine[-1],
                  registered_reference=registered,
                  against_experiment_21=dict(
                      exp27_initial=ours['initial_fingerprint'],
                      exp21_initial=parent['initial_fingerprint'],
                      exp27_final=ours['final_fingerprint'],
                      exp21_final=parent['final_fingerprint'],
                      initial_equal=ours['initial_fingerprint'] ==
                      parent['initial_fingerprint'],
                      final_equal=ours['final_fingerprint'] == parent['final_fingerprint'],
                      tensors_equal=equal, tensors_compared=count,
                      mismatched_tensors=mismatched,
                      note='same seed, same pool, same exclusion set; the experiment-21 '
                           'control path run with this experiment\'s data wave'))
    if out:
        C.write_new(refuse_existing(out), result)
    print(json.dumps({k: v for k, v in result.items()
                      if k not in ('source_files', 'control_path_losses')}), flush=True)
    return result


def treatment_equivalence(seed, exp, updates=50, out=None, scratch=None):
    """Design 4.3: arm L started at 0.13856 reproduces experiment 21's treatment.

    Both sides run over the same pool, the same exclusion set and the same code namespace
    (experiment 21's), so the only thing being tested is whether this file changed anything
    but the one number.
    """
    pool = load_pool(exp)
    with contextlib.ExitStack() as stack:
        root = Path(scratch) if scratch else Path(
            stack.enter_context(tempfile.TemporaryDirectory()))
        root.mkdir(parents=True, exist_ok=True)
        mine = train_run('L', seed, exp, updates=updates, out=root/'exp27-L',
                         pool=pool, log_every=0, code_scale=EXP21_CODE_SCALE,
                         code_namespace=N.TRAIN_CODE_NAMESPACE)
        theirs = N.train_run('treatment', seed, exp, updates=updates,
                             out=root/'exp21-treatment', pool=pool, log_every=0)
        mine_state = P.load(root/'exp27-L/final.pt')['state_dict']
        their_state = P.load(root/'exp21-treatment/final.pt')['state_dict']
    equal, mismatched, count = _state_dict_equal(mine_state, their_state)
    result = dict(provenance(), seed=seed, updates=updates,
                  code_scale_start=EXP21_CODE_SCALE,
                  code_namespace=N.TRAIN_CODE_NAMESPACE,
                  exp27_initial=mine['initial_fingerprint'],
                  exp21_initial=theirs['initial_fingerprint'],
                  exp27_final=mine['final_fingerprint'],
                  exp21_final=theirs['final_fingerprint'],
                  initial_equal=mine['initial_fingerprint'] == theirs['initial_fingerprint'],
                  final_equal=mine['final_fingerprint'] == theirs['final_fingerprint'],
                  tensors_equal=equal, tensors_compared=count,
                  mismatched_tensors=mismatched,
                  exp27_trainable=mine['trainable_parameters'],
                  exp21_trainable=theirs['trainable_parameters'])
    if out:
        C.write_new(refuse_existing(out), result)
    print(json.dumps({k: v for k, v in result.items() if k != 'source_files'}), flush=True)
    return result


def inertness(exp, updates=50, seed=9, arms=CODE_ARMS, out=None, scratch=None):
    """Design 4.6: the trace changes no computation, for one F and one L fixture run."""
    assert seed not in SEEDS, 'the inertness proof runs on a fixture seed'
    pool = load_pool(exp)
    rows = {}
    with contextlib.ExitStack() as stack:
        root = Path(scratch) if scratch else Path(
            stack.enter_context(tempfile.TemporaryDirectory()))
        root.mkdir(parents=True, exist_ok=True)
        for arm in arms:
            on = train_run(arm, seed, exp, updates=updates, out=root/f'{arm}-on',
                           pool=pool, log_every=0, trace_every=TRACE_EVERY)
            off = train_run(arm, seed, exp, updates=updates, out=root/f'{arm}-off',
                            pool=pool, log_every=0, trace_every=0)
            on_state = P.load(root/f'{arm}-on/final.pt')['state_dict']
            off_state = P.load(root/f'{arm}-off/final.pt')['state_dict']
            equal, mismatched, count = _state_dict_equal(on_state, off_state)
            rows[arm] = dict(initial_equal=on['initial_fingerprint'] ==
                             off['initial_fingerprint'],
                             final_equal=on['final_fingerprint'] ==
                             off['final_fingerprint'],
                             flops_equal=on['flops'] == off['flops'],
                             tensors_equal=equal, tensors_compared=count,
                             mismatched_tensors=mismatched,
                             trace_rows_on=len(on['trace']), trace_rows_off=len(off['trace']),
                             final_fingerprint=on['final_fingerprint'])
    result = dict(provenance(), seed=seed, updates=updates, trace_every=TRACE_EVERY,
                  arms=rows, all_inert=all(r['final_equal'] and r['tensors_equal']
                                           for r in rows.values()))
    if out:
        C.write_new(refuse_existing(out), result)
    print(json.dumps({k: v for k, v in result.items() if k != 'source_files'}), flush=True)
    return result


def cmd_train(args):
    exp = Path(args.exp)
    return train_run(args.arm, args.seed, exp, updates=args.updates, out=args.out,
                     wave_start=args.wave_start, fixture_step0=args.fixture_step0,
                     trace_every=args.trace_every)


def cmd_control_equivalence(args):
    return control_equivalence(args.seed, Path(args.exp), args.updates, args.out,
                               args.scratch)


def cmd_treatment_equivalence(args):
    return treatment_equivalence(args.seed, Path(args.exp), args.updates, args.out,
                                 args.scratch)


def cmd_inertness(args):
    return inertness(Path(args.exp), args.updates, args.seed, out=args.out,
                     scratch=args.scratch)


# ====================================================================== scoring

cell_programs = N.cell_programs
cell_diagnostics = N.cell_diagnostics


def bind_cell(model, panel, subset, which_pool, cell):
    """This experiment's panel-code namespace; seed-independent, paired by chunk."""
    model.clear_bindings()
    return model.bind_panel(panel, lambda index, worlds: assign_codes(
        subset, f'{PANEL_CODE_NAMESPACE}:{which_pool}:{cell}:{index}', worlds, ENTITIES)[0])


def score_model(model, exp, which_pool, pool=None, panels=None, work_seconds=1e9):
    """The ten gated cells through the unmodified `astra_canonical_operator_run.score_cell`.

    The fixed external loop `A.execute`, the single-forward `M` baseline and the gold-path
    oracle, on the FINAL checkpoint only.  Arms F and L bind this pool's per-world codes to
    each chunk first; the panel files are never written, so the two scorings of an arm run
    on byte-identical panels.
    """
    rows = panels if panels is not None else panel_paths(exp)
    coded = isinstance(model, N.NewNamesOperator)
    subset = pool_subset(pool, which_pool) if coded else None
    cells, started = {}, time.monotonic()
    for cell, row in rows.items():
        panel = load_panel(row)
        if coded:
            bind_cell(model, panel, subset, which_pool, cell)
        result = R.score_cell(model, panel, time.monotonic(), work_seconds)
        summary = {k: v for k, v in result.items() if k != 'records'}
        summary['diagnostics_by_operation'] = cell_diagnostics(panel, result)
        summary['cutoff'] = row['cutoff']
        summary['panel_sha256'] = row['sha256']
        cells[cell] = summary
        print(json.dumps(dict(cell=cell, pool=which_pool, R=result['R'], M=result['M'],
                              n=result['n'])), flush=True)
        del result, panel
        gc.collect()
    if coded:
        model.clear_bindings()
    return dict(cells=cells, pool=which_pool if coded else None,
                seconds=round(time.monotonic()-started, 1))


def cmd_score(args):
    exp = Path(args.exp)
    run = Path(args.run) if args.run else exp/'runs'/f'{args.arm}-{args.seed}'
    checkpoint = run/'final.pt'
    if not (run/'completion.json').exists():
        raise SystemExit(f'{run} has no completion.json (not a completed run)')
    model, sha, saved = load_checkpoint(checkpoint)
    arm = saved['arm']
    out = Path(args.out) if args.out else exp/'scores'/f'{arm}-{saved["seed"]}.json'
    refuse_existing(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    pool = load_pool(exp) if arm in CODE_ARMS else None
    rows = panel_paths(exp)
    training = json.loads((run/'training.json').read_text())
    buffer_ok = None
    if arm == 'F':
        # `check_frozen` raises if the buffer moved at all; this also re-checks that the
        # value it was frozen at is the registered 1.2 (to float32's precision).
        buffer_ok = bool(abs(model.check_frozen('at scoring')-CODE_SCALE) <= 1e-6)
    scorings = {}
    if arm == 'control':
        scorings['control'] = score_model(model, exp, 'train', pool=None, panels=rows)
    else:
        for which in POOLS:
            scorings[which] = score_model(model, exp, which, pool=pool, panels=rows)
    payload = dict(provenance(), arm=arm, seed=saved['seed'], run=str(run.resolve()),
                   checkpoint=str(checkpoint.resolve()), checkpoint_sha256=sha,
                   final_fingerprint=saved['final_fingerprint'], updates=saved['updates'],
                   codes=saved.get('codes'),
                   pool_sha256=pool['reference']['pool_pt_sha256'] if pool else None,
                   cutoffs=CUTOFFS, cell_order=list(CELL_ORDER),
                   code_scale_final=training.get('code_scale_final'),
                   code_scale_is_buffer=training.get('code_scale_is_buffer'),
                   buffer_ok=buffer_ok, trace_summary=training.get('trace_summary'),
                   scorings=scorings)
    C.write_new(out, payload)
    print(json.dumps(dict(arm=arm, seed=saved['seed'], out=str(out),
                          sha256=C.sha(out))), flush=True)
    return payload


# ====================================================================== gates

seed_verdict = N.seed_verdict


def paired_warnings(verdict):
    """21b Q10 / design 4.4: a two-sided warning line, which is not a mark."""
    return [cell for cell in CELL_ORDER
            if abs(verdict['cells'][cell].get('paired_delta', 0)) > PAIRED_SLACK]


def failure_signatures(arm, reserved, reference=None, verdict=None, summary=None):
    """Design 4.5, computed mechanically.  Descriptive: they never change a verdict."""
    base = N.failure_signatures(reserved)
    cells = reserved['cells']
    link = base['first_stage_link_accuracy']
    link_at_chance = bool(link) and all(row['accuracy'] <= LINK_CHANCE_AT
                                        for row in link.values())
    paired = ([verdict['cells'][cell].get('paired_delta') for cell in CELL_ORDER]
              if verdict is not None else [])
    name_blind = bool(paired and all(delta == 0 for delta in paired) and link_at_chance)
    sub_label = None
    if name_blind:
        bias = (summary or {}).get('final_entity_output_bias')
        gain = (summary or {}).get('final_mean_answer_length')
        if bias is not None and bias <= BIAS_EXIT_AT:
            sub_label = 'bias_exit'
        elif gain is not None and gain < GAIN_EXIT_AT:
            sub_label = 'gain_exit'
        else:
            sub_label = 'unexplained'
    reserved_gap = None
    if reference is not None:
        reserved_meets = all(cells[c]['R'] >= CUTOFFS[c] for c in CELL_ORDER)
        train_meets = all(reference['cells'][c]['R'] >= CUTOFFS[c] for c in CELL_ORDER)
        reserved_gap = bool(train_meets and not reserved_meets)
    scale_collapsed = bool(arm == 'L' and (summary or {}).get('scale_collapsed'))
    passed = bool(verdict['passed']) if verdict is not None else None
    named = dict(never_started=base['never_started'],
                 copy_side_failure=base['attributes_fine_link_at_chance'],
                 name_blind=name_blind, reserved_gap=bool(reserved_gap),
                 scale_collapsed=scale_collapsed)
    unnamed = bool(passed is False and not any(named.values()))
    return dict(named, arm=arm, name_blind_sub_label=sub_label, unnamed=unnamed,
                paired_deltas={cell: delta for cell, delta in zip(CELL_ORDER, paired)},
                one_call_attribute_accuracy=base['one_call_attribute_accuracy'],
                first_stage_link_accuracy=link,
                rules=dict(
                    scale_collapsed=f'arm L only: |code_scale| < {SCALE_COLLAPSED_AT} at '
                                    f'any logged point from update {SCALE_COLLAPSED_FROM}; '
                                    'for arm F a changed buffer is a BUG (INVALID)',
                    name_blind='all ten paired differences exactly 0 AND first-stage LINK '
                               f'<= {LINK_CHANCE_AT} on every cell; sub-label bias_exit if '
                               f'entity_output_bias <= {BIAS_EXIT_AT}, gain_exit if the '
                               f'mean answer length < {GAIN_EXIT_AT}, else unexplained',
                    never_started=base['never_started_rule'],
                    copy_side_failure=base['scale_bug_rule'],
                    reserved_gap='all ten cutoffs met on training-pool codes and at least '
                                 'one missed on reserved codes',
                    unnamed='the seed failed and none of the above fired'))


def invalid_runs(exp):
    """Arm-F runs whose frozen buffer moved: the run, and the experiment, are INVALID."""
    rows = []
    folder = Path(exp)/'runs'
    for arm in ARMS:
        for seed in SEEDS:
            failure = folder/f'{arm}-{seed}/failure.json'
            if failure.exists():
                row = json.loads(failure.read_text())
                if row.get('invalid'):
                    rows.append(dict(run=f'{arm}-{seed}', reason=row.get('reason')))
    return rows


def run_integrity(exp):
    """AUDIT-27 §2.3.  Every scored run must be a FULL run produced by ONE source version.

    Gate-side only: it reads `training.json` files that are already on disk and decides
    nothing about a model.  Three ways a run is not a registered run -- fewer (or more)
    than 6,000 updates, any fixture override recorded, or a source fingerprint that
    differs from the other runs' -- and each one makes the experiment INVALID.
    """
    rows, problems = {}, []
    for arm in ARMS:
        for seed in SEEDS:
            path = Path(exp)/'runs'/f'{arm}-{seed}'/'training.json'
            if not path.exists():
                continue
            row = json.loads(path.read_text())
            name = f'{arm}-{seed}'
            rows[name] = dict(updates=row.get('updates'),
                              source_fingerprint=row.get('source_fingerprint'),
                              overrides=row.get('overrides') or {})
            if row.get('updates') != UPDATES:
                problems.append(f'{name}: {row.get("updates")} updates, not {UPDATES}')
            if row.get('overrides'):
                problems.append(f'{name}: overrides {row["overrides"]}')
    prints = sorted({r['source_fingerprint'] for r in rows.values()})
    if len(prints) > 1:
        problems.append(f'the runs were produced by {len(prints)} different source '
                        f'versions: {prints}')
    return dict(runs=rows, source_fingerprints=prints, problems=problems,
                rule=f'every scored run must record exactly {UPDATES} updates, no '
                     'override, and the same source fingerprint as the others')


def collect_scores(exp):
    folder = Path(exp)/'scores'
    scores = {}
    for arm in ARMS:
        for seed in SEEDS:
            path = folder/f'{arm}-{seed}.json'
            if path.exists():
                scores[(arm, seed)] = json.loads(path.read_text())
    return scores


def gate_table(exp, wave=1):
    """Wave 1 decides the verdict (control + F).  Arm L is descriptive, always."""
    scores = collect_scores(exp)
    gated_arms = ('control', 'F')
    missing = [f'{arm}-{seed}' for arm in gated_arms for seed in SEEDS
               if (arm, seed) not in scores]
    verdicts = {arm: {} for arm in ARMS}
    signatures, warnings = {}, {}
    for arm in ARMS:
        for seed in SEEDS:
            row = scores.get((arm, seed))
            if not row:
                continue
            summary = row.get('trace_summary')
            if arm == 'control':
                verdict = seed_verdict('control', row['scorings']['control'])
                verdicts['control'][seed] = verdict
                signatures[f'control-{seed}'] = failure_signatures(
                    'control', row['scorings']['control'], verdict=verdict)
                continue
            reserved, trained = row['scorings']['reserved'], row['scorings']['train']
            verdict = seed_verdict(arm, reserved, reference=trained)
            verdict['training_pool'] = seed_verdict(arm, trained)
            verdict['buffer_ok'] = row.get('buffer_ok')
            verdict['code_scale_final'] = row.get('code_scale_final')
            verdicts[arm][seed] = verdict
            warnings[f'{arm}-{seed}'] = paired_warnings(verdict)
            signatures[f'{arm}-{seed}'] = failure_signatures(
                arm, reserved, reference=trained, verdict=verdict, summary=summary)
    control_pass = sum(1 for v in verdicts['control'].values() if v['passed'])
    f_pass = sum(1 for v in verdicts['F'].values() if v['passed'])
    l_pass = sum(1 for v in verdicts['L'].values() if v['passed'])
    bad_buffer = [f'F-{seed}' for seed, v in verdicts['F'].items()
                  if v.get('buffer_ok') is False]
    invalid = invalid_runs(exp)
    integrity = run_integrity(exp)
    if invalid or bad_buffer or integrity['problems']:
        verdict, reason = 'INVALID', (
            'the frozen code_scale changed / a run is not a full registered run: '
            f'{[r["run"] for r in invalid] + bad_buffer + integrity["problems"]}')
    elif missing:
        verdict, reason = 'INCOMPLETE', f'missing runs: {", ".join(missing)}'
    elif control_pass < 2:
        verdict, reason = 'VOID', 'recipe did not reproduce'
    elif f_pass == len(SEEDS):
        verdict, reason = 'PASS', f'{f_pass}/{len(SEEDS)} F seeds'
    elif f_pass == 2:
        verdict, reason = 'PARTIAL', '2/3 F seeds; reported as partial, no claim'
    else:
        verdict, reason = 'FAIL', f'{f_pass}/{len(SEEDS)} F seeds'
    summary = {name: [k for k, sig in signatures.items() if sig.get(name)]
               for name in ('never_started', 'name_blind', 'copy_side_failure',
                            'reserved_gap', 'scale_collapsed', 'unnamed')}
    return dict(provenance(), wave=wave, seeds=list(SEEDS), arms=list(ARMS),
                cutoffs=CUTOFFS, paired_slack=-PAIRED_SLACK, code_scale=CODE_SCALE,
                missing=missing, invalid_runs=invalid, buffer_violations=bad_buffer,
                integrity=integrity,
                control={str(k): v for k, v in verdicts['control'].items()},
                F={str(k): v for k, v in verdicts['F'].items()},
                L={str(k): v for k, v in verdicts['L'].items()},
                control_seeds_passed=control_pass, F_seeds_passed=f_pass,
                L_seeds_passed=l_pass, verdict=verdict, reason=reason,
                signatures=signatures, signature_summary=summary,
                paired_warnings={k: v for k, v in warnings.items() if v},
                rules=dict(marks='reserved-code panels >= cutoff on every cell',
                           paired='reserved minus training-pool >= -13/512 on every cell; '
                                  'a two-sided WARNING at |difference| > 13 is not a mark',
                           control='>= 2/3 control seeds must meet the same ten cutoffs, '
                                   'else VOID ("recipe did not reproduce")',
                           all_seed_pass='3/3 arm F', partial='2/3 arm F, no claim',
                           arm_L='DESCRIPTIVE: no verdict depends on it',
                           invalid='any arm-F run whose frozen buffer moved, or any run '
                                   'that is not a full registered run (run_integrity)',
                           integrity=integrity['rule']))


def cmd_gates(args):
    exp = Path(args.exp)
    table = gate_table(exp, wave=args.wave)
    out = Path(args.out) if args.out else exp/'gates.json'
    if not out.exists():
        C.write_new(out, table)
    print(json.dumps(dict({k: table[k] for k in
                           ('verdict', 'reason', 'control_seeds_passed', 'F_seeds_passed',
                            'L_seeds_passed', 'missing', 'invalid_runs',
                            'buffer_violations', 'signature_summary', 'paired_warnings')},
                          integrity_problems=table['integrity']['problems']),
                     indent=2), flush=True)
    return table


# ====================================================================== report

def cmd_report(args):
    exp = Path(args.exp)
    table = gate_table(exp, wave=args.wave)
    lines, add = [], None
    add = lines.append
    add('# 27 / M1-F "new names", name scale frozen at 1.2 -- reserved-code panels')
    add('')
    add(f'source fingerprint  {table["source_fingerprint"]}')
    add(f'verdict             {table["verdict"]}  ({table["reason"]})')
    add(f'frozen code_scale   {CODE_SCALE}  (arm F: a constant buffer; arm L: the start '
        f'value of a learned scalar)')
    add(f'control seeds met the ten cutoffs   {table["control_seeds_passed"]}/{len(SEEDS)}')
    add(f'arm F seeds passed                  {table["F_seeds_passed"]}/{len(SEEDS)}')
    add(f'arm L seeds passed (DESCRIPTIVE)    {table["L_seeds_passed"]}/{len(SEEDS)}')
    if table['invalid_runs'] or table['buffer_violations']:
        add(f'INVALID RUNS        {table["invalid_runs"]} {table["buffer_violations"]}')
    integrity = table['integrity']
    add(f'run integrity       {len(integrity["runs"])} runs, '
        f'{len(integrity["source_fingerprints"])} source version(s), '
        + ('all full registered runs' if not integrity['problems']
           else f'PROBLEMS {integrity["problems"]}'))
    add('')
    add('## R (fixed loop) per cell; the F and L columns are the RESERVED-code scoring')
    add('cell    cutoff  ' + '  '.join(f'{arm[:4]}-{seed}' for arm in ARMS
                                       for seed in SEEDS))
    for cell in CELL_ORDER:
        row = [f'{cell:<7}', f'{CUTOFFS[cell]:>6}']
        for arm in ARMS:
            for seed in SEEDS:
                entry = table[arm].get(str(seed))
                row.append('     -' if not entry else f'{entry["cells"][cell]["R"]:>6}')
        add('  '.join(row))
    add('')
    add('## paired reserved minus training-pool (mark: >= -13/512; warning if |d| > 13)')
    add('cell    ' + '  '.join(f'{arm}-{seed}' for arm in CODE_ARMS for seed in SEEDS))
    for cell in CELL_ORDER:
        row = [f'{cell:<7}']
        for arm in CODE_ARMS:
            for seed in SEEDS:
                entry = table[arm].get(str(seed))
                row.append('     -' if not entry else
                           f'{entry["cells"][cell].get("paired_delta", 0):>+6}')
        add('  '.join(row))
    if table['paired_warnings']:
        add(f'paired warnings: {json.dumps(table["paired_warnings"])}')
    add('')
    add('## pre-named failure signatures (descriptive; they never move a verdict)')
    for name, sig in sorted(table['signatures'].items()):
        fired = [key for key in ('never_started', 'name_blind', 'copy_side_failure',
                                 'reserved_gap', 'scale_collapsed', 'unnamed')
                 if sig.get(key)]
        label = f' [{sig["name_blind_sub_label"]}]' if sig.get('name_blind_sub_label') else ''
        add(f'{name}: {", ".join(fired) if fired else "none"}{label}')
        links = sig['first_stage_link_accuracy']
        if links:
            add('    first-stage LINK accuracy  ' +
                '  '.join(f'{k}={v["accuracy"]:.3f}' for k, v in sorted(links.items())))
    add('')
    add('## training trace (every 100 updates; arms F and L)')
    scores = collect_scores(exp)
    for (arm, seed), row in sorted(scores.items()):
        summary = row.get('trace_summary')
        if not summary:
            continue
        add(f'{arm}-{seed}  final code_scale {summary["final_code_scale"]:.4f}  '
            f'min |scale| from 500 '
            f'{summary["min_abs_code_scale_from_500"] if summary["min_abs_code_scale_from_500"] is None else round(summary["min_abs_code_scale_from_500"], 4)}  '
            f'bias {summary["final_entity_output_bias"]:.3f}  '
            f'|answer| {summary["final_mean_answer_length"]:.2f}  '
            f'effective scale {summary["final_effective_name_scale"]:.2f}')
    text = '\n'.join(lines)+'\n'
    out = Path(args.out) if args.out else exp/'report.txt'
    if not out.exists():
        out.write_text(text)
    print(text, flush=True)
    return text


# ====================================================== descriptive read-outs (4.6)

def _line_ids(inputs):
    """Recompute the frozen forward's token -> story-line map, per question row.

    This mirrors `TokenMemoryReasoner.forward` exactly (compaction of the padded memory)
    and is a pure function of `inputs.memory`; no model is involved.
    """
    v, lines, length = inputs.memory.shape
    real = inputs.memory.ne(0).flatten(1)
    rank = real.long().cumsum(1)-1
    owner = torch.arange(v)[:, None].expand_as(real)
    size = max(1, int(real.sum(1).max()))
    table = torch.full((v, size), -1, dtype=torch.long)
    source = torch.arange(lines).repeat_interleave(length)[None].expand_as(real)
    table[owner[real], rank[real]] = source[real]
    return table[inputs.owner], lines


def line_attention(inputs, attention):
    """[questions, lines] -- the LAST read step's cross-attention mass per story line."""
    owned, lines = _line_ids(inputs)
    question_valid = inputs.questions.ne(0)
    last = question_valid.sum(-1)-1
    weights = attention[:, -1].mean(1)                       # mean over heads
    weights = weights[torch.arange(weights.shape[0]), last][:, :owned.shape[1]]
    valid = owned.ge(0)
    index = torch.where(valid, owned, torch.zeros_like(owned))
    mass = torch.zeros(weights.shape[0], lines)
    mass.scatter_add_(1, index, weights*valid)
    return mass


def openset_readout(model, exp, pool, which_pool, candidates, panels=None):
    """Design 4.6 / 21b Q5: first-stage LINK with an OPEN candidate set.

    For every gold path whose first stage is a LINK, the model is run once on that stage's
    canonical input (the same input `A.oracle_inputs` would build) and the answer vector is
    compared against EVERY candidate code -- 1,024 reserved codes for read-out A, all 4,096
    for read-out B -- as well as against the 52 non-name rows.  The stage counts as correct
    only when the right person's own code beats all of them.  Strictly descriptive: it is
    not a gate, it changes nothing, and it is reported for every F seed, pass or fail.
    """
    assert candidates in ('reserved', 'all'), candidates
    rows = panels if panels is not None else panel_paths(exp)
    subset = pool_subset(pool, which_pool)
    bank = pool['codes'] if candidates == 'all' else pool_subset(pool, 'reserved')
    cells, total, correct_total = {}, 0, 0
    for cell, row in rows.items():
        panel = load_panel(row)
        bind_cell(model, panel, subset, which_pool, cell)
        n = hit = 0
        for sides in P.chunks(panel):
            x, _targets = sides['a']
            paths = A.truth_paths(x)
            ids = [i for i, path in enumerate(paths)
                   if path and path[0]['operation'] == LINK]
            if not ids:
                continue
            stage = A.canonical_input(x, [paths[i][0]['entity'] for i in ids],
                                      [LINK]*len(ids), ids)
            answer = answer_state(model, stage)
            codes = model.codes_for(stage.memory)
            with torch.no_grad():
                scale = float(model.code_scale.detach())
                bias = float(model.entity_output_bias.detach())
                own_index = torch.tensor([paths[i][0]['target']-ENTITY_MIN for i in ids])
                own_code = codes[stage.owner, own_index]
                own = (answer*own_code).sum(-1)*scale + bias
                open_logits = answer @ (scale*bank).T + bias
                base = answer @ model.base_embedding.detach().T \
                    + model.base_output_bias.detach()
                beaten = open_logits.gt(own[:, None]).sum(-1) \
                    + base.gt(own[:, None]).sum(-1)
            n += len(ids)
            hit += int(beaten.eq(0).sum())
        cells[cell] = dict(n=n, correct=hit, accuracy=hit/n if n else None)
        total += n
        correct_total += hit
        del panel
        gc.collect()
    model.clear_bindings()
    return dict(candidates=candidates, candidate_count=int(bank.shape[0]),
                scored_pool=which_pool, cells=cells, n=total, correct=correct_total,
                pooled_accuracy=correct_total/total if total else None,
                note='DESCRIPTIVE ONLY.  First-stage LINK under gold-path inputs, scored '
                     'against an open candidate set; not a gate and not part of any mark.')


def attention_readout(model, exp, pool, which_pool, panels=None):
    """Design 4.6 / 25b: "right line attended, wrong name emitted".

    Among first-stage LINK calls where the closed-set emission is wrong, how often did the
    last read step put most of its attention on the story line that states the answer?
    """
    rows = panels if panels is not None else panel_paths(exp)
    subset = pool_subset(pool, which_pool)
    cells = {}
    wrong_total = right_line_total = stages_total = 0
    for cell, row in rows.items():
        panel = load_panel(row)
        bind_cell(model, panel, subset, which_pool, cell)
        n = wrong = right_line = 0
        for sides in P.chunks(panel):
            x, _targets = sides['a']
            paths = A.truth_paths(x)
            ids = [i for i, path in enumerate(paths)
                   if path and path[0]['operation'] == LINK]
            if not ids:
                continue
            stage = A.canonical_input(x, [paths[i][0]['entity'] for i in ids],
                                      [LINK]*len(ids), ids)
            with torch.no_grad():
                logits, attention = model(stage, trace=True)
                emitted = logits.argmax(-1).tolist()
            mass = line_attention(stage, attention)
            top = mass.argmax(-1).tolist()
            memory = x.memory.tolist()
            for slot, i in enumerate(ids):
                target = paths[i][0]['target']
                entity = paths[i][0]['entity']
                n += 1
                if emitted[slot] == target:
                    continue
                wrong += 1
                owner = int(stage.owner[slot])
                gold = [j for j, line in enumerate(memory[owner])
                        if len(line) >= 4 and line[0] == WORLD and line[1] == entity
                        and line[2] == LINK]
                if gold and top[slot] in gold:
                    right_line += 1
        cells[cell] = dict(n=n, wrong=wrong, right_line_attended=right_line,
                           fraction=right_line/wrong if wrong else None)
        n_, wrong_, right_ = n, wrong, right_line
        stages_total += n_
        wrong_total += wrong_
        right_line_total += right_
        del panel
        gc.collect()
    model.clear_bindings()
    return dict(scored_pool=which_pool, cells=cells, n=stages_total, wrong=wrong_total,
                right_line_attended=right_line_total,
                fraction=right_line_total/wrong_total if wrong_total else None,
                note='DESCRIPTIVE ONLY.  Last read step, attention averaged over heads at '
                     'the final question token, grouped by story line.')


def cmd_readouts(args):
    exp = Path(args.exp)
    run = Path(args.run) if args.run else exp/'runs'/f'{args.arm}-{args.seed}'
    model, sha, saved = load_checkpoint(run/'final.pt')
    arm = saved['arm']
    if arm not in CODE_ARMS:
        raise SystemExit('the read-outs are for the code arms (F, L) only')
    out = Path(args.out) if args.out else exp/'readouts'/f'{arm}-{saved["seed"]}.json'
    refuse_existing(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    pool, rows = load_pool(exp), panel_paths(exp)
    payload = dict(provenance(), arm=arm, seed=saved['seed'],
                   checkpoint=str((run/'final.pt').resolve()), checkpoint_sha256=sha,
                   descriptive=True,
                   openset_A=openset_readout(model, exp, pool, 'reserved', 'reserved', rows),
                   openset_B=openset_readout(model, exp, pool, 'reserved', 'all', rows),
                   attention=attention_readout(model, exp, pool, 'reserved', rows))
    C.write_new(out, payload)
    print(json.dumps(dict(arm=arm, seed=saved['seed'],
                          openset_A=payload['openset_A']['pooled_accuracy'],
                          openset_B=payload['openset_B']['pooled_accuracy'],
                          right_line_wrong_name=payload['attention']['fraction'],
                          out=str(out))), flush=True)
    return payload


def cmd_fingerprint(args):
    files = source_files()
    payload = dict(source_fingerprint=source_fingerprint(files), source_files=files)
    if args.out:
        C.write_new(refuse_existing(args.out), payload)
    print(json.dumps(payload, indent=2), flush=True)
    return payload


# ====================================================================== CLI

def build_parser():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    sub = parser.add_subparsers(dest='command', required=True)

    p = sub.add_parser('pool', help='freeze a hash-checked reference to 21\'s code pool')
    p.add_argument('--out', default=str(OUT))
    p.add_argument('--source', default=str(POOL_SOURCE),
                   help='the experiment folder holding pool/pool.json (experiment 21)')

    p = sub.add_parser('panels', help='the fresh ten-cell suite and the data audit')
    p.add_argument('--out', default=str(OUT))
    p.add_argument('--n', type=int, default=PANEL_N)
    p.add_argument('--namespace', default=PANEL_NAMESPACE,
                   help='FIXTURE USE ONLY: anything but the default builds panels that are '
                        'not this experiment\'s registered ones, and says so')
    p.add_argument('--seed-base', type=int, default=PANEL_SEED_BASE)
    p.add_argument('--audit-updates', type=int, default=100,
                   help='partial training-stream replay for the audit (0 disables)')
    p.add_argument('--skip-dev-audit', action='store_true')

    p = sub.add_parser('control-equivalence',
                       help='the control arm against the registered recipe AND against '
                            'experiment 21\'s own control path')
    p.add_argument('--exp', default=str(OUT))
    p.add_argument('--seed', type=int, required=True)
    p.add_argument('--updates', type=int, default=50)
    p.add_argument('--out', default=None)
    p.add_argument('--scratch', default=None)

    p = sub.add_parser('treatment-equivalence',
                       help='arm L at 0.13856 against experiment 21\'s treatment')
    p.add_argument('--exp', default=str(OUT))
    p.add_argument('--seed', type=int, required=True)
    p.add_argument('--updates', type=int, default=50)
    p.add_argument('--out', default=None)
    p.add_argument('--scratch', default=None)

    p = sub.add_parser('inertness', help='the 100-update trace on and off (fixture seed)')
    p.add_argument('--exp', default=str(OUT))
    p.add_argument('--seed', type=int, default=9)
    p.add_argument('--updates', type=int, default=50)
    p.add_argument('--out', default=None)
    p.add_argument('--scratch', default=None)

    p = sub.add_parser('train', help='one run')
    p.add_argument('--exp', default=str(OUT))
    p.add_argument('--arm', choices=list(ARMS), required=True)
    p.add_argument('--seed', type=int, required=True)
    p.add_argument('--updates', type=int, default=UPDATES)
    p.add_argument('--out', default=None)
    p.add_argument('--wave-start', type=float, default=None)
    p.add_argument('--fixture-step0', type=int, default=0,
                   help='start the curriculum clock at this update (FIXTURE TIMING ONLY; '
                        'refused for the registered seeds)')
    p.add_argument('--trace-every', type=int, default=TRACE_EVERY,
                   help='FIXTURE USE ONLY: the registered seeds refuse anything but 100')

    p = sub.add_parser('score', help='one checkpoint against the frozen panels')
    p.add_argument('--exp', default=str(OUT))
    p.add_argument('--arm', choices=list(ARMS))
    p.add_argument('--seed', type=int)
    p.add_argument('--run', default=None)
    p.add_argument('--out', default=None)

    p = sub.add_parser('gates', help='the marks, the verdict and the signatures')
    p.add_argument('--exp', default=str(OUT))
    p.add_argument('--out', default=None)
    p.add_argument('--wave', type=int, default=1)

    p = sub.add_parser('report', help='human-readable tables')
    p.add_argument('--exp', default=str(OUT))
    p.add_argument('--out', default=None)
    p.add_argument('--wave', type=int, default=1)

    p = sub.add_parser('readouts', help='the two DESCRIPTIVE read-outs of design 4.6')
    p.add_argument('--exp', default=str(OUT))
    p.add_argument('--arm', choices=list(CODE_ARMS))
    p.add_argument('--seed', type=int)
    p.add_argument('--run', default=None)
    p.add_argument('--out', default=None)

    p = sub.add_parser('fingerprint', help='sha256 of this file and every frozen module')
    p.add_argument('--out', default=None)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    configure_once()
    return {'pool': cmd_pool, 'panels': cmd_panels, 'train': cmd_train,
            'control-equivalence': cmd_control_equivalence,
            'treatment-equivalence': cmd_treatment_equivalence,
            'inertness': cmd_inertness, 'score': cmd_score, 'gates': cmd_gates,
            'report': cmd_report, 'readouts': cmd_readouts,
            'fingerprint': cmd_fingerprint}[args.command](args)


if __name__ == '__main__':
    main()
