#!/usr/bin/env python3
"""Resumable driver that grows the village pattern bank with two local writers.

  plan        request counts per bank
  generate    ask a writer for patterns -> raw/<writer>.jsonl (one line per request, resumable)
  verify      parse + check_pattern + dedup -> candidates.jsonl
  crosscheck  the OTHER writer confirms each candidate's meaning -> crosscheck/<checker>.jsonl
  finalize    accepted patterns split train/validation/test -> bank-v1.json
  topup       plan extra requests for banks below target
  status      progress

Stdlib only, so it runs under both the uv Python and the Bonsai (MLX) venv.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import hashlib
import http.client
import json
import re
import math
import random
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable, Iterable, Optional, Sequence
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from learnlab import patterns as P  # noqa: E402

DATA = ROOT / "data" / "village" / "patterns"
BONSAI_PACK = ROOT / ".runtime" / "teacher" / "models" / "Ternary-Bonsai-2-27B-mlx-2bit"
LLAMA_URL = "http://127.0.0.1:18081"
LLAMA_MODEL = "qwen3.8-27b"
GEN_PARAMS = {"temperature": 0.9, "top_p": 0.95, "max_tokens": 700}
CHECK_PARAMS = {"temperature": 0.0, "top_p": 1.0, "max_tokens": 8}


# ------------------------------------------------------------------- backends


class LlamaBackend:
    """llama-server's OpenAI-compatible chat endpoint, thinking disabled per request."""

    def __init__(self, url: str = LLAMA_URL, model: str = LLAMA_MODEL, timeout: float = 300.0, retries: int = 3) -> None:
        self.url, self.model, self.timeout, self.retries = url.rstrip("/"), model, timeout, retries
        self.threaded = True

    def complete(self, prompt: str, *, temperature: float, top_p: float, seed: int, max_tokens: int) -> tuple[str, int]:
        body = json.dumps({
            "model": self.model, "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature, "top_p": top_p, "seed": seed, "max_tokens": max_tokens,
            "chat_template_kwargs": {"enable_thinking": False},
        }).encode()
        for attempt in range(self.retries + 1):
            try:
                request = urllib.request.Request(f"{self.url}/v1/chat/completions", body, {"Content-Type": "application/json"})
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    data = json.load(response)
                return data["choices"][0]["message"].get("content") or "", int(data.get("usage", {}).get("completion_tokens", 0))
            except (urllib.error.URLError, http.client.HTTPException, TimeoutError, ConnectionError, KeyError, ValueError) as error:
                if attempt == self.retries:
                    raise RuntimeError(f"llama request failed after {self.retries} retries: {error}") from error
                time.sleep(5 * 3 ** attempt)
        raise AssertionError("unreachable")


class MlxBackend:
    """Ternary Bonsai 2 27B on the Mac, loaded once per process, one request at a time."""

    def __init__(self, pack: Path = BONSAI_PACK) -> None:
        self.pack, self.threaded, self._loaded = pack, False, None

    def complete(self, prompt: str, *, temperature: float, top_p: float, seed: int, max_tokens: int) -> tuple[str, int]:
        if self._loaded is None:
            sys.path.insert(0, str(self.pack / "runtime"))
            from vision_artifact import load_vl_model  # type: ignore
            from mlx_vlm import generate  # type: ignore
            model, processor, _config = load_vl_model(str(self.pack))
            self._loaded = (model, processor, generate)
        model, processor, generate = self._loaded
        chat = processor.tokenizer.apply_chat_template(
            [{"role": "user", "content": prompt}], tokenize=False, add_generation_prompt=True, enable_thinking=False
        )
        result = generate(model, processor, chat, image=None, max_tokens=max_tokens, temperature=temperature,
                          top_p=top_p, seed=seed, verbose=False)
        return getattr(result, "text", result), int(getattr(result, "generation_tokens", 0) or 0)


def make_backend(args: argparse.Namespace) -> Any:
    return LlamaBackend(args.url) if args.backend == "llama" else MlxBackend()


# ------------------------------------------------------------------ requests


def _hash_int(text: str) -> int:
    return int(hashlib.sha256(text.encode()).hexdigest()[:8], 16)


def _variants(bank_id: str) -> tuple[str, ...]:
    return P.STYLES if P.BANKS[bank_id].kind == "teacher" else tuple(P.FLAVOURS)


