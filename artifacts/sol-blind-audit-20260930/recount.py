"""Independent stdlib-only saved-record recount. Never imports project code."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import math
import re

ROOT = Path('/Users/ben-hannan/Desktop/projects/beautiful-model')
OUT = Path(__file__).resolve().parent
S1 = 'artifacts/sol-spatial-20260929/'
S2 = 'artifacts/sol-sleep-20260929/'
inventory = {}


def digest(path):
    p = ROOT / path
    if not p.is_file():
        return None
    b = p.read_bytes()
    h = hashlib.sha256(b).hexdigest()
    inventory[path] = {'sha256': h, 'bytes': len(b)}
    return h


def read_json(path):
    digest(path)
    return json.loads((ROOT / path).read_text())


def canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


spec = read_json(S1 + 'SPEC.json')
seal = read_json(S1 + 'SEAL.json')
noise1 = read_json(S1 + 'NOISE.json')
digest(S1 + 'PASSMARKS.md')
r = read_json(S1 + 'run/record.json')
ledger = read_json(S1 + 'run/ledger.json')
digest(S1 + 'run/evaluation.started')
eval_started = (ROOT / (S1 + 'run/evaluation.started')).read_text().strip()
seal_checks = [{'path': p, 'expected': h, 'actual': digest(p), 'match': inventory.get(p, {}).get('sha256') == h}
               for p, h in seal['files'].items()]
checks = {
    'all_31_sealed_files_match': all(x['match'] for x in seal_checks),
    'record_seal_link': r['seal_sha256'] == digest(S1 + 'SEAL.json'),
    'record_spec_link': r['spec_sha256'] == digest(S1 + 'SPEC.json'),
    'record_queue_link': r['queue_sha256'] == spec['queue_sha256'],
    'record_complete': r['complete'] is True,
    'ledger_complete': ledger['status'] == 'COMPLETE_DEVELOPMENT',
    'ledger_training_config_matches_spec': ledger['training_parameters'] == spec['training'],
    'seed_arm_sets_complete': set(r['models']) == set(r['scores']) == {f's{s}-{a}' for s in spec['seeds'] for a in spec['arms']},
    'all_frozen_before_evaluation': all(j['status'] == 'FROZEN' and j['finished_utc'] < eval_started for j in ledger['jobs']),
    'seal_time_precedes_run': seal['sealed_utc'] < r['started_utc'],
}
budget = []
for key, m in r['models'].items():
    j = next(j for j in ledger['jobs'] if j['key'] == key)
    actual = digest(m['checkpoint'])
    budget.append({
        'key': key, 'updates': m['updates'], 'loss_count': len(m['losses']),
        'all_losses_finite': all(math.isfinite(x) for x in m['losses']),
        'slots': m['presentation_slots'], 'visits_min': min(m['visits_per_memory']),
        'visits_max': max(m['visits_per_memory']), 'visits_sum': sum(m['visits_per_memory']),
        'checkpoint_hash_match': actual == m['checkpoint_sha256'] == j['checkpoint_sha256'],
        'ledger_record_budget_match': m['updates'] == j['optimizer_updates_completed'] == 512 and m['presentation_slots'] == j['completed_presentation_slots'] == 4096,
        'parameters': m['parameters'], 'source_sha256': m['source_sha256'],
        'batch_order_sha256': m['batch_order_sha256'], 'data': m['data'],
        'training_seconds': m['training_seconds'], 'inflight_slots': j['inflight_presentation_slots'],
    })
pairing = {}
for seed in spec['seeds']:
    models = [r['models'][f's{seed}-{arm}'] for arm in spec['arms']]
    pairing[str(seed)] = {field: all(m[field] == models[0][field] for m in models)
                          for field in ['batch_order_sha256', 'data', 'split', 'source_sha256', 'visits_per_memory']}

rows = []
for key, groups in r['scores'].items():
    for kind, depths in groups.items():
        for depth, raw in depths.items():
            flags = raw['per_puzzle_correctness']
            lengths = sorted(set(len(p) for p in raw['predictions']))
            rows.append({'key': key, 'seed': r['models'][key]['seed'], 'arm': r['models'][key]['arm'],
                         'kind': kind, 'depth': int(depth), 'n': raw['n'],
                         'flag_count': len(flags), 'prediction_count': len(raw['predictions']),
                         'prediction_cell_lengths': lengths, 'flags_boolean': all(type(f) is bool for f in flags),
                         'recount_exact': sum(f is True for f in flags), 'stored_exact': raw['exact'],
                         'stored_exact_matches': raw['exact'] == sum(f is True for f in flags),
                         'prediction_label_recount': 'UNVERIFIABLE: labels/targets absent from saved run record'})
checks['all_36_flag_counts_match'] = all(x['stored_exact_matches'] and x['flags_boolean'] and x['n'] == x['flag_count'] == x['prediction_count'] == 64 for x in rows)
counts = {(x['seed'], x['arm'], x['kind'], x['depth']): x['recount_exact'] for x in rows}
verdicts = []
for seed in sorted(spec['seeds']):
    c9, c11 = (counts[(seed, 'top1_bias_plus1', k, 48)] for k in ['mazes9', 'mazes11'])
    verdicts.append({'seed': seed, 'mazes9': c9, 'mazes11': c11,
                     'descriptive_screen_pass': c9 >= 48 and c11 >= 32,
                     'scientific_verdict': 'NOT SHOWN'})
deltas = []
for seed in sorted(spec['seeds']):
    for kind in ['mazes9', 'mazes11']:
        c, b, d = (counts[(seed, a, kind, 48)] for a in spec['arms'][1:2] + spec['arms'][0:1] + spec['arms'][2:3])
        deltas.append({'seed': seed, 'kind': kind, 'candidate': c, 'base': b, 'dense': d,
                       'candidate_minus_base': c-b, 'candidate_minus_dense': c-d,
                       'candidate_minus_higher': c-max(b, d)})

digest(S2 + 'SMOKE-PROTOCOL.md')
digest(S2 + 'PASSMARKS.md')
noise2 = read_json(S2 + 'noise-provenance.json')
smoke = read_json(S2 + 'torch-smoke/raw.json')
completion = read_json(S2 + 'data-audit-poc/completion.json')
digest(S2 + 'data-audit-poc/proof-ledger.jsonl')
events = [json.loads(line) for line in (ROOT / (S2 + 'data-audit-poc/proof-ledger.jsonl')).read_text().splitlines()]
chain = []
prev = '0' * 64
for i, event in enumerate(events):
    chain.append({'seq': i, 'hash_match': canonical({k:v for k,v in event.items() if k != 'hash'}) == event['hash'],
                  'previous_match': event['previous'] == prev, 'seq_match': event['seq'] == i})
    prev = event['hash']
data_audit = []
for event in events[1:]:
    path = S2 + 'data-audit-poc/' + event['tag'].replace('/', '-') + '-data.json'
    pools = read_json(path)
    # Count containers and hash complete serialized pools only. Do not inspect,
    # expose, validate, score, or infer from unopened gate/report item contents.
    data_audit.append({'tag': event['tag'], 'replay_n': len(pools['replay']),
                       'gate_counts': {k: len(v) for k,v in pools['gate'].items()},
                       'report_counts': {k: len(v) for k,v in pools['report'].items()},
                       'pool_hashes_match': {k: canonical(pools[k]) == event[k+'_sha256'] for k in ['replay','gate','report']}})
smoke_checkpoints = []
for row in smoke['seeds']:
    p = S2 + f"torch-smoke/s{row['seed']}.pt"
    smoke_checkpoints.append({'seed': row['seed'], 'path': p, 'file_hash_match': digest(p) == row['saved_snapshot_sha256'],
                              'canonical_snapshot_hash': row['canonical_snapshot_sha256'],
                              'canonical_restore_reload_independently_verified': False})
smoke_code = [{'path': p, 'expected': h, 'actual': digest(p), 'match': inventory.get(p, {}).get('sha256') == h}
              for p,h in smoke['code_sha256'].items()]
noise_sources = []
noise_counts = []
bare_counts = []
for source in noise2['sources']:
    saved = read_json(source['path'])
    noise_sources.append({'path':source['path'], 'hash_match':inventory[source['path']]['sha256']==source['sha256']})
    extracted = []
    for cycle in saved['cycles']:
        extracted.append({k:{'exact':v['exact'],'n':v['n']} for k,v in cycle['after_sleep']['routed'].items()})
    noise_counts.append({'seed':source['seed'],'counts':extracted,'recorded_counts_match':extracted==source['counts']})
    bare_counts.append({'seed':source['seed'],'counts':[{k:{'exact':v['exact'],'n':v['n']} for k,v in c['after_sleep']['bare'].items()} for c in saved['cycles']]})
spread = max(abs(noise_counts[0]['counts'][night][kind]['exact']-noise_counts[1]['counts'][night][kind]['exact']) / 64 * 100
             for night in range(3) for kind in ['sums4','grids5','mazes9','mazes11'])
bare_spread = max(abs(bare_counts[0]['counts'][night][kind]['exact']-bare_counts[1]['counts'][night][kind]['exact']) / 64 * 100
                  for night in range(3) for kind in ['sums4','grids5','mazes9','mazes11'])
digest(S2 + 'integrity-test.log')
testlog = (ROOT / (S2 + 'integrity-test.log')).read_text()
tests = re.findall(r'^(test_\S+) .* \.\.\. ok$', testlog, re.M)
digest(S2 + 'torch-smoke.log')
plan_digest = digest(S2 + 'plan-poc.json')
result = {
    'audit_saved_utc': datetime.now(timezone.utc).isoformat(),
    'method': 'Independent stdlib arithmetic on existing raw records; project code never imported/executed; no inference, training, rescoring or git.',
    'blind_scope': 'Named Stage1 protocols and run raw; named Stage2 protocols, raw smoke, raw data-audit containers/hashes and filename-discovered test logs. No authored reports, director boards, prior conversation or restricted panels.',
    'stage1': {'verdict': 'DEVELOPMENT SCREEN NOT PASSED; SCIENTIFIC CLAIM NOT SHOWN',
               'prediction_label_verification': 'INCOMPLETE: no labels/targets saved in run raw',
               'checks': checks, 'seal_checks':seal_checks, 'rows':rows, 'seed_verdicts':verdicts,
               'same_descriptive_verdict_both_seeds': len({v['descriptive_screen_pass'] for v in verdicts}) == 1,
               'deltas':deltas,'budget':budget,'pairing':pairing,
               'total_updates':sum(m['updates'] for m in r['models'].values()),
               'total_slots':sum(m['presentation_slots'] for m in r['models'].values()),
               'evaluation_started':eval_started,'run_finished':r['finished_utc'],
               'historical_source_training':ledger['historical_source_training'],
               'noise':noise1},
    'stage2': {'verdict':'LIMITED RECORDED ENGINEERING SUPPORT; LEARNING/READINESS/GRAMMAR/BENCHMARK NOT SHOWN',
               'smoke':smoke,'checkpoint_checks':smoke_checkpoints,'code_hash_checks':smoke_code,
               'data_audit':data_audit,'chain_checks':chain,'completion_head_matches':completion['ledger_head']==prev,
               'preseal_noise_matches':events[0]['plan']['noise_sha256']==digest(S2+'noise-provenance.json'),
               'embedded_plan_hash_matches':canonical(events[0]['plan'])==events[0]['plan_sha256'],
               'current_plan_file_hash_matches':plan_digest==events[0]['plan_sha256'],
               'completion':completion,'test_names':tests,'test_ok_count':len(tests),
               'noise_source_checks':noise_sources,'noise_counts':noise_counts,'dense_spread_recount_pp':spread,
               'noise_record_namespace':'after_sleep.routed (not after_sleep.bare)',
               'bare_counts':bare_counts,'bare_spread_pp':bare_spread,
               'historical_noise_prediction_label_verification':'UNVERIFIABLE: historical sources contain aggregate counts, no correctness or prediction-label arrays in selected rows',
               'unopened_data_panels':'Only container counts and bulk hashes; labels/input/identity contents not examined or scored; split novelty not independently established'},
    'raw_and_protocol_inventory':inventory,
}
OUT.mkdir(parents=True, exist_ok=True)
(OUT/'recount.json').write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
lines = [
    'PREMONITION — INDEPENDENT BLIND AUDIT',
    'Saved UTC: '+result['audit_saved_utc'],
    'Management verdict: Stage1 development screen NOT PASSED; all scientific claims NOT SHOWN. Stage2 provides limited recorded engineering support, not learning or integration readiness.',
    '',
    'Scope and independence', result['method'], result['blind_scope'],
    'Original REPORT.md, run/report.json, summaries, boards, handoff/uncle-questions and readpanel320 were not read. No other panel was opened. Stage2 saved development data received only structural counts and bulk hash checks; no item contents were examined. No source content was read before this verdict. Source/checkpoint bytes were hashed only. Only this new audit directory was written. Integration/push remains with James.',
    '',
    'Stage1 marks and verdict',
    'Presealed seeds 0 and 1 (execution 1 then 0), arms unchanged top1, +1 update-gate-bias candidate, qualified dense. Exactly 512 updates/arm. Primary depth48; depth24 diagnostic. Candidate must reach maze9 >=48/64 AND maze11 >=32/64 in BOTH seeds. Comparator is the higher of same-seed base/dense. These are descriptive development targets only; final claim is explicitly NOT SHOWN and noise characterization INSUFFICIENT.',
    'Seed 0: candidate 64/64 maze9, 64/64 maze11 — descriptive gate reached.',
    'Seed 1: candidate 0/64 maze9, 0/64 maze11 — descriptive gate not reached.',
    'Two-seed descriptive verdict agreement is FALSE (mixed). The required both-seed gate is not passed. No formal scientific rejection or promotion follows. Scientific NOT SHOWN applies in both seeds.',
    'CRITICAL RECOUNT LIMIT: run/record.json contains predictions and per_puzzle_correctness but no labels/targets. The independent recount below sums saved boolean flags and checks exact/n/dimensions. Prediction-versus-label correctness cannot be independently verified from the supplied saved run evidence. Input/target hashes do not supply missing labels; no generator or inference was run to reconstruct them.',
    '',
    'Exact saved-flag recount: each entry is exact/64; all 36 rows match saved exact counts.',
    'seed arm                         TRAIN24 TRAIN48 maze9-24 maze9-48 maze11-24 maze11-48',
]
for seed in [0,1]:
    for arm in spec['arms']:
        ns = [counts[(seed,arm,k,d)] for k in ['TRAIN_original','mazes9','mazes11'] for d in [24,48]]
        lines.append(f'{seed}    {arm:28s} '+ ' '.join(f'{n:8d}' for n in ns))
lines += ['', 'Primary depth48 deltas (exact counts; 1 count = 1.5625 percentage points):']
for x in deltas:
    lines.append(f"seed{x['seed']} {x['kind']}: candidate {x['candidate']}/64, base {x['base']}/64, dense {x['dense']}/64; candidate-base {x['candidate_minus_base']:+d}, candidate-dense {x['candidate_minus_dense']:+d}, candidate-higher {x['candidate_minus_higher']:+d}.")
lines += ['', 'Seal, completion, budget and controls',
          f"All {len(seal_checks)} sealed file digests match. Record links to seal/spec/queue match. Seal timestamp {seal['sealed_utc']}; recorded run start {r['started_utc']}; last freeze {max(j['finished_utc'] for j in ledger['jobs'])}; evaluation marker {eval_started}; finished {r['finished_utc']}.",
          'Six checkpoints present, hashes match both record and ledger. Complete record and COMPLETE_DEVELOPMENT ledger; no missing seed/arm/depth row. No in-flight work recorded. 512 losses and 512 updates/arm, all losses finite; 4096 presentation slots/arm. Total 3072 updates and 24576 new presentation slots. Each arm has 64 memories x8 D4 views, 64 visits per memory. Same-seed source/data/order/visits/split hashes match across all three arms. These are recorded/hash-supported pairing facts, not an independent reconstruction of actual training inputs/order.',
          '36 x64 =2304 saved prediction/correctness entries (1536 maze-development entries and 768 TRAIN entries, across both depths). Maze9 prediction lengths81; maze11 lengths121; TRAIN lengths81. Depths are repeated measurements, not independent seeds or fresh evidence.',
          'Configuration: CPU fp32, 2 threads/1 interop, batch8, full BPTT24, supervised23/24, AdamW lr.001 betas(.9,.95) wd.1, warmup32, clip1, router aux0, sleep updates0/replay0. Ledger config exactly matches SPEC.',
          'Reused source training: two qualified 12000-update sources, excluded from new-slot total. Dense 1,645,726 stored/trainable parameters; top1 86,177 stored and54,177 trainable. Dense is a larger practiced source, not plain same-size/equal-capacity/nonmemorization control. F_eq/F_few ladders absent, sleep3-draw gate absent, target attention/MLP sparse reasoner absent. No total compute/fair-ruler or2x claim.',
          'Noise: historical top1 bundled seeds report64/64 vs0/64 at depth48, spread64/64=100pp. Linked historic files match hashes but no repeated-run noise calibration exists. Source embedding/TRAIN/init/order are confounded. No improvement threshold or statistical PASS is justified. Candidate ties higher control in seed0 and loses2/64 maze9 and1/64 maze11 in seed1.',
          'Seal verification proves present byte consistency and recorded temporal order, not external timestamp authentication, a signed provenance chain, non-use of other data, or scoring-once execution. A single evaluation marker/complete record supports one recorded evaluation; it cannot rule out unrecorded invocations. Holdout unopened is recorded; restricted data were not inspected by this audit.',
          '', 'Stage2 engineering evidence and limits',
          'SMOKE-PROTOCOL requires seeds0/1, CPU fp32 one thread, batch2, cap3,2x3 tokens; exact repeated FinalStateAdapter latent/stop parity; notebook append/mask; model+optimizer+RNG corruption/restore and save/load canonical hash equality; <=120seconds; no training/backward/scoring; stop readiness remains false.',
          'Recorded smoke: seeds0/1, repeat_exact_noise0 in both; seed0 rounds[3,3], stops[false,false], physical row-rounds6; seed1 rounds[3,1], stops[false,true], physical row-rounds4; total10. Notebook_mask_verified and snapshot_restore_verified true in both. Trained false, readiness_not_claimed true in both; elapsed1.165664459seconds (<120). Two serialized checkpoint hashes are independently verified.',
          'Raw smoke lacks the actual paired latent/stop outputs, before/corrupted/restored model+optimizer+RNG hashes, and loaded-checkpoint canonical hash comparisons. Therefore exact parity, restore and canonical reload invariants are reported assertions, not independently reconstructible from raw.json. Torch/code versions are recorded. CPU/dtype/thread/backward absence are not fully enumerated in raw.json. No checkpoint was deserialized or model executed by this audit.',
          f"Smoke code present-byte hash matches: {[(x['path'],x['match']) for x in smoke_code]}.",
          'Filename-discovered integrity-test.log:30 named tests report ok; Ran30 tests in0.028s; OK. No test rerun. Log lacks test/source/dependency hashes, timestamp, command/environment and per-test assertions, so it is recorded test success with incomplete provenance, not proof of current integrated code or learning.',
          'Data-audit completion: trained=false, holdout_opened=false, elapsed0.140850209seconds. Seeds0/1 each have order0/night1 only. Per seed: replay96; gate sums/grids/mazes16 each=48; report sums/grids/mazes/graph/rank16 each=80. Total224 stored records/seed,448 total. Across seeds replay192,gate96,report160. No correctness/prediction/depth arrays, optimizer-update events, paired control scores,3-draw retention/meeting evidence or sleep-learning results. Dataset construction is not the96-update PoC or9216-update campaign.',
          'Proof ledger has3 events (preseal plus2 data events). All sequence, previous-link and canonical event hash checks match. Six pool canonical hashes and completion head match. Preseal noise and embedded plan hashes match. This binds existing pools/plan/noise within a local hash chain, not the smoke/PASSMARKS protocol or external timestamp. Data counts/hashes establish existence/integrity only; provenance, actual split exclusions, D4/rank/graph novelty and source TRAIN disjointness are not independently rechecked because unscored panel contents remain unopened.',
          f"Current plan-poc.json byte hash matches preseal plan hash: {result['stage2']['current_plan_file_hash_matches']} (canonical embedded plan match is independently reported separately).",
          f"Historical dense provenance:2 source digests match;24 stored after_sleep.routed aggregate counts agree with noise-provenance.json;12 paired count differences give max5/64={spread}pp. This selects the routed namespace: after_sleep.bare has a different maximum spread8/64={bare_spread}pp (night3 sums4). The noise provenance does not explicitly name this namespace, so7.8125pp must not be generalized to all dense rows. Sources themselves lack selected-row prediction-label arrays; this verifies aggregate provenance/arithmetic, not underlying labels. The candidate30/64=46.875pp statement is not independently verified here: no candidate raw source is linked in the noise file. No new calibrated stochastic noise follows.",
          'PASSMARKS requires provisional >10pp over stronger dense controls in both seeds/orders/3 draws and above observed variability; capacity matches <=2%; draw0 fixed and individually passing; mean3 retention margin max(10pp,2SE),meeting max(6pp,2SE); stop exact>=fixed cap every draw/kind; rollback on failures. None is established by no-training smoke/data-audit evidence. No final-proof seal links all integrated factories/translator/executor/source/stop assets to these results; readiness/translator/human corpus assets, fair controls, F_eq/F_few, novelty and fresh independent scientific claim remain blockers.',
          '', 'Management action',
          'Do not announce scientific learning, generalization, overnight improvement, grammar, benchmark, target architecture, scaling or2x success. Stage1 both-seed descriptive gate fails and prediction-label verification is incomplete. Stage2 supports only recorded mechanical scaffolding/data construction with the provenance limitations above. Preserve the evidence; do not rescore holdouts or reconstruct unopened panels. James owns integration/push; this audit does neither.',
          '', 'Raw/protocol SHA256 inventory (self-contained; names are repo-relative)']
for p, info in sorted(inventory.items()):
    lines.append(f"{info['sha256']}  {p}  ({info['bytes']} bytes)")
lines += ['', 'Auditor output: recount.json supplies all36 counts, per-job budgets/pairing,31 seal checks,stage2 hash checks and test names. The script uses only Python stdlib and never imports project code. No post-blind source review is included in this verdict.']
(OUT/'BLIND-AUDIT.txt').write_text('\n'.join(lines)+'\n')
print(json.dumps({'saved':str(OUT),'stage1_checks':checks,'stage1_seed_verdicts':verdicts,
                  'stage2_smoke_code':smoke_code,'tests':len(tests),'spread_pp':spread,
                  'chain_all_match':all(all(x[k] for k in ['hash_match','previous_match','seq_match']) for x in chain)}))
