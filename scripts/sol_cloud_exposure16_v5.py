#!/usr/bin/env python3
"""HELD connected16 HUMAN TRAIN diagnostic; execution requires reviewed release.

Imports no Torch until watcher, release, inventory and source gates pass.
The prepared protocol is not authorized to run merely because this file exists.
"""
from __future__ import annotations
import argparse
from collections import Counter
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from sol_cloud_trainonly_v1 import canonical_sha, load_packet, sha

OWN = ROOT / 'artifacts/sol-cloud-exposure16-20260930/r5'


class BoundedFileSink:
    """Reject an extent/cap violation before a serializer can write bytes."""
    def __init__(self, stream, maximum_bytes, before_extent):
        self.stream = stream
        self.maximum_bytes = maximum_bytes
        self.before_extent = before_extent
        self.extent = 0

    def write(self, data):
        prospective = max(self.extent, self.stream.tell() + len(data))
        if prospective > self.maximum_bytes:
            raise RuntimeError('serialized write would exceed sealed per-file allowance')
        self.before_extent(prospective)
        result = self.stream.write(data)
        self.extent = max(self.extent, self.stream.tell())
        return result

    def seek(self, offset, whence=0):
        old = self.stream.tell()
        target = self.stream.seek(offset, whence)
        if target < 0 or target > self.maximum_bytes:
            self.stream.seek(old)
            raise RuntimeError('serializer seek outside bounded file extent')
        return target

    def tell(self):
        return self.stream.tell()

    def flush(self):
        self.before_extent(self.extent)
        return self.stream.flush()

    def fileno(self):
        return self.stream.fileno()


def read_pin(path, digest):
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError('external artifact pin differs')
    return json.loads(raw.decode('utf-8'))


def gates(args):
    if not os.environ.get('JOB') or Path(os.environ.get('TREE', '')).resolve() != ROOT:
        raise RuntimeError('watcher queue JOB and exact TREE required')
    seal_path = OWN / 'SEAL.json'
    release = read_pin(args.release, args.release_sha256)
    if (release.get('authorized_by') != 'Derek' or release.get('fit_released') is not True
            or release.get('seal_sha256') != sha(seal_path)
            or release.get('bridge_priority_satisfied') is not True):
        raise RuntimeError('exact reviewed fit release absent or bridge priority unresolved')
    review = release.get('independent_review', {})
    report = read_pin(review['path'], review['sha256'])
    if report.get('release_readiness') is not True or report.get('seal_sha256') != sha(seal_path):
        raise RuntimeError('independent pre-run review has not approved this exact seal')
    inventory = read_pin(args.inventory, args.inventory_sha256)
    timestamp = datetime.datetime.fromisoformat(inventory['observed_utc'].replace('Z', '+00:00'))
    age = (datetime.datetime.now(datetime.timezone.utc) - timestamp).total_seconds()
    if (not 0 <= age <= 120 or inventory.get('gpu_inventory_verified') is not True
            or inventory.get('project_gpu_processes') != []
            or inventory.get('other_watcher_running_claims') != []
            or inventory.get('V11_source_checkpoint_closure_verified') is not True
            or inventory.get('checkpoint_serialization_bound_verified') is not True):
        raise RuntimeError('fresh exclusive PC/GPU/watcher/closure inventory required')
    seal = json.loads(seal_path.read_text())
    for path, digest in seal['files'].items():
        if path.startswith('handoff/') or '/corpus/' in path:
            raise ValueError('legacy mixed/raw/document files cannot be admitted by this seal')
        if sha(ROOT / path) != digest:
            raise ValueError('sealed source pin differs: ' + path)
    plan = json.loads((OWN / 'PLAN.json').read_text())
    if (plan['arms'] != ['connected'] or plan['batch'] != 1 or plan['rounds'] != 4
            or plan['updates_per_seed'] != 800 or plan['visits_per_row'] != 50):
        raise ValueError('sealed exposure protocol differs')
    budget = read_pin(ROOT / plan['budget']['path'], plan['budget']['sha256'])
    if budget['per_seed']['outer_seconds'] > 600 or budget['aggregate_output_cap_including_atomic_peak_bytes'] > 384 * 1024 ** 2:
        raise RuntimeError('parent hard time/output caps exceeded')
    if (type(inventory.get('delivery_package_and_tree_bytes')) is not int
            or not 0 <= inventory['delivery_package_and_tree_bytes'] <= budget['package_delivery_cap_bytes']):
        raise RuntimeError('actual delivered code/packet bytes exceed included delivery allowance')
    if shutil.disk_usage(OWN).free < budget['startup_free_bytes']:
        raise RuntimeError('current startup free space below sealed reserve')
    source = plan['source']
    rows = load_packet(ROOT / source['packet']['path'], source['packet']['sha256'],
                       ROOT / source['manifest']['path'], source['manifest']['sha256'])
    byid = {r['id']: r for r in rows}
    selected = [byid[identity] for identity in plan['TRAIN_ids']]
    entry = plan['schedules'][str(args.seed)]
    schedule = read_pin(ROOT / entry['path'], entry['sha256'])
    if Counter(schedule) != Counter({r['id']: 50 for r in selected}):
        raise ValueError('sealed exact50 exposure schedule differs')
    for key in ('parent', 'reader', 'adapter'):
        binding = plan['warmstart']['tuples'][str(args.seed)]
        if sha(binding[key + '_path']) != binding[key + '_sha256']:
            raise ValueError('original V11 closed200 tuple differs: ' + key)
    return plan, budget, selected, schedule, inventory


