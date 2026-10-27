# Exp 160b RESULTS — bare corrections target the last stated fact (loop160b = loop150 + one mixin)

A bare correction (160's five sealed shapes) now rewrites the ONE fact the
agent's immediately previous reply stated — the triple it just saved, or
the final-hop fact of the answer it just gave — through the existing
correction path. Anything older is never targeted; a fact-free previous
reply gets the sealed clarify with 0 writes. Additive only: new files with
the 160b prefix; loop150, 160 files and all sealed artifacts read, never
written; no commits.

## Marks table (integer counts, every seed/case reported, never averaged)

| mark | bar | got | status |
|---|---|---|---|
| C1 probe (56 dialogues, probe160b-loop160b.json) | A 16/16 + B 16/16 triples+reply equal to "Actually" twins; C 14/14 exact clarify, 0 writes on bare turn; D 10/10 byte-equal replies+writes vs loop150 | 16/16 + 16/16 + 14/14 + 10/10 = 56/56 OK | PASS |
| C2/G3 sessions (180 turns, run160b-session152-summary.json) | exactly 1 predicted move (S3n6 UNHELPFUL->OK, +1 write, "Saved: Rao's city is denver."); other 179 identical; 0 new WRONG | predicted 1/1 met; unpredicted 0; new_wrong 0 | PASS |
| G1 bench (600 items, fable_bench160b_loop160b_summary.json) | 0 verdict + 0 reply moves vs loop150 rows, 0 new wrong | 600/600 identical (edit200 150/50/0; old 157/43/0; new 136/63/1, same 1 pre-existing wrong) | PASS |
| G2 marks123 (marks160b vs marks150) | per-case identical, 0 predicted moves except sleep SKIP agent-file naming | p2 64/64, p3 L1-L6 7/7, p4 30/30, rt110 62/62, q1, bench 400/400, rt81 74/74, soak 2000/3/0-0-0, q4 leaks identical; sleep SKIP names loop160b file only | PASS |
| G4 budget | each run < 1500 s Mac CPU | probe 10.4 s, sessions 7.2 s, bench 96.1 s, p3 38.8 s, rt110 136.6 s, soak 158.9 s | PASS |

## Deviations

1. G2 full-parallel run (load avg 59–119, four sibling agents running
   marks suites concurrently): p3 `run_l1` raised `no outbox reply for r
   within 180s` on a loop96-after daemon. First diagnosed as contention
   starvation (same known mailbox class as 139b->150/155/158) — WRONG.
   The solo open re-run failed identically, and the leftover daemon log
   showed the real cause: `Loop160bDaemon.__init__`
   (scripts/fable_loop160b_agent.py) never set `self.idle_seconds`, so
   every loop160b daemon crashed on its first tick
   (`AttributeError` at scripts/fable_daemon74_run.py:198). The sealed
   correction rule was never reached and is untouched.
2. Post-seal harness fix (reported, rule unchanged): one line added,
   `self.idle_seconds = float(idle_seconds)`, mirroring loop150 line 72
   exactly (same precedent as 150c/164a daemon fixes). No sealed file
   touched (`shasum -c SEAL.sha256.txt` still OK); the sealed rule module
   `fable_fix160b_laststated.py` is byte-untouched. Affected suites re-run
   solo in the open: p3 PASS (38.8 s, L1-L6 7/7), rt110 PASS (136.6 s,
   62/62 verdicts match sealed expectations); per-case diffs vs marks150
   are zero for both. Both the crashed attempts and the clean re-runs are
   reported here.
3. q4 + summary aggregation: q4 computed with the runner's own
   `suite_q4`/`collect_replies`, and `fable_marks123_summary.json` built
   with the parent's own table schema (per-suite reports already on disk;
   no suite re-run). Reference summary is overall FAIL too (p2/q1/rt81/q4
   are known-bug documentation suites, FAIL identically in marks150).

## Questions for Ben

None. Conservative default kept: a bare correction can only address what
the previous reply stated (never an older fact, never a guess), and it
travels the same guarded "Actually, ..." path.

## Reproduce (worktree root, seal check first)

shasum -c artifacts/fable-correct160b-20260922/SEAL.sha256.txt
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix160b_probe.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix160b_session152.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix160b_bench.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop160b_agent.py --config artifacts/fable-correct160b-20260922/loop160b-config.json --out artifacts/fable-correct160b-20260922/marks160b --workers 4

What it means: bare "no wait, it's V"-style corrections now follow the
conversation — the just-saved triple or the just-answered fact — exactly
like "Actually, ..." does, with zero measured regressions.
What it does not mean: pronouns, multi-fact answers and held-out wording
beyond the sealed shapes were not tested and still clarify.
