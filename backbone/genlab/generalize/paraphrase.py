#!/usr/bin/env python3
"""Paraphrase multiplicity: grow the TRAIN wordings of the village pattern bank.

Reads data/village/patterns/bank-v1.json and writes bank-v1-aug.json, identical except that
  * every non-teacher bank (ev.*, q.*, rule.*) gains TRAIN-only patterns until it has at least
    `--target` (default 24) train wordings, and
  * every teacher bank gains patterns in the six TRAIN styles until each (bank, style) has at least
    twice its old count.
Validation and test entries, ids, texts and order are never touched.

A bank that `PatternSource.load` already fills wholly from the fallback (some split or teacher style
is empty in bank-v1) is left alone: adding train patterns there would change nothing, because the
loader throws the whole bank away, and filling the missing held-out split would change evaluation.

Acceptance follows scripts/gen_patterns.py: parse_generation -> check_pattern -> dedup (here against
EVERY existing pattern of the bank in all splits, mechanically) -> a meaning check by a second model
call, yes on both sampled value sets (teacher frames: the frame check, one call). Extra mechanical
guards, done without reading held-out text: teacher frames may not overlap a held-out frame (what
`gen_patterns._drop_shared_frames` does), and a simulated `splits.audit_examples` pass over every
pattern must raise no leak that involves a new id.

Only TRAIN texts are ever put into a prompt. Writer: claude-sonnet-5-5, checker: claude-haiku-5-5
(Anthropic API, key from $LEARNER_ANTHROPIC_API_KEY, never printed). Raw responses are cached under
/tmp/paraphrase-cache so reruns cost nothing.

  python -m generalize.paraphrase plan
  python -m generalize.paraphrase run [--target 24] [--budget 8.0] [--banks q.,rule.]
  python -m generalize.paraphrase report
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import random
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from learnlab import patterns as P  # noqa: E402
from learnlab.splits import SPLITS, SplitManifest, SplitLeak  # noqa: E402
from learnlab.village import render as R  # noqa: E402

PATTERNS = ROOT / "data" / "village" / "patterns"
SRC = PATTERNS / "bank-v1.json"
OUT = PATTERNS / "bank-v1-aug.json"
CACHE = Path("/tmp/paraphrase-cache")
STATE = Path("/tmp/paraphrase-cache/state.json")  # accepted patterns so far (resumable)
API = "https://api.anthropic.com/v1/messages"
WRITER, CHECKER = "claude-sonnet-5-5", "claude-haiku-5-5"
# USD per million tokens (input, output); an assumption used only for the budget guard and the log.
PRICE = {WRITER: (3.0, 15.0), CHECKER: (1.0, 5.0)}
TRAIN_STYLES = ("bossy", "cheerful", "grandparent", "questioning", "storyteller", "terse")
THINKING_OFF = {WRITER: {"type": "between_tools"}, CHECKER: {"type": "disabled"}}
PER_REQUEST = 16
WRITER_TEMPERATURE = 1.0
MAX_ROUNDS = 8


def _load_gen_patterns() -> Any:
    spec = importlib.util.spec_from_file_location("gen_patterns", ROOT / "scripts" / "gen_patterns.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


G = _load_gen_patterns()

# ------------------------------------------------------------------ API with cache


class Usage:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.calls: Counter = Counter()
        self.cached: Counter = Counter()
        self.tokens: dict[str, list[int]] = defaultdict(lambda: [0, 0])

    def add(self, model: str, usage: Mapping[str, int], cached: bool) -> None:
        with self.lock:
            if cached:
                self.cached[model] += 1
                return
            self.calls[model] += 1
            self.tokens[model][0] += int(usage.get("input_tokens", 0))
            self.tokens[model][1] += int(usage.get("output_tokens", 0))

    def cost(self) -> float:
        return sum(i * PRICE[m][0] / 1e6 + o * PRICE[m][1] / 1e6 for m, (i, o) in self.tokens.items())

    def summary(self) -> str:
        parts = [f"{m}: {self.calls[m]} calls (+{self.cached[m]} cached), {i} in / {o} out tokens"
                 for m, (i, o) in sorted(self.tokens.items())]
        return "; ".join(parts) + f"; est. cost ${self.cost():.2f}"


USAGE = Usage()
BUDGET = {"limit": 8.0}


class BudgetExceeded(RuntimeError):
    pass


def complete(model: str, prompt: str, *, max_tokens: int, temperature: Optional[float], tag: str = "") -> str:
    """One Messages API call, cached on (model, prompt, max_tokens, temperature, tag)."""
    key = hashlib.sha256(json.dumps([model, prompt, max_tokens, temperature, tag]).encode()).hexdigest()
    path = CACHE / key[:2] / f"{key}.json"
    if path.exists():
        record = json.loads(path.read_text())
        USAGE.add(model, record["usage"], cached=True)
        return record["text"]
    if USAGE.cost() > BUDGET["limit"]:
        raise BudgetExceeded(f"estimated spend ${USAGE.cost():.2f} passed the limit ${BUDGET['limit']:.2f}")
    payload = {"model": model, "max_tokens": max_tokens, "messages": [{"role": "user", "content": prompt}]}
    payload["thinking"] = THINKING_OFF[model]  # otherwise the model spends max_tokens on hidden thinking
    if temperature is not None:  # claude-haiku-5-5 rejects the parameter ("deprecated for this model")
        payload["temperature"] = temperature
    body = json.dumps(payload).encode()
    headers = {"x-api-key": os.environ["LEARNER_ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01",
               "content-type": "application/json"}
    last: Optional[Exception] = None
    for attempt in range(8):
        try:
            with urllib.request.urlopen(urllib.request.Request(API, data=body, headers=headers), timeout=120) as response:
                data = json.load(response)
            text = "".join(block.get("text", "") for block in data["content"] if block.get("type") == "text")
            usage = data.get("usage", {})
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(f".{threading.get_ident()}.tmp")
            tmp.write_text(json.dumps({"model": model, "tag": tag, "prompt": prompt, "text": text,
                                       "usage": {"input_tokens": usage.get("input_tokens", 0),
                                                 "output_tokens": usage.get("output_tokens", 0)}}))
            tmp.replace(path)
            USAGE.add(model, usage, cached=False)
            return text
        except urllib.error.HTTPError as error:
            last = RuntimeError(f"HTTP {error.code}")  # never include headers or the key
            if error.code not in (408, 409, 429, 500, 502, 503, 504, 529):
                raise last from None
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as error:
            last = RuntimeError(f"network error {type(error).__name__}")
        time.sleep(min(60.0, 2.0 ** attempt) * (0.5 + random.random()))
    raise last or RuntimeError("API failed")


# ------------------------------------------------------------------ bank handling


def fallback_banks(path: Path) -> set[str]:
    """Banks that PatternSource.load fills wholly from the fallback (ids start with 'fb-')."""
    source = R.PatternSource.load(path)
    return {bank for pid, bank in source.bank.items() if pid.startswith("fb-")}


def current_train(data: Mapping[str, Any]) -> dict[Any, list[str]]:
    """key -> train texts; key is the bank (non-teacher) or (bank, style) (teacher)."""
    out: dict[Any, list[str]] = {}
    for bank, by_split in data["banks"].items():
        if bank.startswith("t."):
            for style in TRAIN_STYLES:
                out[(bank, style)] = [e["text"] for e in by_split["train"] if e.get("style") == style]
        else:
            out[bank] = [e["text"] for e in by_split["train"]]
    return out


def all_texts(data: Mapping[str, Any], bank: str) -> list[str]:
    return [e["text"] for split in SPLITS for e in data["banks"][bank].get(split, [])]


def held_out_frames(data: Mapping[str, Any]) -> list[str]:
    return [e["text"] for bank in data["banks"] if bank.startswith("t.") for split in ("validation", "test")
            for e in data["banks"][bank][split]]


def plan(data: Mapping[str, Any], target: int, skip: set[str]) -> dict[Any, int]:
    """key -> number of train patterns to add."""
    need: dict[Any, int] = {}
    for key, texts in current_train(data).items():
        bank = key[0] if isinstance(key, tuple) else key
        if bank in skip:
            continue
        want = len(texts) if isinstance(key, tuple) else target - len(texts)
        if want > 0:
            need[key] = want
    return need


# ------------------------------------------------------------------ candidate pipeline


def writer_prompt(key: Any, variant: str, examples: Sequence[str], round_: int) -> str:
    bank = key[0] if isinstance(key, tuple) else key
    prompt = P.build_prompt(bank, variant, PER_REQUEST)
    if examples:
        shown = random.Random(f"{key}:{variant}:{round_}").sample(list(examples), min(8, len(examples)))
        marker = "Now write exactly"
        extra = "Wordings that already exist (write different ones, with a different shape):\n" + "\n".join(shown)
        head, _, tail = prompt.rpartition(marker)
        prompt = f"{head}{extra}\n{marker}{tail}"
    return prompt


def check_candidate(bank: str, text: str) -> bool:
    """The meaning check: yes on 2 sampled value sets (frame banks: the frame check, once)."""
    pid = P.pattern_id(bank, text)
    frame = bank in P.FRAME_BANKS
    for values in P.crosscheck_values(bank, pid):
        if frame:
            prompt = P.frame_prompt(bank, text, values)
            answer = complete(CHECKER, prompt, max_tokens=200, temperature=None, tag="check")
            if not P.parse_last_yes_no(answer):
                return False
            return True
        answer = complete(CHECKER, P.crosscheck_prompt(bank, text, values), max_tokens=8, temperature=None, tag="check")
        if not P.parse_yes_no(answer):
            return False
    return True


class Run:
    def __init__(self, data: dict[str, Any], need: dict[Any, int], workers: int) -> None:
        self.data, self.need, self.workers = data, need, workers
        self.frames = held_out_frames(data)
        self.accepted: dict[Any, list[dict[str, Any]]] = defaultdict(list)  # key -> new entries
        self.stats: dict[Any, Counter] = defaultdict(Counter)
        self.checked: dict[str, bool] = {}
        self.seen_ids = {e["id"] for by_split in data["banks"].values() for rows in by_split.values() for e in rows}
        self.rejected_lines: dict[Any, list[tuple[str, str]]] = defaultdict(list)
        if STATE.exists():
            saved = json.loads(STATE.read_text())
            for item in saved["accepted"]:
                key = (item["bank"], item["style"]) if item.get("style") else item["bank"]
                if key in need and item["id"] not in self.seen_ids:
                    self.accepted[key].append(item)
                    self.seen_ids.add(item["id"])

    def save(self) -> None:
        STATE.parent.mkdir(parents=True, exist_ok=True)
        rows = [e for entries in self.accepted.values() for e in entries]
        STATE.write_text(json.dumps({"accepted": rows}, indent=1, sort_keys=True))

    def remaining(self, key: Any) -> int:
        return self.need[key] - len(self.accepted[key])

    def existing(self, key: Any) -> list[str]:
        return current_train(self.data)[key] + [e["text"] for e in self.accepted[key]]

    def variant_list(self, key: Any) -> list[str]:
        return [key[1]] if isinstance(key, tuple) else list(P.FLAVOURS)

    def request_count(self, key: Any, round_: int) -> int:
        seen = self.stats[key]["lines"]
        rate = max(0.05, self.stats[key]["accepted"] / seen) if seen else 0.35
        wanted = self.remaining(key) / (rate * PER_REQUEST) * 1.15
        return max(1, min(6, math.ceil(wanted)))

    def generate(self, key: Any, round_: int) -> list[str]:
        variants = self.variant_list(key)
        existing = self.existing(key)
        jobs = []
        for i in range(self.request_count(key, round_)):
            variant = variants[(round_ * 3 + i) % len(variants)]
            jobs.append(writer_prompt(key, variant, existing, round_ * 10 + i))
        texts: list[str] = []
        for prompt in jobs:
            out = complete(WRITER, prompt, max_tokens=1000, temperature=WRITER_TEMPERATURE, tag="write")
            texts += P.parse_generation(out)
        return texts

    def filter_mechanical(self, key: Any, lines: list[str]) -> list[str]:
        bank = key[0] if isinstance(key, tuple) else key
        stat = self.stats[key]
        stat["lines"] += len(lines)
        pool = all_texts(self.data, bank) + [e["text"] for entries in self.accepted.values() for e in entries
                                              if e["bank"] == bank]
        kept: list[str] = []
        for text in lines:
            if P.check_pattern(bank, text):
                stat["mech_fail"] += 1
                continue
            if any(P.normalize(text) == P.normalize(t) or P.jaccard(text, t) >= P.NEAR_DUPLICATE for t in pool + kept):
                stat["dup"] += 1
                continue
            if bank.startswith("t.") and any(G._frames_overlap(text, h) for h in self.frames):
                stat["frame_overlap"] += 1
                continue
            if P.pattern_id(bank, text) in self.seen_ids:
                stat["dup"] += 1
                continue
            kept.append(text)
        return kept

    def round(self, round_: int) -> bool:
        open_keys = [k for k in self.need if self.remaining(k) > 0]
        if not open_keys:
            return False
        print(f"round {round_}: {len(open_keys)} keys open, {sum(self.remaining(k) for k in open_keys)} patterns missing; "
              f"{USAGE.summary()}", flush=True)
        with ThreadPoolExecutor(self.workers) as pool:
            generated = list(pool.map(lambda k: self.generate(k, round_), open_keys))
        candidates = {}
        for key, lines in zip(open_keys, generated):
            kept = self.filter_mechanical(key, lines)
            candidates[key] = kept[: max(4, int(self.remaining(key) * 2.2))]
        flat = [(k, t) for k, ts in candidates.items() for t in ts]
        with ThreadPoolExecutor(self.workers) as pool:
            verdicts = list(pool.map(lambda kt: check_candidate(kt[0][0] if isinstance(kt[0], tuple) else kt[0], kt[1]), flat))
        for (key, text), ok in zip(flat, verdicts):
            bank = key[0] if isinstance(key, tuple) else key
            stat = self.stats[key]
            stat["checked"] += 1
            if not ok:
                self.rejected_lines[key].append((text, "meaning"))
                continue
            pid = P.pattern_id(bank, text)
            rivals = all_texts(self.data, bank) + [e["text"] for es in self.accepted.values() for e in es if e["bank"] == bank]
            if pid in self.seen_ids or any(P.jaccard(text, t) >= P.NEAR_DUPLICATE for t in rivals):
                stat["dup_across_keys"] += 1  # two styles (or keys) of one bank wrote the same wording this round
                continue
            entry = {"id": pid, "text": text, "writer": WRITER, "bank": bank}
            if isinstance(key, tuple):
                entry["style"] = key[1]
            stat["accepted"] += 1
            self.accepted[key].append(entry)
            self.seen_ids.add(pid)
        self.save()
        return True


# ------------------------------------------------------------------ simulated leak audit

_FILL = {
    "person": ("Kelo", "Rami"), "person_b": ("Tosa", "Vemi"), "leader": ("Nuba", "Lira"), "giver": ("Zobi", "Mafo"),
    "receiver": ("Rami", "Kelo"), "object": ("the red cup", "the cup"), "place": ("the old barn", "the barn"),
    "place2": ("the green mill", "the mill"), "container": ("the blue box", "the box"), "object_kind": ("plates", "red plates"),
    "item": ("a cup", "an apple"), "time": ("noon", "night"), "material": ("glass", "clay"), "category": ("dishes", "toys"),
    "colour": ("red", "blue"), "direction": ("north", "west"), "count": ("three", "four"),
}


def synthetic_examples(source: R.PatternSource) -> list[dict[str, Any]]:
    """Each pattern as the audit would see its unit (nested sentences masked as x), twice."""
    examples = []
    for pid, text in source.text.items():
        for variant in (0, 1):
            masked = {name: (R.MASK if name in R.NESTED_SLOTS else _FILL[name][variant]) for name in R.BANK_SLOTS[source.bank[pid]]}
            unit = R._BREAKS.sub(" ", R._SLOT.sub(lambda m: masked[m.group(1)], text)).strip()
            examples.append({"id": f"{pid}/{variant}", "split": source.split[pid], "provenance": {"template": [pid]}, "text": unit})
    return examples


def leaking_ids(path: Path) -> set[str]:
    """Pattern ids named in a simulated audit of the bank at `path` (empty set when clean)."""
    from learnlab.splits import audit_examples
    from learnlab.village.stream import split_vocab
    source = R.PatternSource.load(path)
    registry = R.village_registry(source)
    try:
        audit_examples(synthetic_examples(source), registry, text_of=lambda r: r["text"], vocab=split_vocab(source),
                       require_recorded=False)
    except SplitLeak as error:
        message = str(error)
        return set(re.findall(r"\(([0-9a-f]{12})/\d\)", message)) | set(re.findall(r"template '([0-9a-f]{12})'", message))
    return set()


# ------------------------------------------------------------------ writing the bank


def assemble(base: Mapping[str, Any], new: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """bank-v1 plus `new` train entries: banks, manifest assignment, digest, counts and shortfalls."""
    new = list(new)
    out = json.loads(json.dumps(base))
    assignment = out["manifest"]["families"]["template"]["assignment"]
    for entry in new:
        if entry["id"] in assignment:
            raise ValueError(f"id {entry['id']} already assigned")
        row = {"id": entry["id"], "text": entry["text"], "writer": entry["writer"]}
        if entry.get("style"):
            row["style"] = entry["style"]
        out["banks"][entry["bank"]]["train"].append(row)
        assignment[entry["id"]] = "train"
    for by_split in out["banks"].values():
        by_split["train"].sort(key=lambda e: e["id"])
    out["manifest_digest"] = SplitManifest.from_json(json.dumps(out["manifest"])).digest()
    for bank, count in out["counts"].items():
        count["train"] = len(out["banks"][bank]["train"])
        count["accepted"] = sum(len(out["banks"][bank][s]) for s in SPLITS)
    out["shortfalls"] = shortfalls(out)
    out["augmentation"] = {
        "script": "generalize/paraphrase.py", "base_digest": base["manifest_digest"],
        "note": "train-only additions; validation/test entries and all old assignments unchanged",
        "new_train_patterns": len(new),
    }
    return out


def shortfalls(data: Mapping[str, Any]) -> dict[str, int]:
    missing = {}
    for bank_id, bank in P.BANKS.items():
        rows = [e for s in SPLITS for e in data["banks"][bank_id][s]]
        if bank.kind == "teacher":
            per = Counter(e["style"] for e in rows)
            for style in P.STYLES:
                if per[style] < bank.target:
                    missing[f"{bank_id}/{style}"] = bank.target - per[style]
        elif len(rows) < bank.target:
            missing[bank_id] = bank.target - len(rows)
    return missing


def write_bank(data: Mapping[str, Any], path: Path) -> None:
    path.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n")


def verify_untouched(base: Mapping[str, Any], aug: Mapping[str, Any]) -> None:
    for bank, by_split in base["banks"].items():
        for split in ("validation", "test"):
            if aug["banks"][bank][split] != by_split[split]:
                raise AssertionError(f"{bank} {split} changed")
    old = base["manifest"]["families"]["template"]["assignment"]
    new = aug["manifest"]["families"]["template"]["assignment"]
    assert all(new[k] == v for k, v in old.items()), "old assignment changed"
    assert all(new[k] == "train" for k in set(new) - set(old)), "new id not train"
    assert aug["manifest"]["families"]["teacher_style"] == base["manifest"]["families"]["teacher_style"]
    for bank, by_split in base["banks"].items():
        olds = {e["id"]: e for e in by_split["train"]}
        assert all(e in aug["banks"][bank]["train"] for e in olds.values()), f"{bank} lost train entries"


def final_dedup(base: Mapping[str, Any], run: "Run") -> int:
    """Drop accepted entries that near-duplicate an earlier accepted one of the same bank (e.g. two styles)."""
    dropped = 0
    kept: dict[str, list[str]] = defaultdict(list)
    for key in list(run.accepted):
        survivors = []
        for entry in run.accepted[key]:
            bank = entry["bank"]
            pool = all_texts(base, bank) + kept[bank]
            if any(P.jaccard(entry["text"], t) >= P.NEAR_DUPLICATE for t in pool):
                dropped += 1
                continue
            kept[bank].append(entry["text"])
            survivors.append(entry)
        run.accepted[key] = survivors
    print(f"final cross-key dedup dropped {dropped}", flush=True)
    return dropped


# ------------------------------------------------------------------ main


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("plan", "run", "report"))
    parser.add_argument("--target", type=int, default=24)
    parser.add_argument("--budget", type=float, default=8.0)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--banks", default="", help="comma-separated bank-id prefixes to restrict to (default all)")
    parser.add_argument("--source", type=Path, default=SRC)
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--rounds", type=int, default=MAX_ROUNDS)
    args = parser.parse_args(argv)
    BUDGET["limit"] = args.budget
    base = json.loads(args.source.read_text())
    skip = fallback_banks(args.source)
    need = plan(base, args.target, skip)
    prefixes = tuple(p for p in args.banks.split(",") if p)
    if prefixes:
        need = {k: v for k, v in need.items() if (k[0] if isinstance(k, tuple) else k).startswith(prefixes)}
    if args.command == "plan":
        print(f"left on the fallback (unchanged): {sorted(skip)}")
        for key, count in sorted(need.items(), key=str):
            print(f"  {key}: have {len(current_train(base)[key])}, add {count}")
        print(f"total to add: {sum(need.values())}")
        return
    CACHE.mkdir(parents=True, exist_ok=True)
    run = Run(base, need, args.workers)
    try:
        for round_ in range(args.rounds):
            if not run.round(round_):
                break
    except BudgetExceeded as error:
        print("STOPPED:", error, flush=True)
    run.save()
    final_dedup(base, run)
    # Leak-audit loop: write, simulate the audit, drop any new id it names, repeat.
    dropped: set[str] = set()
    for _ in range(6):
        entries = [e for es in run.accepted.values() for e in es if e["id"] not in dropped]
        aug = assemble(base, entries)
        write_bank(aug, args.out)
        bad = leaking_ids(args.out) - set(base["manifest"]["families"]["template"]["assignment"])
        print(f"simulated audit: {len(bad)} new ids implicated", flush=True)
        if not bad:
            break
        dropped |= bad
    verify_untouched(base, aug)
    R.PatternSource.load(args.out)
    print(f"dropped by audit: {len(dropped)}")
    print(f"wrote {args.out}: {len(entries)} new train patterns")
    print(USAGE.summary())
    summary = {"new": len(entries), "dropped_by_audit": len(dropped), "usage": USAGE.summary(),
               "stats": {str(k): dict(v) for k, v in run.stats.items()},
               "unfilled": {str(k): run.remaining(k) for k in run.need if run.remaining(k) > 0}}
    (CACHE / "summary.json").write_text(json.dumps(summary, indent=1))
    still = {k: v for k, v in summary["unfilled"].items()}
    print("keys still below target:", still)


if __name__ == "__main__":
    main()
