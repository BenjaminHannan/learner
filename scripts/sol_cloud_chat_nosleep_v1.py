#!/usr/bin/env python3
"""Existing joined model chat. Sleep/training/activation are disabled."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

PLAN_REL = 'artifacts/sol-cloud-exposure16-20260930/r5/PLAN.json'
PLAN_SHA = '48c68acb57f6779f899e7d87faf9dee0f6504825758f276dc4b18706aea991d5'
SEAL_REL = 'artifacts/sol-cloud-exposure16-20260930/r5/SEAL.json'
SEAL_SHA = 'd8a50948c5c5831928fd3d68e2ed87f8620bbf3af0b5dbfa8efe27afde08a018'


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            digest.update(block)
    return digest.hexdigest()


def text_sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def admission(args):
    root = args.runtime_root.resolve()
    for relative, expected in [(PLAN_REL, PLAN_SHA), (SEAL_REL, SEAL_SHA)]:
        if sha(root / relative) != expected:
            raise ValueError('existing joined metadata pin differs: ' + relative)
    plan = json.loads((root / PLAN_REL).read_bytes())
    seal = json.loads((root / SEAL_REL).read_bytes())
    # Hash code only, never decode legacy mixed/raw corpus or documents.
    for relative, expected in seal['files'].items():
        if relative.startswith('scripts/') and sha(root / relative) != expected:
            raise ValueError('existing runtime source pin differs: ' + relative)
    binding = plan['warmstart']['tuples'][str(args.seed)]
    for component in ('parent', 'reader', 'adapter'):
        if sha(binding[component + '_path']) != binding[component + '_sha256']:
            raise ValueError('existing V11 base tuple pin differs: ' + component)
    if sha(binding['lm_provenance']) != plan['LM_provenance']['sha256']:
        raise ValueError('frozen local LM provenance differs')
    if bool(args.connected_resume) != bool(args.connected_resume_sha256):
        raise ValueError('connected resume path and SHA are both required')
    if args.connected_resume and sha(args.connected_resume) != args.connected_resume_sha256:
        raise ValueError('selected connected checkpoint differs')
    return root, plan, binding


def validate_connected(raw, seed, binding):
    if (type(raw) is not dict or raw.get('arm') != 'connected' or raw.get('seed') != seed
            or raw.get('update') != 200 or not isinstance(raw.get('binding'), dict)
            or any(raw['binding'].get(key) != binding.get(key) for key in ('parent_sha256', 'reader_sha256', 'adapter_sha256', 'order_contract', 'lm_path'))
            or not {'core', 'reader', 'prefix'}.issubset(raw) or 'table' in raw):
        raise ValueError('exact V12 connected200 joined checkpoint required; TABLE rejected')
    return raw


def load_joined(args):
    admission_start = time.perf_counter()
    root, plan, binding = admission(args)
    admission_seconds = time.perf_counter() - admission_start
    started = time.perf_counter()
    sys.path[:0] = [str(root), str(root / 'scripts')]
    os.environ.setdefault('HF_HUB_OFFLINE', '1')
    os.environ.setdefault('TRANSFORMERS_OFFLINE', '1')
    import torch
    from sol_translator_grounding_v6 import HumanInputProjection, question_notebook_tokens
    from sol_translator_english_ordered_v10 import load_ordered_english
    from sol_spatial_poc_ordered_v2 import load_ordered_bundle
    from sol_spatial_poc_ordered_train_api_v2 import fixed4_training
    from scripts.sol_stop_ordered_api2 import ordered_attention_math
    from sol_translator_decoder import FinalLatent
    torch.set_num_threads(2)
    device = args.device
    if device == 'cuda' and not torch.cuda.is_available():
        raise RuntimeError('selected CUDA device unavailable')
    prefix_metadata = torch.load(binding['adapter_path'], map_location='cpu', weights_only=True)
    if (prefix_metadata.get('parent_sha256') != binding['parent_sha256']
            or prefix_metadata.get('reader_sha256') != binding['reader_sha256']):
        raise ValueError('base English prefix does not bind the admitted core and reader')
    del prefix_metadata
    dec, tok, _ = load_ordered_english(binding['lm_path'], binding['lm_provenance'], binding['adapter_path'], device)
    core, _ = load_ordered_bundle(binding['parent_path'], device)
    rraw = torch.load(binding['reader_path'], map_location='cpu', weights_only=True)
    reader = HumanInputProjection(rraw['lm_width']).to(device)
    reader.load_state_dict(rraw['state_dict'], strict=True)
    if args.connected_resume:
        raw = validate_connected(torch.load(args.connected_resume, map_location='cpu', weights_only=True), args.seed, binding)
        core.load_state_dict(raw['core'], strict=True)
        reader.load_state_dict(raw['reader'], strict=True)
        dec.adapter.load_state_dict(raw['prefix'], strict=True)
        del raw
    for module in (core, reader, dec):
        module.eval().requires_grad_(False)
        if any(p.is_floating_point() and p.dtype != torch.float32 for p in module.parameters()):
            raise ValueError('existing joined components must remain FULL FP32')
    if device == 'cuda':
        torch.cuda.synchronize()
    return {'root': root, 'plan': plan, 'binding': binding, 'torch': torch, 'core': core,
            'reader': reader, 'dec': dec, 'tok': tok, 'tokenize': question_notebook_tokens,
            'fixed4': fixed4_training, 'ordered_math': ordered_attention_math, 'FinalLatent': FinalLatent,
            'device': device, 'cold_load_seconds': time.perf_counter() - started,
            'admission_seconds': admission_seconds, 'request_count': 0,
            'LM_dtype': str(next(dec.lm.parameters()).dtype),
            'gpu': torch.cuda.get_device_name(0) if device == 'cuda' else None,
            'checkpoint_family': 'V12-connected200-HUMAN-TRAIN-memorization-only' if args.connected_resume else 'V11-closed200-known-unqualified-fallback'}


def answer(runtime, question, context, max_new_tokens=32, input_identity=None):
    if not isinstance(question, str) or not question.strip() or not isinstance(context, str):
        raise ValueError('nonempty question and optional text context required')
    if not 1 <= max_new_tokens <= 32:
        raise ValueError('max new tokens must be within1..32')
    torch, device = runtime['torch'], runtime['device']
    runtime['request_count'] += 1
    sync = torch.cuda.synchronize if device == 'cuda' else lambda: None
    sync(); whole = time.perf_counter()
    with torch.no_grad():
        ids, valid, mids, mvalid = runtime['tokenize'](runtime['tok'], {'question': question, 'context': context}, device, max_question=48, max_context=512)
        qe = runtime['dec'].lm.get_input_embeddings()(ids)
        query = runtime['reader'](qe, valid)
        notebook = None
        notebook_mask = None
        if mids.shape[1]:
            notebook = runtime['reader'](runtime['dec'].lm.get_input_embeddings()(mids), mvalid).flatten(1, 2)
            notebook_mask = mvalid
        sync(); core_start = time.perf_counter()
        with runtime['ordered_math']():
            latent, _, _ = runtime['fixed4'](runtime['core'], query, notebook, query_mask=valid, notebook_mask=notebook_mask)
        sync(); core_seconds = time.perf_counter() - core_start
        final = runtime['FinalLatent'](latent.detach(), torch.ones_like(latent, dtype=torch.bool), valid, (1, latent.shape[1]))
        sync(); generation_start = time.perf_counter()
        # The talker receives ONLY FinalLatent, never question/context/targets.
        generated = runtime['dec'].generate(final, max_tokens=max_new_tokens)[0]
        sync(); generation_seconds = time.perf_counter() - generation_start
        generated_text = runtime['tok'].decode(generated, skip_special_tokens=True)
    sync()
    return {'schema': 'sol.cloud.chat.no-sleep.answer.v1', 'MODEL_generated_text': generated_text,
            'MODEL_generated_ids': generated, 'generated_token_count': len(generated), 'batch': 1,
            'token_count_scope': 'returned non-EOS IDs; decoder strips EOS',
            'returned_non_EOS_tokens_per_generation_second': len(generated) / generation_seconds if generation_seconds else None,
            'request_index': runtime['request_count'], 'request_phase': 'first request' if runtime['request_count'] == 1 else 'warm request',
            'question_sha256': text_sha(question), 'context_sha256': text_sha(context),
            'input_identity': input_identity, 'input_ids': ids.cpu().tolist(), 'input_mask': valid.cpu().tolist(),
            'notebook_ids': mids.cpu().tolist(), 'notebook_mask': mvalid.cpu().tolist(),
            'core_seconds_synchronized': core_seconds, 'generation_seconds_synchronized': generation_seconds,
            'whole_answer_seconds_synchronized': time.perf_counter() - whole,
            'cold_model_load_seconds_separate': runtime['cold_load_seconds'], 'first_token_seconds': None,
            'source_checkpoint_admission_seconds_separate': runtime['admission_seconds'],
            'first_token_measurement': 'not instrumented', 'gpu_identity': runtime['gpu'], 'LM_dtype': runtime['LM_dtype'], 'all_components_FP32_checked': True,
            'checkpoint_family': runtime['checkpoint_family'], 'fixed_rounds': 4,
            'sleep_enabled': False, 'optimizer_updates': 0, 'training_eligible': False, 'activation': False,
            'semantic_qualified': False, 'generated_outputs_never_training_material': True}


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--runtime-root', type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument('--seed', type=int, choices=(0, 1), default=0)
    p.add_argument('--device', choices=('cuda', 'cpu'), default='cuda')
    p.add_argument('--connected-resume', type=Path)
    p.add_argument('--connected-resume-sha256')
    choice = p.add_mutually_exclusive_group()
    choice.add_argument('--once', help='Ask one question, emit one JSON answer and exit.')
    choice.add_argument('--train-id', action='append', help='Already released TRAIN identity; repeat for same-model queued smoke.')
    p.add_argument('--context', default='', help='Optional context supplied only to the core notebook.')
    p.add_argument('--max-new-tokens', type=int, default=32)
    p.add_argument('--verify-only', action='store_true', help='Hash admission only; no model load.')
    return p


def main():
    args = parser().parse_args()
    if args.verify_only:
        root, plan, binding = admission(args)
        print(json.dumps({'verified': True, 'seed': args.seed, 'sleep_enabled': False, 'optimizer_updates': 0, 'model_calls': 0}))
        return
    runtime = load_joined(args)
    provenance = {'CLI_sha256': sha(Path(__file__)), 'plan_sha256': PLAN_SHA, 'seal_sha256': SEAL_SHA,
                  'seed': args.seed, 'base_tuple_sha256': {k: runtime['binding'][k + '_sha256'] for k in ('parent', 'reader', 'adapter')},
                  'connected_checkpoint_sha256': args.connected_resume_sha256}
    def emit(question, context, identity=None, human_readable=False):
        record = answer(runtime, question, context, args.max_new_tokens, identity)
        print(record['MODEL_generated_text'] if human_readable else json.dumps({**record, **provenance}, ensure_ascii=False, allow_nan=False), flush=True)
    if args.train_id:
        from sol_cloud_trainonly_v1 import load_packet
        source = runtime['plan']['source']
        rows = load_packet(runtime['root'] / source['packet']['path'], source['packet']['sha256'], manifest_path=runtime['root'] / source['manifest']['path'], manifest_sha256=source['manifest']['sha256'])
        by_id = {row['id']: row for row in rows}
        for identity in args.train_id:
            selected = by_id.get(identity)
            if selected is None or identity not in runtime['plan']['TRAIN_ids']:
                raise ValueError('smoke identity outside sixteen already released HUMAN TRAIN rows')
            emit(selected['question'], selected['context'], selected['id'])
    elif args.once is not None:
        emit(args.once, args.context)
    else:
        print('Sleep disabled. Type /quit to exit.', file=sys.stderr, flush=True)
        while True:
            try:
                question = input('Question: ')
            except (EOFError, KeyboardInterrupt):
                break
            if question.strip() == '/quit':
                break
            if question.strip():
                emit(question, args.context, human_readable=True)


if __name__ == '__main__':
    main()
