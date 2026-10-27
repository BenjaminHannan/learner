"""Parallel, resumable, deterministic stream shards.

Shard k of a split holds visits [k * per_shard, (k + 1) * per_shard) as
  shard-<k>.txt    the stream text (each visit's lines, then a blank line)
  shard-<k>.jsonl  one {"kind": "visit"} row per visit, then one {"kind": "question"} row per question
Line numbers in the JSONL are 0-based indices into that shard's .txt file.
A shard's content depends only on (split, visit range, seed, generator, patterns),
so any number of workers writes the same bytes. Each file is written to a
temporary name and renamed, the .txt last, so a shard exists only when its
.txt does; a rerun skips finished shards. `manifest.json` pins the settings and
the split manifest, and a rerun with different settings is refused.
"""
from __future__ import annotations

import json
import multiprocessing
import os
from pathlib import Path
import tempfile
import time
from typing import Any, Mapping, Optional

from learnlab.splits import assert_consumable

from .render import PatternSource, village_registry
from .stream import WINDOW_CHARS, RenderedVisit, audit, load_callable, render_visit

GENERATOR = "learnlab.village.shards:world_visit"
FAMILIES = "learnlab.village.scheduler:world_families"
NAMES = "learnlab.village.names:all_names"
VISITS_PER_SHARD = 256
CHARS_PER_TOKEN = 4          # the estimate used when no trained tokenizer is given
AUDIT_EVERY = 64             # full text audit on every Nth visit; provenance is checked on all

_STATE: dict[str, Any] = {}


def world_visit(split: str, index: int, *, seed: int, registry: Any) -> dict[str, Any]:
    """Visit `index` of the stream with `seed`: a standalone first visit from the village scheduler."""
    from .scheduler import generate_visit
    return generate_visit(split, seed * 1_000_000_000 + index, registry=registry)


def default_out_dir() -> Path:
    return Path(tempfile.gettempdir()) / "village-stream"


def _setup(config: Mapping[str, Any]) -> None:
    """Per process: patterns, registry, generator, optional names and tokenizer."""
    source = PatternSource.load(Path(config["patterns"])) if config.get("patterns") else PatternSource.load()
    families = load_callable(config["families"])() if config.get("families") else None
    tokenizer = None
    if config.get("tokenizer"):
        from learnlab.tokenizer import Tokenizer
        tokenizer = Tokenizer.load(config["tokenizer"])
    _STATE.update(
        config=dict(config), source=source, registry=village_registry(source, families),
        generate=load_callable(config["generator"]),
        names=list(load_callable(config["names"])()) if config.get("names") else [],
        tokenizer=tokenizer,
    )


def _shifted(question: Mapping[str, Any], offset: int) -> dict[str, Any]:
    row = dict(question)
    row["text_line"] += offset
    row["context_start"] += offset
    row["evidence_text_lines"] = [None if t is None else t + offset for t in question["evidence_text_lines"]]
    return row


def render_range(split: str, start: int, stop: int) -> tuple[str, list[str], list[RenderedVisit]]:
    """Text, JSONL rows and rendered visits for visits [start, stop) of `split` (needs `_setup`)."""
    config, source, registry = _STATE["config"], _STATE["source"], _STATE["registry"]
    parts: list[str] = []
    rows: list[str] = []
    rendered: list[RenderedVisit] = []
    offset = 0
    for index in range(start, stop):
        visit = _STATE["generate"](split, index, seed=config["seed"], registry=registry)
        done = render_visit(visit, source, registry, window_chars=config["window_chars"])
        assert_consumable(done.audit_record(), split, registry=registry)
        rows.append(json.dumps({"kind": "visit", "id": done.id, "split": split, "index": index, "first_line": offset,
                                "lines": len(done.lines), "provenance": done.provenance}, sort_keys=True))
        rows += [json.dumps({"kind": "question", **_shifted(q, offset)}, sort_keys=True) for q in done.questions]
        parts.append(done.text + "\n\n")
        offset += len(done.lines) + 1
        rendered.append(done)
    every = config["audit_every"]
    sampled = [done for index, done in zip(range(start, stop), rendered) if every and index % every == 0]
    if sampled:
        audit(sampled, registry, source, _STATE["names"])
    return "".join(parts), rows, rendered


def _write(path: Path, text: str) -> None:
    temp = path.with_name(f"{path.name}.tmp-{os.getpid()}")
    temp.write_text(text, encoding="utf-8")
    os.replace(temp, path)


def _make_shard(task: tuple[str, int, int, int, str]) -> dict[str, Any]:
    split, shard, start, stop, directory = task
    started = time.perf_counter()
    text, rows, rendered = render_range(split, start, stop)
    tokenizer = _STATE["tokenizer"]
    tokens = len(tokenizer.encode(text)) if tokenizer is not None else None
    base = Path(directory) / f"shard-{shard:05d}"
    _write(base.with_suffix(".jsonl"), "\n".join(rows) + "\n")
    _write(base.with_suffix(".txt"), text)
    return {"shard": shard, "visits": stop - start, "questions": sum(len(r.questions) for r in rendered),
            "chars": len(text), "tokens": tokens, "seconds": time.perf_counter() - started}


def _worker_init(config: Mapping[str, Any]) -> None:
    _setup(config)


