"""Shared English pilot model path (probe G5, worker G7, eval G9).

Architecture is unchanged: frozen LFM2.5 LM, contextual frozen features -> thin
reader -> ordered core (four fixed latent loops, notebook=None, English cap64
binding) -> StatePrefix (8 prefix vectors) -> frozen LM. Training loss is the
unchanged human_loss only (BOS + shifted target, -100 masking, per-example
valid-token mean incl. EOS). Generation is the unchanged native greedy
FrozenEnglishDecoder.generate seen through the 48-token observer.

Import is stdlib-only; import_runtime() loads Torch and the pinned modules.
"""
import importlib
import importlib.util
from pathlib import Path
import sys
import types

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for entry in (str(HERE), str(ROOT / 'scripts'), str(ROOT)):
    if entry not in sys.path:
        sys.path.insert(0, entry)
import english_pilot_common_v1 as common  # noqa: E402

PARAMETER_COUNT = 114
NONE_GRAD_CORE_CHILDREN = ('halt', 'tok', 'slot', 'head', 'ln_out')
TRAINABLE_WITH_GRADIENT = ('reader', 'core', 'prefix')
ADAM_RECIPE = {'lr': 0.001, 'weight_decay': 0, 'betas': (0.9, 0.999), 'eps': 1e-8}


def import_runtime():
    import torch
    from sol_translator_grounding_v6 import HumanInputProjection, human_loss
    from sol_translator_english_v6 import FrozenEnglishDecoder
    import sol_spatial_poc_ordered_v2 as ordered
    import sol_spatial_poc_ordered_train_api_v2 as train_api
    from scripts.sol_stop_ordered_api2 import ordered_attention_math
    from scripts.sol_stop_adapter import FinalLatent
    import sol_cloud_capability256_v1 as sealed
    import english_ordered_begin_cap64_v1 as cap64
    import english_observe_generation48_v1 as observer
    import english_feature_cache64_v1 as cache
    return types.SimpleNamespace(
        torch=torch, HumanInputProjection=HumanInputProjection, human_loss=human_loss,
        FrozenEnglishDecoder=FrozenEnglishDecoder, ordered=ordered, train_api=train_api,
        ordered_attention_math=ordered_attention_math, FinalLatent=FinalLatent, sealed=sealed,
        cap64=cap64, observer=observer, cache=cache,
        constructors=importlib.import_module('scripts.cap256_launch.fresh_core_calculator_constructor'),
        calculator=importlib.import_module('scripts.cap256_launch.calculator_runtime_depth_compare'),
        compare=cache.load_compare_worker())


def build_modules(rt, dec, seed, device):
    """Same constructors as the parent run; weights are overwritten by strict load."""
    reader = rt.compare.build_fresh_reader(rt.torch, rt.HumanInputProjection, seed, device)
    core = rt.constructors.build_fresh_core('shallow', seed, device)
    tool = rt.calculator.CalculatorPath(dim=256).to(device)
    return [('core', core), ('reader', reader), ('prefix', dec.adapter), ('tool', tool)]


def module_dict(modules):
    return dict(modules)


def restore_parent_modules(rt, saved, modules, lm):
    torch = rt.torch
    for name, module in modules:
        module.load_state_dict(saved[name], strict=True)
        module.train().requires_grad_(True)
    core, tool = module_dict(modules)['core'], module_dict(modules)['tool']
    core.halt.requires_grad_(False)
    if core.constructor() != saved['constructor'] or tool.constructor() != saved['tool_constructor']:
        raise ValueError('exact saved module constructors required')
    if any(p.dtype != torch.float32 for m in [lm] + [m for _, m in modules] for p in m.parameters()):
        raise ValueError('full FP32 modules required')
    rt.cap64.bind_english_cap64(core)
    named = [(component + '.' + n, p) for component, module in modules
             for n, p in module.named_parameters() if p.requires_grad]
    names = [n for n, _ in named]
    if len(names) != PARAMETER_COUNT or len(set(names)) != PARAMETER_COUNT:
        raise ValueError('exact 114 named trainable parameters required')
    return named


