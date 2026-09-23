"""Experiment 19b -- U8 versus U5: the DATA side.

Astra's next step after experiment 19 FAILED its registered rule
(`artifacts/fable-novelty19-replay-20260920/RESULTS.md`).  The specification is
`design/v3/19-development-readout-and-next-step.md`, sections "One next experiment" and
"Prospective marks"; this module builds every byte the trainer consumes and nothing
else.  It NEVER edits experiment 19: `scripts/fable_novelty19_data.py` is frozen at
`ef1df0e1...` and imported unchanged, and everything under
`artifacts/fable-novelty19-replay-20260920/` is opened read-only and hash-verified.

-------------------------------------------------------------------------------
WHAT CHANGES, AND WHAT DOES NOT
-------------------------------------------------------------------------------
Two arms, D only, 2,000 offline updates, three seeds -> six continuations:

    U5 control     length law c uniform 1..5   (experiment 19's U law, unchanged)
    U8 treatment   length law c uniform 1..8   (ONLY the length support changes)

Everything else is experiment 19's U recipe verbatim, and is reused from the frozen
module rather than re-implemented: the same 1,024 six-person memory worlds and story
bytes per seed, 64 candidates/world, first-four-distinct acceptance, the fixed-slot
fallback (ruling 3), four questions/world, uniform subject binding, the terminal rule
(r = 8/9/10 at c=1, r = 8/9 otherwise), composite r=10 excluded globally, and the
shared offline world-index order.

Six-person worlds cycle, and c=7/8 NECESSARILY revisits people.  That is disclosed, not
repaired: `buffer_revisits` counts it per arm and length.  Chains are never
success-filtered and U8 never gets larger worlds than U5.

-------------------------------------------------------------------------------
THE PAIRED STREAM MAPPING (frozen here, verified by the audit)
-------------------------------------------------------------------------------
Two named streams, one per decision, both keyed by (seed, world, candidate) alone:

    length/ending   random.Random(f'{NS_LENGTH}:{seed}:{world}:{candidate}')
    subject binding random.Random(f'{NS_BIND}:{seed}:{world}:{candidate}')

The key does NOT contain the arm, so at every candidate slot both arms bind the SAME
start person from the SAME draw, and the two length laws are read off the same seeded
stream.  The pairing is therefore key-determined and outcome-independent: nothing about
what U5 accepted can move what U8 proposes, and vice versa.  `NS_LENGTH` is experiment
19's `astra-novelty19-uniform-v1` and `NS_BIND` its `astra-novelty19-bind-v1`, which is
what makes U5 reproduce experiment 19's U buffer item for item (see below).

U5 VERSUS EXPERIMENT 19's U.  The specification permits it and the code asserts it:
with the same memory, the same keys and the same 1..5 law, every U5 question, start,
chain, owner and source operation string equals experiment 19's U buffer.  The stored
`.pt` is NOT byte-identical, because the block records its own `kind` ('buffer-U5' vs
'buffer-U') and its own execution profile; the claim that can be asserted, and is, is
ITEM-level identity.  `audit` runs it as `u5_matches_experiment_19_u`.

-------------------------------------------------------------------------------
THE 38 DEVELOPMENT CELLS
-------------------------------------------------------------------------------
The 26 old N/P/F/H/E cells (experiment 19's 32 cells minus its six mixed-ending L
cells), plus nine separate-ending long cells and three c=8 held-out edit pairs:

    N 4   c=4/5, r=10, p6/p16                         (never-trained)
    E 6   c=5 link/value/irrelevant  +  c=8 link/value/irrelevant, r=10, p16
    F 7   c=1 r=8/9/10, c=2/3 r=8/9, p6               (retention)
    P 8   c=4/5, r=8/9, p6/p16                        (practised length)
    H 4   c=2/3, r=10, p6/p16                         (short held-out ending)
    L 9   c=6/7/8 x r=8/9/10, p16                     (separate endings, new)

Nine SEPARATE-ending long cells replace experiment 19's six balanced ones so that one
practised ending cannot conceal the other; each is single-ending and therefore still
answer-balanced by `target_answer(i) = 12 + (i mod 16)` alone.  Rulings 5 and 6 of
`design/v3/19-rulings-1.md` still hold: all visited people distinct on both sides of
every pair in every cell, and any mixed-ending cell would use r(i) = 8 + ((i // 16) mod
2) -- 19b has no mixed-ending cell left, and the audit proves that.

Panels are fresh, interpreter-only, with a fixed rejection limit and logged attempts.
Their exclusions are the named-token question signature AND the question-free world
signature of: the canonical operator's reconstructed history, ALL experiment-19
training/replay/candidate worlds (awake stream, memory, buffers of all three seeds),
experiment 19's own development panels, and all 19b buffer worlds.  Every one of those
files is hash- and count-verified against the manifest that published it (R2-7), and
the panel manifest records exactly which bytes it consumed.

-------------------------------------------------------------------------------
ON-DISK LAYOUT  (EXP2 = artifacts/fable-novelty19b-u8-20260920/)
-------------------------------------------------------------------------------
  EXP2/buffers-<seed>/buffer-U5.pt, buffer-U8.pt, offline-order.json, audit.json,
                      forbidden-semantics.json, forbidden-worlds.json, manifest.json
  EXP2/dev-panels/<cell>.json x38, forbidden-semantics.json, forbidden-worlds.json,
                      forbidden-worlds-primary.json, manifest.json
  EXP2/confirm-panels/   -- LOCKED behind EXP2/DEV-PASSED.json; not generated here
  EXP2/audit/audit-<seed>.json

-------------------------------------------------------------------------------
SUBCOMMANDS
-------------------------------------------------------------------------------
  buffers      the U5 and U8 offline buffers over experiment 19's memory worlds
  dev-panels   the 38 fresh development cells (--confirmation is locked)
  audit        re-verify every 19b artifact from disk and print one JSON verdict
"""

import argparse
import json
import random
import time
from pathlib import Path

import fable_novelty19_data as N

V3 = N.V3
A = N.A
torch = N.torch
sha = N.sha
configure = N.configure
write_doc = N.write_doc
digest_of = N.digest_of

QUESTION, ANSWER = N.QUESTION, N.ANSWER
HELDOUT_REL = N.HELDOUT_REL                       # 10
PRACTISED_RELS = N.PRACTISED_RELS                 # (8, 9)
FIRST_REL = N.FIRST_REL                           # 8
VALUE_MIN, VALUE_COUNT = N.VALUE_MIN, N.VALUE_COUNT
PANEL_PEOPLE, TRAIN_PEOPLE = N.PANEL_PEOPLE, N.TRAIN_PEOPLE

WORKTREE = N.WORKTREE
EXP19 = WORKTREE / 'artifacts' / 'fable-novelty19-replay-20260920'
EXP2_DEFAULT = WORKTREE / 'artifacts' / 'fable-novelty19b-u8-20260920'

# ---- frozen registered numbers.  DO NOT CHANGE. -----------------------------
SEEDS = N.REGISTERED_SEEDS                        # (1900, 1901, 1902)
ARMS = ('U5', 'U8')
ARM_CALLS = dict(U5=(1, 2, 3, 4, 5), U8=(1, 2, 3, 4, 5, 6, 7, 8))
CONTROL_ARM, TREATMENT_ARM = 'U5', 'U8'
CANDIDATES_PER_WORLD = N.CANDIDATES_PER_WORLD     # 64
BUFFER_QUESTIONS_PER_WORLD = N.BUFFER_QUESTIONS_PER_WORLD   # 4
MEMORY_WORLDS = N.MEMORY_WORLDS                   # 1024
OFFLINE_UPDATES = N.OFFLINE_UPDATES               # 2000
OFFLINE_VISITS = N.OFFLINE_VISITS                 # 16
DEV_N = N.DEV_N                                   # 64
CONFIRM_N = N.CONFIRM_N                           # 512
DEV_ATTEMPTS = N.DEV_ATTEMPTS                     # 10,000
ARCHITECTURES = ('D',)                            # D only: startup is already qualified