def plan() -> list[dict[str, Any]]:
    """The base requests: 2.5x each target, spread over flavours (or per teacher style)."""
    requests = []
    flavours = tuple(P.FLAVOURS)
    for index, (bank_id, bank) in enumerate(P.BANKS.items()):
        count = math.ceil(bank.target * P.OVERSAMPLE / P.PER_REQUEST)
        if bank.kind == "teacher":
            for style in P.STYLES:
                requests += [{"id": f"{bank_id}:{style}:{k}", "bank": bank_id, "variant": style, "n": P.PER_REQUEST} for k in range(count)]
        else:
            for k in range(count):
                flavour = flavours[(index + k) % len(flavours)]
                requests.append({"id": f"{bank_id}:{flavour}:{k}", "bank": bank_id, "variant": flavour, "n": P.PER_REQUEST})
    return requests


def all_requests(data: Path) -> list[dict[str, Any]]:
    requests = plan()
    seen = {r["id"] for r in requests}
    for row in read_jsonl(data / "requests-topup.jsonl"):
        if row["id"] not in seen:
            seen.add(row["id"])
            requests.append(row)
    return requests


def in_share(item_id: str, share: tuple[int, int]) -> bool:
    index, total = share
    return _hash_int(item_id) % total == index


def parse_share(text: str) -> tuple[int, int]:
    index, total = (int(part) for part in text.split("/"))
    if not 0 <= index < total:
        raise argparse.ArgumentTypeError(f"share must be I/N with 0 <= I < N, got {text}")
    return index, total


def _bank_match(bank_id: str, prefixes: Optional[Sequence[str]]) -> bool:
    return not prefixes or any(bank_id.startswith(prefix) for prefix in prefixes)


# ------------------------------------------------------------------ jsonl io


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Rows of a JSONL file; a torn final line (killed mid-write) is skipped."""
    if not path.exists():
        return []
    rows = []
    for line in path.read_text().splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


class Appender:
    """Thread-safe line appender that flushes every line."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.stat().st_size and not path.read_bytes().endswith(b"\n"):
            with path.open("a") as handle:
                handle.write("\n")  # seal a torn line so the next row starts clean
        self._handle = path.open("a")
        self._lock = threading.Lock()

    def write(self, row: dict[str, Any]) -> None:
        with self._lock:
            self._handle.write(json.dumps(row, sort_keys=True) + "\n")
            self._handle.flush()

    def close(self) -> None:
        self._handle.close()


def _run(jobs: Sequence[Any], work: Callable[[Any], None], workers: int) -> None:
    if workers <= 1:
        for job in jobs:
            work(job)
        return
    with ThreadPoolExecutor(workers) as pool:
        list(pool.map(work, jobs))


# ------------------------------------------------------------------ commands


def generate(backend: Any, writer: str, data: Path = DATA, *, share: tuple[int, int] = (0, 1),
             banks: Optional[Sequence[str]] = None, max_requests: Optional[int] = None, workers: int = 1) -> int:
    """Run this share's pending requests; returns how many were written."""
    out = data / "raw" / f"{writer}.jsonl"
    done = {row["id"] for row in read_jsonl(out)}
    todo = [r for r in all_requests(data) if r["id"] not in done and in_share(r["id"], share) and _bank_match(r["bank"], banks)]
    todo = todo[:max_requests] if max_requests is not None else todo
    appender, written = Appender(out), []

    def work(request: dict[str, Any]) -> None:
        prompt = P.build_prompt(request["bank"], request["variant"], request["n"])
        params = {**GEN_PARAMS, "seed": _hash_int(request["id"])}
        started = time.time()
        try:
            text, tokens = backend.complete(prompt, **params)
        except Exception as error:  # one failed request must not stop the run; it stays pending
            print(f"FAILED {request['id']}: {error}", file=sys.stderr, flush=True)
            return
        seconds = round(time.time() - started, 2)
        appender.write({**request, "writer": writer, "prompt": prompt, "text": text, "params": params,
                        "seconds": seconds, "tokens": tokens, "ts": time.time()})
        written.append(request["id"])
        print(f"{request['id']}: {tokens} tokens in {seconds}s", flush=True)

    try:
        _run(todo, work, workers if getattr(backend, "threaded", False) else 1)
    finally:
        appender.close()
    return len(written)