def validate_parent_metadata(saved, names, expected_update):
    required = {'core', 'reader', 'prefix', 'tool', 'constructor', 'tool_constructor', 'optimizer',
                'optimizer_parameter_names', 'participation', 'torch_rng', 'cuda_rng', 'python_rng', 'update'}
    if type(saved) is not dict or not required <= set(saved):
        raise ValueError('complete parent checkpoint fields required')
    if saved['update'] != expected_update:
        raise ValueError('parent update count differs from the pinned parent')
    if saved['optimizer_parameter_names'] != names:
        raise ValueError('parent 114-name optimizer traversal differs')
    opt = saved['optimizer']
    if (set(opt) != {'state', 'param_groups'} or len(opt['param_groups']) != 1
            or opt['param_groups'][0]['params'] != list(range(len(names)))
            or set(opt['state']) - set(range(len(names)))):
        raise ValueError('parent Adam index layout differs')
    participation = saved['participation']
    if set(participation) - set(names) or any(type(v) is not int or v < 0 for v in participation.values()):
        raise ValueError('parent participation differs')
    return True


def make_optimizer(torch, params):
    return torch.optim.AdamW(params, lr=ADAM_RECIPE['lr'], weight_decay=ADAM_RECIPE['weight_decay'],
                             betas=ADAM_RECIPE['betas'], eps=ADAM_RECIPE['eps'])


def restore_adam(torch, opt, saved, named):
    """Continue the parent's Adam state exactly (no reset)."""
    if saved['optimizer_parameter_names'] != [n for n, _ in named]:
        raise ValueError('actual 114 parameter traversal differs before Adam load')
    # Optimizer.load_state_dict keeps same-device/dtype tensors aliased; Adam would then
    # mutate the parent's saved moments in place (shared by both arms). Load a deep copy.
    import copy
    opt.load_state_dict(copy.deepcopy(saved['optimizer']))
    if not common.state_equal(opt.state_dict(), saved['optimizer'], torch):
        raise ValueError('complete loaded Adam state differs')
    for group in opt.param_groups:
        if (group['lr'], group['weight_decay'], tuple(group['betas']), group['eps']) != (
                ADAM_RECIPE['lr'], ADAM_RECIPE['weight_decay'], ADAM_RECIPE['betas'], ADAM_RECIPE['eps']):
            raise ValueError('inherited AdamW recipe differs')
    for name, p in named:
        state = opt.state.get(p, {})
        step = int(state['step']) if state else 0
        if step != saved['participation'].get(name, 0):
            raise ValueError('Adam step/participation differs: ' + name)
        if state and (set(state) != {'step', 'exp_avg', 'exp_avg_sq'}
                      or state['exp_avg'].shape != p.shape or state['exp_avg_sq'].shape != p.shape
                      or state['exp_avg'].dtype != torch.float32 or state['exp_avg_sq'].dtype != torch.float32
                      or not bool(torch.isfinite(state['exp_avg']).all())
                      or not bool(torch.isfinite(state['exp_avg_sq']).all())):
            raise ValueError('finite FP32 Adam moments required: ' + name)
    return sum(1 for _, p in named if opt.state.get(p))


def adam_steps(opt, named):
    return {n: (int(opt.state[p]['step']) if opt.state.get(p) else 0) for n, p in named}


def english_graph(rt, core, reader, features, mask):
    """features [1,N,2048] frozen -> reader -> 4 fixed loops; returns h [1,N,256], aux (observed only)."""
    rt.cap64.require_bound(core)
    query = rt.compare.project_cached_question(reader, features, mask)
    with rt.ordered_attention_math():
        h, _q, aux = rt.train_api.fixed4_training(core, query, None, query_mask=mask)
    if h.ndim != 3 or h.shape[:2] != mask.shape or h.shape[-1] != 256:
        raise ValueError('final latent [1,N,256] required')
    return h, aux


def english_loss(rt, lm, dec, h, mask, target):
    """Unchanged human_loss plus an independent valid-token CE decomposition check."""
    torch = rt.torch
    captured = []
    hook = lm.register_forward_hook(lambda module, args, result: captured.append(result.logits))
    try:
        prefix = dec.adapter.project_training(h, torch.ones_like(h, dtype=torch.bool), mask, (1, h.shape[1]))
        if tuple(prefix.shape[:2]) != (1, 8):
            raise ValueError('exactly 8 prefix vectors required')
        per, prediction = rt.human_loss(lm, prefix, target, dec.bos_id, dec.eos_id, True, True)
    finally:
        hook.remove()
    if len(captured) != 1:
        raise ValueError('one teacher-forced LM forward required')
    logits = captured[0][:, prefix.shape[1]:].float().detach()
    valid = target != -100
    ce = torch.nn.functional.cross_entropy(logits.transpose(1, 2), target, ignore_index=-100, reduction='none')
    independent = ce.sum(1) / valid.sum(1)
    if not torch.allclose(independent, per.detach(), rtol=1e-5, atol=1e-6):
        raise ValueError('valid-token CE decomposition differs from human_loss')
    correct = (prediction == target) & valid
    stats = {'CE': float(per.detach().mean()), 'valid_target_tokens': int(valid.sum()),
             'first_token_CE': float(ce[0, 0]), 'EOS_CE': float(ce[0, int(valid.sum()) - 1]),
             'teacherforced_token_accuracy': float(correct.sum()) / int(valid.sum()),
             'teacherforced_exact': bool(correct.sum() == valid.sum())}
    return per, prediction, stats


