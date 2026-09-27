# PASSMARKS — Experiment 151: no-question-mark fix (2026-09-22)

Single-change fix for the director probe: after "The capital of Peru is
Lima", "What is the capital of peru?" answers but "What is the capital of
Peru" (no "?"), "what is the capital of peru", "who is jo ng married to",
"whats jo ng's country of citizenship", "Where is Jo Ng a citizen of" all
reply "I didn't understand that."

Question-vs-statement decision (read-only, never edited):
`scripts/fable_loop121_agent.py:175` (`Loop121Ears.hear`: ends in "?" ->
question side exact loop113b, else teach path) is where the loop decides
question vs statement. Also gating on "?": `fable_loop113b_agent.py:70`
(N-hop router only on "?"), `fable_loop132_agent.py:83` (132 rewriter only
on clarified "?"), `fable_loop102_agent.py:290` (F4 strip never on "?").

THE ONE CHANGE (question side only; teach path and everything else
byte-identical): a message containing NO "?" at all is fed through the
exact base path as its byte-exact "?" twin (whitespace collapsed, trailing
phone-typing "." / "!" stripped, "?" appended) when (a) its first word
after optional openers is a sealed question word/auxiliary AND (b) the
existing teach parser (`hear_teach_template` + `hear_teach_extra`) accepts
nothing on the collapsed text or its qualifier-stripped form. All other
turns pass through untouched. New files only:
`scripts/fable_qmark151_core.py` (sealed list + pure predicate),
`scripts/fable_loop151_agent.py` (variant A Loop151 over loop134; variant B
Qmark151 over loop132 + wordmatch149 re-applied at bind), drivers
`scripts/fable_qmark151_q1.py` / `_run143.py` / `_bench.py`, artifact
`artifacts/fable-qmark151-20260922/`, doc
`design/v3/30-modes/151-no-question-mark-muse.md`. No existing file is
edited; sealed 143/bench/marks files are read-only.

SEALED WORD LIST (exact; case-insensitive, U+2019 -> ASCII, punctuation
stripped): openers hey, hi, ok, so, and, um (skipped repeatedly); singles
what, whats, what's, who, whos, who's, whose, where, wheres, where's,
which, when, how, is, are, was, does, do, did, can, could; phrases tell me,
do you know. ("where's" is the apostrophe-normalised twin of "wheres".)

Pre-seal dev evidence (not registered): teach parsers return None on all
probe question shapes and the triple on teaches; loop134 "?" twins answer
where taught (capital/spouse/employer/2-hop frames) and clarify elsewhere
with 0 writes; all 800 bench questions end in "?"; bench scan finds 0
teaches that trigger the predicate with both parsers rejecting; sealed
suite scan finds trigger-shaped turns only in rt81 D_q_vs_s-02/-03
(".", no "?"; twins dev-verified: D-02 still answers Lisbon, D-03 still
clarifies) while rt110 interior-"?" turns are untouched (rule needs NO "?"
at all). Core/mixin unit behaviour verified in-process on loop134 shapes.

Registered runs (Mac CPU, offline, `export OMP_NUM_THREADS=1
MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with torch
--with numpy python -B ...`; every seed/case reported, never averaged):
  scripts/fable_qmark151_q1.py --variant 151 | qrewrite
    (32 sealed pairs x2 dialogues + 22 non-questions, fresh daemon dir each)
  scripts/fable_qmark151_run143.py
    (sealed 143 runner imported; ART redirected here; variant B only)
  scripts/fable_qmark151_bench.py --variant 151 | qrewrite
    (scorer v2 imported from bench132 runner; 4 suites each)
  scripts/fable_marks123_all.py --agent scripts/fable_loop151_agent.py
    --config artifacts/fable-qmark151-20260922/loop151-config.json
    --out artifacts/fable-qmark151-20260922/marks151 --workers 4
    (variant A only; generic runner picks Loop151Daemon by name)

| Mark | Pass condition |
|---|---|
| Q1 paired probe, each variant | 32/32 no-"?" replies byte-equal to "?" twins; 22/22 non-questions carry an abstain marker with 0 notebook writes (no confident fact answer) |
| Q2 143 re-run, variant B only | J5 + J10 answer as their "?" twins would (OK); 0 of the other 122 cases worse than sealed qrewrite149 rows (worse = OK->non-OK or MISSED->WRONG-ANSWER; improvements allowed) |
| Q3 benches per-item identical | 0 verdict diffs on all 4 suites x both variants vs the stated bases (sealed loop134 rows / sealed loop132 rows / same-process loop134 / same-process qrewrite149) |
| Q4 marks123 vs loop134 | every suite verdict identical to sealed marks134; exactly one predicted reply-text-only diff: rt81 D_q_vs_s-02 ("Mira's city is Lisbon?." -> "Mira's city is Lisbon."), verdict stays OK; each registered run < 25 min wall-clock Mac CPU; daemon wrappers accept idle_seconds (explicit) |

A registered FAIL is recorded as FAIL, never re-run into a pass. Claims
never exceed evidence.