def verify(data: Path = DATA) -> list[dict[str, Any]]:
    """Parse every raw file, check and dedup per bank, write candidates.jsonl; returns the rows."""
    parsed = []
    for path in sorted((data / "raw").glob("*.jsonl")):
        for record in read_jsonl(path):
            for line_index, text in enumerate(P.parse_generation(record["text"])):
                parsed.append({
                    "id": P.pattern_id(record["bank"], text), "bank": record["bank"], "text": text,
                    "writer": record["writer"], "request": record["id"], "line": line_index,
                    "style": record["variant"] if P.BANKS[record["bank"]].kind == "teacher" else None,
                    "flavour": None if P.BANKS[record["bank"]].kind == "teacher" else record["variant"],
                    "ts": record.get("ts", 0.0),
                })
    parsed.sort(key=lambda row: (row["ts"], row["writer"], row["request"], row["line"]))
    by_bank: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in parsed:
        row["reasons"] = P.check_pattern(row["bank"], row["text"])
        row["mechanical"] = not row["reasons"]
        by_bank[row["bank"]].append(row)
    for rows in by_bank.values():
        passing = [row for row in rows if not row["reasons"]]
        for row, match in zip(passing, P.dedup([row["text"] for row in passing])):
            if match is not None:
                original = passing[match]
                same = P.normalize(original["text"]) == P.normalize(row["text"])
                row["reasons"] = [f"{'duplicate' if same else 'near-duplicate'} of {original['id']}"]
    for row in parsed:
        row["ok"] = not row["reasons"]
    data.mkdir(parents=True, exist_ok=True)
    with (data / "candidates.jsonl").open("w") as handle:
        for row in parsed:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    return parsed


def report_verify(rows: Sequence[dict[str, Any]]) -> None:
    stats: dict[tuple[str, str], Counter] = defaultdict(Counter)
    reasons: Counter = Counter()
    for row in rows:
        stat = stats[(row["bank"], row["writer"])]
        stat["lines"] += 1
        stat["mechanical"] += row["mechanical"]
        stat["kept"] += row["ok"]
        for reason in row["reasons"]:
            reasons[reason.split(" of ")[0] if "duplicate of" in reason else reason.split("'")[0].strip()] += 1
    print(f"{'bank':22} {'writer':10} {'lines':>5} {'mech':>5} {'kept':>5}  pass")
    for (bank_id, writer), stat in sorted(stats.items()):
        rate = stat["mechanical"] / stat["lines"] if stat["lines"] else 0.0
        print(f"{bank_id:22} {writer:10} {stat['lines']:5d} {stat['mechanical']:5d} {stat['kept']:5d}  {rate:.0%}")
    total = sum(s["lines"] for s in stats.values())
    kept = sum(s["kept"] for s in stats.values())
    print(f"total lines {total}, kept {kept}" + (f" ({kept / total:.0%})" if total else ""))
    for reason, count in reasons.most_common(12):
        print(f"  {count:5d}  {reason}")


def _crosscheck_rows(data: Path) -> dict[str, list[dict[str, Any]]]:
    results: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for path in sorted((data / "crosscheck").glob("*.jsonl")):
        for row in read_jsonl(path):
            results[row["id"]].append(row)
    return results


def in_audit(item_id: str, fraction: Optional[float]) -> bool:
    """A fixed pseudo-random subset (the same for every run) used for independent audits."""
    return fraction is None or _hash_int("audit:" + item_id) % 10000 < fraction * 10000