# ---- the paired stream mapping, frozen ---------------------------------------
NS_LENGTH = N.NS_UNIFORM                          # 'astra-novelty19-uniform-v1'
NS_BIND = N.NS_BIND                               # 'astra-novelty19-bind-v1'
NS_ORDER = N.NS_ORDER                             # shared world-index order
NS_DEV = 'astra-novelty19b-dev-v1'
NS_CONFIRM = 'astra-novelty19b-confirm-v1'
STREAM_MAPPING = dict(
    length=dict(namespace=NS_LENGTH, key='{ns}:{seed}:{world}:{candidate}',
                draws=['calls', 'terminal'], arm_in_key=False),
    binding=dict(namespace=NS_BIND, key='{ns}:{seed}:{world}:{candidate}',
                 draws=['start'], arm_in_key=False),
    order=dict(namespace=NS_ORDER, key='{ns}:{seed}:{update}', arm_in_key=False),
    pairing='outcome-independent: the key never contains the arm, so both arms bind the '
            'same start person at every candidate slot and read both length laws off '
            'the same seeded stream',
    arm_calls={a: list(ARM_CALLS[a]) for a in ARMS})
STREAM_MAPPING_SHA256 = None                      # filled below, after digest_of exists

DEV_PASSED_SCHEMA = 'novelty19b-dev-passed-v1'
LAYOUT = dict(buffers='buffers-{seed}', dev_panels='dev-panels',
              confirm_panels='confirm-panels', audit='audit')
# experiment 19's artifacts, read-only, by the SAME layout the frozen module uses
EXP19_LAYOUT = N.EXPERIMENT_LAYOUT


def checkpoint_keys(stage, seeds=SEEDS):
    """The trainer's checkpoint names: 3 awake ('D-<seed>'), 6 offline ('D-U5-<seed>')."""
    if stage == 'awake':
        return tuple(f'{a}-{s}' for a in ARCHITECTURES for s in seeds)
    if stage == 'offline':
        return tuple(f'{a}-{m}-{s}' for a in ARCHITECTURES for m in ARMS for s in seeds)
    raise ValueError(f'unknown stage {stage!r}')


def fingerprint():
    """This module's fingerprint on top of the frozen module's."""
    out = dict(N.fingerprint())
    out['novelty19b_data'] = sha(__file__)
    return out


def execution_profile():
    profile = dict(N.execution_profile())
    sources = dict(profile.get('sources') or {})
    sources['novelty19b_data'] = sha(__file__)
    profile['sources'] = sources
    profile['script_sha256'] = sha(__file__)
    return profile


STREAM_MAPPING_SHA256 = digest_of(STREAM_MAPPING)


# =========================================================================== buffers


def uniform_string(rng, arm):
    """19b's length law: c uniform over `ARM_CALLS[arm]`, r = 8/9/10 at c=1 else 8/9.

    Byte-for-byte experiment 19's `uniform_string` with the call support as a parameter:
    the SAME two draws in the SAME order off the SAME rng, so at arm 'U5' the returned
    string is exactly what the frozen module returns for the same key.
    """
    calls = rng.choice(list(ARM_CALLS[arm]))
    terminal = rng.choice(['8', '9', '10']) if calls == 1 else rng.choice(['8', '9'])
    return ['LINK'] * (calls - 1) + [terminal]


def propose_for_world(seed, world_index, rows, *, arm, questions_per_world,
                      awake_items, histograms):
    """Experiment 19's U candidate schedule for ONE remembered world, with 19b's law.

    Exactly `CANDIDATES_PER_WORLD` candidates are drawn in fixed RNG order; the first
    `questions_per_world` DISTINCT accepted signatures win; duplicates consume an
    attempt; nothing refills the budget.  Ruling 3's fixed-slot fallback is unchanged:
    if `k < 4` candidates are accepted, slots `k..3` take original awake question `j`,
    kept and logged even when it duplicates an accepted one, never replaced.
    """
    people = N.world_people(rows)
    accepted, taken, fallbacks = [], set(), []
    for candidate in range(CANDIDATES_PER_WORLD):
        key = f'{NS_LENGTH}:{seed}:{world_index}:{candidate}'
        names = uniform_string(random.Random(key), arm)
        kind = ' '.join(names)
        histograms['proposed'][kind] = histograms['proposed'].get(kind, 0) + 1
        if N.composite_r10(names):
            # unreachable under this law (c>=2 ends on 8/9); kept as a live guard
            histograms['rejected']['composite_r10'] = \
                histograms['rejected'].get('composite_r10', 0) + 1
            histograms['rejected_types'][kind] = histograms['rejected_types'].get(kind, 0) + 1
            continue
        bind = random.Random(f'{NS_BIND}:{seed}:{world_index}:{candidate}')
        start = bind.choice(people)
        question = N.question_from_names(start, names)
        signature = A.visible_signature(rows, question)
        if signature in taken:
            histograms['rejected']['duplicate_signature'] = \
                histograms['rejected'].get('duplicate_signature', 0) + 1
            continue
        if len(accepted) >= questions_per_world:
            histograms['rejected']['after_quota_filled'] = \
                histograms['rejected'].get('after_quota_filled', 0) + 1
            continue
        taken.add(signature)
        histograms['accepted'][kind] = histograms['accepted'].get(kind, 0) + 1
        accepted.append(dict(names=names, start=int(start), candidate=candidate,
                             sampled=True, namespace=key))
    for j in range(len(accepted), questions_per_world):
        item = awake_items[j]
        names = N.op_names(item['question'][2:-1])
        accepted.append(dict(names=names, start=int(item['question'][1]), candidate=None,
                             sampled=False, namespace=None, fallback_index=j))
        fallbacks.append(dict(world_index=world_index, slot=j,
                              operation_string=' '.join(names),
                              duplicates_accepted=bool(
                                  A.visible_signature(rows, item['question']) in taken)))
        histograms['fallback'][' '.join(names)] = \
            histograms['fallback'].get(' '.join(names), 0) + 1
    return accepted, fallbacks


def _new_histograms():
    return dict(proposed={}, rejected={}, rejected_types={}, accepted={}, fallback={})


def length_ending_histogram(items):
    """Accepted counts per (length, ending), the readout's "per length and ending"."""
    return N._length_histogram(items)


def revisit_report(items, stories):
    """Disclosure, not a filter: how often an accepted chain revisits a person.

    Six-person worlds cycle and c=7/8 MUST revisit; this counts it per length so the
    report states the exposure instead of hiding or repairing it.
    """
    per_length, revisiting = {}, 0
    for item in items:
        # an interpreter step is [subject, relation, value]; the subjects ARE the
        # visited people, in order, one per executed call
        people = [int(step[0]) for step in item['chain']]
        repeats = len(people) - len(set(people))
        key = f'c={item["hops"]}'
        row = per_length.setdefault(key, dict(units=0, with_revisits=0, max_repeats=0))
        row['units'] += 1
        if repeats:
            row['with_revisits'] += 1
            revisiting += 1
        row['max_repeats'] = max(row['max_repeats'], repeats)
    return dict(units=len(items), with_revisits=revisiting, per_length=per_length,
                note='six-person worlds cycle; c=7/8 necessarily revisits people. '
                     'Disclosed, never success-filtered.')


