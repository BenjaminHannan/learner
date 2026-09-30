#!/usr/bin/env python3
"""Queued, bounded numeric TRAIN fit: fixed4 loop versus unshared4 sparse plain.

Question text only enters the reader. Independently verified numeric constants
plus EOS are labels. This runner has no sleep, activation, or held-panel path.
Torch and pretrained components are imported only after the pinned queue gates.
"""
from __future__ import annotations

import argparse
from collections import Counter
import datetime
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import random
import re
import shutil
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
OWN = ROOT / 'artifacts/sol-cloud-numeric-fit-20260930'
MIB = 1024 ** 2
RESERVE = 1024 ** 3
PAIR_CAP = 1280 * MIB
PROTECTED = ('uncle-questions', 'readpanel320', '/blind/', 'sealed-panels',
             'sealedquestions', 'sealed-user', 'sealeduser', 'sealed-blind', 'dev100', 'stop88')
NUMERIC = re.compile(r'-?(?:0|[1-9][0-9]*)(?:/[1-9][0-9]*|\.[0-9]+)?\Z')


def safe(path, root=None):
    text = '/' + str(path).replace('\\', '/').lower().strip('/') + '/'
    if any(item in text for item in PROTECTED):
        raise ValueError('protected path refused before content access')
    resolved = Path(path).resolve()
    text = '/' + str(resolved).replace('\\', '/').lower().strip('/') + '/'
    if any(item in text for item in PROTECTED):
        raise ValueError('protected resolved path refused before content access')
    if root is not None and not resolved.is_relative_to(Path(root).resolve()):
        raise ValueError('path outside approved root')
    return resolved


def sha(path):
    digest = hashlib.sha256()
    with safe(path).open('rb') as stream:
        for block in iter(lambda: stream.read(MIB), b''):
            digest.update(block)
    return digest.hexdigest()


