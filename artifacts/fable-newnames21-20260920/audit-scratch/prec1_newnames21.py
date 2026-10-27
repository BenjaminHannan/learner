"""Experiment 21 / milestone M1 -- "new names" (Fable review `design/v3/21`, section 5).

THE ONE CHANGE.  The lookup operator's sixteen entity embeddings -- which are one and the
same vector for the input token, the story token and, through the tied output head, the
answer logit -- stop being trained parameters.  They become FIXED random codes, drawn per
world from a pool of 4,096, of which 1,024 are reserved and never appear in training.  One
learned scalar (`code_scale`) and one shared entity output bias replace the sixteen trained
rows and their sixteen output biases, so the treatment has FEWER trainable parameters than
the control (78,534 against 79,316).

ARMS (seeds 2100, 2101, 2102; six runs; one Mac wave).
  control    the frozen clean-start `grow-blind` recipe exactly as is.  Nothing in this
             file re-implements it: `fable_operator_startup.configure_variant('grow-blind')`
             rebinds `astra_canonical_operator`'s batch/step/flops exactly as the registered
             wave does, the hyper-parameters come from the registered launch manifest via
             `fable_operator_startup.registered_params`, the model is `A.new_model(seed)`,
             the optimizer `A.T.optimizer_for`, the world stream `random.Random(1101)`, and
             the loop is `astra_canonical_operator_run.worker`'s loop, call for call.
             `train --arm control --equivalence N` proves it: N updates of this path against
             N updates driven by the registered functions called directly, comparing the
             parameter fingerprint after EVERY update, not only the loss.
  treatment  identical in every respect except the embedding change above.  The batch, the
             curriculum, the loss, the schedule, the optimizer, the world stream and the
             update count are the control's; the data is byte-identical batch for batch
             because no batch builder ever sees the model.

DATA.  Same generator, six-person training worlds, per-seed world stream shared by both
arms.  A FRESH ten-cell panel (c1-c6, the three-hop stress cell s3, and three 12-person
cells; 512 units each) is built in a new RNG namespace by
`fable_confirmation_panels.build_operator_suite`, which is the registered generator with
the namespace and seed passed explicitly.  Scoring is the fixed loop
(`astra_canonical_operator.execute`) through the unmodified
`astra_canonical_operator_run.score_cell`.

  exclusions   the union of the registered screen's `forbidden-semantics.json` (what the
               registered grow-blind wave itself used, so the control stays byte-identical)
               and this experiment's fresh panel semantics is handed to the trainer as
               `forbidden`.  Every training record is checked against it at every one of the
               6,000 updates and the run ABORTS on a collision, which is a complete
               guarantee that these runs' training worlds are excluded from the panels --
               stronger than the partial replay index the `panels` audit also writes.

  two scorings, byte-identical panels   the treatment is scored twice on the SAME panel
               files: once with per-world codes drawn from the 3,072 training codes and once
               from the 1,024 reserved codes.  The per-world assignment is keyed by
               (namespace, pool, cell, chunk), so the two scorings differ in nothing but the
               pool, and the two sides of a pair cell always receive the SAME codes.

  descriptive extra (treatment, reserved codes only)   64-person worlds, 256 facts, the
               first look past the sixteen-entity ceiling.  Not gated, reported separately.

MARKS (per seed, no averaging; section 5).
  * reserved-code panels >= 487/512 on c1, c2, p12-1, p12-2 and >= 461/512 on the other six;
  * reserved minus training-pool >= -13/512 on every cell, paired;
  * the control must meet its own marks in >= 2/3 seeds, else the verdict is VOID
    ("recipe did not reproduce");
  * all-seed pass = 3/3; 2/3 is reported as partial, with no claim.

PRE-NAMED FAILURE SIGNATURES (section 5's two most likely failures, named before the run).
  never_started                     per seed; c1 and c2 at or below twice chance.
  attributes_fine_link_at_chance    one-hop accuracy split by relation: LINK against each
                                    attribute relation.  Attributes healthy while the LINK
                                    lookup sits at chance is the scale mismatch the reviewer
                                    predicted -- a fixable bug, NOT "binding is impossible".

SUBCOMMANDS
  pool         draw and freeze the 4,096-code pool and its 3,072/1,024 split
  panels       build the fresh ten-cell suite, the 64-person descriptive cells, and the
               data audit (within-suite, against every development source, and a partial
               replay of the training stream)
  train        one run:  --arm {control,treatment} --seed S
  score        one run's checkpoint against the frozen panels (treatment: both pools)
  gates        apply the marks above and emit the verdict and the failure signatures
  report       human-readable tables
  fingerprint  sha256 of this file and of every frozen module it imports

Every output carries that source fingerprint.  Every checkpoint is hashed before it is
loaded.  Nothing is overwritten: folders are created with `exist_ok=False` and files with
`premonition_memnn_compare.write_new`.

Location note: this file lives in the `card-experiment-handoff-7c5b27` worktree because the
harness refuses writes to the base checkout.  `BASE` and `BASE/scripts` are prepended to
`sys.path`, exactly as `scripts/fable_operator_startup.py` does, so every registered module,
the frozen `premonition` package and the registered artifacts are the BASE repository's.
"""
from __future__ import annotations

import sys
from pathlib import Path

BASE = Path('/Users/ben-hannan/Desktop/projects/beautiful-model')
HERE = Path(__file__).resolve().parent
WORKTREE = HERE.parent
if HERE != (BASE/'scripts'):
    for _entry in (str(BASE), str(BASE/'scripts')):
        while _entry in sys.path:
            sys.path.remove(_entry)
        sys.path.insert(0, _entry)

import argparse                                                            # noqa: E402
import contextlib                                                          # noqa: E402
import datetime                                                            # noqa: E402
import gc                                                                  # noqa: E402
import hashlib                                                             # noqa: E402
import json                                                                # noqa: E402
import math                                                                # noqa: E402
import os                                                                  # noqa: E402
import random                                                              # noqa: E402
import resource                                                            # noqa: E402
import time                                                                # noqa: E402
import traceback                                                           # noqa: E402

import astra_canonical_operator as A                                       # noqa: E402
import astra_canonical_operator_run as R                                   # noqa: E402
import astra_canonical_operator_panels as P                                # noqa: E402
import fable_operator_startup as S                                         # noqa: E402
import fable_operator_variants as V                                        # noqa: E402
import premonition_memnn_compare as C                                      # noqa: E402
import premonition_token_initialization_probe as I                         # noqa: E402

# imported last: it prepends the WORKTREE scripts folder to sys.path for its own
# `fable_dispatcher*` imports.  Everything registered is already bound above.
sys.path.insert(0, str(HERE))
import fable_confirmation_panels as FC                                     # noqa: E402

torch, data, T, E = A.torch, A.data, A.T, A.E
nn = T.nn
ROOT = R.ROOT
assert ROOT == BASE, (ROOT, BASE)
for _module in (A, R, P, S, V, C, I):
    assert Path(_module.__file__).resolve().parent == BASE/'scripts', _module.__file__
assert Path(FC.__file__).resolve().parent == HERE, FC.__file__

QUESTION, ANSWER, WORLD, LINK = A.QUESTION, A.ANSWER, A.WORLD, A.LINK
ENTITY_MIN, ENTITY_MAX = A.ENTITY_MIN, A.ENTITY_MAX
ENTITIES = ENTITY_MAX - ENTITY_MIN                  # 16 entity token slots
ATTRIBUTE_RELATIONS = S.ATTRIBUTE_RELATIONS         # (8, 9, 10)
CANONICAL_OPS = ATTRIBUTE_RELATIONS + (LINK,)
PYTHON = R.PYTHON

# ----------------------------------------------------------------------- registration

OUT = WORKTREE/'artifacts/fable-newnames21-20260920'
VARIANT = 'grow-blind'
SEEDS = (2100, 2101, 2102)
ARMS = ('control', 'treatment')
POOLS = ('train', 'reserved')
UPDATES = 6000
VISITS = 16

