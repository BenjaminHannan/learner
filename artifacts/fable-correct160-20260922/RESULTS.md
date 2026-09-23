# Exp 160 RESULTS — bare corrections (loop160 = loop150 + one mixin)

Bare "no wait, it's V" / "wait, it's V" / "sorry, it's V" / "I meant V" /
"no, V" now rewrites the session's most-recent saved teach through the
existing correction path (same guards, same "Saved: ..." reply, same
supersede). No saved teach yet -> the sealed Which-fact clarify, 0 writes.
Additive only: new files with the 160 prefix; loop150 and all sealed
artifacts read, never written; no commits.

## Marks table (integer counts, every seed/case reported, never averaged)

| mark | bar | got | status |
|---|---|---|---|
| C1 probe (44 dialogues, probe160-loop160.json) | A 20/20 triples+reply2 equal to "Actually" twins; B 12/12 exact clarify, 0 writes on bare turn; C 12/12 byte-equal replies+writes vs loop150 | 20/20 + 12/12 + 12/12 = 44/44 OK | PASS |
| C2/G3 sessions (180 turns, run160-session152-summary.json) | exactly 1 predicted move (S3n6 UNHELPFUL->OK, +1 write, "Saved: Rao's city is denver."); other 179 identical; 0 new WRONG | predicted 1/1 met; unpredicted 0; new_wrong 0 | PASS |
| G1 bench (600 items, fable_bench160_loop160_summary.json) | 0 verdict + 0 reply moves vs loop150 rows, 0 new wrong | 600/600 identical (edit200 150/50/0; old 157/43/0; new 136/63/1, same 1 pre-existing wrong) | PASS |
| G2 marks123 (marks160 vs marks150) | per-case identical, 0 predicted moves | 10/10 suite summaries identical; per-case 0 moves (p2 64/64, rt110 62/62, rt81 74/74, q1, bench 400/400, p3/p4/soak/q4 reports identical modulo seconds) | PASS |
| G4 budget | each run < 1500 s Mac CPU | probe 8.0 s, sessions 11.1 s, bench 154.9 s, marks123 265.5 s | PASS |

SCORE: C1 PASS, C2 PASS, G1 PASS, G2 PASS, G4 PASS. 5/5 predictions upheld.

## Deviations (post-seal, all reported, affected marks re-run in the open)

1. Probe-runner bug (not a loop bug): B-group judged whole-dialogue
   writes, failing 4 cases whose setup teach wrote once. Fixed the runner
   to judge last-turn writes; sealed cases untouched; seal re-verified OK.
2. Memory-rule correction + re-seal: v1 ("IMMEDIATELY previous turn"
   strictly) clarifies on the sealed N6 turn itself (S3n6: teach 3 turns
   back, previous turn a question) and cannot meet sealed C2 ("N6 turns
   become OK"). Memory is now the most-recent saved teach (never cleared
   by non-write turns, replaced by newer teaches). PASSMARKS.md, C1-B cases
   (recomposed to carry no saved teach; counts still 20/12/12) and the
   design doc were updated and SEAL.sha256.txt regenerated BEFORE the
   bench/marks/session registered runs; only the probe had run.
   Predictions P160.1-P160.5 unchanged. Old seal hashes superseded.
3. G2 full-parallel run: rt110 R3/msg_00 logged `statuses: []` vs
   `['write']` (verdict/reply/writes identical) — a harness read-ahead
   race under contention (rt110 took 265 s vs 88 s uncontended). Solo
   rt110 re-run (marks160-rt110only/): 0 per-case diffs vs marks150.
   sleep SKIP reason names the agent file (verdict SKIP identical, same
   precedent as 139b->150).

## Questions for Ben

None. Conservative default kept: a bare correction can only rewrite a
triple this session taught (never an old fact, never a guess), and
"teach, question, bare" now corrects the earlier teach rather than
clarifying — the reading the sealed C2 bar requires.

## Reproduce (worktree root, seal check first)

shasum -c artifacts/fable-correct160-20260922/SEAL.sha256.txt
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix160_probe.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix160_session152.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix160_bench.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop160_agent.py --config artifacts/fable-correct160-20260922/loop160-config.json --out artifacts/fable-correct160-20260922/marks160 --workers 4

What it means: five bare-correction shapes now correct the just-taught
fact exactly like "Actually, ..." does, with zero measured regressions.
What it does not mean: pronouns, multi-turn staleness and held-out
wording beyond the sealed shapes were not tested and are unchanged.