def build_buffers(out, seed, memory, *, dev_panels, extra_exclusion=(),
                  questions_per_world=BUFFER_QUESTIONS_PER_WORLD, arms=ARMS,
                  offline_updates=OFFLINE_UPDATES, compare_buffers=None, progress=False):
    """The U5 and U8 offline buffers over experiment 19's OWN remembered worlds.

    `memory` is an experiment-19 `memory-<seed>` folder, opened read-only and
    hash-verified by the frozen `load_memory`; both arms store byte-identical world rows
    in the same order, so only the questions differ.  `dev_panels` is mandatory and is
    experiment 19's frozen panel folder: the collision abort must be armed here too, at
    the question level and at the primary (N/E) world level.
    """
    configure()
    folder = Path(out)
    forbidden, exclusion_record = N.build_exclusion_union(dev_panels, extra_exclusion)
    primary_worlds, primary_record = N.primary_world_exclusion(dev_panels)
    manifest_mem, mem, table = N.load_memory(memory)
    if int(manifest_mem['seed']) != int(seed):
        raise SystemExit(f'memory holds seed {manifest_mem["seed"]}, asked for {seed}')
    stories = mem['stories']
    qpw_mem = len(mem['items']) // len(stories)
    folder.mkdir(parents=True, exist_ok=True)
    began = time.time()
    per_arm, audits = {}, {}
    for arm in arms:
        if arm not in ARM_CALLS:
            raise SystemExit(f'unknown arm {arm!r}; 19b has {list(ARMS)}')
        histograms = _new_histograms()
        items, source, fallbacks = [], [], []
        for w, rows in enumerate(stories):
            awake_items = mem['items'][w * qpw_mem:(w + 1) * qpw_mem]
            chosen, made = propose_for_world(
                seed, w, rows, arm=arm, questions_per_world=questions_per_world,
                awake_items=awake_items, histograms=histograms)
            fallbacks.extend(made)
            for j, pick in enumerate(chosen):
                item = N.make_buffer_item(rows, w, pick['start'], pick['names'],
                                          len(rows) + j)
                signature = A.visible_signature(rows, item['question'])
                if signature in forbidden:
                    raise RuntimeError(
                        f'buffer-{arm} world {w} slot {j} collides with the exclusion '
                        f'union; run invalid')
                if N.composite_r10(pick['names']):
                    raise RuntimeError(f'composite r=10 reached buffer-{arm}; run invalid')
                items.append(item)
                source.append(dict(memory_index=w, slot=j, arm=arm,
                                   operation_string=' '.join(pick['names']),
                                   start=int(pick['start']), candidate=pick['candidate'],
                                   sampled=bool(pick['sampled']),
                                   namespace=pick['namespace']))
        block = N.encode_block(f'buffer-{arm}', seed, 0, mem['namespaces'], stories,
                               items, source)
        N.assert_worlds_allowed([block], primary_worlds, f'buffer-{arm}')
        path = folder / f'buffer-{arm}.pt'
        buffer_sha = N.save_chunk(path, [block], dict(
            kind=f'buffer-{arm}', seed=int(seed), worlds=len(stories),
            questions_per_world=questions_per_world, arm_calls=list(ARM_CALLS[arm]),
            execution_profile=execution_profile(), fingerprint=fingerprint()))
        audits[arm] = dict(
            arm=arm, calls=list(ARM_CALLS[arm]), worlds=len(stories),
            questions=len(items), questions_per_world=questions_per_world,
            candidates_per_world=CANDIDATES_PER_WORLD,
            proposed=histograms['proposed'], rejected=histograms['rejected'],
            rejected_types=histograms['rejected_types'], accepted=histograms['accepted'],
            fallback_types=histograms['fallback'], fallbacks=len(fallbacks),
            fallback_log=fallbacks[:256],
            fallback_duplicates_accepted=sum(1 for f in fallbacks
                                             if f['duplicates_accepted']),
            length_histogram=length_ending_histogram(items),
            revisits=revisit_report(items, stories), sha256=buffer_sha)
        per_arm[arm] = dict(block=block, items=items, source=source)
        if progress:
            print(f'  buffer-{arm}: {len(items)} questions, {len(fallbacks)} fallbacks, '
                  f'{time.time() - began:.1f}s', flush=True)

    identical = N._identical_world_bytes(per_arm)
    exposure = N.r10_exposure(mem, table, per_arm)
    pairing = paired_stream_report(per_arm)
    comparison = (compare_with_experiment19_u(per_arm.get(CONTROL_ARM), compare_buffers)
                  if compare_buffers else None)
    order = N.offline_order(seed, updates=offline_updates, visits=OFFLINE_VISITS,
                            worlds=len(stories))
    write_doc(folder / 'offline-order.json', dict(
        namespace=NS_ORDER, seed=int(seed), updates=int(offline_updates),
        visits=OFFLINE_VISITS, worlds=len(stories), chunk=N.OFFLINE_CHUNK,
        shared_with='experiment 19: the same NS_ORDER keys and the same seeds, so the '
                    'world-index order is identical',
        order_sha256=digest_of(order), order=order))
    questions, worlds_seen = set(), set()
    for payload in per_arm.values():
        q, w = N.block_signatures([payload['block']])
        questions |= q
        worlds_seen |= w
    published = N.write_forbidden(folder, questions, worlds_seen)
    audit_doc = dict(kind='buffers', experiment='19b', seed=int(seed), arms=list(arms),
                     per_arm=audits, identical_world_bytes=identical,
                     composite_r10_exposure=exposure,
                     stream_mapping=STREAM_MAPPING,
                     stream_mapping_sha256=STREAM_MAPPING_SHA256,
                     paired_streams=pairing,
                     u5_vs_experiment19_u=comparison,
                     offline_order_sha256=digest_of(order),
                     memory=dict(path=str(Path(memory).resolve()),
                                 manifest_sha256=sha(Path(memory) / 'manifest.json'),
                                 worlds=len(stories), read_only=True,
                                 experiment='fable-novelty19-replay-20260920'),
                     exclusion=exclusion_record,
                     primary_world_exclusion=primary_record,
                     published_exclusions=published,
                     execution_profile=execution_profile(), fingerprint=fingerprint())
    write_doc(folder / 'audit.json', audit_doc, seconds=time.time() - began)
    write_doc(folder / 'manifest.json', dict(
        kind='buffers', experiment='19b', seed=int(seed), arms=list(arms),
        files={f'buffer-{a}.pt': audits[a]['sha256'] for a in arms},
        audit_sha256=sha(folder / 'audit.json'),
        offline_order_sha256=sha(folder / 'offline-order.json'),
        stream_mapping_sha256=STREAM_MAPPING_SHA256,
        published_exclusions=published,
        execution_profile=execution_profile(), fingerprint=fingerprint()))
    return audit_doc


def paired_stream_report(per_arm):
    """Verify the pairing claim on the built buffers, not merely in prose.

    For every candidate slot both arms drew the same binding key, so a candidate
    accepted by both arms must carry the same start person; and each arm's accepted
    operation string must be exactly what its own length law returns for that key.
    """
    arms = [a for a in per_arm if a in ARM_CALLS]
    by_key = {}
    for arm in arms:
        for src in per_arm[arm]['source']:
            if src['candidate'] is None:
                continue
            by_key.setdefault((src['memory_index'], src['candidate']), {})[arm] = src
    shared, start_mismatch, law_mismatch = 0, 0, 0
    for (world, candidate), row in by_key.items():
        for arm, src in row.items():
            names = uniform_string(random.Random(src['namespace']), arm)
            if ' '.join(names) != src['operation_string']:
                law_mismatch += 1
        if len(row) == len(arms) > 1:
            shared += 1
            starts = {src['start'] for src in row.values()}
            if len(starts) != 1:
                start_mismatch += 1
    return dict(arms=arms, shared_candidate_slots=shared,
                start_mismatches=start_mismatch, length_law_mismatches=law_mismatch,
                verified=bool(start_mismatch == 0 and law_mismatch == 0),
                mapping_sha256=STREAM_MAPPING_SHA256,
                note='the RNG key never contains the arm, so a shared candidate slot '
                     'binds the same start person in both arms')


def _item_view(items, source):
    """The arm-independent content of a buffer: what U5 and experiment 19's U share."""
    return [dict(owner=int(it['owner']), question=list(it['question']),
                 chain=[list(step) for step in it['chain']], hops=int(it['hops']),
                 terminal=int(it['terminal']), answer=int(it['answer']),
                 operation_string=src['operation_string'], start=int(src['start']),
                 candidate=src['candidate'], sampled=bool(src['sampled']))
            for it, src in zip(items, source)]


def compare_with_experiment19_u(control, buffers19):
    """Is U5 experiment 19's U buffer?  Measured, not assumed.

    `.pt` bytes CANNOT be identical -- the block records its own `kind` ('buffer-U5')
    and this module's execution profile -- so the assertable claim is item-level
    identity: same questions, starts, chains, owners, answers and source operation
    strings, in the same order, over byte-identical world rows.
    """
    if control is None:
        return None
    old = N.load_buffer(buffers19, 'U')             # hash-verified against its manifest
    ours = N.decode_block(control['block'])
    mine = _item_view(ours['items'], ours['source'])
    theirs = _item_view(old['items'], old['source'])
    differing = [i for i, (a, b) in enumerate(zip(mine, theirs)) if a != b]
    same_worlds = ours['stories'] == old['stories']
    return dict(
        compared=str(Path(buffers19).resolve()), items=len(mine), other_items=len(theirs),
        identical_items=bool(len(mine) == len(theirs) and not differing),
        first_differences=differing[:8], identical_world_rows=bool(same_worlds),
        item_view_sha256=digest_of(mine), other_item_view_sha256=digest_of(theirs),
        byte_identical_file=False,
        note="U5 reuses experiment 19's memory, keys and 1..5 law, so it reproduces "
             "buffer-U item for item; the .pt differs only in the block's own kind "
             "string and execution profile, which is why identity is asserted at the "
             "item level")


