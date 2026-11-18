"""G10: mechanical free-answer scorer and section-7 verdict for the English pilot. Stdlib only.

Order (seal before gold): verify SEALED.json and every RAW file hash, verify
that the sealed fresh source hash equals the frozen eval hash and the bytes on
disk, and only then parse the gold-bearing eval file.

Scoring: NFC, lowercase, apostrophe normalization, trimmed surrounding quotes
and terminal punctuation, collapsed whitespace; correct only on exact equality
with the canonical answer or any accepted answer after normalization. No judge,
no hand override.

Measures per state: P1 = QA items in subset fresh_comprehension, P2 = QA items in
subset meaning_transfer (all items count; yes/no and two-option items are also
reported separately, per the freeze rules). Paraphrase-task items are never
scored here (blind sheet, G11). TRAIN fit = 48 TRAIN QA against the bank.
Verdict per protocol section 7: VOID / UNDERFIT-VOID / PASS / FAIL (prove-wrong)
/ HARM / NULL.
"""
import argparse
import json
import math
from pathlib import Path
import re
import sys
import unicodedata

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import english_pilot_common_v1 as common  # noqa: E402

# Same tuple as train_english_paraphrase_pilot_windows_v1.MATCHED_FIELDS (the per-arm 'arm' key is excluded).
MATCHED_FIELDS = ('parent_checkpoint_sha256', 'QA_frames_in_order_sha256', 'schedule_sha256',
                  'optimizer_sha256', 'RNG_sha256', 'code_sha256', 'initial_model_sha256')

SCHEMA = 'premonition.English-pilot-scores.v1'
SEAL_SCHEMA = 'premonition.English-pilot-sealed-outputs.v1'
STATES = ('seed0-parent', 'seed1-parent', 'seed0-control', 'seed0-treatment', 'seed1-control', 'seed1-treatment')
P1_SUBSET, P2_SUBSET = 'fresh_comprehension', 'meaning_transfer'
TRAIN_FIT_MIN = 40
APOSTROPHES = dict.fromkeys(map(ord, '‘’‛ʼ´`′'), "'")
QUOTES = dict.fromkeys(map(ord, '“”„‟″'), '"')
EDGE = '"\' \t\n'
TERMINAL = '.!?,;:'


def normalize(text):
    text = unicodedata.normalize('NFC', str(text)).lower().translate(APOSTROPHES).translate(QUOTES)
    text = re.sub(r'\s+', ' ', text).strip()
    previous = None
    while previous != text:
        previous = text
        text = text.strip(EDGE).rstrip(TERMINAL).strip()
    return text


def is_correct(output, canonical, accepted):
    answers = {normalize(a) for a in [canonical] + list(accepted)}
    answers.discard('')
    return normalize(output) in answers


def read_raw(path):
    return [json.loads(line) for line in Path(path).read_text(encoding='utf-8').splitlines() if line.strip()]


def verify_seal(eval_dir, frozen_sha256, eval_items_path):
    """Everything checkable without gold. Returns (seal, {state: rows}). Never opens gold."""
    eval_dir = Path(eval_dir)
    seal = common.read_json(eval_dir / 'SEALED.json')
    if seal.get('schema') != SEAL_SCHEMA or seal.get('gold_accessed') is not False \
            or seal.get('grading_metadata_opened') is not False:
        raise ValueError('V3: sealed-before-gold record required')
    if [s['state_id'] for s in seal['states']] != list(STATES) or sorted(seal['raw_files']) != sorted(STATES):
        raise ValueError('V3: exact six sealed states required')
    if seal.get('fresh_source_sha256') != frozen_sha256 or common.digest(eval_items_path) != frozen_sha256:
        raise ValueError('V3: fresh set hash differs from the frozen hash')
    rows = {}
    for state in STATES:
        pin = seal['raw_files'][state]
        path = eval_dir / pin['path']
        if common.digest(path) != pin['sha256']:
            raise ValueError('V3: raw output hash differs for ' + state)
        rows[state] = read_raw(path)
        if any(r.get('state_id') != state for r in rows[state]):
            raise ValueError('raw rows carry a different state id')
    fresh_sets = {state: sorted(r['item_id'] for r in rows[state] if r['panel'] == 'fresh') for state in STATES}
    if len({tuple(v) for v in fresh_sets.values()}) != 1 or len(set(fresh_sets[STATES[0]])) != len(fresh_sets[STATES[0]]):
        raise ValueError('every state must answer every fresh item exactly once')
    return seal, rows


