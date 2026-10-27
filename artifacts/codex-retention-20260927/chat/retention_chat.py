#!/usr/bin/env python3
"""C1: live request-scoped validation of saved dl-5 grid adapters.

No training, learned router, download, or domain inference. Every request must
carry an external domain_id: ``grid`` enables the adapter; ``general`` bypasses
it. Validation consumes a caller-frozen JSONL manifest and genuinely generates
on base, always-on, and scoped routes. Run only after PASSMARKS is committed.

General row: {"domain_id":"general","q":"...","kind":"capital","gold":"..."}
Grid row: {"domain_id":"grid","q":"...","prefix":"The number ... is ","gold":3}
General scoring uses dl-1's harm_right, including its optional ``letter`` field.
``--hash-manifest`` must be a separate JSON file already committed at HEAD:
{"revision":"87179e5c...", "snapshot_files":{"config.json":"<sha256>", ...},
 "model_code_files":{"/absolute/loaded/modeling.py":"<sha256>", ...}}.
List every local snapshot file, including weights and tokenizer files. Runtime
code hashes must include the loaded model/tokenizer classes, forward/generate,
chat-template implementation, B2.add_lora, and RequestScopedAdapter. The runner
verifies the listed bytes and loaded entry points; the directory name alone is
never treated as evidence of model provenance.
"""
from __future__ import annotations

import argparse
from contextlib import nullcontext
import gc
import hashlib
import inspect
import json
import os
import re
import subprocess
import sys
from pathlib import Path

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "implementation"))
PIN = "87179e5c1f455ef22e6223592d2d61351b525bfc"
ADAPTERS = Path("/Users/ben-hannan/premonition-models/dl5-adapters")
SIDECARS = ROOT / "artifacts/claude-dl5-20260926/gpu"
DOMAINS = ("general", "grid")
OUTPUT_DIR = Path(__file__).resolve().parent
PROBE_TOKENS = 6


def route(domain_id: str) -> bool:
    if domain_id not in DOMAINS:
        raise ValueError(f"caller must supply domain_id in {DOMAINS}; got {domain_id!r}")
    return domain_id == "grid"


def retention(before: list[bool], after: list[bool]) -> dict:
    if not before or len(before) != len(after):
        raise ValueError("aligned, nonempty answers required")
    return {"n": len(before), "base_correct": sum(before), "right": sum(after),
            "lost_base_correct": sum(b and not a for b, a in zip(before, after)),
            "gained_base_wrong": sum(not b and a for b, a in zip(before, after))}


def read_manifest(path: Path) -> tuple[list[dict], str]:
    raw = path.read_bytes()
    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    if not rows:
        raise ValueError("empty manifest")
    for i, row in enumerate(rows):
        if not isinstance(row, dict) or not isinstance(row.get("q"), str) or not row["q"]:
            raise ValueError(f"row {i}: nonempty q required")
        route(row.get("domain_id"))
        if row["domain_id"] == "grid":
            if not isinstance(row.get("prefix"), str) or type(row.get("gold")) is not int \
                    or row["gold"] not in range(1, 6):
                raise ValueError(f"row {i}: grid needs prefix and integer gold 1..5")
        elif "kind" not in row or "gold" not in row:
            raise ValueError(f"row {i}: general needs kind and gold")
    return rows, hashlib.sha256(raw).hexdigest()


def score(row: dict, reply: str) -> bool:
    if row["domain_id"] == "grid":
        m = re.match(r"\s*([1-5])(?:\b|$)", reply)
        return bool(m and int(m.group(1)) == row["gold"])
    import claude_dl1_nights as nights
    return bool(nights.harm_right(row, reply))


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_snapshot(path: Path, manifest: dict) -> None:
    """Require exact, prelisted local files including weights, tokenizer and code."""
    if path.resolve().name != PIN or manifest.get("revision") != PIN:
        raise ValueError("snapshot path and committed manifest must name the pinned revision")
    expected = manifest.get("snapshot_files")
    if not isinstance(expected, dict) or not expected:
        raise ValueError("manifest needs snapshot_files hashes")
    actual_paths = {str(p.relative_to(path)) for p in path.rglob("*") if p.is_file()}
    if set(expected) != actual_paths:
        raise ValueError(f"snapshot file list differs: missing={sorted(actual_paths - set(expected))[:3]}, "
                         f"extra={sorted(set(expected) - actual_paths)[:3]}")
    if "config.json" not in expected or not any(k.endswith((".safetensors", ".bin")) for k in expected):
        raise ValueError("manifest must cover config and model weights")
    if not any(Path(k).name.startswith(("tokenizer", "vocab", "merges", "special_tokens_map", "added_tokens"))
               for k in expected):
        raise ValueError("manifest must cover tokenizer files")
    for name, want in expected.items():
        if Path(name).is_absolute() or ".." in Path(name).parts or not re.fullmatch(r"[0-9a-f]{64}", want):
            raise ValueError(f"invalid snapshot file entry {name!r}")
        if sha_file(path / name) != want:
            raise ValueError(f"snapshot hash mismatch: {name}")
    code = manifest.get("model_code_files")
    if not isinstance(code, dict) or not code:
        raise ValueError("manifest must hash installed model and tokenizer implementation code")
    for name, want in code.items():
        code_path = Path(name)
        if not code_path.is_absolute() or code_path.suffix != ".py" or not re.fullmatch(r"[0-9a-f]{64}", want):
            raise ValueError(f"invalid model code entry {name!r}")
        if not code_path.is_file() or sha_file(code_path) != want:
            raise ValueError(f"model code hash mismatch: {name}")