def load_buffer(buffers, arm):
    """Hash-verified loader; the trainer's entry point for one arm of one seed."""
    return N.load_buffer(buffers, arm)


def offline_order(seed, updates=OFFLINE_UPDATES, visits=OFFLINE_VISITS,
                  worlds=MEMORY_WORLDS):
    """The SHARED world-index order both arms consume -- experiment 19's, unchanged."""
    return N.offline_order(seed, updates=updates, visits=visits, worlds=worlds)


# =========================================================================== the 38 cells


def _cells():
    """The 38 development cells of the readout, in the order the report prints them.

    The 26 old N/P/F/H/E specifications are taken from the FROZEN experiment-19 table
    (its 32 cells minus the six mixed-ending L cells) so they are the same objects, not
    a retyped copy.  Twelve are new:

      * nine SEPARATE-ending long cells, c=6/7/8 x r=8/9/10, sixteen people.  Experiment
        19 had six balanced 8/9-or-10 cells; separating the endings stops one practised
        ending concealing the other, and makes each long cell single-ending, hence
        answer-balanced by `target_answer` alone.
      * three c=8 held-out edit pairs repeating E's changed-LINK, changed-endpoint-value
        and irrelevant-edit constructions at the new length.

    `distinct=True` everywhere (ruling 5): every visited person is distinct on BOTH
    sides of every pair in every cell, which sixteen-person worlds make reachable at
    c=8.
    """
    cells = {name: dict(cfg) for name, cfg in N.DEV_CELLS.items()
             if not name.startswith('L-')}
    assert len(cells) == 26, f'{len(cells)} inherited cells, expected 26'
    for edit, invariant in (('link', False), ('value', False), ('irrelevant', True)):
        cells[f'E-c8-{edit}'] = N._cell(
            'pair', 8, PANEL_PEOPLE, 'heldout', HELDOUT_REL, edit=edit,
            invariant=invariant,
            title=f'c=8 held-out {edit}-edit twin pair, {PANEL_PEOPLE} people')
    for calls in (6, 7, 8):
        for relation in (FIRST_REL, FIRST_REL + 1, HELDOUT_REL):
            kind = 'heldout' if relation == HELDOUT_REL else 'practised'
            cells[f'L-c{calls}-r{relation}-p16'] = N._cell(
                'single', calls, PANEL_PEOPLE, kind, relation,
                title=f'bounded execution: c={calls}, r={relation} only, '
                      f'{PANEL_PEOPLE} people')
    return cells


CELLS = _cells()
CELL_ORDER = (
    [f'N-c{c}-p{p}' for c in (4, 5) for p in (TRAIN_PEOPLE, PANEL_PEOPLE)]
    + [f'E-c5-{e}' for e in ('link', 'value', 'irrelevant')]
    + [f'E-c8-{e}' for e in ('link', 'value', 'irrelevant')]
    + [f'F-c1-r{r}' for r in (FIRST_REL, FIRST_REL + 1, HELDOUT_REL)]
    + [f'F-c{c}-r{r}' for c in (2, 3) for r in PRACTISED_RELS]
    + [f'P-c{c}-r{r}-p{p}' for c in (4, 5) for r in PRACTISED_RELS
       for p in (TRAIN_PEOPLE, PANEL_PEOPLE)]
    + [f'H-c{c}-p{p}' for c in (2, 3) for p in (TRAIN_PEOPLE, PANEL_PEOPLE)]
    + [f'L-c{c}-r{r}-p16' for c in (6, 7, 8)
       for r in (FIRST_REL, FIRST_REL + 1, HELDOUT_REL)])
assert sorted(CELL_ORDER) == sorted(CELLS), '19b cell order/table disagree'
assert len(CELLS) == 38, f'{len(CELLS)} development cells, expected 38'
FAMILY_SIZES = dict(N=4, E=6, F=7, P=8, H=4, L=9)
assert {k: sum(1 for c in CELLS if c.startswith(k + '-')) for k in FAMILY_SIZES} \
    == FAMILY_SIZES
assert sum(FAMILY_SIZES.values()) == 38
PRIMARY_FAMILIES = N.PRIMARY_FAMILIES              # ('N', 'E'): never-trained + twins

# the readout's prospective marks, carried with the cells so the trainer and the report
# read ONE table.  `n=64` development, `n=512` confirmation (58->464, 61->488, 13->104,
# 7->56).  These are thresholds on units, evaluated per seed; nothing here scores.
MARKS = dict(
    bounded_competence=dict(
        condition=1, metric='answers AND strict traces', arm='U8', dev=58, confirm=464,
        n_dev=DEV_N, n_confirm=CONFIRM_N,
        cells=([f'N-c{c}-p{p}' for c in (4, 5) for p in (TRAIN_PEOPLE, PANEL_PEOPLE)]
               + [f'P-c{c}-r{r}-p{p}' for c in (4, 5) for r in PRACTISED_RELS
                  for p in (TRAIN_PEOPLE, PANEL_PEOPLE)]
               + [f'L-c{c}-r{r}-p16' for c in (6, 7, 8)
                  for r in (FIRST_REL, FIRST_REL + 1, HELDOUT_REL)])),
    treatment_effect=dict(
        condition=2, metric='U8 strict minus U5 strict on identical units', dev=13,
        confirm=104, paired=True,
        cells=[f'L-c{c}-r{HELDOUT_REL}-p16' for c in (6, 7, 8)]),
    guards=dict(condition=3, metric='strict pair units, both branches', arm='U8',
                dev=58, confirm=464,
                cells=[f'E-c{c}-{e}' for c in (5, 8)
                       for e in ('link', 'value', 'irrelevant')]),
    retention_f=dict(condition=4, metric='answers AND strict', arm='U8', dev=61,
                     confirm=488, cells=[c for c in CELL_ORDER if c.startswith('F-')]),
    retention_h=dict(condition=4, metric='answers AND strict', arm='U8', dev=58,
                     confirm=464, max_loss_vs_awake_anchor=dict(dev=7, confirm=56),
                     cells=[c for c in CELL_ORDER if c.startswith('H-')]))


def registered_cells(cells=None):
    """Expose the 19b cells to `V3.audit_side` / `V3.audit_unit` for the duration."""
    return N.registered_cells(CELLS if cells is None else cells)


def cell_table(cells=None):
    """`{cell: {family, hops, ending, people, kind, mark}}` -- the trainer's census."""
    cells = CELLS if cells is None else cells
    marked = {}
    for name, mark in MARKS.items():
        for cell in mark['cells']:
            marked.setdefault(cell, []).append(name)
    out = {}
    for cell in [c for c in CELL_ORDER if c in cells] + \
                [c for c in cells if c not in CELL_ORDER]:
        cfg = cells[cell]
        out[cell] = dict(family=cell.split('-')[0], hops=cfg['hops'],
                         people=cfg['people'], kind=cfg['kind'],
                         terminal=cfg['terminal'], ending=cfg['fixed_terminal'],
                         edit=cfg['edit'], invariant=cfg['invariant'],
                         distinct=cfg['distinct'], title=cfg['title'],
                         marks=marked.get(cell, []))
    return out


# =========================================================================== exclusions


def experiment19_folders(root=EXP19, seeds=SEEDS):
    """Every experiment-19 artifact folder the fresh panels must avoid, read-only."""
    root = Path(root)
    out = {}
    for seed in seeds:
        for key in ('stream', 'memory', 'buffers'):
            out[f'exp19_{key}_{seed}'] = root / EXP19_LAYOUT[key].format(seed=seed)
    out['exp19_dev_panels'] = root / EXP19_LAYOUT['dev_panels']
    return out


def buffer_folders(experiment=EXP2_DEFAULT, seeds=SEEDS):
    root = Path(experiment)
    return {f'buffers_{seed}': root / LAYOUT['buffers'].format(seed=seed)
            for seed in seeds}


def panel_exclusion_folders(experiment=EXP2_DEFAULT, exp19=EXP19, seeds=SEEDS,
                            confirmation=False):
    """The folders whose questions AND worlds the fresh 19b panels must exclude.

    The operator history is handled separately (ruling 2 makes a COMPLETE
    reconstruction a prerequisite, not merely an exclusion source).  Confirmation adds
    the 19b development panels themselves.
    """
    folders = dict(experiment19_folders(exp19, seeds))
    folders.update(buffer_folders(experiment, seeds))
    if confirmation:
        folders['dev_panels_19b'] = Path(experiment) / LAYOUT['dev_panels']
    return folders


