# Exp 117 pass marks — redteam110 patches on loop102 (sealed before the registered wave)

Loop117 = loop102 + three small fixes, nothing else (new file
`scripts/fable_loop117_agent.py`, subclass/wrap only; no existing file
edited): (1) F5 please-forget keeps its space; (2) shouted possessives
split (`_APOS` runtime override, this process only); (3) replies render
relation names with spaces (mouth wrapper; stored keys unchanged).

- Q1: the F5 reproducer (teach / "Please forget Mira city" / re-teach
  Paris / ask -> contains "Paris", absent "Lisbon") and the M5 reproducer
  (teach / "WHO IS MIRA'S CITY?" -> contains "Lisbon") each run once
  through a REAL loop117 daemon subprocess via its mailbox
  (`artifacts/fable-loop117-20260922/repro/fable_loop117_repro_{F5,M5}.py`).
  Bar: both OK.
- Q2: all 62 sealed exp-110 cases
  (`artifacts/fable-redteam110-20260921/fable_redteam110_cases.json`)
  re-run on loop117 with the SEALED exp-110 checker
  (`fable_redteam110_runner.judge`, same mailbox harness, only the daemon
  binary swapped). Bar: 0 OK->BUG, 0 HARNESS-ERROR, F5 and M5 BUG->OK;
  R4/N6/S3/S6 stay BUG (safe declines per the exp-110 RESULTS analysis;
  any other still-BUG fails the mark).
- Q3: loop102 marks P2 (64 redteam98 cases), P3 (L1-L6), P4 (30 innocent
  sentences) re-run against loop117
  (`scripts/fable_loop117_marks.py`, agent-class swap only). Bar: same
  pass/fail outcomes as the sealed loop102 marks, 0 new wrong writes
  (wrong_write counts and still-BUG lists compared field by field;
  reply-text-only diffs are listed, never averaged).
- Q4: no reply in any Q2/Q3 transcript contains an underscore inside a
  relation name (`scripts/fable_loop117_q4scan.py` over q2-report.json,
  p2/p4-report.json, p3/ reports; a hit is an underscore token in the
  possessive relation slot or matching a known multi-word relation key).
  Bar: 0 leaks.
- Q5: whole registered wave (Q1+Q2+Q3+Q4) < 20 min wall-clock on the Mac
  CPU, `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`, offline
  (`uv run --offline --no-project --python 3.12 --with torch --with numpy
  python -B ...`).

Deviations locked before the run: (a) P3-L2 runs in-process, so the
runtime `_APOS` override also widens the loop90 "before" arm there (L1's
before arm is a separate subprocess and stays pristine); the sealed
comparison is on pass/fail + wrong writes, with the changed-list diff
explained, not hidden. (b) The mouth renders every "_" as " " in replies,
so a taught literal VALUE containing an underscore (e.g. the pet name
"MISSING_FACT" in one L2 turn) displays spaced; stored values/keys are
byte-identical. (c) One pre-run smoke only, with unsealed sentences
(import + three unit checks, config write). A registered FAIL is recorded
as FAIL, never re-run into a pass. Claims never exceed evidence. Every
case reported, never averaged.
