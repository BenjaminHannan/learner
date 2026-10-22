"""G11: blind paraphrase checklist sheet for the English pilot (secondary S1). Stdlib only.

Run only after the seal is verified (score_english_free_answer_v1.verify_seal).
Every paraphrase-task output of every state becomes one row with an opaque id;
rows are shuffled with a fixed seed. The sheet shows the passage, the required
propositions and the output, never the state, seed or arm. KEY.json (kept away
from the rater) maps opaque ids back to state and item. For each proposition the
rater marks kept / missing / reversed, and records added claims per output.
tally() joins the filled sheet with the key: an output passes S1 only if all
propositions are kept, none reversed, and no claims were added.
"""
import argparse
import hashlib
import json
from pathlib import Path
import random
import sys

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import english_pilot_common_v1 as common  # noqa: E402
import score_english_free_answer_v1 as scorer  # noqa: E402

SHEET_SCHEMA = 'premonition.English-pilot-blind-paraphrase-sheet.v1'
KEY_SCHEMA = 'premonition.English-pilot-blind-paraphrase-key.v1'
MARKS = ('kept', 'missing', 'reversed')
SHUFFLE_SALT = 'English-pilot-blind-paraphrase-sheet-v1'


def opaque_id(seal_sha, state, item_id):
    return 'R-' + hashlib.sha256(('%s|%s|%s|%s' % (SHUFFLE_SALT, seal_sha, state, item_id)).encode()).hexdigest()[:12]


def build_sheet(eval_dir, eval_items_path, frozen_sha256):
    seal, rows = scorer.verify_seal(eval_dir, frozen_sha256, eval_items_path)
    gold, passages, _ = scorer.load_gold(eval_items_path)
    seal_sha = common.digest(Path(eval_dir) / 'SEALED.json')
    entries, key = [], {}
    for state in scorer.STATES:
        for row in rows[state]:
            if row['panel'] != 'fresh':
                continue
            g = gold[row['item_id']]
            if g['task'] != 'paraphrase':
                continue
            rid = opaque_id(seal_sha, state, row['item_id'])
            entries.append({'row_id': rid, 'passage': passages[g['passage_id']]['passage'],
                            'required_propositions': [{'proposition': p, 'mark': None} for p in g['required_propositions']],
                            'output': row['output_text'], 'added_claims': None, 'rater_note': ''})
            key[rid] = {'state_id': state, 'item_id': row['item_id']}
    rng = random.Random(int(hashlib.sha256((SHUFFLE_SALT + seal_sha).encode()).hexdigest(), 16))
    rng.shuffle(entries)
    sheet = {'schema': SHEET_SCHEMA, 'instructions': (
        'For each row, mark every required proposition as kept, missing or reversed in the output, and set '
        'added_claims to the number of claims in the output that the passage does not state (0 if none). '
        'Do not guess which system wrote the output.'), 'marks': list(MARKS), 'rows': entries}
    return sheet, {'schema': KEY_SCHEMA, 'sealed_sha256': seal_sha, 'rows': key}


def tally(sheet, key):
    if sorted(r['row_id'] for r in sheet['rows']) != sorted(key['rows']):
        raise ValueError('sheet and key rows differ')
    per_state = {}
    for row in sheet['rows']:
        marks = [p['mark'] for p in row['required_propositions']]
        if any(m not in MARKS for m in marks) or type(row['added_claims']) is not int or row['added_claims'] < 0:
            raise ValueError('incomplete rating for ' + row['row_id'])
        state = key['rows'][row['row_id']]['state_id']
        s = per_state.setdefault(state, {'outputs': 0, 'all_kept_none_added_none_reversed': 0,
                                         'propositions': 0, 'kept': 0, 'missing': 0, 'reversed': 0, 'added_claims': 0})
        s['outputs'] += 1
        s['propositions'] += len(marks)
        for m in MARKS:
            s[m] += marks.count(m)
        s['added_claims'] += row['added_claims']
        s['all_kept_none_added_none_reversed'] += all(m == 'kept' for m in marks) and row['added_claims'] == 0
    return per_state


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='command', required=True)
    b = sub.add_parser('build')
    b.add_argument('--eval-dir', required=True)
    b.add_argument('--freeze', required=True)
    b.add_argument('--sheet-out', required=True)
    b.add_argument('--key-out', required=True)
    t = sub.add_parser('tally')
    t.add_argument('--sheet', required=True)
    t.add_argument('--key', required=True)
    args = ap.parse_args()
    if args.command == 'build':
        freeze_path = Path(args.freeze).resolve()
        freeze = common.read_json(freeze_path)
        sheet, key = build_sheet(args.eval_dir, freeze_path.parent / freeze['eval_items']['path'],
                                 freeze['eval_items']['sha256'])
        print(json.dumps({'sheet_sha256': common.write_new_json(args.sheet_out, sheet),
                          'key_sha256': common.write_new_json(args.key_out, key), 'rows': len(sheet['rows'])}))
    else:
        print(json.dumps(tally(common.read_json(args.sheet), common.read_json(args.key)), indent=1, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
