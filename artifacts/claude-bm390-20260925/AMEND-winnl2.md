# bm-390 amendment 2: the fixed Windows line-ending wrapper (benchmarks thread, 2026-09-25, registered before any run on real items)

Updates AMEND-winnl.md. The sealed files (SEAL-code.sha256.txt, 8 lines; the 336b seal, 229 lines) are unchanged.
Nothing about the marks, arms, data, prompts or scoring changes. AMEND-winnl.md's "Clarification" (0.1's chat and
creative replies are sampled, so P is one draw) still stands.

## What happened
Attempt 2 on BensPC (RESULTS-benspc2.md on builder-outbox) stopped at its smoke test, before any model loaded, with
`TypeError: argument of type 'WindowsPath' is not iterable` inside scripts/claude_winnl_wrap.py. My bug: version 1
installed a plain Python function as open. Python 3.10's pathlib (BensPC runs 3.10.9) stores open as a class
attribute when it is first imported (`_NormalAccessor.open = io.open`). A stored builtin stays unbound; a stored
Python function binds as a method, so every Path.open call passed the Path as the mode. My Linux test missed it for
two reasons: it ran Python 3.11, and it imported pathlib before installing the wrapper.

## The one difference now
Every bm-390 command on BensPC starts with `python -B scripts/claude_winnl2_wrap.py` (claude_winnl_wrap.py is no
longer used). Version 2 installs open as an instance of a small class with `__call__`. An instance is not a
descriptor, so it is never bound as a method, wherever it is stored. Its behaviour is version 1's: on Windows only,
a text-mode open for writing that does not choose a newline gets newline="" (Linux bytes); reads, binary opens and
explicit newlines are untouched; off Windows nothing changes. It applies to every arm.

## Evidence (Linux, Windows line endings simulated by scripts/claude_winnl2_test.py; pathlib first imported after
the wrapper, as in a fresh BensPC process)
Binding test, Python 3.10.20 (`binding`; each row is a fresh process; the same test on 3.11.15 also prints
WINNL2-BINDING PASS):
```
sim, no fix | {"python": "3.10.20", "pathlib_loaded_before_fix": false, "sim": true, "fix": "none", "ok": true, "crlf": 3, "text_ok": true, "metadata_ok": true}
sim, version 1 | {"python": "3.10.20", "pathlib_loaded_before_fix": false, "sim": true, "fix": "1", "ok": false, "error": "TypeError: argument of type 'PosixPath' is not iterable"}
sim, version 2 | {"python": "3.10.20", "pathlib_loaded_before_fix": false, "sim": true, "fix": "2", "ok": true, "crlf": 0, "text_ok": true, "metadata_ok": true}
plain | {"python": "3.10.20", "pathlib_loaded_before_fix": false, "sim": false, "fix": "none", "ok": true, "crlf": 0, "text_ok": true, "metadata_ok": true}
PASS pathlib not imported before the fix (BensPC order)
PASS the simulation writes \r\n
PASS version 1 fails like BensPC (TypeError from a stored open)
PASS version 2 passes, 0 \r\n
PASS plain run passes, 0 \r\n
WINNL2-BINDING (3.10.20) PASS
```
Version 1 fails here with the same TypeError as BensPC (PosixPath instead of WindowsPath), so this test
would have caught attempt 2's bug.

Unit test on the sealed turn log and notebook, Python 3.10.20 (3.11.15 also prints WINNL2-UNIT PASS):
```
{"sim_windows": true, "fix": false, "turnlog": "TurnLog323Corrupt: turnlog323: read-back mismatch", "notebook": "LogCorrupt: read-back mismatch", "files": 2, "crlf_in_files": 2}
{"sim_windows": true, "fix": true, "turnlog": "ok lines=2 torn=False", "notebook": "ok events=2 torn=False", "files": 2, "crlf_in_files": 0}
{"sim_windows": false, "fix": false, "turnlog": "ok lines=2 torn=False", "notebook": "ok events=2 torn=False", "files": 2, "crlf_in_files": 0}
PASS without the fix, simulated Windows fails like BensPC
PASS with version 2, simulated Windows passes
PASS plain Linux passes
PASS file bytes with version 2 equal plain Linux bytes
PASS the wrapper changes nothing off Windows
WINNL2-UNIT (3.10.20) PASS
```

Full registered smoke commands on the made-up smoke chat, Python 3.10.20 venv (torch 2.14.0, transformers 5.17.0,
CPU, stand-in reader = the base 1B), simulated Windows with version 2 installed before pathlib is imported:

| Command | Exit | Result |
|---|---|---|
| T smoke (plain arm) | 0 | wrote locomo_T.jsonl rows=5; 0 "\r\n" in its files; 238 s |
| P smoke (agent arm, sleepcheck wrapper, --also-bare) | 0 | wrote locomo_P.jsonl rows=5 bare=5; sleep log 2 rows, both checkpoint_exists true (0 attempted learning, as in every smoke: fewer than 8 word episodes); 0 "\r\n"; 830 s |

The reading row and all 5 question-only (P_bare) replies equal the plain Linux 3.11 control run from AMEND-winnl.md.

## Checks on BensPC (handoff task 001-bench-bm390x)
Before any model loads, a probe runs twice on BensPC itself: without the wrapper it must show "\r\n" (real Windows
translation), with it 0 "\r\n" and no error (pathlib, open and package metadata, where attempt 2 broke). Then the
registered smoke must pass with 0 "\r\n" in its files before any real item runs.
