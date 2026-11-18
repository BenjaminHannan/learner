"""Load LFM3 from the vendored model code (vendor/) and a LOCAL weights directory: no trust_remote_code, nothing fetched at load time.
    net = load_model("~/learner-ops/models/lfm3-1.7b-hf", dtype=torch.float16)
needs a recent transformers (the vendored file imports transformers.initialization, present in 5.x; the HF repo was written by 5.12.1) and torch."""
import hashlib, importlib, importlib.util, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
VENDOR = os.path.join(HERE, "vendor")
PKG = "lfm3_vendor"
PINNED_REVISION = "40ebe0aa6662c9d40389c2f5d565b6a2c6aebacd"
HASHES = {   # sha256 of the vendored files (also listed in vendor/README.md)
    "modeling_lfm3.py": "e8cd5254ea99ce6bd731b57b10908c2e8b5010ce8315341f895a38484885eeab",
    "lfm3_conv.py": "80d4a985382a22774212759248a6b4c737bfbf9c2a47b3dd7f797dda748e4bb4",
    "configuration_lfm3.py": "176cced35657aedfea7d7002221360582d1c05fcaca882c21508bc3a73b282e5",
    "config.json": "8c6ae8b8f6d88c87cfb98cf4b5e34e943d0ee07e24215c4121b3159a46e1399d",
}
# LFM3-FACTS.md: attention q/k/v/o, short-conv in/out, feed-forward w1/w2/w3 (not the heads-sized attention gate_proj, not the depthwise conv kernel)
TARGET_REGEX = r".*\.layers\.\d+\.(self_attn\.(q_proj|k_proj|v_proj|o_proj)|conv\.(in_proj|out_proj)|feed_forward\.(w1|w2|w3))"
MODULE_KINDS = ("q_proj", "k_proj", "v_proj", "o_proj", "in_proj", "out_proj", "w1", "w2", "w3")


def check_hashes(vendor=VENDOR):
    """-> list of files whose sha256 differs from the pinned one (empty = vendored copy intact)."""
    return [f for f, h in HASHES.items() if hashlib.sha256(open(os.path.join(vendor, f), "rb").read()).hexdigest() != h]


def vendored():
    """-> (modeling module, configuration module), imported from vendor/ as the package `lfm3_vendor`."""
    if PKG not in sys.modules:
        spec = importlib.util.spec_from_file_location(PKG, os.path.join(VENDOR, "__init__.py"), submodule_search_locations=[VENDOR])
        pkg = importlib.util.module_from_spec(spec)
        sys.modules[PKG] = pkg
        spec.loader.exec_module(pkg)
    return importlib.import_module(PKG + ".modeling_lfm3"), importlib.import_module(PKG + ".configuration_lfm3")


def load_model(path, dtype=None, device=None):
    """Lfm3ForCausalLM with the weights in `path` (a local HF snapshot dir). Never trust_remote_code, never the network."""
    modeling, _ = vendored()
    path = os.path.expanduser(path)
    if not os.path.isdir(path):
        raise FileNotFoundError(f"HF weights dir not found: {path} (run_m3.sh downloads it)")
    try:
        net = modeling.Lfm3ForCausalLM.from_pretrained(path, dtype=dtype, local_files_only=True)
    except TypeError:       # transformers < 4.56 spells it torch_dtype
        net = modeling.Lfm3ForCausalLM.from_pretrained(path, torch_dtype=dtype, local_files_only=True)
    if device:
        net.to(device)
    return net


def tiny_config(vocab_size=128000):
    """A few-million-parameter Lfm3Config of the same architecture (conv + both attention kinds), for tests and smoke runs."""
    _, cfgmod = vendored()
    import json
    base = json.load(open(os.path.join(VENDOR, "config.json")))
    base.pop("auto_map", None)
    base.update(hidden_size=64, intermediate_size=128, num_hidden_layers=4, num_attention_heads=4, num_key_value_heads=2, head_dim=16, vocab_size=vocab_size,
                layer_types=["conv", "full_attention", "conv", "sliding_attention"], sliding_window=32, max_position_embeddings=32768, dtype="float32")
    if vocab_size <= max(base["bos_token_id"], base["eos_token_id"], base["pad_token_id"]):       # a smaller vocabulary than the tokenizer's (tests): keep the special ids inside it
        base.update(pad_token_id=0, bos_token_id=1, eos_token_id=2)
    return cfgmod.Lfm3Config(**base)
