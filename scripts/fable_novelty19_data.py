#!/usr/bin/env python3
"""novelty-19 DATA SIDE: the common awake stream, replay memory, R/G/U buffers and the
32 development panels of `design/v3/19-novelty-experiment-preregistration-draft.md`.

ADDITIVE ONLY.  Nothing here edits, deletes or re-hashes an existing file.  Every
generator is a thin wrapper around the already-frozen ones -- `fable_dispatcher_v3`
(worlds, rendering, questions, the independent interpreter, pair edits, panel audit),
`fable_baseline_transformer` (the training stream, step/line targets, packing) and
`fable_baseline_transformer_v2` (exclusion unions, registered stream settings).  This
file re-implements NO world, question, chain, target or audit logic.

-------------------------------------------------------------------------------
THE NEUTRAL RECORD SCHEMA
-------------------------------------------------------------------------------
One awake update (16 worlds x 4 questions) or one buffer world is stored as a
"block": a dict of tensors and plain lists, saved with `torch.save` inside a chunk
file.  A block is architecture-neutral: it stores the world rows and the raw question
exactly as the generators produced them, plus every derived target BOTH trainers need,
and nothing that is specific to either model.  `decode_block` turns it back into the
exact objects `fable_baseline_transformer.pack_batch` and
`astra_canonical_operator.data.pack` consume, so the SAME bytes drive D and T.

block = {
  'kind'            : str    'awake' | 'buffer-R' | 'buffer-G' | 'buffer-U'
  'seed'            : int    registered seed
  'index'           : int    update number (awake) or first world index (buffer chunk)
  'namespaces'      : list[str]            one frozen RNG namespace per world, in order
  'rows'            : uint8  [W, R, T]     visible story rows, 0 = pad (token 0 is unused
                                           by the grammar, so padding is reversible)
  'row_count'       : int16  [W]           real rows per world
  'owner'           : int16  [Q]           which world (0..W-1) each question belongs to
  'question'        : uint8  [Q, QW]       raw question tokens, 0 = pad
  'ops'             : uint8  [Q, C]        question[2:-1] = LINK*(c-1) + terminal, 0 = pad
  'calls'           : uint8  [Q]           c, the TOTAL primitive lookup calls (= `hops`)
  'terminal'        : uint8  [Q]           terminal attribute relation 8/9/10
  'start'           : uint8  [Q]           the asked person (entity token)
  'answer'          : uint8  [Q]           the gold final value token
  'people'          : uint8  [Q, C]        chain subjects, step by step, 0 = pad
  'chain_result'    : uint8  [Q, C]        chain results, step by step, 0 = pad
  'support'         : int16  [Q, C]        supporting visible-row index per step, -1 = pad
  'where'           : int16  [Q]           the dispatcher's question line inside `memory`
  'signature'       : uint8  [Q, 32]       A.visible_signature raw digest bytes
  'world_signature' : uint8  [W, 32]       CP.world_signature raw digest bytes
  'source'          : list[dict]           per question: provenance (awake: seed/update/
                                           slot; buffers: memory index + how it was made)
}

`decode_block(block)` returns a record:

record = {
  'kind', 'seed', 'index', 'namespaces', 'source'      -- as above
  'stories' : list[list[list[int]]]        W stories, each a list of rows (no pad)
  'memories': list[list[list[int]]]        the same rows + 4 empty question lines
  'items'   : list[dict(owner, question, chain, hops, terminal, answer, support,
                        where, start, signature, world_signature)]
}

`record['items']` is byte-for-byte what `fable_baseline_transformer.training_items`
returns (same keys, same types), so

    B1.pack_batch(record['stories'], record['items'], 'steps', support=True)

is the baseline batch, and

    A.data.pack(record['memories'], [it['question'] ...], [it['owner'] ...],
                [it['where'] ...])

is the dispatcher `Inputs` -- exactly as `V3.training_visits` builds it.  The helpers
`baseline_batch(record)` and `dispatcher_inputs(record)` do both; the tests prove they
equal what the frozen training code would have produced for the same world/question.

`hops` is kept as the item key because that is what every frozen consumer reads; the
spec's `c` is the same number and is stored as `calls` in the block.

-------------------------------------------------------------------------------
EXCLUSION FILES EVERY ARTIFACT PERSISTS
-------------------------------------------------------------------------------
Section 7 asks the confirmation suite to exclude "all training, candidate-generation
and replay WORLDS, not merely accepted training questions".  So every generated
artifact folder writes BOTH levels, in the same format the frozen panels use:

  forbidden-semantics.json   sorted list of `A.visible_signature` question signatures
  forbidden-worlds.json      sorted list of `CP.world_signature` world signatures

written by `awake-stream`, `memory`, `buffers`, `dev-panels` and `operator-history`.
`dev-panels` additionally writes `forbidden-worlds-primary.json`, the world signatures
of the N and E cells alone; `awake-stream` and `buffers` REFUSE to emit any world in
that set, so the primary cells' worlds can never enter training material.

Each producer also records, in its own `manifest.json` (`index.json` for the awake
stream), a `published_exclusions` block holding the sha256 AND the entry count of every
file it published.  EVERY consumer -- the development and confirmation panel builds,
the training builders and `audit` -- re-hashes and re-counts each file it reads against
that block and REFUSES on any mismatch, so a truncated or edited exclusion file cannot
silently narrow the union (the auditor cut a buffer's world file from 1,024 entries to
5 and the confirmation build accepted it).  The panel manifests record every source
they consumed, with the sha256 it was verified at, under `consumed_exclusions`.

-------------------------------------------------------------------------------
DEV-PASSED.json -- the confirmation lockout
-------------------------------------------------------------------------------
`dev-panels --confirmation` refuses unless `<experiment>/DEV-PASSED.json` exists, is
non-empty, parses, and has exactly this shape (the report tool writes it):

{
  "schema": "novelty19-dev-passed-v1",
  "seeds": [1900, 1901, 1902],
  "report_sha256": "<64 hex: sha256 of the development report.json>",
  "dev_panels": {"path": "<folder>", "manifest_sha256": "<64 hex>"},
  "awake_checkpoints":   {"D-1900": "<64 hex>", ... 6 entries: {D,T} x 3 seeds},
  "offline_checkpoints": {"D-G-1900": "<64 hex>", ... 18 entries: {D,T} x {R,G,U} x 3}
}

Every hash must be 64 lowercase hex characters, the seed list must be exactly the
registered seeds, the six awake and eighteen offline keys must all be present, and
`dev_panels.manifest_sha256` must equal the sha256 of the development panel manifest
ON DISK.  Anything else refuses.

-------------------------------------------------------------------------------
HASH-STABLE MANIFESTS
-------------------------------------------------------------------------------
No wall-clock value is written into a hashed document.  `created_unix`, `seconds` and
the like go into a `<name>.meta.json` sidecar, so two identical runs produce identical
`index.json` / `manifest.json` / `audit.json` bytes.  Every manifest carries the same
`execution_profile` (CPython version, torch version, platform, source sha256s); `audit`
fails if two manifests inside one experiment disagree.

-------------------------------------------------------------------------------
EXPERIMENT LAYOUT AND GENERATION ORDER
-------------------------------------------------------------------------------
One experiment folder holds everything under fixed names, so `--confirmation
--experiment <folder>` finds all of it without further flags:

  <experiment>/operator-history/        the section-7 provenance reconstruction
  <experiment>/dev-panels/              the 32 development cells
  <experiment>/awake-<seed>/            the per-seed awake stream (3 seeds)
  <experiment>/memory-<seed>/           the 1,024 remembered worlds + 6x6 table
  <experiment>/buffers-<seed>/          the R, G and U buffers
  <experiment>/DEV-PASSED.json          written only after development passes

The order is forced by the exclusions: `operator-history` first (ruling 2 makes it a
freeze prerequisite), then `dev-panels`, then `awake-stream` -> `memory` -> `buffers`
per seed, then `audit`.  `design/v3/19-rulings-1.md` is part of the spec; rulings 1, 2,
3, 4, 5 and 6 are implemented here and cited at the code that implements them.

-------------------------------------------------------------------------------
SUBCOMMANDS
-------------------------------------------------------------------------------
  awake-stream      spec section 2 -- the common per-seed awake data stream
  memory            spec section 3 -- first 1,024 distinct worlds + the 6x6 count table
  buffers           spec section 4 -- the R, G and U buffers + section 5 generation gate
  dev-panels        spec section 6 -- the 32 development cells, v3 panel JSON format
  operator-history  spec section 7 -- the frozen operator's historical training worlds
                    and question signatures, reconstructed WITHOUT model forwards
  audit             re-verify every artifact from disk and print one JSON verdict
"""

import argparse
import copy
import hashlib
import json
import math
import platform
import random
import re
import time
from contextlib import contextmanager
from pathlib import Path

import fable_dispatcher as V1
import fable_dispatcher_v3 as V3
import fable_dispatcher_v4 as V4
import fable_baseline_transformer as B1
import fable_baseline_transformer_v2 as B2
import fable_confirmation_panels as CP

A = V3.A
torch = V3.torch
sha = V3.sha
write_new = V3.write_new
configure = V3.configure

QUESTION, ANSWER, WORLD, LINK = V3.QUESTION, V3.ANSWER, V3.WORLD, V3.LINK
NEWLINE = V3.NEWLINE
FIRST_REL, RELATIONS, VALUES = V3.FIRST_REL, V3.RELATIONS, V3.VALUES
HELDOUT_REL = V3.HELDOUT_REL                      # 10
PRACTISED_RELS = V3.PRACTISED_RELS                # (8, 9)
ENTITY_MIN, ENTITY_MAX = V3.ENTITY_MIN, V3.ENTITY_MAX
VALUE_MIN = FIRST_REL + RELATIONS + 1             # 12
VALUE_COUNT = VALUES                              # 16
PANEL_N = V3.PANEL_N                              # 64
PANEL_PEOPLE = V3.PANEL_PEOPLE                    # 16
TRAIN_PEOPLE = V3.TRAIN_PEOPLE                    # 6

WORKTREE = Path(__file__).resolve().parent.parent

# ---- frozen registered numbers, section 2/3/4/6/7.  DO NOT CHANGE. ----------
REGISTERED_SEEDS = (1900, 1901, 1902)
AWAKE_UPDATES = 6000
AWAKE_VISITS = 16                                 # six-person worlds per update
AWAKE_QUESTIONS_PER_WORLD = 4
AWAKE_PEOPLE = TRAIN_PEOPLE                       # 6
AWAKE_CALLS = (1, 2, 3)                           # c uniform 1..3
MEMORY_WORLDS = 1024
BUFFER_QUESTIONS_PER_WORLD = 4
CANDIDATES_PER_WORLD = 64                         # "exactly 64 independent candidates"
MAX_DRAWS_AFTER_BOS = 7                           # "a maximum of seven draws after BOS"
MAX_BUFFER_CALLS = 5                              # "rejecting any string with > 5 calls"
UNIFORM_CALLS = (1, 2, 3, 4, 5)                   # U: c uniform 1..5
OFFLINE_UPDATES = 2000
OFFLINE_VISITS = 16
AWAKE_CHUNK = 750                                 # section 9 resumable chunk sizes
OFFLINE_CHUNK = 500
GENERATION_GATE_STRUCTURES = ((4, 8), (4, 9), (5, 8), (5, 9))
GENERATION_GATE_MIN = 16                          # >= 16 distinct questions in >= 16 worlds
DEV_N = PANEL_N                                   # 64 units per development cell
CONFIRM_N = 512
DEV_ATTEMPTS = 10_000                             # section 7's "at most 10,000 attempts/unit"

# Ruling 1 of design/v3/19-rulings-1.md (RATIFIED, not pending): a "distinct question"
# is a distinct (question-free world signature, full raw question tokens) INSTANCE.
# Both readings are always reported; this constant alone decides the gate, so changing
# the ruling is a one-line change here.
GATE_READING = 'instances'                        # or 'raw_tokens'
assert GATE_READING in ('instances', 'raw_tokens')

# Section 7's operator-history provenance wave, re-implemented from the archived
# driver (`scripts/astra_canonical_operator_run.py:worker`): ONE sequential
# `random.Random(1101)`, 6,000 updates x 16 `toy_ladder.visit(..., training=True)`,
# then one `rng.randrange(1 << 30)` per update.  No model forward is involved.
OPERATOR_HISTORY_RNG_SEED = 1101
OPERATOR_HISTORY_UPDATES = 6000
OPERATOR_HISTORY_VISITS = 16
OPERATOR_HISTORY_WORLD_UNION_SHA256 = (
    '0730f99e6e627fa00db03cef5919b814599dfacb3a299a8ded440d28f0dc900a')

# Confirmation lockout (see the module docstring for the full DEV-PASSED.json schema).
DEV_PASSED_SCHEMA = 'novelty19-dev-passed-v1'
ARCHITECTURES = ('D', 'T')                        # dispatcher v4 reg+ctx, baseline v2 I1-H1
ARMS = ('R', 'G', 'U')
AWAKE_CHECKPOINT_KEYS = tuple(f'{a}-{s}' for a in ARCHITECTURES for s in REGISTERED_SEEDS)
OFFLINE_CHECKPOINT_KEYS = tuple(f'{a}-{m}-{s}' for a in ARCHITECTURES for m in ARMS
                                for s in REGISTERED_SEEDS)
HEX64 = re.compile(r'^[0-9a-f]{64}$')


def checkpoint_keys(stage, seeds=REGISTERED_SEEDS):
    """The six awake / eighteen offline checkpoint names DEV-PASSED.json must carry."""
    if stage == 'awake':
        return tuple(f'{a}-{s}' for a in ARCHITECTURES for s in seeds)
    return tuple(f'{a}-{m}-{s}' for a in ARCHITECTURES for m in ARMS for s in seeds)

# One experiment folder holds every artifact under these fixed names, so
# `--confirmation --experiment <folder>` can find all of them without further flags.
EXPERIMENT_LAYOUT = dict(stream='awake-{seed}', memory='memory-{seed}',
                         buffers='buffers-{seed}', dev_panels='dev-panels',
                         operator_history='operator-history')

FORBIDDEN_QUESTIONS = 'forbidden-semantics.json'
FORBIDDEN_WORLDS = 'forbidden-worlds.json'
FORBIDDEN_PRIMARY_WORLDS = 'forbidden-worlds-primary.json'
PRIMARY_FAMILIES = ('N', 'E')                     # the never-trained cells and their twins
# the manifest a producer writes beside its exclusion files; a consumer verifies every
# file it reads against the sha256 and entry count recorded here (audit R2-7)
ARTIFACT_MANIFESTS = ('manifest.json', 'index.json')

NS_AWAKE = 'astra-novelty19-awake-v1'
NS_PROPOSE = 'astra-novelty19-propose-v1'
NS_BIND = 'astra-novelty19-bind-v1'
NS_UNIFORM = 'astra-novelty19-uniform-v1'
NS_ORDER = 'astra-novelty19-offline-order-v1'
NS_DEV = 'astra-novelty19-dev-v1'
NS_CONFIRM = 'astra-novelty19-confirm-v1'

# the transition alphabet of section 3, in the frozen 6x6 row/column order
ALPHABET = ('BOS', 'LINK', '8', '9', '10', 'EOS')
ALPHABET_INDEX = {name: i for i, name in enumerate(ALPHABET)}
TOKEN_OF = {'LINK': LINK, '8': FIRST_REL, '9': FIRST_REL + 1, '10': HELDOUT_REL}
NAME_OF = {v: k for k, v in TOKEN_OF.items()}

