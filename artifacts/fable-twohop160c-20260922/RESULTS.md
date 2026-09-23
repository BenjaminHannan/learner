# Exp 160c RESULTS — bare correction after a >= 2-fact chain asks which fact is meant

After a multi-hop answer, a bare correction no longer guesses the last hop.
It writes nothing and asks which fact is wrong, listing every fact of the
chain; an explicit follow-up ("Actually, ...") then saves exactly the named
fact. Single-fact answers behave exactly as loop160b did. Additive only:
new files with the 160c prefix; loop160b, 160/160b files and all sealed
artifacts read, never written; no commits.

Step 1 answer: 160b picks the last-stated fact at
scripts/fable_fix160b_laststated.py:141-151 (`LastStated160bMixin._act`
resolves `bare_correct` against `_last_stated160b`, the saved triple or the
final-hop fact). The 160c mixin intercepts only the >= 2-fact-chain case.

## Marks table (integer counts, every seed/case reported, never averaged)

| mark | bar | got | status |
|---|---|---|---|
| T1 probe (68 dialogues, probe160c-loop160c.json) | H 20/20 exact clarify + 0 writes, follow-up changes only named fact; S 24/24 + O 24/24 identical to loop160b | 20/20 + 24/24 + 24/24 = 68/68 OK | PASS |
| T2 0 wrong writes | bare turns 0 writes, follow-ups write exactly named fact | 0 wrong over 68 dialogues | PASS |
| C2/G3 sessions (180 turns, run160c-session152-summary.json) | exactly 1 predicted move (S3n6 OK->UNHELPFUL, writes 1->0, which-one-is-wrong clarify); other 179 identical; 0 new WRONG | predicted 1/1 met; unpredicted 0; new_wrong 0 (S4's 2 WRONG pre-exist in loop160b run) | PASS |
| G3 redteam136 (145) + redteam143 (124) | 0 moves, 0 new WRONG vs live loop160b arm | 0 moves; new_wrong 0/0 (14 WRONG-WRITE + 5 MISSED on 136, 21 WRONG-ANSWER + 12 MISSED on 143, all pre-existing) | PASS |
| G1 bench (600 items, fable_bench160c_loop160c_summary.json) | 0 verdict + 0 reply moves vs loop160b rows, 0 new wrong | 600/600 identical (edit200 150/50/0; old 157/43/0; new 136/63/1, same 1 pre-existing wrong) | PASS |
| G2 marks123 (marks160c vs marks160b) | per-case identical except predicted sleep naming | p2 64/64, p4 30/30, p3 L1-L6 7/7, rt110 62/62, rt81 74/74, q1/q4/soak/bench content-identical, sleep SKIP names new file only | PASS |
| G4 budget | each run < 1500 s Mac CPU | probe 1.7 s, bench 66.0 s, sessions 4.1 s, redteam 24.1 s, marks123 219.6 s total | PASS |

## Deviations

None. No code edit after the seal (`shasum -c SEAL.sha256.txt` OK); no
re-runs (no flakes met: rt110/soak ran clean first time, solo). Suite-level
FAILs on p2/q1/rt81/q4 are the known-bug documentation suites, FAIL
identically per-case in marks160b. Pre-seal dev checks (director probe,
3-hop, first-hop follow-up, S3-only session, full H-20 dry run) wrote no
artifact files.

## Questions for Ben

None. Conservative default kept: a bare value after a chain answer is
treated as ambiguous (ask, don't guess); the example in the clarify names
the last chain fact, so fixing any other hop still needs one explicit turn.

## Reproduce (worktree root, seal check first, one at a time)

shasum -c artifacts/fable-twohop160c-20260922/SEAL.sha256.txt
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix160c_probe.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix160c_bench.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix160c_session152.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix160c_redteam.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop160c_agent.py --config artifacts/fable-twohop160c-20260922/loop160c-config.json --out artifacts/fable-twohop160c-20260922/marks160c --workers 4

What it means: bare "no wait, it's V"-style corrections after a two- or
three-hop answer now ask which fact is wrong instead of silently rewriting
the last hop, with zero measured regressions anywhere else.
What it does not mean: pronouns, held-out wording beyond the sealed shapes,
and multi-row answers are unchanged and still get the old clarify.
