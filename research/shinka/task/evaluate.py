"""ShinkaEvolve scorer for the binding toy (see research/shinka/CARD.md).

Usage (called by ShinkaEvolve):
  python evaluate.py --program_path gen_N/main.py --results_dir gen_N/results
Writes metrics.json and correct.json. `--seeds` overrides the seeds, which is
used only for the noise and fresh-seed runs, never during evolution.
"""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import toy  # noqa: E402

EVOLVE_SEEDS = (0, 1, 2)

# The candidate only gets reader states. The source is checked on its syntax tree:
#   - top level: only imports, class/function definitions and constant assignments,
#     so no code runs at import time;
#   - imports: only math, torch, torch.nn, torch.nn.functional;
#   - every attribute path that starts at a module (torch.x.y, nn.x, F.x, math.x) must be
#     on an ALLOW-list (torch re-exports builtins/importlib/ctypes/overrides, so a
#     deny-list is not enough), and module names may not be used as bare values (no aliasing);
#   - no name, attribute, function, class or argument that starts with "_" (except __init__);
#   - attribute assignment only on self (self.x = ...);
#   - no builtins that reach code, files or objects (open, exec, getattr, type, ...);
#   - no generators or async code.
# The check is a first line of defence only. The real boundary is process isolation:
# toy.run_seed runs the writer in a child process (task/worker.py) that sees reader
# states and nothing else, while the parent keeps labels, answerer, loss, metrics and
# the behavioural checks (no state kept between calls, each card from its own line).
# Finalists are also read by hand.
_TORCH_FUNCS = set("""
einsum softmax log_softmax sigmoid tanh relu exp log log1p expm1 sqrt rsqrt abs sign clamp clamp_min
clamp_max cat stack split chunk zeros ones zeros_like ones_like full full_like empty empty_like eye
arange linspace randn rand randn_like rand_like randint matmul bmm mm outer dot cross sum mean max min
amax amin argmax argmin topk sort argsort cumsum cumprod prod std var norm where masked_fill gather
scatter scatter_add index_select tril triu diag diagonal diag_embed roll flip transpose permute reshape
unsqueeze squeeze flatten broadcast_to tensor as_tensor float32 float64 float bool long int64 no_grad
enable_grad is_tensor numel logsumexp erf pow square reciprocal maximum minimum lerp addcmul baddbmm
cosine_similarity cdist nan inf pi e Tensor finfo tensordot kron cos sin atan2 floor ceil round
nan_to_num isfinite isnan isinf clip logical_and logical_or logical_not any all eq ne gt lt ge le
mul add sub div fmod remainder trunc frac sinh cosh asin acos atan hypot sigmoid_ logit
count_nonzero bincount unique searchsorted bucketize nonzero masked_select heaviside
linalg fft special nn
""".split())
_F_FUNCS = set("""
softmax log_softmax gelu relu silu elu leaky_relu sigmoid tanh softplus normalize layer_norm linear
cosine_similarity dropout pad one_hot gumbel_softmax glu mse_loss cross_entropy logsigmoid hardtanh
softsign scaled_dot_product_attention multi_head_attention_forward softmin mish hardswish
hardsigmoid selu celu prelu rrelu tanhshrink softshrink hardshrink threshold relu6 embedding
conv1d avg_pool1d max_pool1d adaptive_avg_pool1d adaptive_max_pool1d unfold fold pairwise_distance
kl_div binary_cross_entropy_with_logits smooth_l1_loss l1_loss local_response_norm group_norm
instance_norm batch_norm rms_norm
""".split())
_NN_ATTRS = set("""
Module Linear Parameter ModuleList ModuleDict Sequential LayerNorm GELU ReLU Tanh Sigmoid SiLU
Embedding Dropout Identity GRU LSTM GRUCell LSTMCell Conv1d MultiheadAttention Softmax ParameterList
Bilinear init functional Softplus LeakyReLU ELU Hardtanh Mish SELU PReLU RMSNorm GroupNorm
BatchNorm1d TransformerEncoderLayer TransformerEncoder Unflatten Flatten RNN RNNCell
Softsign Softmin LogSoftmax GLU AvgPool1d MaxPool1d AdaptiveAvgPool1d ParameterDict
""".split())
_INIT_FUNCS = set("xavier_uniform_ xavier_normal_ kaiming_uniform_ kaiming_normal_ normal_ uniform_ zeros_ ones_ orthogonal_ constant_ eye_".split())
_ALLOW = {
    "torch": _TORCH_FUNCS,
    "torch.linalg": set("norm vector_norm matrix_norm qr svd eigh inv solve det".split()),
    "torch.fft": set("fft ifft rfft irfft".split()),
    "torch.special": set("erf expit logit".split()),
    "torch.nn": _NN_ATTRS,
    "torch.nn.init": _INIT_FUNCS,
    "torch.nn.functional": _F_FUNCS,
}
ALLOWED_MODULES = {"math", "torch", "torch.nn", "torch.nn.functional", "__future__"}
DENIED_NAMES = {
    "open", "exec", "eval", "compile", "globals", "locals", "getattr", "setattr", "delattr",
    "vars", "breakpoint", "input", "type", "memoryview", "help", "exit", "quit", "object",
}
# Attributes that are never allowed, on any object (tensor and module methods included).
DENIED_ATTRS = {
    "load", "save", "from_file", "frombuffer", "storage", "untyped_storage", "numpy", "tofile",
    "register_forward_hook", "register_forward_pre_hook", "register_full_backward_hook",
    "register_backward_hook", "register_module_forward_hook", "register_hook",
    "load_state_dict", "cuda", "mps", "to_sparse", "share_memory_",
    "f_back", "f_locals", "f_globals", "f_code", "tb_frame", "gi_frame", "cr_frame", "ag_frame",
}


