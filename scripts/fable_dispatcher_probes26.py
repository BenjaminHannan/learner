"""Experiment 26 -- dispatcher fault-localisation probes.  NO TRAINING.

Binding specification:
    design/v3/26-dispatcher-stop-probes-registration-fable-review.md
    sha256 7d7708e79e7b755bfa47d50bd7aeb8b550d02b20930a313ad1547a7337a09f45

This script is ADDITIVE.  It imports the v1/v3/v4 dispatcher modules and the
experiment-19 trainer module and edits none of them; it writes only under its own
--out directory.  Nothing here trains, and the prohibited held-out operator checkpoint is
never named (V1.FrozenOperator refuses it by name in any case).

Sub-commands
    panel   build the 640 throwaway units of section 3 (namespace `fable-probe26-v1`),
            write them, their sha256, the section-2 code hashes and the verified
            checkpoint hashes.  Refuses to overwrite.
    probe   run probes A-D on ONE checkpoint (section 4), verifying that checkpoint's
            recorded sha256 BEFORE it is loaded.  Resumable: an existing output file
            for that checkpoint is left alone and the call is a no-op.
    report  apply the section-5 thresholds and the section-6 decision table
            mechanically; positive control first.  `--suffix control` reports the control
            and prints no row of the decision table; `--suffix final` refuses unless all
            twelve control and all nine registered checkpoints have been probed; any other
            report prints, in place of the table, the list of what is missing.

Version pinning: the panel manifest and every probe output record the sha256 of THIS
file, and `probe` and `report` refuse to touch a directory whose recorded source hash is
not the running one.  Editing the script means starting a fresh --out directory.

Probes (section 4)
    A  free run, first-fault typing (trained operator and, as a check, the oracle)
    B  the five existing handed-component replays (V3.INTERVENTIONS, unchanged),
       with native logits logged for `force_operation+subject`
    C  offset start: the gold subject and two chosen LINK positions are forced at
       steps 0 and 1 only; from step 2 the controller is free
    D  geometry of `model.question_context` (learned-position arms only)

Claim limits (section 7): a forced action is never an autonomous success; every
number from probes B and C is a diagnostic of one component with the others handed
to it; all of it is descriptive development evidence on throwaway units.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import statistics
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import fable_dispatcher as V1                                              # noqa: E402
import fable_dispatcher_v3 as V3                                           # noqa: E402
import fable_dispatcher_v4 as V4                                           # noqa: E402
import fable_novelty19_train as TR                                         # noqa: E402

torch = V4.torch
sha = V1.sha
write_new = V1.write_new

WORKTREE = HERE.parent

# --------------------------------------------------------------------------- frozen numbers

SPEC_PATH = WORKTREE / 'design' / 'v3' / '26-dispatcher-stop-probes-registration-fable-review.md'
SPEC_SHA256 = '7d7708e79e7b755bfa47d50bd7aeb8b550d02b20930a313ad1547a7337a09f45'

# the frozen forecasts.  `panel` records these hashes so a report can prove which text of
# P102-P117 the run was answering (audit M2).
FORECAST_DIR = WORKTREE / 'artifacts' / 'fable-dispatcher-probes26-20260921'
PREDICTIONS_PATH = FORECAST_DIR / 'FABLE-PREDICTIONS.md'
PREDICTIONS_RECORD_PATH = FORECAST_DIR / 'FABLE-PREDICTIONS.sha256.txt'
LEDGER_PATH = WORKTREE / 'artifacts' / 'fable-predictions-ledger.md'

NAMESPACE = 'fable-probe26-v1'                 # section 3; not any registered panel namespace
PANEL_N = 64                                   # indices 0..63 in every cell
CELLS26 = ('k3-prac', 'k3-held', 'k4-prac', 'k4-held', 'k5-prac', 'k5-held',
           'k6-prac', 'k6-held', 'k8-prac', 'k8-held')
EVAL_CAP = V3.EVAL_CAP                         # 16
BLOCK = 32                                     # the block the registered scorers used
PROBE_SEED = 260921                            # nothing samples; set so a stray RNG is pinned

LINK = V3.LINK                                 # 11
RELATIONS = (V3.FIRST_REL, V3.FIRST_REL + 1, V3.FIRST_REL + 2)      # 8, 9, 10

# section 2 code hashes at design time; `panel` records what it finds and `probe` stops
# on any change since `panel`.
CODE_FILES = ('fable_dispatcher_v4.py', 'fable_dispatcher_v3.py', 'fable_dispatcher.py',
              'fable_novelty19_train.py', 'fable_novelty19_data.py')
DESIGN_CODE_SHA256 = {
    'fable_dispatcher_v4.py': 'f4e8ffd05b25662c052d6f2d508cdd7bb30bd4ab54c188cd74fd9791d5dff4e2',
    'fable_dispatcher_v3.py': '8fa4674d1b1dbcad5ae4fe51f4bfe74fe3fb6be3361569b825a4183be3aa8d53',
    'fable_dispatcher.py': '2081a94cae4f3d152230e86d58772d4c5aeabdb03dac46be5efff85fefa91545',
    'fable_novelty19_train.py': '77644a1f15e6e683b2260261b04411a6ee30c8bb74f80121a8ef7318749cd5a8',
    'fable_novelty19_data.py': 'ef1df0e149aa4741a22f7185fadb9eaeb054b072d50c09a1ad2a196a998ae9de',
}

OPERATOR_PATH = TR.OPERATOR_PATH
OPERATOR_SHA256 = TR.OPERATOR_SHA256

_N19 = WORKTREE / 'artifacts' / 'fable-novelty19-replay-20260920' / 'runs'
_N19B = WORKTREE / 'artifacts' / 'fable-novelty19b-u8-20260920' / 'runs'
_V4 = WORKTREE / 'artifacts' / 'fable-dispatcher-v4-20260920'

# family -> dict(group, arm, loader, members {id: (path, sha256, seed)})
# group: 'control'    the twelve v4 checkpoints, the known-answer positive control
#        'registered' the nine experiment-19/19b checkpoints of the decision table
#        'optional'   the descriptive 19-U family (reported, not in the decision table)
FAMILIES = {}


def _register(family, group, arm, loader, members):
    FAMILIES[family] = dict(family=family, group=group, arm=arm, loader=loader,
                            members=dict(members))


_register('19-awake', 'registered', 'reg+ctx', 'tr', {
    f'19-awake-s{seed}': (_N19 / f'awake-D-s{seed}' / 'ckpt-006000.pt', digest, seed)
    for seed, digest in (
        (1900, 'bd4330b6737600ab8b36564237e117244607729c8f2bc6a84c003bd33cabf4b1'),
        (1901, '56dbc8f5e96b210eef29441d8dbaec2c79c816faa33f84ebe4167db88c58632e'),
        (1902, 'b3c182ebfdac9433ab379425f175fedfa58fdf9a2ad181d6601e2d9423fc5740'))})

_register('19b-U5', 'registered', 'reg+ctx', 'tr', {
    f'19b-U5-s{seed}': (_N19B / f'offline-D-s{seed}-U5' / 'ckpt-002000.pt', digest, seed)
    for seed, digest in (
        (1900, '3ba084db4cf17dc8680c2419f02cb11a7e22b7e9aa9e0c16c6f1a540799d9989'),
        (1901, '1034f27c871d40809ba30e20f7299f5995961538fac90fab6e5ef114dbc43e20'),
        (1902, '9de47eafeed754e820be46e609402ae74e91eb50279db0299a8e16a1f3955045'))})

_register('19b-U8', 'registered', 'reg+ctx', 'tr', {
    f'19b-U8-s{seed}': (_N19B / f'offline-D-s{seed}-U8' / 'ckpt-002000.pt', digest, seed)
    for seed, digest in (
        (1900, '2cb2675200db919a8a0e89af40d7b5960956988229474a5017340ce8002d379a'),
        (1901, '898fd21affc6624eeaf81e64555516b4a8245f233397b615080cca0d93d0674f'),
        (1902, 'd90f51b37fc42abff8510d17345b352ecafe1e6181888be3518a3051be441980'))})

_register('19-U', 'optional', 'reg+ctx', 'tr', {
    f'19-U-s{seed}': (_N19 / f'offline-D-s{seed}-U' / 'ckpt-002000.pt', digest, seed)
    for seed, digest in (
        (1900, '4ad7fd385b6c3a9759e132e0a40a930c648dc72d5c19a62ddad1dd104db73163'),
        (1901, 'c4a2ad8939b4dbc7ba4a574ed8a382c81818ac795876032b9e0550af2fc854d1'),
        (1902, '2d28373fa937e2aa44e0ced9d645876b1492e9a217e132d2f2259cfa4f1333e0'))})

_V4_SHA = {
    'reg-ctx': ('022125ac80b8fbd7702506e00d169a0dfc489463e0c5cd6a2dd0bebe9ce5a0cc',
                '6dc0e9ca72303bfd08d6b1ca9141f9960c4580e4ced7d5e03406dd9669a394f2',
                'aba9da4d3ad8e403b7fcfbd32ff034cd3cfb9c63b2c1fd125537e5c220c003e3'),
    'ctx': ('f5eb693edfc0616b1eeac01059159a254f9bd928a8ddf011278a7c547c640b56',
            '42444cea7e3973ddd918a52849378a5664c380135cae4cbac4dcd36562dc7cf9',
            '5f96206b67388de36bf2337aa7b2d14001f3e1047aa2febfe8541088379bdce0'),
    'reg': ('dec8a6363303410677469a298dd144ee49d798acdc80b1b80cbd516a86724c1a',
            'b36a5d84ee01d853abd8263ce153fe3c69f0b4617dcf7e58d3281f23d73156e1',
            '4282a44067d22fb66251aeabe7e9beeb7ae1942dc4e6f6c3055c38970aa8bdeb'),
    'v3-repro': ('a62b9be8f8c2357b59d05c8442dd294b76dc767710d88553d97b68b934552244',
                 '3b259b05799075bedba58d9caadb74df0fbdb9a09629a3506a30386561ca2763',
                 'edd13d508c60cc88b2d4adf1231c52bbf16b0a0db09e9c7c76fb0f9ba2743ff6'),
}
for _dir, _digests in _V4_SHA.items():
    _arm = 'reg+ctx' if _dir == 'reg-ctx' else _dir
    _register(f'v4-{_dir}', 'control', _arm, 'v4', {
        f'v4-{_dir}-s{seed}': (_V4 / _dir / f'seed-{seed}' / 'dispatcher.pt', _digests[seed], seed)
        for seed in (0, 1, 2)})

CHECKPOINTS = {}
for _family in FAMILIES.values():
    for _id, (_path, _digest, _seed) in _family['members'].items():
        CHECKPOINTS[_id] = dict(id=_id, family=_family['family'], group=_family['group'],
                                arm=_family['arm'], loader=_family['loader'], path=_path,
                                sha256=_digest, seed=_seed)

CONTROL_IDS = tuple(k for k, v in CHECKPOINTS.items() if v['group'] == 'control')
REGISTERED_IDS = tuple(k for k, v in CHECKPOINTS.items() if v['group'] == 'registered')
LEARNED_POSITION_ARMS = ('ctx', 'reg+ctx')

# section 5 thresholds -- exactly these numbers, nowhere else in the file.
MARK_R1 = 61          # GPT-6 Pro's own rule for "STOP right on handed prefixes"
MARK_R3 = 59          # the project's cell mark, V4.CELL_MARK
MARK_R2 = 48          # "early attribute dominates" / probe C majority
MARK_R5 = 16          # "premature STOP survives a handed prefix"
MARK_R7_RATIO = 0.10
MARK_R7_MARGIN = 0.01
assert MARK_R3 == V4.CELL_MARK


# --------------------------------------------------------------------------- small helpers


def code_hashes():
    return {name: sha(HERE / name) for name in CODE_FILES}


def source_sha256():
    """The sha256 of THIS script.  Every output records it and every later command
    refuses to mix outputs written by a different version (audit B1)."""
    return sha(Path(__file__).resolve())


def forecast_hashes():
    """Audit M2: pin the text of the frozen forecasts at panel time.

    Nothing is committed to git, so without these hashes the only evidence that
    P102-P117 predate the run is a file mtime.  Missing files are recorded as null
    rather than refused, so a scratch/dev directory outside the registered layout still
    builds; the report prints whatever is recorded.
    """
    def maybe(path):
        return sha(path) if Path(path).is_file() else None

    recorded = None
    if PREDICTIONS_RECORD_PATH.is_file():
        first = PREDICTIONS_RECORD_PATH.read_text().split()
        recorded = first[0] if first else None
    found = maybe(PREDICTIONS_PATH)
    return dict(
        predictions=str(PREDICTIONS_PATH), predictions_sha256=found,
        predictions_recorded_sha256=recorded,
        predictions_matches_its_record=bool(found is not None and found == recorded),
        ledger=str(LEDGER_PATH), ledger_sha256=maybe(LEDGER_PATH))


def question_layout(question):
    """Where the LINKs and the terminal relation sit in one raw question.

    A k-hop question is [QUESTION, asker, LINK * (k-1), relation, ANSWER], so the LINK
    positions are 2..k and the relation is at k+1 (`left` = 0: `pad_questions` puts the
    question at the left edge, and every unit in a cell has the same length).
    """
    links = [p for p, t in enumerate(question) if t == LINK]
    rels = [p for p, t in enumerate(question) if t in RELATIONS]
    if len(rels) != 1:
        raise ValueError(f'expected exactly one relation token in {question}')
    return dict(width=len(question), links=tuple(links), rel=rels[0])


def candidate_token(index, question, results, width):
    """The token a candidate index carries: a question position, or a result slot."""
    if index < width:
        return int(question[index]) if index < len(question) else 0
    slot = index - width
    return int(results[slot]) if 0 <= slot < len(results) else 0


def median(values):
    return float(statistics.median(values)) if values else None


def _counter(values):
    return dict(sorted(Counter(str(v) for v in values).items()))


# --------------------------------------------------------------------------- probe A classifier


CATEGORIES = ('NONE', 'OPERATOR', 'OP_EARLY_ATTR', 'OP_RUN_ON', 'SUBJECT', 'STOP_EARLY',
              'STOP_LATE', 'INVALID', 'OTHER')


def classify_first_fault(transcript, chain, status, pointers, question):
    """Type the FIRST free-run fault of one episode.  Pure; no model, no tensors.

    Section 4, probe A: the categories are tested in the order written there.  The raw
    `question` is needed only to type an INVALID pointer (which token the illegal
    pointer actually carried); it adds no label and no truth.

    Returns dict(category, index, detail).  `index` is the transcript index of the first
    fault, or the transcript length when only the length differs, or None for success.
    """
    transcript = [list(step) for step in transcript]
    chain = [list(step) for step in chain]
    width = len(question)
    results = [step[2] for step in transcript]
    if transcript == chain and status == 'answered':
        return dict(category='NONE', index=None, detail=None)
    common = min(len(transcript), len(chain))
    first = None
    for i in range(common):
        if transcript[i] != chain[i]:
            first = i
            break
    if first is not None:
        subject_t, operation_t, _result_t = transcript[first]
        subject_c, operation_c, _result_c = chain[first]
        if subject_t == subject_c and operation_t == operation_c:
            return dict(category='OPERATOR', index=first, detail='returned token wrong')
        if operation_c == LINK and operation_t in RELATIONS:
            return dict(category='OP_EARLY_ATTR', index=first,
                        detail=f'asked relation {operation_t} where the chain links')
        if operation_t == LINK and operation_c in RELATIONS:
            return dict(category='OP_RUN_ON', index=first,
                        detail='linked on where the chain takes the terminal relation')
        if operation_t == operation_c:
            return dict(category='SUBJECT', index=first, detail='operation right, subject wrong')
        return dict(category='OTHER', index=first,
                    detail=f'operation {operation_t} for chain operation {operation_c}')
    if len(transcript) < len(chain):
        if status == 'answered':
            return dict(category='STOP_EARLY', index=len(transcript),
                        detail=f'stopped after {len(transcript)} of {len(chain)} calls')
        if status == 'invalid_action':
            return dict(category='INVALID', index=len(transcript),
                        detail=_invalid_detail(pointers, question, results, width))
        return dict(category='OTHER', index=len(transcript), detail=f'short and {status}')
    if len(transcript) > len(chain):
        if status in ('answered', 'over_cap'):
            return dict(category='STOP_LATE', index=len(chain),
                        detail=f'{len(transcript)} calls for a {len(chain)}-call chain ({status})')
        if status == 'invalid_action':
            return dict(category='INVALID', index=len(chain),
                        detail=_invalid_detail(pointers, question, results, width))
        return dict(category='OTHER', index=len(chain), detail=f'long and {status}')
    if status == 'invalid_action':
        return dict(category='INVALID', index=len(chain),
                    detail=_invalid_detail(pointers, question, results, width))
    if status == 'over_cap':
        return dict(category='STOP_LATE', index=len(chain), detail='never chose STOP')
    return dict(category='OTHER', index=len(chain), detail=f'chain complete but {status}')


def _invalid_detail(pointers, question, results, width):
    """Which pointer was illegal, from the rollout's own `pointers` record.

    `rollout_v4` appends [subject, operation, -1] for the step whose action was refused
    and appends nothing to the transcript, so the illegal step is the last pointer row
    whose stop entry is -1.
    """
    illegal = [row for row in pointers if len(row) == 3 and row[2] == -1]
    if not illegal:
        return 'INVALID_UNKNOWN (no refused pointer row)'
    subject, operation, _ = illegal[-1]
    subject_token = candidate_token(subject, question, results, width)
    operation_token = candidate_token(operation, question, results, width)
    bad_subject = not (V1.ENTITY_MIN <= subject_token < V1.ENTITY_MAX)
    bad_operation = operation_token not in V1.OPS
    if bad_subject and bad_operation:
        kind = 'INVALID_BOTH'
    elif bad_subject:
        kind = 'INVALID_SUBJECT'
    elif bad_operation:
        kind = 'INVALID_OPERATION'
    else:
        kind = 'INVALID_UNKNOWN'
    return f'{kind} (subject slot {subject} token {subject_token}, ' \
           f'operation slot {operation} token {operation_token})'


def classify_rows(rows, units):
    """Classify every scored row of one cell side against its own unit's question."""
    out = []
    for row, unit in zip(rows, units):
        question = unit['a']['question']
        out.append(classify_first_fault(row['transcript'], row['truth_chain'], row['status'],
                                        row['pointers'], question))
    return out


