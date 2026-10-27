#!/usr/bin/env python3
"""rd-378g: which Codex setting lets GPT-6 Luna write one practice batch in time? (Trustworthy notes thread,
2026-09-27; rd-378g addendum J). New file.

007-rd378g-writeluna's pilot failed on time: 9 of 9 attempts timed out at the helper's 300 s. This sends batch 18's
exact WRITE prompt (claude_rd378g_teacher.WRITE, area and speaker letters as claude_rd378g_writemore_oc.one_batch builds
them) once per setting, the settings in parallel, one attempt each, through claude_luna_effort's run line plus --json
(Codex's JSONL event stream). For each setting it prints counts only, never text: exit code, wall seconds, event counts
by type, token usage numbers, reply length, whether the reply is error-like, whether it parses as a list, check_batch's
verdict, and repeats of first turns already in --have. Nothing it writes is kept.

python -B scripts/claude_rd378g_lunadiag.py run --have glm/notes_w1.jsonl --settings low:600,default:1200
python -B scripts/claude_rd378g_lunadiag.py selftest   (no network)
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_luna_effort as E  # noqa: E402
import claude_rd378g_teacher as G  # noqa: E402

BATCH = 18


def prompt(b=BATCH):
    letters = ", ".join(G.LETTERS[(3 * b + j) % len(G.LETTERS)] for j in range(3))
    return G.WRITE.replace("{area}", G.AREAS[b]).replace("{letters}", letters)


def events(stdout):
    kinds, usage = {}, {}
    for line in stdout.splitlines():
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if not isinstance(ev, dict):
            continue
        k = str(ev.get("type") or (ev.get("msg") or {}).get("type") or "?")
        item = ev.get("item") if isinstance(ev.get("item"), dict) else None
        if item and item.get("type"):
            k += ":" + str(item["type"])
        kinds[k] = kinds.get(k, 0) + 1
        for src in (ev.get("usage"), (ev.get("msg") or {}).get("usage") if isinstance(ev.get("msg"), dict) else None):
            if isinstance(src, dict):
                for uk, uv in src.items():
                    if isinstance(uv, (int, float)):
                        usage[uk] = usage.get(uk, 0) + uv
    return kinds, usage


def one(text, effort, timeout, seen, runner=subprocess.run):
    rep = {"effort": effort or "default", "timeout_s": timeout}
    with tempfile.TemporaryDirectory(prefix="luna-diag-") as td:
        out_file = os.path.join(td, ".last.txt")
        t0 = time.time()
        try:
            p = runner(E.args_for(td, out_file, E.MODEL, effort, extra=["--json"]), input=text.encode("utf-8"),
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=td, timeout=timeout)
            rep["exit"] = p.returncode
            stdout = p.stdout.decode("utf-8", "replace")
        except subprocess.TimeoutExpired as e:
            rep["exit"] = "timeout"
            stdout = (e.stdout or b"").decode("utf-8", "replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
        rep["wall_s"] = round(time.time() - t0, 1)
        rep["event_counts"], rep["usage"] = events(stdout)
        reply = ""
        if os.path.exists(out_file):
            with open(out_file, encoding="utf-8", errors="replace") as f:
                reply = f.read().strip()
    rows = G.json_list(reply) if reply else None
    bad = G.check_batch(rows) if reply else "no reply"
    firsts = set() if bad else {r["turns"][0]["text"].strip().lower() for r in rows}
    rep.update({"reply_chars": len(reply), "error_like": E.L.looks_like_error(reply),
                "parsed_items": len(rows) if isinstance(rows, list) else None,
                "check_batch": bad or "ok", "repeats": len(firsts & seen)})
    rep["pass"] = rep["exit"] == 0 and not rep["error_like"] and bad is None and rep["repeats"] == 0
    return rep


def run(a, runner=subprocess.run):
    have = [json.loads(x) for x in Path(a.have).read_text(encoding="utf-8").splitlines() if x.strip()]
    seen = {x["turns"][0]["text"].strip().lower() for x in have}
    text = prompt()
    settings = []
    for s in a.settings.split(","):
        eff, _, t = s.partition(":")
        settings.append((None if eff == "default" else eff, int(t)))
    out = [None] * len(settings)

    def go(i, eff, t):
        out[i] = one(text, eff, t, seen, runner)
    th = [threading.Thread(target=go, args=(i, eff, t)) for i, (eff, t) in enumerate(settings)]
    for x in th:
        x.start()
    for x in th:
        x.join()
    for r in out:
        print(json.dumps(r))
    return out


def selftest():
    good = json.dumps([{"kind": k, "speakers": sp, "date": "8 May 2023",
                        "turns": [{"speaker": sp[j % 2], "text": "ok" if j else f"we got a dog last May {k} {i}",
                                   "notes": ([{"text": "The user got a dog.", "cites": [0], "when": "last May"}]
                                             if j == 0 else [])} for j in range(12)]}
                       for k, sp in (("chat", ["user", "assistant"]), ("overheard", ["Wren", "Tobin"]))
                       for i in range(3)])

    class P:
        def __init__(self, rc, out):
            self.returncode, self.stdout, self.stderr = rc, out, b""

    def runner(args, input=None, stdout=None, stderr=None, cwd=None, timeout=None, **kw):
        if args[1:3] == ["exec", "--help"]:
            return P(0, b"--output-last-message")
        if "-c" in args:
            raise subprocess.TimeoutExpired(args, timeout, output=b'{"type":"turn.started"}\n')
        Path(args[args.index("--output-last-message") + 1]).write_text(good)
        return P(0, b'{"type":"item.completed","item":{"type":"agent_message"}}\n'
                    b'{"type":"turn.completed","usage":{"input_tokens":10,"output_tokens":20}}\n')
    real = subprocess.run
    subprocess.run = runner
    E.L._HAS_O = None
    try:
        with tempfile.TemporaryDirectory() as d:
            h = Path(d) / "have.jsonl"
            h.write_text(json.dumps({"dialog": "kg-001", "turns": [{"text": "hi"}]}) + "\n")
            r = run(argparse.Namespace(have=str(h), settings="low:5,default:9"), runner=runner)
    finally:
        subprocess.run = real
        E.L._HAS_O = None
    ok = (r[0]["exit"] == "timeout" and r[0]["pass"] is False and r[0]["event_counts"] == {"turn.started": 1}
          and r[1]["exit"] == 0 and r[1]["check_batch"] == "ok" and r[1]["pass"] is True
          and r[1]["usage"] == {"input_tokens": 10, "output_tokens": 20}
          and r[1]["event_counts"] == {"item.completed:agent_message": 1, "turn.completed": 1}
          and "{area}" not in prompt() and "{letters}" not in prompt())
    print("rd378g lunadiag selftest " + ("1/1 ok" if ok else "FAIL"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["run", "selftest"])
    ap.add_argument("--have", default="")
    ap.add_argument("--settings", default="low:600,default:1200")
    a = ap.parse_args()
    if a.mode == "selftest":
        sys.exit(selftest())
    run(a)


if __name__ == "__main__":
    main()