def write_shards(
    split: str,
    n_visits: int,
    out_dir: Optional[os.PathLike] = None,
    workers: int = 1,
    *,
    seed: int = 0,
    visits_per_shard: int = VISITS_PER_SHARD,
    generator: str = GENERATOR,
    families: Optional[str] = FAMILIES,
    names: Optional[str] = NAMES,
    patterns: Optional[str] = None,
    tokenizer: Optional[str] = None,
    window_chars: int = WINDOW_CHARS,
    audit_every: int = AUDIT_EVERY,
    verbose: bool = True,
) -> dict[str, Any]:
    """Write (or finish writing) `n_visits` visits of `split` under `out_dir/<split>/`; return a report.

    `generator`, `families` and `names` are 'module:function' specs:
    generator(split, index, *, seed, registry) -> visit, families() -> extra
    split families for `village_registry`, names() -> every pool name (for the audit).
    Workers are spawned processes, so a calling script needs an `if __name__ == "__main__":` guard.
    """
    if n_visits < 0 or visits_per_shard < 1 or workers < 1:
        raise ValueError("need n_visits >= 0, visits_per_shard >= 1 and workers >= 1")
    directory = Path(out_dir if out_dir is not None else default_out_dir()) / split
    directory.mkdir(parents=True, exist_ok=True)
    config = {"split": split, "n_visits": n_visits, "seed": seed, "visits_per_shard": visits_per_shard,
              "generator": generator, "families": families, "names": names, "patterns": patterns,
              "tokenizer": tokenizer, "window_chars": window_chars, "audit_every": audit_every}
    _setup(config)
    manifest = {
        "split": split, "n_visits": n_visits, "seed": seed, "visits_per_shard": visits_per_shard, "generator": generator,
        "families": families, "window_chars": window_chars, "patterns": _STATE["source"].version,
        "split_manifest": _STATE["registry"].manifest().payload(),
    }
    path = directory / "manifest.json"
    if path.exists():
        saved = json.loads(path.read_text(encoding="utf-8"))
        if saved != manifest:
            changed = sorted(key for key in set(saved) | set(manifest) if saved.get(key) != manifest.get(key))
            raise ValueError(f"{directory} was written with different settings ({', '.join(changed)}); use a new directory")
    else:
        _write(path, json.dumps(manifest, indent=1, sort_keys=True) + "\n")

    tasks = []
    for shard, start in enumerate(range(0, n_visits, visits_per_shard)):
        if not (directory / f"shard-{shard:05d}.txt").exists():
            tasks.append((split, shard, start, min(start + visits_per_shard, n_visits), str(directory)))
    started = time.perf_counter()
    if workers == 1 or len(tasks) <= 1:
        results = [_make_shard(task) for task in tasks]
    else:
        context = multiprocessing.get_context("spawn")
        with context.Pool(min(workers, len(tasks)), initializer=_worker_init, initargs=(config,)) as pool:
            results = list(pool.imap_unordered(_make_shard, tasks))
    wall = time.perf_counter() - started
    chars = sum(r["chars"] for r in results)
    estimate = tokenizer is None
    tokens = chars / CHARS_PER_TOKEN if estimate else sum(r["tokens"] for r in results)
    report = {
        "split": split, "directory": str(directory), "shards_written": len(results),
        "shards_skipped": -(-n_visits // visits_per_shard) - len(results) if n_visits else 0,
        "visits": sum(r["visits"] for r in results), "questions": sum(r["questions"] for r in results),
        "chars": chars, "tokens": tokens, "tokens_estimated": estimate, "wall_seconds": wall, "workers": workers,
        "chars_per_second": chars / wall if wall > 0 and chars else 0.0,
        "tokens_per_second": tokens / wall if wall > 0 and chars else 0.0,
        "chars_per_worker_second": chars / sum(r["seconds"] for r in results) if results else 0.0,
    }
    if verbose:
        how = f"estimate: 1 token ~ {CHARS_PER_TOKEN} characters" if estimate else "trained tokenizer"
        print(f"{split}: wrote {report['shards_written']} shards ({report['visits']} visits, {report['questions']} questions), "
              f"skipped {report['shards_skipped']}; {chars:,} chars in {wall:.2f}s = {report['chars_per_second']:,.0f} chars/s, "
              f"~{report['tokens_per_second']:,.0f} tokens/s ({how}); {report['chars_per_worker_second']:,.0f} chars/s per worker",
              flush=True)
    return report


def sample_text(split: str, visits: int, *, seed: int = 0, start: int = 0, generator: str = GENERATOR,
                families: Optional[str] = FAMILIES, names: Optional[str] = NAMES, patterns: Optional[str] = None) -> str:
    """The rendered stream of visits [start, start + visits) of `split`, every visit audited."""
    _setup({"seed": seed, "generator": generator, "families": families, "names": names, "patterns": patterns,
            "window_chars": WINDOW_CHARS, "audit_every": 1})
    return render_range(split, start, start + visits)[0]


__all__ = ["AUDIT_EVERY", "CHARS_PER_TOKEN", "FAMILIES", "GENERATOR", "NAMES", "VISITS_PER_SHARD", "default_out_dir", "render_range", "sample_text", "world_visit", "write_shards"]