def none_grad_parameters(lm, core, tool):
    rows = [('lm.' + n, p) for n, p in lm.named_parameters()]
    rows += [('tool.' + n, p) for n, p in tool.named_parameters()]
    for child in NONE_GRAD_CORE_CHILDREN:
        rows += [('core.%s.%s' % (child, n), p) for n, p in getattr(core, child).named_parameters()]
    return rows


def gradient_contract(rt, modules, lm):
    """reader/core/prefix grads finite with positive norm; LM, halt, tool, tok/slot/head/ln_out None."""
    torch = rt.torch
    parts = module_dict(modules)
    receipts = {name: common.gradient_receipt(module, torch) for name, module in modules}
    violations = [name for name in TRAINABLE_WITH_GRADIENT
                  if not receipts[name]['finite'] or not receipts[name]['norm'] > 0]
    unexpected = [n for n, p in none_grad_parameters(lm, parts['core'], parts['tool']) if p.grad is not None]
    return {'component_gradients': receipts, 'trainable_violations': violations,
            'unexpected_gradients': unexpected[:20], 'unexpected_gradient_count': len(unexpected),
            'passed': not violations and not unexpected}


def generate_observed(rt, dec, core, reader, features, mask, max_tokens=48):
    torch = rt.torch
    with torch.no_grad():
        h, _ = english_graph(rt, core, reader, features, mask)
    packet = rt.FinalLatent(h.detach(), torch.ones_like(h, dtype=torch.bool), mask, (1, h.shape[1]))
    return rt.observer.observe_generation48(dec, packet, max_tokens)


def preserved_measurement(call, roots, opt, torch):
    """Inference only: model, Adam, gradients, RNG and module modes must be unchanged."""
    rng = common.rng_snapshot(torch)
    submodules, seen = [], set()
    for _, root in roots:
        for module in root.modules():
            if id(module) not in seen:
                seen.add(id(module))
                submodules.append((module, module.training))
    parameters, seen = [], set()
    for _, root in roots:
        for p in root.parameters():
            if id(p) not in seen:
                seen.add(id(p))
                parameters.append((p, p.requires_grad, p.grad,
                                   None if p.grad is None else p.grad.detach().clone()))

    def snapshot():
        return {'model': common.tree_digest({n: m.state_dict() for n, m in roots}, torch),
                'optimizer': None if opt is None else common.tree_digest(opt.state_dict(), torch),
                'gradients': common.tree_digest([(p.requires_grad, None if p.grad is None else p.grad.detach())
                                                 for p, _, _, _ in parameters], torch),
                'RNG': common.tree_digest(common.rng_snapshot(torch), torch)}
    before = {**snapshot(), 'modes': [m for _, m in submodules]}
    try:
        for _, module in roots:
            module.eval()
        with torch.no_grad():
            value = call()
    finally:
        for module, mode in submodules:
            module.training = mode
        with torch.no_grad():
            for p, requires, original, copy_ in parameters:
                p.requires_grad_(requires)
                p.grad = original
                if original is not None:
                    original.copy_(copy_)
        common.restore_rng(rng, torch)
    after = {**snapshot(), 'modes': [m.training for m, _ in submodules]}
    if before != after:
        raise ValueError('measurement changed model/Adam/gradient/RNG/mode state')
    return value, {'before': before, 'model_unchanged': True, 'optimizer_unchanged': True,
                   'gradients_unchanged': True, 'RNG_restored': True, 'modes_restored': True}


def checkpoint_payload(modules, opt, names, participation, extra, rng):
    core = module_dict(modules)['core']
    tool = module_dict(modules)['tool']
    return {**extra, 'constructor': core.constructor(), 'tool_constructor': tool.constructor(),
            **{name: module.state_dict() for name, module in modules}, 'optimizer': opt.state_dict(),
            'optimizer_parameter_names': names, 'participation': dict(participation), **rng}


# ---------------------------------------------------------------------------
# Native configuration (stdlib checks) and native stack loading (PC only).
# ---------------------------------------------------------------------------
CONFIG_SCHEMA = 'premonition.English-pilot-native-config.v1'
PARENT_SHAS = {0: '49a350235164a7c2f4ccc2731358dc615cf8a25086abd32afe71e4c3bd44c001',
               1: '4c3c410f99ae37a8f46d5de58af7b71d550d841d6ecd306d2a1c2c8199c1330d'}