def summarise_rows(rows, units):
    """Counts for one scored cell side: answers, strict, statuses, histograms, categories."""
    faults = classify_rows(rows, units)
    invalid_kinds = [f['detail'].split(' ')[0] for f in faults
                     if f['category'] == 'INVALID' and f['detail']]
    return dict(
        n=len(rows),
        answers=sum(int(r['correct']) for r in rows),
        strict=sum(int(r['strict_path']) for r in rows),
        loose=sum(int(r['loose_path']) for r in rows),
        answered=sum(r['status'] == 'answered' for r in rows),
        over_cap=sum(r['status'] == 'over_cap' for r in rows),
        invalid_action=sum(r['status'] == 'invalid_action' for r in rows),
        mean_calls=sum(r['calls'] for r in rows) / max(1, len(rows)),
        calls_histogram=_counter(r['calls'] for r in rows),
        first_fault_index=_counter('none' if f['index'] is None else f['index'] for f in faults),
        categories={k: sum(f['category'] == k for f in faults) for k in CATEGORIES},
        invalid_subtypes=_counter(invalid_kinds),
        operator_wrong_on_true_chain=sum(int(r.get('operator_chain_all') == 0) for r in rows),
        examples=[dict(index=r['index'], status=r['status'], calls=r['calls'],
                       category=f['category'], fault_index=f['index'], detail=f['detail'])
                  for r, f in list(zip(rows, faults))[:4]])