WIDTH = 48
VOCAB = 68
POOL_SIZE = 4096
RESERVED_SIZE = 1024
TRAIN_SIZE = POOL_SIZE - RESERVED_SIZE              # 3,072
EMBED_INIT_STD = .02                                # TokenMemoryReasoner._initialize

# THE CODE SCALE RULE, fixed before training and never tuned.  A control entity embedding
# row is 48 independent N(0, .02^2) draws, so its root-mean-square norm at initialisation
# is exactly std * sqrt(width).  `code_scale` starts there and is the only thing about the
# codes that learns.  (Measured check, seed 0: the mean control entity-row norm is 0.1409
# against this 0.1386 -- the same quantity up to the sampling noise of sixteen rows.)
CODE_SCALE_INIT = EMBED_INIT_STD*math.sqrt(WIDTH)

POOL_NAMESPACE = 'newnames21/pool'
SPLIT_NAMESPACE = 'newnames21/pool/split'
TRAIN_CODE_NAMESPACE = 'newnames21/train-codes'
PANEL_CODE_NAMESPACE = 'newnames21/panel-codes'
PANEL_NAMESPACE = 'newnames21-operator-v1-20260920'
PANEL_SEED_BASE = 202609212100
WIDE_NAMESPACE = 'newnames21/wide64'

CELL_ORDER = FC.OPERATOR_CELL_ORDER                 # c1..c6, p12-1..3, s3
CUTOFFS = {key: cfg['cutoff'] for key, cfg in FC.OPERATOR_CELLS.items()}
PAIRED_SLACK = 13                                   # reserved - training-pool >= -13/512
PANEL_N = 512

# the 64-person descriptive extra: 64 people x (3 attributes + 1 link) = 256 facts.
WIDE_PEOPLE = 64
WIDE_WORLDS = 64
WIDE_CHUNK = 8
WIDE_ATTR_PER_WORLD = 4
WIDE_LINK_PER_WORLD = 2
WIDE_TWO_HOP_PER_WORLD = 2

# Watchdog caps.  These are NOT part of the learning recipe (the registered grow-blind
# manifest's own 1,500 s / 1,740 s / 1,770 s were set for a THREE-process wave; this wave
# runs six).  A cap only ever aborts a run; it never changes a single update.
TRAINING_SECONDS = 1680
WORK_SECONDS = 1740
TERMINATE_SECONDS = 1770

CHANCE = 1/16.                                      # 16 value tokens, 16 entity tokens
NEVER_STARTED_AT = 2*CHANCE                         # "never started": c1 and c2 <= 2x chance
LINK_CHANCE_AT = 2*CHANCE                           # "LINK at chance": stage-0 LINK <= 2x
ATTRIBUTES_FINE_AT = .90                            # every attribute relation at/above this

REGISTERED_EXCLUSION = ROOT/('artifacts/astra-canonical-operator-screen-20260920/'
                             'astra_canonical_operator_panels/forbidden-semantics.json')
REGISTERED_GROW_BLIND = ROOT/'artifacts/fable-operator-grow-blind-20260920'


# ============================================================== source fingerprint

FROZEN_MODULES = (A, R, P, S, V, C, I, FC, T, E, data)


def source_files():
    """This script, every frozen module it imports, and the frozen world generator."""
    files = {str(Path(__file__).resolve()): None}
    for module in FROZEN_MODULES:
        files[str(Path(module.__file__).resolve())] = None
    data.bootstrap()
    import premonition.toy_ladder as TL
    import premonition_pair_suite as PS
    for module in (TL, PS):
        files[str(Path(module.__file__).resolve())] = None
    return {name: C.sha(name) for name in sorted(files)}


def source_fingerprint(files=None):
    files = files if files is not None else source_files()
    payload = json.dumps(files, sort_keys=True, separators=(',', ':')).encode()
    return hashlib.sha256(payload).hexdigest()


def provenance():
    files = source_files()
    return dict(source_fingerprint=source_fingerprint(files), source_files=files,
                created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())


def digest_bytes(*chunks):
    h = hashlib.sha256()
    for chunk in chunks:
        h.update(chunk if isinstance(chunk, bytes) else str(chunk).encode())
    return h.hexdigest()


def namespace_seed(namespace):
    """A reproducible 63-bit torch seed from a string namespace."""
    return int.from_bytes(hashlib.sha256(namespace.encode()).digest()[:8], 'big') >> 1


def tensor_sha(tensor):
    return hashlib.sha256(tensor.detach().cpu().contiguous().numpy().tobytes()).hexdigest()


def refuse_existing(path):
    path = Path(path)
    if path.exists():
        raise SystemExit(f'refusing to overwrite {path}')
    return path


_CONFIGURED = []


def configure_once():
    """`astra_canonical_operator_run.configure` -- single-threaded torch, bootstrapped data.

    It is not idempotent (`torch.set_num_interop_threads` raises on a second call), so the
    one call per process lives here.
    """
    if not _CONFIGURED:
        R.configure()
        _CONFIGURED.append(True)
    assert torch.get_num_threads() == torch.get_num_interop_threads() == 1


@contextlib.contextmanager
def widened_entities(entity_max):
    """Temporarily widen the frozen executor's entity-id range (64-person cells ONLY).

    `astra_canonical_operator.execute` and `.truth_paths` read `A.ENTITY_MIN`/`A.ENTITY_MAX`
    at call time, so widening them runs the REGISTERED loop -- the same code object, not a
    copy -- over entity ids 52..52+n-1.  The ten gated cells are always scored with the
    module untouched; this is used for the descriptive 64-person extra only, and the
    original values are restored even on an exception.
    """
    old_min, old_max = A.ENTITY_MIN, A.ENTITY_MAX
    try:
        A.ENTITY_MAX = int(entity_max)
        yield
    finally:
        A.ENTITY_MIN, A.ENTITY_MAX = old_min, old_max
        assert (A.ENTITY_MIN, A.ENTITY_MAX) == (52, 68), (A.ENTITY_MIN, A.ENTITY_MAX)


# ====================================================================== the code pool

def build_pool(namespace=POOL_NAMESPACE, split_namespace=SPLIT_NAMESPACE):
    """4,096 fixed codes at the model's embedding width, and the 3,072/1,024 split.

    DISTRIBUTION (declared, not tuned): each code is an independent standard-Gaussian
    direction in R^48, normalised to unit length -- i.e. uniform on the unit sphere.  The
    length is carried entirely by the single learned `code_scale`, so "which person" is a
    direction and "how loud a name is" is one number shared by every person.  Nothing about
    the pool depends on any seed, arm or outcome.

    SPLIT: a fixed permutation of 0..4095 drawn in its own namespace; the first 3,072
    entries are the training codes and the last 1,024 are RESERVED and never drawn during
    training.  The permutation, not a prefix of the pool, so the two halves are exchangeable.
    """
    generator = torch.Generator().manual_seed(namespace_seed(namespace))
    raw = torch.randn(POOL_SIZE, WIDTH, generator=generator, dtype=torch.float32)
    codes = raw/raw.norm(dim=1, keepdim=True)
    split_generator = torch.Generator().manual_seed(namespace_seed(split_namespace))
    permutation = torch.randperm(POOL_SIZE, generator=split_generator)
    train = permutation[:TRAIN_SIZE].clone()
    reserved = permutation[TRAIN_SIZE:].clone()
    assert len(set(train.tolist()) & set(reserved.tolist())) == 0
    assert len(train) == TRAIN_SIZE and len(reserved) == RESERVED_SIZE
    return dict(codes=codes, train_index=train, reserved_index=reserved,
                namespace=namespace, split_namespace=split_namespace,
                distribution='unit-norm Gaussian directions (uniform on the unit sphere)',
                width=WIDTH, size=POOL_SIZE, train_size=TRAIN_SIZE,
                reserved_size=RESERVED_SIZE, code_scale_init=CODE_SCALE_INIT,
                code_scale_rule='embedding init std (.02) x sqrt(width) = the control '
                                'entity row RMS norm at initialisation; fixed before '
                                'training, learned thereafter as one scalar')