def committed_manifest(manifest_path: Path, model_path: Path) -> tuple[dict, str, str]:
    """Read manifest bytes from HEAD, then verify local bytes are identical."""
    manifest_path = manifest_path.resolve()
    try:
        relative = manifest_path.relative_to(ROOT)
    except ValueError as exc:
        raise ValueError("hash manifest must be committed in this repository") from exc
    try:
        committed = subprocess.run(["git", "-C", str(ROOT), "show", f"HEAD:{relative.as_posix()}"],
                                   check=True, capture_output=True).stdout
        head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                              check=True, capture_output=True, text=True).stdout.strip()
    except subprocess.CalledProcessError as exc:
        raise ValueError("hash manifest is not available in HEAD") from exc
    if manifest_path.read_bytes() != committed:
        raise ValueError("working hash manifest differs from committed HEAD")
    manifest = json.loads(committed)
    check_snapshot(model_path.resolve(), manifest)
    return manifest, hashlib.sha256(committed).hexdigest(), head


def check_runtime_code(manifest: dict, model, tok) -> None:
    import claude_blurt2 as blurt
    from retention import RequestScopedAdapter

    listed = manifest["model_code_files"]
    sources = (model.__class__, model.forward, model.generate, tok.__class__,
               tok.apply_chat_template, blurt.add_lora, RequestScopedAdapter)
    for source in sources:
        path = Path(inspect.getfile(source)).resolve()
        if str(path) not in listed or sha_file(path) != listed[str(path)]:
            raise ValueError(f"unhashed loaded model/tokenizer class code: {path}")


def load_model(path: Path, device: str, dtype_name: str):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    path = path.resolve()
    if path.name != PIN or not (path / "config.json").is_file():
        raise SystemExit(f"require existing local MiniCPM5-1B snapshot named {PIN}")
    if device == "mps" and not torch.backends.mps.is_available():
        raise SystemExit("MPS unavailable; refusing silent CPU fallback")
    tok = AutoTokenizer.from_pretrained(path, trust_remote_code=True, local_files_only=True)
    dtype = {"bf16": torch.bfloat16, "fp32": torch.float32, "fp16": torch.float16}[dtype_name]
    model = AutoModelForCausalLM.from_pretrained(path, trust_remote_code=True,
                                                  local_files_only=True, dtype=dtype).to(device).eval()
    for parameter in model.parameters():
        parameter.requires_grad_(False)
    return torch, tok, model


def install_controller(model):
    import claude_blurt2 as blurt
    from retention import RequestScopedAdapter

    blurt.add_lora(model)
    model.eval()
    return RequestScopedAdapter(model)


def wrap_controller(model):
    """Wrap an already loaded, original B2 LoRA after reference collection."""
    from retention import RequestScopedAdapter
    model.eval()
    return RequestScopedAdapter(model)


def load_adapter(torch, model, seed: int) -> str:
    name = f"dl5-S-s{seed}"
    path = ADAPTERS / f"{name}.pt"
    meta = json.loads((SIDECARS / f"{name}.json").read_text(encoding="utf-8"))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != meta["sha256"]:
        raise SystemExit(f"{name}: adapter hash mismatch")
    weights = torch.load(path, map_location="cpu", weights_only=True)
    expected = {k for k in model.state_dict() if k.endswith((".A", ".B"))}
    if not isinstance(weights, dict) or set(weights) != expected or len(expected) != meta["tensors"]:
        raise SystemExit(f"{name}: expected exactly the saved A/B tensors; base keys forbidden")
    if any(not torch.is_tensor(value) for value in weights.values()):
        raise SystemExit(f"{name}: adapter has a non-tensor value")
    model.load_state_dict(weights, strict=False)
    model.eval()
    return digest