# --------------------------------------------------------------------------- probe C policy


def offset_start_policy(first, second, width, left=0):
    """Probe C: hand the gold subject and TWO chosen LINK positions, steps 0 and 1 only.

    Same signature as the inner `policy` of `V3.intervention_policy`.  The subject rule is
    that function's own (question position left+1 at step 0, then the most recent result
    slot); the operation is the condition's forced position.  STOP is never forced, and
    `step < 2` is the ONLY mask, so from step 2 on every component is the model's own.
    """
    positions = (int(first), int(second))

    def policy(step, tokens, results, n_results):
        batch = tokens.shape[0]
        mask = torch.full((batch,), bool(step < 2), dtype=torch.bool)
        subject = torch.where(n_results > 0, width + n_results - 1,
                              torch.full((batch,), left + 1, dtype=torch.long))
        chosen = positions[0] if step == 0 else positions[1]
        operation = torch.full((batch,), chosen, dtype=torch.long)
        return dict(subject=(subject, mask), operation=(operation, mask))
    return policy


def offset_conditions(layout, left=0):
    """S0 / S3 / S5 of section 4 for a k8 question (seven LINKs at left+2 .. left+8)."""
    links = layout['links']
    if len(links) != 7:
        raise ValueError(f'probe C is defined for k8 questions only; found {len(links)} LINKs')
    return dict(
        S0=dict(forced=(left + 2, left + 3), next=left + 4,
                note='as in a normal run'),
        S3=dict(forced=(left + 5, left + 6), next=left + 7,
                note='start deeper'),
        S5=dict(forced=(left + 7, left + 8), next=left + 9,
                note='control: the last two LINKs; "next" is the attribute'))


# --------------------------------------------------------------------------- native logit reading


@torch.no_grad()
def native_steps(model, flags, units, cell, prepared, cap, policy_factory, max_step,
                 conditions=None):
    """Run one policy over a cell and read the model's NATIVE logits at every step.

    `rollout_v4` stores the subject, operation and STOP logits the model itself produced,
    before the forced overwrite (`fable_dispatcher_v4.py:493-499`), so these numbers are
    the controller's own preferences while its executed actions were handed to it.

    Returns (per-step aggregates, scored rows) -- the rows are the same episodes, so a
    failure sub-type can be read off the same run.
    """
    steps = {}
    rows_out = []
    for block_index, start in enumerate(range(0, len(units), BLOCK)):
        chunk = units[start:start + BLOCK]
        _inputs, questions, table = prepared[block_index]
        tokens, present = V1.pad_questions(questions)
        width = int(tokens.shape[1])
        hops = torch.tensor([len(unit['a']['chain']) for unit in chunk], dtype=torch.long)
        policy = policy_factory(hops, width)
        record, gates = [], []
        episodes = V4.rollout_v4(model, tokens, present, table, torch.arange(len(chunk)), cap,
                                 mode='greedy', policy=policy, flags=flags, record=record,
                                 gates=gates)
        gate_at = {int(row['step']): row['gate'] for row in gates if row['gate'] is not None}
        layouts = [question_layout(unit['a']['question']) for unit in chunk]
        for entry in record:
            step = int(entry['step'])
            if step > max_step:
                continue
            bucket = steps.setdefault(step, _fresh_step_bucket())
            active = entry['active']
            operation = entry['operation']
            subject = entry['subject']
            stop_p = torch.softmax(entry['stop'].float(), -1)[:, 1]
            gate = gate_at.get(step)
            for i in range(len(chunk)):
                if not bool(active[i]):
                    continue
                layout = layouts[i]
                used = {int(p[1]) for p in episodes.pointers[i][:step]}
                _accumulate_step(bucket, operation[i], subject[i], float(stop_p[i]), layout, used,
                                 step, width,
                                 None if gate is None else float(gate[i]),
                                 conditions)
        for i, unit in enumerate(chunk):
            chain = unit['a']['chain']
            transcript = episodes.transcripts[i]
            answered = episodes.status[i] == 'answered'
            rows_out.append(dict(index=unit['index'], side='a', answer=int(episodes.answer[i]),
                                 target=unit['a']['answer'],
                                 correct=int(int(episodes.answer[i]) == unit['a']['answer']),
                                 status=episodes.status[i], calls=int(episodes.calls[i]),
                                 hops=len(chain), transcript=transcript,
                                 pointers=episodes.pointers[i], truth_chain=chain,
                                 strict_path=int(transcript == chain and answered),
                                 loose_path=int([[s, o] for s, o, _ in transcript]
                                                == [[s, o] for s, o, _ in chain] and answered)))
    return {str(k): _finish_step_bucket(v) for k, v in sorted(steps.items())}, rows_out


def _fresh_step_bucket():
    return dict(n_active=0, op_category=Counter(), subject_gold=0, p_stop=[],
                margin_unused_link_minus_rel=[], margin_rel_minus_best_link=[],
                margin_rel_minus_best_unused_link=[], adjacent_unused_link_abs=[],
                gate=[], offset_category=Counter())


