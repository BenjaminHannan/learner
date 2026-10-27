"""Shared bits of the MLX port of Probe-3 (Addendum 1): constants copied from train_lora.py (a test pins them), prompt/label encoding, the K2 loader, memory limits.
No torch here: the Mac venv has mlx-lm, transformers, tokenizers only."""
import importlib.util, json, math, os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
P3 = os.path.dirname(HERE)
CREATIVE = os.path.dirname(P3)
sys.path.insert(0, os.path.join(CREATIVE, "probe1"))   # write_probes / probe_common / analyze (plain python, shared with the CUDA lane)
MODEL = "IFM/K2-Horizon-3.7B"
TEMPLATE = os.path.join(CREATIVE, "guess1", "k2_nothink.jinja")
VENDORED = os.path.join(HERE, "k2_horizon_mlx.py")
END_OF_TURN = "<|ifm|im_end|>"
TARGETS = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
LORA_KEYS = ["self_attn." + p for p in TARGETS[:4]] + ["mlp." + p for p in TARGETS[4:]]   # module paths inside a decoder layer
R, ALPHA, DROPOUT, LR, WARMUP, EPOCHS, BATCH, SEED = 16, 32, 0.05, 1e-4, 0.03, 2, 16, 0   # == train_lora.py
TINY = dict(hidden_size=64, num_hidden_layers=2, num_attention_heads=4, num_key_value_heads=2, head_dim=16, rope_head_dim=16, intermediate_size=128, mlp_only_layers=[0, 1])


def read_jsonl(p):
    return [json.loads(l) for l in open(p) if l.strip()]


def encode(tok, tpl, prompt, target, max_len=None):
    """-> (input_ids, labels), the same as train_lora.encode (a test compares them): labels = -100 on the generation prompt, token ids of target + <|ifm|im_end|> after it."""
    user = [dict(role="user", content=prompt)]
    p = tok.apply_chat_template(user, chat_template=tpl, add_generation_prompt=True, tokenize=False)
    full = tok.apply_chat_template(user + [dict(role="assistant", content=target)], chat_template=tpl, tokenize=False)
    assert full.startswith(p), "chat template: assistant turn does not extend the generation prompt"
    pi, ai = (tok(x, add_special_tokens=False)["input_ids"] for x in (p, full[len(p):]))
    ids = pi + ai
    return None if max_len and len(ids) > max_len else (ids, [-100] * len(pi) + ai)


def prompt_ids(tok, tpl, prompt):
    """Token ids of the generation prompt (exactly the text vLLM was given in Probe-2)."""
    p = tok.apply_chat_template([dict(role="user", content=prompt)], chat_template=tpl, add_generation_prompt=True, tokenize=False)
    return tok(p, add_special_tokens=False)["input_ids"]


def hf_tokenizer(model=MODEL):
    from transformers import AutoTokenizer
    return AutoTokenizer.from_pretrained(model, trust_remote_code=False)   # explicit: otherwise transformers asks on stdin; the tokenizer is a plain tokenizers-backed fast tokenizer


def stop_ids(tok, model_eos=None):
    """Ids that end a reply: the tokenizer's eos, the model config's eos and <|ifm|im_end|>."""
    s = {tok.convert_tokens_to_ids(END_OF_TURN)}
    for e in ([tok.eos_token_id] if tok.eos_token_id is not None else []) + (list(model_eos) if isinstance(model_eos, (list, tuple)) else [model_eos] if model_eos is not None else []):
        s.add(int(e))
    assert None not in s and tok.unk_token_id not in s, "end-of-turn token missing from the tokenizer"
    return sorted(s)


def arch_module():
    """mlx-lm's own k2_horizon if this mlx-lm has one, else the vendored copy (loaded through the `model_file` hook)."""
    if importlib.util.find_spec("mlx_lm.models.k2_horizon") is not None:
        import mlx_lm.models.k2_horizon as m
        return m, None
    spec = importlib.util.spec_from_file_location("k2_horizon_mlx", VENDORED)
    m = importlib.util.module_from_spec(spec)
    sys.modules["k2_horizon_mlx"] = m
    spec.loader.exec_module(m)
    return m, VENDORED