def _small_literal(node) -> bool:
    """A literal constant such as -1e9, (1, 2) or 1 / 8: numbers, short strings, tuples of
    them, and + - * / between two numbers. No powers, no big repetition."""
    import ast
    if isinstance(node, ast.Constant):
        return not isinstance(node.value, (str, bytes)) or len(node.value) <= 200
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        return isinstance(node.operand, ast.Constant) and isinstance(node.operand.value, (int, float))
    if isinstance(node, ast.Tuple):
        return len(node.elts) <= 64 and all(_small_literal(e) for e in node.elts)
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
        def num(x):
            return (isinstance(x, ast.Constant) and isinstance(x.value, (int, float))
                    and abs(x.value) < 1e9) or (isinstance(x, ast.UnaryOp) and num(x.operand))
        return num(node.left) and num(node.right)
    return False


def _dotted(node):
    """('torch', ['nn', 'functional', 'relu']) for torch.nn.functional.relu, else None."""
    import ast
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        return node.id, parts[::-1]
    return None


def static_check(source: str) -> str | None:
    """Return a reason the program is rejected, or None if it passes."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return f"syntax error: {exc}"
    roots: dict[str, str] = {}   # local alias -> module path
    for stmt in tree.body:
        if isinstance(stmt, (ast.Import, ast.ImportFrom, ast.ClassDef, ast.FunctionDef)):
            continue
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
            continue  # docstring
        if isinstance(stmt, (ast.Assign, ast.AnnAssign)) and stmt.value is not None:
            targets = stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]
            if not all(isinstance(t, ast.Name) for t in targets) or \
                    (isinstance(stmt, ast.AnnAssign) and not isinstance(stmt.annotation, ast.Name)):
                return f"top-level assignment must be NAME = constant (line {stmt.lineno})"
            if _small_literal(stmt.value):
                continue
        return f"top-level statement not allowed (line {stmt.lineno}): only imports, defs and constants"
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name not in ALLOWED_MODULES:
                    return f"import not allowed: {alias.name} (only math, torch, torch.nn, torch.nn.functional)"
                if alias.asname:
                    roots[alias.asname] = alias.name
                else:
                    roots[alias.name.split(".")[0]] = alias.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom):
            if node.module not in ALLOWED_MODULES or node.level:
                return f"import not allowed: from {node.module}"
            for alias in node.names:
                if node.module == "__future__":
                    continue
                full = f"{node.module}.{alias.name}"
                ok = (node.module == "math" and not alias.name.startswith("_")) or \
                    alias.name in _ALLOW.get(node.module, set())
                if not ok:
                    return f"import not allowed: from {node.module} import {alias.name}"
                if full in _ALLOW:  # a submodule, e.g. from torch.nn import functional as F
                    roots[alias.asname or alias.name] = full
    defined = {n.name for n in ast.walk(tree) if isinstance(n, (ast.ClassDef, ast.FunctionDef))}
    defined |= set(roots)
    for n in ast.walk(tree):  # names imported from torch (e.g. Module, Tensor) are torch objects
        if isinstance(n, ast.ImportFrom):
            defined |= {al.asname or al.name for al in n.names}
    for node in ast.walk(tree):
        if isinstance(node, (ast.Yield, ast.YieldFrom, ast.Await, ast.AsyncFunctionDef,
                             ast.AsyncWith, ast.AsyncFor, ast.Global, ast.Nonlocal, ast.Match)):
            return f"{type(node).__name__} not allowed"
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name.startswith("_") \
                and node.name != "__init__":
            return f"definition name not allowed: {node.name}"
        if isinstance(node, ast.arg) and node.arg.startswith("_"):
            return f"argument name not allowed: {node.arg}"
        if isinstance(node, ast.Name):
            if node.id in DENIED_NAMES or (node.id.startswith("__")):
                return f"name not allowed: {node.id}"
        if isinstance(node, ast.Attribute):
            if node.attr in DENIED_ATTRS or (node.attr.startswith("_") and node.attr != "__init__"):
                return f"attribute not allowed: .{node.attr}"
            if isinstance(node.ctx, (ast.Store, ast.Del)):
                # state may not be attached to classes, functions or torch objects, where
                # the number count cannot see it; self.x = ... and local objects are fine
                root = _dotted(node)
                if root is not None and (root[0] in defined or root[0] in ("nn", "torch", "F", "math")):
                    return f"attribute assignment on {root[0]} is not allowed (use self.x = ...)"
    # attribute paths rooted at a module must be allow-listed; bare module names are not values
    parent_of = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parent_of[id(child)] = node
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in roots:
            par = parent_of.get(id(node))
            if not (isinstance(par, ast.Attribute) and par.value is node):
                return f"module '{node.id}' may only be used as module.attribute"
            top = par
            while isinstance(parent_of.get(id(top)), ast.Attribute) and parent_of[id(top)].value is top:
                top = parent_of[id(top)]
            if isinstance(top.ctx, (ast.Store, ast.Del)):
                return f"assigning to a module attribute is not allowed: {node.id}..."
            root, parts = _dotted(top)
            path = roots[root]
            if path == "math":
                continue
            for part in parts:
                if part not in _ALLOW[path]:
                    return f"attribute not allowed: {path}.{part}"
                path = f"{path}.{part}"
                if path not in _ALLOW:
                    break  # reached a function or class; later attributes are on its result
            else:
                # the whole path names a module (e.g. nn.functional): not usable as a value
                return f"module path may only be used as module.attribute: {path}"
    return None


# Behaviour descriptor for the strange slot: how the key and the value respond to
# each token role. Accuracies are left out so that distance is not just score gap.
DESCRIPTOR_KEYS = ("dk_person", "dk_rel", "dk_val", "dk_fill",
                   "dv_person", "dv_rel", "dv_val", "dv_fill")


def _failure(error: str) -> dict:
    return {"combined_score": 0.0, "public": {"error": error[:500]}, "private": {},
            "text_feedback": f"Program failed: {error[:1500]}"}


def _feedback(m: dict) -> str:
    return (
        f"Held-out answer accuracy: familiar names {m['acc_familiar']:.3f}, NOVEL names {m['acc_novel']:.3f}. "
        f"Right card picked: familiar {m['pick_familiar']:.3f}, novel {m['pick_novel']:.3f}. "
        f"Errors that pick the same relation of ANOTHER person (person lost): "
        f"familiar {m['err_person_lost_familiar']:.3f}, novel {m['err_person_lost_novel']:.3f}. "
        f"Errors that pick another relation of the same person: novel {m['err_relation_lost_novel']:.3f}. "
        f"Key sensitivity share (person/relation/value/filler): "
        f"{m['dk_person']:.2f}/{m['dk_rel']:.2f}/{m['dk_val']:.2f}/{m['dk_fill']:.2f}; "
        f"value sensitivity share: {m['dv_person']:.2f}/{m['dv_rel']:.2f}/{m['dv_val']:.2f}/{m['dv_fill']:.2f}. "
        f"Writer params {int(m['writer_params'])} (cap {toy.ToyConfig().max_writer_params})."
    )


def evaluate(program_path: str, seeds=EVOLVE_SEEDS) -> tuple[dict, bool, str]:
    source = Path(program_path).read_text(encoding="utf-8")
    bad = static_check(source)
    if bad:
        msg = f"rejected by sandbox: {bad}"
        return _failure(msg), False, msg
    try:
        # the candidate is imported only inside the writer's child process (task/worker.py)
        result = toy.run((str(Path(program_path).resolve()), "CardWriter", False), seeds)
    except Exception as exc:  # noqa: BLE001
        msg = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()[-1200:]}"
        return _failure(msg), False, msg
    m = result["mean"]
    if not all(v == v for v in m.values()):  # NaN check
        return _failure("NaN in metrics"), False, "NaN in metrics"
    metrics = {
        "combined_score": m["score"],
        "public": {k: round(v, 4) for k, v in m.items()},
        "private": {"per_seed": result["per_seed"], "seeds": list(seeds),
                    "descriptor": [m[k] for k in DESCRIPTOR_KEYS]},
        "text_feedback": _feedback(m),
    }
    return metrics, True, ""


def main(program_path: str, results_dir: str, seeds=EVOLVE_SEEDS) -> None:
    metrics, correct, error = evaluate(program_path, seeds)
    out = Path(results_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    (out / "correct.json").write_text(json.dumps({"correct": correct, "error": error}, indent=2),
                                      encoding="utf-8")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--program_path", required=True)
    ap.add_argument("--results_dir", required=True)
    ap.add_argument("--seeds", default=None, help="comma-separated; default = evolution seeds")
    a = ap.parse_args()
    seeds = tuple(int(s) for s in a.seeds.split(",")) if a.seeds else EVOLVE_SEEDS
    main(a.program_path, a.results_dir, seeds)