def _accumulate_step(bucket, operation_logits, subject_logits, p_stop, layout, used, step, width,
                     gate, conditions):
    """One active row's native preferences at one step."""
    rel = layout['rel']
    links = layout['links']
    unused = [p for p in links if p not in used]
    logits = operation_logits
    choice = int(logits.argmax(-1))
    if choice == rel:
        category = 'REL'
    elif choice in links:
        category = 'UNUSED_LINK' if choice in unused else 'USED_LINK'
    else:
        category = 'OTHER'
    bucket['op_category'][category] += 1
    bucket['n_active'] += 1
    gold_subject = 1 if step == 0 else width + step - 1
    bucket['subject_gold'] += int(int(subject_logits.argmax(-1)) == gold_subject)
    bucket['p_stop'].append(p_stop)
    rel_logit = float(logits[rel])
    if links:
        bucket['margin_rel_minus_best_link'].append(
            rel_logit - float(max(logits[p] for p in links)))
    if unused:
        best_unused = float(max(logits[p] for p in unused))
        bucket['margin_unused_link_minus_rel'].append(best_unused - rel_logit)
        bucket['margin_rel_minus_best_unused_link'].append(rel_logit - best_unused)
    if len(unused) >= 2:
        pairs = [abs(float(logits[b]) - float(logits[a]))
                 for a, b in zip(unused, unused[1:])]
        bucket['adjacent_unused_link_abs'].extend(pairs)
    if gate is not None:
        bucket['gate'].append(gate)
    if conditions is not None:
        bucket['offset_category'][_offset_category(choice, conditions, links, rel)] += 1


def _offset_category(choice, condition, links, rel):
    """Probe C's step-2 reading: REL / NEXT / THIRD / other LINK / other, in that order."""
    if choice == rel:
        return 'REL'
    if choice == condition['next']:
        return 'NEXT'
    if choice == condition['third']:
        return 'THIRD'
    if choice in links:
        return 'OTHER_LINK'
    return 'OTHER'


def _finish_step_bucket(bucket):
    return dict(n_active=bucket['n_active'],
                op_category=dict(sorted(bucket['op_category'].items())),
                offset_category=dict(sorted(bucket['offset_category'].items())),
                subject_gold=bucket['subject_gold'],
                p_stop_median=median(bucket['p_stop']),
                p_stop_max=max(bucket['p_stop']) if bucket['p_stop'] else None,
                margin_unused_link_minus_rel_median=median(bucket['margin_unused_link_minus_rel']),
                margin_rel_minus_best_link_median=median(bucket['margin_rel_minus_best_link']),
                margin_rel_minus_best_unused_link_median=median(
                    bucket['margin_rel_minus_best_unused_link']),
                adjacent_unused_link_abs_median=median(bucket['adjacent_unused_link_abs']),
                gate_median=median(bucket['gate']))


# --------------------------------------------------------------------------- probe D


@torch.no_grad()
def geometry(model, panel):
    """Section 4 probe D: how far apart adjacent LINK positions sit in the encoder.

    `sep_trained` -- median ||ctx[LINK#1] - ctx[LINK#2]|| over the k3 units (the depth the
    v4 arms actually trained on).  `sep_long` -- median over the k8 units of the same
    distance for the adjacent pairs among LINK #3..#6.  Result slots carry zero context
    (`fable_dispatcher_v4.py:295-301`), so there is no result-position geometry to read.
    """
    if not model.flags().contextual_positions:
        return None

    def separations(cells, pairs_of):
        values = []
        per_cell = {}
        for cell in cells:
            units = panel[cell]
            questions = [unit['a']['question'] for unit in units]
            tokens, present = V1.pad_questions(questions)
            context = model.question_context(tokens, present)
            here = []
            for i, unit in enumerate(units):
                layout = question_layout(unit['a']['question'])
                for a, b in pairs_of(layout):
                    here.append(float(torch.linalg.vector_norm(context[i, b] - context[i, a])))
            per_cell[cell] = median(here)
            values.extend(here)
        return median(values), per_cell

    trained, trained_cells = separations(
        ('k3-prac', 'k3-held'), lambda layout: [(layout['links'][0], layout['links'][1])])
    long, long_cells = separations(
        ('k8-prac', 'k8-held'),
        lambda layout: [(layout['links'][i], layout['links'][i + 1]) for i in (2, 3, 4)])
    ratio = None if not trained else long / trained
    return dict(sep_trained=trained, sep_trained_per_cell=trained_cells,
                sep_long=long, sep_long_per_cell=long_cells, ratio=ratio,
                definition=dict(sep_trained='median ||ctx(LINK#1) - ctx(LINK#2)|| over k3 units',
                                sep_long='median ||ctx(LINK#i) - ctx(LINK#i+1)||, i = 3..5, '
                                         'over k8 units (adjacent pairs among LINK #3..#6)',
                                ratio='sep_long / sep_trained'))


# --------------------------------------------------------------------------- panel


def build_panel(out, force_cells=CELLS26, n=PANEL_N, dev=False):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    panel_path = out / 'panel.json'
    manifest_path = out / 'manifest.json'
    if panel_path.exists() or manifest_path.exists():
        raise SystemExit(f'refusing to overwrite an existing panel in {out}')
    off_spec = (int(n) != PANEL_N or tuple(force_cells) != CELLS26)
    if off_spec and not dev:                                   # audit M1
        raise SystemExit(f'section 3 fixes the panel at {PANEL_N} units in each of the cells '
                         f'{CELLS26}; got n={n} and cells={tuple(force_cells)}.  Every section-5 '
                         'threshold is an absolute count out of 64, so a smaller panel cannot be '
                         'read; pass --dev for a throwaway development panel that `probe` and '
                         '`report` will also refuse to treat as registered')
    spec_sha = sha(SPEC_PATH)
    if spec_sha != SPEC_SHA256:
        raise SystemExit(f'the specification at {SPEC_PATH} hashes to {spec_sha}, not the '
                         f'registered {SPEC_SHA256}; refusing to build a panel for it')
    started = time.monotonic()
    units = {}
    for cell in force_cells:
        made = []
        for index in range(n):
            unit = V4.throwaway_unit(cell, index, NAMESPACE)
            problems = V3.audit_unit(unit)
            if problems:
                raise SystemExit(f'{cell}:{index} failed its audit: {problems}')
            if unit['kind'] != 'single':
                raise SystemExit(f'{cell} is not a single-sided cell; probe 26 expects singles')
            made.append(unit)
        units[cell] = made
        print(json.dumps(dict(event='panel', cell=cell, n=len(made))), flush=True)
    write_new(panel_path, dict(namespace=NAMESPACE, n=n, cells=list(force_cells), units=units))
    found = code_hashes()
    checkpoints = {}
    for key, entry in CHECKPOINTS.items():
        path = Path(entry['path'])
        if not path.is_file():
            raise SystemExit(f'checkpoint missing: {path}')
        actual = sha(path)
        if actual != entry['sha256']:
            raise SystemExit(f'{path} hashes to {actual}, section 2 records {entry["sha256"]}')
        checkpoints[key] = dict(path=str(path), sha256=actual, family=entry['family'],
                                group=entry['group'], arm=entry['arm'], loader=entry['loader'],
                                seed=entry['seed'], verified_unix=time.time())
    operator_sha = sha(OPERATOR_PATH)
    if operator_sha != OPERATOR_SHA256:
        raise SystemExit(f'the frozen operator hashes to {operator_sha}, section 2 records '
                         f'{OPERATOR_SHA256}')
    manifest = dict(
        experiment='26 dispatcher fault-localisation probes',
        spec=str(SPEC_PATH), spec_sha256=spec_sha,
        namespace=NAMESPACE, cells=list(force_cells), n_per_cell=n, eval_cap=EVAL_CAP,
        block=BLOCK, probe_seed=PROBE_SEED,
        panel_sha256=sha(panel_path),
        panel_units=sum(len(v) for v in units.values()),
        code_sha256=found,
        code_sha256_at_design_time=DESIGN_CODE_SHA256,
        code_unchanged_since_design=all(found[k] == DESIGN_CODE_SHA256[k] for k in found),
        probe_source_sha256=source_sha256(),
        forecasts=forecast_hashes(),
        dev_panel=bool(off_spec),
        operator=dict(path=str(OPERATOR_PATH), sha256=operator_sha),
        checkpoints=checkpoints,
        thresholds=dict(R1=MARK_R1, R2=MARK_R2, R3=MARK_R3, R5=MARK_R5,
                        R7_ratio=MARK_R7_RATIO, R7_margin=MARK_R7_MARGIN),
        seconds=time.monotonic() - started, created_unix=time.time(),
        torch=torch.__version__, python=sys.version.split()[0],
        note=('throwaway units in a NEW namespace; never the v3 registered panels, the '
              'experiment-19 dev panels or any confirmation suite'))
    write_new(manifest_path, manifest)
    print(json.dumps(dict(event='panel-done', units=manifest['panel_units'],
                          panel_sha256=manifest['panel_sha256'],
                          seconds=round(manifest['seconds'], 1))), flush=True)
    return manifest


