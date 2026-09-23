"""LINK isolation v2 -- qualified terminal, clean absent-candidate arm (Fable, 2026-09-20).

Built to ``design/v3/18-link-isolation-v2-preregistration-draft.md``. Additive only: this
file imports ``fable_link_isolation`` (v1, frozen, withdrawn before any run) READ-ONLY and
never modifies it. Everything v1 already does that the spec asks for -- the stage-A and
stage-B batch builders, the unrestricted marginal, the frozen-copy construction, the
``link_metrics``/``one_hop_by_relation`` measurements, the ``freeze``/``wave``/
``check_manifest`` plumbing -- is reused by import.

WHAT V2 CHANGES (each item is a spec line, not an improvement of taste):

1.  Seeds 1400/1401/1402 with independently NAMED model and data RNG streams. v1 drew every
    seed's worlds from ``random.Random(1101)``, i.e. all three seeds saw the same worlds.
2.  A stage-A qualification GATE in code. On a separate prebuilt full-story validation set:
    >= 487/512 attribute answers for EACH of relations 8/9/10, and >= 487/512 terminal
    answers given the TRUE endpoint of practised two-hop questions (evaluator-only). Stage B
    refuses to start for a seed whose ``qualification.json`` does not say ``qualified`` and
    whose stage-A checkpoint hash does not match. A failed seed is reported as "stage A
    failed; stage-B hypothesis untested for this seed": no replacement seeds, no checkpoint
    search, no silent extension.
3.  Arms. ``shared`` and ``frozen`` are the primary contrast. ``frozen-present-mask`` is the
    CLEAN absent-candidate arm: frozen setup, the marginal sums only over the people present
    in the visible rows, WITHOUT renormalisation, so mass wasted on absent identities and on
    non-entity tokens is still penalised. v1's renormalised ``frozen-terminal-6`` is NOT
    included. ``detached`` is an optional third DIAGNOSTIC arm behind ``--include-detached``:
    terminal probabilities detached but recomputed from the MOVING trainable weights. It is
    not frozen and is labelled that way everywhere it is printed or stored.
4.  Stage-B schedule frozen at 3,000 updates, warm-up over 100 updates to 1e-3, flat through
    2,000, linear to 1e-4 at 3,000. (v1's rescaled v3r shape warmed up over 50.)
5.  Measurements before any stage-B update and every 100 updates: full-vocabulary LINK argmax
    accuracy, entity-only argmax as a diagnostic, p_link mass on true / wrong-present /
    absent / non-entity, terminal true-person margin, answer-value collision rate, and
    attribute accuracy by relation.
6.  The six- and sixteen-person validation probes are frozen BEFORE training and their ACTUAL
    semantic signatures are added to the training exclusion union; every training batch is
    checked against that union, both as constructed (full story) and as presented (the
    reduced story the model actually sees).
7.  Final scoring runs TWO inference systems separately for the frozen arms: (1) LINK from
    the trainable model followed by the frozen terminal used in training; (2) both calls
    through the trainable model, the intended single-model deployment.
8.  Frozen-copy immutability is checked at initialisation, at every logged checkpoint and at
    final scoring: fingerprint, eval mode, no ``requires_grad``, no accumulated gradient, and
    not present in the optimizer's parameter groups.

FIVE VALIDATION SETS, all built before ``freeze`` and hashed into the manifest:

  ``qualification``  six-person, 512 two-hop questions + 512 attribute questions per relation.
                     Development validation for the stage-A gate ONLY.
  ``probe-six``      six-person, the stage-B trajectory probe (primary fit condition).
  ``probe-sixteen``  sixteen-person, transfer, reported separately.
  ``confirm-six``    six-person, the reserved FINAL confirmation set; acceptance is scored
                     here and nowhere else.
  ``confirm-sixteen`` sixteen-person transfer at final scoring, reported separately.

The three families are checked pairwise disjoint at build time, and all five are checked
against the registered ``forbidden-semantics.json`` before anything is written.

ACCEPTANCE (per qualified seed, per arm, per inference system, on ``confirm-six``):
>= 487/512 LINK predictions, retained attribute accuracy >= 487/512 for each relation, and
>= 461/512 complete correct two-call paths AND final answers. The report always prints the
ORIGINAL three-seed denominator and names every stage-A failure; a subset of qualified seeds
is never "3/3".

WHAT REMAINS SUPPLIED, in both stages and every arm: the decomposition (a two-hop question is
a LINK call followed by a terminal call -- the marginal's form encodes it), the token grammar,
and visible fact parsing. Not supplied: the intermediate entity, any supporting-line or
attention target, and ``row.gold`` / ``row.supplied`` / ``row.answer`` / ``row.hops`` /
``row.relation``, which are never read in any code path that builds a record or a loss.

Location note: this file lives in the ``card-experiment-handoff-7c5b27`` worktree because the
harness refuses writes to the base checkout. ``BASE`` and ``BASE``/scripts are prepended to
``sys.path`` so every registered module, the frozen ``premonition`` package, ``ROOT``, the
panels and the artifacts folder are the BASE repository's.
"""
from __future__ import annotations

import sys
from pathlib import Path

BASE = Path('/Users/ben-hannan/Desktop/projects/beautiful-model')
if Path(__file__).resolve().parent != (BASE/'scripts'):
    for entry in (str(BASE), str(BASE/'scripts'), str(Path(__file__).resolve().parent)):
        while entry in sys.path:
            sys.path.remove(entry)
        sys.path.insert(0, entry)

import argparse
import copy
import datetime
import hashlib
import json
import os
import random
import resource
import subprocess
import time
import traceback

import fable_link_isolation as G1                     # v1: READ-ONLY, never modified
import fable_operator_startup as S
import fable_operator_variants as V

A, P, C, R, torch = G1.A, G1.P, G1.C, G1.R, G1.torch
E, T, data, F = G1.E, G1.T, G1.data, G1.F
ROOT = G1.ROOT
assert ROOT == BASE, (ROOT, BASE)
assert Path(G1.__file__).resolve().name == 'fable_link_isolation.py'

QUESTION, ANSWER, WORLD, LINK = A.QUESTION, A.ANSWER, A.WORLD, A.LINK
ENTITY_MIN, ENTITY_MAX = A.ENTITY_MIN, A.ENTITY_MAX
ENTITIES = ENTITY_MAX - ENTITY_MIN
ATTRIBUTE_RELATIONS = S.ATTRIBUTE_RELATIONS            # (8, 9, 10)
TWO_HOP_RELATIONS = S.TWO_HOP_RELATIONS                # (8, 9)
COUNTED_OPERATIONS = S.COUNTED_OPERATIONS

NAME = 'fable-link-isolation-v2-20260920'
STAGES = ('a', 'b')
PRIMARY_ARMS = ('shared', 'frozen', 'frozen-present-mask')
DIAGNOSTIC_ARMS = ('detached',)                        # NOT frozen; behind --include-detached
ALL_ARMS = PRIMARY_ARMS + DIAGNOSTIC_ARMS
FROZEN_ARMS = ('frozen', 'frozen-present-mask')        # arms that use the immutable copy
SEEDS = (1400, 1401, 1402)                             # the registered seeds; never replaced

# ``FABLE_LINK_ISOLATION_V2_OUT`` exists for ONE purpose: the check suite's short smoke runs
# every subcommand -- including a real ``wave`` with real subprocesses -- into a temporary
# directory. A registered run never sets it; ``freeze`` records which mode it was in and
# every other command refuses to mix the two.
DEV_OUT = os.environ.get('FABLE_LINK_ISOLATION_V2_OUT') or None
OUT = Path(DEV_OUT) if DEV_OUT else ROOT/f'artifacts/{NAME}'
LOCAL_ARTIFACTS = Path(__file__).resolve().parent.parent/'artifacts'/NAME

ARCHITECTURE = dict(G1.ARCHITECTURE)
PARAMETERS = G1.PARAMETERS                             # 79,316
LOG_EVERY_A = G1.LOG_EVERY_A                           # 250
MEASURE_EVERY_B = 100                                  # the spec's "every 100 updates"

STAGE_A_UPDATES = 3000
STAGE_B_UPDATES = 3000
STAGE_B_WARMUP = 100
STAGE_B_PEAK = 1e-3
STAGE_B_FLAT_THROUGH = 2000
STAGE_B_FINAL = 1e-4

# Acceptance, frozen here and copied into the manifest.
ACCEPT = dict(denominator=512, link=487, attribute=487, path_and_answer=461)
QUALIFY = dict(denominator=512, attribute=487, terminal_true_endpoint=487)


def registered_thresholds(manifest, key):
    """Thresholds as FROZEN in the manifest, never the module constants.

    A registered freeze copies ``ACCEPT``/``QUALIFY`` verbatim and refuses any validation
    size but 512. Dev-mode smokes (``FABLE_LINK_ISOLATION_V2_OUT``) freeze a zero-threshold
    copy at the smoke's own denominator, so the gate and the acceptance logic are exercised
    end to end without pretending a 10-update run qualified.
    """
    blob = manifest['acceptance' if key == 'acceptance' else 'qualification']
    return dict(blob)

# ------------------------------------------------------------------ independent RNG streams
NAMESPACE_MODEL = 'fable-link-isolation-v2-model'
NAMESPACE_TORCH = 'fable-link-isolation-v2-torch'
NAMESPACE_WORLD = 'fable-link-isolation-v2-world'
NAMESPACE_A = 'fable-link-isolation-v2-a'
NAMESPACE_A_EXTRA = 'fable-link-isolation-v2-a-extra'
NAMESPACE_B = 'fable-link-isolation-v2-b'
NAMESPACE_VALIDATION = 'fable-link-isolation-v2-validation'
# NEITHER stage-B namespace contains the arm: every arm must draw identical batches.
assert all(arm not in NAMESPACE_B for arm in ALL_ARMS)

VALIDATION_SETS = ('qualification', 'probe-six', 'probe-sixteen',
                   'confirm-six', 'confirm-sixteen')