def cmd_pool(args):
    folder = refuse_existing(Path(args.out)/'pool')
    folder.mkdir(parents=True, exist_ok=False)
    pool = build_pool(args.namespace, f'{args.namespace}/split')
    if args.namespace != POOL_NAMESPACE:
        print(json.dumps(dict(warning='FIXTURE POOL: not the registered namespace',
                              namespace=args.namespace)), flush=True)
    path = folder/'pool.pt'
    torch.save(pool, path)
    cosine = (pool['codes'] @ pool['codes'].T).abs()
    cosine.fill_diagonal_(0.)                      # off-diagonal only
    off = POOL_SIZE*(POOL_SIZE-1)
    summary = dict(provenance(), path=str(path), sha256=C.sha(path),
                   namespace=args.namespace, split_namespace=pool['split_namespace'],
                   registered=args.namespace == POOL_NAMESPACE,
                   codes_sha256=tensor_sha(pool['codes']),
                   train_index_sha256=tensor_sha(pool['train_index']),
                   reserved_index_sha256=tensor_sha(pool['reserved_index']),
                   size=POOL_SIZE, width=WIDTH, train_size=TRAIN_SIZE,
                   reserved_size=RESERVED_SIZE,
                   distribution=pool['distribution'],
                   code_scale_init=CODE_SCALE_INIT,
                   code_scale_rule=pool['code_scale_rule'],
                   unit_norm_max_error=float((pool['codes'].norm(dim=1)-1).abs().max()),
                   max_abs_cosine=float(cosine.max()),
                   mean_abs_cosine=float(cosine.sum()/off))
    C.write_new(folder/'pool.json', summary)
    print(json.dumps({k: v for k, v in summary.items() if k != 'source_files'}), flush=True)
    return summary


def load_pool(exp):
    """Read the frozen pool and verify every hash before anything uses it."""
    folder = Path(exp)/'pool'
    summary = json.loads((folder/'pool.json').read_text())
    path = Path(summary['path'])
    if C.sha(path) != summary['sha256']:
        raise RuntimeError(f'pool file changed on disk: {path}')
    pool = torch.load(path, map_location='cpu', weights_only=False)
    for key, field in (('codes', 'codes_sha256'), ('train_index', 'train_index_sha256'),
                       ('reserved_index', 'reserved_index_sha256')):
        if tensor_sha(pool[key]) != summary[field]:
            raise RuntimeError(f'pool tensor changed: {key}')
    pool['summary'] = summary
    return pool


def pool_subset(pool, which):
    """The code matrix a scoring or training pass is allowed to draw from."""
    assert which in POOLS, which
    index = pool['train_index'] if which == 'train' else pool['reserved_index']
    return pool['codes'].index_select(0, index)


def assign_codes(subset, key, worlds, people):
    """[worlds, people, width] -- `people` DISTINCT codes per world, drawn from `subset`.

    One `random.Random(key)` draws every world's assignment in order, so the assignment is a
    pure function of (key, pool subset, worlds, people) and is reproducible from the frozen
    pool alone.  Distinct within a world (two people must never share a name); worlds are
    independent, so the same code may serve different people in different worlds -- that is
    the point of "re-drawn per world".
    """
    rng = random.Random(key)
    total = subset.shape[0]
    rows = [rng.sample(range(total), people) for _ in range(worlds)]
    index = torch.tensor(rows, dtype=torch.long)
    codes = subset[index.reshape(-1)].reshape(worlds, people, subset.shape[1])
    return codes.detach().clone(), index


# ============================================================ the treatment model

class TiedHead(nn.Module):
    """Holds the identity matrix the frozen forward multiplies its answer state by.

    `TokenMemoryReasoner.forward` ends with `F.linear(answer, self.embedding.weight,
    self.output_bias)`.  With an identity weight and a zero bias that expression returns the
    answer state itself, so the frozen forward is reused UNCHANGED and the per-world tied
    output head is applied here, in `NewNamesOperator.forward`.  Both are constant buffers:
    they never learn and they appear in the state dict only so a reload is exact.
    """

    def __init__(self, width):
        super().__init__()
        self.register_buffer('weight', torch.eye(width))


class NewNamesOperator(A.CanonicalOperator):
    """The control operator with its entity rows replaced by fixed per-world codes.

    WHAT CHANGES.  Rows 0..51 of the tied embedding (structure, relations, values, filler)
    are the control's trained parameters, untouched.  Rows 52.. are `code_scale * code`,
    where the codes are supplied per world and never receive a gradient.  The same rows are
    used for the input tokens, the story tokens and the tied output logits, so a person is
    one vector in all three places -- exactly as in the control.  The sixteen per-entity
    output biases become ONE shared `entity_output_bias`.

    TRAINABLE PARAMETERS: 79,316 - 68*48 - 68 + 52*48 + 52 + 1 + 1 = 78,534, fewer than the
    control, as section 5 requires.

    BINDING.  Codes are bound to a memory TENSOR, not to a step counter, because the frozen
    scoring loop (`astra_canonical_operator_run.score_cell` -> `A.execute` ->
    `A.oracle_inputs`) calls the model many times on the same story with different
    questions.  `bind` records the tensor object itself and `forward` refuses unless the
    bound object IS the one it was given, so a recycled id can never silently mis-name a
    world.  Both sides of a pair cell are bound to the same codes.
    """

    def __init__(self, vocab=VOCAB, width=WIDTH, heads=4, steps=3, entity_min=ENTITY_MIN,
                 code_scale=CODE_SCALE_INIT):
        super().__init__(vocab=vocab, width=width, heads=heads, steps=steps)
        assert 0 < entity_min < vocab, entity_min
        self.entity_min = int(entity_min)
        base = self.embedding.weight.detach()[:entity_min].clone()
        bias = self.output_bias.detach()[:entity_min].clone()
        del self.embedding
        del self._parameters['output_bias']
        self.embedding = TiedHead(width)
        self.register_buffer('output_bias', torch.zeros(width))
        self.base_embedding = nn.Parameter(base)
        self.base_output_bias = nn.Parameter(bias)
        self.entity_output_bias = nn.Parameter(torch.zeros(()))
        self.code_scale = nn.Parameter(torch.tensor(float(code_scale)))
        with torch.no_grad():
            self.base_embedding[0].zero_()
        self._bindings = {}
        self._codes = self._lines = self._owner = None

    # ------------------------------------------------------------------ code binding

    def bind(self, memory, codes):
        """Bind one packed memory tensor to its per-world codes [visits, people, width]."""
        assert codes.dim() == 3 and codes.shape[0] == memory.shape[0], \
            (tuple(codes.shape), tuple(memory.shape))
        assert codes.shape[2] == self.width, tuple(codes.shape)
        assert not codes.requires_grad, 'codes are never trained'
        self._bindings[id(memory)] = (memory, codes)

    def bind_batch(self, batch, codes):
        for inputs in (batch.canonical, batch.monolithic):
            self.bind(inputs.memory, codes)

    def bind_panel(self, panel, codes_for_chunk):
        """Bind every chunk of a packed panel; both sides of a pair share their codes."""
        bound = 0
        for index, sides in enumerate(P.chunks(panel)):
            codes = codes_for_chunk(index, next(iter(sides.values()))[0].memory.shape[0])
            for _side, (x, _targets) in sorted(sides.items()):
                self.bind(x.memory, codes)
                bound += 1
        return bound

    def clear_bindings(self):
        self._bindings = {}

    def codes_for(self, memory):
        entry = self._bindings.get(id(memory))
        if entry is None or entry[0] is not memory:
            raise RuntimeError('no world codes are bound to this memory tensor')
        return entry[1]

    # ------------------------------------------------------------------ the forward

    def world_weight(self, codes):
        """[worlds, entity_min + people, width] -- the per-world tied embedding table."""
        entity = self.code_scale*codes
        base = self.base_embedding[None].expand(codes.shape[0], -1, -1)
        return torch.cat((base, entity), 1)

    def output_bias_vector(self, people):
        return torch.cat((self.base_output_bias, self.entity_output_bias.expand(people)))

    def embed(self, ids, kind):
        """`TokenMemoryReasoner.embed` with a per-world table instead of a global one.

        `kind` is 0 for the memory rows (the frozen forward passes them reshaped to
        [visits*lines, tokens]) and 1 for the questions ([questions, tokens]), which is
        exactly the information needed to recover each row's world.
        """
        weight = self.world_weight(self._codes)
        if kind == 0:
            owner = torch.arange(ids.shape[0], device=ids.device)//self._lines
        else:
            owner = self._owner
        x = weight[owner[:, None].expand_as(ids), ids]
        return (x + .1*T.positions(ids.shape[-1], self.width, x)
                + self.types[kind])*ids.ne(0)[..., None]

    def forward(self, inputs, *, trace=False):
        codes = self.codes_for(inputs.memory)
        previous = (self._codes, self._lines, self._owner)
        self._codes, self._lines, self._owner = codes, inputs.memory.shape[1], inputs.owner
        try:
            # The frozen forward, unchanged: `embed` above and the identity tied head turn
            # its return value into the answer state rather than logits.
            out = super().forward(inputs, trace=trace)
        finally:
            self._codes, self._lines, self._owner = previous
        answer, attention = out if trace else (out, None)
        weight = self.world_weight(codes)[inputs.owner]
        logits = torch.einsum('qd,qvd->qv', answer, weight) \
            + self.output_bias_vector(codes.shape[1])
        return (logits, attention) if trace else logits


