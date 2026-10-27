#!/usr/bin/env python3
"""Scan files (paths from stdin, NUL- or newline-separated) for likely secrets.
Prints only file:line and the pattern NAME, never the matched text."""
import re, sys, os

PATS = {
    "openai-like key": re.compile(rb"\bsk-[A-Za-z0-9_\-]{20,}"),
    "anthropic key": re.compile(rb"sk-ant-[A-Za-z0-9_\-]{10,}"),
    "github token": re.compile(rb"\bgh[pousr]_[A-Za-z0-9]{30,}"),
    "aws key id": re.compile(rb"\bAKIA[0-9A-Z]{16}\b"),
    "slack token": re.compile(rb"\bxox[baprs]-[A-Za-z0-9\-]{10,}"),
    "private key block": re.compile(rb"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "bearer literal": re.compile(rb"Bearer\s+[A-Za-z0-9_\-\.=]{24,}"),
    "hf token": re.compile(rb"\bhf_[A-Za-z0-9]{30,}"),
    "google api key": re.compile(rb"\bAIza[0-9A-Za-z_\-]{35}\b"),
    "assigned secret": re.compile(rb"(?i)\b(api[_-]?key|secret|password|passwd|auth[_-]?token|access[_-]?token)\b\s*[:=]\s*[\"'][^\"'\s$]{12,}[\"']"),
}
data = sys.stdin.buffer.read()
paths = [p for p in re.split(rb"[\0\n]", data) if p]
hits = 0
for p in paths:
    p = p.decode()
    try:
        if os.path.getsize(p) > 20_000_000:
            continue
        b = open(p, "rb").read()
    except Exception:
        continue
    for name, rx in PATS.items():
        for m in rx.finditer(b):
            line = b.count(b"\n", 0, m.start()) + 1
            print(f"{p}:{line}: {name}")
            hits += 1
print(f"SCANNED {len(paths)} files, {hits} hits", file=sys.stderr)