def crosscheck(backend: Any, checker: str, data: Path = DATA, *, share: tuple[int, int] = (0, 1),
               banks: Optional[Sequence[str]] = None, max_items: Optional[int] = None, workers: int = 1,
               include_self: bool = False, sample: Optional[float] = None) -> int:
    """Check candidates; two instantiations, both must be answered yes.

    By default only other writers' candidates are checked. `include_self` also checks the checker's own
    (a fresh-context self-check); `sample` restricts to a fixed audit fraction of candidates.
    """
    out = data / "crosscheck" / f"{checker}.jsonl"
    done = {row["id"] for row in read_jsonl(out)}
    todo = [row for row in read_jsonl(data / "candidates.jsonl")
            if row["ok"] and (include_self or row["writer"] != checker.removesuffix("-frame")) and row["id"] not in done
            and (not checker.endswith("-frame") or row["bank"] in P.FRAME_BANKS)
            and in_share(row["id"], share) and _bank_match(row["bank"], banks) and in_audit(row["id"], sample)]
    todo = todo[:max_items] if max_items is not None else todo
    appender, written = Appender(out), []

    def work(row: dict[str, Any]) -> None:
        checks, answers = [], {}
        for values in P.crosscheck_values(row["bank"], row["id"]):
            frame = checker.endswith("-frame")
            prompt = (P.frame_prompt if frame else P.crosscheck_prompt)(row["bank"], row["text"], values)
            try:
                if prompt not in answers:
                    params = {**CHECK_PARAMS, "max_tokens": 200} if frame else CHECK_PARAMS
                    answers[prompt] = backend.complete(prompt, **params, seed=_hash_int(prompt))[0]
            except Exception as error:
                print(f"FAILED {row['id']}: {error}", file=sys.stderr, flush=True)
                return
            checks.append({"values": values, "sentence": P.render(row["text"], values),
                           "answer": answers[prompt],
                           "yes": (P.parse_last_yes_no if frame else P.parse_yes_no)(answers[prompt])})
            if frame:
                break  # the frame does not depend on the instantiation; one check is enough
        passed = all(check["yes"] for check in checks)
        appender.write({"id": row["id"], "bank": row["bank"], "text": row["text"], "writer": row["writer"],
                        "checker": checker, "checks": checks, "pass": passed, "ts": time.time()})
        written.append(row["id"])
        print(f"{row['id']} {'PASS' if passed else 'fail'}  {row['text']}", flush=True)

    try:
        _run(todo, work, workers if getattr(backend, "threaded", False) else 1)
    finally:
        appender.close()
    return len(written)


# 2026-09-18 audit: Bonsai said yes to 18% of instantiations and vetoed 26/63 Qwen-accepted patterns;
# a manual read found about 22 of the first 25 vetoes were fine sentences, so its audit is advisory only.
ADVISORY_CHECKERS = frozenset({"bonsai"})