def load_gold(eval_items_path):
    document = common.read_json(eval_items_path)
    gold = {g['item_id']: g for g in document['grading_metadata']}
    passages = {p['passage_id']: p for p in document['passages']}
    return gold, passages, document


def breakdown(results, predicate):
    chosen = [r for r in results if predicate(r)]
    return {'correct': sum(r['correct'] for r in chosen), 'N': len(chosen)}


def score_fresh(rows, gold):
    by_subset = {}
    items = []
    fresh_ids = {r['item_id'] for r in rows if r['panel'] == 'fresh'}
    qa_ids = {i for i, g in gold.items() if g['task'] == 'QA'}
    if not qa_ids <= fresh_ids:
        raise ValueError('a gold QA item has no sealed output')
    for row in rows:
        if row['panel'] != 'fresh' or row['item_id'] not in qa_ids:
            continue
        g = gold[row['item_id']]
        ok = bool(row.get('observation_valid')) and is_correct(row['output_text'], g['canonical_answer'],
                                                                g['accepted_answers'])
        items.append({'item_id': row['item_id'], 'subset': g['subset'], 'question_type': g.get('question_type'),
                      'yes_no': normalize(g['canonical_answer']) in ('yes', 'no'),
                      'two_option': g.get('two_option_choice') is True, 'correct': ok,
                      'observation_valid': bool(row.get('observation_valid')),
                      'normalized_output': normalize(row['output_text'])})
    for subset in (P1_SUBSET, P2_SUBSET):
        chosen = [r for r in items if r['subset'] == subset]
        by_subset[subset] = {
            'correct': sum(r['correct'] for r in chosen), 'N': len(chosen),
            'yes_no': breakdown(chosen, lambda r: r['yes_no']),
            'two_option': breakdown(chosen, lambda r: r['two_option']),
            'open_answer': breakdown(chosen, lambda r: not r['yes_no'] and not r['two_option']),
            'by_question_type': {str(t): breakdown(chosen, lambda r, t=t: r['question_type'] == t)
                                 for t in sorted({str(r['question_type']) for r in chosen})}}
    return by_subset, items


def score_train_fit(rows, bank):
    examples = bank['examples']
    results = []
    for row in rows:
        if row['panel'] != 'TRAIN' or row['frame_index'] % 4 not in (0, 1):
            continue
        p, q = divmod(row['frame_index'], 4)
        question = examples[p]['questions'][q]
        results.append(bool(row.get('observation_valid')) and is_correct(
            row['output_text'], question['canonical_answer'], question.get('accepted_answers', [])))
    if len(results) != 48:
        raise ValueError('TRAIN panel must hold exactly 48 QA generations')
    return {'correct': sum(results), 'N': 48}


def verdict(p, train_fit, v1_ok, v3_ok=True):
    """p[state][measure] = correct count; measures 'P1','P2' with N in p['N']."""
    n1, n2 = p['N']['P1'], p['N']['P2']
    if not v3_ok or not v1_ok:
        return {'verdict': 'VOID', 'reason': 'validity gate V1 or V3 failed'}
    underfit = [s for s in STATES[2:] if train_fit[s]['correct'] < TRAIN_FIT_MIN]
    if underfit:
        return {'verdict': 'UNDERFIT-VOID', 'underfit_states': underfit}
    t = {'P1': math.ceil(n1 / 8), 'P2': math.ceil(n2 / 8)}
    harm_limit = math.ceil(n1 / 16)
    d = {seed: {m: p['seed%d-treatment' % seed][m] - p['seed%d-control' % seed][m] for m in ('P1', 'P2')}
         for seed in (0, 1)}
    parent_loss = {s: p['seed%s-parent' % s[4]]['P1'] - p[s]['P1'] for s in STATES[2:]}
    detail = {'D': d, 'T': t, 'parent_harm_limit': harm_limit, 'P1_loss_vs_parent': parent_loss}
    if (all(d[s][m] >= t[m] for s in (0, 1) for m in ('P1', 'P2'))
            and all(loss <= harm_limit for loss in parent_loss.values())):
        return {'verdict': 'PASS', **detail}
    if all(d[s][m] <= 0 for s in (0, 1) for m in ('P1', 'P2')):
        harm = any(all(d[s][m] <= -t[m] for s in (0, 1)) for m in ('P1', 'P2'))
        return {'verdict': 'HARM' if harm else 'FAIL', **detail}
    if any(all(d[s][m] <= -t[m] for s in (0, 1)) for m in ('P1', 'P2')):
        return {'verdict': 'HARM', **detail}
    return {'verdict': 'NULL', **detail}