def load_k2(model=MODEL, tiny=False, adapter=None, revision=None):
    """-> (mlx model, model config dict). bf16 weights straight from the HF repo (never a quantized copy); tiny=True: random-init, same architecture, for the CPU smoke run."""
    import mlx.core as mx
    from huggingface_hub import hf_hub_download, snapshot_download
    from pathlib import Path
    arch, model_file = arch_module()
    if tiny:
        cfg = json.load(open(hf_hub_download(model, "config.json", revision=revision)))
        cfg.update(TINY)
        mx.random.seed(SEED)
        net = arch.Model(arch.ModelArgs.from_dict(cfg))
        mx.eval(net.parameters())
    else:
        from mlx_lm.utils import load_model
        path = Path(snapshot_download(model, revision=revision, allow_patterns=["*.json", "*.safetensors", "*.jinja"]))
        cfg0 = json.load(open(path / "config.json"))
        assert "quantization" not in cfg0 and "quantization_config" not in cfg0, f"{model} is quantized; Addendum 1 needs bf16"
        net, cfg = load_model(path, lazy=False, strict=True, model_config=dict(model_file=model_file) if model_file else None, trust_remote_code=True)
        import mlx.utils as mu
        dts = {str(v.dtype) for _, v in mu.tree_flatten(net.parameters())}
        print("weights loaded; dtypes:", sorted(dts), flush=True)
        assert dts == {"mlx.core.bfloat16"}, f"expected pure bf16 weights, got {dts}"
    if adapter:
        from mlx_lm.tuner.utils import load_adapters
        net = load_adapters(net, adapter)
        mx.eval(net.parameters())
    return net, cfg


def backbone_and_head(net):
    """K2 in mlx-lm: net.model (K2HorizonModel: embed_tokens, layers, final norm; returns normalised hidden states) and net.lm_head (untied nn.Linear). Tied -> embed_tokens.as_linear."""
    head = net.lm_head if hasattr(net, "lm_head") else net.model.embed_tokens.as_linear
    return net.model, head


def set_memory(limit_gb):
    """Cap MLX's memory use (soft limit) and its wired memory at limit_gb; the Mac shares RAM with another model server."""
    import mlx.core as mx
    if not limit_gb:
        return
    b = int(limit_gb * 2**30)
    mx.set_memory_limit(b)
    try:
        rec = mx.device_info().get("max_recommended_working_set_size", b)
        mx.set_wired_limit(min(b, int(rec * 0.9)))
    except Exception as e:  # noqa  (CPU backend / old mlx)
        print("wired limit not set:", e)
    print(f"memory limit {limit_gb} GB", flush=True)


def peak_gb():
    import mlx.core as mx
    return mx.get_peak_memory() / 2**30


def atomic_write(path, text):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        f.write(text)
    os.replace(tmp, path)


PRESSURE_NAMES = {1: "normal", 2: "warn", 4: "critical"}


def memory_pressure_level():
    """macOS kernel memory-pressure level: 1 normal, 2 warn, 4 critical. None where it cannot be read (Linux, tests)."""
    if sys.platform != "darwin":
        return None
    import subprocess
    try:
        return int(subprocess.run(["sysctl", "-n", "kern.memorystatus_vm_pressure_level"], capture_output=True, text=True, timeout=10).stdout.strip())
    except Exception:  # noqa
        return None


def pressure_ok(max_level=1):
    """(ok, message). Unreadable pressure counts as ok."""
    lv = memory_pressure_level()
    if lv is None or lv <= max_level:
        return True, ""
    return False, f"macOS memory pressure is {PRESSURE_NAMES.get(lv, lv)} (level {lv} > {max_level}); another process (the K2 q4 server?) needs the RAM"


EXIT_PRESSURE = 75   # "paused, rerun to resume"


OUT_NAMES = dict(tuned="probes_k2.jsonl", base="probes_k2base_mlx.jsonl")   # --arm -> probe file name (analyze.py reads probes_k2.jsonl; MLX-BASE is reported beside it)


def lr_at(step, warm, total):
    """transformers.get_cosine_schedule_with_warmup (as in train_lora.py): factor for optimizer step `step` (0-based) -> learning rate."""
    f = step / max(1, warm) if step < warm else 0.5 * (1 + math.cos(math.pi * (step - warm) / max(1, total - warm)))
    return LR * f


def epoch_orders(n, epochs, seed=SEED):
    """Same shuffles as train_lora.py: one Random(seed), a fresh list(range(n)) shuffled per epoch."""
    rng, out = random.Random(seed), []
    for _ in range(epochs):
        o = list(range(n))
        rng.shuffle(o)
        out.append(o)
    return out


def make_rows(chunk, prompts, outs, tok, max_tokens):
    """chunk: [(task, sample)], prompts: token-id lists, outs: generated token ids (stop token excluded) -> (probe rows in write_probes' record format, side-log rows)."""
    rows, logs = [], []
    for (t, s), p, toks in zip(chunk, prompts, outs):
        rows.append(_wp().record("k2", t["id"], s, tok.decode(toks, skip_special_tokens=True)))   # source "k2": analyze.py / replay treat the file exactly like the vLLM one
        logs.append(dict(key=f"{t['id']}|{s}", prompt_tokens=len(p), new_tokens=len(toks), hit_max=len(toks) >= max_tokens))
    return rows, logs


def _wp():
    import write_probes
    return write_probes