VALIDATION_FAMILY = dict(qualification='qualification', **{k: 'probe' for k in
                                                           ('probe-six', 'probe-sixteen')},
                         **{k: 'confirmation' for k in ('confirm-six', 'confirm-sixteen')})

DEFAULTS = dict(G1.DEFAULTS)                           # balance, blind_lines, grow_g1/g2,
DEFAULTS.update(                                       # stage_a_extra, dedupe, single_forward
    probe_six=512, probe_sixteen=512, probe_per_visit=4,
    probe_attribute=512,
    qualification_two_hop=512, qualification_attribute=512,
    confirm_six=512, confirm_sixteen=512, confirm_attribute=512,
    presented_exclusion_check=True,
    include_detached=False)

# Process-local wiring; never serialized, never part of the registered manifest.
STATE = dict(stage=None, arm=None, seed=None, params=dict(DEFAULTS), frozen=None,
             running=dict.fromkeys(map(str, COUNTED_OPERATIONS), 0))


def prereg_path():
    local = LOCAL_ARTIFACTS/'PREREGISTRATION.md'
    return local if local.exists() else OUT/'PREREGISTRATION.md'


def normalize_params(params):
    unknown = set(params) - set(DEFAULTS)
    assert not unknown, unknown
    merged = dict(DEFAULTS, **params)
    assert 0 <= merged['grow_g1'] <= merged['grow_g2'], (merged['grow_g1'], merged['grow_g2'])
    assert merged['blind_lines'] >= 1, merged['blind_lines']
    assert merged['stage_a_extra'] >= 0, merged['stage_a_extra']
    assert 1 <= merged['probe_per_visit'] <= 12, merged['probe_per_visit']
    for key in ('probe_six', 'probe_sixteen', 'probe_attribute', 'qualification_two_hop',
                'qualification_attribute', 'confirm_six', 'confirm_sixteen',
                'confirm_attribute'):
        assert merged[key] >= 1, (key, merged[key])
    return merged


def named_seed(namespace, seed):
    """A deterministic 31-bit seed from an explicitly NAMED stream.

    Model init, the torch stream and every data stream get their own name, so changing one
    stream's definition cannot shift another's draws.
    """
    digest = hashlib.sha256(f'{namespace}:{seed}'.encode()).hexdigest()
    return int(digest[:8], 16) % (1 << 31)


def new_model(seed):
    """``A.new_model`` on the NAMED model stream, so the model init is independent of data."""
    model = A.new_model(named_seed(NAMESPACE_MODEL, seed))
    assert model.parameters_count() == PARAMETERS, model.parameters_count()
    return model


# ------------------------------------------------------------------------ lr schedules

def lr_stage_a(step, updates):
    """Stage A retains the proposed schedule: v3r's shape rescaled to the stage length.

    The spec fixes stage B's schedule explicitly and says the proposed stage-A schedule "may
    be retained"; retaining it verbatim is the conservative choice and keeps stage A
    comparable to ``grow-blind``.
    """
    return G1.lr_at_scaled(step, updates)


def lr_stage_b(step, updates=STAGE_B_UPDATES):
    """The spec's stage-B schedule: warm-up 100 to 1e-3, flat through 2,000, 1e-4 at 3,000.

    Written in terms of ``updates`` only so the short smoke runs have a schedule at all; the
    registered budget is 3,000, at which ``flat_through`` is exactly 2,000 and the warm-up is
    exactly 100 updates. ``freeze`` refuses any other budget outside dev mode, and the worker
    re-checks the four anchor values against the manifest before its first update.
    """
    assert updates > 0, updates
    flat = (2*updates)//3
    warm = min(STAGE_B_WARMUP, max(1, flat))
    if step < flat:
        return STAGE_B_PEAK * min(1., (step+1)/warm)
    return STAGE_B_PEAK + (STAGE_B_FINAL - STAGE_B_PEAK) * (step - flat) / (updates - flat)


def stage_b_schedule_anchors(updates=STAGE_B_UPDATES):
    flat = (2*updates)//3
    warm = min(STAGE_B_WARMUP, max(1, flat))
    return dict(updates=updates, warmup=warm, peak=STAGE_B_PEAK, flat_through=flat,
                final=STAGE_B_FINAL,
                lr_first=lr_stage_b(0, updates), lr_at_warmup_end=lr_stage_b(warm-1, updates),
                lr_at_flat_end=lr_stage_b(flat, updates),
                lr_last=lr_stage_b(updates-1, updates))


# ------------------------------------------------------------------------------- wiring

def configure(stage, seed=None, arm=None, frozen=None, **params):
    """Set the process-local wiring for v2 AND for v1's batch builders.

    v1's builders read ``fable_link_isolation.STATE``; that dict is explicitly process-local
    wiring, never serialized and never part of any manifest, so populating it is the intended
    read-only reuse of the builders. The ARM is deliberately NOT written into v1's state: the
    batch builder must not be able to see which arm it is serving.
    """
    assert stage in STAGES, stage
    assert arm is None or arm in ALL_ARMS, arm
    merged = normalize_params({k: v for k, v in params.items() if k in DEFAULTS})
    merged['stage_a_updates'] = params.get('stage_a_updates', STAGE_A_UPDATES)
    merged['stage_b_updates'] = params.get('stage_b_updates', STAGE_B_UPDATES)
    namespace = NAMESPACE_A if stage == 'a' else NAMESPACE_B
    v1_params = {k: merged[k] for k in G1.DEFAULTS}
    v1_params['stage_a_updates'] = merged['stage_a_updates']
    v1_params['stage_b_updates'] = merged['stage_b_updates']
    G1.STATE.update(stage=stage, arm=None, seed=seed, step=0, params=v1_params, frozen=None,
                    vrng=None if seed is None else random.Random(f'{namespace}:{seed}'),
                    xrng=None if seed is None else random.Random(f'{NAMESPACE_A_EXTRA}:{seed}'),
                    running=dict.fromkeys(map(str, COUNTED_OPERATIONS), 0))
    STATE.update(stage=stage, arm=arm, seed=seed, params=merged, frozen=frozen,
                 running=dict.fromkeys(map(str, COUNTED_OPERATIONS), 0))
    R.OUT = OUT
    return OUT


def set_step(step):
    G1.STATE['step'] = step
    STATE['step'] = step


def world_rng(seed):
    """The NAMED world stream. v1 used ``random.Random(1101)`` for every seed."""
    return random.Random(f'{NAMESPACE_WORLD}:{seed}')


def stage_folder(stage, arm=None, seed=None):
    folder = OUT/('stage-a' if stage == 'a' else f'stage-b/{arm}')
    return folder if seed is None else folder/f'seed-{seed}'


def check_manifest():
    """``R.check_manifest`` plus the invariants this experiment adds."""
    manifest = R.check_manifest()
    assert manifest.get('experiment') == NAME, 'manifest/experiment mismatch'
    assert manifest.get('dev_out') == DEV_OUT, \
        'registered and dev output roots must not be mixed'
    return manifest


def registered_params():
    manifest = json.loads((OUT/'astra_canonical_operator_launch.json').read_text())
    assert manifest['experiment'] == NAME, 'manifest/experiment mismatch'
    return normalize_params(manifest.get('params', {}))


# ------------------------------------------------------------------ validation set builder

