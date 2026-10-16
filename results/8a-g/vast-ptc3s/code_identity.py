#!/usr/bin/env python3
"""Code identity of a custom_io tree, the same on Windows and Linux (RUNBOOK.md, "Is it the same code as the PC job?").

  python code_identity.py FOLDER            prints CODE-HASH-LF <10 hex> and FILES-LIST-SHA256 <64 hex> (<n> files)
  python code_identity.py FOLDER files      prints one line per file: <sha256 of the file with CRLF turned into LF>  custom_io/<path>
  python code_identity.py FOLDER hash       prints the 10 hex alone

FOLDER is the frozen copy that holds the custom_io folder: on the PC WORK\\code\\8aPTC3S-pc-<10 hex>, on the box $J/work/code/8aPTC3S-pc-<10 hex> (the box script
runs this very file and keeps the output in RUN/box/code_files_lf.sha256 and code_hash_lf.txt). Standard library only; reads files, writes nothing.

Why not local_runner.code_hash(): it hashes the raw bytes (a Windows checkout with CRLF line endings gives another hash for the same code) and it sorts
pathlib paths (Windows ignores upper/lower case there, Linux does not). Here both are fixed: CRLF counts as LF, and paths are sorted as plain text.
The hash line uses local_runner's formula otherwise: sha1 over `path NUL bytes NUL` for every .py / .json file outside results/ and __pycache__, first 10 hex.
The list covers .py, .json and .txt files (the .txt files hold the queue files).
"""
import hashlib
import pathlib
import sys


def entries(folder):
    root = pathlib.Path(folder)
    out = []
    for f in root.joinpath('custom_io').rglob('*'):
        rel = f.relative_to(root).as_posix()
        if f.is_file() and f.suffix in ('.py', '.json', '.txt') and '__pycache__' not in rel and not rel.startswith('custom_io/results/'):
            out.append((rel, f.read_bytes().replace(b'\r\n', b'\n'), f.suffix))
    return sorted(out, key=lambda e: e[0])


def file_lines(es):
    return ['%s  %s' % (hashlib.sha256(b).hexdigest(), rel) for rel, b, _ in es]


def code_hash(es):
    h = hashlib.sha1()
    for rel, b, suf in es:
        if suf in ('.py', '.json'):
            h.update(rel.encode() + b'\0' + b + b'\0')
    return h.hexdigest()[:10]


if __name__ == '__main__':
    es = entries(sys.argv[1])
    mode = sys.argv[2] if len(sys.argv) > 2 else 'both'
    if mode == 'files':
        print('\n'.join(file_lines(es)))
    elif mode == 'hash':
        print(code_hash(es))
    else:
        print('CODE-HASH-LF', code_hash(es))
        print('FILES-LIST-SHA256', hashlib.sha256(('\n'.join(file_lines(es)) + '\n').encode()).hexdigest(), '(%d files)' % len(es))
