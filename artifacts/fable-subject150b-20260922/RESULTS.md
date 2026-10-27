# Exp 150b RESULTS — clause-in-subject guard on loop150 (Muse)

Target: loop150b = loop150 + Subject150BMixin
(scripts/fable_fix150b_subject150b.py; wrapper
scripts/fable_loop150b_agent.py; config
artifacts/fable-subject150b-20260922/loop150b-config.json). THE ONE CHANGE:
loop150's subject guard looks only for hedge/reporting/filler words, so a
teach whose SUBJECT swallows a whole second clause ("Ann is famous for
Cats and Tom died in the city of Oslo" -> subject "Ann is famous for Cats
and Tom", place_of_death, Oslo; director re-checked on loop129b, loop144
AND loop150) saves a wrong triple. Now any teach/correct whose subject
span holds a relation cue from the loop's own relation tables or a
lower-case finite verb/copula is refused with the existing SPLIT reply (0
writes). Matching is case-sensitive (only lowercase fires), so
capitalised titles ("Gone with the Wind", "Who Framed Roger Rabbit",
"Is This It", "The Lives of Others", "Born to Run") still teach exactly;
bare role nouns and verbless of-phrases are not cues, so possessive tails
pass; single-token subjects are exempt. Values, relations,
forget/ask/clarify untouched.

## Marks table (integer counts, every case reported, never averaged)

| mark | bar (PASSMARKS.md, sealed) | got | verdict |
|---|---|---|---|
| S1 49-case probe through loop150b | 23 refuses 0 wrong writes; 24 must-writes >= 90 % exact 0 wrong writes; t14 refuses | 49/49 OK (23/23 refuse-empty SPLIT; 14/14 plain + 10/10 verb-titles exact; t14 refuse-empty SPLIT; 2/2 possessive-title literals no-write; 0 wrong writes) | PASS |
| S2 cases150.json re-run | per-case identical to sealed loop150 run, 0 moves | 57/57 OK, moves=[] replies identical | PASS |
| G1 bench 3 splits | per-item identical to sealed loop150 rows, 0 new wrong | 600/600 verdict-identical, reply_moves 0, new_wrong [] (edit200 150/50/0; old 157/43/0; new 136/63/1); re-run post-fix identical again (23.6 s) | PASS |
| G2 marks123 suites | per-case identical to loop150's marks150 | p2 64/64 rows + p4 30/30 + q1 + rt81 74/74 + bench 400/400 + sleep SKIP + soak 2000/3/0-0-0 + q4 leaks identical; p3 L1-L6 PASS; rt110 62/62 verdicts identical (see deviation 3) | PASS * |
| G3 152 sessions | replies identical to T-T, 0 new WRONG/writes | reply_diffs [] all 6 sessions, new_wrong [], new_writes [] (see deviation 4) | PASS * |
| G4 each run < 1500 s | < 1500 s Mac CPU | probe 4.2/5.4 s, bench 62.5/23.6 s, sessions 3.4 s, suites p3 46 s rt110 140/225 s soak 133 s q1/p2/p4/rt81/sleep seconds each; full-parallel marks123 invocation breached (see deviation 2) | FAIL * |

\* verdicts with deviations, all disclosed below; no silent re-runs.

## What it means

Teaches that pack two facts with the extra clause hiding in the subject no
longer corrupt the notebook (23/23 refused, 0 writes, incl. the exact 144
t14 text), while every ordinary teach -- including titles built from verbs
-- stores exactly as before, with zero behaviour change on benches, marks
suites and phone sessions wherever the harness delivered the turns.

## What it does not mean

It does not judge truth -- a confidently-stated false single fact still
stores; it does not touch the value span (139b's business), questions, or
the one-word-names FakeEars ceiling (the two possessive-title literals
still clarify instead of teaching, exactly as on loop150).

## Deviations

1. Post-seal one-line fix (reported): Loop150bDaemon.__init__ missed
   `self.idle_seconds = float(idle_seconds)` (loop150 has it), so daemon
   subprocesses crashed after boot (AttributeError in run()). Fixed in
   scripts/fable_loop150b_agent.py; S1/S2/bench/sessions do not exercise
   that line (in-process builds), bench G1 re-run post-fix identical;
   p3/rt110/soak ran post-fix.
2. G4 FAIL: the sealed full `marks123 --workers 4` invocation exceeded 25
   min (killed at the timeout, mid-rt110) -- 5+ agents' suites ran
   concurrently on the same Mac. Same work completed as per-suite
   invocations, each < 1500 s. One G4 FAIL with this diagnosis note.
3. G2 rt110 (three runs, all disclosed): run 1 (post-fix): 62/62 verdicts
   identical incl. R4 BUG/BUG (one log-only flake: phantom empty msg_00
   served once, verdict unchanged). Run 2 under heavier load: T2 OK->BUG +
   N5 log flake, both with leading "I didn't catch anything." (empty input
   served, real turn 0 lost to the sealed harness's non-atomic inbox write
   vs daemon poll). Run 3: 62/62 verdicts identical, reasons identical,
   ok_to_bug=[] bug_to_ok=[]; only two cosmetic `statuses:[]` vs
   `['write'/'clarify']` status-file read races, replies and writes
   identical everywhere. In-process loop150-vs-loop150b replays of the
   exact R4/T2 turn texts are byte-identical (replies + triples), and no
   SPLIT reply appears in any regression log -- the guard fired nowhere
   outside the probe. The moves are harness-race artifacts under 5-agent
   concurrent load, verdict-identity holds wherever turns were delivered.
4. G3: one verdict-label-only move (S5 turn 16 OK->UNHELPFUL) with
   byte-identical reply ("I already have that.") and 0 writes: the sealed
   T-T label is hand-corrected ("CORRECTED: idempotent re-teach"), the
   re-judge is mechanical. Replies identical, 0 new WRONG, 0 write deltas.

Reproduce: PASSMARKS.md command block (sealed SEAL.sha256.txt; p3/rt110/
soak also runnable per-suite with --suite). Ledger: P150b outcomes below.