PARENT_UPDATE = 5120
BANK_SHA256 = 'f2f5cce3dd2775af16ab13db8fa36b08a70b305bd1229df9e9471c4fdf7fb9ac'
SERIALIZER_PATH = ('artifacts/cap256-launch/contextual-input-compare-v1/'
                   'ENGLISH-PARAPHRASE-RECONSTRUCTION-CPU-FEASIBILITY-v1/'
                   'SMALL-TRAIN-QUALIFICATION-PREPARATION-v1/english_clean_train_input_v2.py')
GIB = 1024 ** 3
BUDGETS = {  # kind -> (max worker seconds, max new output bytes)
    'probe': (2400, 2 * GIB), 'train': (28800, 4 * GIB), 'eval': (14400, 2 * GIB)}
BASE_KEYS = {'schema', 'kind', 'device', 'lm', 'feature_identity', 'bank', 'frames', 'schedule',
             'parents', 'output_namespace', 'cache_namespace', 'budget', 'dispatch_allowed', 'runner'}
KIND_KEYS = {'probe': set(), 'train': {'resume_every_updates'}, 'eval': {'fresh_inputs', 'states'}}


def validate_budget(budget, kind):
    seconds, output = BUDGETS[kind]
    keys = {'worker_seconds', 'new_output_bytes', 'cuda_peak_reserved_cap_bytes', 'project_cap_bytes',
            'retained_free_bytes', 'aggregate_spend_usd_cap'}
    if (type(budget) is not dict or set(budget) != keys
            or type(budget['worker_seconds']) is not int or not 0 < budget['worker_seconds'] <= seconds
            or type(budget['new_output_bytes']) is not int or not 0 < budget['new_output_bytes'] <= output
            or type(budget['cuda_peak_reserved_cap_bytes']) is not int
            or not 0 < budget['cuda_peak_reserved_cap_bytes'] <= 10 * GIB
            or budget['project_cap_bytes'] != 100000000000
            or budget['retained_free_bytes'] != 2 * GIB
            or budget['aggregate_spend_usd_cap'] != '0.00'):
        raise ValueError('fixed zero-spend English pilot resource caps required (%s)' % kind)


