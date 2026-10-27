#!/usr/bin/env python3
"""Prepare and seal a held 16-row HUMAN TRAIN exposure diagnostic; never train."""
from __future__ import annotations
import argparse
import ast
from collections import Counter
import datetime
import json
from pathlib import Path
import random
import subprocess

from sol_cloud_trainonly_v1 import ROOT, canonical_sha, load_packet, sha

OWN = ROOT / 'artifacts/sol-cloud-exposure16-20260930/r5'
OLD = ROOT / 'artifacts/sol-translator-20260929'
MIB = 1024 ** 2


def write_new(path, value):
    if path.exists():
        raise ValueError('preserve earlier preparation; additive version required')
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def check(path=OWN / 'PLAN.json'):
    plan = json.loads(Path(path).read_text())
    if (plan['arms'] != ['connected'] or plan['updates_per_seed'] != 800
            or plan['batch'] != 1 or plan['visits_per_row'] != 50
            or plan['seeds'] != [0, 1] or len(set(plan['TRAIN_ids'])) != 16):
        raise ValueError('fixed unchanged-objective 16x50 exposure protocol differs')
    for seed in plan['seeds']:
        entry = plan['schedules'][str(seed)]
        p = ROOT / entry['path']
        if sha(p) != entry['sha256']:
            raise ValueError('schedule pin differs')
        schedule = json.loads(p.read_text())
        if Counter(schedule) != Counter({i: 50 for i in plan['TRAIN_ids']}):
            raise ValueError('exact exposure count differs')
        for at in range(0, 800, 16):
            if set(schedule[at:at + 16]) != set(plan['TRAIN_ids']):
                raise ValueError('full shuffled pass differs')
    if plan['historical_four_row_comparison']['fair_architecture_comparison']:
        raise ValueError('historical comparison is not an architecture qualification')
    return {'status': 'PASS preparation consistency', 'seeds': 2, 'rows': 16,
            'updates_per_seed': 800, 'visits_each_row_per_seed': 50,
            'model_calls': 0, 'optimizer_updates': 0, 'live_queue_entries': 0}