# the legacy exclusion sources of section 7.  The v3 development panels, both
# baseline-v2 panels and both fresh confirmation suites.  The superseded
# `fable-dispatcher-pilot-20260920` panels are NOT part of the registered union
# (pass them with --extra-exclusion to widen it); missing files abort.
LEGACY_EXCLUSIONS = (
    'artifacts/fable-dispatcher-v3-20260920/panels/forbidden-semantics.json',
    'artifacts/fable-baseline-transformer-v2-20260920/fit-panels/forbidden-semantics.json',
    'artifacts/fable-baseline-transformer-v2-20260920/confirm-panels/forbidden-semantics.json',
    'artifacts/fable-confirmation-panels-20260920/dispatcher/forbidden-semantics.json',
    'artifacts/fable-confirmation-panels-20260920/operator/forbidden-semantics.json',
)

DEV_SEED_FLOOR = B2.DEV_SEED_FLOOR                # 990100; fixtures live at/above it


def fingerprint():
    """Every source this module's output depends on."""
    return dict(novelty19_data=sha(__file__), dispatcher_v3=sha(V3.__file__),
                dispatcher_v4=sha(V4.__file__), dispatcher_v1=sha(V1.__file__),
                baseline=sha(B1.__file__), baseline_v2=sha(B2.__file__),
                confirmation_panels=sha(CP.__file__), canonical_operator=sha(A.__file__),
                torch=torch.__version__)