def load_serializer(root):
    path = Path(root).resolve() / SERIALIZER_PATH
    spec = importlib.util.spec_from_file_location('_english_serializer_v2', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_native_config(root, cfg, kind, runner_path):
    """Stdlib-only admission: positive allowlist, pins, frames, schedule, parents, budget."""
    import english_full_pilot_schedule_v1 as schedule_module
    root = Path(root).resolve()
    if kind not in KIND_KEYS:
        raise ValueError('kind probe/train/eval required')
    if type(cfg) is not dict or set(cfg) != BASE_KEYS | KIND_KEYS[kind] or cfg['schema'] != CONFIG_SCHEMA \
            or cfg['kind'] != kind:
        raise ValueError('positive allowlist English pilot %s config required' % kind)
    if cfg['device'] not in ('cuda', 'cpu'):
        raise ValueError('device cuda/cpu required')
    if common.pinned(root, cfg['runner']) != Path(runner_path).resolve():
        raise ValueError('runner self pin differs')
    validate_budget(cfg['budget'], kind)
    lm = cfg['lm']
    if type(lm) is not dict or set(lm) != {'model_path', 'provenance', 'adapter'} or type(lm['model_path']) is not str:
        raise ValueError('lm model_path/provenance/adapter pins required')
    common.pinned(root, lm['provenance'])
    common.pinned(root, lm['adapter'])
    if cfg['bank'].get('sha256') != BANK_SHA256:
        raise ValueError('pinned v3 TRAIN bank required')
    bank = common.read_json(common.pinned(root, cfg['bank']))
    serializer = load_serializer(root)
    frames = serializer.validate_frames_document(common.read_json(common.pinned(root, cfg['frames'])),
                                                 bank, BANK_SHA256)
    schedules = schedule_module.validate_schedule_document(
        common.read_json(common.pinned(root, cfg['schedule'])))
    parents = cfg['parents']
    if (type(parents) is not list or [p.get('seed') for p in parents] != [0, 1]
            or any(set(p) != {'seed', 'checkpoint'} for p in parents)):
        raise ValueError('exact seed0/seed1 parent pins required')
    for p in parents:
        if p['checkpoint'].get('sha256') != PARENT_SHAS[p['seed']]:
            raise ValueError('fixed root-decision parent checkpoint required for seed %d' % p['seed'])
        common.pinned(root, p['checkpoint'])
    for name in ('output_namespace', 'cache_namespace'):
        rel = cfg[name]
        if type(rel) is not str or not rel or Path(rel).is_absolute() or '..' in Path(rel).parts:
            raise ValueError('relative owned namespace required: ' + name)
    if kind == 'train' and (type(cfg['resume_every_updates']) is not int
                            or cfg['resume_every_updates'] not in (72, 144, 288, 576)):
        raise ValueError('resume checkpoint cadence must divide the pass structure')
    if type(cfg['dispatch_allowed']) is not bool:
        raise ValueError('explicit dispatch_allowed flag required')
    return {'frames': frames, 'schedules': schedules, 'bank': bank, 'serializer': serializer}


def load_native_stack(rt, root, cfg):
    """Frozen LM + decoder (prefix weights replaced later by each parent), tokenizer checks."""
    import os
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    from sol_translator_english_ordered_v10 import load_ordered_english
    root = Path(root).resolve()
    model = Path(cfg['lm']['model_path'])
    model = model if model.is_absolute() else root / model
    dec, tokenizer, provenance = load_ordered_english(
        str(model), str(common.pinned(root, cfg['lm']['provenance'])),
        str(common.pinned(root, cfg['lm']['adapter'])), cfg['device'])
    lm = dec.lm
    lm.eval().requires_grad_(False)
    rt.compare.verify_feature_provenance(provenance, cfg['feature_identity'])
    rt.compare.verify_lm_runtime(lm, tokenizer, cfg['feature_identity'], rt.torch)
    if (dec.bos_id, dec.eos_id) != (common.BOS_ID, common.EOS_ID):
        raise ValueError('constant BOS1/EOS7 required')
    return dec, tokenizer, lm


def check_tokenizer_frames(tokenizer, frames):
    """The native tokenizer must reproduce every pinned frame ID array exactly."""
    for frame in frames:
        ids = list(tokenizer.encode(frame['learner_text'], add_special_tokens=False)) + [common.EOS_ID]
        labels = list(tokenizer.encode(frame['target_text'], add_special_tokens=False)) + [common.EOS_ID]
        if ids != frame['input_ids'][0] or labels != frame['labels'][0]:
            raise ValueError('native tokenizer differs from pinned frame %d' % frame['frame_index'])
    return True


def frame_tensors(torch, frames, device):
    return {f['frame_index']: (torch.tensor(f['input_ids'], device=device, dtype=torch.long),
                               torch.tensor(f['input_mask'], device=device, dtype=torch.bool),
                               torch.tensor(f['labels'], device=device, dtype=torch.long)) for f in frames}


def code_digests():
    names = ['english_pilot_common_v1.py', 'english_pilot_runtime_v1.py', 'english_ordered_begin_cap64_v1.py',
             'english_observe_generation48_v1.py', 'english_feature_cache64_v1.py',
             'english_full_pilot_schedule_v1.py', 'english_zero_update_probe_v1.py',
             'train_english_paraphrase_pilot_windows_v1.py', 'eval_english_fresh_windows_v1.py']
    return {n: common.digest(HERE / n) for n in names if (HERE / n).is_file()}


def make_guards(rt, out, budget, project, wall):
    """Disk/output/wall guard plus CUDA reservation guard (CUDA only)."""
    import os
    import shutil
    torch = rt.torch
    out = Path(out)
    project = Path(project)

    def output_bytes():
        total = 0
        if out.exists():
            for base, _, files in os.walk(out):
                for name in files:
                    try:
                        total += (Path(base) / name).stat().st_size
                    except FileNotFoundError:
                        pass
        return total

    def guard(additional=0, check_wall=True):
        used = output_bytes()
        free = shutil.disk_usage(project).free
        if used + additional > budget['new_output_bytes'] or free - additional < budget['retained_free_bytes']:
            raise RuntimeError('output/free disk cap exceeded; preserve evidence')
        if check_wall:
            wall.check()
        return {'output_bytes': used, 'free_bytes': free}

    def gpu_guard():
        if not common.cuda_available(torch):
            return {'device': 'cpu'}
        peak = torch.cuda.max_memory_reserved()
        if peak > budget['cuda_peak_reserved_cap_bytes']:
            raise RuntimeError('CUDA peak reservation cap exceeded')
        return {'peak_reserved_bytes': peak, 'reserved_bytes': torch.cuda.memory_reserved(),
                'allocated_bytes': torch.cuda.memory_allocated()}
    return guard, gpu_guard
