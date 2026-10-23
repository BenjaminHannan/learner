"""Mixed-axis probe sets: TRAIN visits with exactly one concern switched to its validation setting.

Concerns (design/generalize/PASSMARKS.md):
  name        person and village names drawn from the validation name pool
  template    non-teacher narrator / question / rule patterns of the validation split
  style       validation teacher styles (the teacher patterns follow their style)
  difficulty  every scheduler knob keyed on the split: MAX_DEPTH, DEPTH_TARGET, question_allowed (combination
              rule), `deep`, `quiet`, the deepen rate. Rule families stay train's R1-R7 and link_rules stays off.
  rule        validation's rule-family set (adds R8); every other knob stays train's

Probes: P0 (nothing), Pname, Pword (template), Pstyle, Pdepth (difficulty), Prule, Pall (everything: the
validation distribution, and with the same seed it IS validation, visit for visit).

HARD RULE: the sealed `test` split is never drawn. `Profile` refuses any setting outside {train, validation},
`MixedView` only accepts items whose registry split equals the axis setting, and `audit_visits` /
`audit_probe_dir` re-check provenance, template ids and every name in the text against the per-axis split map.

Run:  python3 -m generalize.probes OUT_DIR --visits 1000 --workers 4 [--probes P0,Pname,...] [--seed 101]
Training data with a concern switched (only `difficulty`: the other concerns would put validation items in
training):  `write_training_data(("difficulty",), n, OUT_DIR)`.
"""
from __future__ import annotations

import argparse
import json
import multiprocessing
import os
import re
import sys
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence

from learnlab.splits import SplitLeak, SplitRegistry, SplitView
from learnlab.village import names as village_names_mod
from learnlab.village import vocab
from learnlab.village.render import TEACHER_BANKS, PatternSource, village_registry
from learnlab.village.scheduler import generate_visit, style_assignment, world_families
from learnlab.village.shards import AUDIT_EVERY, VISITS_PER_SHARD, _shifted, _write
from learnlab.village.stream import WINDOW_CHARS, render_visit

ALLOWED_SPLITS = frozenset({"train", "validation"})      # the sealed `test` split is not in here, on purpose
CONCERNS = ("name", "template", "style", "difficulty", "rule")
PROBES: dict[str, tuple[str, ...]] = {
    "P0": (), "Pname": ("name",), "Pword": ("template",), "Pstyle": ("style",),
    "Pdepth": ("difficulty",), "Prule": ("rule",), "Pall": CONCERNS,
}
PROBE_SEED = 101                  # TRAIN / DEV / validation use seed 0
TRAIN_ARM_OFFSET = 10_000_000     # visit-index offset of training data with a concern switched (train uses 0..99,999)
_AXIS_OF = {"name": "name", "template": "template", "teacher_style": "style", "rule_family": "rule"}
_NAME_WORD = re.compile(r"[A-Z][a-z]+")


def _only_allowed(**settings: str) -> None:
    for what, split in settings.items():
        if split not in ALLOWED_SPLITS:
            raise SplitLeak(f"probe setting {what}={split!r} is not train/validation (the test split is sealed)")


@dataclass(frozen=True)
class Profile:
    """Which concerns of a TRAIN base are switched to validation."""
    switched: frozenset = frozenset()
    base: str = "train"
    other: str = "validation"

    def __post_init__(self) -> None:
        bad = set(self.switched) - set(CONCERNS)
        if bad:
            raise ValueError(f"unknown concern(s) {sorted(bad)}; choose from {CONCERNS}")
        _only_allowed(base=self.base, other=self.other, **{c: self.setting(c) for c in CONCERNS})

    @classmethod
    def of(cls, concerns: Iterable[str]) -> "Profile":
        return cls(frozenset(concerns))

    def setting(self, concern: str) -> str:
        return self.other if concern in self.switched else self.base

    @property
    def label(self) -> str:
        """The split label that seeds the random streams and tags visits: validation iff everything is switched."""
        return self.other if set(self.switched) == set(CONCERNS) else self.base

    @property
    def knobs(self) -> str:
        return self.setting("difficulty")

    @property
    def families(self) -> str:
        return self.setting("rule")

    def axis_split(self, axis: str) -> str:
        """Split an item of registry axis `axis` (name, template, teacher_style, rule_family) must belong to."""
        return self.setting(_AXIS_OF[axis])

    def axis_map(self) -> dict[str, str]:
        return {axis: self.axis_split(axis) for axis in _AXIS_OF}

    def describe(self) -> dict[str, Any]:
        return {"switched": sorted(self.switched), "label": self.label, "axes": self.axis_map(),
                "knobs": self.knobs, "families": self.families}