def canonical(record):
    return hashlib.sha256(json.dumps(record, sort_keys=True, separators=(',', ':'),
                                    ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def read_pin(path, expected, root=None):
    path = safe(path, root)
    if type(expected) is not str or not re.fullmatch('[0-9a-f]{64}', expected):
        raise ValueError('exact SHA256 required')
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError('pinned artifact differs: ' + str(path))
    return json.loads(raw)


def artifact(pin):
    if type(pin) is not dict or set(pin) != {'path', 'sha256'}:
        raise ValueError('closed path/SHA pin required')
    path = Path(pin['path'])
    return safe(path if path.is_absolute() else ROOT / path, ROOT)


def validate_plan(plan):
    if (plan.get('schema') != 'sol.cloud.numeric-fit.plan.v1'
            or plan.get('seeds') != [0, 1] or plan.get('arms') != ['loop', 'plain']
            or plan.get('updates_per_arm') != 800 or plan.get('visits_per_row') != 50
            or plan.get('batch') != 1 or plan.get('rounds') != 4
            or plan.get('objective') != 'numeric-answer-CE-only'
            or plan.get('diagnostic_updates') != [0, 200, 400, 800]
            or plan.get('checkpoint_updates') != [800]
            or plan.get('input_scope') != 'question-only-empty-notebook'
            or plan.get('warmstart_family') != 'V12-connected200'
            or plan.get('optimizer') != {'name': 'AdamW', 'lr': 0.001, 'weight_decay': 0,
                    'betas': [0.9, 0.999], 'eps': 1e-8, 'clip_norm': 1, 'reset': True}
            or plan.get('generation_max_new_tokens') != 32
            or plan.get('question_cap') != 48 or plan.get('target_with_EOS_cap') != 64
            or plan.get('primary_metric') != 'target_ids_plus_observed_EOS_exact'):
        raise ValueError('authorized numeric-fit protocol differs')
    ids = plan.get('selected_ids')
    if type(ids) is not list or len(ids) != 16 or len(set(ids)) != 16 or any(type(i) is not str for i in ids):
        raise ValueError('exact sixteen unique predeclared IDs required')
    budget = plan.get('budget', {})
    if budget != {'pair_cap_bytes': PAIR_CAP, 'retained_free_bytes': RESERVE,
                  'planned_pair_peak_bytes': 540 * MIB,'planned_matrix_peak_bytes':1088*MIB,
                  'checkpoint_cap_bytes': {'loop': 108 * MIB, 'plain': 416 * MIB},
                  'raw_cap_bytes_per_pair': 16 * MIB, 'worker_seconds': 570,
                  'outer_seconds': 600, 'delivery_cap_bytes': 8 * MIB,
                  'delivery_scope':'global-once-including-staging-telemetry-and-logs'}:
        raise ValueError('approved bounded runtime/output budget differs')
    if type(plan.get('run_namespace')) is not str or not re.fullmatch(r'run-[a-z0-9-]+', plan['run_namespace']):
        raise ValueError('new literal additive run namespace required')
    return plan


def numeric_exact(text, target):
    # No eval, expression parser, solver, answer substitution, or prose target.
    text = text.strip()
    return bool(NUMERIC.fullmatch(text)) and Fraction(text) == Fraction(target)


def numeric_optimizer_step(ce, optimizer, parameters, torch_api, before_step=None):
    """One declared CE backward and one AdamW call, easy to test without Torch."""
    if not bool(torch_api.isfinite(ce)):
        raise RuntimeError('nonfinite numeric CE')
    ce.backward()
    if before_step is not None:
        before_step()
    preclip = torch_api.nn.utils.clip_grad_norm_(parameters,1,error_if_nonfinite=True)
    optimizer.step()
    return preclip


def observe_generation(decoder, packet, max_tokens=32):
    """Observe the SAME native generate result before the existing EOS strip.

    This supplies no extra generation argument, target, text, or forward call.
    The original instance/class method arrangement is restored even on failure.
    """
    if type(max_tokens) is not int or not 1 <= max_tokens <= 32:
        raise ValueError('strict integer observed-generation cap1..32')
    lm = decoder.lm
    original = lm.generate
    had_instance_method = 'generate' in vars(lm)
    original_instance_method = vars(lm).get('generate')
    calls = []
    def observed(*args, **kwargs):
        record = {'argument_keys': sorted(kwargs), 'positional_argument_count': len(args)}
        calls.append(record)
        result = original(*args, **kwargs)
        record['raw_ids'] = result.tolist()
        return result
    lm.generate = observed
    error = None
    returned = None
    try:
        returned = decoder.generate(packet,max_tokens=max_tokens)
    except Exception as caught:
        error = {'error_type':type(caught).__name__,'error':str(caught)}
    finally:
        if had_instance_method: lm.generate = original_instance_method
        else: delattr(lm,'generate')
    raw = calls[0].get('raw_ids') if len(calls)==1 else None
    allowed = ['attention_mask','bos_token_id','do_sample','eos_token_id','inputs_embeds',
               'max_new_tokens','pad_token_id','use_cache']
    call_valid = (len(calls)==1 and calls[0]['argument_keys']==allowed
                  and calls[0]['positional_argument_count']==0)
    typed = (type(raw) is list and len(raw)==1 and type(raw[0]) is list
             and all(type(token) is int and token>=0 for token in raw[0]))
    full = raw[0] if typed else None
    eos_positions = [i for i,token in enumerate(full) if token==decoder.eos_id] if typed else []
    if not call_valid or error: reason='invalid_native_generation_call'
    elif not typed: reason='invalid_or_multiple_output_sequences'
    elif len(full)>max_tokens: reason='invalid_generation_extent'
    elif len(eos_positions)>1: reason='invalid_multiple_EOS'
    elif eos_positions and eos_positions[-1]!=len(full)-1: reason='invalid_tokens_after_EOS'
    elif eos_positions: reason='observed_EOS'
    elif len(full)==max_tokens: reason='max_new_tokens_without_EOS'
    else: reason='terminated_without_observed_EOS'
    expected_strip = full[:eos_positions[0]] if eos_positions else full
    stripped_equal = typed and returned==[expected_strip]
    if not stripped_equal and reason=='observed_EOS': reason='invalid_native_stripped_output_parity'
    return {'MODEL_raw_generate_ids':raw,'MODEL_generated_ids_with_observed_EOS':full,
            'MODEL_native_decoder_return':returned,'native_generate_call_count':len(calls),
            'native_call_contract_valid':call_valid,'raw_output_single_typed_sequence':typed,
            'EOS_positions':eos_positions,'observed_EOS':bool(eos_positions),
            'termination_reason':reason,'native_stripped_output_equal':stripped_equal,
            'generation_error':error,'same_generation_call_no_rescore':True}


def score_observed_generation(observed, canonical_target_ids_with_EOS, eos_id):
    full=observed['MODEL_generated_ids_with_observed_EOS']
    return (observed['termination_reason']=='observed_EOS'
            and observed['native_stripped_output_equal'] is True
            and canonical_target_ids_with_EOS[-1]==eos_id
            and full==canonical_target_ids_with_EOS)


def resource_account(free_bytes,matrix_retained_bytes,pair_retained_bytes,
                     remaining_matrix_peak_bytes,global_retained_bytes,global_cap_bytes=8*MIB):
    values=(free_bytes,matrix_retained_bytes,pair_retained_bytes,remaining_matrix_peak_bytes,
            global_retained_bytes,global_cap_bytes)
    if (any(type(value) is not int for value in values) or min(values)<0
            or pair_retained_bytes>matrix_retained_bytes):
        raise ValueError('nonnegative consistent physical resource inventory required')
    if global_retained_bytes>global_cap_bytes:raise RuntimeError('global shared source/staging/log cap exceeded')
    additional=remaining_matrix_peak_bytes+global_cap_bytes-global_retained_bytes
    floor=RESERVE+additional
    return {'current_free_bytes':free_bytes,'matrix_retained_allocated_bytes':matrix_retained_bytes,
            'current_pair_retained_allocated_bytes':pair_retained_bytes,
            'other_seed_retained_allocated_bytes':matrix_retained_bytes-pair_retained_bytes,
            'remaining_matrix_peak_bytes':remaining_matrix_peak_bytes,
            'global_shared_retained_allocated_bytes':global_retained_bytes,
            'global_shared_cap_bytes':global_cap_bytes,
            'additional_whole_matrix_peak_bytes':additional,'startup_free_floor_bytes':floor,
            'retained_matrix_already_charged_to_current_free':True,'passed':free_bytes>=floor}


def allocated_bytes(directory, unit=65536):
    if not directory.exists(): return 0
    return sum(((p.stat().st_size+unit-1)//unit)*unit for p in directory.rglob('*') if p.is_file())


def filesystem_allocation_unit(path):
    if os.name=='nt':
        import ctypes
        sectors,bytes_per_sector,free_clusters,total_clusters=(ctypes.c_ulong() for _ in range(4))
        if not ctypes.windll.kernel32.GetDiskFreeSpaceW(str(path.resolve().anchor),ctypes.byref(sectors),
                ctypes.byref(bytes_per_sector),ctypes.byref(free_clusters),ctypes.byref(total_clusters)):
            raise RuntimeError('cannot verify filesystem allocation unit before writing')
        unit=sectors.value*bytes_per_sector.value
    else:
        stat=os.statvfs(path);unit=max(stat.f_frsize,stat.f_bsize)
    if not 0<unit<=65536:raise RuntimeError('allocation unit exceeds64KiB reserve allowance')
    return unit


def remaining_matrix_peak(matrix,plan,unit,plan_sha256):
    """Only future writes; closed checkpoints remain charged to fresh free."""
    remaining=0;closed=[]
    for seed in plan['seeds']:
        pair=matrix/('seed%d'%seed)
        raw=allocated_bytes(pair,unit)-sum(((p.stat().st_size+unit-1)//unit)*unit
            for p in pair.rglob('*') if p.is_file() and p.suffix in ('.pt','.tmp')) if pair.exists() else 0
        if raw>plan['budget']['raw_cap_bytes_per_pair']:
            raise RuntimeError('retained raw allocated bytes exceed sealed pair cap')
        pair_closed=True
        for arm in plan['arms']:
            marker=pair/arm/'CLOSED.json';is_closed=False
            if marker.exists():
                record=json.loads(safe(marker,OWN).read_bytes())
                is_closed=(record.get('closed') is True and record.get('optimizer_updates')==800
                    and record.get('seed')==seed and record.get('arm')==arm
                    and record.get('plan_sha256')==plan_sha256)
                if not is_closed:raise RuntimeError('invalid terminal closed marker; no resource credit')
            if is_closed:closed.append({'seed':seed,'arm':arm})
            else:
                pair_closed=False
                remaining+=plan['budget']['checkpoint_cap_bytes'][arm]
        if not pair_closed:remaining+=plan['budget']['raw_cap_bytes_per_pair']-raw
    return remaining,closed


def require_new_output(out):
    if out.exists() or out.is_symlink():
        raise RuntimeError('prior launch evidence exists; require additive namespace')


def save_new_atomic_file(path, allowance, serialize, before_extent):
    temporary=path.with_suffix(path.suffix+'.tmp')
    if any(p.exists() or p.is_symlink() for p in (path,temporary)):
        raise RuntimeError('checkpoint destination or temporary exists; never replace prior evidence')
    with temporary.open('xb') as stream:
        sink=BoundedFileSink(stream,allowance,before_extent)
        serialize(sink);sink.flush();os.fsync(sink.fileno())
    os.replace(temporary,path)  # First write: rename the one file, never a copy.
    return path


def token_gate(plan):
    pin = plan['token_gate']
    record = read_pin(artifact(pin),pin['sha256'],ROOT)
    if (record.get('status') != 'INDEPENDENT_SAVED_TOKEN_ENGINEERING_RECOUNT_PASS'
            or record.get('row_seal_sha256') != plan['selection']['sha256']
            or record.get('checks_passed') != 2412
            or record.get('accepted_source_rows') != 396
            or record.get('raw_tokenizer_reruns_by_review') != 0):
        raise ValueError('independent saved-token engineering recount missing')
    return record


def gates(args):
    if not os.environ.get('JOB') or safe(os.environ.get('TREE', '')) != ROOT:
        raise RuntimeError('watcher JOB and exact TREE required before imports')
    plan = validate_plan(read_pin(args.plan, args.plan_sha256, ROOT))
    seal = read_pin(args.seal, args.seal_sha256, ROOT)
    if seal.get('plan_sha256') != args.plan_sha256:
        raise ValueError('seal binds a different execution plan')
    for path, expected in seal['files'].items():
        source = safe(ROOT / path, ROOT)
        if sha(source) != expected:
            raise ValueError('sealed source differs: ' + path)
    if seal['files'].get(Path(__file__).resolve().relative_to(ROOT).as_posix()) != sha(__file__):
        raise ValueError('running numeric driver not sealed')
    release = read_pin(args.release, args.release_sha256, ROOT)
    if (release.get('authorized_by') not in ('Derek', 'Ben') or release.get('fit_released') is not True
            or release.get('seal_sha256') != args.seal_sha256):
        raise RuntimeError('exact numeric fit release absent')
    review_pin = release['independent_review']
    review = read_pin(artifact(review_pin), review_pin['sha256'], ROOT)
    if review.get('release_readiness') is not True or review.get('seal_sha256') != args.seal_sha256:
        raise RuntimeError('independent exact-seal review absent')
    inventory = read_pin(args.inventory, args.inventory_sha256, ROOT)
    timestamp = datetime.datetime.fromisoformat(inventory['observed_utc'].replace('Z', '+00:00'))
    age = (datetime.datetime.now(datetime.timezone.utc) - timestamp).total_seconds()
    if (not 0 <= age <= 120 or inventory.get('gpu_inventory_verified') is not True
            or inventory.get('project_gpu_processes') != []
            or inventory.get('other_watcher_running_claims') != []
            or inventory.get('source_checkpoint_closure_verified') is not True):
        raise RuntimeError('fresh exclusive resource and checkpoint inventory required')
    delivered = inventory.get('delivery_package_and_tree_bytes')
    if type(delivered) is not int or not 0 <= delivered <= plan['budget']['delivery_cap_bytes']:
        raise RuntimeError('delivered files exceed declared included allowance')
    global_retained=inventory.get('global_shared_allocated_bytes')
    if (inventory.get('global_shared_storage_verified') is not True
            or inventory.get('global_shared_cap_bytes')!=plan['budget']['delivery_cap_bytes']
            or type(global_retained) is not int or not 0<=global_retained<=plan['budget']['delivery_cap_bytes']):
        raise RuntimeError('fresh global-once source/staging/telemetry/log allocation proof required')
    selection = read_pin(artifact(plan['selection']), plan['selection']['sha256'], ROOT)
    if selection['selected_ids'] != plan['selected_ids']:
        raise ValueError('presealed selection differs')
    token_gate(plan)
    protocol = read_pin(artifact(plan['protocol']),plan['protocol']['sha256'],ROOT)
    if (protocol.get('row_seal_sha256') != plan['selection']['sha256']
            or protocol.get('numeric_target_CE_plus_EOS_only') is not True
            or protocol.get('sparse_auxiliary_in_objective') is not False):
        raise ValueError('parent protocol/selected rows/numeric objective differs')
    schedule_pin = plan['schedules'][str(args.seed)]
    schedule = read_pin(artifact(schedule_pin), schedule_pin['sha256'], ROOT)
    if Counter(schedule) != Counter({identity: 50 for identity in plan['selected_ids']}):
        raise ValueError('exact sixteen times fifty schedule differs')
    binding = plan['warmstart']['tuples'][str(args.seed)]
    if (binding['connected_resume_sha256'] != protocol['warmstart']['seed%d_sha256' % args.seed]
            or binding['connected_resume_path'] != protocol['warmstart']['seed%d_path' % args.seed]):
        raise ValueError('selected V12 warmstart differs from parent protocol')
    for key in ('parent', 'reader', 'adapter', 'connected_resume'):
        if sha(binding[key + '_path']) != binding[key + '_sha256']:
            raise ValueError('warm-start checkpoint differs: ' + key)
    if sha(binding['lm_provenance']) != plan['LM_provenance']['sha256']:
        raise ValueError('immutable frozen talker provenance differs')
    # Loader imports only its prepared question/constant/manifest packet path.
    sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
    from sol_cloud_luna_batch_adapter_v1 import load_verified_numeric_packet
    source = plan['source']
    rows = load_verified_numeric_packet(artifact(source['question']), source['question']['sha256'],
        artifact(source['target']), source['target']['sha256'],
        artifact(source['manifest']), source['manifest']['sha256'], ROOT)
    by_id = {row.id: row for row in rows}
    rows = [by_id[identity] for identity in plan['selected_ids']]
    audited = read_pin(artifact(plan['token_audit']), plan['token_audit']['sha256'], ROOT)
    if audited.get('selected_ids') != plan['selected_ids']:
        raise ValueError('token audit selected membership differs')
    audits = {record['id']: record for record in audited['selected_rows']}
    if any(identity not in audits for identity in plan['selected_ids']):
        raise ValueError('exact tokenizer audit lacks selected row coverage')
    for token_pin in audited['tokenizer_files']:
        if token_pin['name'] not in ('config.json','special_tokens_map.json','tokenizer.json','tokenizer_config.json'):
            raise ValueError('closed tokenizer metadata whitelist required')
        if sha(Path(binding['lm_path']) / token_pin['name']) != token_pin['sha256']:
            raise ValueError('actual frozen tokenizer file differs from row audit')
    pair = safe(OWN / plan['run_namespace'] / ('seed%d' % args.seed), OWN)
    matrix=OWN/plan['run_namespace']
    unit=filesystem_allocation_unit(OWN)
    existing=allocated_bytes(pair,unit)
    remaining,closed=remaining_matrix_peak(matrix,plan,unit,args.plan_sha256)
    account=resource_account(shutil.disk_usage(OWN).free,allocated_bytes(matrix,unit),existing,
                             remaining,global_retained,plan['budget']['delivery_cap_bytes'])
    account['actual_allocation_unit_bytes']=unit
    account['terminal_closed_arms']=closed
    if not account['passed']:
        raise RuntimeError('fresh disk lacks conservative pair peak plus1GiB reserve')
    return plan, binding, rows, schedule, inventory, audits, pair, account


class BoundedFileSink:
    """Same proven v5 extent guard; rejection happens before serializer writes."""
    def __init__(self, stream, maximum_bytes, before_extent):
        self.stream, self.maximum_bytes, self.before_extent = stream, maximum_bytes, before_extent
        self.extent = 0
    def write(self, data):
        extent = max(self.extent, self.stream.tell() + len(data))
        if extent > self.maximum_bytes:
            raise RuntimeError('serialized write exceeds per-file cap')
        self.before_extent(extent)
        written = self.stream.write(data)
        self.extent = max(self.extent, self.stream.tell())
        return written
    def seek(self, offset, whence=0):
        old = self.stream.tell()
        target = self.stream.seek(offset, whence)
        if not 0 <= target <= self.maximum_bytes:
            self.stream.seek(old)
            raise RuntimeError('serializer seek outside bounded extent')
        return target
    def tell(self): return self.stream.tell()
    def flush(self):
        self.before_extent(self.extent)
        return self.stream.flush()
    def fileno(self): return self.stream.fileno()


def validate_connected(raw, seed, binding):
    if (type(raw) is not dict or raw.get('arm') != 'connected' or raw.get('seed') != seed
            or raw.get('update') != 200 or type(raw.get('binding')) is not dict
            or any(raw['binding'].get(k) != binding.get(k) for k in
                   ('parent_sha256', 'reader_sha256', 'adapter_sha256', 'order_contract', 'lm_path'))
            or not {'core', 'reader', 'prefix', 'optimizer'}.issubset(raw) or 'table' in raw):
        raise ValueError('exact V12 connected200 core/reader/prefix lineage required; TABLE refused')
    return raw


def run(args):
    plan, binding, rows, schedule, inventory, audits, pair, account = gates(args)
    import torch
    from sol_translator_grounding_v6 import HumanInputProjection, human_loss
    from sol_translator_english_ordered_v10 import load_ordered_english
    from sol_spatial_poc_ordered_v2 import load_ordered_bundle, OrderedPlainAttentionReasoner
    from sol_spatial_poc_ordered_train_api_v2 import fixed4_training
    from scripts.sol_stop_ordered_api2 import ordered_attention_math
    from sol_translator_decoder import FinalLatent
    from sol_translator_runtime import component_fingerprint

    out = pair / args.arm
    require_new_output(out)
    out.mkdir(parents=True)
    launched = time.monotonic()
    updates = 0
    identity = {'schema': 'sol.cloud.numeric-fit.identity.v1', 'seed': args.seed, 'arm': args.arm,
        'job': os.environ['JOB'], 'plan_sha256': args.plan_sha256, 'seal_sha256': args.seal_sha256,
        'driver_sha256': sha(__file__), 'release_sha256': args.release_sha256,
        'inventory_sha256': args.inventory_sha256, 'source': plan['source'],
        'selection_sha256': plan['selection']['sha256'], 'token_audit_sha256': plan['token_audit']['sha256'],
        'binding': binding, 'actual_user_day': False, 'sleep_enabled': False, 'activation': False,
        'qualification': 'sixteen-TRAIN-numeric-fit-only-no-generalization-or-advantage-claim',
        'generated_outputs_never_training_labels': True,
        'supervisor_pid_metadata': os.environ.get('SOL_NUMERIC_FIT_SUPERVISOR_PID')}
    raw_identity = {key: identity[key] for key in ('seed', 'arm', 'job', 'plan_sha256',
        'seal_sha256', 'driver_sha256', 'selection_sha256', 'token_audit_sha256', 'actual_user_day')}
    allocation_unit=filesystem_allocation_unit(out)
    def allocated(size): return ((size+allocation_unit-1)//allocation_unit)*allocation_unit
    def total(): return sum(allocated(p.stat().st_size) for p in pair.rglob('*') if p.is_file())
    peak_pair_allocated_bytes=total()
    peak_matrix_allocated_bytes=allocated_bytes(pair.parent,allocation_unit)
    def guard(extra):
        if total() + extra > PAIR_CAP or shutil.disk_usage(out).free < RESERVE + extra:
            raise RuntimeError('pair allocation cap or1GiB retained reserve violated')
    def write_json(name, record, append=False):
        data = (json.dumps(record, sort_keys=True, ensure_ascii=False, allow_nan=False) + '\n').encode()
        if name=='CLOSED.json' and len(data)>65536:
            raise RuntimeError('final receipt exceeds declared64KiB allocation bound')
        path=out/name
        raw_bytes=sum(allocated(p.stat().st_size) for p in pair.rglob('*') if p.is_file() and p.suffix not in ('.pt','.tmp'))
        old_size=path.stat().st_size if path.exists() else 0
        prospective_raw=raw_bytes-allocated(old_size)+allocated(old_size+len(data) if append else len(data))
        if prospective_raw>plan['budget']['raw_cap_bytes_per_pair']:
            raise RuntimeError('raw JSON cap; preserve earlier records')
        guard(len(data) + 65536)
        with (out / name).open('ab' if append else 'xb') as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
    def tensor_hash(tensor):
        tensor = tensor.detach().cpu().contiguous()
        return {'shape': list(tensor.shape), 'dtype': str(tensor.dtype),
                'sha256': hashlib.sha256(tensor.numpy().tobytes()).hexdigest()}
    def timeout():
        if time.monotonic() - launched > plan['budget']['worker_seconds']:
            raise RuntimeError('bounded worker time exhausted; preserve partial evidence')
    def state_identity(core, reader, decoder):
        return {key: component_fingerprint(module) for key, module in
                [('core', core), ('reader', reader), ('prefix', decoder.adapter)]}
    def save_checkpoint(payload):
        nonlocal peak_pair_allocated_bytes,peak_matrix_allocated_bytes
        path = out / 'final-resume.pt'
        temporary = out / 'final-resume.pt.tmp'
        allowance = plan['budget']['checkpoint_cap_bytes'][args.arm]
        guard(allowance + 65536)
        def before_extent(extent):
            nonlocal peak_pair_allocated_bytes,peak_matrix_allocated_bytes
            actual = temporary.stat().st_size
            prospective = total() - allocated(actual) + allocated(max(actual, extent))
            matrix_prospective=allocated_bytes(pair.parent,allocation_unit)-allocated(actual)+allocated(max(actual,extent))
            peak_pair_allocated_bytes=max(peak_pair_allocated_bytes,prospective)
            peak_matrix_allocated_bytes=max(peak_matrix_allocated_bytes,matrix_prospective)
            if prospective + 65536 > PAIR_CAP or shutil.disk_usage(out).free < RESERVE + max(0, extent - actual) + 65536:
                raise RuntimeError('atomic serialization cap/reserve refusal; temporary preserved')
        save_new_atomic_file(path,allowance,lambda sink:torch.save(payload,sink),before_extent)
        return sha(path)

    try:
        write_json('LAUNCH.json', {**identity, 'optimizer_updates': 0, 'inventory': inventory,
                                'whole_matrix_resource_account':account})
        torch.set_num_threads(2)
        torch.manual_seed(args.seed)
        device = 'cuda'
        if not torch.cuda.is_available(): raise RuntimeError('authorized GPU unavailable')
        os.environ['HF_HUB_OFFLINE'] = '1'; os.environ['TRANSFORMERS_OFFLINE'] = '1'
        prefix_metadata = torch.load(binding['adapter_path'], map_location='cpu', weights_only=True)
        if prefix_metadata['parent_sha256'] != binding['parent_sha256'] or prefix_metadata['reader_sha256'] != binding['reader_sha256']:
            raise ValueError('base prefix tuple lineage differs')
        dec, tok, _ = load_ordered_english(binding['lm_path'], binding['lm_provenance'], binding['adapter_path'], device)
        lm = dec.lm
        loop, _ = load_ordered_bundle(binding['parent_path'], device)
        reader_raw = torch.load(binding['reader_path'], map_location='cpu', weights_only=True)
        reader = HumanInputProjection(reader_raw['lm_width']).to(device)
        reader.load_state_dict(reader_raw['state_dict'], strict=True)
        prior = validate_connected(torch.load(binding['connected_resume_path'], map_location='cpu', weights_only=True), args.seed, binding)
        inherited = {'V12_updates': 200, 'V12_optimizer_source_checkpoint_sha256': binding['connected_resume_sha256'],
                     'prior_optimizer_reset_not_reused': True, 'V11_binding': prior['binding']}
        loop.load_state_dict(prior['core'], strict=True)
        reader.load_state_dict(prior['reader'], strict=True)
        dec.adapter.load_state_dict(prior['prefix'], strict=True)
        del prior, prefix_metadata, reader_raw
        plain = OrderedPlainAttentionReasoner(loop).to(device)
        lm.eval().requires_grad_(False)
        if any(p.dtype != torch.float32 for module in (loop, plain, reader, dec.adapter, lm) for p in module.parameters()):
            raise RuntimeError('all inherited components must remain frozen-LM/fullFP32')
        tokens = []
        for row in rows:
            question = row.model_input(); target = row.target_text()
            qids = tok.encode(question, add_special_tokens=False)
            labels = tok.encode(target, add_special_tokens=False)
            audit = audits[row.id]
            if (not qids or len(qids) > 48 or len(labels) + 1 > 64
                    or qids != audit['question_token_ids_before_EOS'] or labels != audit['target_token_ids_before_EOS']
                    or qids+[tok.eos_token_id] != audit['question_token_ids_with_EOS']
                    or labels+[tok.eos_token_id] != audit['target_token_ids_with_EOS']
                    or audit['question_sha256'] != row.question_sha256
                    or audit['numeric_target'] != target):
                raise ValueError('actual current-tokenizer audit differs; no truncation or row replacement')
            ids = torch.tensor([qids + [tok.eos_token_id]], device=device, dtype=torch.long)
            target_ids = torch.tensor([labels + [tok.eos_token_id]], device=device, dtype=torch.long)
            tokens.append((ids, torch.ones_like(ids, dtype=torch.bool), target_ids))
        frames = [{'id': row.id, 'question_sha256': row.question_sha256,
            'canonical_numeric_target': row.target_text(), 'input_ids': item[0].cpu().tolist(),
            'input_mask': item[1].cpu().tolist(), 'notebook_ids': [[]], 'notebook_mask': [[]],
            'labels': item[2].cpu().tolist(), 'label_mask': (item[2] != -100).cpu().tolist()}
            for row,item in zip(rows,tokens)]
        for frame in frames: frame['frame_sha256'] = canonical(frame)
        write_json('INPUT-FRAMES.json', {**identity, 'rows': frames, 'truncation': False})
        def latent(module, i):
            ids, mask, _ = tokens[i]
            with torch.no_grad(): embeddings = lm.get_input_embeddings()(ids)
            query = reader(embeddings, mask)
            with ordered_attention_math():
                h, _, auxiliary = fixed4_training(module, query, None, query_mask=mask)
            return h, auxiliary
        loop.eval(); plain.eval(); reader.eval(); dec.adapter.eval()
        parity = []
        with torch.no_grad():
            for i, row in enumerate(rows):
                a, _ = latent(loop, i); b, _ = latent(plain, i)
                parity.append({'id': row.id, 'loop_final': tensor_hash(a), 'plain_final': tensor_hash(b),
                               'equal': bool(torch.equal(a,b)), 'max_abs_delta': float((a-b).abs().max())})
                if not torch.equal(a,b): raise RuntimeError('function-preserving initial loop/plain parity failed')
        core = loop if args.arm == 'loop' else plain
        if args.arm == 'loop': del plain
        else: del loop
        write_json('INITIAL-FUNCTION-PARITY.json', {**identity, 'all16_exact': True, 'rows': parity})
        # Restore the same declared RNG AFTER all constructors and parity calls.
        rng_seed = plan['rng_seeds'][str(args.seed)]
        random.seed(rng_seed); torch.manual_seed(rng_seed); torch.cuda.manual_seed_all(rng_seed)
        initial_cpu_rng = torch.get_rng_state().clone()
        initial_cuda_rng = [r.clone() for r in torch.cuda.get_rng_state_all()]
        lm_before = component_fingerprint(lm)
        initial = state_identity(core, reader, dec)
        for module in (core, reader, dec.adapter): module.train().requires_grad_(True)
        # Fixed4 never trains a halt criterion; no halt-loss or stop qualification.
        core.halt.requires_grad_(False)
        frozen_core = {'halt': component_fingerprint(core.halt),
                       'buffers': {name:tensor_hash(value) for name,value in core.named_buffers()}}
        named = [(group + '.' + name, p) for group,module in [('core',core), ('reader',reader), ('prefix',dec.adapter)]
                 for name,p in module.named_parameters() if p.requires_grad]
        params = [p for _,p in named]
        initial_parameter_hashes = {name: tensor_hash(p) for name,p in named}
        parameter_bytes = sum(p.numel() * p.element_size() for p in params)
        checkpoint_bound = 3 * parameter_bytes + 3 * MIB
        if checkpoint_bound > plan['budget']['checkpoint_cap_bytes'][args.arm]:
            raise RuntimeError('conservative parameter+Adam serialization bound fails before optimizer')
        write_json('INITIAL-STATE.json', {**identity, 'fingerprints': initial, 'inherited_lineage': inherited,
            'core_parameter_accounting':core.counts(),
            'reader_parameters':sum(p.numel() for p in reader.parameters()),
            'prefix_parameters':sum(p.numel() for p in dec.adapter.parameters()),
            'parameter_bytes': parameter_bytes, 'checkpoint_bound_bytes': checkpoint_bound,
            'initial_parameter_hashes': initial_parameter_hashes,
            'initial_torch_rng': tensor_hash(initial_cpu_rng),
            'initial_cuda_rng': [tensor_hash(r) for r in initial_cuda_rng], 'declared_rng_seed': rng_seed,
            'optimizer_initial_steps': 0, 'optimizer_reset': True,
            'frozen_core': frozen_core,
            'halt_frozen': True, 'objective': 'numeric-answer-CE-only', 'auxiliary_weight': 0})
        def graph(i):
            h, auxiliary = latent(core, i)
            prefix = dec.adapter.project_training(h, torch.ones_like(h, dtype=torch.bool), tokens[i][1], (1,h.shape[1]))
            return h, prefix, auxiliary
        @torch.no_grad()
        def diagnostic(step):
            before = state_identity(core, reader, dec)
            for module in (core, reader, dec.adapter): module.eval()
            for i, row in enumerate(rows):
                h, prefix, _ = graph(i)
                packet = FinalLatent(h.detach(), torch.ones_like(h,dtype=torch.bool), tokens[i][1], (1,h.shape[1]))
                observed=observe_generation(dec,packet,max_tokens=32)
                returned=observed['MODEL_native_decoder_return']
                generated=returned[0] if type(returned) is list and len(returned)==1 else None
                text=None;decode_error=None
                if generated is not None:
                    try:text=tok.decode(generated,skip_special_tokens=True)
                    except Exception as caught:decode_error={'error_type':type(caught).__name__,'error':str(caught)}
                expected = tokens[i][2][0,:-1].cpu().tolist()
                per, pred = human_loss(lm, prefix, tokens[i][2], dec.bos_id, dec.eos_id, True, True)
                write_json('DIAGNOSTIC-RAW.jsonl', {**raw_identity, 'update': step, 'id': row.id,
                    'source_question_sha256': row.question_sha256, 'input_frame_sha256': frames[i]['frame_sha256'],
                    'labels': tokens[i][2].cpu().tolist(), 'label_mask': (tokens[i][2] != -100).cpu().tolist(),
                    'canonical_numeric_target': row.target_text(), 'expected_answer_ids_without_EOS': expected,
                    'MODEL_generated_ids': generated, 'MODEL_generated_text': text,
                    'target_ids_exact': generated == expected,
                    'numeric_constant_exact':numeric_exact(text,row.target_text()) if type(text) is str else False,
                    'canonical_target_ids_with_EOS':tokens[i][2][0].cpu().tolist(),
                    'target_ids_plus_observed_EOS_exact':score_observed_generation(observed,tokens[i][2][0].cpu().tolist(),dec.eos_id),
                    'single_numeric_constant_text':bool(NUMERIC.fullmatch(text.strip())) if type(text) is str else False,
                    'decode_error':decode_error,**observed,
                    'teacherforced_argmax': pred.cpu().tolist(), 'numeric_CE': float(per.mean()),
                    'model_state_fingerprints': before, 'final_query': tensor_hash(h), 'final_prefix': tensor_hash(prefix),
                    'output_translator_input': 'FinalLatent-only', 'notebook_tokens': 0,
                    'generated_outputs_never_training_labels': True}, append=True)
                timeout()
            if state_identity(core,reader,dec) != before: raise RuntimeError('diagnostic mutated model weights')
            for module in (core, reader, dec.adapter): module.train()
            lm.eval()
        diagnostic(0)
        # Real graph/gradient memory admission; no optimizer step or extra loss.
        torch.cuda.reset_peak_memory_stats()
        for i in range(16):
            _, prefix, _ = graph(i)
            ce = human_loss(lm, prefix, tokens[i][2], dec.bos_id, dec.eos_id)
            ce.backward()
            for p in params: p.grad = None
            timeout()
        reserved = torch.cuda.max_memory_reserved()
        memory_cap = torch.cuda.get_device_properties(0).total_memory
        memory_pass = reserved + 4 * parameter_bytes + 512 * MIB <= memory_cap
        write_json('MEMORY-PREFLIGHT.json', {**identity, 'optimizer_updates': 0,
            'actual_graphs': 16, 'peak_reserved_bytes': reserved, 'Adam_margin_bytes': 4*parameter_bytes,
            'safety_bytes': 512*MIB, 'cap_bytes': memory_cap, 'passed': memory_pass})
        if not memory_pass or state_identity(core,reader,dec) != initial:
            raise RuntimeError('memory/unchanged-state preflight failed before optimizer')
        torch.set_rng_state(initial_cpu_rng); torch.cuda.set_rng_state_all(initial_cuda_rng)
        opt = torch.optim.AdamW(params, lr=0.001, weight_decay=0, betas=(0.9,0.999), eps=1e-8)
        visits = Counter(); participation = Counter(); nonzero_grad = Counter()
        by_id = {row.id:i for i,row in enumerate(rows)}
        fit_started = time.monotonic()
        for step, identity_id in enumerate(schedule,1):
            timeout()
            i = by_id[identity_id]
            opt.zero_grad(set_to_none=True)
            _, prefix, auxiliary = graph(i)
            per, pred = human_loss(lm,prefix,tokens[i][2],dec.bos_id,dec.eos_id,True,True)
            ce = per.mean()
            def record_participation():
                for name,p in named:
                    if p.grad is not None:
                        participation[name] += 1
                        if bool(torch.count_nonzero(p.grad)): nonzero_grad[name] += 1
            # Deliberately no router auxiliary/reward/grammar term.
            preclip = numeric_optimizer_step(ce,opt,params,torch,record_participation)
            updates = step; visits[identity_id] += 1
            if any(p.grad is not None for p in lm.parameters()): raise RuntimeError('frozen talker received gradients')
            write_json('TRAIN-RAW.jsonl', {**raw_identity, 'update': step, 'id': identity_id,
                'visit_for_row': visits[identity_id], 'schedule_sha256': plan['schedules'][str(args.seed)]['sha256'],
                'input_frame_sha256': frames[i]['frame_sha256'], 'source_question_sha256': rows[i].question_sha256,
                'labels': tokens[i][2].cpu().tolist(), 'label_mask': (tokens[i][2]!=-100).cpu().tolist(),
                'teacherforced_argmax': pred.cpu().tolist(), 'numeric_CE': float(ce.detach()),
                'router_auxiliary_observed_excluded': float(auxiliary.detach()), 'auxiliary_weight': 0,
                'preclip_norm': float(preclip), 'objective': 'numeric-answer-CE-only'}, append=True)
            if step in plan['diagnostic_updates']: diagnostic(step)
        if updates != 800 or visits != Counter({row.id:50 for row in rows}): raise RuntimeError('exact fit exposure incomplete')
        if component_fingerprint(lm) != lm_before: raise RuntimeError('frozen talker changed')
        if frozen_core != {'halt':component_fingerprint(core.halt),
                'buffers':{name:tensor_hash(value) for name,value in core.named_buffers()}}:
            raise RuntimeError('fixed halt or ordered boundary buffers changed')
        final = state_identity(core,reader,dec)
        optimizer_audit = []
        for name,p in named:
            state = opt.state.get(p,{})
            adam_step = int(state['step']) if state else 0
            if adam_step != participation[name]: raise RuntimeError('Adam step differs from actual gradient participation')
            changed = tensor_hash(p) != initial_parameter_hashes[name]
            if not state and changed: raise RuntimeError('unparticipating parameter changed')
            if nonzero_grad[name] and not bool(torch.count_nonzero(state['exp_avg_sq'])):
                raise RuntimeError('nonzero gradient lost durable second moment')
            optimizer_audit.append({'name': name, 'participation': participation[name],
                'nonzero_gradient_updates': nonzero_grad[name], 'Adam_step': adam_step, 'changed': changed,
                'final_parameter': tensor_hash(p), 'moments': {k:tensor_hash(state[k]) for k in ('exp_avg','exp_avg_sq')} if state else {}})
        checkpoint = {**identity, 'update': updates, 'constructor': core.constructor(),
            'core': core.state_dict(), 'reader': reader.state_dict(), 'prefix': dec.adapter.state_dict(),
            'optimizer': opt.state_dict(), 'optimizer_parameter_names': [name for name,_ in named],
            'torch_rng': torch.get_rng_state(), 'cuda_rng': torch.cuda.get_rng_state_all(),
            'python_rng': random.getstate(), 'initial_torch_rng': initial_cpu_rng,
            'initial_cuda_rng': initial_cuda_rng, 'declared_rng_seed': rng_seed,
            'visits': dict(visits), 'participation': dict(participation), 'optimizer_audit': optimizer_audit,
            'model_state_fingerprints': final, 'LM_fingerprint_unchanged': lm_before,
            'input_frames_sha256': sha(out/'INPUT-FRAMES.json'), 'TRAIN_raw_sha256': sha(out/'TRAIN-RAW.jsonl'),
            'DIAGNOSTIC_raw_sha256': sha(out/'DIAGNOSTIC-RAW.jsonl'),
            'schedule_sha256': plan['schedules'][str(args.seed)]['sha256'], 'raw_watermark_update': updates}
        checkpoint_sha = save_checkpoint(checkpoint)
        restored = torch.load(out/'final-resume.pt', map_location='cpu', weights_only=True)
        if restored['update'] != 800 or restored['visits'] != dict(visits) or restored['TRAIN_raw_sha256'] != sha(out/'TRAIN-RAW.jsonl'):
            raise RuntimeError('durable final checkpoint binding mismatch')
        for name,module in [('core',core), ('reader',reader), ('prefix',dec.adapter)]:
            for key,value in module.state_dict().items():
                if not torch.equal(restored[name][key],value.detach().cpu()): raise RuntimeError('durable model tensor reload differs')
        saved_states = restored['optimizer']['state']
        for index,(name,p) in enumerate(named):
            state = opt.state.get(p,{})
            saved = saved_states.get(index,{})
            if set(saved) != set(state): raise RuntimeError('durable optimizer state coverage differs')
            for key,value in state.items():
                if not torch.equal(saved[key],value.detach().cpu()): raise RuntimeError('durable Adam step/moment reload differs')
        timeout()
        write_json('CLOSED.json', {**identity, 'closed': True, 'optimizer_updates': updates, 'visits': dict(visits),
            'checkpoint': {'path': str((out/'final-resume.pt').relative_to(ROOT)), 'sha256': checkpoint_sha},
            'TRAIN_raw_sha256': sha(out/'TRAIN-RAW.jsonl'), 'DIAGNOSTIC_raw_sha256': sha(out/'DIAGNOSTIC-RAW.jsonl'),
            'input_frames_sha256': sha(out/'INPUT-FRAMES.json'), 'initial_fingerprints': initial,
            'final_fingerprints': final, 'initial_function_parity_all16_exact': True,
            'LM_unchanged': True, 'optimizer_reset': True, 'durable_model_and_Adam_reload_equal': True,
            'checkpoint_destination_absent_before_save':True,'final_checkpoint_writes_per_arm':1,
            'checkpoint_atomic_rename_not_copy':True,
            'checkpoint_serialization_peak_pair_allocated_bytes':peak_pair_allocated_bytes,
            'checkpoint_serialization_peak_matrix_allocated_bytes':peak_matrix_allocated_bytes,
            'peak_scope':'checkpoint serialization; final CLOSED.json separately adds at most64KiB',
            'final_CLOSED_JSON_additional_allocation_cap_bytes':65536,
            'whole_matrix_resource_account':account,
            'wall_seconds': time.monotonic()-launched, 'fit_plus_diagnostics_seconds': time.monotonic()-fit_started,
            'independent_saved_raw_recount': 'required-no-rescore', 'primary_metric': plan['primary_metric'],
            'primary_mark': 'both-loop-seeds16of16-final;plain-scored-identically', 'scientific_claim': False})
        print(json.dumps({'status':'CLOSED-NUMERIC-TRAIN-FIT','seed':args.seed,'arm':args.arm,
                          'optimizer_updates':800,'checkpoint_sha256':checkpoint_sha,'activation':False,
                          'final_pair_allocated_bytes_after_CLOSED':total(),
                          'final_matrix_allocated_bytes_after_CLOSED':allocated_bytes(pair.parent,allocation_unit)}),flush=True)
    except Exception as error:
        # Never overwrite/truncate prior raw or failed partial serializations.
        try: write_json('FAILED.json', {**identity, 'optimizer_updates':updates,
            'error_type':type(error).__name__,'error':str(error),'evidence_preserved':True})
        except Exception: pass
        raise


def supervise(args):
    """The proven direct-base v5 lifetime bound, with PID as metadata only."""
    environment = dict(os.environ, SOL_NUMERIC_FIT_SUPERVISOR_PID=str(os.getpid()))
    executable = getattr(sys,'_base_executable',sys.executable)
    command = [executable,'-X','utf8','-B',str(Path(__file__).resolve()),*sys.argv[1:],'--worker']
    options = {'env':environment}
    if os.name == 'nt': options['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP
    else: options['start_new_session'] = True
    process = subprocess.Popen(command,**options)
    try: return process.wait(timeout=570)
    except subprocess.TimeoutExpired:
        if os.name == 'nt': subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],check=True,timeout=10)
        else:
            os.killpg(process.pid,signal.SIGTERM)
            try: process.wait(timeout=3)
            except subprocess.TimeoutExpired: os.killpg(process.pid,signal.SIGKILL)
        process.wait(timeout=10)
        print(json.dumps({'status':'OWNED-WORKER-TIMEOUT','seed':args.seed,'arm':args.arm,
                          'owned_pid':process.pid,'activation':False,'evidence_preserved':True}),flush=True)
        return 124


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--seed',type=int,choices=(0,1),required=True)
    p.add_argument('--arm',choices=('loop','plain'),required=True)
    for name in ('plan','seal','release','inventory'):
        p.add_argument('--'+name,type=Path,required=True)
        p.add_argument('--'+name+'-sha256',required=True)
    p.add_argument('--worker',action='store_true',help=argparse.SUPPRESS)
    args=p.parse_args()
    if args.worker: run(args)
    else: raise SystemExit(supervise(args))


if __name__=='__main__': main()