def encode_row(tok, row: dict, device: str):
    prompt = tok.apply_chat_template([{"role": "user", "content": row["q"]}], tokenize=False,
                                     add_generation_prompt=True, enable_thinking=False) + row.get("prefix", "")
    return tok(prompt, return_tensors="pt").to(device)


def tensor_hash(tensor) -> str:
    value = tensor.detach().cpu().contiguous()
    digest = hashlib.sha256(f"{value.dtype}:{tuple(value.shape)}\n".encode())
    digest.update(value.view(__import__("torch").uint8).numpy().tobytes())
    return digest.hexdigest()


def probe_model(torch, model, ids, eos_token_id: int, controller=None, enabled=False) -> dict:
    """Compact bitwise prefill and cached autoregressive references."""
    scope = controller.scope(enabled) if controller is not None else nullcontext()
    with scope, torch.inference_mode():
        prefill = model(**ids, use_cache=False, return_dict=True).logits
        prefill_hash = tensor_hash(prefill)
    kw = dict(**ids, max_new_tokens=PROBE_TOKENS, min_new_tokens=PROBE_TOKENS,
              do_sample=False, pad_token_id=eos_token_id, use_cache=True,
              return_dict_in_generate=True, output_scores=True)
    with torch.inference_mode():
        result = controller.generate(enabled=enabled, **kw) if controller is not None else model.generate(**kw)
    if len(result.scores) != PROBE_TOKENS or getattr(result, "past_key_values", None) is None:
        raise RuntimeError("reference generation did not report six cached decode steps")
    return {"prefill_logits_sha256": prefill_hash,
            "decode_score_sha256": [tensor_hash(value) for value in result.scores],
            "output_token_ids": result.sequences.detach().cpu().tolist()}


def generate(torch, tok, controller, row: dict, device: str, enabled: bool) -> str:
    ids = encode_row(tok, row, device)
    cut = ids["input_ids"].shape[1]
    max_new = 4 if row["domain_id"] == "grid" else 16
    with torch.inference_mode():
        out = controller.generate(enabled=enabled, **ids, max_new_tokens=max_new,
                                  do_sample=False, pad_token_id=tok.eos_token_id,
                                  use_cache=True)
    return tok.decode(out[0][cut:], skip_special_tokens=True).strip()


def prepare_seed(args, seed: int, probe_rows: list[dict], manifest: dict):
    """One model at a time: base refs, original B2 refs, then scoped parity."""
    import claude_blurt2 as blurt

    torch, tok, model = load_model(args.model, args.device, args.dtype)
    check_runtime_code(manifest, model, tok)
    ids = [encode_row(tok, row, args.device) for row in probe_rows]
    base_refs = [probe_model(torch, model, item, tok.eos_token_id) for item in ids]
    blurt.add_lora(model)
    model.eval()
    adapter_sha = load_adapter(torch, model, seed)
    adapter_refs = [probe_model(torch, model, item, tok.eos_token_id) for item in ids]
    controller = wrap_controller(model)
    base_digest = controller.base_digest()
    for i, item in enumerate(ids):
        for label, on, reference in (("base", False, base_refs[i]),
                                     ("adapter", True, adapter_refs[i]),
                                     ("base-again", False, base_refs[i])):
            actual = probe_model(torch, model, item, tok.eos_token_id, controller, on)
            if actual != reference:
                raise RuntimeError(f"seed {seed} prompt {i}: scoped {label} differs from unwrapped reference")
    parity = {"checked_prompts": len(ids), "cached_decode_steps_each": PROBE_TOKENS,
              "bit_identical": True,
              "references": [{"prompt_sha256": hashlib.sha256(row["q"].encode()).hexdigest(),
                              "base": b, "original_b2_lora": a}
                             for row, b, a in zip(probe_rows, base_refs, adapter_refs)]}
    return torch, tok, model, controller, adapter_sha, base_digest, parity