class MixedView(SplitView):
    """A SplitView whose axes may belong to different splits (train / validation only)."""

    def __init__(self, registry: SplitRegistry, profile: Profile, teacher_patterns: frozenset = frozenset()) -> None:
        super().__init__(registry, profile.axis_split("template"))   # `.split` picks the renderer's narrator patterns
        self.profile, self.teacher_patterns = profile, teacher_patterns

    def _expected(self, axis: str, item: str) -> str:
        if axis == "template" and item in self.teacher_patterns:      # a teacher pattern is split with its style
            return self.profile.axis_split("teacher_style")
        return self.profile.axis_split(axis)

    def available(self, axis: str, candidates: Iterable[str]) -> list[str]:
        if isinstance(candidates, (str, bytes)):
            raise ValueError("candidates must be an iterable of item names, not one string")
        return [i for i in sorted(set(candidates)) if self.registry.split_of(axis, i) == self._expected(axis, i)]

    def use(self, axis: str, item: str) -> str:
        want = self._expected(axis, item)
        _only_allowed(**{f"{axis}:{item}": want})
        self.registry.record(axis, item, want)
        used = self._used.setdefault(axis, [])
        if item not in used:
            used.append(item)
        return item


# ------------------------------------------------------------------------------------------------ generation
_STATE: dict[str, Any] = {}


def _setup(config: Mapping[str, Any]) -> None:
    source = PatternSource.load(Path(config["patterns"])) if config.get("patterns") else PatternSource.load()
    registry = village_registry(source, world_families())
    teacher = frozenset(p for p, b in source.bank.items() if b in TEACHER_BANKS)
    _STATE.update(config=dict(config), profile=Profile.of(config["switched"]), source=source, registry=registry,
                  teacher=teacher, names=frozenset(village_names_mod.all_names()), styles=style_assignment())


def _view() -> MixedView:
    return MixedView(_STATE["registry"], _STATE["profile"], _STATE["teacher"])


def probe_visit(index: int) -> dict[str, Any]:
    """Visit `index` of the configured probe (needs `_setup`)."""
    config, profile = _STATE["config"], _STATE["profile"]
    seed = config["seed"] * 1_000_000_000 + config["index_offset"] + index
    return generate_visit(profile.label, seed, registry=_STATE["registry"], view=_view(),
                          knobs=profile.knobs, families=profile.families)


def audit_visits(rendered: Sequence[Any], profile: Profile, registry: SplitRegistry, names: frozenset,
                 teacher: frozenset, styles: Mapping[str, str]) -> None:
    """The per-axis equivalent of `splits.audit`: provenance, template ids and text names against `profile`'s axis map."""
    problems = []
    for done in rendered:
        for axis, items in done.provenance.items():
            if axis not in _AXIS_OF:
                problems.append(f"{done.id}: unknown axis {axis!r}")
                continue
            for item in items:
                want = profile.axis_split(axis)
                if axis == "template" and item in teacher:
                    want = profile.axis_split("teacher_style")
                got = registry.split_of(axis, item)
                if got == "test" or got != want:
                    problems.append(f"{done.id}: {axis} {item!r} is {got}, probe needs {want}")
        used = set(done.provenance.get("name", ()))
        for word in set(_NAME_WORD.findall(done.text)):
            if word in names:
                if registry.split_of("name", word) != profile.axis_split("name"):
                    problems.append(f"{done.id}: name {word!r} in text is {registry.split_of('name', word)}")
                if word not in used:
                    problems.append(f"{done.id}: name {word!r} in text but not in provenance")
        style = next(iter(done.provenance.get("teacher_style", ())), None)
        if style is not None and styles[style] != profile.axis_split("teacher_style"):
            problems.append(f"{done.id}: style {style!r}")
    if problems:
        raise SplitLeak("probe audit failed: " + "; ".join(problems[:8]), problems)


