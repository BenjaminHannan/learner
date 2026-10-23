"""Extra training shards for D, shared by `generalize.dtrain_only` (D-only runs) and `v1.run` (FULL / FLOOR arms).

--extra-train DIR (repeatable): extra shard directories (holding shard-*.txt/.jsonl, or a `train/` subdirectory with them). Their
caches are built with the SAME train-fitted name detector and the label-free regime, and saved under OUT/extra-cache (reused on
resume). The batch stream mixes the sources at the batch level: step s draws from the source picked by a deterministic function
of (seed, s), with probability proportional to token counts (main train first); each source has its own endless shuffled stream
(seed + 1000*i). Resume re-derives per-source batch counts from the step number, so it is exact. With no extras the stream is
exactly `v1.dtrain.train_stream`.

--detector-patterns BANK.json sets env GEN_DETECTOR_PATTERNS (premonition.data.name_detector then also blocks that bank's template
words) BEFORE the data root is opened. It only takes effect when the root has no `premonition-names.json` yet (the detector is
loaded from that file if present); `check_detector_patterns` refuses a stale detector that lacks the bank's words.
"""
from __future__ import annotations

import itertools
import os
import random
import time
from pathlib import Path
from typing import Any, Optional

from premonition import data as pdata
from premonition import preprocess

log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def shard_dir(path: Path) -> Path:
    from learnlab import step1
    path = Path(path)
    for cand in (path, path / "train"):
        if cand.is_dir() and step1.shard_files(cand):
            return cand
    raise SystemExit(f"--extra-train {path}: no shard files found (looked in it and in its train/ subdirectory)")


def open_extra(dirs: list[Path], data, out: Path, workers: int) -> list[Any]:
    caches = []
    for k, d in enumerate(dirs):
        sd = shard_dir(d)
        cp = out / "extra-cache" / f"{k}-{sd.parent.name}-{sd.name}.pt"
        cache = None
        if cp.is_file():
            cache = pdata.VisitCache.load(cp)
            if cache.info.get("source") != str(sd) or cache.info.get("detector_sha256") != data.detector.digest:
                cache = None
        if cache is None:
            cache = pdata.build_cache(sd, data.tokenizer, data.detector, split="train", workers=workers, regime=preprocess.LABEL_FREE)
            cp.parent.mkdir(parents=True, exist_ok=True)
            tmp = cp.with_suffix(".tmp")
            tmp.write_bytes(cache.to_bytes())
            tmp.replace(cp)
        log(f"extra-train {sd}: {len(cache):,} visits, {int(cache.lengths.sum()):,} tokens")
        caches.append(cache)
    return caches


def mixed_stream(caches: list[Any], max_tokens: int, seed: int, skip: int, max_visits: Optional[int]):
    """Batch-level mixture, proportional to token counts; `skip` batches already trained (resume)."""
    w = [float(c.lengths.sum()) for c in caches]
    cum = list(itertools.accumulate(w))

    def pick(step: int) -> int:
        r = random.Random(f"{seed}-mix-{step}").random() * cum[-1]
        return next(i for i, c in enumerate(cum) if r < c) if len(cum) > 1 else 0

    counts = [0] * len(caches)
    for s in range(skip):
        counts[pick(s)] += 1
    streams = [itertools.islice(pdata.batches(c, max_tokens, seed=seed + 1000 * i, epochs=None, max_visits=max_visits), counts[i], None)
               for i, c in enumerate(caches)]
    step = skip
    while True:
        yield next(streams[pick(step)])
        step += 1


def set_detector_patterns(path: Optional[str]) -> None:
    """Call before the data root is opened."""
    if path:
        if not Path(path).is_file():
            raise SystemExit(f"--detector-patterns {path}: no such file")
        os.environ["GEN_DETECTOR_PATTERNS"] = str(Path(path).resolve())


def check_detector_patterns(detector, path: Optional[str]) -> None:
    """Refuse a detector that does not block the bank's template words (e.g. a premonition-names.json fitted before the env was set)."""
    if not path:
        return
    from learnlab.village.render import PatternSource
    from premonition.pointer import template_words
    missing = sorted(template_words(PatternSource.load(Path(path)).text.values()) - set(detector.template))
    if missing:
        raise SystemExit(f"--detector-patterns {path}: the root's saved name detector ({detector.digest[:12]}) lacks {len(missing)} of the "
                         f"bank's template words ({', '.join(missing[:8])}...). It was fitted without the bank: use a data root with no "
                         f"premonition-names.json (a fresh copy of the root) so it is refitted with GEN_DETECTOR_PATTERNS set.")