def check_runs(run_receipts):
    """V1 from the four CLOSED.json run receipts (None -> gate not established)."""
    if run_receipts is None:
        return False, 'run receipts not supplied'
    seen = set()
    for r in run_receipts:
        if not (r.get('closed') is True and r.get('optimizer_updates') == 2304 and r.get('cap_violations') == 0
                and r.get('finite_loss_all_updates') is True and r.get('gradient_contract_failures') == 0):
            return False, 'run %s/%s not a clean 2304-update close' % (r.get('seed'), r.get('arm'))
        seen.add((r.get('seed'), r.get('arm')))
    if seen != {(0, 'control'), (0, 'treatment'), (1, 'control'), (1, 'treatment')}:
        return False, 'four run receipts required'
    for seed in (0, 1):
        a = [{k: r['matched'].get(k) for k in MATCHED_FIELDS} for r in run_receipts if r['seed'] == seed]
        if a[0] != a[1]:
            return False, 'matched asserts differ for seed %d' % seed
    return True, 'ok'


def score(eval_dir, eval_items_path, frozen_sha256, bank, run_receipts=None):
    seal, rows = verify_seal(eval_dir, frozen_sha256, eval_items_path)
    gold, _passages, _doc = load_gold(eval_items_path)  # only after the seal is verified
    per_state, items, train_fit = {}, {}, {}
    for state in STATES:
        per_state[state], items[state] = score_fresh(rows[state], gold)
        train_fit[state] = score_train_fit(rows[state], bank)
    p = {s: {'P1': per_state[s][P1_SUBSET]['correct'], 'P2': per_state[s][P2_SUBSET]['correct']} for s in STATES}
    p['N'] = {'P1': per_state[STATES[0]][P1_SUBSET]['N'], 'P2': per_state[STATES[0]][P2_SUBSET]['N']}
    v1_ok, v1_reason = check_runs(run_receipts)
    result = verdict(p, train_fit, v1_ok)
    return {'schema': SCHEMA, 'sealed_sha256': common.digest(Path(eval_dir) / 'SEALED.json'),
            'frozen_eval_sha256': frozen_sha256, 'V1': {'passed': v1_ok, 'reason': v1_reason},
            'V3': {'passed': True}, 'TRAIN_fit': train_fit, 'primaries': p, 'per_state': per_state,
            'items': items, **result}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--eval-dir', required=True)
    ap.add_argument('--freeze', required=True, help='FRESH-EVAL-FREEZE-v1.json')
    ap.add_argument('--bank', required=True)
    ap.add_argument('--run-closed', action='append', help='CLOSED.json of each of the four runs')
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    freeze_path = Path(args.freeze).resolve()
    freeze = common.read_json(freeze_path)
    eval_items = freeze_path.parent / freeze['eval_items']['path']
    receipts = [common.read_json(p) for p in args.run_closed] if args.run_closed else None
    record = score(args.eval_dir, eval_items, freeze['eval_items']['sha256'], common.read_json(args.bank), receipts)
    record['freeze_sha256'] = common.digest(freeze_path)
    sha = common.write_new_json(args.out, record)
    print(json.dumps({'verdict': record['verdict'], 'scores_sha256': sha}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
