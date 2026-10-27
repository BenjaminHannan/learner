# Exp 223 RESULTS — negated capability questions pass the screen (Muse)

One change on loop138i (`scripts/fable_loop223_agent.py`, subclass only):
a "?" turn the 148 screen would stop skips the screen iff the base's own
`route127` intent is C24/C25 AND the turn has a second-person word
(you/your/yours/yourself). No router widening, no new reply text.

## Marks (integer counts, every case reported)

| mark | bar | got | verdict |
|---|---|---|---|
| M1 A-cases exact/identical, 0 writes | 22/22 | 22/22 (19 C25 CANNOT sheets + A09/A11/A12 DECLINE byte-identical), writes 0 | PASS |
| M2 B+C byte-identical reply + stored facts | 54/54 | 54/54 | PASS |
| M3 suitediff vs 138i rt136/rt143/sessions152/bench | 0 moves | 0/0/0/0 (detail moved lists empty; bench splits 187/9/4, 195/5/0, 149/51/0, 191/9/0) | PASS |
| M4 sleepsmoke206 same marks as 138i | identical | sleeps=1 installed=1 probes=5/5 wrong=0 broken=abstain taught=50/50 ow=0, same as 138i | PASS |
| M5 0 new wrong writes anywhere | 0 | probe write-parity 0; suites new WRONG/WRONG-WRITE/junk 0 (incl. marks123 0 moves) | PASS |

Verdict: PASS. 76 probe cases (22 A / 32 B / 22 C), fresh loop pair per
case, 4 shared fictional teaches (Kim/Lee). All B-cases route
DECLINE/D7 and stay screened. Registered probe 13.1 s; longest run smoke
92.5 s (< 25 min each, one suite at a time, Mac CPU offline).

## Reproduce
`export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_loop223_probe.py --run --out artifacts/fable-cantdo223-20260922`
then `python -B scripts/fable_suitediff.py --agent scripts/fable_loop223_agent.py --config artifacts/fable-cantdo223-20260922/loop223-config.json --base 138i --out <dir> --only <suite>` per suite, then `python -B scripts/fable_sleepsmoke206.py --agent scripts/fable_loop223_agent.py --config artifacts/fable-cantdo223-20260922/loop223-config.json --root <dir> --report <f> --label <l> --idle-seconds 5`.
Seal: `shasum -c artifacts/fable-cantdo223-20260922/SEAL.sha256.txt` (5/5 OK post-runs).

## Deviations
None from the brief. Probe methodology note: stored-facts fingerprint
compares semantic triples, not raw events (event_id carries a per-build
random suffix); per-case fresh loops keep counters in lockstep.

What it means: "What can't you do?"-style questions now get the fixed
CANNOT sheet instead of the negation clarify; nothing else changed.
What it does not mean: no screening, routing, or reply text changed
anywhere else; DECLINE stays DECLINE.
