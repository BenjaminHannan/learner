"""Opt-in KL contexts from the frozen base's answers to public generic prompts.

These are teacher references, not independently fact-checked answers. No diary,
incumbent-adapter output, or private fact is admitted. KL still evaluates the
base distribution at training time; this cache supplies its answer contexts.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
from collections import Counter
from pathlib import Path

from .paths import read_json, write_json

VERSION = "base-continuation-1"
# Match the existing replay renderer so paired experiments change the contexts
# and mask, without also changing the system instruction.
TEACHER_SYSTEM = "Answer with just the name."


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def question_key(text):
    # Ignore formatting and punctuation so trivial edits cannot leak a gate row.
    from .gate import normalize
    return normalize(text)


def public_questions(questions, excluded):
    blocked, seen, out = {question_key(q) for q in excluded}, set(), []
    for q in questions:
        key = question_key(q)
        if key and key not in blocked and key not in seen:
            seen.add(key)
            out.append(q)
    return out


def reference_identity(backend, renderer):
    """Invalidate on source, local weights, tokenizer, template, or runtime change.

    Large weight files use path/size/mtime identities, not a claimed content
    checksum; pinned upstream revision and small config files are also recorded.
    Tokenizer assets are content hashed, including the loaded fast tokenizer.
    """
    p, tok = renderer.p, getattr(backend, "tok", renderer.tok)
    root = Path(p.expanded_model_dir) if p.model_dir else None
    assets, weights = {}, []
    if root and root.is_dir():
        for file in sorted(root.iterdir()):
            if not file.is_file():
                continue
            if file.suffix in (".safetensors", ".bin", ".gguf"):
                stat = file.stat()
                weights.append([file.name, stat.st_size, stat.st_mtime_ns])
            elif (file.name in ("config.json", "generation_config.json") or
                  file.name.startswith(("tokenizer", "special_tokens", "added_tokens", "vocab", "merges", "chat_template"))):
                assets[file.name] = hashlib.sha256(file.read_bytes()).hexdigest()
    tokenizer = {"class": type(tok).__module__ + "." + type(tok).__qualname__,
                 "chat_template": getattr(tok, "chat_template", None),
                 "special_tokens": getattr(tok, "special_tokens_map", None),
                 "name_or_path": getattr(tok, "name_or_path", None)}
    fast = getattr(tok, "backend_tokenizer", None)
    if fast is not None and callable(getattr(fast, "to_str", None)):
        tokenizer["vocabulary"] = digest(fast.to_str())
    elif callable(getattr(tok, "get_vocab", None)):
        tokenizer["vocabulary"] = digest(tok.get_vocab())
    versions = {}
    for name in ("mlx", "mlx-lm", "torch", "transformers", "tokenizers", "peft"):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            pass
    return {"version": VERSION, "profile": p.name, "hf_id": p.hf_id,
            "source_revision": p.source_revision, "model_dir": str(root.resolve()) if root else None,
            "local_weight_identity": "path-size-mtime_ns", "weights": weights, "assets": assets,
            "backend": type(backend).__module__ + "." + type(backend).__qualname__,
            "backend_source": [getattr(backend, "model_id", None), str(getattr(backend, "model_dir", ""))],
            "loader": [p.loader, p.loader_path], "tokenizer": tokenizer, "versions": versions,
            "template": [p.template_mode, p.template, p.nothink_suffix, p.think_open, p.think_close,
                         p.training_answer_prefix, p.quirks], "stop_id": backend.stop_id,
            "encoding_probe": backend.encode("Replay identity probe: café 17!\n")}


def prompt_examples(backend, prompts, max_seq_len):
    """Legacy KL contexts, with an explicit context bound and no truncation."""
    out = []
    for prompt in prompts:
        ids = backend.encode(prompt) + [backend.stop_id]
        if 1 < len(ids) <= max_seq_len:
            out.append((ids, 0))
    return out


def continuation_examples(backend, renderer, questions, cache_path, *, max_tokens=128,
                          max_seq_len=640, before_generate=None):
    """Return (examples, diagnostics), falling back per failed teacher response.

    External stops and deadline Stop exceptions propagate for normal checkpoint
    handling. A backend TimeoutError falls back to bounded legacy contexts; no
    empty/oversized answer is cached. Text-only backends do not report EOS, so
    completion is explicitly unknown; capped prefixes remain valid KL contexts.
    """
    if max_tokens < 1 or max_seq_len < 2:
        raise ValueError("replay token and context limits must be positive")
    prompts = [renderer.render(TEACHER_SYSTEM, q) for q in questions]
    identity = dict(reference_identity(backend, renderer), prompts=digest(prompts),
                    max_tokens=max_tokens, max_seq_len=max_seq_len, system=TEACHER_SYSTEM)
    key = digest(identity)
    cache = read_json(cache_path, {}) or {}
    records = cache.get("records", {}) if cache.get("identity_sha256") == key else {}
    if not isinstance(records, dict):
        records = {}
    stats = Counter(questions=len(prompts))
    stats["cache_identity_sha256"] = key
    stats["mode"] = "continuation"
    provenance = {"source": "base-model-teacher", "adapter": False, "temperature": 0.0,
                  "completion": "unknown; text-only generation API",
                  "verified": "identity-and-integrity; not factual verification", "version": VERSION}
    responses, pending = {}, []
    for i, prompt in enumerate(prompts):
        row = records.get(digest(prompt), {})
        answer = row.get("answer") if isinstance(row, dict) else None
        if (isinstance(answer, str) and answer.strip() and row.get("provenance") == provenance
                and row.get("answer_sha256") == digest(answer)):
            responses[i] = answer
            stats["cache_hits"] += 1
        else:
            pending.append(i)
    prefix = backend.encode(renderer.p.training_answer_prefix)
    # Reject overlong prompts before generating; preserve prompt and answer whole.
    pending = [i for i in pending if 0 < len(backend.encode(prompts[i])) < max_seq_len - len(prefix) - 1]
    for offset in range(0, len(pending), max(1, backend.gen_batch)):
        indices = pending[offset:offset + max(1, backend.gen_batch)]
        limit = min(max_tokens, min(max_seq_len - len(backend.encode(prompts[i])) - len(prefix) - 1 for i in indices))
        if before_generate is not None:
            before_generate(limit)
        try:
            result = backend.generate([prompts[i] for i in indices], limit, temp=0.0, adapter=False)
        except TimeoutError:
            stats["generation_timeouts"] += len(indices)
            continue
        if len(result) != len(indices):
            stats["incomplete_batches"] += 1
            continue
        changed = False
        for i, answer in zip(indices, result):
            if not isinstance(answer, str) or not answer.strip():
                stats["empty_answers"] += 1
                continue
            answer_ids = backend.encode(answer)
            prompt_ids = backend.encode(prompts[i])
            if (not answer_ids or len(answer_ids) > limit or
                    len(prompt_ids) + len(prefix) + len(answer_ids) + 1 > max_seq_len):
                stats["oversized_answers"] += 1
                continue
            responses[i] = answer
            records[digest(prompts[i])] = {"answer": answer, "answer_sha256": digest(answer), "provenance": provenance}
            stats["generated_answers"] += 1
            changed = True
        if changed:
            write_json(cache_path, {"identity": identity, "identity_sha256": key, "records": records})
    examples = []
    for i, prompt in enumerate(prompts):
        ids = backend.encode(prompt)
        answer = responses.get(i)
        target = prefix + backend.encode(answer) + [backend.stop_id] if answer else []
        if target and len(target) > len(prefix) + 1 and len(ids) + len(target) <= max_seq_len:
            examples.append((ids + target, len(ids)))
            stats["continuation_examples"] += 1
            stats["continuation_target_tokens"] += len(target)
        else:
            fallback = prompt_examples(backend, [prompt], max_seq_len)
            examples.extend(fallback)
            stats["fallback_prompt_examples"] += len(fallback)
            stats["skipped_contexts"] += int(not fallback)
    return examples, dict(stats)