def run(args):
    plan, budget, rows, schedule, inventory = gates(args)
    # The above gates fail before imports/model loading/optimizer creation.
    import torch
    from sol_translator_grounding_v6 import HumanInputProjection, question_notebook_tokens, target_tokens, human_loss
    from sol_translator_english_ordered_v10 import load_ordered_english
    from sol_spatial_poc_ordered_v2 import load_ordered_bundle
    from sol_spatial_poc_ordered_train_api_v2 import fixed4_training
    from scripts.sol_stop_ordered_api2 import ordered_attention_math
    from sol_translator_decoder import FinalLatent
    from sol_translator_runtime import component_fingerprint
    from sol_spatial_decoder_parity_adapter_v12 import probe_decoder_parity

    out = OWN / 'runs' / ('s%d' % args.seed)
    if out.exists():
        raise RuntimeError('preserve earlier launch; new additive protocol required')
    out.mkdir(parents=True)
    launched = time.monotonic()
    updates = 0
    diag_elapsed = 0.0
    fit_elapsed = 0.0
    checkpoint_elapsed = 0.0
    byid = {r['id']: i for i, r in enumerate(rows)}
    binding = plan['warmstart']['tuples'][str(args.seed)]
    identity = {'seed': args.seed, 'job': os.environ['JOB'], 'binding': binding,
                'plan_sha256': sha(OWN / 'PLAN.json'), 'seal_sha256': sha(OWN / 'SEAL.json'),
                'release_sha256': args.release_sha256, 'inventory_sha256': args.inventory_sha256,
                'source': plan['source'], 'actual_user_day': False,
                'generated_training_material': False, 'split': 'released-HUMAN-TRAIN-memorization-only'}
    raw_identity = {'seed': args.seed, 'job': os.environ['JOB'],
                    'plan_sha256': identity['plan_sha256'], 'seal_sha256': identity['seal_sha256'],
                    'binding_sha256': canonical_sha(binding),
                    'TRAIN_packet_sha256': plan['source']['packet']['sha256'],
                    'TRAIN_manifest_sha256': plan['source']['manifest']['sha256'],
                    'actual_user_day': False, 'split': identity['split']}

    def total_bytes():
        return sum(p.stat().st_size for p in OWN.rglob('*') if p.is_file())

    allocation_unit = 65536
    if os.name == 'nt':
        import ctypes
        sectors, bytes_per_sector, free_clusters, total_clusters = (ctypes.c_ulong() for _ in range(4))
        volume = str(out.resolve().anchor)
        if not ctypes.windll.kernel32.GetDiskFreeSpaceW(volume, ctypes.byref(sectors), ctypes.byref(bytes_per_sector),
                                                       ctypes.byref(free_clusters), ctypes.byref(total_clusters)):
            raise RuntimeError('cannot verify filesystem allocation unit before writing')
        allocation_unit = sectors.value * bytes_per_sector.value
    else:
        stat = os.statvfs(out)
        allocation_unit = max(stat.f_frsize, stat.f_bsize)
    if not 0 < allocation_unit <= 65536:
        raise RuntimeError('allocation unit exceeds sealed64KiB reserve margin')

    def disk_guard(estimate):
        if (total_bytes() + estimate > budget['operating_run_output_cap_bytes']
                or shutil.disk_usage(out).free < budget['retained_free_bytes'] + estimate):
            raise RuntimeError('sealed output cap or 1GiB free reserve; preserve earlier evidence')

    def raw_bytes():
        return sum(p.stat().st_size for p in out.iterdir() if p.is_file() and p.suffix not in ('.pt', '.tmp'))

    def json_write(path, record, append=False):
        data = (json.dumps(record, ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8')
        if raw_bytes() + len(data) > budget['raw_JSON_cap_bytes_per_seed']:
            raise RuntimeError('sealed raw JSON cap; preserve evidence')
        # Data growth plus a verified allocation-unit and metadata margin.
        disk_guard(len(data) + 65536)
        with path.open('ab' if append else 'xb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())

    def tensor_hash(x):
        x = x.detach().cpu().contiguous()
        return {'shape': list(x.shape), 'dtype': str(x.dtype),
                'sha256': hashlib.sha256(x.numpy().tobytes()).hexdigest()}

    def binary_save(path, record, checkpoint=False):
        nonlocal checkpoint_elapsed
        save_start = time.monotonic()
        estimate = budget['checkpoint_serialized_cap_bytes_per_seed'] if checkpoint else record.pop('_estimated_bytes')
        disk_guard(estimate)
        tmp = path.with_suffix('.pt.tmp')
        if tmp.exists():
            raise RuntimeError('preserve earlier incomplete serialization')
        def before_extent(extent):
            actual = tmp.stat().st_size
            # Buffered writes may be ahead of file.stat(); charge their full
            # extent exactly once, plus any growth in the proposed write.
            projected_total = total_bytes() - actual + max(actual, extent)
            pending_growth = max(0, extent - actual)
            if (projected_total > budget['operating_run_output_cap_bytes']
                    or shutil.disk_usage(out).free < budget['retained_free_bytes'] + pending_growth + 65536):
                raise RuntimeError('serialized write would exceed aggregate cap or1GiB reserve')
        with tmp.open('xb') as stream:
            bounded = BoundedFileSink(stream, estimate, before_extent)
            torch.save(record, bounded)
            bounded.flush()
            os.fsync(bounded.fileno())
        if tmp.stat().st_size > estimate or total_bytes() > budget['operating_run_output_cap_bytes']:
            raise RuntimeError('actual serialization exceeds seal; preserve temporary/prior checkpoint')
        if not checkpoint:
            frame_bytes = sum(p.stat().st_size for p in out.glob('frames-*.pt')) + tmp.stat().st_size
            if frame_bytes > budget['binary_frame_cap_bytes_per_seed']:
                raise RuntimeError('binary frame cap; preserve prior evidence')
        os.replace(tmp, path)
        if checkpoint:
            checkpoint_elapsed += time.monotonic() - save_start
            if checkpoint_elapsed > budget['per_seed']['checkpoint_seconds']:
                raise RuntimeError('sealed checkpoint time budget exceeded; durable evidence preserved')
        return sha(path)

    json_write(out / 'LAUNCH.json', {**identity, 'optimizer_updates': 0, 'inventory': inventory})
    torch.set_num_threads(2)
    torch.manual_seed(args.seed)
    device = 'cuda'
    dec, tok, _ = load_ordered_english(binding['lm_path'], ROOT / plan['LM_provenance']['path'],
                                      binding['adapter_path'], device)
    lm = dec.lm
    core, _ = load_ordered_bundle(binding['parent_path'], device)
    rraw = torch.load(binding['reader_path'], weights_only=True, map_location=device)
    reader = HumanInputProjection(rraw['lm_width']).to(device)
    reader.load_state_dict(rraw['state_dict'])
    tokens = [(*question_notebook_tokens(tok, r, device, max_question=48, max_context=512),
               target_tokens(tok, [r], device, max_tokens=64)) for r in rows]
    before_lm = component_fingerprint(lm)
    groups = [('core', list(core.parameters())), ('reader', list(reader.parameters())),
              ('prefix', list(dec.adapter.parameters()))]
    params = [p for _, ps in groups for p in ps]
    param_bytes = sum(p.numel() * p.element_size() for p in params)
    if 3 * param_bytes + 3 * 1024 ** 2 > budget['checkpoint_serialized_cap_bytes_per_seed']:
        raise RuntimeError('actual parameter/Adam bound exceeds sealed checkpoint cap')
    initial = {key: component_fingerprint(module) for key, module in
               [('core', core), ('reader', reader), ('prefix', dec.adapter)]}
    json_write(out / 'INITIAL-STATE.json', {**identity, 'optimizer_updates': 0,
               'model_state_fingerprints': initial, 'LM_fingerprint': before_lm,
               'trainable_parameter_bytes': param_bytes, 'warmstart_tuple_hashes_verified': True})
    initial_cpu_rng = torch.get_rng_state().clone()
    initial_cuda_rng = [state.clone() for state in torch.cuda.get_rng_state_all()]
    initial_weights = {key: [p.detach().cpu().clone() for p in ps] for key, ps in groups}
    for module in (core, reader, dec.adapter):
        module.train().requires_grad_(True)
    hooks = {}
    handles = [dec.adapter.project[0].register_forward_pre_hook(lambda m, x: hooks.__setitem__('normalized_geometry', x[0])),
               dec.adapter.project[-1].register_forward_hook(lambda m, x, y: hooks.__setitem__('token_projected', y))]

    def graph(i, no_book=False):
        ids, valid, mids, mvalid, _ = tokens[i]
        with torch.no_grad():
            qe, be = lm.get_input_embeddings()(ids), lm.get_input_embeddings()(mids)
        query = reader(qe, valid)
        book = reader(be, mvalid).flatten(1, 2)
        if no_book:
            book, mvalid = book[:, :0], mvalid[:, :0]
        with ordered_attention_math():
            h, _, aux = fixed4_training(core, query, book, query_mask=valid, notebook_mask=mvalid)
        prefix = dec.adapter.project_training(h, torch.ones_like(h, dtype=torch.bool), valid, (1, h.shape[1]))
        return prefix, aux, {'final_query': h, 'normalized_geometry': hooks['normalized_geometry'],
                             'token_projected': hooks['token_projected'], 'pooled_prefix': prefix}

    def packet(i, trace):
        h = trace['final_query'].detach()
        return FinalLatent(h, torch.ones_like(h, dtype=torch.bool), tokens[i][1], (1, h.shape[1]))

    input_frames = []
    for i, row in enumerate(rows):
        ids, valid, mids, mvalid, labels = tokens[i]
        frame = {'id': row['id'], 'input_ids': ids.cpu().tolist(), 'input_mask': valid.cpu().tolist(),
                 'notebook_ids': mids.cpu().tolist(), 'notebook_mask': mvalid.cpu().tolist(),
                 'labels': labels.cpu().tolist(), 'label_mask': (labels != -100).cpu().tolist(),
                 'human_field_sha256': row['field_sha256'], 'source_hash': row['source_hash'],
                 'packet_row_canonical_sha256': canonical_sha(row),
                 'question_full_token_count': len(tok.encode(row['question'], add_special_tokens=False)),
                 'context_full_token_count': len(tok.encode(row['context'], add_special_tokens=False)),
                 'fixed_caps_not_answer_dependent': True}
        frame['frame_sha256'] = canonical_sha(frame)
        input_frames.append(frame)
    json_write(out / 'INPUT-FRAMES.json', {**identity, 'rows': input_frames})
    for identity_id in plan['parity_initial_ids']:
        i = byid[identity_id]
        with torch.no_grad():
            _, _, trace = graph(i)
            result = probe_decoder_parity(dec, packet(i, trace), tokens[i][-1],
                                          max_new_tokens=plan['parity_max_new_tokens'])
        json_write(out / ('PARITY-initial-%s.json' % identity_id), {**identity, 'id': identity_id, 'result': result})
    torch.cuda.reset_peak_memory_stats()
    probe_records = []
    for probe in range(16):
        torch.cuda.reset_peak_memory_stats()
        pp, aux, trace = graph(probe)
        ce, _ = human_loss(lm, pp, tokens[probe][-1], dec.bos_id, dec.eos_id, True, True)
        (ce.mean() + aux).backward()
        probe_records.append({'id': rows[probe]['id'],
            'question_token_count': tokens[probe][0].numel(),
            'notebook_token_count': tokens[probe][2].numel(),
            'target_with_EOS_token_count': tokens[probe][-1].numel(),
            'input_frame_sha256': input_frames[probe]['frame_sha256'],
            'peak_allocated_bytes': torch.cuda.max_memory_allocated(),
            'peak_reserved_bytes': torch.cuda.max_memory_reserved(), 'optimizer_updates': 0})
        for p in params:
            p.grad = None
        del pp, aux, trace, ce
        hooks.clear()
    reserved = max(record['peak_reserved_bytes'] for record in probe_records)
    cap = min(budget['peak_GPU_cap_bytes'], torch.cuda.get_device_properties(0).total_memory)
    memory_pass = reserved + 4 * param_bytes + 512 * 1024 ** 2 <= cap
    fp32_frozen = all(p.dtype == torch.float32 and not p.requires_grad for p in lm.parameters())
    json_write(out / 'MEMORY-PREFLIGHT.json', {**identity, 'optimizer_updates': 0,
               'probe_scope': 'ALL16 actual HUMAN input+target graphs',
               'per_row_actual_graph_probes': probe_records, 'peak_reserved_bytes': reserved,
               'trainable_parameter_bytes': param_bytes, 'Adam_margin_bytes_inferred': 4 * param_bytes,
               'safety_bytes': 512 * 1024 ** 2, 'cap_bytes': cap,
               'all_LM_FP32_frozen': fp32_frozen, 'guard_passed': memory_pass})
    if not memory_pass or not fp32_frozen or time.monotonic() - launched > budget['per_seed']['load_and_preflight_seconds']:
        raise RuntimeError('actual graph/preflight budget fails; no optimizer created')
    after_probes = {key: component_fingerprint(module) for key, module in
                    [('core', core), ('reader', reader), ('prefix', dec.adapter)]}
    lm_unchanged = component_fingerprint(lm) == before_lm
    gradients_cleared = all(p.grad is None for p in params) and all(p.grad is None for p in lm.parameters())
    torch.set_rng_state(initial_cpu_rng)
    torch.cuda.set_rng_state_all(initial_cuda_rng)
    if after_probes != initial or not lm_unchanged or not gradients_cleared:
        raise RuntimeError('zero-optimizer probes changed initial state or left gradients')
    json_write(out / 'PREFLIGHT-INVARIANTS.json', {**identity, 'optimizer_updates': 0,
        'core_reader_prefix_fingerprints_unchanged': True, 'LM_fingerprint_unchanged': lm_unchanged,
        'all_gradients_cleared': gradients_cleared, 'CPU_RNG_restored': bool(torch.equal(torch.get_rng_state(), initial_cpu_rng)),
        'CUDA_RNG_restored': all(torch.equal(a, b) for a, b in zip(torch.cuda.get_rng_state_all(), initial_cuda_rng)),
        'CPU_RNG_sha256': tensor_hash(initial_cpu_rng),
        'CUDA_RNG_sha256': [tensor_hash(state) for state in initial_cuda_rng]})
    frame_pins = {}

    @torch.no_grad()
    def diagnostic(update):
        nonlocal diag_elapsed
        start = time.monotonic()
        state_fingerprints = {key: component_fingerprint(module) for key, module in
                              [('core', core), ('reader', reader), ('prefix', dec.adapter)]}
        state_identity_sha256 = canonical_sha({'update': update, 'seed': args.seed,
                                               'fingerprints': state_fingerprints})
        full, empty, frames = [], [], []
        for i in range(16):
            _, _, trace = graph(i)
            full.append(packet(i, trace))
            raw = {key: trace[key].detach().cpu().contiguous() for key in ('final_query', 'pooled_prefix')}
            intermediate_summary = {key: {**tensor_hash(trace[key]), 'L2': float(trace[key].detach().float().norm())}
                                    for key in ('normalized_geometry', 'token_projected')}
            _, _, no_trace = graph(i, True)
            empty.append(packet(i, no_trace))
            raw['no_notebook_final_query'] = no_trace['final_query'].detach().cpu().contiguous()
            raw['answer_mask'] = tokens[i][1].cpu()
            raw['no_notebook_prefix'] = no_trace['pooled_prefix'].detach().cpu().contiguous()
            frames.append({'id': rows[i]['id'], 'tensors': raw,
                           'tensor_sha256': {key: tensor_hash(value) for key, value in raw.items()},
                           'redundant_intermediate_shape_hash_L2_only': intermediate_summary})
        size = sum(v.numel() * v.element_size() for f in frames for v in f['tensors'].values()) + 65536
        frame_path = out / ('frames-%06d.pt' % update)
        frame_pins[frame_path.name] = binary_save(frame_path, {'rows': frames, 'update': update,
                          **identity, 'model_state_fingerprints': state_fingerprints,
                          'model_state_identity_sha256': state_identity_sha256, '_estimated_bytes': size})
        if update == 0:
            # Row shapes and raw tensor storage are invariant across all four
            # stages. Extra64KiB per later file bounds metadata variation.
            projected = frame_path.stat().st_size * len(plan['diagnostic_updates']) + 65536 * (len(plan['diagnostic_updates']) - 1)
            json_write(out / 'FRAME-SIZE-PREFLIGHT.json', {**identity, 'optimizer_updates': 0,
                'initial_actual_serialized_frame_bytes': frame_path.stat().st_size,
                'planned_frame_files': len(plan['diagnostic_updates']),
                'projected_all_frame_bytes_with_metadata_margin': projected,
                'sealed_frame_cap_bytes': budget['binary_frame_cap_bytes_per_seed'],
                'guard_passed': projected <= budget['binary_frame_cap_bytes_per_seed']})
            if projected > budget['binary_frame_cap_bytes_per_seed']:
                raise RuntimeError('all four required frame files exceed sealed budget before optimizer')
        for i, row in enumerate(rows):
            donor_id = plan['latent_swap_donor_id'][row['id']]
            donor = byid[donor_id]
            controls = {'actual': (full[i], i), 'no_notebook': (empty[i], i),
                        'latent_swap_same_context': (full[donor], donor)}
            for name, (final, expected_i) in controls.items():
                # Decoder boundary receives FinalLatent only. Donor mask/shape
                # remain the donor's, even when paired question lengths differ.
                generated = dec.generate(final, max_tokens=plan['generation_max_new_tokens'])[0]
                expected = tokens[expected_i][-1][0].cpu().tolist()
                expected = expected[:-1] if expected and expected[-1] == dec.eos_id else expected
                labels = tokens[i][-1]
                prefix = dec.adapter(final)
                per, pred = human_loss(lm, prefix, labels, dec.bos_id, dec.eos_id, True, True)
                json_write(out / 'DIAGNOSTIC-RAW.jsonl', {**raw_identity, 'update': update,
                    'id': row['id'], 'control': name, 'expected_human_id': rows[expected_i]['id'],
                    'expected_human_answer_ids': expected, 'MODEL_generated_ids': generated,
                    'MODEL_generated_text_storage': 'omitted; exact IDs and pinned tokenizer retained',
                    'labels': labels.cpu().tolist(), 'label_mask': (labels != -100).cpu().tolist(),
                    'teacherforced_argmax': pred.cpu().tolist(), 'teacherforced_CE': per.cpu().tolist(),
                    'source_hash': row['source_hash'], 'input_frame_sha256': input_frames[i]['frame_sha256'],
                    'frames_file_sha256': frame_pins[frame_path.name],
                    'model_state_fingerprints': state_fingerprints,
                    'model_state_identity_sha256': state_identity_sha256,
                    'generated_outputs_never_training_labels': True}, append=True)
                if diag_elapsed + time.monotonic() - start > budget['per_seed']['all_diagnostics_seconds']:
                    raise RuntimeError('sealed total diagnostic time exceeded; preserve partial evidence')
        diag_elapsed += time.monotonic() - start
        for module in (core, reader, dec.adapter):
            module.train()

    diagnostic(0)
    # Bound the actual full Adam-state serialization before any optimizer exists.
    # This occupies the same resume path later atomically replaced by trained
    # state, rather than creating a second warmstart or LM copy.
    full_zero_adam_bound = {i: {'step': torch.tensor(0.0), 'exp_avg': torch.zeros_like(p),
                               'exp_avg_sq': torch.zeros_like(p)} for i, p in enumerate(params)}
    preflight_record = {**identity, 'optimizer_updates': 0,
        'core': core.state_dict(), 'reader': reader.state_dict(), 'prefix': dec.adapter.state_dict(),
        'full_zero_Adam_tensor_storage_bound': full_zero_adam_bound,
        'CPU_RNG': initial_cpu_rng, 'CUDA_RNG': initial_cuda_rng,
        'serialization_margin_bytes': budget['checkpoint_serialized_cap_bytes_per_seed'] - 3 * param_bytes}
    preflight_digest = binary_save(out / 'connected-resume.pt', preflight_record, checkpoint=True)
    json_write(out / 'SERIALIZATION-PREFLIGHT.json', {**identity, 'optimizer_updates': 0,
        'actual_serialized_full_storage_bound_bytes': (out / 'connected-resume.pt').stat().st_size,
        'serialized_sha256': preflight_digest,
        'cap_bytes': budget['checkpoint_serialized_cap_bytes_per_seed'],
        'includes_full_core_reader_prefix_and_two_Adam_moment_tensors_per_parameter': True,
        'actual_serialization_passed': True})
    del preflight_record, full_zero_adam_bound
    torch.set_rng_state(initial_cpu_rng)
    torch.cuda.set_rng_state_all(initial_cuda_rng)
    if any(p.grad is not None for p in params) or any(p.grad is not None for p in lm.parameters()):
        raise RuntimeError('initial diagnostic/preflight left gradients')
    if {key: component_fingerprint(module) for key, module in
        [('core', core), ('reader', reader), ('prefix', dec.adapter)]} != initial:
        raise RuntimeError('initial diagnostic/preflight changed warmstart tensors')
    if time.monotonic() - launched > budget['per_seed']['load_and_preflight_seconds'] + diag_elapsed:
        raise RuntimeError('pre-optimizer phase budget exceeded')
    # Conservative numeric record scaffolding estimates future raw storage.
    # It is never passed to the model or used as a label/training record.
    largest_finite_json = -1.7976931348623157e308
    def encoded_bytes(record):
        return len(json.dumps(record, ensure_ascii=False, allow_nan=False).encode('utf-8')) + 1
    raw_projection = raw_bytes()
    vocab_last = lm.get_input_embeddings().weight.shape[0] - 1
    for row_id in schedule:
        i = byid[row_id]
        label_values = tokens[i][-1].cpu().tolist()
        scaffold = {**raw_identity, 'update': 800, 'id': row_id, 'visit_for_row': 50,
            'schedule_sha256': plan['schedules'][str(args.seed)]['sha256'],
            'input_frame_sha256': input_frames[i]['frame_sha256'], 'human_field_sha256': rows[i]['field_sha256'],
            'labels': label_values, 'label_mask': (tokens[i][-1] != -100).cpu().tolist(),
            'teacherforced_argmax': [[vocab_last] * len(label_values[0])],
            'human_CE': largest_finite_json, 'auxiliary_separate': largest_finite_json,
            'total_preclip_norm': largest_finite_json,
            'CE_only_gradients': {name: {'CE_only_L2': largest_finite_json, 'tensors_with_grad': len(ps)}
                                  for name, ps in groups},
            'parameter_delta_L2_from_initial': {name: largest_finite_json for name, _ in groups}}
        scaffold['CE_only_gradients']['activations'] = {key: {'CE_only_L2': largest_finite_json, 'present': False}
             for key in ('final_query', 'normalized_geometry', 'token_projected', 'pooled_prefix')}
        raw_projection += encoded_bytes(scaffold)
    worst_diagnostic_bytes = 0
    for i, row in enumerate(rows):
        label_values = tokens[i][-1].cpu().tolist()
        expected_count = max(tokens[j][-1].numel() for j in (i, byid[plan['latent_swap_donor_id'][row['id']]]))
        scaffold = {**raw_identity, 'update': 800, 'id': row['id'], 'control': 'latent_swap_same_context',
            'expected_human_id': plan['latent_swap_donor_id'][row['id']],
            'expected_human_answer_ids': [vocab_last] * expected_count,
            'MODEL_generated_ids': [vocab_last] * plan['generation_max_new_tokens'],
            'MODEL_generated_text_storage': 'omitted; exact IDs and pinned tokenizer retained',
            'labels': label_values, 'label_mask': (tokens[i][-1] != -100).cpu().tolist(),
            'teacherforced_argmax': [[vocab_last] * len(label_values[0])],
            'teacherforced_CE': [largest_finite_json], 'source_hash': row['source_hash'],
            'input_frame_sha256': input_frames[i]['frame_sha256'], 'frames_file_sha256': '0' * 64,
            'model_state_fingerprints': {name: '0' * 64 for name, _ in groups},
            'model_state_identity_sha256': '0' * 64, 'generated_outputs_never_training_labels': True}
        worst_diagnostic_bytes = max(worst_diagnostic_bytes, encoded_bytes(scaffold))
    raw_projection += 16 * 3 * (len(plan['diagnostic_updates']) - 1) * worst_diagnostic_bytes + 65536
    json_write(out / 'RAW-SIZE-PREFLIGHT.json', {**identity, 'optimizer_updates': 0,
        'projected_all_raw_bytes_with_conservative_numeric_bound': raw_projection,
        'sealed_raw_cap_bytes': budget['raw_JSON_cap_bytes_per_seed'],
        'generated_text_omitted_exact_generated_IDs_preserved': True,
        'guard_passed': raw_projection <= budget['raw_JSON_cap_bytes_per_seed']})
    if raw_projection > budget['raw_JSON_cap_bytes_per_seed']:
        raise RuntimeError('all required raw evidence exceeds sealed budget before optimizer')
    opt = torch.optim.AdamW(params, lr=plan['lr'], weight_decay=plan['weight_decay'])
    visits = Counter()

    def norm(gradients):
        present = [g.detach().float().square().sum() for g in gradients if g is not None]
        return float(torch.sqrt(sum(present))) if present else 0.0

    for step, row_id in enumerate(schedule, 1):
        start = time.monotonic()
        i = byid[row_id]
        opt.zero_grad(set_to_none=True)
        hooks.clear()
        prefix, aux, activations = graph(i)
        labels = tokens[i][-1]
        per, pred = human_loss(lm, prefix, labels, dec.bos_id, dec.eos_id, True, True)
        ce = per.mean()
        gradient_raw = {}
        if step in plan['CE_gradient_capture_updates']:
            items = list(activations.items())
            grads = torch.autograd.grad(ce, params + [v for _, v in items], retain_graph=True, allow_unused=True)
            at = 0
            for name, ps in groups:
                gs = grads[at:at + len(ps)]
                gradient_raw[name] = {'CE_only_L2': norm(gs), 'tensors_with_grad': sum(g is not None for g in gs)}
                at += len(ps)
            gradient_raw['activations'] = {key: {'CE_only_L2': norm([g]), 'present': g is not None}
                                          for (key, _), g in zip(items, grads[len(params):])}
        loss = ce + aux
        if not bool(torch.isfinite(loss)):
            raise RuntimeError('nonfinite loss')
        loss.backward()
        preclip = torch.nn.utils.clip_grad_norm_(params, plan['clip_norm'], error_if_nonfinite=True)
        opt.step()
        updates = step
        visits[row_id] += 1
        if any(p.grad is not None for p in lm.parameters()):
            raise RuntimeError('frozen LM received gradients')
        json_write(out / 'TRAIN-RAW.jsonl', {**raw_identity, 'update': step, 'id': row_id,
            'visit_for_row': visits[row_id], 'schedule_sha256': plan['schedules'][str(args.seed)]['sha256'],
            'input_frame_sha256': input_frames[i]['frame_sha256'], 'human_field_sha256': rows[i]['field_sha256'],
            'labels': labels.cpu().tolist(), 'label_mask': (labels != -100).cpu().tolist(),
            'teacherforced_argmax': pred.cpu().tolist(), 'human_CE': float(ce.detach()),
            'auxiliary_separate': float(aux.detach()), 'total_preclip_norm': float(preclip),
            'CE_only_gradients': gradient_raw,
            'parameter_delta_L2_from_initial': {name: norm([p.detach().cpu() - v for p, v in zip(ps, initial_weights[name])])
                                               for name, ps in groups} if gradient_raw else None}, append=True)
        fit_elapsed += time.monotonic() - start
        if step in plan['diagnostic_updates']:
            diagnostic(step)
        if step in plan['checkpoint_updates']:
            state_fingerprints = {key: component_fingerprint(module) for key, module in
                                  [('core', core), ('reader', reader), ('prefix', dec.adapter)]}
            state_identity_sha256 = canonical_sha({'update': step, 'seed': args.seed,
                                                   'fingerprints': state_fingerprints})
            checkpoint = {**identity, 'arm': 'connected', 'update': step,
                'core': core.state_dict(), 'reader': reader.state_dict(), 'prefix': dec.adapter.state_dict(),
                'optimizer': opt.state_dict(), 'torch_rng': torch.get_rng_state(),
                'cuda_rng': torch.cuda.get_rng_state_all(), 'visits': dict(visits),
                'schedule_sha256': plan['schedules'][str(args.seed)]['sha256'],
                'raw_watermark_update': step, 'TRAIN_raw_sha256': sha(out / 'TRAIN-RAW.jsonl'),
                'frame_sha256': dict(frame_pins), 'activation_qualified': False,
                'model_state_fingerprints': state_fingerprints,
                'model_state_identity_sha256': state_identity_sha256}
            digest = binary_save(out / 'connected-resume.pt', checkpoint, checkpoint=True)
            json_write(out / ('CHECKPOINT-RECEIPT-%06d.json' % step), {**identity,
                'update': step, 'checkpoint_sha256': digest,
                'model_state_fingerprints': state_fingerprints,
                'model_state_identity_sha256': state_identity_sha256,
                'TRAIN_raw_sha256': checkpoint['TRAIN_raw_sha256'],
                'DIAGNOSTIC_raw_sha256_at_save': sha(out / 'DIAGNOSTIC-RAW.jsonl'),
                'raw_watermark_update': step, 'frame_sha256': dict(frame_pins),
                'activation_qualified': False})
            print(json.dumps({'status': 'DURABLE-TRAIN-DIAGNOSTIC', 'seed': args.seed,
                              'updates': step, 'sha256': digest, 'activation_qualified': False}), flush=True)
        if fit_elapsed > budget['per_seed']['fit_seconds'] or time.monotonic() - launched > budget['per_seed']['child_seconds']:
            raise RuntimeError('sealed fit/child budget exceeded; preserve partial evidence, no reduced schedule')
    for handle in handles:
        handle.remove()
    if visits != Counter({r['id']: 50 for r in rows}) or updates != 800:
        raise RuntimeError('requested exact exposure incomplete')
    if component_fingerprint(lm) != before_lm:
        raise RuntimeError('frozen LM changed')
    restored = torch.load(out / 'connected-resume.pt', map_location='cpu', weights_only=True)
    if restored['update'] != 800 or restored['visits'] != dict(visits) or restored['TRAIN_raw_sha256'] != sha(out / 'TRAIN-RAW.jsonl'):
        raise RuntimeError('durable final checkpoint/raw exposure binding mismatch')
    json_write(out / 'CLOSED.json', {**identity, 'closed': True, 'updates': updates,
        'visits': dict(visits), 'checkpoint_sha256': sha(out / 'connected-resume.pt'),
        'TRAIN_raw_sha256': sha(out / 'TRAIN-RAW.jsonl'), 'DIAGNOSTIC_raw_sha256': sha(out / 'DIAGNOSTIC-RAW.jsonl'),
        'frame_sha256': frame_pins, 'initial_fingerprints': initial,
        'final_fingerprints': {key: component_fingerprint(module) for key, module in
                               [('core', core), ('reader', reader), ('prefix', dec.adapter)]},
        'LM_unchanged': True, 'fit_seconds': fit_elapsed, 'diagnostic_seconds': diag_elapsed,
        'checkpoint_seconds': checkpoint_elapsed,
        'wall_seconds': time.monotonic() - launched, 'activation': False,
        'semantic_promotion': False, 'independent_saved_raw_recount': 'required, no model rescore'})


def supervise(args):
    """Own remote worker lifetime across load, generate, and file serialization.

    Mac SSH timeout is an additional bound.  This supervisor independently
    terminates only its own child process tree on Windows or Linux.
    """
    environment = dict(os.environ, SOL_EXPOSURE_SUPERVISOR_PID=str(os.getpid()))
    command = [sys.executable, '-X', 'utf8', '-B', str(Path(__file__).resolve()), *sys.argv[1:], '--worker']
    options = {'env': environment}
    if os.name == 'nt':
        options['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        options['start_new_session'] = True
    process = subprocess.Popen(command, **options)
    try:
        return process.wait(timeout=570)
    except subprocess.TimeoutExpired:
        if os.name == 'nt':
            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], check=True, timeout=10)
        else:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=10)
        print(json.dumps({'status': 'OWNED WORKER TIMEOUT, evidence preserved', 'owned_pid': process.pid,
                          'worker_seconds': 570, 'hard_outer_seconds': 600, 'activation': False}), flush=True)
        return 124


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', type=int, choices=(0, 1), required=True)
    parser.add_argument('--release', type=Path, required=True)
    parser.add_argument('--release-sha256', required=True)
    parser.add_argument('--inventory', type=Path, required=True)
    parser.add_argument('--inventory-sha256', required=True)
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        if args.worker:
            if os.environ.get('SOL_EXPOSURE_SUPERVISOR_PID') != str(os.getppid()):
                raise RuntimeError('worker must have the owned600second supervisor')
            run(args)
        else:
            raise SystemExit(supervise(args))
    except Exception as error:
        print(json.dumps({'status': 'FAILED OR HELD; evidence preserved', 'error_type': type(error).__name__,
                          'error': str(error), 'activation': False}), flush=True)
        raise