def serve(args) -> None:
    row = {"domain_id": args.domain_id, "q": args.question, "prefix": args.prefix}
    manifest, manifest_sha, head = committed_manifest(args.hash_manifest, args.model)
    torch, tok, model, controller, digest, before, parity = prepare_seed(args, args.seed, [row], manifest)
    reply = generate(torch, tok, controller, row, args.device, route(args.domain_id))
    if controller.base_digest() != before:
        raise RuntimeError("base tensors or buffers changed during serving")
    print(json.dumps({"reply": reply, "domain_id": args.domain_id,
                      "adapter_on": route(args.domain_id), "adapter_sha256": digest,
                      "dtype": args.dtype, "device": args.device, "hash_manifest_sha256": manifest_sha,
                      "manifest_commit": head, "reference_parity": parity["bit_identical"]}))


def write_exclusive(path: Path, value) -> None:
    with path.open("x", encoding="utf-8") as file:
        json.dump(value, file, indent=2)
        file.write("\n")


def validate(args) -> None:
    rows, manifest_sha = read_manifest(args.manifest)
    if args.out.resolve().parent != OUTPUT_DIR:
        raise SystemExit(f"output must be inside {OUTPUT_DIR}")
    output_paths = [args.out] + [args.out.with_name(f"{args.out.stem}-replies-s{seed}.json") for seed in (8, 9)]
    if any(path.exists() for path in output_paths):
        raise SystemExit("output or reply sidecar exists; preserve the earlier validation")
    probes = []
    for domain in DOMAINS:
        selected = [row for row in rows if row["domain_id"] == domain][:2]
        if len(selected) < 2:
            raise ValueError(f"manifest needs at least two {domain} rows for parity probes")
        probes.extend(selected)
    hash_manifest, hash_manifest_sha, head = committed_manifest(args.hash_manifest, args.model)
    report = {"manifest_sha256": manifest_sha, "base_revision_label": PIN,
              "hash_manifest_sha256": hash_manifest_sha, "hash_manifest_commit": head,
              "dtype": args.dtype, "device": args.device, "n": len(rows),
              "domain_counts": {d: sum(x["domain_id"] == d for x in rows) for d in DOMAINS},
              "seeds": {}, "scope": "externally supplied domain ID; no learned router"}
    for seed in (8, 9):
        torch, tok, model, controller, digest, base_digest, parity = prepare_seed(args, seed, probes, hash_manifest)
        details = []
        for row in rows:
            on = route(row["domain_id"])
            # Each route starts a separate model.generate with a fresh cache.
            replies = {name: generate(torch, tok, controller, row, args.device, enabled)
                       for name, enabled in (("base", False), ("always", True), ("scoped", on))}
            details.append({"domain_id": row["domain_id"], "replies": replies,
                            "right": {k: score(row, v) for k, v in replies.items()},
                            "scoped_adapter_on": on})
        domains = {}
        for domain in DOMAINS:
            subset = [x for x in details if x["domain_id"] == domain]
            if not subset:
                continue
            base = [x["right"]["base"] for x in subset]
            domains[domain] = {mode: retention(base, [x["right"][mode] for x in subset])
                               for mode in ("base", "always", "scoped")}
            domains[domain]["scoped_adapter_on"] = sum(x["scoped_adapter_on"] for x in subset)
            reference = "always" if domain == "grid" else "base"
            domains[domain]["scoped_reply_equal_expected_route"] = sum(
                x["replies"]["scoped"] == x["replies"][reference] for x in subset)
        if controller.base_digest() != base_digest:
            raise RuntimeError(f"seed {seed}: base tensors or buffers changed during serving")
        report["seeds"][str(seed)] = {"adapter_sha256": digest, "base_digest_unchanged": True,
                                      "reference_parity": parity, "domains": domains}
        reply_path = args.out.with_name(f"{args.out.stem}-replies-s{seed}.json")
        write_exclusive(reply_path, details)
        del controller, model
        gc.collect()
        if args.device == "mps":
            torch.mps.empty_cache()
    write_exclusive(args.out, report)
    print(json.dumps(report, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("serve", "validate"))
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--hash-manifest", type=Path, required=True,
                        help="Committed JSON manifest of exact snapshot and runtime code file hashes")
    parser.add_argument("--device", choices=("mps", "cpu"), default="mps")
    parser.add_argument("--dtype", choices=("bf16", "fp32", "fp16"), default="bf16")
    parser.add_argument("--seed", choices=(8, 9), type=int, default=8)
    parser.add_argument("--domain-id", choices=DOMAINS)
    parser.add_argument("--question")
    parser.add_argument("--prefix", default="")
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.command == "serve":
        if not args.domain_id or not args.question:
            parser.error("serve needs --domain-id and --question")
        serve(args)
    else:
        if not args.manifest or not args.out:
            parser.error("validate needs --manifest and --out")
        validate(args)


if __name__ == "__main__":
    main()