def build_validation(label, entities, two_hop, per_visit, attribute_per_relation,
                     chunk_visits=8):
    """A fixed, fresh validation set of FULL stories. Never enters a loss.

    Returns v1's ``ProbeChunk`` structure unchanged, so every v1 measurement function
    (``link_metrics``, ``one_hop_by_relation``, ``probe_diagnostics``) consumes it verbatim.
    The builder itself is v2's because v1's probe puts only ONE attribute question per
    relation per visit (128 per relation at 512 two-hop questions), and the spec's stage-A
    gate and the retained-attribute acceptance both need a 512 denominator PER RELATION.

    Questions are drawn by this module's own validation RNG from the VISIBLE facts of fresh
    stories, never from the generator's own question rows, and no annotation is read: the
    true middle person and the answer-value collision flag are computed here only so the
    EVALUATOR can use them, and they live in the chunk's evaluator-only fields.
    """
    data.bootstrap()
    from premonition.toy_ladder import LadderSpec, visit
    spec = LadderSpec(entities=entities)
    prng = random.Random(f'{NAMESPACE_VALIDATION}:{label}:{entities}:{two_hop}:'
                         f'{per_visit}:{attribute_per_relation}')
    visits_needed = -(-two_hop // per_visit)
    per_visit_attribute = -(-attribute_per_relation // visits_needed)
    chunks, made = [], 0
    attribute_made = dict.fromkeys(ATTRIBUTE_RELATIONS, 0)
    for start in range(0, visits_needed, chunk_visits):
        block = min(chunk_visits, visits_needed - start)
        memories = []
        link = dict(q=[], owner=[], where=[])
        term = dict(q=[], owner=[], where=[])
        mono = dict(q=[], owner=[], where=[])
        one = dict(q=[], owner=[], where=[])
        rows_index, answers, present, intermediate, shares, one_answers = [], [], [], [], [], []
        for v in range(block):
            rows, world, _ = visit(spec, prng, training=True)
            assert len(world.ents) == entities, (len(world.ents), entities)
            full = [[] if row.question else list(row.tokens) for row in rows]
            where = len(full)                       # every visible fact line is eligible
            attr, links = S._visible_facts(full, range(len(full)))
            people = G1._people_present(full)
            assert len(people) == entities, (len(people), entities)
            mask = G1._present_mask(people)
            memories.append(full)
            terminal_key = {}

            options = sorted((a, r) for a in links for r in TWO_HOP_RELATIONS
                             if (links[a][0], r) in attr)
            take = min(per_visit, len(options), max(0, two_hop - made))
            for asker, relation in prng.sample(options, take):
                target, _ = links[asker]
                answer, _ = attr[(target, relation)]
                link['q'].append([QUESTION, asker, LINK, ANSWER])
                link['owner'].append(v); link['where'].append(where)
                mono['q'].append([QUESTION, asker, LINK, relation, ANSWER])
                mono['owner'].append(v); mono['where'].append(where)
                row_ids = []
                for entity in range(ENTITY_MIN, ENTITY_MAX):
                    key = (relation, entity)
                    hit = terminal_key.get(key)
                    if hit is not None:
                        row_ids.append(hit)
                        continue
                    term['q'].append([QUESTION, entity, relation, ANSWER])
                    term['owner'].append(v); term['where'].append(where)
                    terminal_key[key] = len(term['q']) - 1
                    row_ids.append(len(term['q']) - 1)
                rows_index.append(row_ids)
                answers.append(answer)
                present.append(list(mask))
                # ---- EVALUATOR-ONLY: the true middle person and the collision flag.
                intermediate.append(target)
                shares.append(int(any(other != target and (other, relation) in attr
                                      and attr[(other, relation)][0] == answer
                                      for other in people)))
                made += 1
            for relation in ATTRIBUTE_RELATIONS:
                want = min(per_visit_attribute,
                           max(0, attribute_per_relation - attribute_made[relation]))
                if not want:
                    continue
                eligible = [who for who in people if (who, relation) in attr]
                assert eligible, (label, relation)
                chosen = (prng.sample(eligible, want) if want <= len(eligible)
                          else [eligible[prng.randrange(len(eligible))] for _ in range(want)])
                for who in chosen:
                    one['q'].append([QUESTION, who, relation, ANSWER])
                    one['owner'].append(v); one['where'].append(where)
                    one_answers.append(attr[(who, relation)][0])
                    attribute_made[relation] += 1
        if not answers and not one_answers:
            continue

        def pack(d):
            return data.pack(memories, d['q'], d['owner'], d['where'])

        chunks.append(G1.ProbeChunk(
            pack(link), pack(term), torch.tensor(rows_index, dtype=torch.long),
            torch.tensor(answers), torch.tensor(present, dtype=torch.bool),
            pack(mono), pack(one), torch.tensor(one_answers),
            torch.tensor(intermediate, dtype=torch.long),
            torch.tensor(shares, dtype=torch.long)))
    total = sum(int(c.answers.shape[0]) for c in chunks)
    assert total == two_hop, (label, total, two_hop)
    for relation in ATTRIBUTE_RELATIONS:
        assert attribute_made[relation] == attribute_per_relation, \
            (label, relation, attribute_made[relation], attribute_per_relation)
    return dict(label=label, entities=entities, n=total, per_visit=per_visit,
                attribute_per_relation=attribute_per_relation, chunks=chunks)


def set_signatures(vset):
    """Every question's ACTUAL visible semantic signature, over the story it is asked about."""
    out = set()
    for chunk in vset['chunks']:
        memory = chunk.link.memory.tolist()
        for x in (chunk.link, chunk.terminal, chunk.monolithic, chunk.one_hop):
            for owner, q in zip(x.owner.tolist(), x.questions.tolist()):
                out.add(A.visible_signature(memory[owner], q))
    return out


def set_fingerprint(vset):
    """A content hash of every tensor the set carries, so a worker can prove it rebuilt it."""
    h = hashlib.sha256()
    h.update(f"{vset['label']}|{vset['entities']}|{vset['n']}|"
             f"{vset['attribute_per_relation']}".encode())
    for chunk in vset['chunks']:
        for x in (chunk.link, chunk.terminal, chunk.monolithic, chunk.one_hop):
            for tensor in (x.memory, x.questions, x.owner, x.eligible):
                h.update(tensor.detach().cpu().contiguous().numpy().tobytes())
        for tensor in (chunk.terminal_index, chunk.answers, chunk.present,
                       chunk.one_hop_answers, chunk.intermediate, chunk.shares_answer):
            h.update(tensor.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()


def validation_plan(params):
    """(label, entities, two_hop, per_visit, attribute_per_relation) for all five sets."""
    per_visit = params['probe_per_visit']
    return [
        ('qualification', 6, params['qualification_two_hop'], per_visit,
         params['qualification_attribute']),
        ('probe-six', 6, params['probe_six'], per_visit, params['probe_attribute']),
        ('probe-sixteen', ENTITIES, params['probe_sixteen'], per_visit,
         params['probe_attribute']),
        ('confirm-six', 6, params['confirm_six'], per_visit, params['confirm_attribute']),
        ('confirm-sixteen', ENTITIES, params['confirm_sixteen'], per_visit,
         params['confirm_attribute']),
    ]


def build_all_validation(params):
    return {label: build_validation(label, entities, two_hop, per_visit, attribute)
            for label, entities, two_hop, per_visit, attribute in validation_plan(params)}


def validation_dir():
    return OUT/'validation'


def build_validation_command(params):
    """Build, audit and WRITE the five validation sets' signatures + the exclusion union.

    Written before ``freeze`` so that ``freeze`` can hash both files and every worker can be
    refused if either changes. Nothing model-dependent happens here: the sets are not
    filtered by any model's correctness.
    """
    registered = registered_exclusion()
    sets = build_all_validation(params)
    signatures = {label: set_signatures(sets[label]) for label in sets}
    report = {}
    for label, vset in sets.items():
        clash = signatures[label] & registered
        if clash:
            raise RuntimeError(f'validation set {label} overlaps the registered exclusion '
                               f'set ({len(clash)} signatures); build invalid')
        report[label] = dict(entities=vset['entities'], two_hop=vset['n'],
                             attribute_per_relation=vset['attribute_per_relation'],
                             chunks=len(vset['chunks']),
                             signatures=len(signatures[label]),
                             fingerprint=set_fingerprint(vset))
    families = {}
    for label, signature_set in signatures.items():
        families.setdefault(VALIDATION_FAMILY[label], set()).update(signature_set)
    names = sorted(families)
    for i, left in enumerate(names):
        for right in names[i+1:]:
            clash = families[left] & families[right]
            if clash:
                raise RuntimeError(f'validation families {left} and {right} share '
                                   f'{len(clash)} signatures; the confirmation set must be '
                                   f'reserved and disjoint from development validation')
    union = sorted(registered | set().union(*signatures.values()))
    validation_dir().mkdir(parents=True, exist_ok=True)
    C.write_new(validation_dir()/'exclusion_union.json', union)
    C.write_new(validation_dir()/'validation.json',
                dict(experiment=NAME, created_utc=_now(), namespace=NAMESPACE_VALIDATION,
                     params={k: params[k] for k in sorted(DEFAULTS) if k in params},
                     registered_exclusion_path=str(registered_exclusion_path()),
                     registered_exclusion_entries=len(registered),
                     union_entries=len(union), sets=report,
                     families={k: len(v) for k, v in families.items()},
                     families_pairwise_disjoint=True,
                     selected_on_model_outcomes=False))
    print(json.dumps(dict(union_entries=len(union),
                          sets={k: v['fingerprint'][:12] for k, v in report.items()})),
          flush=True)


def load_validation(manifest, labels=VALIDATION_SETS):
    """Rebuild the requested sets and prove they match the registered fingerprints."""
    registered = json.loads((validation_dir()/'validation.json').read_text())
    assert registered['experiment'] == NAME
    params = normalize_params(manifest.get('params', {}))
    wanted = {label for label in labels}
    sets = {}
    for label, entities, two_hop, per_visit, attribute in validation_plan(params):
        if label not in wanted:
            continue
        vset = build_validation(label, entities, two_hop, per_visit, attribute)
        got, want = set_fingerprint(vset), registered['sets'][label]['fingerprint']
        if got != want:
            raise RuntimeError(f'validation set {label} did not rebuild to its registered '
                               f'fingerprint ({got[:12]} vs {want[:12]}); run invalid')
        sets[label] = vset
    return sets


def registered_exclusion_path():
    v1 = json.loads((G1.V1/'astra_canonical_operator_launch.json').read_text())
    return Path(v1['exclusion_path'])


def registered_exclusion():
    return set(json.loads(registered_exclusion_path().read_text()))


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


# ------------------------------------------------------------------------ batches + losses

def training_batch_stage_a(rng, visits=16, forbidden=frozenset()):
    """v1's stage-A batch builder, unchanged, serving v2's RNG streams."""
    return G1.training_batch_stage_a(rng, visits, forbidden)


def training_batch_stage_b(rng, visits=16, forbidden=frozenset()):
    """v1's stage-B batch builder, unchanged. It cannot see the arm: v2 never writes the arm
    into ``G1.STATE`` and the stage-B curriculum namespace does not contain it."""
    return G1.training_batch_stage_b(rng, visits, forbidden)


def marginal_from(batch, link_logits, terminal_probabilities, *, present_mask=False):
    """P(y) = sum_e p_link[e] * p_term(y | S, e, r) over the sixteen entity tokens.

    ``present_mask=False`` delegates to v1 verbatim: ``p_link`` is the LINK softmax restricted
    to 52..67 and NOT renormalised, so mass on non-entity tokens is lost and penalised.

    ``present_mask=True`` is the CLEAN absent-candidate arm: the sum keeps only the people
    visibly PRESENT in the story and ``p_link`` is NOT renormalised over them, so mass wasted
    on absent identities AND on non-entity tokens is still penalised. This is the whole point
    of the arm, and the reason v1's renormalised ``frozen-terminal-6`` is not included: away
    from clamps, conditional normalisation removes that penalty entirely while native decoding
    still uses full-vocabulary argmax.
    """
    if not present_mask:
        return G1.marginal_from(batch, link_logits, terminal_probabilities, restrict=False)
    n = link_logits.shape[0]
    assert batch.terminal_index.shape == (n, ENTITIES)
    p1 = link_logits.softmax(-1)[:, ENTITY_MIN:ENTITY_MAX]                  # [n, 16]
    pt = terminal_probabilities[batch.terminal_index]                       # [n, 16, V]
    index = batch.two_hop_answers[:, None, None].expand(n, ENTITIES, 1)
    conditional = pt.gather(2, index).squeeze(2)                            # [n, 16]
    mask = batch.present.to(p1.dtype)
    assert mask.shape == (n, ENTITIES)
    return (p1 * mask * conditional).sum(1)                                 # NO renormalisation


def stage_b_pieces(model, batch, arm, frozen):
    """(one_logits, link_logits, terminal_probabilities). Only ``shared`` backprops terminals."""
    assert arm in ALL_ARMS, arm
    if arm != 'detached':
        # ``shared`` and both frozen arms are exactly v1's two code paths; the present mask
        # lives in the marginal, not in the forward.
        return G1.stage_b_pieces(model, batch, 'shared' if arm == 'shared' else
                                 'frozen-terminal', frozen)
    # ``detached``: terminal probabilities RECOMPUTED FROM THE MOVING TRAINABLE WEIGHTS with
    # no gradient. This is NOT the frozen arm and must never be relabelled as one.
    plan = batch.plan
    if plan['single_forward']:
        logits = model(batch.combined_head)
        piece = {name: logits[start:stop]
                 for name, (start, stop) in plan['slices_head'].items()}
        one_logits, link_logits = piece['one_hop'], piece['link']
    else:
        one_logits, link_logits = model(batch.one_hop), model(batch.link)
    was = model.training
    model.eval()
    try:
        with torch.no_grad():
            detached_terminal = model(batch.terminal).softmax(-1)
    finally:
        model.train(was)
    return one_logits, link_logits, detached_terminal


def stage_b_losses(model, batch, arm, frozen=None):
    one_logits, link_logits, terminal_probabilities = stage_b_pieces(model, batch, arm, frozen)
    one = F.cross_entropy(one_logits, batch.one_hop_answers)
    marg = -marginal_from(batch, link_logits, terminal_probabilities,
                          present_mask=(arm == 'frozen-present-mask')
                          ).clamp_min(1e-12).log().mean()
    return one, marg


def link_weights(batch):
    """v1's rule verbatim: 1/3 attribute CE + 1/3 marginal at 16 visits, monolithic REMOVED
    rather than renormalised away, exactly as the spec states."""
    return G1.link_weights(batch)


def _step_stage_a(model, optimizer, batch, step):
    """v1's stage-A step verbatim (its lr comes from ``G1.lr_at_scaled``)."""
    G1._step_stage_a(model, optimizer, batch, step)


def _step_stage_b(model, optimizer, batch, step, updates=STAGE_B_UPDATES):
    for group in optimizer.param_groups:
        group['lr'] = lr_stage_b(step, updates)
    optimizer.zero_grad(set_to_none=True)
    one, marg = stage_b_losses(model, batch, STATE['arm'], STATE['frozen'])
    w1, w2 = link_weights(batch)
    loss = w1*one + w2*marg
    if not bool(torch.isfinite(loss)):
        raise RuntimeError("nonfinite training loss")
    loss.backward()
    S._finish(model, optimizer)


def training_flops_stage_a(batch, model):
    return G1.training_flops_stage_a(batch, model)


def training_flops_stage_b(batch, model, arm, frozen=None):
    """Honest per-forward count of exactly the forwards ``stage_b_losses`` performs."""
    if arm == 'shared':
        return G1.training_flops_stage_b(batch, model, 'shared')
    if arm == 'detached':
        head = (T.training_flops(batch.combined_head, model) if batch.plan['single_forward']
                else T.training_flops(batch.one_hop, model)
                + T.training_flops(batch.link, model))
        return head + A.inference_flops(batch.terminal, model)
    return G1.training_flops_stage_b(batch, model, 'frozen-terminal', frozen)


# ------------------------------------------------------------------- the immutable copy

def make_frozen(model):
    """A deep copy the optimizer never sees and nothing ever updates."""
    frozen = copy.deepcopy(model)
    frozen.eval()
    for parameter in frozen.parameters():
        parameter.requires_grad_(False)
    return frozen


def assert_frozen_intact(frozen, fingerprint, optimizer, where):
    """Fingerprint, eval mode, no grads, not in the optimizer. Called at init, at every
    logged checkpoint and at final scoring."""
    assert frozen is not None, f'{where}: the frozen copy is missing'
    assert not frozen.training, f'{where}: the frozen copy left eval mode'
    assert all(not q.requires_grad for q in frozen.parameters()), \
        f'{where}: a frozen parameter requires grad'
    assert all(q.grad is None for q in frozen.parameters()), \
        f'{where}: a frozen parameter accumulated a gradient'
    if optimizer is not None:
        owned = {id(q) for group in optimizer.param_groups for q in group['params']}
        assert not any(id(q) in owned for q in frozen.parameters()), \
            f'{where}: a frozen parameter is in the optimizer'
    got = C.fingerprint(frozen)
    assert got == fingerprint, f'{where}: the frozen copy moved ({got[:12]} vs {fingerprint[:12]})'
    return True


# -------------------------------------------------------------- exclusion-union enforcement

def presented_signatures(*inputs):
    """The signature of the story the model ACTUALLY SEES for each question.

    v1's builders check every constructed question against the exclusion set using the FULL
    story of the visit. Under the curriculum the model is shown a REDUCED story, so the audit
    asked for the presented input to be indexed too; this is that check, computed from the
    packed batch after construction.
    """
    out = set()
    for x in inputs:
        memory = x.memory.tolist()
        for owner, q in zip(x.owner.tolist(), x.questions.tolist()):
            out.add(A.visible_signature(memory[owner], q))
    return out


def assert_no_validation_overlap(union, *inputs):
    hit = presented_signatures(*inputs) & union
    if hit:
        raise RuntimeError('training/validation semantic overlap in the PRESENTED story '
                           f'({len(hit)} signatures); run invalid')
    return True


# ----------------------------------------------------------------------------- measurement

MEASURED_KEYS = ('link_accuracy', 'link_accuracy_entity_argmax', 'p_link_true',
                 'p_link_wrong_present', 'p_link_absent', 'p_link_non_entity',
                 'terminal_p_true_person', 'terminal_p_wrong_present', 'terminal_margin',
                 'terminal_true_is_argmax_present', 'shared_answer_rate',
                 'marginal_probability', 'one_hop_accuracy',
                 'one_hop_accuracy_r8', 'one_hop_accuracy_r9', 'one_hop_accuracy_r10')


def _empty_execution():
    return dict(n=0, answer_correct=0, path_and_answer_correct=0, via_right_person=0,
                via_wrong_person=0, link_correct=0, wrong_answer=0, aborted=0)


def _accumulate(acc, emitted, answers, truths):
    for em, y, t in zip(emitted, answers, truths):
        acc['n'] += 1
        if len(em) < 2:
            acc['aborted'] += 1
            continue
        correct_link = em[0] == t
        acc['link_correct'] += int(correct_link)
        if em[1] == y:
            acc['answer_correct'] += 1
            acc['via_right_person' if correct_link else 'via_wrong_person'] += 1
            acc['path_and_answer_correct'] += int(correct_link)
        else:
            acc['wrong_answer'] += 1
    return acc


def _rates(acc):
    n = max(1, acc['n'])
    return dict(acc, answer_accuracy=G1._round(acc['answer_correct']/n),
                path_and_answer_accuracy=G1._round(acc['path_and_answer_correct']/n),
                via_right_person_rate=G1._round(acc['via_right_person']/n),
                via_wrong_person_rate=G1._round(acc['via_wrong_person']/n),
                link_accuracy=G1._round(acc['link_correct']/n))


@torch.no_grad()
def measure_set(model, vset, frozen=None, execution=False):
    """Every measurement the spec lists, on one fixed validation set.

    The masses, margins and per-relation accuracies come from v1's ``link_metrics`` and
    ``one_hop_by_relation`` unchanged; ``execution`` adds the real two-call rollout through
    the trainable model (v1's ``probe_diagnostics`` always paid for that, which is too
    expensive to run every 100 updates).
    """
    was = model.training
    model.eval()
    try:
        rows, sizes, one_rows, one_sizes, frozen_margin = [], [], [], [], []
        acc = _empty_execution()
        for chunk in vset['chunks']:
            if int(chunk.answers.shape[0]):
                link_logits = model(chunk.link)
                terminal = model(chunk.terminal).softmax(-1)
                row = G1.link_metrics(link_logits, terminal, chunk.terminal_index,
                                      chunk.answers, chunk.present, chunk.intermediate,
                                      chunk.shares_answer)
                rows.append(row); sizes.append(row['n'])
                if frozen is not None:
                    frozen_margin.append(G1.link_metrics(
                        link_logits, frozen(chunk.terminal).softmax(-1), chunk.terminal_index,
                        chunk.answers, chunk.present, chunk.intermediate,
                        chunk.shares_answer)['terminal_margin'])
                if execution:
                    result = A.execute(model, chunk.monolithic)
                    _accumulate(acc, result['emitted'], chunk.answers.tolist(),
                                chunk.intermediate.tolist())
            one = G1.one_hop_by_relation(model, chunk.one_hop, chunk.one_hop_answers)
            one_rows.append(one); one_sizes.append(int(chunk.one_hop_answers.shape[0]))
    finally:
        model.train(was)
    out = dict(label=vset['label'], entities=vset['entities'], n=vset['n'])
    for key in (rows[0] if rows else {}):
        if key == 'n':
            continue
        out[key] = G1._round(G1._weighted([r[key] for r in rows], sizes))
    for key in one_rows[0]:
        out[key] = G1._round(G1._weighted([r[key] for r in one_rows], one_sizes))
    if frozen is not None and frozen_margin:
        out['frozen_terminal_margin'] = G1._round(G1._weighted(frozen_margin, sizes))
    if execution:
        out['execution'] = _rates(acc)
    return out


@torch.no_grad()
def attribute_counts(model, vset):
    """Integer counts per relation. Gates are decided on counts, never on rounded rates."""
    was = model.training
    model.eval()
    correct = dict.fromkeys(ATTRIBUTE_RELATIONS, 0)
    total = dict.fromkeys(ATTRIBUTE_RELATIONS, 0)
    try:
        for chunk in vset['chunks']:
            hit = model(chunk.one_hop).argmax(-1) == chunk.one_hop_answers
            for relation in ATTRIBUTE_RELATIONS:
                rows = chunk.one_hop.questions[:, 2] == relation
                correct[relation] += int(hit[rows].sum())
                total[relation] += int(rows.sum())
    finally:
        model.train(was)
    return correct, total


@torch.no_grad()
def qualification_counts(model, vset):
    """The stage-A gate's two count criteria plus the required discriminability report.

    The terminal criterion is EVALUATOR-ONLY: it supplies the true endpoint of a practised
    two-hop question to the terminal call. It is never a training label and never an input
    to LINK.
    """
    was = model.training
    model.eval()
    correct, total = attribute_counts(model, vset)
    terminal_correct = terminal_total = 0
    strata = {0: dict(n=0, p_true=0., p_wrong=0.), 1: dict(n=0, p_true=0., p_wrong=0.)}
    try:
        for chunk in vset['chunks']:
            n = int(chunk.answers.shape[0])
            if not n:
                continue
            logits = model(chunk.terminal)
            probabilities = logits.softmax(-1)
            prediction = logits.argmax(-1)
            column = chunk.intermediate - ENTITY_MIN
            true_rows = chunk.terminal_index.gather(1, column[:, None]).squeeze(1)
            terminal_correct += int((prediction[true_rows] == chunk.answers).sum())
            terminal_total += n
            conditional = probabilities[chunk.terminal_index].gather(
                2, chunk.answers[:, None, None].expand(n, ENTITIES, 1)).squeeze(2)
            one_hot = F.one_hot(column, ENTITIES).bool()
            wrong_present = chunk.present.bool() & ~one_hot
            p_true = conditional.gather(1, column[:, None]).squeeze(1)
            p_wrong = (conditional*wrong_present).sum(1)/wrong_present.sum(1).clamp_min(1)
            for flag in (0, 1):
                rows = chunk.shares_answer == flag
                k = int(rows.sum())
                if not k:
                    continue
                strata[flag]['n'] += k
                strata[flag]['p_true'] += float(p_true[rows].sum())
                strata[flag]['p_wrong'] += float(p_wrong[rows].sum())
    finally:
        model.train(was)
    discriminability = {}
    for flag, blob in strata.items():
        k = max(1, blob['n'])
        name = 'collision' if flag else 'no_collision'
        discriminability[name] = dict(
            n=blob['n'], p_term_true_person=G1._round(blob['p_true']/k),
            p_term_wrong_present=G1._round(blob['p_wrong']/k),
            margin=G1._round((blob['p_true']-blob['p_wrong'])/k))
    return dict(attribute_correct={str(r): correct[r] for r in ATTRIBUTE_RELATIONS},
                attribute_total={str(r): total[r] for r in ATTRIBUTE_RELATIONS},
                terminal_true_endpoint_correct=terminal_correct,
                terminal_true_endpoint_total=terminal_total,
                answer_value_collision_rate=G1._round(
                    strata[1]['n']/max(1, strata[0]['n']+strata[1]['n'])),
                terminal_discriminability=discriminability)


def qualification_verdict(counts, thresholds=QUALIFY):
    d = thresholds['denominator']
    reasons = []
    for relation in ATTRIBUTE_RELATIONS:
        got = counts['attribute_correct'][str(relation)]
        if counts['attribute_total'][str(relation)] != d:
            reasons.append(f'relation {relation}: denominator '
                           f'{counts["attribute_total"][str(relation)]} != {d}')
        if got < thresholds['attribute']:
            reasons.append(f'relation {relation}: {got}/{d} < {thresholds["attribute"]}/{d}')
    got = counts['terminal_true_endpoint_correct']
    if counts['terminal_true_endpoint_total'] != d:
        reasons.append(f'terminal: denominator {counts["terminal_true_endpoint_total"]} != {d}')
    if got < thresholds['terminal_true_endpoint']:
        reasons.append(f'terminal given the true endpoint: {got}/{d} < '
                       f'{thresholds["terminal_true_endpoint"]}/{d}')
    return (not reasons), reasons


# -------------------------------------------------------------- final two-system scoring

@torch.no_grad()
def score_systems(model, vset, frozen=None):
    """Score the TWO inference systems separately, on integer counts.

    ``trainable_two_call``  both calls through the trainable model -- the intended
                            single-model deployment, run with the registered executor
                            ``astra_canonical_operator.execute``.
    ``link_plus_frozen``    LINK from the trainable model followed by THE FROZEN TERMINAL USED
                            IN TRAINING. Reported only for the frozen arms, and reported as a
                            TWO-COPY system: it spends an extra 79,316 frozen parameters.

    LINK argmax is over the FULL vocabulary in both systems; an early non-entity LINK output
    aborts the path and is counted, never replaced.
    """
    was = model.training
    model.eval()
    link_correct = n = 0
    trainable = _empty_execution()
    with_frozen = _empty_execution() if frozen is not None else None
    try:
        for chunk in vset['chunks']:
            k = int(chunk.answers.shape[0])
            if not k:
                continue
            link_prediction = model(chunk.link).argmax(-1)          # full vocabulary
            link_correct += int((link_prediction == chunk.intermediate).sum())
            n += k
            result = A.execute(model, chunk.monolithic)
            _accumulate(trainable, result['emitted'], chunk.answers.tolist(),
                        chunk.intermediate.tolist())
            if frozen is not None:
                frozen_terminal = frozen(chunk.terminal)
                emitted = []
                for i, entity in enumerate(link_prediction.tolist()):
                    if not ENTITY_MIN <= entity < ENTITY_MAX:
                        emitted.append([entity])            # aborted, exactly as A.execute
                        continue
                    row = int(chunk.terminal_index[i, entity - ENTITY_MIN])
                    emitted.append([entity, int(frozen_terminal[row].argmax(-1))])
                _accumulate(with_frozen, emitted, chunk.answers.tolist(),
                            chunk.intermediate.tolist())
        correct, total = attribute_counts(model, vset)
    finally:
        model.train(was)
    out = dict(label=vset['label'], entities=vset['entities'],
               link_correct=link_correct, link_total=n,
               attribute_correct={str(r): correct[r] for r in ATTRIBUTE_RELATIONS},
               attribute_total={str(r): total[r] for r in ATTRIBUTE_RELATIONS},
               systems=dict(trainable_two_call=_rates(trainable)))
    if with_frozen is not None:
        out['systems']['link_plus_frozen'] = dict(
            _rates(with_frozen), extra_frozen_parameters=PARAMETERS,
            note='two-copy system; an optimization diagnostic, not a parameter-matched '
                 'architectural win')
    return out


def acceptance_verdict(score, thresholds=ACCEPT):
    """Per inference system. Returns {system: (bool, [reasons])} plus the shared criteria."""
    d = thresholds['denominator']
    shared = []
    if score['link_total'] != d:
        shared.append(f'LINK denominator {score["link_total"]} != {d}')
    if score['link_correct'] < thresholds['link']:
        shared.append(f'LINK {score["link_correct"]}/{d} < {thresholds["link"]}/{d}')
    for relation in ATTRIBUTE_RELATIONS:
        got = score['attribute_correct'][str(relation)]
        if score['attribute_total'][str(relation)] != d:
            shared.append(f'relation {relation} denominator '
                          f'{score["attribute_total"][str(relation)]} != {d}')
        if got < thresholds['attribute']:
            shared.append(f'retained attribute r{relation} {got}/{d} < '
                          f'{thresholds["attribute"]}/{d}')
    verdicts = {}
    for system, blob in score['systems'].items():
        reasons = list(shared)
        if blob['n'] != d:
            reasons.append(f'{system}: denominator {blob["n"]} != {d}')
        if blob['path_and_answer_correct'] < thresholds['path_and_answer']:
            reasons.append(f'{system}: complete correct two-call paths AND final answers '
                           f'{blob["path_and_answer_correct"]}/{d} < '
                           f'{thresholds["path_and_answer"]}/{d}')
        verdicts[system] = dict(accepted=not reasons, reasons=reasons)
    return verdicts


# ------------------------------------------------------------------------------- workers

def _exclusion_union(manifest):
    return set(json.loads(Path(manifest['exclusion_path']).read_text()))


def worker_stage_a(seed, wave_start, updates=None, training_seconds=None):
    started = time.monotonic()
    folder = stage_folder('a', seed=seed)
    folder.mkdir(parents=True, exist_ok=False)
    trained = 0
    try:
        manifest = check_manifest()
        schedule = manifest['schedule']['stage_a']
        updates = updates or schedule['updates']
        training_seconds = training_seconds or schedule['training_seconds']
        params = registered_params()
        forbidden = _exclusion_union(manifest)
        configure('a', seed=seed, stage_a_updates=updates, **params)
        torch.manual_seed(named_seed(NAMESPACE_TORCH, seed))
        model = new_model(seed)
        initial = C.fingerprint(model)
        optimizer = T.optimizer_for(model)
        rng = world_rng(seed)
        flops = 0
        log = (folder/'log.jsonl').open('x')
        training_start = time.monotonic()
        for step in range(updates):
            R.deadline(wave_start, schedule['work_seconds'])
            if time.monotonic()-training_start >= training_seconds:
                raise TimeoutError('registered stage-A training time cap')
            set_step(step)
            batch = training_batch_stage_a(rng, 16, forbidden)
            if params['presented_exclusion_check']:
                assert_no_validation_overlap(forbidden, batch.one_hop)
            flops += training_flops_stage_a(batch, model)
            _step_stage_a(model, optimizer, batch, step)
            trained += 1
            for key, value in batch.accounting['relations'].items():
                STATE['running'][key] = STATE['running'].get(key, 0) + value
            if trained % LOG_EVERY_A == 0:
                was = model.training
                model.eval()
                probe = G1.one_hop_by_relation(model, batch.one_hop,
                                               batch.one_hop_targets.answer)
                model.train(was)
                line = dict(stage='a', seed=seed, update=trained, **probe,
                            kept_fraction=batch.plan['fraction'],
                            lr=lr_stage_a(step, updates),
                            seconds=time.monotonic()-training_start,
                            records_by_relation=dict(STATE['running']))
                log.write(json.dumps(line)+'\n'); log.flush()
                print(json.dumps(line), flush=True)
        log.close()
        seconds = time.monotonic()-training_start
        checkpoint = folder/'stage_a.pt'
        torch.save(dict(state_dict=model.state_dict(), optimizer=optimizer.state_dict(),
                        torch_rng=torch.get_rng_state(), world_rng=rng.getstate(),
                        vrng=G1.STATE['vrng'].getstate(), xrng=G1.STATE['xrng'].getstate(),
                        seed=seed, updates=trained, params=dict(params),
                        architecture=dict(ARCHITECTURE),
                        model_seed=named_seed(NAMESPACE_MODEL, seed),
                        torch_seed=named_seed(NAMESPACE_TORCH, seed),
                        launch_sha256=C.sha(OUT/'astra_canonical_operator_launch.json')),
                   checkpoint)
        C.write_new(folder/'training.json',
                    dict(stage='a', seed=seed, updates=trained, seconds=seconds, flops=flops,
                         updates_per_second=trained/max(seconds, 1e-9),
                         initial_fingerprint=initial, final_fingerprint=C.fingerprint(model),
                         checkpoint_sha256=C.sha(checkpoint),
                         streams=dict(model=NAMESPACE_MODEL, torch=NAMESPACE_TORCH,
                                      world=NAMESPACE_WORLD, curriculum=NAMESPACE_A,
                                      extra=NAMESPACE_A_EXTRA),
                         attribute_records=trained*16*(4+params['stage_a_extra']),
                         link_records=0, two_hop_records=0, monolithic_records=0,
                         gold_entities_used=0, evidence_lines_used=0,
                         qualified='not evaluated: run the `qualify` command'))
        check_manifest()
        C.write_new(folder/'completion.json',
                    dict(stage='a', seed=seed, complete=True, updates=trained,
                         seconds=time.monotonic()-started,
                         wave_elapsed=time.monotonic()-wave_start,
                         peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                         registered_files_unchanged=True))
    except BaseException as exc:
        C.write_new(folder/'failure.json',
                    dict(stage='a', seed=seed, complete=False, updates=trained,
                         seconds=time.monotonic()-started, error=repr(exc),
                         traceback=traceback.format_exc()))
        raise


# --------------------------------------------------------------------- the stage-A gate

FAILED_MESSAGE = 'stage A failed; stage-B hypothesis untested for this seed'


def load_stage_a(seed):
    path = stage_folder('a', seed=seed)/'stage_a.pt'
    if not path.exists():
        raise RuntimeError(f'seed {seed}: stage A has not been run')
    saved = P.load(path)
    assert saved['seed'] == seed, (saved['seed'], seed)
    assert saved['launch_sha256'] == C.sha(OUT/'astra_canonical_operator_launch.json'), \
        'stage_a.pt was produced under a different registered manifest'
    return saved


def model_from(saved):
    model = A.CanonicalOperator(**saved['architecture'])
    model.load_state_dict(saved['state_dict'], strict=True)
    assert model.parameters_count() == PARAMETERS, model.parameters_count()
    return model


def qualify(seeds):
    """Evaluate the stage-A gate ONCE per seed and write an immutable verdict file.

    Only the FIXED FINAL stage-A checkpoint can qualify: this reads ``stage_a.pt`` and
    nothing else. There is no checkpoint search, no replacement seed and no extension; an
    extended stage A would be a new registration.
    """
    manifest = check_manifest()
    sets = load_validation(manifest, labels=('qualification',))
    thresholds = registered_thresholds(manifest, 'qualification')
    vset = sets['qualification']
    launch = C.sha(OUT/'astra_canonical_operator_launch.json')
    summary = []
    for seed in seeds:
        folder = stage_folder('a', seed=seed)
        checkpoint = folder/'stage_a.pt'
        saved = load_stage_a(seed)
        counts = qualification_counts(model_from(saved), vset)
        ok, reasons = qualification_verdict(counts, thresholds)
        blob = dict(experiment=NAME, stage='a', seed=seed, qualified=bool(ok),
                    evaluated_utc=_now(), thresholds=dict(thresholds), counts=counts,
                    reasons=reasons, checkpoint_sha256=C.sha(checkpoint),
                    launch_sha256=launch,
                    validation_fingerprint=set_fingerprint(vset),
                    validation_label=vset['label'],
                    note=('qualified' if ok else FAILED_MESSAGE),
                    evaluator_only=True, fixed_final_checkpoint_only=True)
        C.write_new(folder/'qualification.json', blob)
        summary.append(blob)
        print(json.dumps(dict(seed=seed, qualified=bool(ok), reasons=reasons,
                              attribute=counts['attribute_correct'],
                              terminal=counts['terminal_true_endpoint_correct'])), flush=True)
    passed = [b['seed'] for b in summary if b['qualified']]
    print(json.dumps(dict(registered_seeds=list(SEEDS), evaluated=list(seeds),
                          qualified=passed,
                          qualified_of_registered=f'{len(passed)}/{len(SEEDS)}',
                          failed=[dict(seed=b['seed'], note=FAILED_MESSAGE)
                                  for b in summary if not b['qualified']])), flush=True)
    return summary


def require_qualified(seed):
    """Stage B REFUSES to run for a seed that has not passed the gate on this manifest."""
    path = stage_folder('a', seed=seed)/'qualification.json'
    if not path.exists():
        raise RuntimeError(f'seed {seed}: stage-A qualification has not been evaluated; '
                           f'run the `qualify` command before any stage-B wave')
    blob = json.loads(path.read_text())
    if not blob.get('qualified'):
        raise RuntimeError(f'seed {seed}: {FAILED_MESSAGE}')
    checkpoint = stage_folder('a', seed=seed)/'stage_a.pt'
    if not checkpoint.exists():
        raise RuntimeError(f'seed {seed}: stage-A checkpoint missing')
    if blob.get('checkpoint_sha256') != C.sha(checkpoint):
        raise RuntimeError(f'seed {seed}: qualification was evaluated on a DIFFERENT '
                           f'stage-A checkpoint; run invalid')
    if blob.get('launch_sha256') != C.sha(OUT/'astra_canonical_operator_launch.json'):
        raise RuntimeError(f'seed {seed}: qualification was evaluated under a different '
                           f'registered manifest; run invalid')
    return blob


def worker_stage_b(seed, arm, wave_start, updates=None, training_seconds=None):
    started = time.monotonic()
    folder = stage_folder('b', arm, seed)
    folder.mkdir(parents=True, exist_ok=False)
    trained = 0
    try:
        manifest = check_manifest()
        assert arm in manifest['arms'], f'arm {arm} is not registered in this manifest'
        schedule = manifest['schedule']['stage_b']
        updates = updates or schedule['updates']
        training_seconds = training_seconds or schedule['training_seconds']
        params = registered_params()
        forbidden = _exclusion_union(manifest)
        gate = require_qualified(seed)                 # the gate, before anything is loaded
        anchors = stage_b_schedule_anchors(updates)
        measure_every = schedule.get('measure_every', MEASURE_EVERY_B)
        for key in ('updates', 'warmup', 'peak', 'flat_through', 'final'):
            assert anchors[key] == schedule[key], (key, anchors[key], schedule[key])
        saved = load_stage_a(seed)
        model = model_from(saved)
        start_fingerprint = C.fingerprint(model)
        frozen = make_frozen(model)
        frozen_fingerprint = C.fingerprint(frozen)
        assert frozen_fingerprint == start_fingerprint
        optimizer = T.optimizer_for(model)
        optimizer.load_state_dict(saved['optimizer'])
        torch.set_rng_state(saved['torch_rng'])
        rng = random.Random()
        rng.setstate(saved['world_rng'])
        # ``configure`` gives stage B its OWN curriculum stream (``NAMESPACE_B``), identical
        # across arms; stage A's ``vrng``/``xrng`` are carried in ``stage_a.pt`` for the
        # record only. The WORLD stream continues from the state stage A ended on, so the
        # arms see identical full stories, questions and ordering.
        configure('b', seed=seed, arm=arm, frozen=frozen, stage_b_updates=updates, **params)
        assert_frozen_intact(frozen, frozen_fingerprint, optimizer, 'initialisation')
        sets = load_validation(manifest, labels=('probe-six', 'probe-sixteen',
                                                 'confirm-six', 'confirm-sixteen'))
        diagnostics = (folder/'diagnostics.jsonl').open('x')

        def write(line):
            diagnostics.write(json.dumps(line)+'\n')
            diagnostics.flush()
            print(json.dumps(line), flush=True)

        def measure(update, kind):
            assert_frozen_intact(frozen, frozen_fingerprint, optimizer,
                                 f'checkpoint {update}')
            full = kind == 'full'
            labels = (('probe-six', 'probe-sixteen') if full else ('probe-six',))
            blob = {label: measure_set(model, sets[label], frozen, execution=full)
                    for label in labels}
            write(dict(stage='b', arm=arm, seed=seed, update=update, kind=f'probe-{kind}',
                       seconds=time.monotonic()-started,
                       frozen_unchanged=True, probes=blob))
            return blob

        initial = measure(0, 'full')                   # BEFORE any stage-B update
        model.train()
        flops = 0
        training_start = time.monotonic()
        for step in range(updates):
            R.deadline(wave_start, schedule['work_seconds'])
            if time.monotonic()-training_start >= training_seconds:
                raise TimeoutError('registered stage-B training time cap')
            set_step(step)
            batch = training_batch_stage_b(rng, 16, forbidden)
            if params['presented_exclusion_check']:
                assert_no_validation_overlap(forbidden, batch.one_hop, batch.link,
                                             batch.terminal)
            assert link_weights(batch) == (1/3, 1/3), link_weights(batch)
            flops += training_flops_stage_b(batch, model, arm, frozen)
            _step_stage_b(model, optimizer, batch, step, updates)
            trained += 1
            for key, value in batch.accounting['relations'].items():
                STATE['running'][key] = STATE['running'].get(key, 0) + value
            if trained % measure_every == 0:
                write(dict(stage='b', arm=arm, seed=seed, update=trained, kind='train',
                           lr=lr_stage_b(step, updates),
                           seconds=time.monotonic()-training_start,
                           **G1.train_diagnostics(model, batch, 'shared' if arm == 'shared'
                                                  else 'frozen-terminal', frozen)))
                measure(trained, 'probe')
        seconds = time.monotonic()-training_start
        final = measure(trained, 'full')
        assert_frozen_intact(frozen, frozen_fingerprint, optimizer, 'final scoring')
        scores = {label: score_systems(model, sets[label],
                                       frozen if arm in FROZEN_ARMS else None)
                  for label in ('confirm-six', 'confirm-sixteen')}
        thresholds = registered_thresholds(manifest, 'acceptance')
        verdicts = {label: acceptance_verdict(scores[label], thresholds)
                    for label in scores}
        assert_frozen_intact(frozen, frozen_fingerprint, optimizer, 'after final scoring')
        diagnostics.close()
        checkpoint = folder/'final.pt'
        torch.save(dict(state_dict=model.state_dict(), seed=seed, arm=arm, updates=trained,
                        architecture=dict(ARCHITECTURE),
                        launch_sha256=C.sha(OUT/'astra_canonical_operator_launch.json')),
                   checkpoint)
        C.write_new(folder/'final_score.json',
                    dict(stage='b', arm=arm, arm_kind=('primary' if arm in PRIMARY_ARMS
                                                       else 'diagnostic, NOT frozen'),
                         seed=seed, updates=trained, seconds=seconds,
                         updates_per_second=trained/max(seconds, 1e-9), flops=flops,
                         stage_a_fingerprint=start_fingerprint,
                         frozen_fingerprint=frozen_fingerprint,
                         frozen_unchanged=C.fingerprint(frozen) == frozen_fingerprint,
                         frozen_checked_at=['initialisation', 'every logged checkpoint',
                                            'final scoring'],
                         final_fingerprint=C.fingerprint(model),
                         checkpoint_sha256=C.sha(checkpoint),
                         gate=dict(qualified=True,
                                   checkpoint_sha256=gate['checkpoint_sha256']),
                         schedule=anchors, acceptance=dict(thresholds),
                         initial=initial, final=final,
                         confirmation=scores, verdicts=verdicts,
                         registered_seed_denominator=len(SEEDS),
                         supplied=['the decomposition (LINK call then terminal call)',
                                   'the token grammar',
                                   'visible fact parsing']))
        check_manifest()
        C.write_new(folder/'completion.json',
                    dict(stage='b', arm=arm, seed=seed, complete=True, updates=trained,
                         seconds=time.monotonic()-started,
                         wave_elapsed=time.monotonic()-wave_start,
                         peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                         final_checkpoint_only=True, frozen_weights_unchanged=True,
                         registered_files_unchanged=True))
    except BaseException as exc:
        C.write_new(folder/'failure.json',
                    dict(stage='b', arm=arm, seed=seed, complete=False, updates=trained,
                         seconds=time.monotonic()-started, error=repr(exc),
                         traceback=traceback.format_exc()))
        raise


# ------------------------------------------------------------------------------- commands

def _register_key(path):
    """Manifest key that ``check_manifest`` can resolve: ROOT-relative, else absolute."""
    path = Path(path).resolve()
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def freeze(schedule, params, arms):
    """Hash every registered source, the five validation sets and the preregistration."""
    if not DEV_OUT:
        assert params['probe_six'] == params['confirm_six'] == 512
        assert params['probe_sixteen'] == params['confirm_sixteen'] == 512
        assert params['qualification_two_hop'] == 512
        assert (params['qualification_attribute'] == params['probe_attribute']
                == params['confirm_attribute'] == 512)
        assert schedule['stage_a']['updates'] == STAGE_A_UPDATES
        assert schedule['stage_b']['updates'] == STAGE_B_UPDATES
        assert schedule['stage_b']['warmup'] == STAGE_B_WARMUP
        assert schedule['stage_b']['flat_through'] == STAGE_B_FLAT_THROUGH
        assert schedule['stage_b']['measure_every'] == MEASURE_EVERY_B
        assert params['presented_exclusion_check'] is True
    union_path = validation_dir()/'exclusion_union.json'
    validation_path = validation_dir()/'validation.json'
    assert union_path.exists() and validation_path.exists(), \
        'run `build-validation` before `freeze`'
    v1 = json.loads((G1.V1/'astra_canonical_operator_launch.json').read_text())
    files = {name: C.sha(ROOT/name) for name in v1['files']
             if not name.startswith('design/') and (ROOT/name).exists()}
    changed = [n for n in files if files[n] != v1['files'][n]]
    assert not changed, changed
    for extra in (Path(V.__file__).resolve(), Path(S.__file__).resolve(),
                  Path(G1.__file__).resolve(), Path(__file__).resolve(), prereg_path(),
                  union_path, validation_path):
        files[_register_key(extra)] = C.sha(extra)
    if DEV_OUT:
        assert params['qualification_two_hop'] == params['qualification_attribute']
        assert params['confirm_six'] == params['confirm_attribute']
        qualification = dict(denominator=params['qualification_attribute'],
                             attribute=0, terminal_true_endpoint=0)
        acceptance = dict(denominator=params['confirm_attribute'], link=0, attribute=0,
                          path_and_answer=0)
    else:
        qualification, acceptance = dict(QUALIFY), dict(ACCEPT)
    manifest = dict(created_utc=_now(), experiment=NAME, seeds=list(SEEDS),
                    arms=list(arms), primary_arms=list(PRIMARY_ARMS),
                    diagnostic_arms=[a for a in arms if a in DIAGNOSTIC_ARMS],
                    params=dict(params), schedule=schedule,
                    acceptance=acceptance, qualification=qualification,
                    exclusion_path=str(union_path),
                    original_exclusion_path=str(registered_exclusion_path()),
                    validation_path=str(validation_path),
                    validation=json.loads(validation_path.read_text())['sets'],
                    panels=v1['panels'], files=files, dev_out=DEV_OUT,
                    v1_launch_sha256=C.sha(G1.V1/'astra_canonical_operator_launch.json'),
                    withdrawn_predecessor='fable-link-isolation-20260920 (v1, never run)')
    OUT.mkdir(parents=True, exist_ok=True)
    C.write_new(OUT/'astra_canonical_operator_launch.json', manifest)
    print(len(files), 'files frozen', NAME,
          C.sha(OUT/'astra_canonical_operator_launch.json'))


def wave(stage, arm, seeds, name):
    manifest = check_manifest()
    refused = {}
    runnable = list(seeds)
    if stage == 'b':
        assert arm in manifest['arms'], f'arm {arm} is not registered in this manifest'
        runnable = []
        for seed in seeds:
            try:
                require_qualified(seed)
                runnable.append(seed)
            except RuntimeError as exc:
                refused[str(seed)] = str(exc)
                print(json.dumps(dict(stage='b', arm=arm, seed=seed, refused=str(exc))),
                      flush=True)
    schedule = manifest['schedule']['stage_a' if stage == 'a' else 'stage_b']
    folder = stage_folder(stage, arm)/name
    folder.mkdir(parents=True, exist_ok=False)
    cap, start = schedule['terminate_seconds'], time.monotonic()
    env = dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
               VECLIB_MAXIMUM_THREADS='1', PYTHONDONTWRITEBYTECODE='1')
    procs = []
    for seed in runnable:
        handle = (folder/f'seed-{seed}.log').open('x')
        args = [R.PYTHON, '-B', str(Path(__file__).resolve()), 'worker', '--stage', stage,
                '--seed', str(seed), '--wave-start', str(start)]
        if stage == 'b':
            args += ['--arm', arm]
        procs.append(subprocess.Popen(args, stdout=handle, stderr=subprocess.STDOUT, env=env,
                                      start_new_session=True))
    while any(p.poll() is None for p in procs):
        if time.monotonic()-start >= cap-2:
            for p in procs:
                if p.poll() is None: p.terminate()
            time.sleep(.5)
            for p in procs:
                if p.poll() is None: p.kill()
            break
        time.sleep(.5)
    exits = [p.wait() for p in procs]
    complete = all(c == 0 for c in exits) and all(
        (stage_folder(stage, arm, s)/'completion.json').exists() for s in runnable)
    C.write_new(folder/'completion.json',
                dict(seconds=time.monotonic()-start, exit_codes=exits, complete=complete,
                     seeds=list(runnable), refused=refused, requested=list(seeds),
                     registered_seed_denominator=len(SEEDS), stage=stage, arm=arm))
    print(json.dumps(dict(stage=stage, arm=arm, seconds=time.monotonic()-start,
                          exit_codes=exits, complete=complete, refused=refused)), flush=True)


# -------------------------------------------------------------------------------- report

REPORT_COLUMNS = (('link_accuracy', 'LINK acc'), ('link_accuracy_entity_argmax', 'LINK ent'),
                  ('p_link_true', 'p(true)'), ('p_link_wrong_present', 'p(wrong)'),
                  ('p_link_absent', 'p(absent)'), ('p_link_non_entity', 'p(non-ent)'),
                  ('terminal_margin', 'T margin'), ('shared_answer_rate', 'collide'),
                  ('one_hop_accuracy_r8', 'attr r8'), ('one_hop_accuracy_r9', 'attr r9'),
                  ('one_hop_accuracy_r10', 'attr r10'))


def _cell(value):
    return '  --  ' if value is None else f'{value:6.3f}'


def report(seeds=SEEDS, arms=None, root=None):
    """Per seed, per arm, per inference system. Nothing is ever averaged across seeds."""
    root = Path(root) if root else OUT
    arms = arms or list(PRIMARY_ARMS) + list(DIAGNOSTIC_ARMS)
    launch = root/'astra_canonical_operator_launch.json'
    manifest = json.loads(launch.read_text()) if launch.exists() else {}
    accept = dict(manifest.get('acceptance', ACCEPT))
    qualify_at = dict(manifest.get('qualification', QUALIFY))

    print('=== stage-A qualification gate (development validation) ===')
    gate = {}
    for seed in seeds:
        path = root/f'stage-a/seed-{seed}/qualification.json'
        if not path.exists():
            print(f'  seed {seed}: (not evaluated)')
            gate[seed] = None
            continue
        blob = json.loads(path.read_text())
        gate[seed] = blob
        counts = blob['counts']
        print(f'  seed {seed}: {"QUALIFIED" if blob["qualified"] else FAILED_MESSAGE} '
              f'| attr ' + '/'.join(str(counts['attribute_correct'][str(r)])
                                    for r in ATTRIBUTE_RELATIONS) +
              f' of {qualify_at["denominator"]}'
              f' | terminal-given-true-endpoint '
              f'{counts["terminal_true_endpoint_correct"]}/{qualify_at["denominator"]}')
        for reason in blob['reasons']:
            print(f'      - {reason}')
    qualified = [s for s in seeds if gate.get(s) and gate[s]['qualified']]
    print(f'  qualified {len(qualified)}/{len(SEEDS)} registered seeds '
          f'(denominator is always the original three).')

    for label in ('probe-six', 'probe-sixteen'):
        print(f'\n=== stage-B trajectory probe: {label} '
              f'(initial = stage A, final = after stage B) ===')
        header = (f'{"seed":>5} {"arm":<20} {"when":<8} '
                  + ' '.join(f'{title:>10}' for _, title in REPORT_COLUMNS))
        print(header)
        print('-'*len(header))
        for seed in seeds:
            for arm in arms:
                path = root/f'stage-b/{arm}/seed-{seed}/final_score.json'
                if not path.exists():
                    print(f'{seed:>5} {arm:<20} (missing)')
                    continue
                blob = json.loads(path.read_text())
                for when in ('initial', 'final'):
                    if label not in blob[when]:
                        continue
                    row = blob[when][label]
                    cells = ' '.join(f'{_cell(row.get(k)):>10}' for k, _ in REPORT_COLUMNS)
                    print(f'{seed:>5} {arm:<20} {when:<8} {cells}')

    print(f'\n=== FINAL CONFIRMATION (confirm-six), acceptance per qualified seed ===')
    print(f'    LINK >= {accept["link"]}/{accept["denominator"]}, retained attribute '
          f'>= {accept["attribute"]}/{accept["denominator"]} per relation, complete correct '
          f'two-call paths AND final answers >= {accept["path_and_answer"]}/'
          f'{accept["denominator"]}.')
    tally = {}
    for arm in arms:
        for seed in seeds:
            path = root/f'stage-b/{arm}/seed-{seed}/final_score.json'
            if not path.exists():
                note = ('stage A failed; stage-B hypothesis untested for this seed'
                        if gate.get(seed) and not gate[seed]['qualified'] else 'missing')
                print(f'  {arm:<20} seed {seed}: {note}')
                continue
            blob = json.loads(path.read_text())
            score = blob['confirmation']['confirm-six']
            kind = blob.get('arm_kind', '')
            print(f'  {arm:<20} seed {seed} [{kind}] LINK '
                  f'{score["link_correct"]}/{score["link_total"]} | attr '
                  + '/'.join(str(score['attribute_correct'][str(r)])
                             for r in ATTRIBUTE_RELATIONS))
            for system, verdict in blob['verdicts']['confirm-six'].items():
                blob_system = score['systems'][system]
                mark = 'ACCEPT' if verdict['accepted'] else 'reject'
                print(f'      {system:<22} paths+answers '
                      f'{blob_system["path_and_answer_correct"]}/{blob_system["n"]} '
                      f'answers {blob_system["answer_correct"]}/{blob_system["n"]} '
                      f'aborted {blob_system["aborted"]} -> {mark}')
                for reason in verdict['reasons']:
                    print(f'          - {reason}')
                tally.setdefault((arm, system), []).append(verdict['accepted'])
    print('\n  summary (denominator is the ORIGINAL three registered seeds):')
    for (arm, system), results in sorted(tally.items()):
        print(f'    {arm:<20} {system:<22} accepted {sum(results)}/{len(SEEDS)} '
              f'(scored {len(results)}; qualified {len(qualified)})')


# ---------------------------------------------------------------------------------- main

def default_schedule(args):
    anchors = stage_b_schedule_anchors(args.stage_b_updates)
    return dict(
        visits_per_update=16,
        stage_a=dict(updates=args.stage_a_updates, training_seconds=args.stage_a_seconds,
                     work_seconds=args.stage_a_seconds+240,
                     terminate_seconds=args.stage_a_seconds+270,
                     lr='v3r shape rescaled to the stage length (retained from the proposal)'),
        stage_b=dict(updates=args.stage_b_updates, warmup=anchors['warmup'],
                     peak=anchors['peak'], flat_through=anchors['flat_through'],
                     final=anchors['final'], anchors=anchors,
                     measure_every=args.measure_every,
                     training_seconds=args.stage_b_seconds,
                     work_seconds=args.stage_b_seconds+240,
                     terminate_seconds=args.stage_b_seconds+270))


def _params_from(args):
    return normalize_params(dict(
        balance=args.balance, blind_lines=args.blind_lines, grow_g1=args.grow_g1,
        grow_g2=args.grow_g2, stage_a_extra=args.stage_a_extra,
        terminal_dedupe=args.terminal_dedupe, single_forward=args.single_forward,
        probe_six=args.probe_six, probe_sixteen=args.probe_sixteen,
        probe_per_visit=args.probe_per_visit, probe_attribute=args.probe_attribute,
        qualification_two_hop=args.qualification_two_hop,
        qualification_attribute=args.qualification_attribute,
        confirm_six=args.confirm_six, confirm_sixteen=args.confirm_sixteen,
        confirm_attribute=args.confirm_attribute,
        presented_exclusion_check=args.presented_exclusion_check,
        include_detached=args.include_detached))


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('command', choices=['build-validation', 'freeze', 'wave', 'worker',
                                        'qualify', 'report'])
    ap.add_argument('--stage', choices=list(STAGES))
    ap.add_argument('--arm', choices=list(ALL_ARMS))
    ap.add_argument('--seeds', default=','.join(map(str, SEEDS)))
    ap.add_argument('--name', default='wave-1')
    ap.add_argument('--seed', type=int)
    ap.add_argument('--wave-start', type=float)
    ap.add_argument('--root', default=None, help='report only: read from this folder')
    ap.add_argument('--stage-a-updates', type=int, default=STAGE_A_UPDATES)
    ap.add_argument('--stage-b-updates', type=int, default=STAGE_B_UPDATES)
    # Measured single-process, one torch thread (v1's cost table, same batches and model):
    # stage A 25.7 updates/s (117 s for 3,000); stage B 4.17 updates/s shared (719 s),
    # 6.45 frozen (465 s). v2 adds the every-100 six-person probe measurement on top.
    ap.add_argument('--stage-a-seconds', type=int, default=420)
    ap.add_argument('--stage-b-seconds', type=int, default=1200)
    # The spec's "every 100 updates". Only a dev-mode smoke may lower it; ``freeze`` refuses
    # any other value for a registered run.
    ap.add_argument('--measure-every', type=int, default=MEASURE_EVERY_B)
    ap.add_argument('--balance', action='store_true', default=DEFAULTS['balance'])
    ap.add_argument('--blind-lines', type=int, default=DEFAULTS['blind_lines'])
    ap.add_argument('--grow-g1', type=int, default=DEFAULTS['grow_g1'])
    ap.add_argument('--grow-g2', type=int, default=DEFAULTS['grow_g2'])
    ap.add_argument('--stage-a-extra', type=int, default=DEFAULTS['stage_a_extra'])
    ap.add_argument('--probe-six', type=int, default=DEFAULTS['probe_six'])
    ap.add_argument('--probe-sixteen', type=int, default=DEFAULTS['probe_sixteen'])
    ap.add_argument('--probe-per-visit', type=int, default=DEFAULTS['probe_per_visit'])
    ap.add_argument('--probe-attribute', type=int, default=DEFAULTS['probe_attribute'])
    ap.add_argument('--qualification-two-hop', type=int,
                    default=DEFAULTS['qualification_two_hop'])
    ap.add_argument('--qualification-attribute', type=int,
                    default=DEFAULTS['qualification_attribute'])
    ap.add_argument('--confirm-six', type=int, default=DEFAULTS['confirm_six'])
    ap.add_argument('--confirm-sixteen', type=int, default=DEFAULTS['confirm_sixteen'])
    ap.add_argument('--confirm-attribute', type=int, default=DEFAULTS['confirm_attribute'])
    # The optional third DIAGNOSTIC arm. Not frozen; never relabelled as frozen.
    ap.add_argument('--include-detached', action='store_true',
                    default=DEFAULTS['include_detached'])
    # Both EXACT reductions are on by default.
    ap.add_argument('--no-terminal-dedupe', dest='terminal_dedupe', action='store_false')
    ap.add_argument('--no-single-forward', dest='single_forward', action='store_false')
    ap.add_argument('--no-presented-exclusion-check', dest='presented_exclusion_check',
                    action='store_false')
    ap.set_defaults(terminal_dedupe=True, single_forward=True,
                    presented_exclusion_check=True)
    return ap


if __name__ == '__main__':
    args = build_parser().parse_args()
    R.configure()
    R.OUT = OUT
    seeds = [int(s) for s in args.seeds.split(',')]
    if args.command == 'build-validation':
        build_validation_command(_params_from(args))
    elif args.command == 'freeze':
        params = _params_from(args)
        assert args.grow_g2 <= args.stage_a_updates, 'the curriculum must finish inside stage A'
        arms = list(PRIMARY_ARMS) + (list(DIAGNOSTIC_ARMS) if args.include_detached else [])
        freeze(default_schedule(args), params, arms)
    elif args.command == 'qualify':
        qualify(seeds)
    elif args.command == 'report':
        report(seeds, root=args.root)
    elif args.command == 'worker':
        assert args.stage in STAGES and args.seed is not None
        if args.stage == 'a':
            worker_stage_a(args.seed, args.wave_start)
        else:
            assert args.arm is not None
            worker_stage_b(args.seed, args.arm, args.wave_start)
    else:
        wave(args.stage, args.arm, seeds, args.name)