def load_panel(out, dev=False):
    out = Path(out)
    manifest = json.loads((out / 'manifest.json').read_text())
    running = source_sha256()
    if manifest.get('probe_source_sha256') != running:          # audit B1
        raise SystemExit(
            f'this script hashes to {running}; the manifest in {out} was written by '
            f'{manifest.get("probe_source_sha256")}.  Outputs from two versions of the probe '
            'must never be mixed: start a FRESH --out directory and rebuild the panel')
    if not dev:                                                 # audit M1
        if manifest.get('dev_panel'):
            raise SystemExit(f'{out} holds a development panel (built with --dev); it cannot be '
                             'read as a registered run')
        if manifest.get('n_per_cell') != PANEL_N:
            raise SystemExit(f'{out} has n_per_cell {manifest.get("n_per_cell")}, section 3 '
                             f'fixes {PANEL_N}')
        if tuple(manifest.get('cells') or ()) != CELLS26:
            raise SystemExit(f'{out} has cells {tuple(manifest.get("cells") or ())}, section 3 '
                             f'fixes {CELLS26}')
    panel_path = out / 'panel.json'
    actual = sha(panel_path)
    if actual != manifest['panel_sha256']:
        raise SystemExit(f'{panel_path} hashes to {actual}, the manifest records '
                         f'{manifest["panel_sha256"]}')
    payload = json.loads(panel_path.read_text())
    if payload['namespace'] != NAMESPACE:
        raise SystemExit(f'panel namespace {payload["namespace"]!r}, expected {NAMESPACE!r}')
    found = code_hashes()
    changed = {k: (manifest['code_sha256'][k], found[k]) for k in found
               if manifest['code_sha256'][k] != found[k]}
    if changed:
        raise SystemExit(f'imported code changed since the panel was built: {changed}')
    if sha(SPEC_PATH) != manifest['spec_sha256']:
        raise SystemExit('the specification changed since the panel was built')
    return manifest, payload['units']


# --------------------------------------------------------------------------- loading a checkpoint


def load_model(entry):
    """Verify the recorded sha256 BEFORE loading, then load with the family's own loader."""
    path = Path(entry['path'])
    actual = sha(path)
    if actual != entry['sha256']:
        raise SystemExit(f'{path} hashes to {actual}, section 2 records {entry["sha256"]}; '
                         'refusing to load it')
    detail = dict(path=str(path), sha256=actual, loader=entry['loader'])
    if entry['loader'] == 'v4':
        config, saved, model, flags = V4.load_checkpoint(path.parent)
        detail.update(arm=config.get('arm'), seed=config.get('seed'),
                      updates=config.get('updates'), train_cap=config.get('train_cap'),
                      train_hops=config.get('train_hops'), call_cost=config.get('call_cost'))
    else:
        saved, model, flags = TR.load_run_checkpoint(path, 'D')
        detail.update(arm=TR.D_ARM, seed=saved.get('seed'), updates=saved.get('updates_done'),
                      phase=saved.get('phase'), arm_label=saved.get('arm'),
                      train_cap=TR.D_TRAIN_CAP, call_cost=TR.D_CALL_COST,
                      verified_on_disk=saved.get('_verified_on_disk'))
    expected = V4.flags_for_arm(entry['arm'])
    if flags != expected or model.flags() != expected:
        raise SystemExit(f'{path}: flags {model.flags().as_dict()} do not match the family arm '
                         f'{entry["arm"]!r} ({expected.as_dict()})')
    model.eval()
    detail.update(parameters=model.parameters_count(), flags=flags.as_dict(),
                  weight_fingerprint=V1.fingerprint(model))
    return model, flags, detail


# --------------------------------------------------------------------------- the probe


@torch.no_grad()
def probe_checkpoint(entry, manifest, panel, out_path):
    if Path(out_path).exists():
        raise FileExistsError(f'refusing to overwrite an existing probe output: {out_path}')
    V1.configure()
    torch.manual_seed(PROBE_SEED)
    started = time.monotonic()
    model, flags, detail = load_model(entry)
    operator = TR.verified_operator()                 # hashes the frozen operator before loading
    oracle = V4.OracleOperator()
    operators = {'trained_operator': operator, 'oracle_operator': oracle}
    before = operator.fingerprint
    cap = EVAL_CAP
    learned_positions = bool(flags.contextual_positions)
    document = dict(
        checkpoint=entry['id'], family=entry['family'], group=entry['group'], arm=entry['arm'],
        seed=entry['seed'], checkpoint_detail=detail, flags=flags.as_dict(),
        learned_positions=learned_positions, eval_cap=cap, block=BLOCK,
        namespace=NAMESPACE, panel_sha256=manifest['panel_sha256'],
        spec_sha256=manifest['spec_sha256'], code_sha256=manifest['code_sha256'],
        probe_source_sha256=source_sha256(),
        forecasts=manifest.get('forecasts'),
        operator=dict(operator.describe(), fingerprint_before=before),
        evaluation='greedy (argmax) episodes; nothing is trained and nothing is sampled',
        claim_limit=('every number under probe_b and probe_c is a diagnostic of ONE component '
                     'with the others handed to it; a forced action is never an autonomous '
                     'success'),
        cells={})
    for cell in manifest['cells']:
        units = panel[cell]
        cfg = V3.CELLS[cell]
        hops = cfg['hops']
        tables = V3.TableCache(operators, block=BLOCK)
        cell_out = dict(hops=hops, people=cfg['people'], terminal=cfg['terminal'], n=len(units),
                        width=len(units[0]['a']['question']))
        hits = {'a': V3.operator_on_chains(operator, units, 'a', BLOCK)}
        # ---- probe A: free run, both operators
        free = {}
        for label in ('trained_operator', 'oracle_operator'):
            rows = V4.score_side_v4(model, operators[label], units, 'a', cap, flags, None,
                                    block=BLOCK,
                                    chain_hits=hits if label == 'trained_operator' else None,
                                    prepared=tables.get(label, cell, units, 'a'))
            free[label] = rows
        cell_out['probe_a'] = {label: summarise_rows(rows, units) for label, rows in free.items()}
        cell_out['probe_a']['agreement'] = dict(
            same_category=sum(int(a['category'] == b['category'])
                              for a, b in zip(classify_rows(free['trained_operator'], units),
                                              classify_rows(free['oracle_operator'], units))),
            n=len(units),
            note='the oracle run separates operator error from controller error')
        # ---- probe B: the five handed-component replays
        replays = {}
        for kind in V3.INTERVENTIONS:
            if kind == 'none':
                rows = free['trained_operator']
            else:
                factory = (lambda hop, width, _k=kind: V3.intervention_policy(_k, hop, width))
                rows = V4.score_side_v4(model, operator, units, 'a', cap, flags, factory,
                                        block=BLOCK,
                                        prepared=tables.get('trained_operator', cell, units, 'a'))
            summary = summarise_rows(rows, units)
            summary['forced'] = 'nothing' if kind == 'none' else \
                f'{kind} while step < hops ({hops}); STOP free unless the kind names it'
            replays[kind] = summary
        # native logits under the operation+subject replay
        factory = (lambda hop, width: V3.intervention_policy('force_operation+subject', hop, width))
        steps, forced_rows = native_steps(model, flags, units, cell,
                                          tables.get('trained_operator', cell, units, 'a'),
                                          cap, factory, max_step=cap - 1)
        native_summary = summarise_rows(forced_rows, units)
        for key in ('answers', 'strict'):
            if native_summary[key] != replays['force_operation+subject'][key]:
                raise SystemExit(f'{cell}: the recorded operation+subject run disagrees with '
                                 f'score_side_v4 on {key}')
        replays['force_operation+subject']['native_steps'] = steps
        cell_out['probe_b'] = replays
        # ---- probe C: offset start (k8 cells, learned-position arms only)
        if learned_positions and hops == 8:
            layout = question_layout(units[0]['a']['question'])
            conditions = offset_conditions(layout)
            offsets = {}
            for name, condition in conditions.items():
                condition = dict(condition, third=4)
                factory = (lambda hop, w, _c=condition:
                           offset_start_policy(_c['forced'][0], _c['forced'][1], w))
                steps_c, rows_c = native_steps(model, flags, units, cell,
                                               tables.get('trained_operator', cell, units, 'a'),
                                               cap, factory, max_step=2, conditions=condition)
                at_two = steps_c.get('2', _finish_step_bucket(_fresh_step_bucket()))
                offsets[name] = dict(
                    forced_positions=list(condition['forced']), next_position=condition['next'],
                    third_position=condition['third'], n_units=len(units),
                    reached_step_2=at_two['n_active'],
                    step2=at_two, steps=steps_c,
                    outcome=summarise_rows(rows_c, units),
                    note=('the two forced calls are legal friend look-ups, so the controller is '
                          'in a state it could have reached by its own choices; STOP is never '
                          'forced and nothing is patched by hand'))
            cell_out['probe_c'] = offsets
        document['cells'][cell] = cell_out
        trained = cell_out['probe_a']['trained_operator']
        print(json.dumps(dict(cell=cell, answers=trained['answers'], strict=trained['strict'],
                              op_subject_strict=cell_out['probe_b'][
                                  'force_operation+subject']['strict'],
                              op_only_strict=cell_out['probe_b']['force_operation']['strict'])),
              flush=True)
    document['probe_d'] = geometry(model, panel)
    assert operator.fingerprint == before, 'the frozen operator changed during the probe'
    document['operator_weights_unchanged'] = True
    document['seconds'] = time.monotonic() - started
    document['created_unix'] = time.time()
    write_new(out_path, document)
    print(json.dumps(dict(event='probe-done', checkpoint=entry['id'],
                          seconds=round(document['seconds'], 1), out=str(out_path))), flush=True)
    return document