def collect_exclusions(folders):
    """Union the published question/world signatures of every folder, VERIFIED.

    Each file is hashed and counted against the `published_exclusions` block of the
    manifest that produced it (audit re-check 2, R2-7), so a truncated or edited
    exclusion file is refused rather than silently narrowing the union.  The returned
    records are the provenance the consumer writes into its own manifest.
    """
    questions, worlds, records = set(), set(), []
    for name, folder in folders.items():
        sets = N.artifact_exclusions(folder)
        questions |= sets['questions']
        worlds |= sets['worlds']
        records.append(dict(name=name, **sets['record']))
    return questions, worlds, records


# =========================================================================== lockout


def validate_dev_passed(experiment, *, panels_folder=None, seeds=SEEDS):
    """19b's confirmation lockout: three awake and six offline D checkpoints.

    Identical in shape to experiment 19's, with 19b's schema string and 19b's
    checkpoint roster (`D-<seed>` and `D-U5/U8-<seed>`).  Anything short of the full
    schema REFUSES, and the recorded dev-panel manifest hash is checked against disk.
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
        raise SystemExit(f'{flag} seeds are {doc.get("seeds")!r}, expected {list(seeds)}')
    if not N.HEX64.match(str(doc.get('report_sha256', ''))):
        raise SystemExit(f'{flag} has no valid report_sha256')
    panels = doc.get('dev_panels')
    if not isinstance(panels, dict) or not N.HEX64.match(
            str(panels.get('manifest_sha256', ''))):
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
        bad = sorted(k for k, v in got.items() if not N.HEX64.match(str(v)))
        if bad:
            raise SystemExit(f'{flag} {field} entries are not sha256: {bad[:6]}')
    return dict(path=str(flag.resolve()), sha256=sha(flag),
                schema=DEV_PASSED_SCHEMA, report_sha256=doc['report_sha256'],
                dev_panels=dict(path=str(folder.resolve()), manifest_sha256=on_disk),
                awake_checkpoints=len(doc['awake_checkpoints']),
                offline_checkpoints=len(doc['offline_checkpoints']))


# =========================================================================== dev panels


def build_dev_panels(out, *, n=DEV_N, namespace=NS_DEV, cells=None, cell_order=None,
                     attempts=DEV_ATTEMPTS, confirmation=False, experiment=None,
                     exp19=EXP19, operator_history=None, require_full_history=True,
                     seeds=SEEDS, extra_exclusion=(), exclusion_folders=None,
                     progress=True, budget=None):
    """The 38 fresh development cells, in the SAME JSON shape as experiment 19's panels.

    Construction is the frozen `dev_unit` verbatim -- interpreter-only, a fixed
    rejection limit, every attempt logged, every accepted unit re-audited by
    `V3.audit_unit`, an audit problem ABORTS.  What 19b changes is the exclusion union:
    besides the legacy sources and the operator history, the panels must avoid EVERY
    experiment-19 training/replay/candidate artifact, experiment 19's own development
    panels, and all 19b buffer worlds -- at the question-signature level AND the
    question-free world level, on both sides of every pair.

    Every source file is hash- and count-verified against the manifest that published
    it, BEFORE the output folder is created, so a refused build never leaves a
    half-written panel folder behind; `consumed_exclusions` records exactly which bytes
    were read.  With `confirmation=True` the 19b development panels join the union and
    the build REFUSES until `<experiment>/DEV-PASSED.json` validates in full.
    """
    cells = CELLS if cells is None else cells
    order = cell_order or [c for c in CELL_ORDER if c in cells] + \
        [c for c in cells if c not in CELL_ORDER]
    if experiment is None:
        experiment = EXP2_DEFAULT
    if operator_history is None:
        operator_history = Path(exp19) / EXP19_LAYOUT['operator_history']
    if not confirmation and namespace == NS_CONFIRM:
        raise SystemExit('the confirmation namespace needs the explicit --confirmation flag')
    if not require_full_history and namespace in (NS_DEV, NS_CONFIRM):
        raise SystemExit('a partial operator history may never back a registered '
                         'namespace; use a fixture namespace for that')
    passed_record = validate_dev_passed(experiment, seeds=seeds) if confirmation else None
    history_manifest, history = N.load_operator_history(
        operator_history, require_full=require_full_history)
    configure()
    # ---- every exclusion source is read and VERIFIED before `out` exists -------
    legacy, legacy_record = N.B2.exclusion_union(
        [str(p) for p in N.legacy_exclusion_paths(extra_exclusion)])
    folders = (panel_exclusion_folders(experiment, exp19, seeds, confirmation)
               if exclusion_folders is None else dict(exclusion_folders))
    source_questions, source_worlds, source_records = collect_exclusions(folders)
    exclusions = frozenset(legacy) | history['questions'] | source_questions
    world_exclusions = frozenset(history['worlds']) | source_worlds
    folder = Path(out)
    folder.mkdir(parents=True, exist_ok=False)
    began = time.time()
    semantic, tensors, panel_worlds, primary_worlds = set(), set(), set(), set()
    manifest = dict(
        experiment='19b', namespace=namespace, n=int(n),
        kind='confirmation' if confirmation else 'development',
        source_sha256=sha(__file__), frozen_source_sha256=sha(N.__file__),
        v3_source_sha256=sha(V3.__file__),
        execution_profile=execution_profile(), fingerprint=fingerprint(),
        frozen_before_any_training=True,
        stratification='target_answer(index) = 12 + index % 16, outcome-independent and '
                       'fixed before generation; 19b has no mixed-ending cell, so every '
                       'cell is single-ending and balanced by that alone (ruling 6 '
                       'would apply if one were added)',
        rulings='design/v3/19-rulings-1.md rulings 5 and 6; '
                'design/v3/19-development-readout-and-next-step.md "Prospective marks"',
        legacy_exclusion=legacy_record,
        operator_history=dict(
            path=str(Path(operator_history).resolve()),
            manifest_sha256=sha(Path(operator_history) / 'manifest.json'),
            complete=bool(history_manifest.get('complete')),
            worlds=len(history['worlds']), questions=len(history['questions']),
            world_union_sha256=history_manifest['world_union_sha256'],
            source=history['record']),
        excluded_sources=dict(
            folders={k: str(Path(v).resolve()) for k, v in folders.items()},
            questions=len(source_questions), worlds=len(source_worlds),
            world_union_sha256=N.world_union_digest(source_worlds)),
        consumed_exclusions=([dict(name='legacy', **s) for s in legacy_record['sources']]
                             + [dict(name='operator_history', **history['record'])]
                             + source_records),
        exclusion_levels=['question_signature', 'world_signature'],
        dev_passed=passed_record, attempt_limit=int(attempts),
        cells={}, cell_order=list(order), families=FAMILY_SIZES,
        marks=MARKS, cell_table=cell_table(cells))
    with registered_cells(cells):
        for cell in order:
            cfg = cells[cell]
            units, rejections, attempts_used = [], {}, []
            for index in range(n):
                unit, signatures, worlds = N.dev_unit(
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
            answers, endings = {}, {}
            for unit in units:
                answer = unit['a']['answer']
                answers[answer] = answers.get(answer, 0) + 1
                key = (answer, int(unit['a']['question'][-2]))
                endings[key] = endings.get(key, 0) + 1
            path = folder / f'{cell}.json'
            write_doc(path, dict(cell=cell, n=int(n), namespace=namespace,
                                 kind=cfg['kind'], title=cfg['title'], hops=cfg['hops'],
                                 people=cfg['people'], terminal=cfg['terminal'],
                                 distinct=cfg['distinct'], invariant=cfg['invariant'],
                                 edit=cfg['edit'], fixed_terminal=cfg['fixed_terminal'],
                                 units=units, rejections=rejections))
            manifest['cells'][cell] = dict(
                path=str(path), sha256=sha(path), n=int(n), kind=cfg['kind'],
                hops=cfg['hops'], people=cfg['people'], terminal=cfg['terminal'],
                fixed_terminal=cfg['fixed_terminal'], title=cfg['title'],
                family=cell.split('-')[0], rejections=rejections,
                attempts_total=sum(attempts_used), attempts_max=max(attempts_used),
                attempt_limit=int(attempts),
                answer_histogram={str(k): v for k, v in sorted(answers.items())},
                answer_values=len(answers),
                answer_evenly_stratified=bool(len(answers) == VALUE_COUNT
                                              and set(answers.values())
                                              == {n // VALUE_COUNT}),
                endings=sorted({int(e) for _, e in endings}),
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
    published = N.write_forbidden(folder, semantic, panel_worlds,
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
                excluded_source_questions=len(source_questions),
                excluded_source_worlds=len(source_worlds),
                operator_history_worlds=len(history['worlds']),
                seconds=time.time() - began,
                manifest_sha256=sha(folder / 'manifest.json'))


def load_dev_panels(panels, cells=None):
    """Hash-verified panel loader; the trainer's entry point for the suites."""
    return N.load_dev_panels(panels, cells)