def render_range(start: int, stop: int, *, audit_every: int = 1) -> tuple[str, list[str], list[Any]]:
    config, profile = _STATE["config"], _STATE["profile"]
    parts, rows, rendered, offset = [], [], [], 0
    label = profile.label
    for index in range(start, stop):
        visit = probe_visit(index)
        assert visit["split"] == label
        done = render_visit(visit, _STATE["source"], _STATE["registry"], window_chars=config["window_chars"], view=_view())
        rows.append(json.dumps({"kind": "visit", "id": done.id, "split": label, "index": index, "first_line": offset,
                                "lines": len(done.lines), "provenance": done.provenance, "probe": config["name"]},
                               sort_keys=True))
        rows += [json.dumps({"kind": "question", **_shifted(q, offset), "probe": config["name"]}, sort_keys=True)
                 for q in done.questions]
        parts.append(done.text + "\n\n")
        offset += len(done.lines) + 1
        rendered.append(done)
    sampled = [d for i, d in zip(range(start, stop), rendered) if audit_every and i % audit_every == 0]
    audit_visits(sampled, profile, _STATE["registry"], _STATE["names"], _STATE["teacher"], _STATE["styles"])
    return "".join(parts), rows, rendered


def _make_shard(task: tuple[int, int, int, str]) -> dict[str, Any]:
    shard, start, stop, directory = task
    started = time.perf_counter()
    text, rows, rendered = render_range(start, stop, audit_every=_STATE["config"]["audit_every"])
    base = Path(directory) / f"shard-{shard:05d}"
    _write(base.with_suffix(".jsonl"), "\n".join(rows) + "\n")
    _write(base.with_suffix(".txt"), text)
    return {"shard": shard, "visits": stop - start, "questions": sum(len(r.questions) for r in rendered),
            "chars": len(text), "seconds": time.perf_counter() - started}


