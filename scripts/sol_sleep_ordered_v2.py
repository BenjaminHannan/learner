#!/usr/bin/env python3
"""Actual ordered-core overnight updates; queue-only, versioned candidate/rollback.

Uses literal verified HUMAN TRAIN data. It never learns model output. Open TRAIN
guards support an engineering decision only, not unseen improvement or retention
proof. The exact awake bundle and native fixed-four-round safety receipt must be
pinned before this job is sealed. No learned-stop qualification is implied.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import random
import signal
import time

ROOT = Path(__file__).resolve().parents[1]
OWN = ROOT / 'artifacts/sol-compose-20260929/ordered-night-v2'
VERSION = 'sol-ordered-night-v2'


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def write(path, value):
    path = Path(path)
    tmp = path.with_suffix(path.suffix + '.tmp')
    with tmp.open('w', encoding='utf8') as f:
        f.write(json.dumps(value, indent=2) + '\n')
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def guard_decision(before, after, repeat_noise):
    """Pure offline decision over persisted records; no inference or fitting."""
    if [r['id'] for r in before] != [r['id'] for r in after] or not before:
        raise ValueError('guard identities changed or empty')
    import math
    if not math.isfinite(repeat_noise) or repeat_noise < 0:
        raise ValueError('invalid measured repeat noise')
    for a, b in zip(before, after):
        for key in ('labels', 'label_mask', 'input_identity_sha256'):
            if a[key] != b[key]:
                raise ValueError('guard input/label/mask changed: ' + key)
        if not math.isfinite(a['CE']) or not math.isfinite(b['CE']):
            return {'pass': False, 'reason': 'nonfinite guard CE'}
    prior_mean = sum(r['CE'] for r in before) / len(before)
    new_mean = sum(r['CE'] for r in after) / len(after)
    lost = [a['id'] for a, b in zip(before, after)
            if exact_sentence(a) and not exact_sentence(b)]
    tolerance = 2 * repeat_noise + 1e-6
    return {'pass': not lost and new_mean <= prior_mean + tolerance,
            'reason': 'open-TRAIN mean CE and prior exact HUMAN sentence guard',
            'before_mean_CE': prior_mean, 'after_mean_CE': new_mean,
            'repeat_CE_noise_measured': repeat_noise,
            'CE_tolerance': tolerance, 'lost_prior_exact_ids': lost,
            'scope': 'engineering guard; unseen retention/improvement NOT SHOWN'}


def exact_sentence(record):
    """Recount generated token IDs against masked HUMAN labels, no saved flag."""
    if len(record['labels']) != 1 or len(record['label_mask']) != 1:
        raise ValueError('one physically sliced guard row required')
    labels, mask = record['labels'][0], record['label_mask'][0]
    if len(labels) != len(mask):
        raise ValueError('label/mask lengths differ')
    expected = [x for x, valid in zip(labels, mask) if valid]
    if expected and expected[-1] == record['eos_token_id']:
        expected = expected[:-1]
    return record['generated_ids'] == expected


def verify_files(pins):
    for path, expected in pins.items():
        if sha(path) != expected:
            raise ValueError('immutable dependency changed: ' + path)


def validate_guard_rows(rows, expected_ids):
    if len(expected_ids) != 8 or len(set(expected_ids)) != 8 or [r['id'] for r in rows] != expected_ids:
        raise ValueError('exact eight presealed guard identities required')
    for row in rows:
        if len(row['labels']) != 1 or len(row['label_mask']) != 1:
            raise ValueError('one label/mask row required')
        labels, mask = row['labels'][0], row['label_mask'][0]
        if len(labels) != len(mask) or not labels or not any(x != -100 for x in labels):
            raise ValueError('nonempty aligned target required')
        if any(type(x) is not int or type(m) is not bool or m != (x != -100) for x,m in zip(labels,mask)):
            raise ValueError('label mask must exactly equal target != -100')
        account = {k: row[k] for k in ('input_ids', 'input_mask', 'notebook_ids', 'notebook_mask')}
        digest = hashlib.sha256(json.dumps(account, sort_keys=True).encode()).hexdigest()
        if digest != row['input_identity_sha256']:
            raise ValueError('guard input bytes differ from identity')
        for ids, mask in [('input_ids', 'input_mask'), ('notebook_ids', 'notebook_mask')]:
            if len(row[ids]) != len(row[mask]) or any(len(a) != len(b) for a,b in zip(row[ids], row[mask])):
                raise ValueError('input mask shape differs')


def check_decision(path, previous_pin, candidate_pin):
    """Assistant pointer callback. Caller independently pins decision SHA.

    Recounts persisted guard records, checks all bound source/candidate bytes.
    Does not accept an author Boolean as a safety or scientific certificate.
    """
    d = read(path)
    if d['version'] != VERSION or d['previous_bundle_pin'] != previous_pin:
        raise ValueError('wrong decision version or previous bundle')
    if d['candidate_bundle_pin'] != candidate_pin or sha(d['candidate_manifest']) != candidate_pin:
        raise ValueError('candidate manifest pin changed')
    verify_files(d['dependency_pins'])
    verify_files(d['candidate_files'])
    before, after, ledger = read(d['before_raw']), read(d['after_raw']), read(d['ledger'])
    repeat, plan = read(d['repeat_raw']), read(d['plan'])
    if d['dependency_pins'].get(d['plan']) != d['plan_sha256'] or sha(d['plan']) != d['plan_sha256']:
        raise ValueError('guard plan pin changed')
    for rows in (before, repeat, after):
        validate_guard_rows(rows, plan['guard_ids'])
    guard_decision(before, repeat, 0.0)  # validates matching inputs/labels and finite CE
    import math
    if any(not math.isfinite(r['CE']) for r in before + repeat + after):
        raise ValueError('nonfinite guard CE')
    measured_noise = abs(sum(r['CE'] for r in repeat)/len(repeat) - sum(r['CE'] for r in before)/len(before))
    if measured_noise != d['repeat_CE_noise_measured']:
        raise ValueError('declared noise differs from pinned repeated raw measurement')
    for key, source in [('before_raw_sha256', d['before_raw']),
                        ('after_raw_sha256', d['after_raw']), ('repeat_raw_sha256', d['repeat_raw']), ('ledger_sha256', d['ledger'])]:
        if sha(source) != d[key]:
            raise ValueError('raw decision evidence changed')
    if not ledger['closed'] or ledger['updates'] != 25 or ledger['core_before'] == ledger['core_after']:
        raise ValueError('no complete changed-core overnight checkpoint')
    if not ledger.get('checkpoint_reload_exact') or not ledger.get('populated_Adam_reload_exact'):
        raise ValueError('saved candidate/optimizer reload not verified')
    if ledger['optimizer_scope'] != 'ordered core ONLY; halt frozen':
        raise ValueError('wrong overnight optimizer scope')
    if ledger['model_authored_targets'] or ledger['DEV_model_calls'] or ledger['learned_stop_qualified']:
        raise ValueError('invalid provenance or implied learned-stop qualification')
    if ledger.get('actual_day_experience'):
        batch_path = d['day_batch']
        batch_sha = ledger['day_batch_sha256']
        if d['dependency_pins'].get(batch_path) != batch_sha:
            raise ValueError('day snapshot not pinned')
        module = importlib.import_module(d['day_adapter_module'])
        if d['dependency_pins'].get(str(Path(module.__file__).resolve())) != sha(module.__file__):
            raise ValueError('day verifier source not pinned')
        if read(batch_path)['bundle']['sha256'] != previous_pin:
            raise ValueError('day source bundle differs')
        rows = module.load_rows(batch_path, batch_sha)
        if [r['id'] for r in rows] != ledger['experience_ids'] or sorted(set(r['origin'] for r in rows)) != ledger['experience_origins']:
            raise ValueError('day provenance/ledger mismatch')
    decision = guard_decision(before, after, measured_noise)
    if not decision['pass'] or not d['activation_eligible']:
        raise ValueError('candidate must roll back')
    return True


def run(a):
    import torch
    if not os.environ.get('JOB') or Path(os.environ.get('TREE', '')).resolve() != ROOT.resolve():
        raise RuntimeError('watcher JOB and exact TREE required; no direct training')
    binding = read(a.binding)
    plan = read(a.plan)
    if plan['version'] != VERSION or plan['updates'] != 25 or plan['batch'] != 2:
        raise ValueError('new seal required for changed overnight budget')
    if plan['source_seeds'] != [0, 1] or a.seed not in plan['source_seeds']:
        raise ValueError('both presealed source seeds required')
    if plan['fixed_rounds'] != 4 or plan['context_cap'] != 512:
        raise ValueError('fixed4/ordered512 engineering contract required')
    if sha(a.plan) != binding['plan_sha256'] or sha(__file__) != binding['driver_sha256']:
        raise ValueError('night plan/driver pin changed')
    verify_files(binding['dependency_pins'])
    s = binding['seeds'][str(a.seed)]
    verify_files({s[k]['path']: s[k]['sha256'] for k in ('parent', 'reader', 'prefix', 'provenance')})
    # Native fixed4 checks anchor the exact new checkpoint; source gates cannot transfer.
    verify_files({s['awake_safety_receipt']['path']: s['awake_safety_receipt']['sha256']})
    safe = read(s['awake_safety_receipt']['path'])
    if (safe['execution_policy'] != 'native-fixed4' or not safe['native_state_parity']
            or safe['parent_sha256'] != s['parent']['sha256']
            or safe['reader_sha256'] != s['reader']['sha256']
            or safe['prefix_sha256'] != s['prefix']['sha256']):
        raise ValueError('exact awake native fixed4 safety receipt absent')
    out = Path(a.out).resolve()
    if not out.is_relative_to(OWN.resolve()) or out.exists():
        raise ValueError('NEW own output directory only; no silent resume/rerun')
    out.mkdir(parents=True)
    import shutil
    if shutil.disk_usage(out).free < plan['disk_floor_bytes']:
        raise RuntimeError('night disk floor')
    torch.set_num_threads(2)
    torch.manual_seed(2026093000 + a.seed)
    ordered = importlib.import_module(binding['ordered_module'])
    graph = importlib.import_module(binding['graph_module'])
    native = importlib.import_module(binding['native_module'])
    from sol_translator_grounding_v6 import (HumanInputProjection, human_rows,
                                            question_notebook_tokens, target_tokens)
    from sol_translator_english_v6 import FrozenEnglishDecoder, load_local_lm
    from sol_translator_runtime import component_fingerprint
    from scripts.sol_stop_adapter import FinalLatent
    lm, tok, _ = load_local_lm(s['model_path'], s['provenance']['path'], a.device)
    core, meta = ordered.load_ordered_bundle(s['parent']['path'], a.device)
    if core.constructor()['notebook_cap'] != 512:
        raise ValueError('ordered512 constructor required')
    reader_raw = torch.load(s['reader']['path'], map_location='cpu', weights_only=True)
    reader = HumanInputProjection(reader_raw['lm_width']).to(a.device)
    reader.load_state_dict(reader_raw['state_dict'])
    prefix_raw = torch.load(s['prefix']['path'], map_location='cpu', weights_only=True)
    if (prefix_raw['parent_sha256'] != s['parent']['sha256']
            or prefix_raw['reader_sha256'] != s['reader']['sha256']
            or prefix_raw['training_origin'] != 'verified-human-origin-verbatim'):
        raise ValueError('awake prefix binding/origin')
    decoder = FrozenEnglishDecoder(lm, 256, tok.bos_token_id, tok.eos_token_id,
                                   hidden=32, prefix_tokens=8).to(a.device)
    decoder.adapter.load_state_dict(prefix_raw['adapter_state'])
    reader.eval().requires_grad_(False)
    decoder.adapter.eval().requires_grad_(False)
    rows, _ = human_rows(binding['corpus'])
    train = {r['id']: r for r in rows if r['split'] == 'train'}
    groups = {name: [train[i] for i in plan[name + '_ids']]
              for name in ('experience', 'replay', 'guard')}
    idsets = [set(plan[name + '_ids']) for name in ('experience', 'replay', 'guard')]
    if any(idsets[i] & idsets[j] for i in range(3) for j in range(i)):
        raise ValueError('experience/replay/guard must be disjoint open TRAIN identities')
    day_pins = {}
    day_rows = None
    if bool(a.day_batch) != bool(a.day_batch_sha256):
        raise ValueError('day batch requires exact external digest')
    if a.day_batch:
        day_module = importlib.import_module(binding['day_adapter_module'])
        if binding['dependency_pins'].get(str(Path(day_module.__file__).resolve())) != sha(day_module.__file__):
            raise ValueError('day adapter source not pinned')
        batch_manifest = read(a.day_batch)
        if batch_manifest['bundle']['sha256'] != s['previous_bundle_pin']:
            raise ValueError('day snapshot belongs to different awake bundle')
        day_rows = day_module.load_rows(a.day_batch, a.day_batch_sha256)
        if not day_rows:
            raise ValueError('no admitted real day experience')
        for row in day_rows:
            if row['origin'] not in ('human-preferred-response-not-factual-certificate', 'verified-symbolic-numeric-execution'):
                raise ValueError('unadmitted day training origin')
            for key, cap in [('question',48), ('context',512), ('target_text',63)]:
                if len(tok.encode(row[key], add_special_tokens=False)) > cap:
                    raise ValueError('day token cap exceeded; no truncation or drop')
        if set(r['id'] for r in day_rows) & (idsets[1] | idsets[2]):
            raise ValueError('day/replay/guard identity overlap')
        def signature(row):
            return tuple(tuple(tok.encode(row[k], add_special_tokens=False)) for k in ('question','context','target_text'))
        protected = {signature(r) for r in groups['replay'] + groups['guard']}
        if any(signature(r) in protected for r in day_rows):
            raise ValueError('day content overlaps pinned replay/guard')
        groups['experience'] = day_rows
        day_pins[a.day_batch] = a.day_batch_sha256
    if reader_raw['human_manifest_sha256'] != sha(Path(binding['corpus']) / 'pairs.json'):
        raise ValueError('human corpus changed')
    frozen = {name: component_fingerprint(m) for name, m in
              [('LM', lm), ('reader', reader), ('prefix', decoder.adapter)]}
    before_core = component_fingerprint(core)
    cancelled = [False]
    signal.signal(signal.SIGTERM, lambda *_: cancelled.__setitem__(0, True))
    signal.signal(signal.SIGINT, lambda *_: cancelled.__setitem__(0, True))
    start = time.monotonic()

    def row_loss(row):
        ids, valid, mids, mvalid = question_notebook_tokens(tok, row, a.device, max_context=512)
        targets = target_tokens(tok, [row], a.device)
        loss, raw = graph.row_graph(lm, core, reader, decoder, ids, valid, mids, mvalid, targets)
        account = {'input_ids': ids.cpu().tolist(), 'input_mask': valid.cpu().tolist(),
                   'notebook_ids': mids.cpu().tolist(), 'notebook_mask': mvalid.cpu().tolist()}
        record = {**account, 'id': row['id'], 'split': 'open-HUMAN-TRAIN-night-engineering',
                  'labels': targets.cpu().tolist(), 'label_mask': (targets != -100).cpu().tolist(),
                  'predictions': raw['predictions'], 'CE': raw['human_CE_per_example'][0],
                  'eos_token_id': tok.eos_token_id,
                  'round': 4, 'binding_sha256': sha(a.binding), 'source_sha256': row['source_sha256'],
                  'input_identity_sha256': hashlib.sha256(json.dumps(account, sort_keys=True).encode()).hexdigest()}
        return loss, record, (ids, valid, mids, mvalid)

    @torch.no_grad()
    def guards():
        core.eval()
        result = []
        for row in groups['guard']:
            _, record, (ids, valid, mids, mvalid) = row_loss(row)
            query = reader(lm.get_input_embeddings()(ids), valid)
            memo = reader(lm.get_input_embeddings()(mids), mvalid).flatten(1, 2)
            with native.ordered_attention_math():
                state = core.begin_latent(query, memo, query_mask=valid, notebook_mask=mvalid)
                for _ in range(4):
                    state = core.advance_latent(state)
                h, _ = core.read_latent(state)
            packet = FinalLatent(h, torch.ones_like(h, dtype=torch.bool), valid, (1, h.shape[1]))
            tokens = decoder.generate(packet, max_tokens=64)[0]
            text = tok.decode(tokens, skip_special_tokens=True)
            record.update(generated_ids=tokens, generated_text_MODEL_LOG_ONLY=text,
                          human_target=row['target_text'])
            record['full_human_sentence_exact'] = exact_sentence(record)
            result.append(record)
        return result

    before = guards()
    repeat = guards()
    repeat_noise = abs(sum(r['CE'] for r in repeat) / len(repeat)
                       - sum(r['CE'] for r in before) / len(before))
    write(out / 'guard-before.json', before)
    write(out / 'guard-before-repeat.json', repeat)
    core.train().requires_grad_(True)
    for name, p in core.named_parameters():
        if 'halt' in name:
            p.requires_grad_(False)
    params = [p for p in core.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params, lr=plan['lr'], weight_decay=plan['weight_decay'])
    rng = random.Random(2026093010 + a.seed)
    ledger = {'version': VERSION, 'seed': a.seed, 'updates': 0, 'closed': False,
              'optimizer_scope': 'ordered core ONLY; halt frozen', 'core_before': before_core,
              'core_after': before_core, 'model_authored_targets': 0, 'DEV_model_calls': 0,
              'learned_stop_qualified': False, 'execution_policy': 'native-fixed4',
              'experience_ids': [r['id'] for r in groups['experience']], 'replay_ids': plan['replay_ids'],
              'actual_day_experience': bool(day_rows), 'day_batch_sha256': a.day_batch_sha256,
              'experience_origins': sorted(set(r.get('origin', 'verified-human-origin-verbatim') for r in groups['experience'])),
              'raw_watermark_update': 0, 'source_binding_sha256': sha(a.binding),
              'job': os.environ['JOB'], 'repeat_CE_noise_measured': repeat_noise,
              'comparative_gain_proof': 'DEFERRED; no scientific promotion'}

    def durable():
        if any(not bool(torch.isfinite(p).all()) for p in core.parameters()):
            raise RuntimeError('nonfinite candidate parameters; prior bundle retained')
        estimated_temporary = 3 * sum(p.numel() * p.element_size() for p in core.parameters()) + 8 * 1024**2
        existing = sum(x.stat().st_size for x in OWN.rglob('*') if x.is_file())
        if existing + estimated_temporary > plan['output_cap_bytes']:
            raise RuntimeError('night output cap before atomic temporary; prior bundle retained')
        if shutil.disk_usage(out).free < plan['disk_floor_bytes']:
            raise RuntimeError('night disk floor before save; prior bundle retained')
        ledger['raw_watermark_update'] = ledger['updates']
        ledger['wall_seconds'] = time.monotonic() - start
        candidate_meta = dict(meta, stage='ordered-night-candidate-unqualified',
                              awake_parent_sha256=s['parent']['sha256'],
                              overnight_updates=ledger['updates'], overnight_ledger=dict(ledger))
        tmp = out / 'candidate-parent.pt.tmp'
        torch.save(ordered.ordered_bundle_payload(core, candidate_meta), tmp)
        os.replace(tmp, out / 'candidate-parent.pt')
        raw = dict(prefix_raw, parent_sha256=sha(out / 'candidate-parent.pt'),
                   training_stage='ordered-night-frozen-prefix-rebound-unqualified')
        tmp = out / 'candidate-English.pt.tmp'
        torch.save(raw, tmp)
        os.replace(tmp, out / 'candidate-English.pt')
        ck = {'core': core.state_dict(), 'optimizer': opt.state_dict(), 'sample_rng': rng.getstate(),
              'torch_rng': torch.get_rng_state(), 'cuda_rng': torch.cuda.get_rng_state_all(),
              'ledger': dict(ledger), 'binding': binding}
        tmp = out / 'night-resume.pt.tmp'
        torch.save(ck, tmp)
        os.replace(tmp, out / 'night-resume.pt')
        write(out / 'night-ledger.json', ledger)
        size = sum(x.stat().st_size for x in OWN.rglob('*') if x.is_file())
        if size > plan['output_cap_bytes']:
            raise RuntimeError('night output cap; candidate not activated')
        print(json.dumps({'status': 'ACTUAL-NIGHT-DURABLE', 'seed': a.seed,
                          'updates': ledger['updates'], 'parent_sha256': sha(out / 'candidate-parent.pt'),
                          'resume_sha256': sha(out / 'night-resume.pt')}), flush=True)

    with (out / 'night-raw.jsonl').open('x', encoding='utf8') as f:
        for update in range(25):
            if cancelled[0] or time.monotonic() - start > plan['wall_cap_seconds']:
                break
            batch = [rng.choice(groups['experience']), rng.choice(groups['replay'])]
            opt.zero_grad(set_to_none=True)
            losses, raw = [], []
            for row in batch:
                loss, record, _ = row_loss(row)
                losses.append(loss)
                raw.append(dict(record, update=update + 1, origin=row.get('origin', 'verified-human-origin-verbatim')))
            loss = torch.stack(losses).mean()
            if not bool(torch.isfinite(loss)):
                raise RuntimeError('nonfinite night loss; prior bundle retained')
            loss.backward()
            torch.nn.utils.clip_grad_norm_(params, 1, error_if_nonfinite=True)
            opt.step()
            for record in raw:
                f.write(json.dumps(record) + '\n')
            f.flush()
            os.fsync(f.fileno())
            ledger['updates'] = update + 1
            if update == 0 or (update + 1) % 5 == 0:
                durable()
    ledger['core_after'] = component_fingerprint(core)
    ledger['closed'] = ledger['updates'] == 25 and not cancelled[0]
    ledger['populated_Adam_states'] = len(opt.state)
    durable()
    restored, _ = ordered.load_ordered_bundle(out / 'candidate-parent.pt', 'cpu')
    ledger['checkpoint_reload_exact'] = component_fingerprint(restored) == ledger['core_after']
    del restored
    restored = torch.load(out / 'night-resume.pt', map_location='cpu', weights_only=True)
    current = opt.state_dict()['state']
    saved = restored['optimizer']['state']
    equal = bool(saved) and current.keys() == saved.keys()
    for key, value in current.items():
        equal = equal and value.keys() == saved[key].keys()
        for name, tensor in value.items():
            other = saved[key][name]
            equal = equal and (torch.equal(tensor.detach().cpu(), other) if isinstance(tensor, torch.Tensor) else tensor == other)
    ledger['populated_Adam_reload_exact'] = bool(equal)
    # Persist the validated flags into the same resume ledger consumed by bundle freeze.
    restored['ledger'] = dict(ledger)
    tmp = out / 'night-resume.pt.tmp'
    torch.save(restored, tmp)
    os.replace(tmp, out / 'night-resume.pt')
    del restored
    verify_resume = torch.load(out / 'night-resume.pt', map_location='cpu', weights_only=True)
    if verify_resume['ledger'] != ledger:
        raise RuntimeError('final resume ledger differs')
    del verify_resume
    write(out / 'night-ledger.json', ledger)
    if not ledger['checkpoint_reload_exact'] or not ledger['populated_Adam_reload_exact']:
        raise RuntimeError('saved candidate/optimizer differs; prior bundle retained')
    for name, m in [('LM', lm), ('reader', reader), ('prefix', decoder.adapter)]:
        if component_fingerprint(m) != frozen[name] or any(p.grad is not None for p in m.parameters()):
            raise RuntimeError('frozen component drift; prior bundle retained')
    after = guards()
    write(out / 'guard-after.json', after)
    decision = guard_decision(before, after, repeat_noise)
    eligible = ledger['closed'] and ledger['core_after'] != before_core and decision['pass']
    manifest = {'version': VERSION, 'seed': a.seed, 'execution_policy': 'native-fixed4',
                'learned_stop': 'UNQUALIFIED', 'parent': {'path': str(out / 'candidate-parent.pt'),
                'sha256': sha(out / 'candidate-parent.pt')}, 'prefix': {'path': str(out / 'candidate-English.pt'),
                'sha256': sha(out / 'candidate-English.pt')}, 'reader': s['reader'],
                'provenance': s['provenance'], 'previous_bundle_pin': s['previous_bundle_pin'],
                'activation_eligible': eligible, 'scientific_gain': 'NOT SHOWN'}
    write(out / 'candidate-manifest.json', manifest)
    record = {'version': VERSION, 'previous_bundle_pin': s['previous_bundle_pin'],
              'candidate_bundle_pin': sha(out / 'candidate-manifest.json'),
              'candidate_manifest': str(out / 'candidate-manifest.json'),
              'dependency_pins': {**binding['dependency_pins'], **day_pins, a.binding: sha(a.binding), a.plan: sha(a.plan),
                  **{s[k]['path']: s[k]['sha256'] for k in ('parent', 'reader', 'prefix', 'provenance', 'awake_safety_receipt')}},
              'candidate_files': {str(out / x): sha(out / x) for x in
                                  ('candidate-parent.pt', 'candidate-English.pt', 'night-resume.pt')},
              'day_batch': a.day_batch, 'day_adapter_module': binding.get('day_adapter_module'),
              'plan': a.plan, 'plan_sha256': sha(a.plan),
              'repeat_raw': str(out / 'guard-before-repeat.json'),
              'repeat_raw_sha256': sha(out / 'guard-before-repeat.json'),
              'before_raw': str(out / 'guard-before.json'), 'after_raw': str(out / 'guard-after.json'),
              'ledger': str(out / 'night-ledger.json'),
              'before_raw_sha256': sha(out / 'guard-before.json'),
              'after_raw_sha256': sha(out / 'guard-after.json'),
              'ledger_sha256': sha(out / 'night-ledger.json'),
              'repeat_CE_noise_measured': repeat_noise, 'activation_eligible': eligible,
              'guard': decision, 'action': 'eligible after independent engineering validation' if eligible else 'ROLLBACK: retain prior bundle',
              'automatic_activation': False, 'comparative_gain_proof': 'DEFERRED'}
    write(out / 'decision.json', record)
    print(json.dumps({'status': 'ACTUAL-NIGHT-CANDIDATE', 'updates': ledger['updates'],
                      'seed': a.seed, 'candidate_changed': ledger['core_after'] != before_core,
                      'activation_eligible': eligible, 'decision_sha256': sha(out / 'decision.json')}), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--binding', required=True)
    p.add_argument('--plan', required=True)
    p.add_argument('--seed', type=int, choices=(0, 1), required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--device', default='cuda')
    p.add_argument('--day-batch')
    p.add_argument('--day-batch-sha256')
    run(p.parse_args())