def resolve_entry(text, family=None):
    if text in CHECKPOINTS:
        entry = CHECKPOINTS[text]
    else:
        path = Path(text).resolve()
        matches = [e for e in CHECKPOINTS.values() if Path(e['path']).resolve() == path]
        if not matches:
            raise SystemExit(f'{text} is not one of the section-2 checkpoints')
        entry = matches[0]
    if family is not None and entry['family'] != family:
        raise SystemExit(f'{entry["id"]} belongs to family {entry["family"]!r}, not {family!r}')
    return entry


def read_documents(folder, manifest):
    """Every probe output in `folder`, refusing any that a different version of this
    script wrote (audit B1) or that was produced against a different panel."""
    running = source_sha256()
    documents = {}
    for path in sorted(Path(folder).glob('probe-*.json')):
        doc = json.loads(path.read_text())
        if doc.get('probe_source_sha256') != running:
            raise SystemExit(
                f'{path} was written by probe source {doc.get("probe_source_sha256")}, but this '
                f'script hashes to {running}.  Outputs from two versions must never be mixed or '
                'skipped over: start a FRESH --out directory and re-run every checkpoint')
        if doc.get('panel_sha256') != manifest['panel_sha256']:
            raise SystemExit(f'{path} was produced against a different panel')
        documents[doc['checkpoint']] = doc
    return documents


def probe(args):
    out = Path(args.out)
    manifest, panel = load_panel(out, dev=getattr(args, 'dev', False))
    entry = resolve_entry(args.ckpt, args.family)
    folder = out / 'probes'
    folder.mkdir(parents=True, exist_ok=True)
    read_documents(folder, manifest)          # refuses a folder holding another version's work
    out_path = folder / f'probe-{entry["id"]}.json'
    if out_path.exists():
        print(json.dumps(dict(event='skip', checkpoint=entry['id'], reason='already probed',
                              out=str(out_path))), flush=True)
        return None
    return probe_checkpoint(entry, manifest, panel, out_path)


# --------------------------------------------------------------------------- report


def strict_of(document, cell, kind):
    return document['cells'][cell]['probe_b'][kind]['strict']


def category_of(document, cell, kind, name):
    return document['cells'][cell]['probe_b'][kind]['categories'].get(name, 0)


def r_flags(document):
    """Section 5, applied mechanically to one checkpoint.  No averaging, no judgement."""
    cells = document['cells']
    flags = {}
    depths = sorted({cells[c]['hops'] for c in cells})
    for d in depths:
        prac, held = f'k{d}-prac', f'k{d}-held'
        if prac not in cells or held not in cells:
            continue
        r1 = (strict_of(document, prac, 'force_operation+subject') >= MARK_R1
              and strict_of(document, held, 'force_operation+subject') >= MARK_R1)
        op_only = (strict_of(document, prac, 'force_operation') >= MARK_R3
                   and strict_of(document, held, 'force_operation') >= MARK_R3)
        flags[f'R1({d})'] = r1
        flags[f'R4({d})'] = bool((not op_only) and r1)
    flags['R2'] = (cells['k8-held']['probe_a']['trained_operator']['categories']['OP_EARLY_ATTR']
                   >= MARK_R2) if 'k8-held' in cells else None
    flags['R3'] = (strict_of(document, 'k8-prac', 'force_operation') >= MARK_R3
                   and strict_of(document, 'k8-held', 'force_operation') >= MARK_R3) \
        if 'k8-held' in cells else None
    early = [category_of(document, cell, 'force_operation+subject', 'STOP_EARLY')
             for cell in ('k4-held', 'k5-held') if cell in cells]
    flags['R5'] = bool(early and max(early) >= MARK_R5)
    probe_c = cells.get('k8-held', {}).get('probe_c')
    if probe_c:
        counts = probe_c['S3']['step2']['offset_category']
        flags['R6'] = counts.get('REL', 0) >= MARK_R2
        flags["R6'"] = (counts.get('NEXT', 0) + counts.get('THIRD', 0)
                        + counts.get('OTHER_LINK', 0)) >= MARK_R2
        adjacent = probe_c['S0']['step2']['adjacent_unused_link_abs_median']
    else:
        flags['R6'] = flags["R6'"] = None
        adjacent = None
    ratio = (document.get('probe_d') or {}).get('ratio')
    flags['R7'] = (bool(ratio is not None and adjacent is not None
                        and ratio <= MARK_R7_RATIO and adjacent <= MARK_R7_MARGIN)
                   if document['learned_positions'] else None)
    flags['_S3_counts'] = probe_c['S3']['step2']['offset_category'] if probe_c else None
    flags['_geometry_ratio'] = ratio
    flags['_adjacent_margin_S0'] = adjacent
    flags['_subject_only_k8_held_strict'] = strict_of(document, 'k8-held', 'force_subject') \
        if 'k8-held' in cells else None
    return flags


def family_holds(documents, flags, family, key, need=2, of=3):
    members = [k for k, d in documents.items() if d['family'] == family]
    held = [k for k in members if flags[k].get(key) is True]
    return dict(family=family, key=key, seeds=len(members), holds=len(held),
                members=sorted(members), held=sorted(held),
                verdict=bool(len(held) >= need and len(members) == of))


def positive_control(documents, flags):
    """Section 5: read FIRST; if it fails, nothing else is read."""
    control = {k: d for k, d in documents.items() if d['group'] == 'control'}
    clauses = []
    missing = [k for k in CONTROL_IDS if k not in control]
    complete = not missing
    r1_4 = [k for k in control if flags[k].get('R1(4)') is True]
    clauses.append(dict(name='R1(4) in 12/12 v4 checkpoints', need='12/12',
                        got=f'{len(r1_4)}/{len(control)}',
                        passed=bool(len(r1_4) == 12 and len(control) == 12)))
    learned = [k for k, d in control.items() if d['learned_positions']]
    r2 = [k for k in learned if flags[k].get('R2') is True]
    clauses.append(dict(name='R2 in >= 5 of the 6 learned-position v4 checkpoints', need='>=5/6',
                        got=f'{len(r2)}/{len(learned)}',
                        passed=bool(len(r2) >= 5 and len(learned) == 6)))
    ctx = [k for k, d in control.items() if d['family'] == 'v4-ctx']
    r3 = [k for k in ctx if flags[k].get('R3') is True]
    clauses.append(dict(name='R3 in 3/3 v4-ctx', need='3/3', got=f'{len(r3)}/{len(ctx)}',
                        passed=bool(len(r3) == 3 and len(ctx) == 3)))
    reg = [k for k, d in control.items() if d['family'] == 'v4-reg']
    subject_ok = [k for k in reg
                  if (flags[k].get('_subject_only_k8_held_strict') or 0) >= MARK_R3]
    clauses.append(dict(name='subject-only strict >= 59/64 on k8-held in >= 2 of 3 v4-reg',
                        need='>=2/3', got=f'{len(subject_ok)}/{len(reg)}',
                        passed=bool(len(subject_ok) >= 2 and len(reg) == 3)))
    return dict(complete=complete, missing=sorted(missing), clauses=clauses,
                passed=bool(complete and all(c['passed'] for c in clauses)))


