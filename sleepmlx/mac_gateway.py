"""LFM3 compatibility layer for the existing, separately installed Mac gateway.

Keeps its diary, image handling and streaming code, while using the same LFM3
server for each chat alias. The external gateway source remains unmodified.
"""
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import sys

CREATIVE_TAG = "[Creative proposal data]"


class PreparedRequest(dict):
    """Carry local request provenance without serializing it upstream."""


def scratch(body, headers=None):
    headers = headers or {}
    return (body.get("test") is True or body.get("purpose") == "creative-proposals"
            or str(headers.get("X-Test", "")) == "1"
            or bool(headers.get("X-Premonition-Warm")))


def clean_messages(messages):
    return [m for m in messages or [] if not (
        isinstance(m, dict) and m.get("role") == "user"
        and isinstance(m.get("content"), str)
        and m["content"].startswith(CREATIVE_TAG))]


def install(module):
    """Patch a loaded gateway module; reject incompatible external versions."""
    if getattr(module, "_premonition_lfm3", False):
        return module
    for owner, name in ((module, "prepare"), (module, "build_diary"),
                        (module.Gateway, "route"), (module.Gateway, "note_prefix"),
                        (module.Handler, "record")):
        if not callable(getattr(owner, name, None)):
            raise ValueError("Unsupported Mac gateway: missing " + name)
    original_prepare, original_diary = module.prepare, module.build_diary
    original_record, original_prefix = module.Handler.record, module.Gateway.note_prefix
    original_route = module.Gateway.route

    def route(self, model):
        if model == "k2-helper" and self.small_up():
            return original_route(self, model)
        # Auto is deliberately a fast request, avoiding a second judge inference.
        thinking = model not in ("lfm3-fast", "lfm3-auto", "qwen36-fast", "qwen36-auto", "k2-helper")
        return "big", self.big_url, thinking, module.BIG_MAX

    def prepare(body, thinking, default_max):
        # Do not inherit Qwen-specific non-thinking sampling defaults.
        b = PreparedRequest(original_prepare(body, None, default_max))
        b.scratch_request = scratch(body)
        b["model"] = "lfm3"
        if thinking is not None:
            b["chat_template_kwargs"] = dict(b.get("chat_template_kwargs") or {}, enable_thinking=thinking)
        for key in ("test", "purpose"):
            b.pop(key, None)
        return b

    def build_diary(body, *args, **kwargs):
        return original_diary(dict(body, messages=clean_messages(body.get("messages"))), *args, **kwargs)

    def record(self, body, *args, **kwargs):
        if scratch(body, self.headers):
            return
        return original_record(self, body, *args, **kwargs)

    def note_prefix(self, body):
        # A creative scratch request must not replace the saved daytime prefix.
        if getattr(body, "scratch_request", False) or scratch(body) or any(isinstance(m, dict) and isinstance(m.get("content"), str)
                                and m["content"].startswith(CREATIVE_TAG)
                                for m in body.get("messages") or []):
            return
        return original_prefix(self, body)

    module.Gateway.route = route
    module.prepare = prepare
    module.build_diary = build_diary
    module.Handler.record = record
    module.Gateway.note_prefix = note_prefix
    module.BIG_MAX = 2048
    module.MODEL_IDS = ["lfm3", "lfm3-fast", "lfm3-auto"]
    module._premonition_lfm3 = True
    return module


def load(path):
    path = Path(path).expanduser().resolve(strict=True)
    spec = importlib.util.spec_from_file_location("premonition_local_gateway", path)
    if spec is None or spec.loader is None:
        raise ValueError("Cannot load installed gateway")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return install(module)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gateway-file", required=True)
    args, rest = parser.parse_known_args(argv)
    module = load(args.gateway_file)
    sys.argv = [str(args.gateway_file), *rest]
    module.main()


if __name__ == "__main__":
    main()