def new_control_model(seed):
    """`astra_canonical_operator.new_model`, untouched."""
    model = A.new_model(seed)
    assert model.parameters_count() == 79316, model.parameters_count()
    return model


def new_treatment_model(seed, code_scale=CODE_SCALE_INIT):
    """The same construction stream: manual_seed, build, rescale the Linear layers.

    `NewNamesOperator.__init__` calls the frozen constructor first, so every shared weight
    starts from the control's draw for this seed; the extra parameters are constants.
    """
    torch.manual_seed(seed)
    model = NewNamesOperator(code_scale=code_scale)
    I.rescale(model)
    return model


def trainable_parameters(model):
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def new_model_for(arm, seed):
    assert arm in ARMS, arm
    return new_control_model(seed) if arm == 'control' else new_treatment_model(seed)


def load_checkpoint(path):
    """Read-only.  The file is hashed BEFORE it is loaded, and the hash is returned."""
    path = Path(path)
    if path.name == 'test.pt':
        raise ValueError('test.pt is prohibited')
    sha = C.sha(path)
    saved = P.load(path)
    arm = saved['arm']
    if arm == 'control':
        model = A.CanonicalOperator(**saved['architecture'])
    else:
        model = NewNamesOperator(**saved['architecture'])
    model.load_state_dict(saved['state_dict'], strict=True)
    model.eval()
    if C.fingerprint(model) != saved['final_fingerprint']:
        raise RuntimeError(f'checkpoint fingerprint mismatch: {path}')
    return model, sha, saved


# ====================================================================== panels

def cmd_panels(args):
    """The fresh ten-cell suite, the 64-person descriptive cells and the data audit."""
    exp = Path(args.out)
    folder = refuse_existing(exp/'panels')
    started = time.monotonic()
    namespace, seed_base = args.namespace, args.seed_base
    if (namespace, seed_base) != (PANEL_NAMESPACE, PANEL_SEED_BASE):
        print(json.dumps(dict(warning='FIXTURE PANELS: not the registered namespace/seed',
                              namespace=namespace, seed_base=seed_base)), flush=True)
    manifest = FC.build_operator_suite(folder, n=args.n, namespace=namespace,
                                       seed_base=seed_base)
    wide = build_wide_panels(folder, worlds=args.wide_worlds)
    audit = panel_audit(exp, folder, manifest, updates=args.audit_updates,
                        dev_sources=not args.skip_dev_audit)
    top = dict(provenance(), n=args.n, namespace=namespace,
               seed_base=seed_base, registered=(namespace, seed_base) ==
               (PANEL_NAMESPACE, PANEL_SEED_BASE),
               cell_order=list(CELL_ORDER), cutoffs=CUTOFFS,
               paired_slack=PAIRED_SLACK,
               operator_manifest_sha256=C.sha(folder/'manifest.json'),
               exclusion_path=manifest['exclusion_path'],
               exclusion_sha256=manifest['exclusion_sha256'],
               exclusion_count=manifest['exclusion_count'],
               wide=wide, audit=audit,
               seconds=round(time.monotonic()-started, 1))
    C.write_new(folder/'newnames21-panels.json', top)
    print(json.dumps(dict(cells=list(CELL_ORDER), wide_worlds=wide['worlds'],
                          exclusion_count=top['exclusion_count'],
                          audit_clear=audit['all_clear'], failures=audit['failures'],
                          seconds=top['seconds'])), flush=True)
    return top


def panel_audit(exp, folder, manifest, updates, dev_sources=True):
    """Outcome-independent: within-suite, against development sources, against training.

    The training-stream check here is a PARTIAL replay (`--audit-updates`, default 100 of
    6,000) and says so.  It is an early-warning check only: the complete guarantee is that
    every one of the 6,000 updates checks its records against the same exclusion set at run
    time and aborts on a collision (`training_batch_blind`'s `forbidden` argument).
    """
    started = time.monotonic()
    panel_semantics = set(json.loads(Path(manifest['exclusion_path']).read_text()))
    failures, sources = [], []
    if dev_sources:
        for row in FC.development_sources():
            entry = dict(row)
            if not row['exists']:
                entry.update(checked=False, disjointness='UNVERIFIED',
                             reason='path not found')
                failures.append(f'unchecked development source: {row["name"]}')
            else:
                semantic, tensors = FC.source_signatures(row)
                overlap = len(panel_semantics & semantic)
                entry.update(checked=True, signatures=len(semantic),
                             overlap_full=overlap,
                             disjointness='clean' if not overlap else 'OVERLAP')
                if overlap:
                    failures.append(f'overlap against {row["name"]}: {overlap} semantic')
            sources.append(entry)
    replay = None
    if updates:
        detail, presented, parent, _tensors = FC.replay_stream(
            VARIANT, SEEDS[0], updates, VISITS, verbose=False)
        overlap = len(panel_semantics & (presented | parent))
        replay = dict(detail, overlap=overlap, partial=updates < UPDATES,
                      full_updates=UPDATES, seed=SEEDS[0],
                      note='PARTIAL: certifies only the updates replayed.  The complete '
                           'guarantee is the run-time `forbidden` check at every update.')
        if overlap:
            failures.append(f'training/panel overlap in the first {updates} updates: '
                            f'{overlap}')
    report = dict(provenance(), panel_signatures=len(panel_semantics),
                  registered_exclusion=str(REGISTERED_EXCLUSION),
                  registered_exclusion_sha256=C.sha(REGISTERED_EXCLUSION),
                  training_exclusion_note='the trainer is handed the UNION of the '
                                          'registered screen exclusion (what the registered '
                                          'grow-blind wave used, so the control stays '
                                          'byte-identical) and these fresh panels',
                  dev_sources_checked=dev_sources, sources=sources, replay=replay,
                  failures=failures, all_clear=not failures,
                  seconds=round(time.monotonic()-started, 1))
    C.write_new(Path(folder)/'audit.json', report)
    return report


