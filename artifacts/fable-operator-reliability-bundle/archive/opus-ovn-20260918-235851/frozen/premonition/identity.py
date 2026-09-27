"""What a checkpoint and a report are, checked before anything is scored (design/06 §9.8, §11).

A checkpoint is scored only after `admit` accepts its `checkpoint_problems`. It fails closed:

- tokenizer: the checkpoint must record the SHA-256 (semantic digest: equal digests mean identical encoding)
  of its tokenizer, and it must equal the tokenizer loaded for scoring; an override path never skips this.
- vocabulary: the model's embedding and head sizes must equal the tokenizer's vocabulary (plus the 16 entity
  ids for pointer contenders).
- model configuration: present, and (for a contender with a fixed shape) the contender's own shape.
- preprocessing: the checkpoint must record the preprocessing identity it was trained under
  (`premonition.preprocess.identity`), and that identity must be one this code produces; D's must be the
  label-free identity, since D reads the same visit cache format at evaluation.

A report is PRIMARY (it may enter a verdict) only when the scoring purpose is "primary", its regime is
label-free, and every check above passed with the project's v2 contender tokenizer
(data/tokenizer/premonition-tok-v2-fallback.json: 7,068 ids, digest prefix 2c9d06aed330). The retired v1
tokenizer is always refused for a primary report. Other purposes are explicit:

- "legacy": a checkpoint missing metadata may be scored as a labelled legacy diagnostic, never a verdict row;
- "fixture": a unit-test tokenizer (never a v2 contender); a verdict over fixtures is mechanics only;
- "diagnostic": with-labels or gold-evidence runs, or anything else not meant for a verdict.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence, Union

from learnlab.tokenizer import Tokenizer

from . import preprocess
from .batch import N_ENT

V2_TOKENIZER = {"name": "premonition-tok-v2-fallback", "path": "data/tokenizer/premonition-tok-v2-fallback.json",
                "vocab_size": 7068, "digest_prefix": "2c9d06aed330"}
RETIRED_TOKENIZERS = {   # digest prefix -> why (design/06 §9.8: every v1 checkpoint is retired)
    "16814d36d218": "premonition-tok-v1-fallback: no syllable splitting, every held-out name is rare pieces",
}
PURPOSES = ("primary", "legacy", "fixture", "diagnostic")
SCOPE = ("design/06 §6 decision cells on label-free items; NOT a full §9/§10 verdict (no visit-clustered "
         "bootstrap, no C*/D-noask/D-soft/E-long comparisons, no seeds; see reviews/opus-milestone-01)")


class CheckpointIncompatible(ValueError):
    """The checkpoint cannot be scored as asked (the message lists every reason)."""


class VerdictRefused(ValueError):
    """These reports cannot produce a verdict together (mixed regimes, unknown identity, not primary ...)."""


def check_purpose(purpose: str) -> str:
    if purpose not in PURPOSES:
        raise ValueError(f"unknown purpose {purpose!r}; choose from {PURPOSES}")
    return purpose


# ----------------------------------------------------------------- tokenizers


def tokenizer_status(tokenizer: Tokenizer) -> str:
    """"v2" (the contender tokenizer), "retired" (v1) or "other" (e.g. a unit-test fixture)."""
    digest = tokenizer.digest
    if any(digest.startswith(prefix) for prefix in RETIRED_TOKENIZERS):
        return "retired"
    if digest.startswith(V2_TOKENIZER["digest_prefix"]) and tokenizer.vocab_size == V2_TOKENIZER["vocab_size"]:
        return "v2"
    return "other"


def tokenizer_identity(tokenizer: Tokenizer, path: Optional[str] = None) -> dict[str, Any]:
    return {"path": path, "sha256": tokenizer.digest, "vocab_size": tokenizer.vocab_size,
            "status": tokenizer_status(tokenizer)}


def verify_v2_tokenizer(project: Union[str, Path]) -> dict[str, Any]:
    """Load the v2 contender tokenizer through the tokenizer API and check its vocabulary and digest."""
    tokenizer = Tokenizer.load(Path(project) / V2_TOKENIZER["path"])
    info = tokenizer_identity(tokenizer, V2_TOKENIZER["path"])
    if info["status"] != "v2":
        raise CheckpointIncompatible(f"{V2_TOKENIZER['path']} has {tokenizer.vocab_size} ids and digest "
                                     f"{tokenizer.digest[:12]}; expected {V2_TOKENIZER['vocab_size']} and "
                                     f"{V2_TOKENIZER['digest_prefix']}")
    return info


# ----------------------------------------------------------------- checkpoints


def config_digest(config: Mapping[str, Any]) -> str:
    canonical = json.dumps(config, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


def checkpoint_digest(path: Union[str, Path]) -> Optional[str]:
    """SHA-256 of a checkpoint's manifest.json (which records every member's SHA-256), if present."""
    manifest = Path(path) / "manifest.json"
    return hashlib.sha256(manifest.read_bytes()).hexdigest() if manifest.is_file() else None


PROBLEM_KINDS = ("tokenizer", "vocab", "config", "inputs", "shape", "preprocess")
_IDS = ("tokenizer", "vocab", "config", "inputs")        # the ids or the input format would mean other things


def problem_kind(problem: str) -> str:
    return problem.split(":", 1)[0]


def checkpoint_problems(config: Mapping[str, Any], tokenizer: Tokenizer, *, model_vocab: Optional[int],
                        entity_ids: bool, expected_shape: Optional[Mapping[str, Any]] = None,
                        shape: Optional[Mapping[str, Any]] = None, reader: str = "core") -> list[str]:
    """Every reason `config` (a checkpoint's) cannot be scored with `tokenizer`, each "kind: message".

    `model_vocab` is the model's vocabulary (embedding rows); `entity_ids` whether it adds the N_ENT
    entity ids; `expected_shape` / `shape` the contender's fixed shape and the checkpoint's own, compared
    key by key; `reader` "core" (Core prompts) or "visit" (D's visit cache, which must be label-free).
    """
    problems: list[str] = []
    recorded = (config.get("tokenizer") or {}).get("sha256")
    if not recorded:
        problems.append("tokenizer: the checkpoint records no tokenizer digest")
    elif recorded != tokenizer.digest:
        problems.append(f"tokenizer: the checkpoint's tokenizer {recorded[:12]} differs from the scoring "
                        f"tokenizer {tokenizer.digest[:12]}")
    if model_vocab is None:
        problems.append("config: the checkpoint records no model configuration")
    else:
        wanted = tokenizer.vocab_size + (N_ENT if entity_ids else 0)
        if model_vocab != wanted:
            problems.append(f"vocab: model vocabulary {model_vocab} != tokenizer {tokenizer.vocab_size}"
                            f"{' + ' + str(N_ENT) + ' entity ids' if entity_ids else ''} = {wanted}")
    if expected_shape is not None and shape is not None:
        diff = {k: (shape.get(k), v) for k, v in expected_shape.items() if shape.get(k) != v}
        if diff:
            problems.append("shape: model configuration differs from the contender's: " + ", ".join(
                f"{k} {got} (expected {want})" for k, (got, want) in sorted(diff.items())))
    recorded_pre = config.get("preprocess")
    found = preprocess.identity_problems(recorded_pre)
    problems.extend(f"preprocess: {p}" for p in found)
    if not found and reader == "visit" and recorded_pre.get("regime") != preprocess.LABEL_FREE:
        problems.append(f"preprocess: D was trained on {recorded_pre.get('regime')} visits; D reads label-free "
                        "visits")
    return problems


def primary_problems(tokenizer: Tokenizer, regime: str, purpose: str) -> list[str]:
    """Why a report of this tokenizer, regime and purpose cannot be primary (checkpoint checks aside)."""
    problems: list[str] = []
    status = tokenizer_status(tokenizer)
    if status == "retired":
        problems.append(f"tokenizer: {tokenizer.digest[:12]} is retired: {RETIRED_TOKENIZERS[tokenizer.digest[:12]]}")
    elif status != "v2":
        problems.append(f"tokenizer: {tokenizer.digest[:12]} ({tokenizer.vocab_size} ids) is not the v2 contender "
                        f"tokenizer {V2_TOKENIZER['digest_prefix']} ({V2_TOKENIZER['vocab_size']} ids)")
    if regime not in preprocess.VERDICT_REGIMES:
        problems.append(f"regime: {regime} reports never enter a verdict")
    if purpose != "primary":
        problems.append(f"purpose: scored as {purpose!r}")
    return problems


def admit(checkpoint_problems_: Sequence[str], tokenizer: Tokenizer, *, regime: str, purpose: str) -> list[str]:
    """Decide whether scoring may start; return the reasons the report will not be primary.

    Raises CheckpointIncompatible, before any scoring, when:
    - purpose "primary": any checkpoint problem, or any reason the report would not be primary
      (not the v2 tokenizer, retired v1, a regime other than label-free);
    - purpose "diagnostic": any checkpoint problem (only the v2 / regime requirements are waived);
    - purpose "fixture": a v2 or retired tokenizer (a toy tokenizer is never a contender), or any checkpoint
      problem except the contender's full-size shape (fixtures are tiny);
    - purpose "legacy": a tokenizer, vocabulary, configuration or input-kind problem (the ids or inputs
      would mean other things); missing preprocessing metadata and shape are allowed and reported.
    """
    check_purpose(purpose)
    preprocess.check_regime(regime)
    problems = list(checkpoint_problems_)
    if purpose == "primary":
        blocking = problems + primary_problems(tokenizer, regime, purpose)
    elif purpose == "diagnostic":
        blocking = problems
    elif purpose == "fixture":
        if tokenizer_status(tokenizer) != "other":
            raise CheckpointIncompatible(f"a fixture must use a test tokenizer, not the {tokenizer_status(tokenizer)} "
                                         "tokenizer: a toy tokenizer is never a v2 contender")
        blocking = [p for p in problems if problem_kind(p) != "shape"]
    else:
        blocking = [p for p in problems if problem_kind(p) in _IDS]
    if blocking:
        raise CheckpointIncompatible(f"not scorable for purpose {purpose!r}: " + "; ".join(blocking))
    return problems + primary_problems(tokenizer, regime, purpose)


def report_identity(*, regime: str, purpose: str, tokenizer: Tokenizer, tokenizer_path: Optional[str],
                    model_kind: str, model_config: Mapping[str, Any], parameters: int,
                    checkpoint: Union[str, Path], checkpoint_config: Mapping[str, Any], data_tag: str,
                    problems: Sequence[str]) -> dict[str, Any]:
    """The identity block every evaluation report carries; `primary` is True only with no problems."""
    return {
        "regime": regime, "purpose": purpose,
        "preprocess": preprocess.identity(regime),
        "tokenizer": tokenizer_identity(tokenizer, tokenizer_path),
        "model": {"kind": model_kind, "config_sha256": config_digest(model_config), "parameters": parameters},
        "checkpoint": {"path": str(checkpoint), "manifest_sha256": checkpoint_digest(checkpoint),
                       "train_preprocess": checkpoint_config.get("preprocess")},
        "data": {"tag": data_tag},
        "primary": not problems, "problems": list(problems), "scope": SCOPE,
    }


# ----------------------------------------------------------------- verdicts


def report_regime(report: Mapping[str, Any]) -> str:
    """A report's input regime; a report that records none is legacy/unknown, never label-free."""
    identity = report.get("identity") or {}
    regime = identity.get("regime", report.get("regime"))
    return regime if regime in preprocess.REGIMES else preprocess.LEGACY


def verdict_problems(reports: Sequence[Mapping[str, Any]], *, allow_fixture: bool = False) -> list[str]:
    """Every reason these reports cannot share a verdict (empty: they can)."""
    problems: list[str] = []
    regimes = {report_regime(r) for r in reports}
    if len(regimes) > 1:
        problems.append(f"mixed input regimes {sorted(regimes)}: never pair reports across regimes")
    for report in reports:
        who = f"{report.get('contender')}{'/W-' + report['wipe'] if report.get('wipe') else ''}"
        identity = report.get("identity") or {}
        regime = report_regime(report)
        if regime == preprocess.LEGACY:
            problems.append(f"{who}: no input regime recorded (legacy/unknown)")
            continue
        if regime not in preprocess.VERDICT_REGIMES:
            problems.append(f"{who}: {regime} reports never enter a verdict")
        found = preprocess.identity_problems(identity.get("preprocess"))
        problems.extend(f"{who}: {p}" for p in found)
        purpose = identity.get("purpose")
        if allow_fixture and purpose == "fixture":
            continue
        if purpose != "primary" or identity.get("primary") is not True:
            reasons = "; ".join(identity.get("problems") or []) or f"purpose {purpose!r}"
            problems.append(f"{who}: not a primary report ({reasons})")
    purposes = {(r.get("identity") or {}).get("purpose") for r in reports}
    if allow_fixture and "fixture" in purposes and purposes != {"fixture"}:
        problems.append("fixture reports cannot share a verdict with other reports")
    digests = {((r.get("identity") or {}).get("preprocess") or {}).get("digest") for r in reports}
    if len(digests) > 1:
        problems.append(f"mixed preprocessing digests {sorted(str(d)[:12] for d in digests)}")
    return problems


def guard_verdict(reports: Sequence[Mapping[str, Any]], *, allow_fixture: bool = False) -> dict[str, Any]:
    """Raise VerdictRefused unless the reports may share a verdict; return what the verdict is scoped to."""
    problems = verdict_problems(reports, allow_fixture=allow_fixture)
    if problems:
        raise VerdictRefused("no verdict: " + "; ".join(problems))
    fixture = allow_fixture and all((r.get("identity") or {}).get("purpose") == "fixture" for r in reports)
    return {"regime": preprocess.LABEL_FREE, "fixture": fixture, "full_verdict": False,
            "scope": ("fixture mechanics only; " if fixture else "") + SCOPE}


__all__ = [
    "CheckpointIncompatible", "PROBLEM_KINDS", "PURPOSES", "RETIRED_TOKENIZERS", "SCOPE", "V2_TOKENIZER",
    "VerdictRefused", "admit", "check_purpose", "checkpoint_digest", "checkpoint_problems", "config_digest",
    "guard_verdict", "primary_problems", "problem_kind", "report_identity", "report_regime", "tokenizer_identity",
    "tokenizer_status", "verdict_problems", "verify_v2_tokenizer",
]
