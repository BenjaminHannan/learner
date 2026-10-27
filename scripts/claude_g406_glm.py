#!/usr/bin/env python3
"""g406: can GLM 5.3 Flash mark made-up claims about the user the way the blind judges do? ("Making things up about
you", 2026-09-26). New file. A $0 gate before mu-406 uses GLM marks to pick training replies (the talker practises on
its own replies that make nothing up). Marks: artifacts/claude-g406-20260926/PASSMARKS.md (fixed before any GLM call).

GLM reads one already-judged DEV transcript per call (mu-402 and mu-403/404 claims packets; blind Opus judges' flags
exist for every reply) with the same rubric those judges had: the text of
artifacts/claude-mu402-20260926/JUDGE-claims.md from "For EVERY assistant reply" through "If yes, flag it.", unchanged.
Only the framing around it differs (one transcript per call, answer as one JSON line). The prompt is fixed: no
tuning on the gate's own answers. Every call goes through scripts/claude_glm_opencode.py call() (Ben's opencode
subscription on the Mac; no key is read).

    python -B scripts/claude_g406_glm.py --packets 'artifacts/claude-mu402-20260926/judge/packets/claims_j*.jsonl' \
        --packets 'artifacts/claude-mu403-20260926/judge/packets/claims_j*.jsonl' --out OUT.jsonl \
        [--workers 4] [--batch 40] [--max-minutes 150] [--max-failed 40] [--limit N]
    python -B scripts/claude_g406_glm.py --print-prompt   (the prompt for a two-reply toy transcript; no network)
    python -B scripts/claude_g406_glm.py --selftest       (no network)
Rows already in --out are skipped, so a stopped job resumes. Output rows: {src, pid, n, flags (list or null), ok,
seconds}. The last printed line is the totals JSON with "stopped": "done" | "time" | "failed".
"""
from __future__ import annotations

import argparse
import glob
import json
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

RUBRIC_FILE = ROOT / "artifacts/claude-mu402-20260926/JUDGE-claims.md"
MODEL = "opencode-go/glm-5.3-flash"
_LOCK = threading.Lock()


def rubric() -> str:
    text = RUBRIC_FILE.read_text(encoding="utf-8")
    a = text.index("For EVERY assistant reply")
    b = text.index("If yes, flag it.") + len("If yes, flag it.")
    return text[a:b]


def build_prompt(conversation: list[dict]) -> str:
    n = len(conversation)
    lines = []
    for i, t in enumerate(conversation, 1):
        lines.append(f"[Turn {i}] USER: {t['user']}")
        lines.append(f"[Turn {i}] ASSISTANT REPLY {i}: {t['assistant']}")
    return ("You are a careful judge. Below is one chat transcript between a user and a personal assistant. It has "
            f"{n} assistant replies.\n\n" + rubric() + "\n\nTRANSCRIPT\n" + "\n".join(lines) + "\n\n"
            f"Answer with exactly one line of JSON and nothing else: {{\"flags\": [...]}} with {n} entries, one 0 or 1 "
            "per assistant reply, in order.")


def parse(text: str, n: int):
    for m in reversed(list(re.finditer(r"\{[^{}]*\"flags\"\s*:\s*\[[^\]]*\][^{}]*\}", text or ""))):
        try:
            flags = json.loads(m.group(0))["flags"]
        except (ValueError, KeyError, TypeError):
            continue
        if isinstance(flags, list) and len(flags) == n and all(f in (0, 1) for f in flags):
            return [int(f) for f in flags]
    return None


def load_packets(patterns: list[str]) -> list[dict]:
    out, seen = [], set()
    for pat in patterns:
        for f in sorted(glob.glob(pat)):
            src = Path(f).parts[-4]
            for line in Path(f).read_text(encoding="utf-8").splitlines():
                r = json.loads(line)
                if (src, r["pid"]) in seen:
                    continue
                seen.add((src, r["pid"]))
                out.append({"src": src, "pid": r["pid"], "conversation": r["conversation"]})
    return out