def panel_paths(exp):
    """{cell: (path, sha256, cutoff)} from the frozen operator manifest."""
    folder = Path(exp)/'panels'
    manifest = json.loads((folder/'manifest.json').read_text())
    rows = {}
    for cell in manifest['cell_order']:
        row = manifest['cells'][cell]
        rows[cell] = dict(path=row['path'], sha256=row['sha256'], cutoff=row['cutoff'],
                          n=row['n'], entities=row['entities'])
    return rows


def load_panel(row):
    if C.sha(row['path']) != row['sha256']:
        raise RuntimeError(f'panel changed on disk: {row["path"]}')
    return P.load(row['path'])


# --------------------------------------------------- the 64-person descriptive cells

def wide_world(index, people=WIDE_PEOPLE):
    """One 64-person world: 64*3 attribute rows + 64 link rows = 256 facts, plus filler.

    The rows come from the FROZEN generator: `premonition.toy_ladder.visit` is called with
    a `world` built here, which is the same escape hatch `fable_story_size_stress.build_world`
    uses for its 16-person worlds.  The world itself is built by the generator's own rule
    (uniform attribute values, a uniform friend map redrawn until the generator's two-hop
    drawability condition holds), with the single difference that the people are indices
    0..63 instead of a 16-way sample -- which is the whole point of the cell, and is only
    expressible at all because a person is now a code rather than one of sixteen tokens.
    """
    data.bootstrap()
    from premonition.toy_ladder import LadderSpec, World, visit
    spec = LadderSpec()
    rng = random.Random(f'{WIDE_NAMESPACE}:world:{index}')
    ents = list(range(people))
    attr = {(e, r): rng.randrange(spec.values) for e in ents for r in range(spec.relations)}
    while True:
        friend = {e: rng.choice([x for x in ents if x != e]) for e in ents}
        if all(any(x not in (a, friend[a]) and friend[x] not in (a, friend[a])
                   for x in ents) for a in ents):
            break
    rows, _world, _plan = visit(spec, rng, training=True, world=World(ents, attr, friend))
    story = [list(row.tokens) for row in rows if not row.question]
    facts = [row for row in story if len(row) >= 4 and row[0] == WORLD
             and row[1] >= spec.vocab_size and 8 <= row[2] <= LINK]
    assert len(facts) == 4*people, (len(facts), people)
    qrng = random.Random(f'{WIDE_NAMESPACE}:questions:{index}')
    questions, answers, kinds = [], [], []
    for e in qrng.sample(ents, WIDE_ATTR_PER_WORLD):
        r = qrng.randrange(spec.relations)
        questions.append([QUESTION, spec.vocab_size+e, spec.relation(r), ANSWER])
        answers.append(spec.value(attr[(e, r)]))
        kinds.append(f'attribute-{spec.relation(r)}')
    for e in qrng.sample(ents, WIDE_LINK_PER_WORLD):
        questions.append([QUESTION, spec.vocab_size+e, LINK, ANSWER])
        answers.append(spec.vocab_size+friend[e])
        kinds.append('link')
    for e in qrng.sample(ents, WIDE_TWO_HOP_PER_WORLD):
        r = qrng.randrange(spec.relations)
        questions.append([QUESTION, spec.vocab_size+e, LINK, spec.relation(r), ANSWER])
        answers.append(spec.value(attr[(friend[e], r)]))
        kinds.append('two-hop')
    return dict(index=index, people=people, rows=story, questions=questions,
                answers=answers, kinds=kinds, facts=len(facts))


def build_wide_panels(folder, worlds=WIDE_WORLDS, people=WIDE_PEOPLE):
    """Three packed descriptive panels over 64-person worlds: attribute, link, two-hop.

    Homogeneous by question shape on purpose: `score_cell`'s per-stage LINK diagnostic
    indexes every record's link list by position, which is only meaningful when every
    record in a panel has the same operation sequence.
    """
    entity_max = ENTITY_MIN + people
    built = [wide_world(i, people) for i in range(worlds)]
    kinds = (('wide64-attr', lambda k: k.startswith('attribute-'), WIDE_ATTR_PER_WORLD),
             ('wide64-link', lambda k: k == 'link', WIDE_LINK_PER_WORLD),
             ('wide64-two', lambda k: k == 'two-hop', WIDE_TWO_HOP_PER_WORLD))
    chunked = {name: [] for name, _want, _per in kinds}
    rows_per_story, tokens_per_story = [], []
    with widened_entities(entity_max):
        for start in range(0, worlds, WIDE_CHUNK):
            block = built[start:start+WIDE_CHUNK]
            memories = [w['rows'] for w in block]
            rows_per_story += [len(w['rows']) for w in block]
            for name, want, _per in kinds:
                qs, owners, lines, targets = [], [], [], []
                for owner, w in enumerate(block):
                    for q, a, k in zip(w['questions'], w['answers'], w['kinds']):
                        if not want(k):
                            continue
                        qs.append(list(q)); owners.append(owner)
                        lines.append(len(w['rows'])); targets.append(a)
                x = data.pack(memories, qs, owners, lines)
                assert [p[-1]['target'] for p in A.truth_paths(x)] == targets, name
                chunked[name].append({'sides': {'a': (x, targets)}})
                if name == 'wide64-attr':
                    tokens_per_story.append(int(x.memory.ne(0).sum(dim=(1, 2)).max()))
    out = {}
    for name, _want, per in kinds:
        chunks, n = chunked[name], worlds*per
        panel = dict(name=name, n=n, kind='single', invariant=False, chunks=chunks,
                     namespace=WIDE_NAMESPACE, seed=None, entities=people,
                     descriptive=True, people=people)
        path = Path(folder)/f'{name}.pt'
        torch.save(panel, path)
        out[name] = dict(path=str(path.resolve()), sha256=C.sha(path), n=n, people=people,
                         chunk_worlds=WIDE_CHUNK)
    summary = dict(worlds=worlds, people=people, facts_per_world=4*people,
                   entity_max=entity_max, panels=out,
                   rows_per_story=dict(min=min(rows_per_story), max=max(rows_per_story)),
                   max_tokens_per_story=max(tokens_per_story),
                   note='DESCRIPTIVE ONLY, treatment + reserved codes.  Not gated.  The '
                        'frozen executor is reused under `widened_entities`, which rebinds '
                        'A.ENTITY_MAX for these cells and restores it afterwards.')
    C.write_new(Path(folder)/'wide64.json', summary)
    return summary


# ====================================================================== training

def configure_recipe(seed):
    """Point the registered runner at the registered grow-blind recipe, as the wave does."""
    configure_once()
    params = S.registered_params(VARIANT)
    S.configure_variant(VARIANT, seed=seed, **params)
    return params


def training_exclusion(exp):
    """The union handed to the trainer; see `panel_audit`."""
    registered = set(json.loads(REGISTERED_EXCLUSION.read_text()))
    manifest = json.loads((Path(exp)/'panels/manifest.json').read_text())
    if C.sha(manifest['exclusion_path']) != manifest['exclusion_sha256']:
        raise RuntimeError('fresh panel exclusion file changed on disk')
    fresh = set(json.loads(Path(manifest['exclusion_path']).read_text()))
    return registered | fresh, dict(registered=len(registered), fresh=len(fresh),
                                    union=len(registered | fresh),
                                    registered_sha256=C.sha(REGISTERED_EXCLUSION),
                                    fresh_sha256=manifest['exclusion_sha256'])


