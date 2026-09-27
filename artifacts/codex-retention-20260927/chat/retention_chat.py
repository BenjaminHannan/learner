#!/usr/bin/env python3
"""C1: live request-scoped validation of saved dl-5 grid adapters.

No training, learned router, download, or domain inference. Every request must
carry an external domain_id: ``grid`` enables the adapter; ``general`` bypasses
it. Validation consumes a caller-frozen JSONL manifest and genuinely generates
on base, always-on, and scoped routes. Run only after PASSMARKS is committed.

General row: {"domain_id":"general","q":"...","kind":"capital","gold":"..."}
Grid row: {"domain_id":"grid","q":"...","prefix":"The number ... is ","gold":3}
General scoring uses dl-1's harm_right, including its optional ``letter`` field.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
PIN = "87179e5c1f455ef22e6223592d2d61351b525bfc"
ADAPTERS = Path("/Users/ben-hannan/premonition-models/dl5-adapters")
SIDECARS = ROOT / "artifacts/claude-dl5-20260926/gpu"
DOMAINS = ("general", "grid")
OUTPUT_DIR = Path(__file__).resolve().parent


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


def load_model(path: Path, device: str):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    path = path.resolve()
    if path.name != PIN or not (path / "config.json").is_file():
        raise SystemExit(f"require existing local MiniCPM5-1B snapshot named {PIN}")
    if device == "mps" and not torch.backends.mps.is_available():
        raise SystemExit("MPS unavailable; refusing silent CPU fallback")
    tok = AutoTokenizer.from_pretrained(path, trust_remote_code=True, local_files_only=True)
    dtype = torch.float16 if device == "mps" else torch.float32
    model = AutoModelForCausalLM.from_pretrained(path, trust_remote_code=True,
                                                  local_files_only=True, dtype=dtype).to(device).eval()
    for parameter in model.parameters():
        parameter.requires_grad_(False)
    return torch, tok, model


def install_controller(model):
    import claude_blurt2 as blurt
    from premonition.retention import RequestScopedAdapter

    blurt.add_lora(model)
    model.eval()
    return RequestScopedAdapter(model)


def load_adapter(torch, controller, seed: int) -> str:
    name = f"dl5-S-s{seed}"
    path = ADAPTERS / f"{name}.pt"
    meta = json.loads((SIDECARS / f"{name}.json").read_text(encoding="utf-8"))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != meta["sha256"]:
        raise SystemExit(f"{name}: adapter hash mismatch")
    weights = torch.load(path, map_location="cpu", weights_only=True)
    if len(weights) != meta["tensors"] or set(weights) - set(controller.model.state_dict()):
        raise SystemExit(f"{name}: adapter does not fit scoped model")
    controller.model.load_state_dict(weights, strict=False)
    controller.model.eval()
    return digest


def generate(torch, tok, controller, row: dict, device: str, enabled: bool) -> str:
    prompt = tok.apply_chat_template([{"role": "user", "content": row["q"]}], tokenize=False,
                                     add_generation_prompt=True, enable_thinking=False) + row.get("prefix", "")
    ids = tok(prompt, return_tensors="pt").to(device)
    cut = ids["input_ids"].shape[1]
    max_new = 4 if row["domain_id"] == "grid" else 16
    with torch.inference_mode():
        out = controller.generate(enabled=enabled, **ids, max_new_tokens=max_new,
                                  do_sample=False, pad_token_id=tok.eos_token_id,
                                  use_cache=True)
    return tok.decode(out[0][cut:], skip_special_tokens=True).strip()


def serve(args) -> None:
    torch, tok, model = load_model(args.model, args.device)
    controller = install_controller(model)
    digest = load_adapter(torch, controller, args.seed)
    row = {"domain_id": args.domain_id, "q": args.question, "prefix": args.prefix}
    reply = generate(torch, tok, controller, row, args.device, route(args.domain_id))
    print(json.dumps({"reply": reply, "domain_id": args.domain_id,
                      "adapter_on": route(args.domain_id), "adapter_sha256": digest}))


def validate(args) -> None:
    rows, manifest_sha = read_manifest(args.manifest)
    if args.out.resolve().parent != OUTPUT_DIR:
        raise SystemExit(f"output must be inside {OUTPUT_DIR}")
    if args.out.exists():
        raise SystemExit("output exists; preserve the earlier validation")
    torch, tok, model = load_model(args.model, args.device)
    controller = install_controller(model)
    base_digest = controller.base_digest()
    report = {"manifest_sha256": manifest_sha, "base_revision": PIN, "n": len(rows),
              "domain_counts": {d: sum(x["domain_id"] == d for x in rows) for d in DOMAINS},
              "seeds": {}, "scope": "externally supplied domain ID; no learned router"}
    for seed in (8, 9):
        digest = load_adapter(torch, controller, seed)
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
        report["seeds"][str(seed)] = {"adapter_sha256": digest, "base_digest_unchanged":
                                      controller.base_digest() == base_digest, "domains": domains}
        reply_path = args.out.with_name(f"{args.out.stem}-replies-s{seed}.json")
        reply_path.write_text(json.dumps(details, indent=2) + "\n", encoding="utf-8")
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("serve", "validate"))
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--device", choices=("mps", "cpu"), default="mps")
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