def dev_panel_worlds(panels):
    """The panels' published world signatures: all cells, and the primary cells alone."""
    return N.dev_panel_worlds(panels)


def whole_cell(panel, units=None):
    """Refuse a partial cell: the answer is a function of the unit index."""
    return N.whole_cell(panel, units)


def family_sizes(cells=None):
    """`{family: cells}` for a cell table; the registered table gives `FAMILY_SIZES`."""
    cells = CELLS if cells is None else cells
    out = {}
    for cell in cells:
        family = cell.split('-')[0]
        out[family] = out.get(family, 0) + 1
    return out


def census(manifest, cells=None):
    """The 38-cell census: purity, endings and answer balance, per family and cell."""
    cells = CELLS if cells is None else cells
    rows, families, impure = {}, {}, []
    for cell, row in manifest['cells'].items():
        cfg = cells.get(cell)
        family = cell.split('-')[0]
        families[family] = families.get(family, 0) + 1
        pure = bool(cfg is not None and row['hops'] == cfg['hops']
                    and row['people'] == cfg['people'] and row['kind'] == cfg['kind']
                    and row['terminal'] == cfg['terminal']
                    and row['fixed_terminal'] == cfg['fixed_terminal']
                    and len(row['endings']) == 1
                    and row['endings'][0] == int(cfg['fixed_terminal']))
        if not pure:
            impure.append(cell)
        rows[cell] = dict(family=family, hops=row['hops'], people=row['people'],
                          kind=row['kind'], endings=row['endings'],
                          answer_values=row['answer_values'],
                          answer_evenly_stratified=row['answer_evenly_stratified'],
                          answer_ending_balanced=row.get('answer_ending_balanced'),
                          attempts_max=row.get('attempts_max'),
                          attempt_limit=row.get('attempt_limit'), pure=pure)
    # a registered build audits the full 38; a fixture audits exactly the cells it was
    # given, so the census is never satisfied by simply building fewer cells
    expected = family_sizes(cells)
    return dict(cells=len(rows), families=families, expected_families=expected,
                expected_cells=len(cells),
                families_match=bool(families == expected), impure_cells=impure,
                all_single_ending=bool(all(len(r['endings']) == 1 for r in rows.values())),
                answer_stratified=bool(all(r['answer_evenly_stratified']
                                           for r in rows.values())),
                answer_ending_balanced=bool(all(r['answer_ending_balanced']
                                                for r in rows.values())),
                per_cell=rows)


# =========================================================================== audit


EXPECTED_AUDIT_CHECKS = (
    'exclusion_files_match_their_manifests',
    'memory_hashes_verified', 'memory_bytes_identical_to_experiment_19',
    'buffer_hashes', 'identical_world_bytes_and_order', 'buffer_shape',
    'buffer_worlds_are_the_memory_worlds', 'buffers_zero_composite_r10',
    'buffer_labels_match_the_fixed_interpreter', 'buffer_accepted_length_support',
    'buffer_revisits_disclosed', 'buffers_published_exclusions',
    'buffers_disjoint_from_dev_panels', 'buffers_worlds_disjoint_from_dev_panels',
    'paired_stream_mapping', 'u5_matches_experiment_19_u',
    'offline_order_reproducible', 'offline_order_matches_experiment_19',
    'recorded_zero_exposure_audit',
    'dev_panel_hashes', 'dev_panel_cell_count', 'dev_panel_census',
    'dev_panel_answer_stratification', 'dev_panel_mixed_ending_balance',
    'dev_panel_attempt_limit', 'dev_panel_world_exclusions_published',
    'dev_panel_excluded_the_operator_history', 'operator_history_complete',
    'panels_disjoint_from_every_excluded_source',
    'panels_worlds_disjoint_from_every_excluded_source',
    'execution_profiles_agree',
)


