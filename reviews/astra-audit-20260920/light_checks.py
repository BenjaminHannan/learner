"""Read-only audit probes. No optimizer step, training, panel selection, or GPU use."""
from __future__ import annotations

import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import random
import sys
import time

for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
             'VECLIB_MAXIMUM_THREADS'):
    os.environ[name] = '1'
BASE = Path('/Users/ben-hannan/Desktop/projects/beautiful-model')
W = BASE / '.claude/worktrees/card-experiment-handoff-7c5b27'
OUT = Path(__file__).resolve().parent


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def baseline():
    sys.path.insert(0, str(W / 'scripts'))
    import fable_baseline_transformer as B
    B.configure()
    torch, F = B.torch, B.F
    T = module(W / 'tests/test_fable_baseline_transformer.py', 'baseline_reference')
    E = module(W / 'tests/test_fable_baseline_evidence_aux.py', 'baseline_evidence_checks')
    checks = ['check_parameters', 'check_causal', 'check_loss_positions',
              'check_targets_match_interpreter', 'check_decode_stops',
              'check_pair_scoring', 'check_reference_equivalence']
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        for name in checks:
            getattr(T, name)()
        E.main()
    result = dict(existing_check_log=output.getvalue(), baseline_checks=T.CHECKS,
                  evidence_checks=E.CHECKS)

    # Multiple questions share a story: compare backward accumulation as well as logits.
    stories, items = B.training_items(random.Random('astra-audit-gradient-v1'), visits=2)
    batch = B.pack_batch(stories, items, 'steps')
    parity = {}
    for position in ('line', 'absolute', 'none'):
        torch.manual_seed(990721)
        cached = B.BaselineTransformer(positions=position)
        dense = copy.deepcopy(cached)
        actual, _ = cached(batch)
        actual_loss = F.cross_entropy(actual.reshape(-1, B.VOCAB), batch.target.reshape(-1))
        actual_loss.backward()
        wanted, targets = [], []
        logit_delta = 0.
        for i, item in enumerate(items):
            emitted = B.output_tokens(item['chain'], 'steps')
            rows = stories[item['owner']]
            logits = T.reference_logits(dense, rows, item['question'], emitted)
            offset = sum(map(len, rows)) + len(item['question']) - 1
            scored = logits[offset:offset+len(emitted)]
            wanted.append(scored)
            targets.extend(emitted)
            begin = len(item['question']) - 1
            logit_delta = max(logit_delta, float((actual[i, begin:begin+len(emitted)]
                                                - scored).detach().abs().max()))
        dense_loss = F.cross_entropy(torch.cat(wanted), torch.tensor(targets))
        dense_loss.backward()
        differences = {}
        for (name, p), (_, q) in zip(cached.named_parameters(), dense.named_parameters()):
            if p.grad is None or q.grad is None:
                assert p.grad is None and q.grad is None, name
            else:
                assert torch.isfinite(p.grad).all() and torch.isfinite(q.grad).all(), name
                differences[name] = float((p.grad - q.grad).abs().max())
        worst = max(differences.values())
        assert logit_delta < 2e-5 and worst < 2e-5, (position, logit_delta, worst)
        parity[position] = dict(logit_max_abs=logit_delta, gradient_max_abs=worst,
                                loss_abs=float(abs(actual_loss.detach()-dense_loss.detach())))
    result['dense_cache_parity'] = parity

    # Inspect trained models only on a fresh, small validation draw, shared across runs.
    stories, items = B.training_items(random.Random('astra-audit-validation-v1'), visits=8)
    batch = B.pack_batch(stories, items, 'steps')
    root = W / 'artifacts/fable-baseline-transformer-20260920'
    result['checkpoint_probe'] = {}
    for relative in ['steps-line-11k/seed-0', 'steps-line-11k/seed-1',
                     'steps-line-11k/seed-2', 'dev/steps-line-990001']:
        saved = torch.load(root / relative / 'baseline.pt', map_location='cpu', weights_only=False)
        model = B.BaselineTransformer(**saved['config']).eval()
        model.load_state_dict(saved['state_dict'], strict=True)
        with torch.no_grad():
            logits, _ = model(batch)
            pred = logits.argmax(-1)
        grouped = {name: [0, 0] for name in ['all', 'end', 'link', 'terminal', 'one_hop']}
        for i, item in enumerate(items):
            out = B.output_tokens(item['chain'], 'steps')
            for j, target in enumerate(out):
                correct = int(pred[i, len(item['question']) - 1 + j] == target)
                labels = ['all', 'end' if target == B.END else
                          ('link' if j < len(item['chain'])-1 else 'terminal')]
                if len(item['chain']) == 1 and target != B.END:
                    labels.append('one_hop')
                for label in labels:
                    grouped[label][0] += correct
                    grouped[label][1] += 1
        result['checkpoint_probe'][relative] = {k: dict(correct=v[0], n=v[1])
                                                for k, v in grouped.items()}
    # Which output-position rows actually receive loss gradients at trained lengths?
    torch.manual_seed(990722)
    model = B.BaselineTransformer()
    B.teacher_forced_loss(model, batch)[0].backward()
    result['output_step_gradient_norms'] = model.output_step.weight.grad.norm(dim=1).tolist()
    result['lr_11k'] = {str(u): B.learning_rate(.001, u, 11000)
                        for u in (0, 99, 7332, 7333, 10999)}
    log_decay = sum(__import__('math').log1p(-.1*B.learning_rate(.001, u, 11000))
                    for u in range(11000))
    result['pure_decay_multiplier_11k'] = __import__('math').exp(log_decay)
    return result


