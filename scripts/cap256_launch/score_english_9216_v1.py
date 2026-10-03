"""Exploratory rescore of the 9216-update endpoints: stock scorer, run check changed 2304 -> 9216 only."""
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import english_pilot_common_v1 as common  # noqa: E402
import score_english_free_answer_v1 as sc  # noqa: E402


def check_runs_9216(receipts):
    seen = set()
    for r in receipts:
        if not (r.get('closed') is True and r.get('optimizer_updates') == 9216 and r.get('cap_violations') == 0
                and r.get('finite_loss_all_updates') is True and r.get('gradient_contract_failures') == 0):
            return False, 'run %s/%s not a clean 9216-update close' % (r.get('seed'), r.get('arm'))
        seen.add((r.get('seed'), r.get('arm')))
    if seen != {(0, 'control'), (0, 'treatment'), (1, 'control'), (1, 'treatment')}:
        return False, 'four run receipts required'
    for seed in (0, 1):
        a = [{k: r['matched'].get(k) for k in sc.MATCHED_FIELDS} for r in receipts if r['seed'] == seed]
        if a[0] != a[1]:
            return False, 'matched asserts differ for seed %d' % seed
    return True, 'ok'


sc.check_runs = check_runs_9216
root, out = Path(sys.argv[1]), sys.argv[2]
RES = sys.argv[4] if len(sys.argv) > 4 else 'RESULTS-v2-9216'
freeze = common.read_json(root / 'FRESH-EVAL-FREEZE-v1.json')
bank = common.read_json(sys.argv[3])
receipts = [common.read_json(root / RES / 'closed' / ('seed%d-%s.json' % (s, a)))
            for s in (0, 1) for a in ('control', 'treatment')]
rec = sc.score(root / RES / 'eval', root / freeze['eval_items']['path'], freeze['eval_items']['sha256'], bank, receipts)
rec['freeze_sha256'] = common.digest(root / 'FRESH-EVAL-FREEZE-v1.json')
print(json.dumps({'verdict': rec['verdict'], 'sha': common.write_new_json(out, rec)}))