def audit_everything(seed, *, buffers, dev_panels, memory=None, experiment=None,
                     exp19=EXP19, operator_history=None, require_full_history=True,
                     seeds=SEEDS, cells=None, exclusion_folders=None):
    """Re-verify every 19b artifact FROM DISK and return one verdict.

    Experiment 19's roster adapted to 19b.  Every source is MANDATORY and an ABSENT
    check is itself a failure, so dropping an artifact can never quietly shrink the
    audit.  Nothing here is read from an in-memory build: the buffers, panels, memory,
    exclusion files and manifests are all re-read and re-hashed.
    """
    configure()
    experiment = Path(experiment or EXP2_DEFAULT)
    exp19 = Path(exp19)
    memory = Path(memory or exp19 / EXP19_LAYOUT['memory'].format(seed=seed))
    operator_history = Path(operator_history
                            or exp19 / EXP19_LAYOUT['operator_history'])
    verdict = dict(experiment='19b', seed=int(seed), checks={}, failures=[],
                   fingerprint=fingerprint())

    def check(name, ok, detail=None):
        if name not in EXPECTED_AUDIT_CHECKS:
            raise AssertionError(f'check {name!r} is not in EXPECTED_AUDIT_CHECKS')
        verdict['checks'][name] = dict(passed=bool(ok), detail=detail)
        if not ok:
            verdict['failures'].append(name)

    # FIRST: every exclusion file must still be the one its producer published
    folders = dict(buffers=Path(buffers), dev_panels=Path(dev_panels),
                   operator_history=operator_history)
    folders.update(panel_exclusion_folders(experiment, exp19, seeds)
                   if exclusion_folders is None else dict(exclusion_folders))
    tampered, verified, records = {}, {}, {}
    for name, folder in folders.items():
        try:
            sets = N.artifact_exclusions(folder, primary=('dev_panels' in name))
            verified[name] = sets
            records[name] = sets['record']
        except SystemExit as exc:
            tampered[name] = str(exc)
    check('exclusion_files_match_their_manifests', not tampered, tampered or records)
    if tampered:
        return _finish_audit(verdict, aborted='a consumed exclusion file does not match '
                                              'the manifest that published it')

    history_manifest, history = N.load_operator_history(
        operator_history, require_full=require_full_history)
    profiles = {}

    def profile(name, doc):
        if isinstance(doc, dict) and doc.get('execution_profile'):
            profiles[name] = doc['execution_profile']

    # ---- memory: experiment 19's own bytes, read-only --------------------------
    manifest_mem, mem, _table = N.load_memory(memory)
    check('memory_hashes_verified', int(manifest_mem['seed']) == int(seed),
          dict(path=str(memory.resolve()), worlds=manifest_mem['worlds'],
               manifest_sha256=sha(memory / 'manifest.json'),
               seed=int(manifest_mem['seed'])))

    # ---- buffers ---------------------------------------------------------------
    folder = Path(buffers)
    manifest_buf = json.loads((folder / 'manifest.json').read_text())
    audit_doc = json.loads((folder / 'audit.json').read_text())
    if sha(folder / 'audit.json') != manifest_buf['audit_sha256']:
        raise RuntimeError('buffer audit.json changed on disk')
    profile('buffers', manifest_buf)
    profile('buffers_audit', audit_doc)
    loaded = {arm: N.load_buffer(folder, arm) for arm in manifest_buf['arms']}
    check('buffer_hashes', sorted(loaded) == sorted(ARMS), dict(arms=sorted(loaded)))
    first = loaded[manifest_buf['arms'][0]]
    same = all(other['stories'] == first['stories']
               and [it['owner'] for it in other['items']]
               == [it['owner'] for it in first['items']]
               for other in loaded.values())
    check('identical_world_bytes_and_order', same,
          dict(arms=sorted(loaded), worlds=len(first['stories'])))
    check('buffer_shape',
          all(len(rec['items']) == len(rec['stories']) * BUFFER_QUESTIONS_PER_WORLD
              for rec in loaded.values()),
          {a: len(r['items']) for a, r in loaded.items()})
    check('memory_bytes_identical_to_experiment_19',
          all(rec['stories'] == mem['stories'] for rec in loaded.values())
          and audit_doc['memory']['manifest_sha256'] == sha(memory / 'manifest.json'),
          dict(worlds=len(mem['stories']),
               recorded=audit_doc['memory']['manifest_sha256'],
               on_disk=sha(memory / 'manifest.json')))
    check('buffer_worlds_are_the_memory_worlds',
          all({it['world_signature'] for it in rec['items']}
              == {it['world_signature'] for it in mem['items']}
              for rec in loaded.values()),
          dict(memory_worlds=len({it['world_signature'] for it in mem['items']})))
    offending = {}
    for arm, rec in loaded.items():
        bad = sorted({' '.join(N.op_names(it['question'][2:-1])) for it in rec['items']
                      if N.composite_r10(N.op_names(it['question'][2:-1]))})
        if bad:
            offending[arm] = bad
    check('buffers_zero_composite_r10', not offending, offending or dict(arms=sorted(loaded)))
    relabelled = {arm: sum(1 for it in rec['items']
                           if N.label_question(rec['stories'][it['owner']],
                                               it['question']) != it['chain'])
                  for arm, rec in loaded.items()}
    check('buffer_labels_match_the_fixed_interpreter',
          all(v == 0 for v in relabelled.values()), relabelled)
    support, histograms = {}, {}
    for arm, rec in loaded.items():
        histograms[arm] = length_ending_histogram(rec['items'])
        support[arm] = sorted({int(it['hops']) for it in rec['items']})
    check('buffer_accepted_length_support',
          all(set(support[a]) <= set(ARM_CALLS[a]) for a in support)
          and max(support[TREATMENT_ARM]) > max(support[CONTROL_ARM]),
          dict(support=support, allowed={a: list(ARM_CALLS[a]) for a in support},
               length_ending_histogram=histograms))
    revisits = {arm: revisit_report(rec['items'], rec['stories'])
                for arm, rec in loaded.items()}
    check('buffer_revisits_disclosed',
          all(audit_doc['per_arm'][a].get('revisits') is not None for a in loaded),
          {a: dict(with_revisits=r['with_revisits'], units=r['units'])
           for a, r in revisits.items()})
    buffer_questions, buffer_worlds = set(), set()
    for rec in loaded.values():
        buffer_questions |= {it['signature'] for it in rec['items']}
        buffer_worlds |= {it['world_signature'] for it in rec['items']}
    buffer_sets = verified['buffers']
    check('buffers_published_exclusions',
          buffer_questions <= buffer_sets['questions']
          and buffer_worlds <= buffer_sets['worlds'],
          dict(published_questions=len(buffer_sets['questions']),
               published_worlds=len(buffer_sets['worlds'])))
    check('paired_stream_mapping',
          paired_stream_check(loaded)['verified']
          and audit_doc.get('stream_mapping_sha256') == STREAM_MAPPING_SHA256,
          dict(recomputed=paired_stream_check(loaded),
               recorded_sha256=audit_doc.get('stream_mapping_sha256'),
               expected_sha256=STREAM_MAPPING_SHA256))
    old_buffers = exp19 / EXP19_LAYOUT['buffers'].format(seed=seed)
    identity = compare_loaded_with_experiment19_u(loaded.get(CONTROL_ARM), old_buffers)
    check('u5_matches_experiment_19_u', bool(identity['identical_items']
                                             and identity['identical_world_rows']),
          identity)
    order = json.loads((folder / 'offline-order.json').read_text())
    rebuilt = N.offline_order(seed, updates=order['updates'], visits=order['visits'],
                              worlds=order['worlds'])
    check('offline_order_reproducible', rebuilt == order['order'],
          dict(updates=order['updates'], sha256=order['order_sha256']))
    old_order = json.loads((old_buffers / 'offline-order.json').read_text())
    check('offline_order_matches_experiment_19',
          old_order['order'] == order['order'],
          dict(sha256=order['order_sha256'], experiment_19=old_order['order_sha256']))
    check('recorded_zero_exposure_audit',
          audit_doc['composite_r10_exposure']['zero_exposure'], None)

    # ---- development panels ----------------------------------------------------
    dev_manifest, panels, dev_forbidden = N.load_dev_panels(dev_panels)
    dev_worlds, dev_primary_worlds = N.dev_panel_worlds(dev_panels)
    profile('dev_panels', dev_manifest)
    check('dev_panel_hashes', True,
          dict(cells=len(panels), signatures=len(dev_forbidden), worlds=len(dev_worlds),
               primary_worlds=len(dev_primary_worlds),
               manifest_sha256=sha(Path(dev_panels) / 'manifest.json')))
    wanted = CELLS if cells is None else cells
    check('dev_panel_cell_count', len(panels) == len(wanted),
          dict(cells=len(panels), expected=len(wanted),
               registered=bool(cells is None)))
    table = census(dev_manifest, wanted)
    check('dev_panel_census',
          table['families_match'] and not table['impure_cells']
          and table['all_single_ending'],
          {k: v for k, v in table.items() if k != 'per_cell'})
    even = {c: r['answer_evenly_stratified'] for c, r in dev_manifest['cells'].items()}
    check('dev_panel_answer_stratification', all(even.values()),
          {c: v for c, v in even.items() if not v} or dict(cells=len(even)))
    balanced = {c: r.get('answer_ending_balanced')
                for c, r in dev_manifest['cells'].items()}
    check('dev_panel_mixed_ending_balance', all(bool(v) for v in balanced.values()),
          {c: v for c, v in balanced.items() if not v} or dict(cells=len(balanced)))
    limits = {c: (r.get('attempt_limit'), r.get('attempts_max'))
              for c, r in dev_manifest['cells'].items()}
    check('dev_panel_attempt_limit',
          all(lim and used and used <= lim for lim, used in limits.values()),
          dict(limit=dev_manifest.get('attempt_limit'),
               worst={c: v for c, v in sorted(limits.items(),
                                              key=lambda kv: -(kv[1][1] or 0))[:3]}))
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

    # ---- panels versus EVERY excluded source, both levels ----------------------
    source_questions, source_worlds = set(), set()
    per_source = {}
    for name, sets in verified.items():
        if name in ('dev_panels', 'operator_history'):
            continue
        per_source[name] = dict(questions=len(dev_forbidden & sets['questions']),
                                worlds=len(dev_worlds & sets['worlds']))
        source_questions |= sets['questions']
        source_worlds |= sets['worlds']
    check('panels_disjoint_from_every_excluded_source',
          not (dev_forbidden & source_questions)
          and all(v['questions'] == 0 for v in per_source.values()),
          dict(sources=per_source, source_questions=len(source_questions)))
    check('panels_worlds_disjoint_from_every_excluded_source',
          not (dev_worlds & source_worlds)
          and all(v['worlds'] == 0 for v in per_source.values()),
          dict(sources=per_source, source_worlds=len(source_worlds),
               panel_worlds=len(dev_worlds)))
    check('buffers_disjoint_from_dev_panels', not (buffer_questions & dev_forbidden),
          dict(overlap=len(buffer_questions & dev_forbidden)))
    check('buffers_worlds_disjoint_from_dev_panels', not (buffer_worlds & dev_worlds),
          dict(overlap=len(buffer_worlds & dev_worlds),
               primary_overlap=len(buffer_worlds & dev_primary_worlds),
               buffer_worlds=len(buffer_worlds)))

    distinct = {digest_of(p): p for p in profiles.values()}
    check('execution_profiles_agree', len(distinct) == 1,
          dict(manifests=sorted(profiles),
               profiles=[{k: v for k, v in p.items() if k != 'sources'}
                         for p in distinct.values()]))
    return _finish_audit(verdict)


def _finish_audit(verdict, *, aborted=None):
    """Close a verdict against 19b's OWN roster: an absent check is itself a failure.

    The frozen `_finish_audit` closes against experiment 19's 37-name roster, so 19b
    needs its own -- otherwise a complete 19b audit would report 31/37 and fail.
    """
    absent = [name for name in EXPECTED_AUDIT_CHECKS if name not in verdict['checks']]
    verdict['checks_run'] = len(verdict['checks'])
    verdict['checks_expected'] = len(EXPECTED_AUDIT_CHECKS)
    verdict['checks_absent'] = absent
    if aborted:
        verdict['aborted'] = aborted
    elif absent:
        verdict['failures'].append('expected_checks_absent')
    verdict['passed'] = not verdict['failures']
    return verdict


