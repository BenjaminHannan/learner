#!/usr/bin/env python3
"""sha256 of a file with CRLF turned into LF, plus its size and line count (RUNBOOK.md section 7, item 5: the PC writes pool files with Windows line endings).

  python lf_sha256.py WORK\\g8a\\pools\\p10-rung30-s400-a64-L\\train.jsonl

Prints:  <sha256 after CRLF to LF>  <bytes as stored>  <bytes after CRLF to LF>  <lines>  <path>
For the box's pool (LF) the first number is the pool's own train_sha256; on the PC the stored size should be the LF size plus the number of lines when every line ends in CRLF.
Standard library only; reads the file in 64 MB pieces, writes nothing.
"""
import hashlib
import sys

path = sys.argv[1]
h = hashlib.sha256()
raw = lf = lines = 0
carry = b''
with open(path, 'rb') as f:
    while True:
        b = f.read(64 * 1024 * 1024)
        if not b:
            break
        raw += len(b)
        b = carry + b
        carry = b'\r' if b.endswith(b'\r') else b''      # a CR at the end of a piece may belong to a CRLF that continues in the next one
        if carry:
            b = b[:-1]
        b = b.replace(b'\r\n', b'\n')
        h.update(b)
        lf += len(b)
        lines += b.count(b'\n')
if carry:
    h.update(carry)
    lf += 1
print(h.hexdigest(), raw, lf, lines, path)
