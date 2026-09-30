"""Exact-tuple native-fixed4 safety receipt; no training or semantic assessment.

Numeric probes only. Does not load the LM, human rows, stop88, or any panel.
CPU is a bounded zero-update check; CUDA execution requires the watcher.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
import torch
from sol_spatial_poc_ordered_v2 import load_ordered_bundle
from sol_translator_grounding_v6 import HumanInputProjection
from sol_translator_english_v6 import StatePrefix
from scripts.sol_stop_adapter import FinalLatent, module_hash
from scripts.sol_stop_ordered_api2 import (
    ORDER_CONTRACT, make_ordered_fixed4_executor, ordered_attention_math)

VERSION = 'sol-stop-ordered-checkpoint-receipt-v1'
OWN = ROOT / 'artifacts/sol-stop-20260929'
API_SHA = '150290c3f2bc82d46cab91047c8e21879de2ddc231f44f06371148e1116e5238'
CORE_SHA = '5344e622855c875312f77a88095d287a5709e17dbaca23c90bdd8733b0a38291'


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def source_paths():
    paths = {str(Path(__file__).resolve())}
    for mod in tuple(sys.modules.values()):
        name = getattr(mod, '__file__', None)
        if name:
            p = Path(name).resolve()
            if p.is_relative_to(ROOT / 'scripts') and p.suffix == '.py':
                paths.add(str(p))
    return sorted(paths)


def verify(pins):
    for path, digest in pins.items():
        if sha(path) != digest:
            raise ValueError('file changed: ' + path)


def require(ok, name):
    if not ok:
        raise ValueError(name)


def finite_state(state):
    require(bool(state), 'empty state dict')
    for value in state.values():
        require(isinstance(value, torch.Tensor), 'non-tensor state entry')
        if value.is_floating_point():
            require(value.dtype == torch.float32 and bool(torch.isfinite(value).all()), 'nonfinite/non-FP32 weights')


def validate_tuple(core_meta, reader, prefix, digests):
    require(core_meta.get('input_version') == 'human-notebook-ordered-v10' and
            core_meta.get('order_contract') == ORDER_CONTRACT, 'ordered parent lineage')
    require(type(core_meta.get('updates')) is int and core_meta['updates'] > 0,
            'actual positive parent TRAIN updates required')
    if core_meta.get('stage') == 'ordered-night-candidate-unqualified':
        require(core_meta.get('overnight_updates') == 25, 'complete 25-update night candidate required')
    else:
        require(core_meta.get('stage') == 'human-grounded-ordered-unqualified' and
                core_meta['updates'] == 500, 'complete 500-update awake candidate required')
    require(reader.get('training_origin') == 'verified-human-origin' and
            reader.get('input_version') == 'human-notebook-ordered-v10' and
            reader.get('order_contract') == ORDER_CONTRACT, 'ordered reader lineage')
    require(prefix.get('training_origin') == 'verified-human-origin-verbatim' and
            prefix.get('source_state_contract') == 'sol-stop-FinalLatent-v1' and
            prefix.get('input_version') == 'human-notebook-ordered-v10' and
            prefix.get('order_contract') == ORDER_CONTRACT, 'ordered prefix lineage')
    require((prefix.get('state_width'), prefix.get('hidden'), prefix.get('prefix_tokens')) == (256, 32, 8),
            'thin prefix architecture')
    require(prefix.get('training_stage') in {
        'ordered-joint-grounding-unqualified', 'ordered-night-frozen-prefix-rebound-unqualified',
        'ordered-frozen-parent-decoder-proof-unqualified'}, 'prefix stage')
    for role in ('parent', 'reader'):
        require(prefix.get(role + '_sha256') == digests[role], 'prefix binding ' + role)
    require(prefix.get('lm_provenance_sha256') == digests['provenance'], 'LM provenance binding')
    manifest = core_meta.get('human_manifest_sha256')
    require(isinstance(manifest, str) and len(manifest) == 64 and
            manifest == reader.get('human_manifest_sha256') == prefix.get('human_manifest_sha256'),
            'human manifest mismatch')
    finite_state(reader['state_dict'])
    finite_state(prefix['adapter_state'])


@torch.no_grad()
def probe(core, reader, prefix, seed, device='cpu'):
    """Two fixed numeric draws, full physical cap and true prefix-padding trim."""
    checks = []
    def require(ok, name):
        if not ok:
            raise ValueError(name)
        checks.append(name)
    generator = torch.Generator(device='cpu').manual_seed(seed)
    qm = torch.ones(1, 49, dtype=torch.bool, device=device)
    mm = torch.ones(1, 512, dtype=torch.bool, device=device)
    if seed == 1:
        qm[:, 43:] = False
        mm[:, 479:] = False
    width = reader.proj[0].normalized_shape[0]
    lexical_q = torch.randn(1, 49, width, generator=generator).to(device)
    lexical_m = torch.randn(1, 512, width, generator=generator).to(device)
    query = reader(lexical_q, qm).flatten(1, 2)
    book = reader(lexical_m, mm).flatten(1, 2)
    qp = (torch.arange(49, device=device) * 2 + 1)[None]
    mp = (torch.arange(512, device=device) * 3 + 11)[None]
    kwargs = dict(query_mask=qm, notebook_mask=mm, query_positions=qp, notebook_positions=mp)
    core.eval()
    with ordered_attention_math():
        state = core.begin_latent(query.unsqueeze(1), book, **kwargs)
        initial = {k: state[k].detach().clone() for k in (
            'h', 'e', 'query_absolute_positions', 'notebook_absolute_positions', 'input_valid')}
        for round_number in range(1, 5):
            state = core.advance_latent(state)
            require(state['round'] == round_number, 'native round counter')
        native, _ = core.read_latent(state)
    require(torch.equal(initial['e'], state['e']), 'native immutable input changed')
    captured = []
    original_begin = core.begin_latent

    def capture(*args, **metadata):
        result = original_begin(*args, **metadata)
        captured.append({k: result[k].detach().clone() for k in initial})
        return result

    core.begin_latent = capture
    try:
        executor = make_ordered_fixed4_executor(core)
        runtime = executor.execute_embeddings(query, qm, (1, 49), notebook_latents=book, **kwargs)
        repeat = executor.execute_embeddings(query, qm, (1, 49), notebook_latents=book, **kwargs)
    finally:
        core.begin_latent = original_begin
    require(len(captured) == 2, 'runtime native begin must execute once per invocation')
    for k in initial:
        require(all(torch.equal(initial[k], seen[k]) for seen in captured), 'native begin mismatch: ' + k)
    require(type(runtime.final) is FinalLatent, 'canonical final class')
    require(torch.equal(native, runtime.final.latent), 'native final parity')
    require(torch.equal(runtime.final.latent, repeat.final.latent), 'repeat parity')
    require(runtime.audit.executed_batch_sizes == (1, 1, 1, 1) and
            runtime.audit.rounds.tolist() == [4] and not bool(runtime.audit.stopped.any()), 'actual fixed4 work')
    n = int(qm.sum())
    require(runtime.final.latent.shape == (1, n, 256) and runtime.final.token_shape == (1, n) and
            torch.equal(runtime.final.answer_mask, qm[:, :n]) and bool(runtime.final.latent_mask.all()),
            'query-only final shape/masks')
    require(not runtime.final.latent.requires_grad and bool(torch.isfinite(runtime.final.latent).all()), 'finite detached final')
    prefix_output = prefix(runtime.final)
    require(bool(torch.isfinite(prefix_output).all()) and prefix_output.shape == (1, 8, width), 'actual canonical prefix consumption')
    for extra in ({'cap': 5}, {'policy': 'learned'}):
        try:
            executor.execute_embeddings(query, qm, (1, 49), **extra)
        except (ValueError, TypeError):
            checks.append('reject ' + str(extra))
        else:
            raise ValueError('unsupported boundary accepted')
    # Padding/compaction control: same original positions, physically trimmed.
    m = int(mm.sum())
    trimmed = executor.execute_embeddings(query[:, :n], qm[:, :n], (1, n), notebook_latents=book[:, :m],
        query_mask=qm[:, :n], notebook_mask=mm[:, :m], query_positions=qp[:, :n], notebook_positions=mp[:, :m])
    require(torch.equal(runtime.final.latent, trimmed.final.latent), 'physical trim parity')
    permuted = book.clone()
    permuted[:, :m] = book[:, :m].flip(1)
    swapped = executor.execute_embeddings(query, qm, (1, 49), notebook_latents=permuted, **kwargs)
    delta = float((runtime.final.latent - swapped.final.latent).abs().max())
    raw = dict(numeric_lexical_query=lexical_q.cpu(), numeric_lexical_book=lexical_m.cpu(),
        projected_query=query.cpu(), projected_book=book.cpu(), query_mask=qm.cpu(), notebook_mask=mm.cpu(),
        query_positions=qp.cpu(), notebook_positions=mp.cpu(),
        native_begin={k: v.cpu() for k, v in initial.items()}, runtime_begin={k: v.cpu() for k, v in captured[0].items()},
        native_final=native.cpu(), runtime_final=runtime.final.latent.cpu(), repeat_final=repeat.final.latent.cpu(),
        final_answer_mask=runtime.final.answer_mask.cpu(), final_latent_mask=runtime.final.latent_mask.cpu(),
        trimmed_final=trimmed.final.latent.cpu(), permuted_final=swapped.final.latent.cpu(), prefix_output=prefix_output.cpu(),
        source_predictions=runtime.audit.predictions.cpu(), rounds=runtime.audit.rounds.cpu())
    record = dict(probe_seed=seed, row_id=f'numeric-probe-{seed}', labels=None,
        input_identity_sha256=hashlib.sha256(lexical_q.cpu().numpy().tobytes() + lexical_m.cpu().numpy().tobytes()).hexdigest(),
        query_valid=n, notebook_valid=m, native_begin_parity=True, native_state_parity=True,
        native_final_max_abs=0.0, repeat_max_abs=0.0, physical_trim_max_abs=0.0,
        notebook_permutation_max_abs=delta, executed_batch_sizes=[1, 1, 1, 1], rounds=[4],
        measured_work=runtime.audit.work,
        checks_passed=len(checks), checks=checks, semantic_qualification=False)
    return raw, record


def run(spec_path, output, device='cpu'):
    if device != 'cpu':
        require(bool(os.environ.get('JOB')) and os.environ.get('TREE') is not None,
                'CUDA checks require watcher JOB/TREE')
        require(Path(os.environ['TREE']).resolve() == ROOT, 'watcher tree mismatch')
    output = Path(output).resolve()
    require(output.is_relative_to(OWN.resolve()) and not output.exists(), 'NEW owned output directory required')
    spec = json.loads(Path(spec_path).read_text())
    require(spec['version'] == VERSION and spec['probe_seeds'] == [0, 1], 'predeclared version/two numeric seeds')
    pins = dict(spec['dependency_pins'])
    require(pins.get(str(ROOT / 'scripts/sol_stop_ordered_api2.py')) == API_SHA and
            pins.get(str(ROOT / 'scripts/sol_spatial_poc_ordered_v2.py')) == CORE_SHA, 'native API/core pins')
    require(set(source_paths()).issubset(pins), 'all imported project sources must be pinned')
    for role in ('parent', 'reader', 'prefix', 'provenance'):
        pins[spec[role]['path']] = spec[role]['sha256']
    pins[str(Path(spec_path).resolve())] = sha(spec_path)
    verify(pins)
    torch.set_num_threads(2)
    core, metadata = load_ordered_bundle(spec['parent']['path'], device)
    reader_raw = torch.load(spec['reader']['path'], map_location='cpu', weights_only=True)
    prefix_raw = torch.load(spec['prefix']['path'], map_location='cpu', weights_only=True)
    digests = {k: spec[k]['sha256'] for k in ('parent', 'reader', 'prefix', 'provenance')}
    validate_tuple(metadata, reader_raw, prefix_raw, digests)
    finite_state(core.state_dict())
    reader = HumanInputProjection(reader_raw['lm_width']).to(device).eval().requires_grad_(False)
    reader.load_state_dict(reader_raw['state_dict'], strict=True)
    prefix = StatePrefix(256, reader_raw['lm_width'], 32, 8).to(device).eval().requires_grad_(False)
    prefix.load_state_dict(prefix_raw['adapter_state'], strict=True)
    before = {k: module_hash(v) for k, v in (('core', core), ('reader', reader), ('prefix', prefix))}
    output.mkdir(parents=True, exist_ok=False)
    records = []
    started = time.monotonic()
    for seed in spec['probe_seeds']:
        raw, record = probe(core, reader, prefix, seed, device)
        identity = dict(version=VERSION, row_id=record['row_id'],
            numeric_input_sha256=record['input_identity_sha256'], component_sha256=digests,
            spec_sha256=sha(spec_path), dependency_pins=spec['dependency_pins'])
        record['bound_identity_sha256'] = hashlib.sha256(
            json.dumps(identity, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        raw['identity'] = identity
        raw['bound_identity_sha256'] = record['bound_identity_sha256']
        raw['labels'] = None  # Numeric execution probes have no human answer target.
        raw['row_id'] = record['row_id']
        raw_path = output / f'raw-probe-{seed}.pt'
        torch.save(raw, raw_path)
        record['raw_path'] = str(raw_path)
        record['raw_sha256'] = sha(raw_path)
        records.append(record)
    require(before == {k: module_hash(v) for k, v in (('core', core), ('reader', reader), ('prefix', prefix))}, 'component state mutation')
    require(set(source_paths()).issubset(pins), 'new unpinned source import during execution')
    verify(pins)
    receipt = dict(version=VERSION, execution_policy='native-fixed4', native_state_parity=True,
        **{k + '_sha256': v for k, v in digests.items()}, order_contract=ORDER_CONTRACT,
        checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        source_pins=pins, constructor=core.constructor(), device=device, torch_version=str(torch.__version__),
        wall_seconds=time.monotonic() - started, records=records, checks_passed=sum(r['checks_passed'] for r in records),
        numeric_probe_seeds=[0, 1], trained_seed=metadata.get('seed'),
        human_rows=0, stop88_reads=0, DEV_reads=0, optimizer_updates=0,
        measured_noise_provenance='exact repeat same frozen weights, two numeric seeds, same device/MATH; both max_abs=0',
        learned_stop_qualified=False, stage_proof_status='NOT SHOWN',
        scope='checkpoint-bound numeric fixed4 safety only; no English competence, learned stopping, rollback or sleep-gain acceptance')
    receipt_path = output / 'receipt.json'
    receipt_path.write_text(json.dumps(receipt, indent=2) + '\n')
    return {'receipt_path': str(receipt_path), 'receipt_sha256': sha(receipt_path), 'checks_passed': receipt['checks_passed']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--spec', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--device', default='cpu')
    args = parser.parse_args()
    print(json.dumps(run(args.spec, args.out, args.device)))