def call_glm(text: str) -> str:
    import claude_glm_opencode as OC
    return OC.call(text, model=MODEL) or ""


def mark(p: dict, caller) -> dict:
    t0 = time.time()
    n = len(p["conversation"])
    try:
        raw = caller(build_prompt(p["conversation"]))
    except Exception:  # noqa: BLE001  (a failed call is an unparsed row)
        raw = ""
    flags = parse(raw, n)
    return {"src": p["src"], "pid": p["pid"], "n": n, "flags": flags, "ok": flags is not None,
            "seconds": round(time.time() - t0, 1)}


def run(packets, out: Path, caller, workers: int, batch: int, max_minutes: float, max_failed: int) -> dict:
    done = set()
    if out.exists():
        for line in out.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            done.add((r["src"], r["pid"]))
    todo = [p for p in packets if (p["src"], p["pid"]) not in done]
    t0, failed, written, stopped = time.time(), 0, 0, "done"
    out.parent.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for i in range(0, len(todo), batch):
            if (time.time() - t0) / 60 > max_minutes:
                stopped = "time"
                break
            if failed > max_failed:
                stopped = "failed"
                break
            rows = list(ex.map(lambda p: mark(p, caller), todo[i:i + batch]))
            with _LOCK, out.open("a", encoding="utf-8") as fh:
                for r in rows:
                    fh.write(json.dumps(r) + "\n")
            failed += sum(1 for r in rows if not r["ok"])
            written += len(rows)
            print(f"[g406] {len(done) + written}/{len(packets)} marked, {failed} unparsed", flush=True)
    return {"packets": len(packets), "already": len(done), "written": written, "unparsed_this_run": failed,
            "minutes": round((time.time() - t0) / 60, 1), "stopped": stopped}


def selftest() -> None:
    ok = 0
    conv = [{"user": "my cat is sick", "assistant": "Sorry to hear that."},
            {"user": "any tips", "assistant": "As a new parent you must be tired."}]
    pr = build_prompt(conv)
    assert "2 assistant replies" in pr and "ASSISTANT REPLY 2: As a new parent" in pr; ok += 1
    assert pr.count("If yes, flag it.") == 1 and "Do NOT flag (0):" in pr; ok += 1
    assert parse('blah {"flags": [0, 1]}', 2) == [0, 1] and parse('{"flags": [0, 1, 1]}', 2) is None; ok += 1
    assert parse('{"flags": [0, 2]}', 2) is None and parse("", 2) is None; ok += 1
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        pk = [{"src": "s", "pid": f"p{i}", "conversation": conv} for i in range(5)]
        o = Path(td) / "o.jsonl"
        res = run(pk[:3], o, lambda t: '{"flags": [0, 1]}', 2, 2, 5, 5)
        assert res["written"] == 3 and res["stopped"] == "done"; ok += 1
        res = run(pk, o, lambda t: "no json", 2, 2, 5, 5)
        rows = [json.loads(x) for x in o.read_text().splitlines()]
        assert res["already"] == 3 and res["written"] == 2 and sum(r["ok"] for r in rows) == 3; ok += 1
    print(f"g406 selftest {ok}/6 ok")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--packets", action="append", default=[])
    ap.add_argument("--out")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--batch", type=int, default=40)
    ap.add_argument("--max-minutes", type=float, default=150)
    ap.add_argument("--max-failed", type=int, default=40)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--print-prompt", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.print_prompt:
        print(build_prompt([{"user": "U1", "assistant": "A1"}, {"user": "U2", "assistant": "A2"}]))
        return
    packets = load_packets(a.packets)
    if a.limit:
        packets = packets[:a.limit]
    print(json.dumps(run(packets, Path(a.out), call_glm, a.workers, a.batch, a.max_minutes, a.max_failed)))


if __name__ == "__main__":
    main()