def decision_rows(documents, flags, control):
    """Section 6, applied mechanically.  D0 short-circuits everything, and an incomplete
    registered set short-circuits the rest (audit B2): D1-D5 are statements about
    19-awake / 19b-U5 / 19b-U8 and cannot be read from checkpoints that were not probed."""
    if not control['passed']:
        return [dict(row='D0', fired=True,
                     meaning='the positive control failed or is incomplete: the probe script is '
                             'wrong',
                     next='fix the script; read nothing else')]
    missing = [k for k in REGISTERED_IDS if k not in documents]
    if missing:
        return [dict(row='-', fired=False, incomplete=True, missing=missing,
                     meaning=('registered set incomplete -- D1-D5 are NOT evaluable; missing '
                              + ', '.join(missing)),
                     next='probe the missing checkpoints, then re-run the report')]
    rows = []

    def fam(family, key, need=2):
        return family_holds(documents, flags, family, key, need=need)

    d1 = all(fam(f, k, need=3)['verdict'] for f in ('19-awake', '19b-U5', '19b-U8')
             for k in ('R1(4)', 'R1(5)')) and fam('19-awake', 'R2')['verdict']
    rows.append(dict(row='D1', fired=bool(d1),
                     meaning='same picture as v4: a healthy STOP behind an operation pointer '
                             'that asks the attribute early',
                     next='the stateless-STOP experiment stays VETOED; the one licensed '
                          'training experiment is 25b step 3, registered separately'))
    r5_awake = fam('19-awake', 'R5')['verdict']
    r5_u5 = fam('19b-U5', 'R5')['verdict']
    r5_u8 = fam('19b-U8', 'R5')['verdict']
    rows.append(dict(row='D2a', fired=bool(r5_awake),
                     meaning='a real premature STOP exists in the cap-8 family that v4 did not '
                             'have',
                     next='the stateless-STOP two-arm experiment becomes licensed for that '
                          'family only, with 25b Problem 3\'s code corrections'))
    rows.append(dict(row='D2b', fired=bool(r5_u8 and not r5_awake and not r5_u5),
                     meaning='long practice under a per-call cost damaged STOP itself',
                     next='STOP-head experiment still not licensed; licensed instead: one '
                          'cost-arm continuation (0.01 vs 0) with a padding plan'))
    d3 = fam('19b-U5', 'R4(6)')['verdict'] or fam('19b-U8', 'R4(6)')['verdict']
    rows.append(dict(row='D3', fired=bool(d3),
                     meaning='after practice pushes the operation pointer out, the '
                             'register/subject pointer is the limiter',
                     next='no further practice-length waves on reg+ctx; such work moves to ctx '
                          'or reg'))
    d4 = fam('v4-ctx', 'R6')['verdict']
    d4p = fam('v4-ctx', "R6'")['verdict']
    rows.append(dict(row='D4', fired=bool(d4),
                     meaning='"counts calls" is the accurate description',
                     next='the step-3 registration must forecast that a learner that counts may '
                          'ignore the new mark'))
    rows.append(dict(row="D4'", fired=bool(d4p),
                     meaning='"follows positions, loses them with depth" is the accurate '
                             'description',
                     next='read R7; if R7 also holds the position encoder is upstream'))
    fired = [r for r in rows if r['fired']]
    rows.append(dict(row='D5', fired=not fired,
                     meaning='no single account',
                     next='report per seed; no training experiment is licensed from this probe'))
    return rows


def _table(lines, title):
    return [title, '-' * len(title)] + lines + ['']