def write_probe(name: str, concerns: Iterable[str], n_visits: int, out_dir: os.PathLike, workers: int = 1, *,
                seed: int = PROBE_SEED, index_offset: int = 0, visits_per_shard: int = VISITS_PER_SHARD,
                window_chars: int = WINDOW_CHARS, audit_every: int = 1, verbose: bool = True,
                patterns: Optional[str] = None) -> dict[str, Any]:
    """Write (or finish writing) `n_visits` visits of the probe `name` under `out_dir/<name>/` (same files as write_shards)."""
    profile = Profile.of(concerns)
    if n_visits < 0 or visits_per_shard < 1 or workers < 1:
        raise ValueError("need n_visits >= 0, visits_per_shard >= 1 and workers >= 1")
    directory = Path(out_dir) / name
    directory.mkdir(parents=True, exist_ok=True)
    config = {"name": name, "switched": sorted(profile.switched), "seed": seed, "index_offset": index_offset,
              "window_chars": window_chars, "audit_every": audit_every}
    if patterns:  # another pattern bank (e.g. the train-only paraphrase bank); recorded so a rerun with another bank is refused
        config["patterns"] = str(patterns)
    _setup(config)
    manifest = {
        "split": profile.label, "probe": name, "n_visits": n_visits, "seed": seed, "index_offset": index_offset,
        "visits_per_shard": visits_per_shard, "window_chars": window_chars, "patterns": _STATE["source"].version,
        "generator": "generalize.probes:probe_visit", **profile.describe(),
        "split_manifest": _STATE["registry"].manifest().payload(),
    }
    path = directory / "manifest.json"
    if path.exists():
        saved = json.loads(path.read_text(encoding="utf-8"))
        if saved != manifest:
            changed = sorted(k for k in set(saved) | set(manifest) if saved.get(k) != manifest.get(k))
            raise ValueError(f"{directory} was written with different settings ({', '.join(changed)}); use a new directory")
    else:
        _write(path, json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    tasks = [(shard, start, min(start + visits_per_shard, n_visits), str(directory))
             for shard, start in enumerate(range(0, n_visits, visits_per_shard))
             if not (directory / f"shard-{shard:05d}.txt").exists()]
    started = time.perf_counter()
    if workers == 1 or len(tasks) <= 1:
        results = [_make_shard(t) for t in tasks]
    else:
        with multiprocessing.get_context("spawn").Pool(min(workers, len(tasks)), initializer=_setup, initargs=(config,)) as pool:
            results = list(pool.imap_unordered(_make_shard, tasks))
    report = {"probe": name, "directory": str(directory), "shards_written": len(results),
              "visits": sum(r["visits"] for r in results), "questions": sum(r["questions"] for r in results),
              "wall_seconds": time.perf_counter() - started}
    if verbose:
        print(f"{name}: wrote {report['shards_written']} shards ({report['visits']} visits, {report['questions']} questions) "
              f"in {report['wall_seconds']:.1f}s", flush=True)
    return report


def write_training_data(concerns: Iterable[str], n_visits: int, out_dir: os.PathLike, workers: int = 1, *,
                        seed: int = 0, index_offset: int = TRAIN_ARM_OFFSET, name: Optional[str] = None,
                        visits_per_shard: int = VISITS_PER_SHARD, **options: Any) -> dict[str, Any]:
    """TRAINING visits (TRAIN names, patterns, styles, families) with the given concerns switched.

    Only "difficulty" is accepted: switching name / template / style / rule would train on validation items.
    Seed 0 is kept, with visit indices from `index_offset` (default 10,000,000), so no visit duplicates
    a normal train visit (indices 0..99,999). Output: `out_dir/<name>/` with name "train+difficulty" by default;
    the visits are labelled split "train" (load the cache with split="train")."""
    concerns = tuple(concerns)
    if options.get("patterns") and concerns:
        raise ValueError("switch one thing at a time: an extra pattern bank or difficulty, not both")
    if set(concerns) - {"difficulty"}:
        raise ValueError("training data may only switch 'difficulty'; other concerns would leak validation items into training")
    if index_offset < 100_000:
        raise ValueError("index_offset must be >= 100,000 so no visit repeats the normal train visits")
    name = name or "train+" + "+".join(concerns or ("none",))
    return write_probe(name, concerns, n_visits, out_dir, workers, seed=seed, index_offset=index_offset,
                       visits_per_shard=visits_per_shard, **options)


# ------------------------------------------------------------------------------------------------ audits / summaries
def audit_probe_dir(directory: os.PathLike) -> dict[str, int]:
    """Re-check a written probe from its files: visit provenance against the manifest's per-axis split map."""
    directory = Path(directory)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    axes = manifest["axes"]
    _only_allowed(label=manifest["split"], **{f"axis {a}": s for a, s in axes.items()})
    source = PatternSource.load()
    registry = village_registry(source, world_families())
    teacher = {p for p, b in source.bank.items() if b in TEACHER_BANKS}
    count = 0
    for meta in sorted(directory.glob("shard-*.jsonl")):
        for line in meta.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            if row["kind"] != "visit":
                continue
            count += 1
            for axis, items in row["provenance"].items():
                for item in items:
                    want = axes["teacher_style"] if axis == "template" and item in teacher else axes[axis]
                    got = registry.split_of(axis, item)
                    if got != want or got not in ALLOWED_SPLITS:
                        raise SplitLeak(f"{meta.name} {row['id']}: {axis} {item!r} is {got}, probe needs {want}")
    return {"visits": count}


def summarize(directory: os.PathLike) -> dict[str, Any]:
    """Question count, depth histogram, R8 / multi-family counts, qtype and style mix of a written probe dir."""
    directory = Path(directory)
    styles = style_assignment()
    depth, qtype, style, fam = Counter(), Counter(), Counter(), Counter()
    visits = questions = r8 = multi = 0
    for meta in sorted(directory.glob("shard-*.jsonl")):
        for line in meta.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            if row["kind"] == "visit":
                visits += 1
                continue
            questions += 1
            depth[row["depth"]] += 1
            qtype[row["base_qtype"]] += 1
            if row.get("style"):
                style[row["style"]] += 1
            fs = row.get("families") or []
            r8 += "R8" in fs
            multi += len(fs) >= 2
            fam.update(fs)
    return {"probe": directory.name, "visits": visits, "questions": questions,
            "depth": {str(k): depth[k] for k in sorted(depth, key=lambda x: (x is None, x))},
            "depth_gt3": sum(v for k, v in depth.items() if k is not None and k > 3), "r8": r8, "multi_family": multi,
            "families": dict(sorted(fam.items())), "qtype": dict(sorted(qtype.items())),
            "styles": dict(sorted(style.items())),
            "validation_style_questions": sum(v for k, v in style.items() if styles[k] == "validation"),
            "train_style_questions": sum(v for k, v in style.items() if styles[k] == "train")}


def summary_markdown(rows: Sequence[Mapping[str, Any]]) -> str:
    keys = sorted({k for r in rows for k in r["depth"]}, key=lambda x: int(x) if x.lstrip("-").isdigit() else 99)
    head = ["probe", "visits", "questions"] + [f"d{k}" for k in keys] + ["d>3", "R8", "multi-fam", "val-style q", "train-style q"]
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for r in rows:
        cells = [r["probe"], r["visits"], r["questions"]] + [r["depth"].get(k, 0) for k in keys] + [
            r["depth_gt3"], r["r8"], r["multi_family"], r["validation_style_questions"], r["train_style_questions"]]
        out.append("| " + " | ".join(map(str, cells)) + " |")
    return "\n".join(out)


def check_pall_reproduces_validation(n_visits: int = 40) -> dict[str, Any]:
    """Pall with seed 0 against the ordinary validation stream, in memory: text and question rows compared visit for visit."""
    from learnlab.village import shards
    shards._setup({"seed": 0, "generator": shards.GENERATOR, "families": shards.FAMILIES, "names": None,
                   "patterns": None, "window_chars": WINDOW_CHARS, "audit_every": 0})
    ref_text, ref_rows, _ = shards.render_range("validation", 0, n_visits)
    _setup({"name": "Pall", "switched": list(CONCERNS), "seed": 0, "index_offset": 0, "window_chars": WINDOW_CHARS,
            "audit_every": 1})
    text, rows, _ = render_range(0, n_visits)
    strip = lambda rs: [{k: v for k, v in json.loads(r).items() if k != "probe"} for r in rs]
    return {"visits": n_visits, "text_identical": text == ref_text, "rows_identical": strip(rows) == strip(ref_rows)}


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("out_dir", nargs="?")
    ap.add_argument("--visits", type=int, default=1000)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--probes", default=",".join(PROBES), help="comma list from " + ",".join(PROBES))
    ap.add_argument("--seed", type=int, default=PROBE_SEED)
    ap.add_argument("--visits-per-shard", type=int, default=VISITS_PER_SHARD)
    ap.add_argument("--check-pall", type=int, metavar="N", help="compare N visits of Pall (seed 0) with validation, then exit")
    a = ap.parse_args(argv)
    if a.check_pall:
        print(json.dumps(check_pall_reproduces_validation(a.check_pall)))
        return 0
    if not a.out_dir:
        ap.error("OUT_DIR is required")
    chosen = [p for p in a.probes.split(",") if p]
    unknown = [p for p in chosen if p not in PROBES]
    if unknown:
        ap.error(f"unknown probes {unknown}; choose from {list(PROBES)}")
    for name in chosen:
        write_probe(name, PROBES[name], a.visits, a.out_dir, a.workers, seed=a.seed, visits_per_shard=a.visits_per_shard)
        audit_probe_dir(Path(a.out_dir) / name)
    rows = [summarize(Path(a.out_dir) / n) for n in chosen]
    (Path(a.out_dir) / "PROBE_SUMMARY.json").write_text(json.dumps(rows, indent=1) + "\n")
    (Path(a.out_dir) / "PROBE_SUMMARY.md").write_text(summary_markdown(rows) + "\n")
    print(summary_markdown(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