def build(output=OWN):
    output = Path(output)
    if output != OWN or (output / 'SEAL.json').exists():
        raise ValueError('new owned preparation only; preserve seals')
    output.mkdir(parents=True, exist_ok=True)
    receipt_path = ROOT / 'artifacts/sol-cloud-trainonly-20260930/VALIDATION-RECEIPT-v1.json'
    receipt = json.loads(receipt_path.read_text())
    rows = load_packet(ROOT / receipt['packet']['path'], receipt['packet']['sha256'],
                       ROOT / receipt['manifest']['path'], receipt['manifest']['sha256'])
    byid = {r['id']: r for r in rows}
    tiny_path = OLD / 'TINY-V12-PLAN.json'
    diag_path = OLD / 'ANSWER-V11-DIAGNOSTIC-PLAN.json'
    tiny, previous = json.loads(tiny_path.read_text()), json.loads(diag_path.read_text())
    old_seal = json.loads((OLD / 'TINY-V12-SEAL.json').read_text())
    for p in (tiny_path, diag_path, ROOT / 'scripts/sol_translator_tiny_v12.py',
              ROOT / 'scripts/sol_translator_package_tiny_v12.py'):
        if sha(p) != old_seal['files'][str(p.relative_to(ROOT))]:
            raise ValueError('historical pre-run source pin differs')
    ids = previous['TRAIN_diagnostic_ids']
    pairs = previous['same_context_pairs']
    if len(ids) != 16 or len(pairs) != 8 or [i for pair in pairs for i in pair] != ids:
        raise ValueError('historical sixteen-ID selection differs')
    if tiny['TRAIN_ids'] != ids[:4] or tiny['same_context_pairs'] != pairs[:2]:
        raise ValueError('V12 first-four historical selection differs')
    swap = {}
    references = []
    for a, b in pairs:
        ra, rb = byid[a], byid[b]
        if ra['context_sha256'] != rb['context_sha256']:
            raise ValueError('pair does not share context')
        if {x.casefold().strip() for x in ra['accepted_human_answers']} & {x.casefold().strip() for x in rb['accepted_human_answers']}:
            raise ValueError('paired human answers overlap')
        swap[a], swap[b] = b, a
    for identity in ids:
        row = byid[identity]
        references.append({
            'id': identity, 'source_hash': row['source_hash'], 'source_ref': row['source_ref'],
            'human_question': row['question'], 'human_context': row['context'],
            'human_answer_target': row['target_text'], 'field_sha256': row['field_sha256'],
            'official_answer_offsets': row['official_answer_offsets'],
            'source_provenance': row['provenance'],
            'packet_row_canonical_sha256': canonical_sha(row),
            'expected_identity_by_control': {'actual': identity, 'no_notebook': identity,
                                             'latent_swap_same_context': swap[identity]},
            'targets_are_human_annotations_only': True,
        })
    refpath = output / 'HUMAN-REFERENCE-FRAMES.json'
    write_new(refpath, {'schema': 'sol.cloud.exposure16.human-references.v1',
                       'model_authored_text_included': False, 'rows': references})
    schedules = {}
    for seed in (0, 1):
        rng = random.Random(2026093016 + seed)
        schedule = []
        for _ in range(50):
            block = list(ids)
            rng.shuffle(block)
            schedule.extend(block)
        path = output / ('SCHEDULE-s%d.json' % seed)
        write_new(path, schedule)
        schedules[str(seed)] = {'path': str(path.relative_to(ROOT)), 'sha256': sha(path),
                                'seed': 2026093016 + seed, 'updates': 800}
    budget = {
        'currency': 'USD', 'rental_cost': 0, 'hardware': 'existing free BensPC RTX5070Ti16GB',
        'execution': 'serial existing Mac watcher queues, bridge has priority',
        'per_seed': {'load_and_preflight_seconds': 150, 'fit_seconds': 300,
                     'all_diagnostics_seconds': 90, 'checkpoint_seconds': 30,
                     'child_seconds': 570, 'transport_seconds': 30, 'outer_seconds': 600},
        'two_seed_serial_outer_seconds': 1200,
        'fit_ETA_inferred_seconds_per_seed': [148, 296],
        'full_ETA_inferred_seconds_per_seed': [240, 570],
        'ETA_basis': {'historical_parent_report': 'V12 about74seconds for400mixed-arm updates perseed',
                      'receipt_locally_available': False, 'first_order_800_update_seconds': 148,
                      'connected_vs_mixed_planning_multiplier_upper': 2,
                      'caveat': 'weak inferredplanningrange, not measuredconfidencebounds; actual mayexceed600s and muststop incomplete, no silentbudget/schedule change'},
        'trainable_parameter_bytes_historical_measured': 36649272,
        'trainable_bytes_source': 'ground-v6-s1-PC.log numeric memory preflight; constructor unchanged',
        'checkpoint_serialized_cap_bytes_per_seed': 108 * MIB,
        'checkpoint_bound_justification': 'actualV12connectedresumes109564463bytes each (parentrc0collector08:37:32.96UTC);3P=109947816bytes fullFP32trainables+Adammoments plus3298392bytesmargin; actualzerooptimizerfullstorage serializationpreflightrequired; eachwrite bounded BEFORE file/global/free-space overrun',
        'raw_JSON_cap_bytes_per_seed': 8 * MIB,
        'binary_frame_cap_bytes_per_seed': 16 * MIB,
        'binary_frames': 'required actual/noNotebook finalquery andpooledprefix tensors only; redundant normalized/projected intermediates retain shape/hash/L2 only; actual initial serializedframex4 preflight BEFOREoptimizer',
        'two_seed_retained_output_bound_bytes': 264 * MIB,
        'atomic_checkpoint_peak_additional_bytes': 108 * MIB,
        'two_seed_output_atomic_bound_bytes': 372 * MIB,
        'aggregate_output_cap_including_atomic_peak_bytes': 384 * MIB,
        'operating_run_output_cap_bytes': 376 * MIB,
        'package_delivery_cap_bytes': 8 * MIB,
        'combined_output_atomic_plus_delivery_bound_bytes': 380 * MIB,
        'retained_free_bytes': 1024 ** 3,
        'startup_free_bytes': (1024 + 384) * MIB,
        'prior_reported_free_bytes': 1859121152,
        'prior_free_space_observed_utc': '2026-09-30T08:09:00Z parent report, exact seconds unavailable',
        'prior_free_space_fit_conditional': 1859121152 >= (1024 + 384) * MIB,
        'actual_current_disk_GPU_process_inventory': 'PENDING, required before release and again at launch',
        'peak_GPU_cap_bytes': 16 * 1024 ** 3,
        'GPU_preflight': 'ALL16 actual allowed input+target CE+aux backwards, zero optimizer; record perrow targetlength/peaks and maximum; clearallgrads, unchangedcore/reader/prefix/LMfingerprints, restoreCPU/CUDARNG; reserved+4P+512MiB<=16GiB',
        'copies': 'existing V11 tuple/LM reused; same resume destination used for zerooptimizerfullAdamstorage serializationpreflight then actualtraining; no LM copies or PC outputarchives; code/packetdelivery8MiB included within384MiBaggregate',
    }
    budget_path = output / 'BUDGET.json'
    write_new(budget_path, budget)
    passmarks = {
        'scope': 'TRAIN-only memorization/optimization diagnosis, not semantics or generalization',
        'mechanics': 'both seeds close exactly800 updates, every ID exactly50visits, correct immutable tuple/LM/source pins, rawdurable evidence and unchangedLM',
        'memorization_milestone': 'actual greedy generation atupdate800 exactlymatches tokenized selectedHUMAN answer withoutEOS on16/16rows in BOTH seeds',
        'controls': 'all16 actual/no_notebook/samecontext donorFinalLatent once atinitial,update200,update400,update800; donor identity and HUMAN expected answer presealed',
        'conditional_sensitivity': 'if actual16/16 eachseed, report noNotebook loss count and paired donoranswer count; deterioration cannot establish notebooksemantics or generalization',
        'noise': 'initial firsttwo predeclared IDs use sealedV12 parityhelper rawrepeat/cache/manual probes; no numeric acceptance threshold; rawrepeated differences retained',
        'interpretation': 'anyseedmissing16/16=>memorization milestone NOTSHOWN; seed disagreement=>INCONCLUSIVE; both16/16 with noNotebook16/16=>notebook necessity NOTSHOWN',
        'independent_recount': 'independent reviewer recomputes exactcounts from frozen savedhumanlabel/generatedID raw once, without modelcalls or rescoring',
        'scientific_promotion': False, 'activation': False, 'grammar_qualified': False,
        'holdouts': 0, 'DEV100': 0, 'stop88': 0, 'live_user_day': False,
        'reports_and_generated_outputs_never_training_material': True,
    }
    markpath = output / 'PASSMARKS.json'
    write_new(markpath, passmarks)
    plan = {
        'schema': 'sol.cloud.exposure16.plan.v1',
        'status': 'CONDITIONAL DEREK RELEASE: independentreviewPASS and actualbridgecomplete/freshinventory/resourcepreflight required',
        'bridge_priority': 'fixture capture-to-night rollback cycle first',
        'TRAIN_ids': ids, 'same_context_pairs': pairs, 'latent_swap_donor_id': swap,
        'seeds': [0, 1], 'updates_per_seed': 800, 'visits_per_row': 50, 'batch': 1,
        'arms': ['connected'], 'lr': tiny['connected_lr'], 'weight_decay': tiny['weight_decay'],
        'clip_norm': tiny['clip_norm'], 'rounds': 4,
        'objective': 'unchanged V12 connected: exactHUMAN answer+EOS shiftedCE plus existingmean8routeraux',
        'architecture': 'unchanged sharedthinreader/recurrentattention+sparseMLPexperts/notebook/sharedprefix/frozenFP32LM; no TABLE or ID routing',
        'output_contract': 'only detached finalquery FinalLatent with mask/shape reaches decoder; no raw question/context/audit/reference prompt',
        'training_graph_contract': 'CE prefix projection remains differentiable through finalquery into sharedcore andreader, exactlyV12connected; only generation/control packets detached',
        'additive_review_repairs': {'prior_seal': {'path': 'artifacts/sol-cloud-exposure16-20260930/SEAL.json',
                                                 'sha256': sha(ROOT / 'artifacts/sol-cloud-exposure16-20260930/SEAL.json')},
                                   'diagnostic_state_identity': 'current core/reader/prefix fingerprints in everydiagnostic/rawframe and durable checkpoint hashreceipt; initial fingerprints saved',
                                   'memory_probe': 'all16 actual graphbackwards including eachHUMAN targetlength, no optimizer; exactweightsunchanged, clearedgrads/restoredRNG',
                                   'frame_bound': 'actualinitialserializedrequired query/prefixframe size timesfour checked beforeoptimizer; intermediates hashes/normsonly',
                                   'parent_caps': '600seconds/seed,384MiB aggregate INCLUDINGatomic savepeak; preserve800x2/50visit schedule; oldlarger caps superseded'},
        'JSON_allocation_guard': 'each JSON write reserves exact encoded bytes plus64KiB before open/write; native filesystem allocation unit must be positive and<=64KiB or fail before evidence writes',
        'atomic_sink_contract': 'eachwrite/flush checked BEFORE crossing perfile allowance, aggregate376MiB run cap plus8MiBdelivery, or1GiBfree reserve; bufferedhighwater/randomseeks accounted',
        'historical_checkpoint_stat': {'path': 'artifacts/sol-cloud-exposure16-20260930/r3/CHECKPOINT-STAT-v1.json',
                                       'sha256': sha(ROOT / 'artifacts/sol-cloud-exposure16-20260930/r3/CHECKPOINT-STAT-v1.json')},
        'input_caps': {'question': 48, 'notebook': 512, 'target_with_EOS': 64},
        'generation_max_new_tokens': 32, 'diagnostic_updates': [0, 200, 400, 800],
        'checkpoint_updates': [200, 400, 600, 800], 'CE_gradient_capture_updates': [1] + list(range(50, 801, 50)),
        'parity_initial_ids': ids[:2], 'parity_max_new_tokens': 16,
        'selection': {'historical_diag': {'path': str(diag_path.relative_to(ROOT)), 'sha256': sha(diag_path)},
                      'basis': 'same first8 pairedgroups/16 IDs predeclared before V11/V12 results, allretained, not successselected'},
        'warmstart': {'basis': 'EXACT V11 closed200 tuples used by V12 at update0; not V12 fittedweights', 'tuples': tiny['tuples']},
        'source': {'packet': receipt['packet'], 'manifest': receipt['manifest'], 'loader': receipt['loader']},
        'historical_four_row_comparison': {'plan': {'path': str(tiny_path.relative_to(ROOT)), 'sha256': sha(tiny_path)},
                                         'rows': 4, 'visits_per_row': 50, 'connected_updates': 200,
                                         'fair_architecture_comparison': False,
                                         'interpretation': 'scales exposedexamples and totalupdates at fixed50visits; not fairarchitecturewin or new heldoutproof'},
        'references': {'path': str(refpath.relative_to(ROOT)), 'sha256': sha(refpath)},
        'schedules': schedules,
        'budget': {'path': str(budget_path.relative_to(ROOT)), 'sha256': sha(budget_path)},
        'passmarks': {'path': str(markpath.relative_to(ROOT)), 'sha256': sha(markpath)},
        'LM_provenance': {'path': str((OLD / 'CACHED-LFM-ORIGINAL-PROVENANCE.json').relative_to(ROOT)),
                          'sha256': sha(OLD / 'CACHED-LFM-ORIGINAL-PROVENANCE.json')},
        'actual_user_day': False, 'generated_training_material': False,
        'stop88_exclusion_metadata': 'unavailable; scope explicitly released existingTRAIN512 only',
        'release_required': True, 'runtime_inventory_required': True, 'independent_review_required': True,
    }
    planpath = output / 'PLAN.json'
    write_new(planpath, plan)
    templatepaths = []
    for seed in (0, 1):
        template = f'''STATUS: HELD
BASH-ONLY: yes
LOAD-LIGHT: yes
GPU: yes
TIME CAP: 10 minutes
LABEL: sol-cloud-exposure16-v1-s{seed}-pc

CONDITIONALLY RELEASED by Derek only after independentreviewPASS and actual
bridgecomplete, fresh inventory and resourcepreflight. Do not copy this held
template into a live queue until conditions are met. Seeds execute serially.
Existing V11 checkpoint tuple and frozen FP32 LM are reused without copies.
Fresh PC disk/GPU/process inventory, closure evidence and reviewed release pins
must be supplied by the designated integrator. This template alone authorizes no launch.

```bash
set -euo pipefail
: "${{SOL_APPROVED_PC_TREE:?released delivery tree required}}"
: "${{SOL_APPROVED_RELEASE:?reviewed release path required}}"
: "${{SOL_APPROVED_RELEASE_SHA256:?reviewed release digest required}}"
: "${{SOL_FRESH_INVENTORY:?fresh inventory path required}}"
: "${{SOL_FRESH_INVENTORY_SHA256:?fresh inventory digest required}}"
perl -e 'alarm shift; exec @ARGV' 600 ssh -T -o BatchMode=yes -o ConnectTimeout=15 benspc \\
  "C:\\Users\\benja\\lis300\\venv\\Scripts\\python.exe -X utf8 -B $SOL_APPROVED_PC_TREE/scripts/sol_cloud_exposure16_v5.py --seed {seed} --release $SOL_APPROVED_RELEASE --release-sha256 $SOL_APPROVED_RELEASE_SHA256 --inventory $SOL_FRESH_INVENTORY --inventory-sha256 $SOL_FRESH_INVENTORY_SHA256"
```

Delivery, watcher environment, unique claim/exit receipts, timeout termination,
evidence collection and hash-verified archive are integrator release duties.
This held template is not a standalone transport or live watcher release.
'''
        path = output / ('HELD-queue-exposure16-s%d.md' % seed)
        if path.exists():
            raise ValueError('preserve held template')
        path.write_text(template)
        syntax = subprocess.run(['bash', '-n'], input=template.split('```bash\n')[1].split('```')[0],
                                capture_output=True, text=True)
        if syntax.returncode:
            raise ValueError('held queue bash syntax')
        templatepaths.append(path)
    runtime_paths = [ROOT / path for path in old_seal['files'] if path.startswith('scripts/')
                     and 'tiny' not in path and 'package' not in path]
    own_scripts = [ROOT / 'scripts/sol_cloud_exposure16_prepare_v5.py',
                   ROOT / 'scripts/sol_cloud_exposure16_v5.py', ROOT / receipt['loader']['path']]
    files = {str(p.relative_to(ROOT)): sha(p) for p in
             runtime_paths + own_scripts + [ROOT / receipt['packet']['path'], ROOT / receipt['manifest']['path'],
             planpath, budget_path, markpath, refpath, tiny_path, diag_path,
             OLD / 'CACHED-LFM-ORIGINAL-PROVENANCE.json'] + templatepaths +
             [ROOT / v['path'] for v in schedules.values()]}
    for p in runtime_paths:
        if sha(p) != old_seal['files'][str(p.relative_to(ROOT))]:
            raise ValueError('historical runtime source changed')
    for p in own_scripts:
        ast.parse(p.read_text())
    sealpath = output / 'SEAL.json'
    write_new(sealpath, {'schema': 'sol.cloud.exposure16.seal.v1',
                         'sealed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                         'status': 'HELD UNTIL DEREK CONDITIONAL RELEASE GATES SATISFIED', 'files': files,
                         'model_calls': 0, 'optimizer_updates': 0, 'live_queue_entries': 0,
                         'approval': 'Derek conditionally released afterbridge+independentreviewPASS+freshresourceinventory;600s/seed384MiB atomiccap; integratoralonepublishes',
                         'independent_review': 'pending; review is separate from immutable seal'})
    checks = check(planpath)
    checks.update(seal_sha256=sha(sealpath), files=len(files),
                  driver_sha256=sha(ROOT / 'scripts/sol_cloud_exposure16_v5.py'),
                  prepare_sha256=sha(__file__))
    write_new(output / 'PREPARATION-CHECKS.json', checks)
    return checks


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['build', 'check'])
    args = parser.parse_args()
    print(json.dumps(build() if args.action == 'build' else check(), indent=2))