def paired_stream_check(loaded):
    """`paired_stream_report` over buffers re-read from disk."""
    return paired_stream_report({arm: dict(source=rec['source'], items=rec['items'])
                                 for arm, rec in loaded.items() if arm in ARM_CALLS})


def compare_loaded_with_experiment19_u(control, buffers19):
    """The U5-vs-U identity, recomputed from the two buffers ON DISK."""
    if control is None:
        return dict(identical_items=False, identical_world_rows=False,
                    error='no U5 buffer loaded')
    old = N.load_buffer(buffers19, 'U')
    mine = _item_view(control['items'], control['source'])
    theirs = _item_view(old['items'], old['source'])
    differing = [i for i, (a, b) in enumerate(zip(mine, theirs)) if a != b]
    return dict(compared=str(Path(buffers19).resolve()), items=len(mine),
                other_items=len(theirs),
                identical_items=bool(len(mine) == len(theirs) and not differing),
                first_differences=differing[:8],
                identical_world_rows=bool(control['stories'] == old['stories']),
                item_view_sha256=digest_of(mine),
                other_item_view_sha256=digest_of(theirs), byte_identical_file=False)


# =========================================================================== CLI


def _folder_overrides(values):
    """`--exclusion-folder name=path`, repeatable: REPLACES the default source set.

    Fixtures use it to point the panel build at a disposable experiment; a registered
    build never passes it, and the manifest records whichever folders were consumed.
    """
    if not values:
        return None
    out = {}
    for value in values:
        if '=' not in value:
            raise SystemExit(f'--exclusion-folder wants name=path, got {value!r}')
        name, path = value.split('=', 1)
        out[name] = Path(path)
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = parser.add_subparsers(dest='command', required=True)

    p = sub.add_parser('buffers', help='the U5 and U8 offline buffers for one seed')
    p.add_argument('--seed', type=int, required=True)
    p.add_argument('--memory', default=None,
                   help="experiment 19's memory-<seed> folder (read-only, hash-verified)")
    p.add_argument('--out', default=None, help='EXP2/buffers-<seed>')
    p.add_argument('--dev-panels', default=None,
                   help="REQUIRED guard: experiment 19's frozen dev-panels folder")
    p.add_argument('--compare-buffers', default=None,
                   help="experiment 19's buffers-<seed>, for the U5 identity check")
    p.add_argument('--no-compare', action='store_true')
    p.add_argument('--extra-exclusion', action='append', default=[])
    p.add_argument('--offline-updates', type=int, default=OFFLINE_UPDATES)
    p.add_argument('--arms', default=','.join(ARMS))
    p.add_argument('--experiment', default=None)
    p.add_argument('--exp19', default=None)
    p.add_argument('--quiet', action='store_true')

    p = sub.add_parser('dev-panels', help='the 38 fresh development cells')
    p.add_argument('--out', default=None, help='EXP2/dev-panels')
    p.add_argument('--n', type=int, default=DEV_N)
    p.add_argument('--namespace', default=NS_DEV)
    p.add_argument('--cells', default=None, help='comma-separated subset, for fixtures')
    p.add_argument('--attempts', type=int, default=DEV_ATTEMPTS)
    p.add_argument('--extra-exclusion', action='append', default=[])
    p.add_argument('--exclusion-folder', action='append', default=[],
                   help='name=path; replaces the default excluded-source set (fixtures)')
    p.add_argument('--experiment', default=None)
    p.add_argument('--exp19', default=None)
    p.add_argument('--operator-history', default=None)
    p.add_argument('--fixture-history', action='store_true',
                   help='fixtures only: accept a partial operator history')
    p.add_argument('--confirmation', action='store_true',
                   help='LOCKED: needs <experiment>/DEV-PASSED.json (19b schema)')
    p.add_argument('--budget', type=float, default=None)
    p.add_argument('--quiet', action='store_true')

    p = sub.add_parser('audit', help='re-verify every 19b artifact from disk')
    p.add_argument('--seed', type=int, required=True)
    p.add_argument('--buffers', default=None)
    p.add_argument('--dev-panels', default=None)
    p.add_argument('--memory', default=None)
    p.add_argument('--experiment', default=None)
    p.add_argument('--exp19', default=None)
    p.add_argument('--operator-history', default=None)
    p.add_argument('--exclusion-folder', action='append', default=[])
    p.add_argument('--fixture-history', action='store_true')

    p = sub.add_parser('cells', help='print the 38-cell table, marks and trainer API')

    args = parser.parse_args(argv)
    exp19 = Path(args.exp19 or EXP19) if hasattr(args, 'exp19') else EXP19
    experiment = Path(getattr(args, 'experiment', None) or EXP2_DEFAULT)

    if args.command == 'buffers':
        memory = args.memory or exp19 / EXP19_LAYOUT['memory'].format(seed=args.seed)
        out = args.out or experiment / LAYOUT['buffers'].format(seed=args.seed)
        dev_panels = args.dev_panels or exp19 / EXP19_LAYOUT['dev_panels']
        compare = None if args.no_compare else (
            args.compare_buffers
            or exp19 / EXP19_LAYOUT['buffers'].format(seed=args.seed))
        doc = build_buffers(out, args.seed, memory, dev_panels=dev_panels,
                            extra_exclusion=args.extra_exclusion,
                            arms=tuple(a for a in args.arms.split(',') if a),
                            offline_updates=args.offline_updates,
                            compare_buffers=compare, progress=not args.quiet)
        print(json.dumps(dict(
            seed=doc['seed'], arms=doc['arms'],
            identical_world_bytes=doc['identical_world_bytes']['identical'],
            zero_composite_r10_exposure=doc['composite_r10_exposure']['zero_exposure'],
            paired_streams=doc['paired_streams'],
            u5_vs_experiment19_u=doc['u5_vs_experiment19_u'],
            fallbacks={a: doc['per_arm'][a]['fallbacks'] for a in doc['arms']},
            length_histogram={a: doc['per_arm'][a]['length_histogram']
                              for a in doc['arms']}), indent=2))
        return doc
    if args.command == 'dev-panels':
        cells = None
        if args.cells:
            cells = {name: CELLS[name] for name in args.cells.split(',') if name}
        out = args.out or (experiment / LAYOUT['confirm_panels'] if args.confirmation
                           else experiment / LAYOUT['dev_panels'])
        doc = build_dev_panels(
            out, n=args.n, namespace=args.namespace, cells=cells,
            attempts=args.attempts, confirmation=args.confirmation,
            experiment=experiment, exp19=exp19,
            operator_history=args.operator_history,
            require_full_history=not args.fixture_history,
            extra_exclusion=args.extra_exclusion,
            exclusion_folders=_folder_overrides(args.exclusion_folder),
            budget=args.budget, progress=not args.quiet)
        print(json.dumps(doc, indent=2))
        return doc
    if args.command == 'audit':
        doc = audit_everything(
            args.seed,
            buffers=args.buffers or experiment / LAYOUT['buffers'].format(seed=args.seed),
            dev_panels=args.dev_panels or experiment / LAYOUT['dev_panels'],
            memory=args.memory, experiment=experiment, exp19=exp19,
            operator_history=args.operator_history,
            require_full_history=not args.fixture_history,
            exclusion_folders=_folder_overrides(args.exclusion_folder))
        print(json.dumps(doc, indent=2))
        print(f'checks run: {doc["checks_run"]}/{doc["checks_expected"]}'
              + (f'  ABSENT: {doc["checks_absent"]}' if doc['checks_absent'] else ''),
              flush=True)
        if not doc['passed']:
            raise SystemExit(1)
        return doc
    if args.command == 'cells':
        print(json.dumps(dict(cells=len(CELLS), families=FAMILY_SIZES,
                              cell_order=list(CELL_ORDER), table=cell_table(),
                              marks=MARKS, arms=list(ARMS),
                              arm_calls={a: list(ARM_CALLS[a]) for a in ARMS},
                              stream_mapping=STREAM_MAPPING,
                              stream_mapping_sha256=STREAM_MAPPING_SHA256,
                              checkpoint_keys=dict(
                                  awake=list(checkpoint_keys('awake')),
                                  offline=list(checkpoint_keys('offline'))),
                              layout=LAYOUT), indent=2))
        return CELLS
    raise SystemExit(f'unknown command {args.command}')


if __name__ == '__main__':
    main()
