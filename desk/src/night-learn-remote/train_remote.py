#!/usr/bin/env python3
"""BensPC-side HANDS training worker.

Runs on Windows with CUDA. Imports the unmodified trainer.py and pixel_model.py
that the Mac runner packs into <job>/src/night-learn, trains with batched CUDA
steps, and writes the same quarantined checkpoint set that trainer.py writes.

Every progress line is one JSON object on stdout so the Mac runner can stream
it and enforce the Mac night gate while the PC trains.
"""
import argparse
import hashlib
import json
import os
import sys
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
JOB = HERE.parent
sys.path.insert(0, str(HERE / 'night-learn'))
sys.path.insert(0, str(HERE))

import torch
import train_core
import trainer
import pixel_model


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha(value):
    raw = json.dumps(value, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def emit(event):
    print(json.dumps(event, separators=(',', ':')), flush=True)


def fail(kind, error, code=1):
    emit({'event': 'error', 'kind': kind, 'error': str(error)[:2000]})
    traceback.print_exc(file=sys.stderr)
    raise SystemExit(code)


def save_state(net, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    torch.save({key: value.detach().cpu() for key, value in net.state_dict().items()}, tmp)
    os.replace(tmp, path)


def verify_inputs(manifest, root):
    problems = []
    for relative, expected in manifest.get('inputSha256', {}).get('files', {}).items():
        path = root / relative
        if not path.is_file():
            problems.append(f'missing {relative}')
        elif sha256_file(path) != expected:
            problems.append(f'hash changed {relative}')
    dataset_hash = canonical_sha(manifest['dataset'])
    if dataset_hash != manifest.get('inputSha256', {}).get('dataset'):
        problems.append('dataset hash changed')
    if problems:
        raise ValueError('; '.join(problems))
    return {'files': len(manifest.get('inputSha256', {}).get('files', {})),
            'datasetSha256': dataset_hash}


def score_row(row):
    action = row['action']
    scored = {'id': row['id'], 'timeMs': row['timeMs'], 'kind': action['kind']}
    if action['kind'] == 'click':
        scored.update(x=action.get('screenX', action['x']), y=action.get('screenY', action['y']))
    elif action['kind'] == 'key':
        scored['key'] = str(action['keyCode'])
    return scored


def predict_arm(net, cache, rows, sizes, device, zero_intent=False, batch_size=32):
    net.eval()
    predictions = {}
    with torch.inference_mode():
        for start in range(0, len(rows), batch_size):
            picks = list(range(start, min(start + batch_size, len(rows))))
            batch = train_core._move(train_core.collate(cache, picks), device)
            if zero_intent:
                batch = (batch[0], batch[1], torch.zeros_like(batch[2]), batch[3], batch[4], batch[5])
            output, _ = net(*batch[:4])
            for index, row in enumerate(rows[start:start + len(picks)]):
                action = row['action']
                if action['kind'] == 'key':
                    predictions[row['id']] = {'key': str(int(output['key'][index].argmax(dim=0)))}
                    continue
                width, height = sizes[row['id']]
                x = float(output['position'][index, 0]) * width
                y = float(output['position'][index, 1]) * height
                display = row.get('display')
                if display:
                    bounds = display['bounds']
                    scale = min(width / bounds['width'], height / bounds['height'])
                    x = (x - (width - bounds['width'] * scale) / 2) / scale * display['scaleX']
                    y = (y - (height - bounds['height'] * scale) / 2) / scale * display['scaleY']
                predictions[row['id']] = {'x': x, 'y': y}
    return predictions


def accuracy(predictions, held, tolerance=40.0):
    clicks = keys = click_hits = key_hits = 0
    for row in held:
        prediction = predictions[row['id']]
        action = row['action']
        if action['kind'] == 'click':
            clicks += 1
            if ((prediction['x'] - action.get('screenX', action['x'])) ** 2 +
                    (prediction['y'] - action.get('screenY', action['y'])) ** 2) ** 0.5 <= tolerance:
                click_hits += 1
        elif action['kind'] == 'key':
            keys += 1
            if prediction['key'] == str(action['keyCode']):
                key_hits += 1
    return {'clicks': clicks, 'keys': keys, 'clickHits': click_hits,
            'keyHits': key_hits, 'clickTolerancePx': tolerance,
            'clickAccuracy': (click_hits / clicks) if clicks else None,
            'keyAccuracy': (key_hits / keys) if keys else None}


def reboot_pending():
    if sys.platform != 'win32':
        return False
    import winreg
    path = r'SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired'
    try:
        winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path)
        return True
    except FileNotFoundError:
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--job', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    started_at = time.time()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    job_file = Path(args.job)

    try:
        manifest = json.loads(job_file.read_text(encoding='utf8'))
    except Exception as error:
        fail('input', f'unreadable job manifest: {error}')

    if not torch.cuda.is_available():
        fail('cuda', 'torch.cuda.is_available() is false', 4)
    device = torch.device('cuda:0')

    try:
        emit({'event': 'phase', 'name': 'verify-inputs', 'pid': os.getpid()})
        verified = verify_inputs(manifest, JOB)
        emit({'event': 'phase', 'name': 'inputs-verified', **verified})
        try:
            smoke = torch.randn(64, 64, device=device)
            if not torch.isfinite((smoke @ smoke).sum()).item():
                raise RuntimeError('nonfinite CUDA smoke result')
            torch.cuda.synchronize()
        except Exception as error:
            fail('cuda', error, 4)
        emit({'event': 'ready', 'pid': os.getpid(), 'device': torch.cuda.get_device_name(0),
              'torch': torch.__version__, 'cuda': torch.version.cuda,
              'capability': list(torch.cuda.get_device_capability(0))})

        config = manifest['config']
        steps = int(config['steps'])
        batch_size = int(config['batchSize'])
        lr = float(config['lr'])
        seed = int(config.get('seed', 101))
        checkpoint_every = int(config.get('checkpointEvery', 10))
        if not 1 <= steps <= 20000 or not 1 <= batch_size <= 64 or not 0 < lr <= 0.01:
            raise ValueError('invalid training config')

        dataset = manifest['dataset']
        rows = dataset['examples']
        emit({'event': 'phase', 'name': 'partition', 'examples': len(rows)})
        if dataset.get('allowSparse') and (len(rows) < 2 or len({row['timeMs'] for row in rows}) < 2):
            train_rows, held_rows, cutoff = rows, [], dataset['endMs']
        else:
            train_rows, held_rows, cutoff = trainer.partition(rows, dataset['startMs'], dataset['endMs'])
        held = [row for row in held_rows if row['action']['kind'] in ('click', 'key')]

        emit({'event': 'phase', 'name': 'preload', 'trainRows': len(train_rows)})
        for row in rows:
            trainer.load_example(row)
        train_cache = train_core.preload(train_rows, trainer.load_example)
        held_cache = train_core.preload(held, trainer.load_example)
        from PIL import Image
        sizes = {}
        for row in held:
            with Image.open(row['frame']) as frame:
                sizes[row['id']] = frame.size

        torch.manual_seed(seed)
        initial = pixel_model.NativeActionPolicy().eval()
        previous = dataset.get('preSleepWeights')
        state = torch.load(JOB / 'starting.pt', map_location='cpu', weights_only=True)
        initial.load_state_dict(state, strict=True)
        old = pixel_model.NativeActionPolicy().eval()
        old.load_state_dict(initial.state_dict())
        candidate = pixel_model.NativeActionPolicy()
        candidate.load_state_dict(initial.state_dict())
        no_intent = pixel_model.NativeActionPolicy()
        no_intent.load_state_dict(initial.state_dict())
        old.to(device)
        candidate.to(device)
        no_intent.to(device)

        emit({'event': 'phase', 'name': 'evaluate-before'})
        old_predictions = predict_arm(old, held_cache, held, sizes, device)
        old_loss = train_core.eval_loss(old, held_cache, device, pixel_model)
        old_accuracy = accuracy(old_predictions, held)

        def report(step, loss, step_ms):
            emit({'event': 'progress', 'step': step, 'loss': loss, 'stepMs': step_ms})

        emit({'event': 'phase', 'name': 'train-candidate', 'steps': steps, 'batchSize': batch_size})
        candidate_curve, candidate_ms = train_core.fit(
            candidate, train_cache, device, pixel_model, steps=steps, batch_size=batch_size,
            lr=lr, seed=seed, on_step=report,
            checkpoint_path=out / 'checkpoints' / 'candidate',
            checkpoint_every=checkpoint_every, save_state=save_state)

        emit({'event': 'phase', 'name': 'train-no-intent', 'steps': steps})
        no_intent_curve, no_intent_ms = train_core.fit(
            no_intent, train_cache, device, pixel_model, steps=steps, batch_size=batch_size,
            lr=lr, seed=seed, zero_intent=True,
            on_step=report,
            checkpoint_path=out / 'checkpoints' / 'no-intent',
            checkpoint_every=checkpoint_every, save_state=save_state)

        emit({'event': 'phase', 'name': 'evaluate-after'})
        candidate_predictions = predict_arm(candidate, held_cache, held, sizes, device)
        no_intent_predictions = predict_arm(no_intent, held_cache, held, sizes, device, zero_intent=True)
        candidate_loss = train_core.eval_loss(candidate, held_cache, device, pixel_model)
        no_intent_loss = train_core.eval_loss(no_intent, held_cache, device, pixel_model, zero_intent=True)
        candidate_accuracy = accuracy(candidate_predictions, held)
        no_intent_accuracy = accuracy(no_intent_predictions, held)

        emit({'event': 'phase', 'name': 'save-checkpoints'})
        save_state(old, out / 'old.pt')
        save_state(candidate, out / 'candidate.pt')
        save_state(no_intent, out / 'no-intent.pt')
        model_sha = {name: sha256_file(out / (name + '.pt'))
                     for name in ('old', 'candidate', 'no-intent')}

        result = {
            'cutoffMs': cutoff,
            'train': [score_row(row) for row in train_rows],
            'held': [score_row(row) for row in held],
            'predictions': {'old': old_predictions, 'candidate': candidate_predictions,
                            'noIntent': no_intent_predictions},
            'modelSha256': model_sha,
            'oldModel': ('previous native-action model' if previous else
                         'initial untrained native-action head; no published compatible model loaded'),
            'hasPreviousModel': bool(previous),
            'baselineWarning': None,
            'trainingStepsPerArm': steps,
            'intentPolicy': {'candidate': 'fixed hash64 of supplied intent',
                             'noIntent': 'all-zero vector',
                             'trainIntentCount': len({row['intent'] for row in train_rows})},
            'status': 'quarantine; not promoted',
            'remote': {
                'backend': 'benspc-gpu',
                'device': torch.cuda.get_device_name(0),
                'capability': list(torch.cuda.get_device_capability(0)),
                'torch': torch.__version__,
                'cuda': torch.version.cuda,
                'python': sys.version.split()[0],
                'steps': steps,
                'batchSize': batch_size,
                'lr': lr,
                'trainExamples': len(train_rows),
                'heldClickExamples': sum(1 for row in held if row['action']['kind'] == 'click'),
                'heldKeyExamples': sum(1 for row in held if row['action']['kind'] == 'key'),
                'stepTime': train_core.timing_summary(candidate_ms),
                'benchmarkStepTime': train_core.timing_summary(candidate_ms[:20]),
                'noIntentStepTime': train_core.timing_summary(no_intent_ms),
                'lossCurve': candidate_curve,
                'noIntentLossCurve': no_intent_curve,
                'heldLoss': {'old': old_loss, 'candidate': candidate_loss,
                             'noIntent': no_intent_loss},
                'accuracy': {'old': old_accuracy, 'candidate': candidate_accuracy,
                             'noIntent': no_intent_accuracy},
                'peakVramMiB': torch.cuda.max_memory_allocated() / (1024 * 1024),
                'checkpointEvery': checkpoint_every,
                'rebootPending': reboot_pending(),
                'checkpointFiles': {str(file.relative_to(out)): sha256_file(file)
                                    for file in (out / 'checkpoints').glob('*')},
                'pid': os.getpid(),
                'startedAt': started_at,
                'finishedAt': time.time(),
            },
        }
        result_file = out / 'result.json'
        tmp = out / 'result.json.tmp'
        tmp.write_text(json.dumps(result, indent=2) + '\n', encoding='utf8')
        os.replace(tmp, result_file)
        emit({'event': 'done', 'resultSha256': sha256_file(result_file),
              'modelSha256': model_sha, 'inputsVerified': verified,
              'seconds': time.time() - started_at})
    except SystemExit:
        raise
    except Exception as error:
        detail = str(error).lower()
        fail('cuda' if any(term in detail for term in ('cuda', 'cudnn', 'cublas', 'sm_120')) else 'training', error)


if __name__ == '__main__':
    main()