def _effective(checks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """A "<name>-frame" check replaces the same checker's whole-line check (see patterns.frame_prompt)."""
    framed = {r["checker"].removesuffix("-frame") for r in checks if r["checker"].endswith("-frame")}
    return [r for r in checks if r["checker"].endswith("-frame") or r["checker"] not in framed]


def accepted_candidates(data: Path) -> tuple[list[dict[str, Any]], int]:
    """(accepted rows, count still awaiting a check).

    A candidate is accepted when at least one checker has checked it and every check on it passed
    (a writer's fresh-context self-check counts; an independent audit can only veto).
    Checkers in ADVISORY_CHECKERS are reported by `status` but never veto.
    """
    results = {key: _effective([r for r in rows if r["checker"] not in ADVISORY_CHECKERS])
               for key, rows in _crosscheck_rows(data).items()}
    accepted, pending = [], 0
    for row in read_jsonl(data / "candidates.jsonl"):
        if not row["ok"]:
            continue
        checks = results.get(row["id"], ())
        if not checks:
            pending += 1
        elif all(r["pass"] for r in checks):
            accepted.append(row)
    return accepted, pending


def _counts(accepted: Iterable[dict[str, Any]]) -> tuple[Counter, Counter]:
    per_bank, per_style = Counter(), Counter()
    for row in accepted:
        per_bank[row["bank"]] += 1
        if row.get("style"):
            per_style[(row["bank"], row["style"])] += 1
    return per_bank, per_style


def shortfalls(accepted: Iterable[dict[str, Any]]) -> dict[str, int]:
    per_bank, per_style = _counts(accepted)
    missing = {}
    for bank_id, bank in P.BANKS.items():
        if bank.kind == "teacher":
            for style in P.STYLES:
                if per_style[(bank_id, style)] < bank.target:
                    missing[f"{bank_id}/{style}"] = bank.target - per_style[(bank_id, style)]
        elif per_bank[bank_id] < bank.target:
            missing[bank_id] = bank.target - per_bank[bank_id]
    return missing


def finalize(data: Path = DATA, *, show: int = 3) -> dict[str, Any]:
    """Write bank-v1.json from accepted patterns and print counts, shortfalls and examples."""
    accepted, pending = accepted_candidates(data)
    manifest, banks = P.assign_splits(accepted)
    dropped = _drop_shared_frames(banks)
    per_bank, _ = _counts(accepted)
    counts = {
        bank_id: {"target": P.bank_target(bank_id), "accepted": per_bank[bank_id],
                  **{split: len(rows) for split, rows in banks[bank_id].items()}}
        for bank_id in P.BANKS
    }
    out = {
        "version": P.MANIFEST_VERSION, "manifest_digest": manifest.digest(), "manifest": manifest.payload(),
        "banks": banks, "counts": counts, "shortfalls": shortfalls(accepted), "pending_crosscheck": pending,
    }
    data.mkdir(parents=True, exist_ok=True)
    (data / "bank-v1.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    rng = random.Random(0)
    for bank_id, count in counts.items():
        print(f"{bank_id:22} {count['accepted']:4d}/{count['target']:<4d} "
              f"train {count['train']:3d} val {count['validation']:3d} test {count['test']:3d}")
        rows = [row for split in banks[bank_id].values() for row in split]
        for row in rng.sample(rows, min(show, len(rows))):
            print(f"    {row['text']}")
    print(f"dropped {len(dropped)} train teacher frames that a held-out frame would match")
    print(f"shortfalls: {len(out['shortfalls'])} banks/styles below target; pending cross-check: {pending}")
    print(f"manifest {P.MANIFEST_VERSION} digest {out['manifest_digest']}")
    return out


def _frame_words(text: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """A teacher line's words before and after its one slot (all words, empty after, for a slot-free line)."""
    before, _, after = text.partition("{")
    after = after.partition("}")[2] if after else ""
    words = lambda part: tuple(re.findall(r"[^\W_]+", part.casefold()))
    return words(before), (words(after) if "{" in text else ("\0",))


def _frames_overlap(a: str, b: str) -> bool:
    """Whether some line could match both teacher frames (the slot stands for any words)."""
    (a1, a2), (b1, b2) = _frame_words(a), _frame_words(b)
    if a2 == ("\0",) or b2 == ("\0",):
        return (a1, a2) == (b1, b2)
    prefix = a1[:len(b1)] == b1 or b1[:len(a1)] == a1
    suffix = a2[len(a2) - len(b2):] == b2 if len(a2) >= len(b2) else b2[len(b2) - len(a2):] == a2
    return prefix and suffix


def _drop_shared_frames(banks: dict[str, dict[str, list[dict[str, Any]]]]) -> list[str]:
    """Teacher frames are split by style, so the same frame can land in train under one style or bank and in a
    held-out split under another; the held-out audit then sees a train template in held-out text. Drop the train copy."""
    teacher = [b for b, bank in P.BANKS.items() if bank.kind == "teacher"]
    held = [row["text"] for b in teacher for split in ("validation", "test") for row in banks[b].get(split, [])]
    dropped = []
    for b in teacher:
        keep = []
        for row in banks[b].get("train", []):
            (dropped if any(_frames_overlap(row["text"], h) for h in held) else keep).append(row)
        banks[b]["train"] = keep
    dropped_ids = [row["id"] for row in dropped]
    return dropped_ids


def topup(data: Path = DATA) -> list[dict[str, Any]]:
    """Append extra requests for banks (teacher: bank/style) below target, sized by the observed yield."""
    accepted, pending = accepted_candidates(data)
    if pending:
        print(f"note: {pending} candidates still await cross-check; they are not counted", file=sys.stderr)
    lines = Counter(row["bank"] for row in read_jsonl(data / "candidates.jsonl"))
    per_bank, _ = _counts(accepted)
    existing = read_jsonl(data / "requests-topup.jsonl")
    round_id = 1 + max((int(r["id"].rsplit(":", 1)[1].split(".")[0][1:]) for r in existing), default=0)
    new = []
    for group, missing in shortfalls(accepted).items():
        bank_id, _, style = group.partition("/")
        rate = max(per_bank[bank_id] / lines[bank_id], 0.1) if lines[bank_id] else 0.3
        count = min(math.ceil(missing / rate / P.PER_REQUEST), 20)
        variants = (style,) if style else _variants(bank_id)
        for k in range(count):
            variant = variants[k % len(variants)]
            new.append({"id": f"{bank_id}:{variant}:u{round_id}.{k}", "bank": bank_id, "variant": variant, "n": P.PER_REQUEST})
    if new:
        appender = Appender(data / "requests-topup.jsonl")
        for row in new:
            appender.write(row)
        appender.close()
    print(f"topup round {round_id}: {len(new)} requests for {len({r['bank'] for r in new})} banks")
    return new


def audit_report(data: Path = DATA) -> dict[str, Any]:
    """Where a writer's self-check passed a pattern, how often did an independent checker reject it?"""
    by_kind: dict[str, Counter] = defaultdict(Counter)
    vetoed = []
    for rows in _crosscheck_rows(data).values():
        own = [r for r in rows if r["checker"] == r["writer"]]
        other = [r for r in rows if r["checker"] != r["writer"]]
        if own and other and all(r["pass"] for r in own):
            kind = P.BANKS[rows[0]["bank"]].kind
            by_kind[kind]["audited"] += 1
            if not all(r["pass"] for r in other):
                by_kind[kind]["vetoed"] += 1
                vetoed.append(rows[0]["text"])
    for kind, counts in sorted(by_kind.items()):
        print(f"  audit {kind:10} {counts['vetoed']}/{counts['audited']} self-accepted patterns vetoed by the independent checker")
    return {"by_kind": {k: dict(v) for k, v in by_kind.items()}, "vetoed": vetoed}


def status(data: Path = DATA) -> None:
    requests = all_requests(data)
    print(f"requests planned: {len(requests)}")
    for path in sorted((data / "raw").glob("*.jsonl")):
        rows = read_jsonl(path)
        print(f"  writer {path.stem}: {len(rows)} requests done, {sum(r.get('tokens', 0) for r in rows)} tokens, "
              f"{sum(r.get('seconds', 0) for r in rows) / 3600:.2f} h")
    for path in sorted((data / "crosscheck").glob("*.jsonl")):
        rows = read_jsonl(path)
        print(f"  checker {path.stem}: {len(rows)} checked, {sum(r['pass'] for r in rows)} passed")
    audit_report(data)
    if (data / "candidates.jsonl").exists():
        accepted, pending = accepted_candidates(data)
        per_bank, _ = _counts(accepted)
        print(f"accepted {len(accepted)}, pending cross-check {pending}")
        for bank_id in P.BANKS:
            print(f"  {bank_id:22} {per_bank[bank_id]:4d}/{P.bank_target(bank_id)}")


def print_plan() -> None:
    requests = plan()
    per_bank = Counter(r["bank"] for r in requests)
    for bank_id, count in per_bank.items():
        print(f"{bank_id:22} {count:3d} requests  {count * P.PER_REQUEST:5d} patterns  target {P.bank_target(bank_id)}")
    print(f"total {len(requests)} requests, {len(requests) * P.PER_REQUEST} patterns asked")


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data", type=Path, default=DATA, help="pattern data directory")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("plan")
    for name in ("generate", "crosscheck"):
        command = commands.add_parser(name)
        command.add_argument("--backend", choices=("llama", "mlx"), required=True)
        command.add_argument("--writer" if name == "generate" else "--checker", dest="name", required=True)
        command.add_argument("--url", default=LLAMA_URL)
        command.add_argument("--workers", type=int, default=1)
        command.add_argument("--share", type=parse_share, default=(0, 1))
        command.add_argument("--banks", nargs="+")
        command.add_argument("--max-requests" if name == "generate" else "--max-items", dest="limit", type=int)
        if name == "crosscheck":
            command.add_argument("--include-self", action="store_true", help="also check the checker's own candidates")
            command.add_argument("--sample", type=float, help="only a fixed audit fraction of candidates, e.g. 0.12")
    for name in ("verify", "finalize", "topup", "status"):
        commands.add_parser(name)
    args = parser.parse_args(argv)
    if args.command == "plan":
        print_plan()
    elif args.command == "generate":
        count = generate(make_backend(args), args.name, args.data, share=args.share, banks=args.banks,
                         max_requests=args.limit, workers=args.workers)
        print(f"wrote {count} requests")
    elif args.command == "crosscheck":
        count = crosscheck(make_backend(args), args.name, args.data, share=args.share, banks=args.banks,
                           max_items=args.limit, workers=args.workers, include_self=args.include_self, sample=args.sample)
        print(f"checked {count} candidates")
    elif args.command == "verify":
        report_verify(verify(args.data))
    elif args.command == "finalize":
        finalize(args.data)
    elif args.command == "topup":
        topup(args.data)
    else:
        status(args.data)


if __name__ == "__main__":
    main()