def train_run(arm, seed, exp, updates=UPDATES, out=None, wave_start=None,
              fixture_step0=0, pool=None, log_every=S.LOG_EVERY):
    """One run.  The loop below is `astra_canonical_operator_run.worker`'s loop, call for
    call; the treatment adds exactly one thing -- binding this update's per-world codes.
    """
    assert arm in ARMS, arm
    started = time.monotonic()
    folder = refuse_existing(Path(out) if out else Path(exp)/'runs'/f'{arm}-{seed}')
    folder.mkdir(parents=True, exist_ok=False)
    updates_done = 0
    try:
        params = configure_recipe(seed)
        forbidden, exclusion = training_exclusion(exp)
        model = new_model_for(arm, seed)
        initial = C.fingerprint(model)
        optimizer = A.T.optimizer_for(model)
        rng = random.Random(1101)
        codes_meta = None
        if arm == 'treatment':
            pool = pool if pool is not None else load_pool(exp)
            subset = pool_subset(pool, 'train')
            code_rng_key = f'{TRAIN_CODE_NAMESPACE}:{seed}'
            code_generator = random.Random(code_rng_key)
            codes_meta = dict(pool_sha256=pool['summary']['sha256'],
                              code_namespace=code_rng_key, pool='train',
                              train_size=TRAIN_SIZE, reserved_size=RESERVED_SIZE,
                              code_scale_init=CODE_SCALE_INIT, people=ENTITIES)
        if fixture_step0:
            assert seed not in SEEDS, 'fixture-step0 is refused for the registered seeds'
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
            if arm == 'treatment':
                # ONE change: this update's names.  The batch above never saw the model,
                # so the control and the treatment consume identical world streams.
                codes, _index = assign_codes(
                    subset, f'{code_rng_key}:{step}:{code_generator.randrange(1 << 30)}',
                    VISITS, ENTITIES)
                model.bind_batch(batch, codes)
            A.training_step(model, optimizer, batch, step)
            if arm == 'treatment':
                model.clear_bindings()
            updates_done += 1
            intervals.append(time.monotonic()-tick)
            if log_every and updates_done % 500 == 0:
                print(json.dumps(dict(arm=arm, seed=seed, updates=updates_done,
                                      training_seconds=time.monotonic()-training_start)),
                      flush=True)
        train_seconds = time.monotonic()-training_start
        final = C.fingerprint(model)
        checkpoint = folder/'final.pt'
        torch.save(dict(state_dict=model.state_dict(), seed=seed, arm=arm,
                        updates=updates_done, final_fingerprint=final,
                        architecture=dict(vocab=VOCAB, width=WIDTH, heads=4, steps=3)
                        if arm == 'control' else
                        dict(vocab=VOCAB, width=WIDTH, heads=4, steps=3,
                             entity_min=ENTITY_MIN, code_scale=CODE_SCALE_INIT),
                        codes=codes_meta, source_fingerprint=source_fingerprint()),
                   checkpoint)
        training = dict(provenance(), arm=arm, seed=seed, variant=VARIANT,
                        registered_params=params, updates=updates_done,
                        base_step=base_step, fixture_step0=int(fixture_step0),
                        seconds=train_seconds,
                        seconds_per_update=train_seconds/max(1, updates_done),
                        tail_seconds_per_update=(sum(intervals[-40:])/min(40, len(intervals))
                                                 if intervals else None),
                        flops=flops, initial_fingerprint=initial, final_fingerprint=final,
                        checkpoint_sha256=C.sha(checkpoint),
                        parameters=model.parameters_count(),
                        trainable_parameters=trainable_parameters(model),
                        exclusion=exclusion, codes=codes_meta,
                        peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        C.write_new(folder/'training.json', training)
        C.write_new(folder/'completion.json',
                    dict(arm=arm, seed=seed, complete=True, updates=updates_done,
                         seconds=time.monotonic()-started,
                         final_checkpoint_only=True,
                         checkpoint_sha256=training['checkpoint_sha256']))
        print(json.dumps({k: training[k] for k in
                          ('arm', 'seed', 'updates', 'seconds', 'seconds_per_update',
                           'trainable_parameters', 'final_fingerprint')}), flush=True)
        return training
    except BaseException as exc:                                          # noqa: BLE001
        C.write_new(folder/'failure.json',
                    dict(arm=arm, seed=seed, complete=False, updates=updates_done,
                         seconds=time.monotonic()-started, error=repr(exc),
                         traceback=traceback.format_exc()))
        raise


# ------------------------------------------------------------ control equivalence

def reference_updates(seed, exp, updates):
    """`updates` updates driven by the REGISTERED functions, called directly.

    This is the comparison object for the control-equivalence proof: nothing in it comes
    from this file except the loop that `astra_canonical_operator_run.worker` also writes.
    Returns (per-update fingerprints, per-update answer losses).
    """
    params = configure_recipe(seed)
    forbidden, _exclusion = training_exclusion(exp)
    model = A.new_model(seed)
    assert model.parameters_count() == 79316
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
    assert params['blind_lines'] == 16
    return fingerprints, losses


def control_path_updates(seed, exp, updates):
    """The same `updates`, driven by THIS file's control path, measured identically."""
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
    return fingerprints, losses


def control_equivalence(seed, exp, updates=50, out=None):
    """Prove the control arm is the registered recipe, update by update.

    Two independent anchors are reported:
      * the INITIAL fingerprint against the registered grow-blind run on disk for this
        seed, when one exists (seeds 0-5) -- a fact about a file nobody here wrote;
      * `updates` updates of this file's control path against `reference_updates`,
        comparing the parameter fingerprint after EVERY update and the answer loss before
        every update.  Equal fingerprints are strictly stronger than equal losses.
    """
    mine, my_losses = control_path_updates(seed, exp, updates)
    theirs, their_losses = reference_updates(seed, exp, updates)
    first_difference = next((i for i, (a, b) in enumerate(zip(mine, theirs)) if a != b), None)
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
    result = dict(provenance(), seed=seed, updates=updates,
                  fingerprints_equal=mine == theirs,
                  first_differing_update=first_difference,
                  max_abs_loss_difference=max((abs(a-b) for a, b in
                                               zip(my_losses, their_losses)), default=0.),
                  losses_equal=my_losses == their_losses,
                  control_path_losses=my_losses,
                  registered_reference=registered,
                  final_fingerprint=mine[-1])
    if out:
        C.write_new(Path(out), result)
    print(json.dumps({k: v for k, v in result.items()
                      if k not in ('source_files', 'control_path_losses')}), flush=True)
    return result


def cmd_train(args):
    exp = Path(args.exp)
    if args.equivalence:
        return control_equivalence(args.seed, exp, args.equivalence, args.equivalence_out)
    return train_run(args.arm, args.seed, exp, updates=args.updates, out=args.out,
                     wave_start=args.wave_start, fixture_step0=args.fixture_step0)


# ====================================================================== scoring

def cell_programs(panel):
    """The side-'a' operation sequence per unit, in `score_cell`'s own record order.

    Model-free: `A.truth_paths` is the evaluator's own interpreter of the visible rows.
    """
    programs = []
    for sides in P.chunks(panel):
        x, _targets = sides['a']
        for path in A.truth_paths(x):
            programs.append([stage['operation'] for stage in path])
    return programs


def cell_diagnostics(panel, result):
    """Accuracy split by operation, for the two pre-named failure signatures."""
    programs = cell_programs(panel)
    records = result['records']
    assert len(programs) == len(records), (len(programs), len(records))
    by_first, one_hop = {}, {}
    for program, record in zip(programs, records):
        correct = record['correct']['R']
        key = str(program[0])
        row = by_first.setdefault(key, dict(n=0, R=0))
        row['n'] += 1
        row['R'] += int(correct)
        if len(program) == 1:
            row = one_hop.setdefault(key, dict(n=0, R=0))
            row['n'] += 1
            row['R'] += int(correct)
    side = result['diagnostics']['a']
    link_stage = None
    if side['native_links']:
        link_stage = dict(n=side['n'], correct=side['native_links'][0],
                          accuracy=side['native_links'][0]/side['n'],
                          note='stage-0 LINK lookup: a ONE-CALL link question, whatever the '
                               'depth of the cell')
    return dict(by_first_operation=by_first, one_call_by_operation=one_hop,
                first_link_stage=link_stage)


def score_model(model, exp, which_pool, pool=None, panels=None, wide=False,
                work_seconds=1e9):
    """The ten gated cells (and optionally the descriptive 64-person cells).

    Scoring is `astra_canonical_operator_run.score_cell`, imported and unmodified: the fixed
    loop `A.execute`, the single-forward `M` baseline and the gold-path oracle, on the FINAL
    checkpoint only.  The treatment binds this pool's per-world codes to each chunk first;
    the panel files are never touched, so the two treatment scorings run on byte-identical
    panels.
    """
    rows = panels if panels is not None else panel_paths(exp)
    treatment = isinstance(model, NewNamesOperator)
    subset = pool_subset(pool, which_pool) if treatment else None
    cells, started = {}, time.monotonic()
    for cell, row in rows.items():
        panel = load_panel(row)
        if treatment:
            model.clear_bindings()
            model.bind_panel(panel, lambda index, worlds, cell=cell: assign_codes(
                subset, f'{PANEL_CODE_NAMESPACE}:{which_pool}:{cell}:{index}',
                worlds, ENTITIES)[0])
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
    if treatment:
        model.clear_bindings()
    out = dict(cells=cells, pool=which_pool if treatment else None,
               seconds=round(time.monotonic()-started, 1))
    if wide and treatment:
        out['wide64'] = score_wide(model, exp, subset, which_pool)
    return out


def score_wide(model, exp, subset, which_pool):
    """The descriptive 64-person cells.  Treatment + reserved codes only, never gated."""
    summary = json.loads((Path(exp)/'panels/wide64.json').read_text())
    people = summary['people']
    out = {}
    with widened_entities(ENTITY_MIN+people):
        for name, row in summary['panels'].items():
            panel = load_panel(row)
            model.clear_bindings()
            model.bind_panel(panel, lambda index, worlds, name=name: assign_codes(
                subset, f'{PANEL_CODE_NAMESPACE}:{which_pool}:{name}:{index}',
                worlds, people)[0])
            result = R.score_cell(model, panel, time.monotonic(), 1e9)
            detail = {k: v for k, v in result.items() if k != 'records'}
            detail['diagnostics_by_operation'] = cell_diagnostics(panel, result)
            detail['panel_sha256'] = row['sha256']
            out[name] = detail
            print(json.dumps(dict(cell=name, pool=which_pool, people=people,
                                  R=result['R'], M=result['M'], n=result['n'])), flush=True)
            del result, panel
            gc.collect()
    model.clear_bindings()
    return dict(people=people, descriptive=True, cells=out)


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
    pool = load_pool(exp) if arm == 'treatment' else None
    rows = panel_paths(exp)
    scorings = {}
    if arm == 'control':
        scorings['control'] = score_model(model, exp, 'train', pool=None, panels=rows)
    else:
        for which in POOLS:
            scorings[which] = score_model(model, exp, which, pool=pool, panels=rows,
                                          wide=(which == 'reserved' and not args.skip_wide))
    payload = dict(provenance(), arm=arm, seed=saved['seed'], run=str(run.resolve()),
                   checkpoint=str(checkpoint.resolve()), checkpoint_sha256=sha,
                   final_fingerprint=saved['final_fingerprint'],
                   updates=saved['updates'], codes=saved.get('codes'),
                   pool_sha256=pool['summary']['sha256'] if pool else None,
                   cutoffs=CUTOFFS, cell_order=list(CELL_ORDER), scorings=scorings)
    C.write_new(out, payload)
    print(json.dumps(dict(arm=arm, seed=saved['seed'], out=str(out),
                          sha256=C.sha(out))), flush=True)
    return payload


# ====================================================================== gates

def seed_verdict(arm, scoring, reference=None):
    """Marks for one seed and one scoring.  `reference` is the paired training-pool run."""
    cells, marks = {}, []
    for cell in CELL_ORDER:
        row = scoring['cells'][cell]
        cutoff = CUTOFFS[cell]
        entry = dict(R=row['R'], M=row['M'], n=row['n'], cutoff=cutoff,
                     meets_cutoff=row['R'] >= cutoff)
        if reference is not None:
            paired = row['R']-reference['cells'][cell]['R']
            entry.update(paired_delta=paired,
                         meets_paired=paired >= -PAIRED_SLACK,
                         paired_slack=-PAIRED_SLACK)
        cells[cell] = entry
        marks.append(entry['meets_cutoff'] and entry.get('meets_paired', True))
    return dict(arm=arm, cells=cells, passed=all(marks),
                failed_cells=[c for c in CELL_ORDER
                              if not (cells[c]['meets_cutoff']
                                      and cells[c].get('meets_paired', True))])


def failure_signatures(scoring):
    """The two signatures named in advance, plus the raw split they are read from."""
    cells = scoring['cells']
    c1, c2 = cells['c1'], cells['c2']
    never_started = (c1['R'] <= NEVER_STARTED_AT*c1['n']
                     and c2['R'] <= NEVER_STARTED_AT*c2['n'])
    attribute = {}
    for cell in ('c1', 'p12-1'):
        for op, row in cells[cell]['diagnostics_by_operation']['one_call_by_operation'].items():
            key = f'{cell}/op{op}'
            attribute[key] = dict(row, accuracy=row['R']/row['n'])
    link = {}
    for cell in CELL_ORDER:
        stage = cells[cell]['diagnostics_by_operation']['first_link_stage']
        if stage:
            link[cell] = stage
    attribute_accuracies = [row['accuracy'] for key, row in attribute.items()
                            if not key.endswith(f'op{LINK}')]
    link_accuracies = [row['accuracy'] for row in link.values()]
    scale_bug = bool(attribute_accuracies and link_accuracies
                     and min(attribute_accuracies) >= ATTRIBUTES_FINE_AT
                     and max(link_accuracies) <= LINK_CHANCE_AT)
    return dict(never_started=bool(never_started),
                never_started_rule=f'c1 and c2 both <= {NEVER_STARTED_AT:.4f} (2x chance)',
                attributes_fine_link_at_chance=scale_bug,
                scale_bug_rule=f'every one-call attribute relation >= {ATTRIBUTES_FINE_AT} '
                               f'while every first-stage LINK <= {LINK_CHANCE_AT:.4f}',
                one_call_attribute_accuracy=attribute,
                first_stage_link_accuracy=link)


def collect_scores(exp):
    folder = Path(exp)/'scores'
    scores = {}
    for arm in ARMS:
        for seed in SEEDS:
            path = folder/f'{arm}-{seed}.json'
            if path.exists():
                scores[(arm, seed)] = json.loads(path.read_text())
    return scores


def gate_table(exp):
    scores = collect_scores(exp)
    missing = [f'{arm}-{seed}' for arm in ARMS for seed in SEEDS
               if (arm, seed) not in scores]
    control, treatment, signatures = {}, {}, {}
    for seed in SEEDS:
        row = scores.get(('control', seed))
        if row:
            control[seed] = seed_verdict('control', row['scorings']['control'])
            signatures[f'control-{seed}'] = failure_signatures(row['scorings']['control'])
        row = scores.get(('treatment', seed))
        if row:
            reserved, trained = row['scorings']['reserved'], row['scorings']['train']
            treatment[seed] = seed_verdict('treatment', reserved, reference=trained)
            treatment[seed]['training_pool'] = seed_verdict('treatment', trained)
            signatures[f'treatment-{seed}'] = failure_signatures(reserved)
            signatures[f'treatment-{seed}-train-pool'] = failure_signatures(trained)
    control_pass = sum(1 for v in control.values() if v['passed'])
    treatment_pass = sum(1 for v in treatment.values() if v['passed'])
    never_started = [name for name, sig in signatures.items()
                     if name.startswith('treatment') and sig['never_started']]
    scale_bug = [name for name, sig in signatures.items()
                 if name.startswith('treatment') and sig['attributes_fine_link_at_chance']]
    if missing:
        verdict, reason = 'INCOMPLETE', f'missing runs: {", ".join(missing)}'
    elif control_pass < 2:
        verdict, reason = 'VOID', 'recipe did not reproduce'
    elif treatment_pass == len(SEEDS):
        verdict, reason = 'PASS', f'{treatment_pass}/{len(SEEDS)} seeds'
    elif treatment_pass == 2:
        verdict, reason = 'PARTIAL', '2/3 seeds; reported as partial, no claim'
    else:
        verdict, reason = 'FAIL', f'{treatment_pass}/{len(SEEDS)} seeds'
    return dict(provenance(), seeds=list(SEEDS), cutoffs=CUTOFFS,
                paired_slack=-PAIRED_SLACK, missing=missing,
                control={str(k): v for k, v in control.items()},
                treatment={str(k): v for k, v in treatment.items()},
                control_seeds_passed=control_pass, treatment_seeds_passed=treatment_pass,
                verdict=verdict, reason=reason,
                signatures=signatures,
                signature_summary=dict(never_started=never_started,
                                       attributes_fine_link_at_chance=scale_bug),
                rules=dict(marks='reserved-code panels >= cutoff on every cell',
                           paired='reserved minus training-pool >= -13/512 on every cell',
                           control='>= 2/3 control seeds must meet their own marks, else '
                                   'VOID ("recipe did not reproduce")',
                           all_seed_pass='3/3', partial='2/3, no claim'))


def cmd_gates(args):
    exp = Path(args.exp)
    table = gate_table(exp)
    out = Path(args.out) if args.out else exp/'gates.json'
    if not out.exists():
        C.write_new(out, table)
    print(json.dumps({k: table[k] for k in
                      ('verdict', 'reason', 'control_seeds_passed',
                       'treatment_seeds_passed', 'missing', 'signature_summary')},
                     indent=2), flush=True)
    return table


# ====================================================================== report

def cmd_report(args):
    exp = Path(args.exp)
    table = gate_table(exp)
    scores = collect_scores(exp)
    lines = []
    add = lines.append
    add('# 21 / M1 "new names" -- reserved-code panels against the frozen grow-blind recipe')
    add('')
    add(f'source fingerprint  {table["source_fingerprint"]}')
    add(f'verdict             {table["verdict"]}  ({table["reason"]})')
    add(f'control seeds met their own marks   {table["control_seeds_passed"]}/{len(SEEDS)}')
    add(f'treatment seeds passed              {table["treatment_seeds_passed"]}/{len(SEEDS)}')
    add('')
    header = 'cell    cutoff  ' + '  '.join(f'{arm[:4]}-{seed}' for arm in ARMS
                                            for seed in SEEDS)
    add('## R (fixed loop) per cell; treatment columns are the RESERVED-code scoring')
    add(header)
    for cell in CELL_ORDER:
        row = [f'{cell:<7}', f'{CUTOFFS[cell]:>6}']
        for arm in ARMS:
            for seed in SEEDS:
                verdicts = table['control' if arm == 'control' else 'treatment']
                entry = verdicts.get(str(seed))
                row.append('     -' if not entry else
                           f'{entry["cells"][cell]["R"]:>6}')
        add('  '.join(row))
    add('')
    add('## paired reserved minus training-pool (mark: >= -13/512)')
    add('cell    ' + '  '.join(f'seed {s}' for s in SEEDS))
    for cell in CELL_ORDER:
        row = [f'{cell:<7}']
        for seed in SEEDS:
            entry = table['treatment'].get(str(seed))
            row.append('      -' if not entry else
                       f'{entry["cells"][cell].get("paired_delta", 0):>+7}')
        add('  '.join(row))
    add('')
    add('## pre-named failure signatures')
    for name, sig in sorted(table['signatures'].items()):
        add(f'{name}: never_started={sig["never_started"]} '
            f'attributes_fine_link_at_chance={sig["attributes_fine_link_at_chance"]}')
        attrs = sig['one_call_attribute_accuracy']
        if attrs:
            add('    one-call attribute accuracy  ' +
                '  '.join(f'{k}={v["accuracy"]:.3f}' for k, v in sorted(attrs.items())))
        links = sig['first_stage_link_accuracy']
        if links:
            add('    first-stage LINK accuracy    ' +
                '  '.join(f'{k}={v["accuracy"]:.3f}' for k, v in sorted(links.items())))
    wide = [(seed, row['scorings']['reserved'].get('wide64'))
            for (arm, seed), row in sorted(scores.items()) if arm == 'treatment']
    wide = [(seed, w) for seed, w in wide if w]
    if wide:
        add('')
        add('## descriptive extra, NOT gated: 64-person worlds (256 facts), reserved codes')
        for seed, w in wide:
            for name, cell in sorted(w['cells'].items()):
                add(f'seed {seed}  {name:<12} R={cell["R"]}/{cell["n"]} '
                    f'M={cell["M"]}/{cell["n"]}')
    text = '\n'.join(lines)+'\n'
    out = Path(args.out) if args.out else exp/'report.txt'
    if not out.exists():
        out.write_text(text)
    print(text, flush=True)
    return text


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

    p = sub.add_parser('pool', help='draw and freeze the 4,096-code pool')
    p.add_argument('--out', default=str(OUT))
    p.add_argument('--namespace', default=POOL_NAMESPACE,
                   help='FIXTURE USE ONLY: anything but the default draws a pool that is '
                        'not this experiment\'s registered one, and says so')

    p = sub.add_parser('panels', help='fresh ten-cell suite, 64-person cells, data audit')
    p.add_argument('--out', default=str(OUT))
    p.add_argument('--n', type=int, default=PANEL_N)
    p.add_argument('--namespace', default=PANEL_NAMESPACE,
                   help='FIXTURE USE ONLY: anything but the default builds panels that are '
                        'not this experiment\'s registered ones, and says so')
    p.add_argument('--seed-base', type=int, default=PANEL_SEED_BASE)
    p.add_argument('--wide-worlds', type=int, default=WIDE_WORLDS)
    p.add_argument('--audit-updates', type=int, default=100,
                   help='partial training-stream replay for the audit (0 disables)')
    p.add_argument('--skip-dev-audit', action='store_true',
                   help='skip the overlap audit against development panels (the audit is '
                        'then WEAKER and says so)')

    p = sub.add_parser('train', help='one run')
    p.add_argument('--exp', default=str(OUT))
    p.add_argument('--arm', choices=list(ARMS))
    p.add_argument('--seed', type=int, required=True)
    p.add_argument('--updates', type=int, default=UPDATES)
    p.add_argument('--out', default=None)
    p.add_argument('--wave-start', type=float, default=None)
    p.add_argument('--fixture-step0', type=int, default=0,
                   help='start the curriculum clock at this update (FIXTURE TIMING ONLY; '
                        'refused for the registered seeds)')
    p.add_argument('--equivalence', type=int, default=0,
                   help='instead of training: prove the control path reproduces the '
                        'registered recipe over N updates')
    p.add_argument('--equivalence-out', default=None)

    p = sub.add_parser('score', help='one checkpoint against the frozen panels')
    p.add_argument('--exp', default=str(OUT))
    p.add_argument('--arm', choices=list(ARMS))
    p.add_argument('--seed', type=int)
    p.add_argument('--run', default=None)
    p.add_argument('--out', default=None)
    p.add_argument('--skip-wide', action='store_true')

    p = sub.add_parser('gates', help='apply the registered marks')
    p.add_argument('--exp', default=str(OUT))
    p.add_argument('--out', default=None)

    p = sub.add_parser('report', help='human-readable tables')
    p.add_argument('--exp', default=str(OUT))
    p.add_argument('--out', default=None)

    p = sub.add_parser('fingerprint', help='sha256 of this file and every frozen module')
    p.add_argument('--out', default=None)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    configure_once()
    return dict(pool=cmd_pool, panels=cmd_panels, train=cmd_train, score=cmd_score,
                gates=cmd_gates, report=cmd_report,
                fingerprint=cmd_fingerprint)[args.command](args)


if __name__ == '__main__':
    main()
