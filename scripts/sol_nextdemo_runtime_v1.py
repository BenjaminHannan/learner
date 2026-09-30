"""Read-only development inference adapter; no optimizer, solver or activation.

Only the existing numeric-fit checkpoint schema is admitted. A future checkpoint
schema needs an explicit adapter revision, never a permissive fallback.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

PROTECTED = ('uncle-questions', 'readpanel320', 'sealed-panels', 'sealed-user',
             'sealed-blind', 'dev100', 'stop88', 'blind', 'reserved')
INTERVENTIONS = ('full', 'no_notebook', 'zero_final', 'reverse_final', 'reader_only')


def safe_path(path):
    p = Path(path)
    for candidate in (p, p.resolve()):
        parts = str(candidate).replace('\\', '/').lower().split('/')
        if any(term in part for part in parts for term in PROTECTED):
            raise ValueError('protected path refused before reading')
    return p.resolve()


def read_pinned(path, digest):
    if type(digest) is not str or not re.fullmatch('[0-9a-f]{64}', digest):
        raise ValueError('external SHA256 pin required')
    raw = safe_path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError('artifact SHA256 differs')
    return raw


def text_sha(text):
    return hashlib.sha256(text.encode('utf8')).hexdigest()


def validate_manifest(m):
    required = {'schema', 'runtime_root', 'checkpoint', 'seed', 'arm', 'update',
                'plan_sha256', 'seal_sha256', 'constructor', 'device', 'binding', 'code_pins'}
    if type(m) is not dict or set(m) != required:
        raise ValueError('exact inference manifest fields required')
    if m['schema'] != 'sol.nextdemo.numeric-inference.v1':
        raise ValueError('unsupported inference manifest')
    if type(m['seed']) is not int or m['seed'] not in (0, 1) or m['arm'] not in ('loop', 'plain'):
        raise ValueError('explicit seed and loop/plain arm required')
    if type(m['update']) is not int or m['update'] <= 0 or m['device'] not in ('cpu', 'cuda'):
        raise ValueError('closed update and explicit device required')
    if type(m['checkpoint']) is not dict or set(m['checkpoint']) != {'path', 'sha256'}:
        raise ValueError('checkpoint path and external hash required')
    for digest in (m['checkpoint']['sha256'], m['plan_sha256'], m['seal_sha256']):
        if type(digest) is not str or not re.fullmatch('[0-9a-f]{64}', digest):
            raise ValueError('exact digest required')
    if type(m['constructor']) is not dict or m['constructor'].get('family') != 'ordered-' + m['arm'] + '-D256-v2':
        raise ValueError('explicit ordered sparse constructor required')
    if type(m['binding']) is not dict or not {'connected_resume_path', 'connected_resume_sha256'}.issubset(m['binding']):
        raise ValueError('complete numeric-fit inherited binding required')
    if type(m['code_pins']) is not dict or set(m['code_pins']) != {
            'scripts/sol_cloud_numeric_fit_v2.py', 'scripts/sol_nextdemo_runtime_v1.py',
            'scripts/sol_nextdemo_dev_v1.py'}:
        raise ValueError('explicit new adapter/driver/observer code pins required')
    safe_path(m['runtime_root']); safe_path(m['checkpoint']['path'])
    return m


def validate_checkpoint(raw, manifest, binding):
    if type(raw) is not dict or raw.get('schema') != 'sol.cloud.numeric-fit.identity.v1':
        raise ValueError('unsupported checkpoint schema; no fallback')
    for key in ('seed', 'arm', 'update', 'plan_sha256', 'seal_sha256', 'constructor'):
        if raw.get(key) != manifest[key]:
            raise ValueError('checkpoint identity differs: ' + key)
    expected = manifest['binding']
    if (raw.get('binding') != expected or
            set(expected) != set(binding) | {'connected_resume_path', 'connected_resume_sha256'} or
            any(expected.get(k) != v for k, v in binding.items()) or
            not {'core', 'reader', 'prefix'}.issubset(raw) or 'table' in raw):
        raise ValueError('exact inherited component binding required; TABLE refused')
    if raw.get('sleep_enabled') is not False or raw.get('activation') is not False:
        raise ValueError('awake unactivated development checkpoint required')
    return raw


def check_lengths(tokenizer, question, context):
    if type(question) is not str or not question.strip() or type(context) is not str:
        raise ValueError('literal nonempty question and notebook text required')
    q = tokenizer.encode(question, add_special_tokens=False)
    c = tokenizer.encode(context, add_special_tokens=False)
    if not q or len(q) > 48 or len(c) > 512:
        raise ValueError('question48/notebook512 exceeded; truncation prohibited')
    return len(q), len(c)


def final_query(runtime, query, memo, valid, mvalid, intervention):
    """Native core needs [B,1,N,256]; only the exported query is flattened."""
    if query.ndim != 4 or query.shape[1] != 1 or query.shape[-1] != 256:
        raise ValueError('native ordered query shape required')
    if intervention == 'reader_only':
        return query.flatten(1, 2)
    with runtime['ordered_math']():
        latent, _, _ = runtime['fixed4'](runtime['core'], query, memo,
            query_mask=valid, notebook_mask=mvalid if memo is not None else None)
    return latent


class Runtime:
    def __init__(self, manifest_path, manifest_sha256):
        self.manifest = validate_manifest(json.loads(read_pinned(manifest_path, manifest_sha256)))
        m = self.manifest
        # Verify selected bytes before importing Torch or loading model components.
        checkpoint = read_pinned(m['checkpoint']['path'], m['checkpoint']['sha256'])
        import io
        import sys
        root = safe_path(m['runtime_root'])
        # Code imports are constrained to this checkout, rather than manifest paths.
        if root != Path(__file__).resolve().parents[1]:
            raise ValueError('runtime root must be this reviewed checkout')
        for relative, digest in m['code_pins'].items():
            read_pinned(root / relative, digest)
        sys.path[:0] = [str(root), str(root / 'scripts')]
        from sol_cloud_chat_nosleep_v1 import load_joined
        from sol_spatial_poc_ordered_v2 import OrderedPlainAttentionReasoner
        args = argparse.Namespace(runtime_root=root, seed=m['seed'], device=m['device'],
                                  connected_resume=None, connected_resume_sha256=None)
        self.r = load_joined(args)
        torch = self.r['torch']
        raw = validate_checkpoint(torch.load(io.BytesIO(checkpoint), map_location='cpu', weights_only=True), m, self.r['binding'])
        if m['arm'] == 'plain':
            self.r['core'] = OrderedPlainAttentionReasoner(self.r['core']).to(m['device'])
        if self.r['core'].constructor() != m['constructor']:
            raise ValueError('native constructor differs')
        for module, key in ((self.r['core'], 'core'), (self.r['reader'], 'reader'), (self.r['dec'].adapter, 'prefix')):
            if any(value.is_floating_point() and value.dtype != torch.float32 for value in raw[key].values()):
                raise ValueError('checkpoint floating state must already be FULL FP32')
            module.load_state_dict(raw[key], strict=True)
            module.eval().requires_grad_(False)
        for module in (self.r['core'], self.r['reader'], self.r['dec']):
            if any(p.is_floating_point() and p.dtype != torch.float32 for p in module.parameters()):
                raise ValueError('FULL FP32 required')

    def answer(self, question, context, intervention='full'):
        if intervention not in INTERVENTIONS:
            raise ValueError('unknown development intervention')
        r = self.r
        # Check the complete supplied context, including when a control removes it.
        counts = check_lengths(r['tok'], question, context)
        supplied_context = context
        if intervention == 'no_notebook':
            context = ''
        torch, device = r['torch'], r['device']
        from sol_cloud_numeric_fit_v2 import observe_generation
        with torch.no_grad():
            ids, valid, mids, mvalid = r['tokenize'](r['tok'], {'question': question, 'context': context}, device, max_question=48, max_context=512)
            query = r['reader'](r['dec'].lm.get_input_embeddings()(ids), valid)
            memo = r['reader'](r['dec'].lm.get_input_embeddings()(mids), mvalid).flatten(1, 2) if mids.shape[1] else None
            latent = final_query(r, query, memo, valid, mvalid, intervention)
            if intervention == 'zero_final':
                latent = torch.zeros_like(latent)
            elif intervention == 'reverse_final':
                latent = latent.flip(1)
            final = r['FinalLatent'](latent.detach(), torch.ones_like(latent, dtype=torch.bool), valid, (1, latent.shape[1]))
            observed = observe_generation(r['dec'], final, 32)
            if observed['generation_error']:
                raise RuntimeError('native generation failed: ' + str(observed['generation_error']))
            tokens = observed['MODEL_native_decoder_return'][0]
            text = r['tok'].decode(tokens, skip_special_tokens=True)
        return dict(text=text, observed=observed, intervention=intervention,
                    question_sha256=text_sha(question), supplied_context_sha256=text_sha(supplied_context),
                    context_sha256=text_sha(context), input_ids=ids.cpu().tolist(), input_mask=valid.cpu().tolist(),
                    notebook_ids=mids.cpu().tolist(), notebook_mask=mvalid.cpu().tolist(),
                    final_latent_sha256=hashlib.sha256(latent.detach().contiguous().cpu().numpy().tobytes()).hexdigest(),
                    checkpoint=self.manifest['checkpoint'], seed=self.manifest['seed'], arm=self.manifest['arm'],
                    rounds=0 if intervention == 'reader_only' else 4, decoder_input='FinalLatent only',
                    original_token_counts=counts, optimizer_updates=0, training_eligible=False,
                    behavioral_qualification=False, reasoner_specific_proof=False)