def report(args):
    out = Path(args.out)
    dev = getattr(args, 'dev', False)
    manifest, _panel = load_panel(out, dev=dev)
    folder = out / 'probes'
    documents = read_documents(folder, manifest)
    if not documents:
        raise SystemExit(f'no probe outputs in {folder}')
    suffix_name = args.suffix or ''
    control_only = (suffix_name == 'control')                       # audit B2
    present_control = [k for k in CONTROL_IDS if k in documents]
    present_registered = [k for k in REGISTERED_IDS if k in documents]
    missing_registered = [k for k in REGISTERED_IDS if k not in documents]
    if suffix_name == 'final':
        problems = []
        if len(present_control) != len(CONTROL_IDS):
            problems.append('positive control '
                            f'{len(present_control)}/{len(CONTROL_IDS)}: missing '
                            + ', '.join(k for k in CONTROL_IDS if k not in documents))
        if missing_registered:
            problems.append(f'registered {len(present_registered)}/{len(REGISTERED_IDS)}: missing '
                            + ', '.join(missing_registered))
        if problems:
            raise SystemExit('refusing to write a FINAL report from an incomplete run -- '
                             + '; '.join(problems)
                             + '.  Probe the missing checkpoints, or write an interim report '
                               'under a different --suffix.')
    flags = {k: r_flags(d) for k, d in documents.items()}
    control = positive_control(documents, flags)
    rows = [] if control_only else decision_rows(documents, flags, control)
    suffix = f'-{suffix_name}' if suffix_name else ''
    text_path = out / f'report{suffix}.txt'
    json_path = out / f'report{suffix}.json'
    forecasts = manifest.get('forecasts') or {}
    lines = []
    lines += _table([
        f'report kind        ' + ('CONTROL ONLY (no section-6 decision table)' if control_only
                                  else ('FINAL' if suffix_name == 'final' else 'interim'))
        + ('   [DEV PANEL -- NOT A REGISTERED RUN]' if dev or manifest.get('dev_panel') else ''),
        f'specification      {manifest["spec"]}',
        f'specification sha  {manifest["spec_sha256"]}',
        f'forecasts          {forecasts.get("predictions")}',
        f'forecasts sha      {forecasts.get("predictions_sha256")}  (matches its recorded '
        f'.sha256.txt: {forecasts.get("predictions_matches_its_record")})',
        f'ledger sha         {forecasts.get("ledger_sha256")}  ({forecasts.get("ledger")})',
        f'panel namespace    {manifest["namespace"]}  ({manifest["panel_units"]} units, '
        f'{manifest["n_per_cell"]}/cell)',
        f'panel sha256       {manifest["panel_sha256"]}',
        f'probe source sha   {source_sha256()}  (identical in the manifest and in every probe '
        'output, or this report would have refused to run)',
        f'eval cap           {manifest["eval_cap"]}   block {manifest["block"]}   '
        f'greedy, single thread',
        f'code unchanged     {manifest["code_unchanged_since_design"]}'
        + ('' if manifest['code_unchanged_since_design'] else
           '   <-- an imported module has drifted from section 2: THIS RUN IS VOID'),
        f'positive control   {len(present_control)} of {len(CONTROL_IDS)} probed',
        f'registered set     {len(present_registered)} of {len(REGISTERED_IDS)} probed'
        + ('' if not missing_registered else '   missing: ' + ', '.join(missing_registered)),
        f'checkpoints probed {len(documents)} of {len(CHECKPOINTS)} in the registry '
        '(the registry also holds the three optional 19-U checkpoints, which are NOT probed: '
        'the auditor loaded them and found their weights bit-identical to 19b-U5 at every seed)',
        'file names         the builder used fable_dispatcher_probes26.py / '
        'test_fable_dispatcher_probes26.py / artifacts/fable-dispatcher-probes26-20260921/ '
        'instead of the names in section 9 (coordinator-instructed; BUILD-NOTES section 2)',
    ], 'EXPERIMENT 26 -- dispatcher fault-localisation probes')
    verdict = 'PASSED' if control['passed'] else 'FAILED'
    body = [f'{c["name"]}: need {c["need"]}, got {c["got"]} -> '
            f'{"ok" if c["passed"] else "FAIL"}' for c in control['clauses']]
    if control['missing']:
        body.append(f'missing control checkpoints: {", ".join(control["missing"])}')
    lines += _table([f'VERDICT: {verdict}'] + body,
                    '1. POSITIVE CONTROL (read first; if it fails nothing else is read)')
    order = [k for k in CHECKPOINTS if k in documents]
    for key in order:
        doc = documents[key]
        head = (f'{key}   family {doc["family"]}   arm {doc["arm"]}   seed {doc["seed"]}   '
                f'{doc["checkpoint_detail"]["parameters"]} parameters')
        body = [head, f'  sha256 {doc["checkpoint_detail"]["sha256"]}', '',
                '  cell      free: ans/strict  op+subj  op-only  subj-only  stop-only  '
                'first-fault categories (free run)']
        for cell in manifest['cells']:
            row = doc['cells'][cell]
            free = row['probe_a']['trained_operator']
            b = row['probe_b']
            cats = ' '.join(f'{k}={v}' for k, v in sorted(free['categories'].items()) if v)
            body.append(f'  {cell:<9} {free["answers"]:>3}/{free["strict"]:<3}        '
                        f'{b["force_operation+subject"]["strict"]:>3}      '
                        f'{b["force_operation"]["strict"]:>3}      '
                        f'{b["force_subject"]["strict"]:>3}       '
                        f'{b["force_stop"]["strict"]:>3}       {cats}')
        oracle_flag = [cell for cell in manifest['cells']
                       if doc['cells'][cell]['probe_a']['trained_operator'][
                           'categories']['OPERATOR'] > 2]
        body.append(f'  OPERATOR category above 2/64 in: '
                    f'{", ".join(oracle_flag) if oracle_flag else "no cell"}')
        agree = {cell: doc['cells'][cell]['probe_a']['agreement'] for cell in manifest['cells']}
        worst = min(agree, key=lambda c: agree[c]['same_category'])
        body.append('  oracle/trained first-fault agreement (section 10): '
                    + ' '.join(f'{c}={agree[c]["same_category"]}/{agree[c]["n"]}'
                               for c in manifest['cells'])
                    + f'   worst cell {worst} '
                    f'{agree[worst]["same_category"]}/{agree[worst]["n"]}')
        if doc.get('probe_d'):
            d = doc['probe_d']
            body.append(f'  geometry: sep_trained {d["sep_trained"]:.4f}  sep_long '
                        f'{d["sep_long"]:.4f}  ratio {d["ratio"]:.4f}')
        c8 = doc['cells'].get('k8-held', {}).get('probe_c')
        if c8:
            for name in ('S0', 'S3', 'S5'):
                counts = c8[name]['step2']['offset_category']
                body.append(f'  probe C {name} (forced {c8[name]["forced_positions"]}, next '
                            f'{c8[name]["next_position"]}): reached step 2 '
                            f'{c8[name]["reached_step_2"]}/{c8[name]["n_units"]}, step-2 '
                            'operation argmax '
                            + ' '.join(f'{k}={v}' for k, v in sorted(counts.items())))
        marks = {k: v for k, v in flags[key].items() if not k.startswith('_')}
        body.append('  flags: ' + ' '.join(f'{k}={v}' for k, v in marks.items()))
        lines += _table(body, f'checkpoint {key}')
    lines += _table([
        'thresholds are exactly section 5; no number is averaged across seeds.',
        'R4(d) is read as: NOT (operation-only strict >= 59 on BOTH kd-prac and kd-held), with',
        'R1(d) holding.  Section 5 does not say which cell "operation-only strict < 59" is read',
        'on; this is the looser of the two readings and row D3 and forecast P106 turn on it.',
        'The per-cell operation-only numbers are in the tables above and in every probe JSON,',
        'so the stricter reading can be applied by hand without re-running anything.',
    ], '2. PER-CHECKPOINT TABLES (above)')
    if control_only:
        lines += _table([
            'This is a CONTROL-ONLY report.  The section-6 decision table is not evaluated here',
            'and no row of it is printed: those rows are statements about 19-awake, 19b-U5 and',
            '19b-U8, and this report was not asked to read them.  Read the positive control in',
            'section 1; if it passed, run the registered probes and write the final report.',
        ], '3. DECISION TABLE (not evaluated)')
    elif not control['passed']:
        lines += _table(['The positive control did not pass, so section 6 row D0 fires and the '
                         'flags above are NOT interpreted.  Fix the script and re-run.'],
                        '3. DECISION TABLE')
    elif missing_registered:
        lines += _table(
            ['The registered set is incomplete, so D1-D5 are NOT evaluable and no row of the',
             'section-6 table is printed.  Missing:']
            + [f'  {k}' for k in missing_registered]
            + ['', 'Probe those checkpoints and re-run the report.'],
            '3. DECISION TABLE (not evaluable)')
    else:
        body = []
        for family in ('19-awake', '19b-U5', '19b-U8', '19-U', 'v4-ctx', 'v4-reg-ctx', 'v4-reg',
                       'v4-v3-repro'):
            members = [k for k in documents if documents[k]['family'] == family]
            if not members:
                continue
            for keyname in ('R1(4)', 'R1(5)', 'R1(6)', 'R1(8)', 'R2', 'R3', 'R4(6)', 'R5', 'R6',
                            "R6'", 'R7'):
                held = [k for k in members if flags[k].get(keyname) is True]
                body.append(f'  {family:<12} {keyname:<7} holds in {len(held)}/{len(members)} '
                            f'seeds ({", ".join(sorted(held)) if held else "none"})')
            body.append('')
        lines += _table(body, '3. PER-FAMILY FLAG COUNTS (>= 2 of 3 = "holds for the family")')
        body = [f'{r["row"]:<4} {"FIRED" if r["fired"] else "-    "}  {r["meaning"]}'
                for r in rows]
        body.append('')
        for r in rows:
            if r['fired']:
                body.append(f'{r["row"]} -> {r["next"]}')
        lines += _table(body, '4. DECISION TABLE (section 6)')
    lines += _table([
        'A forced action is never an autonomous success: every probe-B and probe-C number is a',
        'diagnostic of one component with the others handed to it.  Probe C puts the controller',
        'in reachable but unpractised states; a reading needs agreement between the free-run',
        'fault type (probe A) and at least one intervention.  All of this is descriptive',
        'development evidence on throwaway units: it changes no registered result and licenses',
        'no claim about a system.  At most one training experiment can be licensed, and that',
        'needs its own registration, forecasts and hashes.',
        '',
        'Probe C: condition S5\'s "next position" IS the attribute position, so its NEXT bucket',
        'is 0 by construction and a REL majority at S5 is consistent with BOTH hypotheses.  S5',
        'must not be read as evidence for "counts calls"; R6/R6\' are defined on S3 only.',
        'The logits under probe B are the model\'s own, but they are native GIVEN THE HANDED',
        'PREFIX: the operation scores are computed with the forced subject already selected.',
    ], '5. CLAIM LIMITS (section 7)')
    text = '\n'.join(lines) + '\n'
    with text_path.open('x') as handle:
        handle.write(text)
    write_new(json_path, dict(manifest_sha256=sha(out / 'manifest.json'),
                              panel_sha256=manifest['panel_sha256'],
                              probe_source_sha256=source_sha256(),
                              forecasts=forecasts,
                              kind=('control' if control_only else
                                    ('final' if suffix_name == 'final' else 'interim')),
                              control_probed=present_control,
                              registered_probed=present_registered,
                              registered_missing=missing_registered,
                              decision_table_evaluated=bool(
                                  not control_only and control['passed'] and not missing_registered),
                              r4_reading='R4(d) = NOT (operation-only strict >= 59 on BOTH '
                                         'kd-prac and kd-held) AND R1(d)',
                              checkpoints=sorted(documents),
                              flags=flags, positive_control=control, decisions=rows,
                              thresholds=manifest['thresholds'], created_unix=time.time()))
    print(text, flush=True)
    return dict(control=control, decisions=rows, flags=flags,
                registered_missing=missing_registered, control_only=control_only)


# --------------------------------------------------------------------------- CLI


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)

    p = sub.add_parser('panel', help='build and freeze the 640-unit probe panel')
    p.add_argument('--out', required=True)
    p.add_argument('--n', type=int, default=PANEL_N)
    p.add_argument('--dev', action='store_true',
                   help='build a throwaway development panel of a size section 3 does not '
                        'allow; the panel is marked and every later command refuses it')

    p = sub.add_parser('probe', help='probe ONE checkpoint (resumable; never overwrites)')
    p.add_argument('--out', required=True)
    p.add_argument('--ckpt', required=True, help='a section-2 checkpoint id or its path')
    p.add_argument('--family', default=None, help='cross-check: the family that id belongs to')
    p.add_argument('--dev', action='store_true', help='allow a --dev panel (never registered)')

    p = sub.add_parser('report', help='apply the section-5 thresholds and section-6 table')
    p.add_argument('--out', required=True)
    p.add_argument('--dev', action='store_true', help='allow a --dev panel (never registered)')
    p.add_argument('--suffix', default=None, help='write report-<suffix>.txt instead')

    p = sub.add_parser('list', help='print the checkpoint registry')

    args = parser.parse_args(argv)
    if args.command == 'panel':
        V1.configure()
        build_panel(args.out, n=args.n, dev=args.dev)
    elif args.command == 'probe':
        probe(args)
    elif args.command == 'report':
        report(args)
    else:
        print(json.dumps({k: dict(family=v['family'], group=v['group'], arm=v['arm'],
                                  path=str(v['path']), sha256=v['sha256'])
                          for k, v in CHECKPOINTS.items()}, indent=2), flush=True)


if __name__ == '__main__':
    main()