def factorial():
    sys.path.insert(0, str(W / 'scripts'))
    import fable_startup_factorial as X
    X.R.configure()
    plans, info = X.plan_batch(random.Random(1101), random.Random('audit-plan-v1'), visits=2)
    batches = {arm: X.materialise(plans, arm, info['records'], info['census']) for arm in X.ARMS}
    first = batches['A']
    for arm, b in batches.items():
        for group, targets in [('canonical', 'canonical_targets'), ('monolithic', 'monolithic_targets')]:
            assert X.torch.equal(getattr(b, group).questions, getattr(first, group).questions)
            assert X.torch.equal(getattr(b, targets).answer, getattr(first, targets).answer)
    launch = json.loads((X.OUT/'launch.json').read_text())
    changed = [name for name, expected in launch['files'].items()
               if hashlib.sha256((BASE/name).read_bytes()).hexdigest() != expected]
    assert not changed, changed
    early = X._started([dict(update=1, probe_one_hop_acc=1.)], 1)
    sparse = X._started([dict(update=2500, probe_one_hop_acc=1.)], 2500)
    incomplete_rows = [dict(update=u, probe_one_hop_acc=1.) for u in (2350, 2400, 2450, 2500)]
    return dict(arm_questions_answers_equal=True,
                kept_rows={a:b.accounting['curriculum']['kept_lines'] for a,b in batches.items()},
                hashed_files_checked=len(launch['files']), hashed_files_changed=changed,
                start_rule_accepts_single_first_update=early,
                start_rule_accepts_missing_window=sparse,
                start_rule_accepts_four_probes_over_150_updates=X._started(incomplete_rows,2500),
                default_wave_workers=len(X.build_parser().parse_args(['wave']).arms.split(','))*
                                     len(X.build_parser().parse_args(['wave']).seeds.split(',')))


def staged():
    sys.path.insert(0, str(BASE / 'scripts'))
    import fable_operator_staged as X
    X.R.configure()
    T = module(BASE/'tests/test_fable_operator_staged.py', 'staged_test_helpers')
    # These functions build batches / compute gradients only; no optimizer updates.
    result = {}
    for step in (0, 2499):
        batch = T.staged('marg-staged', step, visits=2)
        model = X.A.new_model(990723)
        one, marg, mono = X.staged_losses(model, batch)
        assert marg is None
        w1,w2,w3 = X.S.marg_weights(batch)
        loss = w1*one+w3*mono
        loss.backward()
        grads = {n:p.grad.detach().clone() for n,p in model.named_parameters() if p.grad is not None}
        model.zero_grad(set_to_none=True)
        direct = (X.F.cross_entropy(model(batch.one_hop), batch.one_hop_targets.answer)+
                  X.F.cross_entropy(model(batch.monolithic), batch.monolithic_answers))/3
        direct.backward()
        worst = max(float((p.grad-grads[n]).abs().max()) for n,p in model.named_parameters()
                    if p.grad is not None)
        assert worst < 2e-5, worst
        result[str(step)] = dict(weights=[w1,w2,w3], forwarded=batch.accounting['forwards']['groups'],
                                loss_delta=float(abs(loss.detach()-direct.detach())),
                                gradient_max_abs=worst, marginal_is_none=True)
    return result


if __name__ == '__main__':
    name = sys.argv[1]
    started = time.monotonic()
    result = globals()[name]()
    result.update(seconds=time.monotonic()-started, no_training=True, device='cpu', threads=1)
    path = OUT/f'{name}-checks.json'
    with path.open('x') as handle:
        json.dump(result, handle, indent=2)
        handle.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k != 'existing_check_log'}, indent=2))