def digest_of(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def hex_rows(tensor):
    return [bytes(row).hex() for row in tensor.tolist()]


def sha_bytes(path):
    return sha(Path(path))


def execution_profile():
    """The interpreter/machine facts every manifest of one experiment must share."""
    return dict(python=platform.python_version(),
                implementation=platform.python_implementation(),
                torch=torch.__version__,
                platform=platform.platform(),
                machine=platform.machine(),
                script_sha256=sha(__file__),
                sources=fingerprint())


def write_doc(path, value, **wall_clock):
    """Write a HASH-STABLE JSON document plus a `<name>.meta.json` wall-clock sidecar.

    Nothing time-dependent may go into a hashed document: two identical runs must
    produce identical `index.json` / `manifest.json` / `audit.json` bytes, so
    `created_unix`, `seconds` and friends live in the sidecar instead.
    """
    path = Path(path)
    write_new(path, value)
    write_new(path.with_name(path.stem + '.meta.json'),
              dict(created_unix=time.time(), **wall_clock))
    return sha(path)


def read_meta(path):
    """The wall-clock sidecar of a hashed document, if one was written."""
    side = Path(path).with_name(Path(path).stem + '.meta.json')
    return json.loads(side.read_text()) if side.exists() else None


# =========================================================================== signature files


def block_signatures(blocks):
    """(question signatures, world signatures) of a list of encoded blocks."""
    questions, worlds = set(), set()
    for block in blocks:
        for row in block['signature'].tolist():
            questions.add(bytes(row).hex())
        for row in block['world_signature'].tolist():
            worlds.add(bytes(row).hex())
    return questions, worlds


def chunk_signatures(path):
    _, blocks = load_chunk(path)
    return block_signatures(blocks)


def write_forbidden(folder, questions, worlds, *, primary_worlds=None):
    """Persist BOTH exclusion levels section 7 asks for, next to the artifact.

    Section 7 wants "all training, candidate-generation and replay WORLDS, not merely
    accepted training questions" excluded from the evaluation suites, so every producer
    writes its question signatures AND its question-free world signatures.
    """
    folder = Path(folder)
    questions, worlds = sorted(questions), sorted(worlds)
    record = dict(
        questions=len(questions), worlds=len(worlds),
        questions_path=str(folder / FORBIDDEN_QUESTIONS),
        questions_sha256=write_doc(folder / FORBIDDEN_QUESTIONS, questions),
        worlds_path=str(folder / FORBIDDEN_WORLDS),
        worlds_sha256=write_doc(folder / FORBIDDEN_WORLDS, worlds))
    if primary_worlds is not None:
        primary = sorted(primary_worlds)
        record.update(primary_worlds=len(primary),
                      primary_worlds_path=str(folder / FORBIDDEN_PRIMARY_WORLDS),
                      primary_worlds_sha256=write_doc(
                          folder / FORBIDDEN_PRIMARY_WORLDS, primary))
    return record


def artifact_manifest(folder):
    """(path, document) of the manifest that PRODUCED an artifact folder.

    Every producer writes exactly one of these next to its exclusion files: the awake
    stream writes `index.json`, everything else writes `manifest.json`.  An exclusion
    file whose producing manifest is absent cannot be verified, so it is refused.
    """
    folder = Path(folder)
    for name in ARTIFACT_MANIFESTS:
        path = folder / name
        if not path.exists():
            continue
        try:
            doc = json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            raise SystemExit(f'malformed artifact manifest at {path}: {exc}') from None
        if not isinstance(doc, dict):
            raise SystemExit(f'artifact manifest at {path} is not a JSON object')
        return path, doc
    raise SystemExit(f'no artifact manifest ({" or ".join(ARTIFACT_MANIFESTS)}) in '
                     f'{folder}: an exclusion file without the manifest that produced '
                     f'it cannot be verified, so it may not be consumed')


def published_exclusion_record(folder):
    """The `published_exclusions` block the producing manifest recorded.

    This is the anchor the consumer checks its file against: it carries the sha256 AND
    the entry count of every exclusion file the artifact published.
    """
    path, manifest = artifact_manifest(folder)
    published = manifest.get('published_exclusions')
    if not isinstance(published, dict) or not published:
        raise SystemExit(f'{path} records no published_exclusions; its exclusion files '
                         f'cannot be verified and may not be consumed')
    for key in ('questions', 'questions_sha256', 'worlds', 'worlds_sha256'):
        if published.get(key) in (None, ''):
            raise SystemExit(f'{path} published_exclusions has no {key}; '
                             f'the exclusion files cannot be verified')
    return path, published


def read_signature_file(path, *, what='signatures', expect_sha256=None,
                        expect_count=None, source=None):
    """A sorted JSON list of 64-hex signatures.  Empty or malformed REFUSES.

    When the producing manifest is known (`expect_sha256` / `expect_count`, with
    `source` naming that manifest) the file is ALSO hashed and counted on read, so a
    truncated or edited exclusion file is refused instead of silently narrowing the
    union.  Shape alone is not enough: the auditor cut a buffer's 1,024 world
    signatures down to 5 and the confirmation build accepted the file.
    """
    path = Path(path)
    if not path.exists():
        raise SystemExit(f'missing {what} file at {path}')
    if path.stat().st_size == 0:
        raise SystemExit(f'empty {what} file at {path}')
    try:
        value = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise SystemExit(f'malformed {what} file at {path}: {exc}') from None
    if not isinstance(value, list) or not value:
        raise SystemExit(f'{what} file at {path} is not a non-empty list')
    bad = [v for v in value if not (isinstance(v, str) and HEX64.match(v))]
    if bad:
        raise SystemExit(f'{what} file at {path} holds {len(bad)} non-signature entries')
    if value != sorted(set(value)):
        raise SystemExit(f'{what} file at {path} is not a sorted list of distinct '
                         f'signatures; refusing a rewritten exclusion file')
    if expect_count is not None and len(value) != int(expect_count):
        raise SystemExit(
            f'{what} file at {path} holds {len(value)} entries but '
            f'{source or "its manifest"} records {int(expect_count)}; refusing a '
            f'truncated or padded exclusion file')
    if expect_sha256 is not None:
        on_disk = sha(path)
        if on_disk != expect_sha256:
            raise SystemExit(
                f'{what} file at {path} hashes to {on_disk} but '
                f'{source or "its manifest"} records {expect_sha256}; refusing a '
                f'tampered exclusion file')
    return frozenset(value)


def artifact_exclusions(folder, *, worlds=True, questions=True, primary=False,
                        verify=True):
    """The forbidden question/world sets an artifact folder published, VERIFIED.

    Every consumer goes through here, and every read is checked against the sha256 and
    entry count in the producing artifact's own manifest (audit re-check 2, R2-7).
    `out['record']` is the provenance the consumer writes into its own manifest.
    """
    folder = Path(folder)
    published, source = {}, None
    if verify:
        manifest_path, published = published_exclusion_record(folder)
        source = str(manifest_path.resolve())
    out = {}
    record = dict(path=str(folder.resolve()), manifest=source, verified=bool(verify))
    wanted = [(questions, 'questions', FORBIDDEN_QUESTIONS, 'forbidden-question'),
              (worlds, 'worlds', FORBIDDEN_WORLDS, 'forbidden-world'),
              (primary, 'primary_worlds', FORBIDDEN_PRIMARY_WORLDS,
               'forbidden-primary-world')]
    for take, key, name, what in wanted:
        if not take:
            continue
        if verify and published.get(f'{key}_sha256') in (None, ''):
            raise SystemExit(f'{source} records no published_exclusions.{key}_sha256; '
                             f'{folder / name} cannot be verified and may not be used')
        out[key] = read_signature_file(
            folder / name, what=what, expect_sha256=published.get(f'{key}_sha256'),
            expect_count=published.get(key), source=source)
        record[key] = len(out[key])
        record[f'{key}_sha256'] = published.get(f'{key}_sha256') or sha(folder / name)
    out['record'] = record
    return out


# =========================================================================== blocks


def _pad(values, width, fill=0, dtype=None):
    out = torch.full((len(values), width), fill, dtype=dtype)
    for i, row in enumerate(values):
        if len(row):
            out[i, :len(row)] = torch.tensor(list(row), dtype=dtype)
    return out


def encode_block(kind, seed, index, namespaces, stories, items, source):
    """Stories + `training_items`-shaped items -> the neutral on-disk block.

    Token 0 never occurs inside the grammar (rows use 3, 7, 8..11, 12..27, 28..51,
    52..67 and questions 4, 5, 8..11, 52..67), so zero padding is losslessly
    reversible via `row_count` and the per-row zero cut.
    """
    rows_n = max(len(s) for s in stories)
    width = max(max(len(r) for r in s) for s in stories)
    rows = torch.zeros(len(stories), rows_n, width, dtype=torch.uint8)
    for i, story in enumerate(stories):
        for j, row in enumerate(story):
            rows[i, j, :len(row)] = torch.tensor(row, dtype=torch.uint8)
    calls = [len(it['chain']) for it in items]
    cmax = max(calls)
    facts = [CP.fact_tuples(story) for story in stories]
    block = {}
    block['kind'] = kind
    block['seed'] = int(seed)
    block['index'] = int(index)
    block['namespaces'] = list(namespaces)
    block['rows'] = rows
    block['row_count'] = torch.tensor([len(s) for s in stories], dtype=torch.int16)
    block['owner'] = torch.tensor([it['owner'] for it in items], dtype=torch.int16)
    block['question'] = _pad([it['question'] for it in items],
                             max(len(it['question']) for it in items), dtype=torch.uint8)
    block['ops'] = _pad([it['question'][2:-1] for it in items], cmax, dtype=torch.uint8)
    block['calls'] = torch.tensor(calls, dtype=torch.uint8)
    block['terminal'] = torch.tensor([it['terminal'] for it in items], dtype=torch.uint8)
    block['start'] = torch.tensor([it['question'][1] for it in items], dtype=torch.uint8)
    block['answer'] = torch.tensor([it['answer'] for it in items], dtype=torch.uint8)
    block['people'] = _pad([[step[0] for step in it['chain']] for it in items], cmax,
                           dtype=torch.uint8)
    block['chain_result'] = _pad([[step[2] for step in it['chain']] for it in items], cmax,
                                 dtype=torch.uint8)
    block['support'] = _pad([it['support'] for it in items], cmax, fill=-1, dtype=torch.int16)
    block['where'] = torch.tensor([it['where'] for it in items], dtype=torch.int16)
    block['signature'] = torch.tensor(
        [list(bytes.fromhex(A.visible_signature(stories[it['owner']], it['question'])))
         for it in items], dtype=torch.uint8)
    block['world_signature'] = torch.tensor(
        [list(bytes.fromhex(CP.world_signature(f))) for f in facts], dtype=torch.uint8)
    block['source'] = list(source)
    return block


def decode_block(block):
    """The neutral block -> exactly the objects the two frozen trainers consume."""
    counts = block['row_count'].tolist()
    stories = []
    for i, n in enumerate(counts):
        story = []
        for j in range(n):
            row = block['rows'][i, j].tolist()
            while row and row[-1] == 0:
                row.pop()
            story.append(row)
        stories.append(story)
    owners = block['owner'].tolist()
    per_owner = {}
    for owner in owners:
        per_owner[owner] = per_owner.get(owner, 0) + 1
    qpw = len(owners) // max(1, len(stories))
    # the questions-per-world division must be exact and uniform: a ragged block would
    # silently mis-size every memory below, so refuse it rather than decode it wrongly
    assert len(owners) == qpw * len(stories), 'block items do not divide among its stories'
    assert set(per_owner.values()) <= {qpw}, 'block owners are not uniformly distributed'
    memories = [[list(row) for row in story] + [[] for _ in range(qpw)] for story in stories]
    items = []
    for q in range(block['owner'].shape[0]):
        c = int(block['calls'][q])
        question = [t for t in block['question'][q].tolist() if t]
        chain = [[int(block['people'][q, s]), int(block['ops'][q, s]),
                  int(block['chain_result'][q, s])] for s in range(c)]
        items.append(dict(owner=int(block['owner'][q]), question=question, chain=chain,
                          hops=c, terminal=int(block['terminal'][q]),
                          answer=int(block['answer'][q]),
                          support=[int(v) for v in block['support'][q].tolist()[:c]],
                          where=int(block['where'][q]), start=int(block['start'][q]),
                          signature=bytes(block['signature'][q].tolist()).hex(),
                          world_signature=bytes(
                              block['world_signature'][int(block['owner'][q])].tolist()).hex()))
    return dict(kind=block['kind'], seed=block['seed'], index=block['index'],
                namespaces=list(block['namespaces']), source=list(block['source']),
                stories=stories, memories=memories, items=items)


def training_item_view(record):
    """`(stories, items)` in EXACTLY `B1.training_items`' shape -- extra keys dropped."""
    keys = ('owner', 'question', 'chain', 'hops', 'terminal', 'answer', 'support')
    return record['stories'], [{k: it[k] for k in keys} for it in record['items']]


def baseline_batch(record, mode='steps', support=True):
    stories, items = training_item_view(record)
    return B1.pack_batch(stories, items, mode, support=support)


def dispatcher_inputs(record):
    """`A.data.pack` exactly as `V3.training_visits` calls it."""
    items = record['items']
    return A.data.pack(record['memories'], [it['question'] for it in items],
                       [it['owner'] for it in items], [it['where'] for it in items])


def merge_records(records):
    """Concatenate several blocks' records, renumbering owners into one flat batch."""
    stories, memories, items, namespaces, source = [], [], [], [], []
    for rec in records:
        shift = len(stories)
        stories.extend(rec['stories'])
        memories.extend(rec['memories'])
        namespaces.extend(rec['namespaces'])
        source.extend(rec['source'])
        for it in rec['items']:
            moved = dict(it)
            moved['owner'] = it['owner'] + shift
            items.append(moved)
    return dict(kind=records[0]['kind'] if records else None,
                seed=records[0]['seed'] if records else None, index=None,
                namespaces=namespaces, source=source, stories=stories, memories=memories,
                items=items)


def save_chunk(path, blocks, meta):
    """`torch.save` a chunk of blocks.  New file only; refuses to overwrite."""
    path = Path(path)
    if path.exists():
        raise SystemExit(f'refusing to overwrite {path}')
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(dict(meta=meta, blocks=blocks), path)
    return sha(path)


def load_chunk(path):
    payload = torch.load(Path(path), weights_only=False)
    return payload['meta'], payload['blocks']


# =========================================================================== exclusions


def legacy_exclusion_paths(extra=()):
    paths = [WORKTREE / rel for rel in LEGACY_EXCLUSIONS]
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        raise SystemExit('missing legacy exclusion source(s): ' + ', '.join(missing))
    return paths + [Path(p) for p in extra]


def build_exclusion_union(dev_panels, extra=()):
    """Legacy union (section 7) plus the new development panels.

    `dev_panels` is MANDATORY for every training artifact: without it the collision
    abort is not armed, and a run that never checked cannot claim disjointness.  A
    missing source ABORTS for the same reason.
    """
    paths = legacy_exclusion_paths(extra)
    if dev_panels is None:
        raise SystemExit('--dev-panels is required: the exclusion collision abort must '
                         'always be armed (see design/v3/19-rulings-1.md, ruling 2)')
    dev = Path(dev_panels)
    panel_record = None
    if dev.is_dir():
        # verify the panel file against the manifest that published it before using it
        panel_record = artifact_exclusions(dev, worlds=False)['record']
        dev = dev / FORBIDDEN_QUESTIONS
    if not dev.exists():
        raise SystemExit(f'missing development-panel exclusion at {dev}')
    paths.append(dev)
    # B2's record already lists every source path with its sha256 and count; the panel
    # record adds the producing manifest those hashes were verified against
    union, record = B2.exclusion_union([str(p) for p in paths])
    record['dev_panel_source'] = panel_record
    return union, record


def primary_world_exclusion(dev_panels):
    """The world signatures of the PRIMARY (N and E) development cells.

    Section 7 excludes evaluation worlds from training material, not only evaluation
    questions.  No awake or replay world may equal one of these, and a collision
    invalidates the run rather than being skipped.  The auditor measured zero overlap;
    this makes it enforced instead of merely observed.
    """
    folder = Path(dev_panels)
    path = folder / FORBIDDEN_PRIMARY_WORLDS
    sets = artifact_exclusions(folder, worlds=False, questions=False, primary=True)
    worlds = sets['primary_worlds']
    return worlds, dict(path=str(path.resolve()), sha256=sha(path), count=len(worlds),
                        source=sets['record'])


def assert_worlds_allowed(blocks, primary_worlds, where):
    """Abort if any generated world equals a primary evaluation world."""
    if not primary_worlds:
        return 0
    checked = 0
    for block in blocks:
        for i, row in enumerate(block['world_signature'].tolist()):
            checked += 1
            if bytes(row).hex() in primary_worlds:
                raise RuntimeError(
                    f'{where}: world slot {i} of block {block["index"]} equals a primary '
                    f'development world; the run is invalid (section 7 world exclusion)')
    return checked


# =========================================================================== awake stream


def awake_namespace(seed, update, slot):
    return f'{NS_AWAKE}:{seed}:{update}:{slot}'


def awake_update(seed, update, forbidden=frozenset(), *, visits=AWAKE_VISITS,
                 people=AWAKE_PEOPLE, calls=AWAKE_CALLS,
                 questions_per_world=AWAKE_QUESTIONS_PER_WORLD):
    """ONE awake update: `visits` worlds x `questions_per_world` questions.

    Each world slot gets its OWN frozen RNG (section 7's
    `astra-novelty19-awake-v1:<seed>:<update>:<world-slot>`), so any update is
    reproducible on its own and a chunked run is bit-identical to an unchunked one.
    The world/question draw itself is `B1.training_items` verbatim -- which consumes
    its RNG in exactly the same order as `V3.training_visits`, and which RAISES on any
    collision with `forbidden` rather than skipping it (section 7's integrity rule).
    """
    stories, items, namespaces, source = [], [], [], []
    for slot in range(visits):
        namespace = awake_namespace(seed, update, slot)
        rng = random.Random(namespace)
        got_stories, got_items = B1.training_items(
            rng, visits=1, people=people, hops_choices=calls, forbidden=forbidden,
            questions_per_world=questions_per_world, support=True)
        assert len(got_stories) == 1 and len(got_items) == questions_per_world
        rows = got_stories[0]
        stories.append(rows)
        namespaces.append(namespace)
        for j, item in enumerate(got_items):
            item = dict(item)
            item['owner'] = slot
            item['where'] = len(rows) + j
            items.append(item)
            source.append(dict(namespace=namespace, seed=int(seed), update=int(update),
                               slot=slot, question_index=j))
    return stories, items, namespaces, source


def awake_block(seed, update, forbidden=frozenset(), **kw):
    stories, items, namespaces, source = awake_update(seed, update, forbidden, **kw)
    return encode_block('awake', seed, update, namespaces, stories, items, source)


def awake_chunk_name(start, end):
    return f'awake-{start:06d}-{end:06d}.pt'


def build_awake_stream(out, seed, updates, *, dev_panels, start=0, chunk=AWAKE_CHUNK,
                       extra_exclusion=(), visits=AWAKE_VISITS, people=AWAKE_PEOPLE,
                       questions_per_world=AWAKE_QUESTIONS_PER_WORLD, budget=None,
                       progress=False):
    """Materialise updates [start, updates) into resumable chunk files + index.json.

    Re-runnable: an existing, hash-matching chunk is kept and skipped, so a wave that
    hits its deadline resumes at the exact next update.  `index.json` is written only
    once every chunk of the full [0, updates) range is present on disk, and the
    forbidden-semantics / forbidden-worlds files this stream publishes are written with
    it -- so a partial stream can never be mistaken for a complete exclusion source.

    `dev_panels` is mandatory at BOTH levels: accepted questions collide against the
    panel question signatures (`B1.training_items` raises), and generated worlds
    collide against the primary (N/E) panel world signatures.
    """
    configure()
    folder = Path(out)
    folder.mkdir(parents=True, exist_ok=True)
    forbidden, exclusion_record = build_exclusion_union(dev_panels, extra_exclusion)
    primary_worlds, primary_record = primary_world_exclusion(dev_panels)
    began = time.time()
    written, skipped = [], []
    bounds = [(s, min(s + chunk, updates)) for s in range(0, updates, chunk)]
    for lo, hi in bounds:
        if hi <= start:
            continue
        path = folder / awake_chunk_name(lo, hi)
        if path.exists():
            skipped.append(path.name)
            continue
        # a wave always makes progress: the budget can end a run, never empty it
        if budget is not None and written and time.time() - began > budget:
            break
        blocks = [awake_block(seed, u, forbidden, visits=visits, people=people,
                              questions_per_world=questions_per_world)
                  for u in range(lo, hi)]
        assert_worlds_allowed(blocks, primary_worlds, f'awake stream {folder.name}')
        meta = dict(kind='awake', seed=int(seed), start=lo, end=hi, visits=visits,
                    people=people, questions_per_world=questions_per_world,
                    calls=list(AWAKE_CALLS), namespace=NS_AWAKE,
                    exclusion_sha256=exclusion_record['union_sha256'],
                    primary_world_exclusion_sha256=primary_record['sha256'],
                    execution_profile=execution_profile(), fingerprint=fingerprint())
        save_chunk(path, blocks, meta)
        written.append(path.name)
        if progress:
            print(f'  {path.name}  {time.time() - began:7.1f}s', flush=True)
    index_path = folder / 'index.json'
    complete = all((folder / awake_chunk_name(lo, hi)).exists() for lo, hi in bounds)
    published = None
    if complete and not index_path.exists():
        questions, worlds = set(), set()
        for lo, hi in bounds:
            q, w = chunk_signatures(folder / awake_chunk_name(lo, hi))
            questions |= q
            worlds |= w
        hit = worlds & primary_worlds
        if hit:
            raise RuntimeError(f'awake stream holds {len(hit)} primary development '
                               f'world(s); the run is invalid')
        published = write_forbidden(folder, questions, worlds)
        write_doc(index_path, dict(
            kind='awake', seed=int(seed), updates=int(updates), chunk=int(chunk),
            visits=visits, people=people, questions_per_world=questions_per_world,
            calls=list(AWAKE_CALLS), namespace=NS_AWAKE, exclusion=exclusion_record,
            primary_world_exclusion=primary_record, published_exclusions=published,
            execution_profile=execution_profile(), fingerprint=fingerprint(),
            chunks=[dict(name=awake_chunk_name(lo, hi), start=lo, end=hi,
                         sha256=sha(folder / awake_chunk_name(lo, hi)),
                         bytes=(folder / awake_chunk_name(lo, hi)).stat().st_size)
                    for lo, hi in bounds]), seconds=time.time() - began)
    return dict(written=written, skipped=skipped, complete=complete,
                seconds=time.time() - began, published_exclusions=published,
                index=str(index_path) if complete else None)


def read_awake_index(stream):
    folder = Path(stream)
    index = json.loads((folder / 'index.json').read_text())
    return folder, index


def iter_awake(seed, start_update, end_update, stream, *, verify=True):
    """BUILDER-B API: yield one decoded record per update in [start, end).

    `record` is the neutral schema documented at the top of this file; feed it to
    `baseline_batch(record)` or `dispatcher_inputs(record)`.  Chunk hashes are checked
    against index.json unless `verify=False`.
    """
    folder, index = read_awake_index(stream)
    if int(index['seed']) != int(seed):
        raise SystemExit(f'stream {folder} holds seed {index["seed"]}, asked for {seed}')
    for entry in index['chunks']:
        if entry['end'] <= start_update or entry['start'] >= end_update:
            continue
        path = folder / entry['name']
        if verify and sha(path) != entry['sha256']:
            raise RuntimeError(f'awake chunk changed on disk: {path}')
        meta, blocks = load_chunk(path)
        for block in blocks:
            if start_update <= block['index'] < end_update:
                yield decode_block(block)


# =========================================================================== replay memory


def op_names(ops):
    """A question's operation string with entity names removed: ['LINK','LINK','8']."""
    return [NAME_OF[int(t)] for t in ops]


def transitions_of(names):
    """BOS -> ops -> EOS, as (from, to) alphabet-name pairs."""
    states = ['BOS'] + list(names) + ['EOS']
    return list(zip(states[:-1], states[1:]))


def build_memory(out, seed, stream, *, worlds=MEMORY_WORLDS, updates=None, progress=False):
    """Section 3: the first `worlds` DISTINCT awake worlds in encounter order, their
    four actual awake questions, and the 6x6 empirical transition-count table.

    World identity is `CP.world_signature` -- the sorted eligible fact tuples only, so
    it ignores row order and filler exactly as the spec requires.  Selection looks at
    nothing but encounter order: no correctness, reward, confidence or path length.
    """
    configure()
    folder = Path(out)
    folder.mkdir(parents=True, exist_ok=True)
    _, index = read_awake_index(stream)
    limit = int(index['updates']) if updates is None else int(updates)
    began = time.time()
    seen, stories, items, namespaces, source, duplicates = {}, [], [], [], [], []
    scanned_updates = 0
    for record in iter_awake(seed, 0, limit, stream):
        scanned_updates += 1
        qpw = len(record['items']) // max(1, len(record['stories']))
        for slot, story in enumerate(record['stories']):
            signature = record['items'][slot * qpw]['world_signature']
            where = seen.get(signature)
            if where is not None:
                duplicates.append(dict(world_signature=signature, first_memory_index=where,
                                       update=record['index'], slot=slot,
                                       namespace=record['namespaces'][slot]))
                continue
            memory_index = len(stories)
            seen[signature] = memory_index
            stories.append(story)
            namespaces.append(record['namespaces'][slot])
            for j in range(qpw):
                item = dict(record['items'][slot * qpw + j])
                item['owner'] = memory_index
                items.append(item)
                src = dict(record['source'][slot * qpw + j])
                src['memory_index'] = memory_index
                source.append(src)
            if len(stories) >= worlds:
                break
        if len(stories) >= worlds:
            break
    if len(stories) < worlds:
        raise SystemExit(f'only {len(stories)} distinct worlds in {scanned_updates} updates; '
                         f'need {worlds}')
    block = encode_block('memory', seed, 0, namespaces, stories, items, source)
    worlds_sha = save_chunk(folder / 'worlds.pt', [block], dict(
        kind='memory', seed=int(seed), worlds=int(worlds),
        questions_per_world=len(items) // len(stories),
        execution_profile=execution_profile(), fingerprint=fingerprint()))
    published = write_forbidden(folder, *block_signatures([block]))

    counts = [[0] * len(ALPHABET) for _ in ALPHABET]
    traces, histogram = {}, {}
    for q, item in enumerate(items):
        names = op_names(item['question'][2:-1])
        histogram[' '.join(names)] = histogram.get(' '.join(names), 0) + 1
        for a, b in transitions_of(names):
            counts[ALPHABET_INDEX[a]][ALPHABET_INDEX[b]] += 1
            key = f'{a}->{b}'
            if key not in traces:
                traces[key] = dict(memory_index=item['owner'], question_index=q,
                                   operation_string=' '.join(names),
                                   namespace=namespaces[item['owner']],
                                   source=source[q])
    rows = []
    for i, name in enumerate(ALPHABET):
        total = sum(counts[i])
        rows.append([c / total for c in counts[i]] if total else None)
    untraced = [f'{a}->{b}' for i, a in enumerate(ALPHABET) for j, b in enumerate(ALPHABET)
                if counts[i][j] and f'{a}->{b}' not in traces]
    if untraced:
        raise RuntimeError(f'nonzero edges without an awake trace: {untraced}')
    table = dict(alphabet=list(ALPHABET), counts=counts, rows=rows,
                 empty_rows=[ALPHABET[i] for i, r in enumerate(rows) if r is None],
                 total=sum(sum(r) for r in counts), questions=len(items),
                 smoothing='none', traces=traces, type_histogram=histogram,
                 counts_sha256=digest_of(counts))
    write_doc(folder / 'transition-counts.json', table)
    manifest = dict(kind='memory', seed=int(seed), worlds=int(worlds),
                    questions=len(items), stream=str(Path(stream).resolve()),
                    stream_index_sha256=sha(Path(stream) / 'index.json'),
                    updates_scanned=scanned_updates, duplicates=len(duplicates),
                    worlds_sha256=worlds_sha, published_exclusions=published,
                    transition_counts_sha256=sha(folder / 'transition-counts.json'),
                    execution_profile=execution_profile(), fingerprint=fingerprint())
    write_doc(folder / 'duplicates.json', duplicates)
    write_doc(folder / 'manifest.json', manifest, seconds=time.time() - began)
    if progress:
        print(json.dumps({k: v for k, v in manifest.items() if k != 'fingerprint'}, indent=2))
    return manifest


def load_memory(memory):
    folder = Path(memory)
    manifest = json.loads((folder / 'manifest.json').read_text())
    if sha(folder / 'worlds.pt') != manifest['worlds_sha256']:
        raise RuntimeError('memory worlds.pt changed on disk')
    if sha(folder / 'transition-counts.json') != manifest['transition_counts_sha256']:
        raise RuntimeError('memory transition-counts.json changed on disk')
    _, blocks = load_chunk(folder / 'worlds.pt')
    table = json.loads((folder / 'transition-counts.json').read_text())
    return manifest, decode_block(blocks[0]), table


# =========================================================================== proposals


def world_people(rows):
    """The world's people, in a fixed order, read only from the stored visible rows."""
    return sorted({row[1] for row in rows
                   if len(row) >= 4 and row[0] == WORLD and ENTITY_MIN <= row[1] < ENTITY_MAX})


def draw_from_counts(rng, counts_row):
    """One transition, sampled from the raw empirical counts -- no smoothing, no floats.

    `rng.randrange(total)` over the cumulative integer counts is exactly the normalised
    row's distribution and is bit-reproducible on any platform.
    """
    total = sum(counts_row)
    if total == 0:
        return None
    pick = rng.randrange(total)
    running = 0
    for index, count in enumerate(counts_row):
        running += count
        if pick < running:
            return ALPHABET[index]
    raise AssertionError('unreachable')


def propose_string(rng, counts):
    """Sample one candidate operation string from BOS.  Returns (names, reason).

    Rejection is never repair: a too-long, unterminated or attribute-less string is
    thrown away whole.  Nothing is truncated and no terminal is appended.
    """
    names, state = [], 'BOS'
    for _draw in range(MAX_DRAWS_AFTER_BOS):
        nxt = draw_from_counts(rng, counts[ALPHABET_INDEX[state]])
        if nxt is None:
            return names, 'empty_row'
        if nxt == 'BOS':
            return names, 'invalid_transition'
        if nxt == 'EOS':
            if not names:
                return names, 'no_attribute_terminus'
            if len(names) > MAX_BUFFER_CALLS:
                return names, 'too_many_calls'
            if names[-1] == 'LINK':
                return names, 'no_attribute_terminus'
            return names, None
        names.append(nxt)
        state = nxt
    return names, 'overrun'


def uniform_string(rng):
    """U's generic curriculum: c uniform 1..5, r uniform 8/9/10 at c=1 else 8/9."""
    calls = rng.choice(list(UNIFORM_CALLS))
    terminal = rng.choice(['8', '9', '10']) if calls == 1 else rng.choice(['8', '9'])
    return ['LINK'] * (calls - 1) + [terminal]


def composite_r10(names):
    return len(names) >= 2 and names[-1] == '10'


def question_from_names(start, names):
    return [QUESTION, int(start)] + [TOKEN_OF[n] for n in names] + [ANSWER]


def label_question(rows, question):
    """Labels from the FIXED interpreter over the stored visible story only."""
    eligible = [True] * len(rows)
    chain = V3.interpret(rows, eligible, question)
    mine = V1.walk(V1.fact_table(rows, eligible), question)
    if mine != chain:
        raise RuntimeError('the two independent interpreters disagree on a buffer question')
    return chain


def make_buffer_item(rows, owner, start, names, where):
    question = question_from_names(start, names)
    chain = label_question(rows, question)
    return dict(owner=owner, question=question, chain=chain, hops=len(chain),
                terminal=int(question[-2]), answer=int(chain[-1][2]),
                support=B1.support_rows(rows, chain), where=where)


def propose_for_world(seed, world_index, rows, counts, *, arm, questions_per_world,
                      awake_items, histograms):
    """Section 4's candidate schedule for ONE remembered world, G or U.

    Exactly `CANDIDATES_PER_WORLD` candidates are drawn in fixed RNG order; the first
    `questions_per_world` DISTINCT accepted signatures win; duplicates consume an
    attempt; nothing refills the budget.

    Ruling 3 of design/v3/19-rulings-1.md fixes the fallback: if `k < 4` candidates are
    accepted, slots `k..3` take original awake question `j` -- the SAME fixed-slot rule
    for G and U.  A fallback may duplicate an already accepted question: it is kept and
    logged (`duplicates_accepted`), never replaced, and the attempt budget is never
    extended.  The generation gate ignores fallbacks entirely.
    """
    people = world_people(rows)
    accepted, taken, fallbacks = [], set(), []
    structure_ns = NS_PROPOSE if arm == 'G' else NS_UNIFORM
    for candidate in range(CANDIDATES_PER_WORLD):
        key = f'{structure_ns}:{seed}:{world_index}:{candidate}'
        rng = random.Random(key)
        if arm == 'G':
            names, reason = propose_string(rng, counts)
        else:
            names, reason = uniform_string(rng), None
        kind = ' '.join(names) if names else '(empty)'
        histograms['proposed'][kind] = histograms['proposed'].get(kind, 0) + 1
        if reason is None and composite_r10(names):
            reason = 'composite_r10'
        if reason is not None:
            histograms['rejected'][reason] = histograms['rejected'].get(reason, 0) + 1
            histograms['rejected_types'][kind] = histograms['rejected_types'].get(kind, 0) + 1
            continue
        bind = random.Random(f'{NS_BIND}:{seed}:{world_index}:{candidate}')
        start = bind.choice(people)
        question = question_from_names(start, names)
        signature = A.visible_signature(rows, question)
        if signature in taken:
            histograms['rejected']['duplicate_signature'] = \
                histograms['rejected'].get('duplicate_signature', 0) + 1
            continue
        if len(accepted) >= questions_per_world:
            # all 64 candidates are always drawn, so the proposed/rejected histograms
            # describe the whole schedule; these were valid but arrived after the four
            # slots were full.  They are NOT a rejection of the type.
            histograms['rejected']['after_quota_filled'] = \
                histograms['rejected'].get('after_quota_filled', 0) + 1
            continue
        taken.add(signature)
        histograms['accepted'][kind] = histograms['accepted'].get(kind, 0) + 1
        accepted.append(dict(names=names, start=int(start), candidate=candidate,
                             sampled=True, namespace=key))
    for j in range(len(accepted), questions_per_world):
        item = awake_items[j]
        names = op_names(item['question'][2:-1])
        accepted.append(dict(names=names, start=int(item['question'][1]), candidate=None,
                             sampled=False, namespace=None, fallback_index=j))
        fallbacks.append(dict(world_index=world_index, slot=j,
                              operation_string=' '.join(names),
                              duplicates_accepted=bool(
                                  A.visible_signature(rows, item['question']) in taken)))
        histograms['fallback'][' '.join(names)] = \
            histograms['fallback'].get(' '.join(names), 0) + 1
    return accepted, fallbacks


# =========================================================================== buffers


def offline_order(seed, updates=OFFLINE_UPDATES, visits=OFFLINE_VISITS, worlds=MEMORY_WORLDS):
    """The SHARED world-index order every arm of a seed consumes (section 4).

    One frozen RNG per update (`astra-novelty19-offline-order-v1:<seed>:<update>`),
    sampled with replacement, so corresponding D/T runs see the same raw data order
    and a resumed chunk reproduces it exactly.
    """
    order = []
    for update in range(updates):
        rng = random.Random(f'{NS_ORDER}:{seed}:{update}')
        order.append([rng.randrange(worlds) for _ in range(visits)])
    return order


def _new_histograms():
    return dict(proposed={}, rejected={}, rejected_types={}, accepted={}, fallback={})


def build_buffers(out, seed, memory, *, dev_panels, extra_exclusion=(),
                  questions_per_world=BUFFER_QUESTIONS_PER_WORLD, arms=ARMS,
                  offline_updates=OFFLINE_UPDATES, progress=False):
    """Section 4: the R, G and U buffers over the SAME remembered worlds.

    Every arm stores byte-identical world rows in the same order; only the questions
    differ.  Labels come from the fixed interpreter over the stored visible story.
    `dev_panels` is mandatory: replay questions collide against the panel question
    signatures and replay worlds against the primary (N/E) panel world signatures.
    """
    configure()
    folder = Path(out)
    folder.mkdir(parents=True, exist_ok=True)
    forbidden, exclusion_record = build_exclusion_union(dev_panels, extra_exclusion)
    primary_worlds, primary_record = primary_world_exclusion(dev_panels)
    manifest_mem, mem, table = load_memory(memory)
    if int(manifest_mem['seed']) != int(seed):
        raise SystemExit(f'memory holds seed {manifest_mem["seed"]}, asked for {seed}')
    counts = table['counts']
    stories = mem['stories']
    qpw_mem = len(mem['items']) // len(stories)
    began = time.time()
    per_arm, audits = {}, {}
    for arm in arms:
        histograms = _new_histograms()
        items, source, fallbacks = [], [], []
        for w, rows in enumerate(stories):
            awake_items = mem['items'][w * qpw_mem:(w + 1) * qpw_mem]
            if arm == 'R':
                chosen = [dict(names=op_names(it['question'][2:-1]),
                               start=int(it['question'][1]), candidate=None, sampled=False,
                               namespace=mem['namespaces'][w], intact=True)
                          for it in awake_items[:questions_per_world]]
                for pick in chosen:
                    histograms['accepted'][' '.join(pick['names'])] = \
                        histograms['accepted'].get(' '.join(pick['names']), 0) + 1
            else:
                chosen, made = propose_for_world(
                    seed, w, rows, counts, arm=arm,
                    questions_per_world=questions_per_world, awake_items=awake_items,
                    histograms=histograms)
                fallbacks.extend(made)
            for j, pick in enumerate(chosen):
                item = make_buffer_item(rows, w, pick['start'], pick['names'],
                                        len(rows) + j)
                signature = A.visible_signature(rows, item['question'])
                if signature in forbidden:
                    raise RuntimeError(
                        f'buffer-{arm} world {w} slot {j} collides with the exclusion '
                        f'union; run invalid')
                if composite_r10(pick['names']):
                    raise RuntimeError(f'composite r=10 reached buffer-{arm}; run invalid')
                items.append(item)
                source.append(dict(memory_index=w, slot=j, arm=arm,
                                   operation_string=' '.join(pick['names']),
                                   start=int(pick['start']), candidate=pick['candidate'],
                                   sampled=bool(pick['sampled']),
                                   namespace=pick['namespace']))
        block = encode_block(f'buffer-{arm}', seed, 0, mem['namespaces'], stories, items,
                             source)
        assert_worlds_allowed([block], primary_worlds, f'buffer-{arm}')
        path = folder / f'buffer-{arm}.pt'
        buffer_sha = save_chunk(path, [block], dict(
            kind=f'buffer-{arm}', seed=int(seed), worlds=len(stories),
            questions_per_world=questions_per_world,
            execution_profile=execution_profile(), fingerprint=fingerprint()))
        audit = dict(arm=arm, worlds=len(stories), questions=len(items),
                     questions_per_world=questions_per_world,
                     candidates_per_world=(CANDIDATES_PER_WORLD if arm != 'R' else 0),
                     proposed=histograms['proposed'], rejected=histograms['rejected'],
                     rejected_types=histograms['rejected_types'],
                     accepted=histograms['accepted'], fallback_types=histograms['fallback'],
                     fallbacks=len(fallbacks), fallback_log=fallbacks[:256],
                     fallback_duplicates_accepted=sum(
                         1 for f in fallbacks if f['duplicates_accepted']),
                     length_histogram=_length_histogram(items),
                     sha256=buffer_sha)
        audits[arm] = audit
        per_arm[arm] = dict(block=block, items=items, source=source)
        if progress:
            print(f'  buffer-{arm}: {len(items)} questions, {len(fallbacks)} fallbacks, '
                  f'{time.time() - began:.1f}s', flush=True)

    identical = _identical_world_bytes(per_arm)
    gate = generation_gate(per_arm.get('G'), mem, table) if 'G' in per_arm else None
    exposure = r10_exposure(mem, table, per_arm)
    order = offline_order(seed, updates=offline_updates, visits=OFFLINE_VISITS,
                          worlds=len(stories))
    write_doc(folder / 'offline-order.json', dict(
        namespace=NS_ORDER, seed=int(seed), updates=int(offline_updates),
        visits=OFFLINE_VISITS, worlds=len(stories), chunk=OFFLINE_CHUNK,
        order_sha256=digest_of(order), order=order))
    questions, worlds_seen = set(), set()
    for payload in per_arm.values():
        q, w = block_signatures([payload['block']])
        questions |= q
        worlds_seen |= w
    published = write_forbidden(folder, questions, worlds_seen)
    audit_doc = dict(kind='buffers', seed=int(seed), arms=list(arms), per_arm=audits,
                     identical_world_bytes=identical, generation_gate=gate,
                     composite_r10_exposure=exposure,
                     offline_order_sha256=digest_of(order),
                     memory=dict(path=str(Path(memory).resolve()),
                                 manifest_sha256=sha(Path(memory) / 'manifest.json'),
                                 worlds=len(stories)),
                     exclusion=exclusion_record,
                     primary_world_exclusion=primary_record,
                     published_exclusions=published,
                     execution_profile=execution_profile(), fingerprint=fingerprint())
    write_doc(folder / 'audit.json', audit_doc, seconds=time.time() - began)
    write_doc(folder / 'manifest.json', dict(
        kind='buffers', seed=int(seed), arms=list(arms),
        files={f'buffer-{a}.pt': audits[a]['sha256'] for a in arms},
        audit_sha256=sha(folder / 'audit.json'),
        offline_order_sha256=sha(folder / 'offline-order.json'),
        published_exclusions=published,
        execution_profile=execution_profile(), fingerprint=fingerprint()))
    return audit_doc


def _length_histogram(items):
    out = {}
    for it in items:
        key = f'c={it["hops"]},r={it["terminal"]}'
        out[key] = out.get(key, 0) + 1
    return out


def _identical_world_bytes(per_arm):
    """Section 4: 'World bytes and their coverage are identical across R/G/U.'"""
    names = list(per_arm)
    first = per_arm[names[0]]['block']
    report = dict(checked=names, identical=True, mismatches=[])
    for name in names[1:]:
        other = per_arm[name]['block']
        same = (torch.equal(first['rows'], other['rows'])
                and torch.equal(first['row_count'], other['row_count'])
                and torch.equal(first['world_signature'], other['world_signature'])
                and list(first['namespaces']) == list(other['namespaces'])
                and torch.equal(first['owner'], other['owner']))
        if not same:
            report['identical'] = False
            report['mismatches'].append(name)
    report['world_signature_sha256'] = digest_of(hex_rows(first['world_signature']))
    return report


def generation_gate(g_arm, mem, table):
    """Section 5's generation gate, evaluated on SAMPLED accepted G questions only.

    Ruling 1 of design/v3/19-rulings-1.md, RATIFIED: per seed and per structure, at
    least 16 unique `(question-free world signature, full raw question tokens)` pairs
    spanning at least 16 unique world signatures, and zero instances of the structure
    anywhere in the awake corpus.  Fallbacks and repeated pairs are excluded (a repeat
    is already impossible inside one world: duplicate signatures are rejected at
    proposal time).  The world SIGNATURE is the key, not the memory index -- the two
    are equivalent only because `memory_worlds_distinct` is verified, and using the
    signature keeps the gate correct without that dependency.

    BOTH readings are always reported: `distinct_question_instances` (the ruling) and
    `distinct_raw_question_tokens`, which cannot exceed 16 per structure because there
    are only 16 entity IDs.  `GATE_READING` alone decides; entity-ID coverage
    (`distinct_bound_subjects`) is descriptive, never a gate.
    """
    awake_types = set(table['type_histogram'])
    qpw_mem = len(mem['items']) // max(1, len(mem['stories']))
    world_of = [mem['items'][w * qpw_mem]['world_signature']
                for w in range(len(mem['stories']))]
    distinct_memory_worlds = len(set(world_of)) == len(world_of)
    per_structure = {}
    passed = True
    for calls, relation in GENERATION_GATE_STRUCTURES:
        names = ['LINK'] * (calls - 1) + [str(relation)]
        key = ' '.join(names)
        pairs, raw, worlds, bound = set(), set(), set(), set()
        for item, src in zip(g_arm['items'], g_arm['source']):
            if not src['sampled'] or src['operation_string'] != key:
                continue
            signature = world_of[src['memory_index']]
            pairs.add((signature, bytes(item['question'])))
            raw.add(bytes(item['question']))
            worlds.add(signature)
            bound.add(int(item['question'][1]))
        counted = len(pairs) if GATE_READING == 'instances' else len(raw)
        row = dict(structure=f'c={calls},r={relation}', operation_string=key,
                   distinct_question_instances=len(pairs),
                   distinct_raw_question_tokens=len(raw),
                   distinct_questions=counted, reading=GATE_READING,
                   distinct_worlds=len(worlds), distinct_bound_subjects=len(bound),
                   awake_instances=table['type_histogram'].get(key, 0),
                   required=GENERATION_GATE_MIN)
        row['passed'] = bool(counted >= GENERATION_GATE_MIN
                             and len(worlds) >= GENERATION_GATE_MIN
                             and row['awake_instances'] == 0)
        passed = passed and row['passed']
        per_structure[row['structure']] = row
    passed = passed and distinct_memory_worlds
    return dict(passed=passed, reading=GATE_READING, structures=per_structure,
                memory_worlds_distinct=distinct_memory_worlds,
                awake_operation_types=sorted(awake_types),
                ruling='design/v3/19-rulings-1.md ruling 1 (ratified)',
                note='fallbacks and repeated (world, question) pairs excluded; awake '
                     'instances counted over the entity-stripped awake corpus; '
                     'entity-ID coverage is descriptive, not a gate')


def r10_exposure(mem, table, per_arm):
    """Section 5: composite r=10 must have ZERO exposure anywhere a learner can see.

    Entity names are stripped first, so this is a TYPE exclusion, not a hash exclusion.
    """
    report = dict(zero_exposure=True, sources={})

    def record(name, strings):
        hits = sorted({s for s in strings if composite_r10(s.split())})
        report['sources'][name] = dict(composite_r10_types=hits, count=len(hits))
        if hits:
            report['zero_exposure'] = False

    record('awake_stream_types', list(table['type_histogram']))
    edges = [f'{a}->{b}' for i, a in enumerate(ALPHABET) for j, b in enumerate(ALPHABET)
             if table['counts'][i][j]]
    report['sources']['transition_counts'] = dict(
        link_to_10=table['counts'][ALPHABET_INDEX['LINK']][ALPHABET_INDEX['10']],
        ten_to_ten=table['counts'][ALPHABET_INDEX['10']][ALPHABET_INDEX['10']],
        nonzero_edges=edges)
    if (table['counts'][ALPHABET_INDEX['LINK']][ALPHABET_INDEX['10']]
            or table['counts'][ALPHABET_INDEX['10']][ALPHABET_INDEX['10']]):
        report['zero_exposure'] = False
    record('memory_questions', [' '.join(op_names(it['question'][2:-1]))
                                for it in mem['items']])
    for arm, payload in per_arm.items():
        record(f'buffer_{arm}_accepted', [s['operation_string'] for s in payload['source']])
        record(f'buffer_{arm}_labels',
               [' '.join(op_names(it['question'][2:-1])) for it in payload['items']])
    proposed = []
    for arm, payload in per_arm.items():
        proposed.extend(s['operation_string'] for s in payload['source'])
    record('all_buffer_sources', proposed)
    return report


def load_buffer(buffers, arm):
    folder = Path(buffers)
    manifest = json.loads((folder / 'manifest.json').read_text())
    path = folder / f'buffer-{arm}.pt'
    if sha(path) != manifest['files'][path.name]:
        raise RuntimeError(f'buffer changed on disk: {path}')
    _, blocks = load_chunk(path)
    return decode_block(blocks[0])


# =========================================================================== dev panels


def _cell(kind, calls, people, terminal, fixed, *, edit=None, invariant=False, title=''):
    return dict(kind=kind, hops=calls, people=people, terminal=terminal,
                fixed_terminal=fixed, edit=edit, invariant=invariant,
                distinct=True, title=title)


def _dev_cells():
    """The 32 development cells of section 6, in the order the report prints them.

    `terminal` keeps v3's 'practised'/'heldout' vocabulary so `V3.audit_side` can audit
    these units unchanged; `fixed_terminal` pins the exact relation a cell asks for
    (an int, or 'balanced' for the L family's balanced 8/9 ending group).
    `distinct=True` everywhere: section 6 requires distinct visited people for c<=5,
    and 16-person worlds make it reachable for c=6..8 as well (v3's k6..k8 cells do
    the same), so no cell tolerates a cycling chain.
    """
    cells = {}
    for calls in (4, 5):                                        # N: 4 cells
        for people in (TRAIN_PEOPLE, PANEL_PEOPLE):
            cells[f'N-c{calls}-p{people}'] = _cell(
                'single', calls, people, 'heldout', HELDOUT_REL,
                title=f'NEVER-TRAINED: c={calls}, held-out relation 10, {people} people')
    for edit, invariant in (('link', False), ('value', False), ('irrelevant', True)):
        cells[f'E-c5-{edit}'] = _cell(                          # E: 3 pair cells
            'pair', 5, PANEL_PEOPLE, 'heldout', HELDOUT_REL, edit=edit,
            invariant=invariant,
            title=f'c=5 held-out {edit}-edit twin pair, {PANEL_PEOPLE} people')
    for relation in (FIRST_REL, FIRST_REL + 1, HELDOUT_REL):    # F: 7 cells
        kind = 'heldout' if relation == HELDOUT_REL else 'practised'
        cells[f'F-c1-r{relation}'] = _cell(
            'single', 1, TRAIN_PEOPLE, kind, relation,
            title=f'ordinary fit: c=1, r={relation}, {TRAIN_PEOPLE} people')
    for calls in (2, 3):
        for relation in PRACTISED_RELS:
            cells[f'F-c{calls}-r{relation}'] = _cell(
                'single', calls, TRAIN_PEOPLE, 'practised', relation,
                title=f'ordinary fit: c={calls}, r={relation}, {TRAIN_PEOPLE} people')
    for calls in (4, 5):                                        # P: 8 cells
        for relation in PRACTISED_RELS:
            for people in (TRAIN_PEOPLE, PANEL_PEOPLE):
                cells[f'P-c{calls}-r{relation}-p{people}'] = _cell(
                    'single', calls, people, 'practised', relation,
                    title=f'practised-length transfer: c={calls}, r={relation}, '
                          f'{people} people')
    for calls in (2, 3):                                        # H: 4 cells
        for people in (TRAIN_PEOPLE, PANEL_PEOPLE):
            cells[f'H-c{calls}-p{people}'] = _cell(
                'single', calls, people, 'heldout', HELDOUT_REL,
                title=f'short held-out ending: c={calls}, r=10, {people} people')
    for calls in (6, 7, 8):                                     # L: 6 cells
        cells[f'L-c{calls}-prac'] = _cell(
            'single', calls, PANEL_PEOPLE, 'practised', 'balanced',
            title=f'length extrapolation: c={calls}, balanced 8/9 ending, '
                  f'{PANEL_PEOPLE} people')
        cells[f'L-c{calls}-held'] = _cell(
            'single', calls, PANEL_PEOPLE, 'heldout', HELDOUT_REL,
            title=f'length extrapolation: c={calls}, relation 10 ending, '
                  f'{PANEL_PEOPLE} people')
    return cells


DEV_CELLS = _dev_cells()
DEV_CELL_ORDER = (
    [f'N-c{c}-p{p}' for c in (4, 5) for p in (TRAIN_PEOPLE, PANEL_PEOPLE)]
    + [f'E-c5-{e}' for e in ('link', 'value', 'irrelevant')]
    + [f'F-c1-r{r}' for r in (FIRST_REL, FIRST_REL + 1, HELDOUT_REL)]
    + [f'F-c{c}-r{r}' for c in (2, 3) for r in PRACTISED_RELS]
    + [f'P-c{c}-r{r}-p{p}' for c in (4, 5) for r in PRACTISED_RELS
       for p in (TRAIN_PEOPLE, PANEL_PEOPLE)]
    + [f'H-c{c}-p{p}' for c in (2, 3) for p in (TRAIN_PEOPLE, PANEL_PEOPLE)]
    + [f'L-c{c}-{t}' for c in (6, 7, 8) for t in ('prac', 'held')])
assert sorted(DEV_CELL_ORDER) == sorted(DEV_CELLS), 'dev cell order/table disagree'
assert len(DEV_CELLS) == 32, f'{len(DEV_CELLS)} development cells, expected 32'
DEV_FAMILY_SIZES = dict(N=4, E=3, F=7, P=8, H=4, L=6)
assert {k: sum(1 for c in DEV_CELLS if c.startswith(k + '-'))
        for k in DEV_FAMILY_SIZES} == DEV_FAMILY_SIZES


@contextmanager
def registered_cells(cells=None):
    """Temporarily expose the new cells to `V3.audit_side` / `V3.audit_unit`.

    Those auditors look their configuration up by name in `V3.CELLS`; every other v3
    consumer iterates `V3.CELL_ORDER`, which is untouched, and the module's import-time
    assertion has already run.  The table is restored exactly on exit, so no frozen
    behaviour changes and nothing is monkey-patched permanently.
    """
    cells = DEV_CELLS if cells is None else cells
    clash = sorted(set(cells) & set(V3.CELLS))
    if clash:
        raise RuntimeError(f'new cell names collide with v3 cells: {clash}')
    V3.CELLS.update(cells)
    try:
        yield
    finally:
        for name in cells:
            V3.CELLS.pop(name, None)


def target_answer(index, n=DEV_N):
    """Outcome-independent answer stratification: unit `index` must answer this value.

    The value vocabulary has 16 values and a cell has 64 units, so `index % 16` gives
    EXACTLY four units per value -- perfectly even, decided before any world is drawn
    and never revised by what the generator finds.
    """
    return VALUE_MIN + (index % VALUE_COUNT)


def cell_terminal(cfg, rng, index):
    """The relation unit `index` must end on.

    Ruling 6 of design/v3/19-rulings-1.md (CODE CHANGE): in a mixed 8/9 cell the ending
    schedule is `r(i) = 8 + (floor(i / 16) mod 2)`, NOT `i mod 2`.  With
    `target_answer(i) = 12 + (i mod 16)` the two cycles of `i mod 2` would have made
    relation 8 predict an even answer and relation 9 an odd one; with the blocked
    schedule every answer value appears equally often with each ending -- twice per
    ending at n=64, sixteen times at n=512.
    """
    fixed = cfg['fixed_terminal']
    if fixed == 'balanced':
        return PRACTISED_RELS[(index // VALUE_COUNT) % len(PRACTISED_RELS)]
    if fixed is None:
        return V3._terminal(rng, cfg['terminal'])
    return int(fixed)


def mixed_ending_balance(n=DEV_N):
    """(answer value, ending) counts for a mixed 8/9 cell of `n` units.

    Used by the audit and the tests: answer parity must not predict the ending.
    """
    table = {}
    for index in range(n):
        key = (target_answer(index, n), cell_terminal(dict(fixed_terminal='balanced'),
                                                      None, index))
        table[key] = table.get(key, 0) + 1
    return table


def unit_world_signatures(unit):
    """Each side's question-free world signature (ruling 4).

    `CP.fact_tuples` sorts the eligible WORLD fact tuples and drops everything else, so
    the identity ignores row order and filler rows exactly as the ruling requires; only
    rows visible before the question (`index < where`) count.
    """
    out = []
    for name in ['a'] + (['b'] if unit['kind'] == 'pair' else []):
        side = unit[name]
        rows = [row for index, row in enumerate(side['memory'])
                if row and index < side['where']]
        out.append(CP.world_signature(CP.fact_tuples(rows)))
    return out


def whole_cell(panel, units=None):
    """Return a cell's units, REFUSING any prefix or subset.

    The answer of unit `i` is a deterministic function of `i`
    (`target_answer(i) = 12 + i % 16`), and in a mixed-ending cell so is the ending.
    Scoring a prefix -- the first 16 units, say -- therefore scores a biased,
    non-representative sub-cell.  Every scorer must go through this helper.
    """
    n = int(panel['n'])
    got = list(panel['units'] if units is None else units)
    indices = [int(u['index']) for u in got]
    if len(got) != n or indices != list(range(n)):
        raise RuntimeError(
            f'refusing a partial cell for {panel.get("cell")}: got {len(got)} units '
            f'{indices[:4]}... of {n}. The answer (and, in mixed-ending cells, the '
            f'ending) is a function of the unit index, so a prefix or subset is biased; '
            f'score the whole cell or nothing.')
    return got


def dev_unit(cell, index, *, namespace=NS_DEV, exclusions=frozenset(),
             world_exclusions=frozenset(), taken_semantic=frozenset(),
             taken_tensor=frozenset(), attempts=DEV_ATTEMPTS, cells=None):
    """One development unit, from its own frozen per-attempt RNG namespace.

    Construction is v3's, verbatim: `build_world`, `distinct_askers`, `make_side`,
    `_edit_world`, `memory_diffs`.  The only additions are (a) the stratified target
    answer, (b) a fresh RNG per attempt so the namespace of section 7 is exact,
    (c) semantic/tensor exclusion and (d) question-free WORLD exclusion, on both sides
    of a pair.  Every accepted unit is audited by the independent evaluator
    (`V3.audit_unit`), and an audit problem ABORTS -- it is never dropped.

    Returns `(unit, [(semantic, tensor), ...], [world_signature, ...])`.
    """
    cfg = (cells or DEV_CELLS)[cell]
    calls = cfg['hops']
    target = target_answer(index)
    rejections = {}
    for attempt in range(attempts):
        rng = random.Random(f'{namespace}:{cell}:{index}:{attempt}')
        world = V3.build_world(rng, cfg['people'])
        askers = V3.distinct_askers(world, calls) if cfg['distinct'] else list(world.ents)
        if not askers:
            V3._bump(rejections, 'no_distinct_chain')
            continue
        terminal = cell_terminal(cfg, rng, index)
        fitting = [a for a in askers
                   if world.attr[(V3.chain_people(world.friend, a, calls)[-1],
                                  terminal)] == target]
        if not fitting:
            V3._bump(rejections, 'answer_target_unreachable')
            continue
        asker = rng.choice(fitting)
        side_a = V3.make_side(world, asker, calls, terminal)
        if side_a['answer'] != target:
            V3._bump(rejections, 'answer_target_missed')
            continue
        if cfg['kind'] == 'single':
            unit = dict(cell=cell, index=index, kind='single', a=side_a,
                        rejections=rejections)
        else:
            made = V3._edit_world(world, asker, cfg['edit'], rng, rejections, calls, terminal)
            if made is None:
                continue
            edited, detail = made
            if cfg['distinct'] and asker not in V3.distinct_askers(edited, calls):
                V3._bump(rejections, 'edit_broke_the_distinct_chain')
                continue
            side_b = V3.make_side(edited, asker, calls, terminal)
            if side_b['question'] != side_a['question'] or side_b['where'] != side_a['where']:
                V3._bump(rejections, 'the_edit_moved_the_question')
                continue
            expected = 1 if cfg['edit'] == 'link' else 2
            if V3.memory_diffs(side_a['memory'], side_b['memory']) != expected:
                V3._bump(rejections, 'unexpected_token_diffs')
                continue
            changed = side_b['answer'] != side_a['answer']
            if cfg['invariant'] and changed:
                V3._bump(rejections, 'irrelevant_edit_changed_the_answer')
                continue
            if not cfg['invariant'] and not changed:
                V3._bump(rejections, 'edit_left_the_answer_alone')
                continue
            if sorted(world.attr.values()) != sorted(edited.attr.values()):
                V3._bump(rejections, 'value_inventory_not_preserved')
                continue
            unit = dict(cell=cell, index=index, kind='pair', a=side_a, b=side_b,
                        edit_detail=detail, rejections=rejections)
        signatures = V3.unit_signatures(unit)
        worlds = unit_world_signatures(unit)
        if any(s in exclusions for s, _ in signatures):
            V3._bump(rejections, 'collides_with_the_exclusion_union')
            continue
        # section 7 / ruling 2: the WORLD itself must be new, on both sides of a pair
        if any(w in world_exclusions for w in worlds):
            V3._bump(rejections, 'collides_with_the_world_exclusion_union')
            continue
        if any(s in taken_semantic for s, _ in signatures):
            V3._bump(rejections, 'duplicate_semantics_inside_the_suite')
            continue
        if any(t in taken_tensor for _, t in signatures):
            V3._bump(rejections, 'duplicate_tensor_inside_the_suite')
            continue
        problems = V3.audit_unit(unit)
        if problems:
            raise RuntimeError(f'{cell}[{index}] failed its own audit: {problems}')
        unit['attempts'] = attempt + 1
        unit['target_answer'] = target
        unit['namespace'] = f'{namespace}:{cell}:{index}:{attempt}'
        return unit, signatures, worlds
    raise RuntimeError(f'{cell}[{index}] exhausted {attempts} attempts: {rejections}')


# =========================================================================== operator history


def world_union_digest(worlds):
    """sha256 over the sorted world signatures, byte-for-byte the auditor's digest."""
    digest = hashlib.sha256()
    for signature in sorted(worlds):
        digest.update(signature.encode())
    return digest.hexdigest()


def reconstruct_operator_history(updates=OPERATOR_HISTORY_UPDATES,
                                 visits=OPERATOR_HISTORY_VISITS, progress=False):
    """Section 7's provenance wave: the FROZEN operator's historical training semantics.

    Re-implemented here from the archived driver, importing only the frozen modules:
    `scripts/astra_canonical_operator_run.py:worker` drives ONE sequential
    `random.Random(1101)` through 6,000 updates of `A.training_batch(rng, 16, ...)`,
    each of which draws 16 `toy_ladder.visit(spec, rng, training=True)` and then burns
    one `rng.randrange(1 << 30)`.  Replaying exactly those draws reproduces exactly the
    worlds and questions the operator saw -- with NO model forward anywhere.

    A two-call question contributes three signatures, because the operator was trained
    on the decomposition as well: the LINK sub-question, the endpoint sub-question and
    the whole question.
    """
    configure()
    A.data.bootstrap()
    from premonition.toy_ladder import LadderSpec, visit
    spec = LadderSpec()
    rng = random.Random(OPERATOR_HISTORY_RNG_SEED)
    worlds, questions = set(), set()
    began = time.time()
    for step in range(updates):
        for _slot in range(visits):
            rows, _world, _ = visit(spec, rng, training=True)
            memory = [[] if r.question else list(r.tokens) for r in rows]
            facts = CP.fact_tuples([r for r in memory if r])
            worlds.add(CP.world_signature(facts))
            for row in rows:
                if not row.question:
                    continue
                question = row.tokens[:row.tokens.index(ANSWER) + 1]
                if row.hops == 1:
                    questions.add(CP.signature_from_facts(facts, question))
                else:
                    link_line, _endpoint_line = row.gold
                    entity = rows[link_line].tokens[3]
                    questions.add(CP.signature_from_facts(
                        facts, [QUESTION, question[1], LINK, ANSWER]))
                    questions.add(CP.signature_from_facts(
                        facts, [QUESTION, entity, question[3], ANSWER]))
                    questions.add(CP.signature_from_facts(facts, question))
        rng.randrange(1 << 30)
        if progress and (step + 1) % 1000 == 0:
            print(f'  {step + 1}/{updates} updates  {time.time() - began:6.1f}s',
                  flush=True)
    return worlds, questions, time.time() - began


def build_operator_history(out, *, updates=OPERATOR_HISTORY_UPDATES,
                           visits=OPERATOR_HISTORY_VISITS, progress=False):
    """Materialise the reconstruction as an ordinary exclusion source.

    `complete` is true only for the full registered replay whose world union matches
    the independently measured digest; ruling 2 makes anything less a freeze blocker,
    so `build_dev_panels` refuses to emit panels from an incomplete one.
    """
    folder = Path(out)
    folder.mkdir(parents=True, exist_ok=False)
    worlds, questions, seconds = reconstruct_operator_history(updates, visits, progress)
    union = world_union_digest(worlds)
    full = bool(updates == OPERATOR_HISTORY_UPDATES and visits == OPERATOR_HISTORY_VISITS)
    published = write_forbidden(folder, questions, worlds)
    manifest = dict(
        kind='operator-history', rng_seed=OPERATOR_HISTORY_RNG_SEED,
        updates=int(updates), visits=int(visits),
        distinct_training_worlds=len(worlds),
        distinct_training_question_signatures=len(questions),
        world_union_sha256=union, expected_world_union_sha256=(
            OPERATOR_HISTORY_WORLD_UNION_SHA256 if full else None),
        matches_expected=bool(full and union == OPERATOR_HISTORY_WORLD_UNION_SHA256),
        full_run=full, complete=bool(full
                                     and union == OPERATOR_HISTORY_WORLD_UNION_SHA256),
        published_exclusions=published, no_model_forwards=True,
        source='design/v3/19-rulings-1.md ruling 2; artifacts/'
               'astra-canonical-operator-screen-20260920 driver replay',
        execution_profile=execution_profile(), fingerprint=fingerprint())
    write_doc(folder / 'manifest.json', manifest, seconds=seconds)
    if full and union != OPERATOR_HISTORY_WORLD_UNION_SHA256:
        raise RuntimeError(
            f'operator-history world union {union} != the independently measured '
            f'{OPERATOR_HISTORY_WORLD_UNION_SHA256}; the reconstruction is not the '
            f'archived stream and panels must not be built from it')
    return manifest


def load_operator_history(folder, *, require_full=True):
    """The reconstruction's exclusion sets; an incomplete one REFUSES (ruling 2)."""
    if folder is None:
        raise SystemExit('the operator-history reconstruction is a freeze prerequisite: '
                         'pass --operator-history (see design/v3/19-rulings-1.md ruling 2)')
    folder = Path(folder)
    path = folder / 'manifest.json'
    if not path.exists():
        raise SystemExit(f'no operator-history manifest at {path}')
    manifest = json.loads(path.read_text())
    if require_full and not manifest.get('complete'):
        raise SystemExit(
            f'operator-history at {folder} is incomplete '
            f'(updates={manifest.get("updates")}, full_run={manifest.get("full_run")}, '
            f'matches_expected={manifest.get("matches_expected")}); ruling 2 makes a '
            f'complete reconstruction a prerequisite for emitting panels')
    # `artifact_exclusions` hashes and counts both files against this manifest's
    # `published_exclusions`, so a truncated or edited reconstruction is refused
    return manifest, artifact_exclusions(folder)


# =========================================================================== lockout


def validate_dev_passed(experiment, *, panels_folder=None, seeds=REGISTERED_SEEDS):
    """The confirmation lockout.  Anything short of the full schema REFUSES.

    An empty or malformed `DEV-PASSED.json` used to be accepted merely by existing;
    now it must parse, carry the report hash, the dev-panel manifest hash (VERIFIED
    against the manifest on disk), and all six awake plus eighteen offline checkpoint
    hashes.  The schema is documented at the top of this file.
    """
    flag = Path(experiment) / 'DEV-PASSED.json'
    if not flag.exists():
        raise SystemExit(f'refusing to build confirmation panels: no {flag}. '
                         'Confirmation is generated only after development passes.')
    if flag.stat().st_size == 0:
        raise SystemExit(f'{flag} is empty; it must carry the development evidence')
    try:
        doc = json.loads(flag.read_text())
    except json.JSONDecodeError as exc:
        raise SystemExit(f'{flag} does not parse: {exc}') from None
    if not isinstance(doc, dict):
        raise SystemExit(f'{flag} is not a JSON object')
    if doc.get('schema') != DEV_PASSED_SCHEMA:
        raise SystemExit(f'{flag} schema is {doc.get("schema")!r}, '
                         f'expected {DEV_PASSED_SCHEMA!r}')
    if [int(s) for s in doc.get('seeds', [])] != list(seeds):
        raise SystemExit(f'{flag} seeds are {doc.get("seeds")!r}, '
                         f'expected {list(seeds)}')
    if not HEX64.match(str(doc.get('report_sha256', ''))):
        raise SystemExit(f'{flag} has no valid report_sha256')
    panels = doc.get('dev_panels')
    if not isinstance(panels, dict) or not HEX64.match(str(panels.get('manifest_sha256', ''))):
        raise SystemExit(f'{flag} has no valid dev_panels.manifest_sha256')
    folder = Path(panels_folder or panels.get('path', ''))
    if not folder.is_absolute():
        folder = Path(experiment) / folder
    manifest = folder / 'manifest.json'
    if not manifest.exists():
        raise SystemExit(f'{flag} points at {folder}, which has no manifest.json')
    on_disk = sha(manifest)
    if on_disk != panels['manifest_sha256']:
        raise SystemExit(f'{flag} records dev-panel manifest {panels["manifest_sha256"]} '
                         f'but {manifest} hashes to {on_disk}')
    for field, expected in (('awake_checkpoints', checkpoint_keys('awake', seeds)),
                            ('offline_checkpoints', checkpoint_keys('offline', seeds))):
        got = doc.get(field)
        if not isinstance(got, dict):
            raise SystemExit(f'{flag} has no {field} object')
        missing = [k for k in expected if k not in got]
        if missing:
            raise SystemExit(f'{flag} {field} is missing {len(missing)} of '
                             f'{len(expected)} entries: {missing[:6]}')
        extra = sorted(set(got) - set(expected))
        if extra:
            raise SystemExit(f'{flag} {field} has unexpected entries: {extra[:6]}')
        bad = sorted(k for k, v in got.items() if not HEX64.match(str(v)))
        if bad:
            raise SystemExit(f'{flag} {field} entries are not sha256: {bad[:6]}')
    return dict(path=str(flag.resolve()), sha256=sha(flag),
                report_sha256=doc['report_sha256'],
                dev_panels=dict(path=str(folder.resolve()), manifest_sha256=on_disk),
                awake_checkpoints=len(doc['awake_checkpoints']),
                offline_checkpoints=len(doc['offline_checkpoints']))


def experiment_folders(experiment, seeds=REGISTERED_SEEDS):
    """Every artifact folder of one experiment, by the fixed layout."""
    root = Path(experiment)
    out = {}
    for seed in seeds:
        for key in ('stream', 'memory', 'buffers'):
            out[f'{key}_{seed}'] = root / EXPERIMENT_LAYOUT[key].format(seed=seed)
    out['dev_panels'] = root / EXPERIMENT_LAYOUT['dev_panels']
    out['operator_history'] = root / EXPERIMENT_LAYOUT['operator_history']
    return out


def confirmation_exclusions(experiment, seeds=REGISTERED_SEEDS):
    """Section 7's confirmation exclusion union: every training/replay artifact of all
    three registered seeds, plus the development panels, at BOTH levels.

    A missing forbidden-semantics.json or forbidden-worlds.json aborts: an artifact
    that never published its semantics cannot be excluded, so the suite is unverified.
    Every file is checked against the sha256 and entry count its own producing manifest
    recorded, and those identities are returned so the confirmation manifest can record
    exactly which bytes it consumed (audit re-check 2, R2-7).
    """
    folders = experiment_folders(experiment, seeds)
    questions, worlds, sources = set(), set(), []
    for name, folder in folders.items():
        if name == 'operator_history':
            continue
        sets = artifact_exclusions(folder)
        questions |= sets['questions']
        worlds |= sets['worlds']
        sources.append(dict(name=name, **sets['record']))
    return questions, worlds, sources


def build_dev_panels(out, *, n=DEV_N, namespace=NS_DEV, cells=None, cell_order=None,
                     extra_exclusion=(), attempts=DEV_ATTEMPTS, confirmation=False,
                     experiment=None, operator_history=None, require_full_history=True,
                     seeds=REGISTERED_SEEDS, progress=True, budget=None):
    """Section 6's 32 development cells, in the SAME JSON shape as the v3 panels.

    `operator_chain_hits` is deliberately absent: it is a model forward, every reader
    fetches it with `panel.get(...)`, and `fable_operator_swap` strips it anyway.  The
    panels are pure data; operator diagnostics belong to the scoring wave.

    Exclusions are enforced at BOTH levels and on both sides of every pair:
      * question signatures -- the legacy union, the reconstructed operator history,
        and (confirmation only) every training/replay artifact of all three seeds plus
        the development panels;
      * question-free WORLD signatures -- the same sources.  Section 7 asks for worlds,
        not merely accepted training questions.

    The operator-history reconstruction (ruling 2) is a PREREQUISITE for both kinds of
    panel: an incomplete one refuses.

    With `confirmation=True` this builds the section-7 confirmation copy instead
    (`--namespace astra-novelty19-confirm-v1 --n 512`).  That path REFUSES until
    `experiment/DEV-PASSED.json` validates in full -- schema, report hash, the
    dev-panel manifest hash checked against disk, and all six awake plus eighteen
    offline checkpoint hashes.
    """
    cells = DEV_CELLS if cells is None else cells
    order = cell_order or [c for c in DEV_CELL_ORDER if c in cells]
    if operator_history is None and experiment is not None:
        operator_history = experiment_folders(experiment)['operator_history']
    if not confirmation and namespace == NS_CONFIRM:
        raise SystemExit('the confirmation namespace needs the explicit --confirmation flag')
    if confirmation and experiment is None:
        raise SystemExit('--confirmation needs --experiment <folder holding DEV-PASSED.json>')
    if not require_full_history and namespace in (NS_DEV, NS_CONFIRM):
        raise SystemExit('a partial operator history may never back a registered '
                         'namespace; use a fixture namespace for that')
    passed_record = validate_dev_passed(experiment, seeds=seeds) if confirmation else None
    history_manifest, history = load_operator_history(
        operator_history, require_full=require_full_history)
    configure()
    # every exclusion source is read and VERIFIED before the output folder exists, so a
    # refusal never leaves a half-built panel folder behind
    exclusions, exclusion_record = B2.exclusion_union(
        [str(p) for p in legacy_exclusion_paths(extra_exclusion)])
    exclusions = frozenset(exclusions) | history['questions']
    world_exclusions = frozenset(history['worlds'])
    training_record = None
    if confirmation:
        more_questions, more_worlds, sources = confirmation_exclusions(experiment, seeds)
        exclusions = exclusions | more_questions
        world_exclusions = world_exclusions | more_worlds
        training_record = dict(sources=sources, questions=len(more_questions),
                               worlds=len(more_worlds),
                               world_union_sha256=world_union_digest(more_worlds))
    folder = Path(out)
    folder.mkdir(parents=True, exist_ok=False)
    began = time.time()
    semantic, tensors, panel_worlds = set(), set(), set()
    primary_worlds = set()
    manifest = dict(namespace=namespace, n=int(n),
                    kind='confirmation' if confirmation else 'development',
                    source_sha256=sha(__file__), v3_source_sha256=sha(V3.__file__),
                    execution_profile=execution_profile(),
                    fingerprint=fingerprint(), frozen_before_any_training=True,
                    stratification='target_answer(index) = 12 + index % 16, '
                                   'outcome-independent and fixed before generation; '
                                   'mixed 8/9 endings follow ruling 6, '
                                   'r(i) = 8 + (i // 16) % 2',
                    rulings='design/v3/19-rulings-1.md',
                    legacy_exclusion=exclusion_record,
                    operator_history=dict(
                        path=str(Path(operator_history).resolve()),
                        manifest_sha256=sha(Path(operator_history) / 'manifest.json'),
                        complete=bool(history_manifest.get('complete')),
                        worlds=len(history['worlds']),
                        questions=len(history['questions']),
                        world_union_sha256=history_manifest['world_union_sha256'],
                        # the exclusion files this build actually read, verified
                        # against the reconstruction's own manifest
                        source=history['record']),
                    training_exclusion=training_record, dev_passed=passed_record,
                    # every exclusion file this build read, with the sha256 it was
                    # verified at: a truncated or edited source cannot reach a panel
                    # without showing up here (audit re-check 2, R2-7)
                    consumed_exclusions=(
                        [dict(name='legacy', **s) for s in exclusion_record['sources']]
                        + [dict(name='operator_history', **history['record'])]
                        + [s for s in (training_record or {}).get('sources', [])]),
                    exclusion_levels=['question_signature', 'world_signature'],
                    cells={}, cell_order=list(order), families=DEV_FAMILY_SIZES)
    with registered_cells(cells):
        for cell in order:
            cfg = cells[cell]
            units, rejections, attempts_used = [], {}, []
            for index in range(n):
                unit, signatures, worlds = dev_unit(
                    cell, index, namespace=namespace, exclusions=exclusions,
                    world_exclusions=world_exclusions, taken_semantic=semantic,
                    taken_tensor=tensors, attempts=attempts, cells=cells)
                for key, value in unit.pop('rejections').items():
                    rejections[key] = rejections.get(key, 0) + value
                attempts_used.append(unit.pop('attempts'))
                for sem, ts in signatures:
                    semantic.add(sem)
                    tensors.add(ts)
                panel_worlds.update(worlds)
                if cell.split('-')[0] in PRIMARY_FAMILIES:
                    primary_worlds.update(worlds)
                units.append(unit)
            answers = {}
            for unit in units:
                answers[unit['a']['answer']] = answers.get(unit['a']['answer'], 0) + 1
            endings = {}
            for unit in units:
                key = (unit['a']['answer'], int(unit['a']['question'][-2]))
                endings[key] = endings.get(key, 0) + 1
            path = folder / f'{cell}.json'
            write_doc(path, dict(cell=cell, n=int(n), namespace=namespace, kind=cfg['kind'],
                                 title=cfg['title'], hops=cfg['hops'], people=cfg['people'],
                                 terminal=cfg['terminal'], distinct=cfg['distinct'],
                                 invariant=cfg['invariant'], edit=cfg['edit'],
                                 fixed_terminal=cfg['fixed_terminal'], units=units,
                                 rejections=rejections))
            manifest['cells'][cell] = dict(
                path=str(path), sha256=sha(path), n=int(n), kind=cfg['kind'],
                hops=cfg['hops'], people=cfg['people'], terminal=cfg['terminal'],
                fixed_terminal=cfg['fixed_terminal'], title=cfg['title'],
                rejections=rejections, attempts_total=sum(attempts_used),
                attempts_max=max(attempts_used),
                answer_histogram={str(k): v for k, v in sorted(answers.items())},
                answer_values=len(answers),
                answer_evenly_stratified=bool(len(answers) == VALUE_COUNT
                                              and set(answers.values()) ==
                                              {n // VALUE_COUNT}),
                endings=sorted({int(e) for _, e in endings}),
                # ruling 6: in a mixed-ending cell every answer value must appear
                # equally often with each ending, so the answer never predicts it
                answer_ending_balanced=bool(
                    len({e for _, e in endings}) == 1
                    or (len(endings) == VALUE_COUNT * len({e for _, e in endings})
                        and len(set(endings.values())) == 1)))
            if progress:
                print(json.dumps(dict(cell=cell, n=int(n), attempts=sum(attempts_used),
                                      seconds=round(time.time() - began, 1))), flush=True)
            if budget is not None and time.time() - began > budget:
                raise SystemExit(f'compute budget {budget}s exceeded after {cell}; '
                                 'the folder is incomplete -- delete it and split the run')
    published = write_forbidden(folder, semantic, panel_worlds,
                                primary_worlds=primary_worlds)
    manifest.update(exclusion_path=published['questions_path'],
                    exclusion_sha256=published['questions_sha256'],
                    exclusion_count=len(semantic),
                    world_exclusion_path=published['worlds_path'],
                    world_exclusion_sha256=published['worlds_sha256'],
                    world_exclusion_count=len(panel_worlds),
                    primary_world_exclusion_path=published['primary_worlds_path'],
                    primary_world_exclusion_sha256=published['primary_worlds_sha256'],
                    primary_world_exclusion_count=len(primary_worlds),
                    primary_families=list(PRIMARY_FAMILIES),
                    distinct_worlds=len(panel_worlds),
                    published_exclusions=published,
                    unique_tensor_inputs=len(tensors),
                    duplicate_or_overlap_failures=0, all_audits_passed=True)
    write_doc(folder / 'manifest.json', manifest, seconds=time.time() - began)
    return dict(panels=str(folder.resolve()), cells=len(order), n=int(n),
                exclusion_count=len(semantic), world_exclusion_count=len(panel_worlds),
                primary_world_exclusion_count=len(primary_worlds),
                unique_tensor_inputs=len(tensors),
                operator_history_worlds=len(history['worlds']),
                seconds=time.time() - began,
                manifest_sha256=sha(folder / 'manifest.json'))


def load_dev_panels(panels, cells=None):
    """v3-compatible loader: re-checks every panel hash before returning it."""
    folder = Path(panels)
    manifest = json.loads((folder / 'manifest.json').read_text())
    loaded = {}
    for cell, row in manifest['cells'].items():
        path = folder / f'{cell}.json'
        if sha(path) != row['sha256']:
            raise RuntimeError(f'panel changed on disk: {path}')
        loaded[cell] = json.loads(path.read_text())
    for name, key in ((FORBIDDEN_QUESTIONS, 'exclusion_sha256'),
                      (FORBIDDEN_WORLDS, 'world_exclusion_sha256'),
                      (FORBIDDEN_PRIMARY_WORLDS, 'primary_world_exclusion_sha256')):
        if manifest.get(key) and sha(folder / name) != manifest[key]:
            raise RuntimeError(f'{name} changed on disk')
    # and again through the shared verifier, so the count is checked too
    sets = artifact_exclusions(folder, worlds=False, primary=False)
    return manifest, loaded, sets['questions']


def dev_panel_worlds(panels):
    """The panels' published world signatures, all cells and the primary cells alone.

    Both files are verified against the panel manifest's `published_exclusions`.
    """
    sets = artifact_exclusions(panels, questions=False, primary=True)
    return sets['worlds'], sets['primary_worlds']


# =========================================================================== audit


def awake_signatures(stream, seed, limit=None):
    """Every visible signature and operation type in the materialised awake stream."""
    folder, index = read_awake_index(stream)
    signatures, worlds, types, questions, updates = set(), set(), {}, 0, 0
    for entry in index['chunks']:
        path = folder / entry['name']
        if sha(path) != entry['sha256']:
            raise RuntimeError(f'awake chunk changed on disk: {path}')
        _, blocks = load_chunk(path)
        for block in blocks:
            if limit is not None and block['index'] >= limit:
                continue
            updates += 1
            for row in block['signature'].tolist():
                signatures.add(bytes(row).hex())
            for row in block['world_signature'].tolist():
                worlds.add(bytes(row).hex())
            for q in range(block['calls'].shape[0]):
                c = int(block['calls'][q])
                key = ' '.join(op_names(block['ops'][q].tolist()[:c]))
                types[key] = types.get(key, 0) + 1
                questions += 1
    return dict(signatures=signatures, worlds=worlds, types=types, questions=questions,
                updates=updates, index_seed=int(index['seed']))


EXPECTED_AUDIT_CHECKS = (
    'dev_panel_hashes', 'dev_panel_cell_count', 'dev_panel_answer_stratification',
    'dev_panel_mixed_ending_balance', 'dev_panel_world_exclusions_published',
    'dev_panel_excluded_the_operator_history',
    'awake_chunk_hashes', 'awake_seed_matches', 'awake_zero_composite_r10',
    'awake_disjoint_from_dev_panels', 'awake_worlds_disjoint_from_dev_panels',
    'awake_published_exclusions',
    'memory_hashes', 'counts_derived_only_from_awake_strings', 'counts_unsmoothed',
    'memory_worlds_distinct', 'memory_questions_come_from_the_stream',
    'memory_disjoint_from_dev_panels', 'memory_worlds_disjoint_from_dev_panels',
    'memory_published_exclusions',
    'buffer_hashes', 'identical_world_bytes_and_order', 'buffer_shape',
    'buffers_zero_composite_r10', 'buffer_labels_match_the_fixed_interpreter',
    'buffers_disjoint_from_dev_panels', 'buffers_worlds_disjoint_from_dev_panels',
    'buffers_published_exclusions', 'buffer_worlds_are_the_memory_worlds',
    'generation_gate', 'recorded_zero_exposure_audit', 'offline_order_reproducible',
    'operator_history_complete', 'operator_history_disjoint_from_dev_panels',
    'operator_history_disjoint_from_training',
    'exclusion_files_match_their_manifests',
    'execution_profiles_agree',
)


def audit_everything(seed, *, stream, memory, buffers, dev_panels, operator_history,
                     limit=None, require_full_history=True):
    """Re-verify every data-side artifact FROM DISK and return one verdict.

    Every source is MANDATORY.  Dropping one used to drop its checks silently (23 with
    `--dev-panels`, 17 without) and a verdict of `passed: true` either way; now the
    roster in `EXPECTED_AUDIT_CHECKS` must run in full, the count is printed, and a
    missing check is itself a failure.
    """
    configure()
    verdict = dict(seed=int(seed), checks={}, failures=[], fingerprint=fingerprint())

    def check(name, ok, detail=None):
        if name not in EXPECTED_AUDIT_CHECKS:
            raise AssertionError(f'check {name!r} is not in EXPECTED_AUDIT_CHECKS')
        verdict['checks'][name] = dict(passed=bool(ok), detail=detail)
        if not ok:
            verdict['failures'].append(name)

    missing = [name for name, value in
               dict(stream=stream, memory=memory, buffers=buffers,
                    dev_panels=dev_panels, operator_history=operator_history).items()
               if value is None]
    if missing:
        raise SystemExit('audit needs every artifact; missing: ' + ', '.join(missing))

    # FIRST: every exclusion file must still be the one its producer published.  The
    # auditor truncated a buffer's world file from 1,024 entries to 5 and the
    # confirmation build accepted it; now the consumer hashes and counts what it reads
    # against the producing manifest, and the audit reports the offender by name
    # instead of dying halfway through (audit re-check 2, R2-7).
    exclusion_sources, tampered, verified = {}, {}, {}
    for name, folder in (('stream', stream), ('memory', memory), ('buffers', buffers),
                         ('dev_panels', dev_panels),
                         ('operator_history', operator_history)):
        try:
            sets = artifact_exclusions(folder, primary=(name == 'dev_panels'))
            verified[name] = sets
            exclusion_sources[name] = sets['record']
        except SystemExit as exc:
            tampered[name] = str(exc)
    check('exclusion_files_match_their_manifests', not tampered,
          tampered or exclusion_sources)
    if tampered:
        return _finish_audit(verdict, aborted='a consumed exclusion file does not match '
                                              'the manifest that published it')

    history_manifest, history = load_operator_history(
        operator_history, require_full=require_full_history)
    profiles = {}

    def profile(name, doc):
        if isinstance(doc, dict) and doc.get('execution_profile'):
            profiles[name] = doc['execution_profile']

    dev_manifest, panels, dev_forbidden = load_dev_panels(dev_panels)
    dev_worlds, dev_primary_worlds = dev_panel_worlds(dev_panels)
    profile('dev_panels', dev_manifest)
    check('dev_panel_hashes', True,
          dict(cells=len(panels), signatures=len(dev_forbidden),
               worlds=len(dev_worlds), primary_worlds=len(dev_primary_worlds),
               manifest_sha256=sha(Path(dev_panels) / 'manifest.json')))
    check('dev_panel_cell_count', len(panels) == 32, dict(cells=len(panels)))
    even = {c: r['answer_evenly_stratified'] for c, r in dev_manifest['cells'].items()}
    check('dev_panel_answer_stratification', all(even.values()), even)
    balanced = {c: r.get('answer_ending_balanced') for c, r in dev_manifest['cells'].items()}
    check('dev_panel_mixed_ending_balance', all(bool(v) for v in balanced.values()),
          {c: v for c, v in balanced.items() if not v} or dict(cells=len(balanced)))
    primary_cells = [c for c in panels if c.split('-')[0] in PRIMARY_FAMILIES]
    check('dev_panel_world_exclusions_published',
          bool(dev_worlds) and bool(dev_primary_worlds)
          and dev_primary_worlds <= dev_worlds
          and len(dev_primary_worlds) >= len(primary_cells),
          dict(worlds=len(dev_worlds), primary_worlds=len(dev_primary_worlds),
               primary_cells=len(primary_cells)))
    overlap = dev_worlds & history['worlds']
    check('dev_panel_excluded_the_operator_history',
          not overlap and not (dev_forbidden & history['questions']),
          dict(world_overlap=len(overlap),
               question_overlap=len(dev_forbidden & history['questions']),
               operator_worlds=len(history['worlds'])))
    check('operator_history_complete',
          bool(history_manifest.get('complete')) or not require_full_history,
          dict(updates=history_manifest.get('updates'),
               full_run=history_manifest.get('full_run'),
               matches_expected=history_manifest.get('matches_expected'),
               world_union_sha256=history_manifest.get('world_union_sha256')))
    check('operator_history_disjoint_from_dev_panels', not overlap,
          dict(world_overlap=len(overlap)))
    profile('operator_history', history_manifest)

    _, awake_index = read_awake_index(stream)
    profile('awake_index', awake_index)
    awake = awake_signatures(stream, seed, limit)
    check('awake_chunk_hashes', True,
          dict(updates=awake['updates'], questions=awake['questions']))
    check('awake_seed_matches', awake['index_seed'] == int(seed),
          dict(index_seed=awake['index_seed']))
    bad = sorted(t for t in awake['types'] if composite_r10(t.split()))
    check('awake_zero_composite_r10', not bad, dict(offending_types=bad))
    overlap = awake['signatures'] & dev_forbidden
    check('awake_disjoint_from_dev_panels', not overlap, dict(overlap=len(overlap)))
    # section 7 wants WORLDS excluded, not only accepted questions; the primary (N/E)
    # worlds are additionally refused at generation time
    world_overlap = awake['worlds'] & dev_worlds
    check('awake_worlds_disjoint_from_dev_panels', not world_overlap,
          dict(overlap=len(world_overlap),
               primary_overlap=len(awake['worlds'] & dev_primary_worlds),
               awake_worlds=len(awake['worlds'])))
    stream_sets = verified['stream']          # already verified above
    check('awake_published_exclusions',
          awake['signatures'] <= stream_sets['questions']
          and awake['worlds'] <= stream_sets['worlds'],
          dict(published_questions=len(stream_sets['questions']),
               published_worlds=len(stream_sets['worlds'])))

    manifest_mem, mem, table = load_memory(memory)
    profile('memory', manifest_mem)
    check('memory_hashes', True, dict(worlds=manifest_mem['worlds'],
                                      duplicates=manifest_mem['duplicates']))
    counts = [[0] * len(ALPHABET) for _ in ALPHABET]
    histogram = {}
    for item in mem['items']:
        names = op_names(item['question'][2:-1])
        histogram[' '.join(names)] = histogram.get(' '.join(names), 0) + 1
        for a, b in transitions_of(names):
            counts[ALPHABET_INDEX[a]][ALPHABET_INDEX[b]] += 1
    check('counts_derived_only_from_awake_strings',
          counts == table['counts'] and histogram == table['type_histogram'],
          dict(recomputed_sha256=digest_of(counts),
               stored_sha256=table['counts_sha256']))
    check('counts_unsmoothed',
          all(c == int(c) for row in counts for c in row)
          and sum(sum(r) for r in counts) == sum(len(op_names(it['question'][2:-1])) + 1
                                                 for it in mem['items']),
          dict(total=sum(sum(r) for r in counts)))
    mem_worlds = {it['world_signature'] for it in mem['items']}
    check('memory_worlds_distinct', len(mem_worlds) == manifest_mem['worlds'],
          dict(distinct=len(mem_worlds)))
    missing_q = {it['signature'] for it in mem['items']} - awake['signatures']
    check('memory_questions_come_from_the_stream', not missing_q,
          dict(missing=len(missing_q)))
    overlap = {it['signature'] for it in mem['items']} & dev_forbidden
    check('memory_disjoint_from_dev_panels', not overlap, dict(overlap=len(overlap)))
    world_overlap = mem_worlds & dev_worlds
    check('memory_worlds_disjoint_from_dev_panels', not world_overlap,
          dict(overlap=len(world_overlap),
               primary_overlap=len(mem_worlds & dev_primary_worlds)))
    memory_sets = verified['memory']          # already verified above
    check('memory_published_exclusions',
          {it['signature'] for it in mem['items']} <= memory_sets['questions']
          and mem_worlds <= memory_sets['worlds'],
          dict(published_questions=len(memory_sets['questions']),
               published_worlds=len(memory_sets['worlds'])))

    folder = Path(buffers)
    manifest_buf = json.loads((folder / 'manifest.json').read_text())
    audit_doc = json.loads((folder / 'audit.json').read_text())
    if sha(folder / 'audit.json') != manifest_buf['audit_sha256']:
        raise RuntimeError('buffer audit.json changed on disk')
    profile('buffers', manifest_buf)
    profile('buffers_audit', audit_doc)
    loaded = {arm: load_buffer(buffers, arm) for arm in manifest_buf['arms']}
    check('buffer_hashes', True, dict(arms=list(loaded)))
    first = loaded[manifest_buf['arms'][0]]
    same = all(other['stories'] == first['stories']
               and [it['owner'] for it in other['items']]
               == [it['owner'] for it in first['items']]
               for other in loaded.values())
    check('identical_world_bytes_and_order', same,
          dict(arms=list(loaded), worlds=len(first['stories'])))
    counts_ok = all(len(rec['items']) == len(rec['stories']) * BUFFER_QUESTIONS_PER_WORLD
                    for rec in loaded.values())
    check('buffer_shape', counts_ok, {a: len(r['items']) for a, r in loaded.items()})
    offending = {}
    for arm, rec in loaded.items():
        bad = sorted({' '.join(op_names(it['question'][2:-1])) for it in rec['items']
                      if composite_r10(op_names(it['question'][2:-1]))})
        if bad:
            offending[arm] = bad
    check('buffers_zero_composite_r10', not offending, offending)
    relabelled = {}
    for arm, rec in loaded.items():
        relabelled[arm] = sum(1 for it in rec['items']
                              if label_question(rec['stories'][it['owner']],
                                                it['question']) != it['chain'])
    check('buffer_labels_match_the_fixed_interpreter',
          all(v == 0 for v in relabelled.values()), relabelled)
    overlap = {arm: len({it['signature'] for it in rec['items']} & dev_forbidden)
               for arm, rec in loaded.items()}
    check('buffers_disjoint_from_dev_panels',
          all(v == 0 for v in overlap.values()), overlap)
    buffer_worlds = set()
    for rec in loaded.values():
        buffer_worlds |= {it['world_signature'] for it in rec['items']}
    world_overlap = buffer_worlds & dev_worlds
    check('buffers_worlds_disjoint_from_dev_panels', not world_overlap,
          dict(overlap=len(world_overlap),
               primary_overlap=len(buffer_worlds & dev_primary_worlds),
               buffer_worlds=len(buffer_worlds)))
    buffer_sets = verified['buffers']         # already verified above
    buffer_questions = set()
    for rec in loaded.values():
        buffer_questions |= {it['signature'] for it in rec['items']}
    check('buffers_published_exclusions',
          buffer_questions <= buffer_sets['questions']
          and buffer_worlds <= buffer_sets['worlds'],
          dict(published_questions=len(buffer_sets['questions']),
               published_worlds=len(buffer_sets['worlds'])))
    check('buffer_worlds_are_the_memory_worlds',
          all(rec['stories'] == mem['stories'] for rec in loaded.values()), None)
    gate = audit_doc.get('generation_gate')
    check('generation_gate', gate is not None and gate['passed'],
          {k: dict(distinct_question_instances=v.get('distinct_question_instances'),
                   distinct_raw_question_tokens=v.get('distinct_raw_question_tokens'),
                   reading=v.get('reading'), distinct_worlds=v['distinct_worlds'],
                   awake_instances=v['awake_instances'])
           for k, v in gate['structures'].items()} if gate else None)
    check('recorded_zero_exposure_audit',
          audit_doc['composite_r10_exposure']['zero_exposure'], None)
    order = json.loads((folder / 'offline-order.json').read_text())
    rebuilt = offline_order(seed, updates=order['updates'], visits=order['visits'],
                            worlds=order['worlds'])
    check('offline_order_reproducible', rebuilt == order['order'],
          dict(updates=order['updates'], sha256=order['order_sha256']))

    training_questions = (awake['signatures'] | {it['signature'] for it in mem['items']}
                          | buffer_questions)
    training_worlds = awake['worlds'] | mem_worlds | buffer_worlds
    check('operator_history_disjoint_from_training',
          not (training_worlds & history['worlds'])
          and not (training_questions & history['questions']),
          dict(world_overlap=len(training_worlds & history['worlds']),
               question_overlap=len(training_questions & history['questions']),
               training_worlds=len(training_worlds)))

    # one experiment, one execution profile: a manifest written under a different
    # interpreter, torch or source revision makes the artifacts incomparable
    distinct = {digest_of(p): p for p in profiles.values()}
    check('execution_profiles_agree', len(distinct) == 1,
          dict(manifests=sorted(profiles),
               profiles=[{k: v for k, v in p.items() if k != 'sources'}
                         for p in distinct.values()]))

    return _finish_audit(verdict)


def _finish_audit(verdict, *, aborted=None):
    """Close a verdict: an absent expected check is itself a failure."""
    absent = [name for name in EXPECTED_AUDIT_CHECKS if name not in verdict['checks']]
    verdict['checks_run'] = len(verdict['checks'])
    verdict['checks_expected'] = len(EXPECTED_AUDIT_CHECKS)
    verdict['checks_absent'] = absent
    if aborted:
        # an aborted audit reports the reason instead of pretending the remaining
        # checks were merely forgotten
        verdict['aborted'] = aborted
    elif absent:
        verdict['failures'].append('expected_checks_absent')
    verdict['passed'] = not verdict['failures']
    return verdict


# =========================================================================== CLI


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = parser.add_subparsers(dest='command', required=True)

    p = sub.add_parser('awake-stream', help='section 2: the common per-seed awake stream')
    p.add_argument('--seed', type=int, required=True)
    p.add_argument('--updates', type=int, default=AWAKE_UPDATES)
    p.add_argument('--start-update', type=int, default=0)
    p.add_argument('--chunk', type=int, default=AWAKE_CHUNK)
    p.add_argument('--out', required=True)
    p.add_argument('--dev-panels', required=True,
                   help='REQUIRED: the collision abort must always be armed, at the '
                        'question level and at the primary-world level')
    p.add_argument('--extra-exclusion', action='append', default=[])
    p.add_argument('--budget', type=float, default=None,
                   help='stop cleanly after this many seconds; resume with the same command')
    p.add_argument('--quiet', action='store_true')

    p = sub.add_parser('memory', help='section 3: 1,024 distinct worlds + the 6x6 table')
    p.add_argument('--seed', type=int, required=True)
    p.add_argument('--stream', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--worlds', type=int, default=MEMORY_WORLDS)
    p.add_argument('--updates', type=int, default=None)

    p = sub.add_parser('buffers', help='section 4/5: the R, G and U buffers')
    p.add_argument('--seed', type=int, required=True)
    p.add_argument('--memory', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--dev-panels', required=True,
                   help='REQUIRED: the collision abort must always be armed')
    p.add_argument('--extra-exclusion', action='append', default=[])
    p.add_argument('--offline-updates', type=int, default=OFFLINE_UPDATES)
    p.add_argument('--arms', default=','.join(ARMS))

    p = sub.add_parser('dev-panels', help='section 6: the 32 development cells')
    p.add_argument('--out', required=True)
    p.add_argument('--n', type=int, default=DEV_N)
    p.add_argument('--namespace', default=NS_DEV)
    p.add_argument('--cells', default=None, help='comma-separated subset, for fixtures')
    p.add_argument('--attempts', type=int, default=DEV_ATTEMPTS)
    p.add_argument('--extra-exclusion', action='append', default=[])
    p.add_argument('--operator-history', default=None,
                   help='the reconstruction folder; defaults to '
                        '<experiment>/operator-history.  Ruling 2 makes it a '
                        'prerequisite for development AND confirmation panels')
    p.add_argument('--fixture-history', action='store_true',
                   help='fixtures only: accept a partial operator history (refused for '
                        'the registered namespaces)')
    p.add_argument('--confirmation', action='store_true',
                   help='build the section-7 confirmation copy; needs DEV-PASSED.json')
    p.add_argument('--experiment', default=None, help='folder holding DEV-PASSED.json')
    p.add_argument('--budget', type=float, default=None)
    p.add_argument('--quiet', action='store_true')

    p = sub.add_parser('operator-history',
                       help="section 7: the frozen operator's historical training "
                            'worlds and questions, with no model forwards')
    p.add_argument('--out', required=True)
    p.add_argument('--updates', type=int, default=OPERATOR_HISTORY_UPDATES)
    p.add_argument('--visits', type=int, default=OPERATOR_HISTORY_VISITS)
    p.add_argument('--quiet', action='store_true')

    p = sub.add_parser('audit', help='re-verify every artifact from disk')
    p.add_argument('--seed', type=int, required=True)
    p.add_argument('--stream', required=True)
    p.add_argument('--memory', required=True)
    p.add_argument('--buffers', required=True)
    p.add_argument('--dev-panels', required=True)
    p.add_argument('--operator-history', required=True)
    p.add_argument('--fixture-history', action='store_true',
                   help='fixtures only: accept a partial operator history')
    p.add_argument('--limit', type=int, default=None)

    args = parser.parse_args(argv)

    if args.command == 'awake-stream':
        out = build_awake_stream(
            args.out, args.seed, args.updates, start=args.start_update, chunk=args.chunk,
            dev_panels=args.dev_panels, extra_exclusion=args.extra_exclusion,
            budget=args.budget, progress=not args.quiet)
        print(json.dumps(out, indent=2))
        return out
    if args.command == 'memory':
        out = build_memory(args.out, args.seed, args.stream, worlds=args.worlds,
                           updates=args.updates)
        print(json.dumps({k: v for k, v in out.items()
                          if k not in ('fingerprint', 'execution_profile')}, indent=2))
        return out
    if args.command == 'buffers':
        out = build_buffers(args.out, args.seed, args.memory, dev_panels=args.dev_panels,
                            extra_exclusion=args.extra_exclusion,
                            arms=tuple(a for a in args.arms.split(',') if a),
                            offline_updates=args.offline_updates, progress=True)
        print(json.dumps(dict(seed=out['seed'], arms=out['arms'],
                              identical_world_bytes=out['identical_world_bytes']['identical'],
                              generation_gate=out['generation_gate'],
                              zero_composite_r10_exposure=out['composite_r10_exposure'][
                                  'zero_exposure'],
                              fallbacks={a: out['per_arm'][a]['fallbacks']
                                         for a in out['arms']}), indent=2))
        return out
    if args.command == 'dev-panels':
        cells = None
        if args.cells:
            names = [c for c in args.cells.split(',') if c]
            cells = {name: DEV_CELLS[name] for name in names}
        out = build_dev_panels(args.out, n=args.n, namespace=args.namespace, cells=cells,
                               extra_exclusion=args.extra_exclusion, attempts=args.attempts,
                               confirmation=args.confirmation, experiment=args.experiment,
                               operator_history=args.operator_history,
                               require_full_history=not args.fixture_history,
                               budget=args.budget, progress=not args.quiet)
        print(json.dumps(out, indent=2))
        return out
    if args.command == 'operator-history':
        out = build_operator_history(args.out, updates=args.updates, visits=args.visits,
                                     progress=not args.quiet)
        print(json.dumps({k: v for k, v in out.items()
                          if k not in ('fingerprint', 'execution_profile')}, indent=2))
        return out
    if args.command == 'audit':
        out = audit_everything(args.seed, stream=args.stream, memory=args.memory,
                               buffers=args.buffers, dev_panels=args.dev_panels,
                               operator_history=args.operator_history,
                               require_full_history=not args.fixture_history,
                               limit=args.limit)
        print(json.dumps(out, indent=2))
        print(f'checks run: {out["checks_run"]}/{out["checks_expected"]}'
              + (f'  ABSENT: {out["checks_absent"]}' if out['checks_absent'] else ''),
              flush=True)
        if not out['passed']:
            raise SystemExit(1)
        return out
    raise SystemExit(f'unknown command {args.command}')


if __name__ == '__main__':
    main()
