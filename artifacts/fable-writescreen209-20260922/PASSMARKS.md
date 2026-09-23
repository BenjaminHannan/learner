# PASSMARKS — Exp 209: WRITE SCREEN on loop138i (Muse)

Agent: `scripts/fable_loop209_agent.py` (subclass of loop138i; 138i never
edited). Config: `artifacts/fable-writescreen209-20260922/loop209-config.json`.
Cases: `cases209-badsave.json` (32), `cases209-nearmiss.json` (33).
Drivers: `scripts/fable_writescreen209_probe.py` (W1/W2),
`scripts/fable_writescreen209_suites.py` (W3 frozen + bench).
Base: loop138i live (plus its sealed rows for the W3 diff).

## The one change (three screens, outermost ears + _act value backstop)

(a) A leading "named"/"called" is stripped from a taught/corrected value
("is named Pip" -> "Pip"; person-valued too: "is named Rita" -> entity
Rita). Only leading occurrences; later-in-phrase stays byte-identical.
Empty-after-strip clarifies ("I didn't get the value."), 0 writes.
(b) Date-type relations (key contains "birthday"/"anniversar", or "birth"
+ "date"/"day", or exactly "birthdate"/"dob") with values "in|on <month|
weekday|date>" store the stripped literal ("in March" -> "March"), never
an entity. Person relations untouched (month-named people stay entities).
(c) A teach/correct whose relation KEY contains a clause word (but, now,
that, which, who, because, then, "used to" as whole tokens) is refused:
0 writes (no FACT/RELATION/ENTITY) + the base's one-fact-at-a-time reply
("I can take one fact at a time — could you split that?"). Values
containing those words are unaffected.

## W1 — bad-save cases on loop209

Bar: 32/32 pass, 0 bad saves; every stored taught fact exactly
(subject display, relation, literal-vs-entity + text) as in the case
file; reply contains/exactly the expected text; nowrite cases add no
RELATION event. Piloted pre-seal: all 32 base-differs (base stores
"named Pip", entity "in March", relation friend_who_lives_in_oslo, ...).

## W2 — near-miss cases loop209 vs loop138i

Bar: 33/33 byte-identical (reply list, stored taught facts with value
kinds, entity names, FACT-event counts). Covers month-named people
(N01-N06), later-in-phrase named/called (N07-N10), multi-add (N13/N29),
Me/verb/of-chain/copula paths, date boundaries (bare "March", "spring",
third-person "Lena's birthday is in March"), clause-in-value (N22),
token boundary "thenar" (N31). Piloted pre-seal: 33/33 identical.

## W3 — frozen suites + marks123 + bench vs loop138i

Bar: per-case identical to loop138i (verdict + reply + stored/writes);
0 new WRONG / WRONG-WRITE / junk writes; 0 moves on every suite.
Piloted pre-seal (final code): rt136 145 cases 0 moves; rt143 124 cases
0 moves; sessions152 0 moves, 0 new writes; bench-v3 4x200 0 moves,
0 new wrong; marks123 per-case identical to the sealed marks138i rows
on every suite (p2/p4/rt81/rt110/bench verdict+reply+stored exact;
p3 l1-l6 case rows exact; q1/q4/soak exact) except the volatile set:
`seconds` timings, l6 `replied_before_kill` kill-timing counts, and
the sleep SKIP reason's agent filename. Predicted moves: NONE.

## Common rules

Seal: shasum -a 256 PASSMARKS.md + cases209-badsave.json +
cases209-nearmiss.json + scripts/fable_loop209_agent.py +
loop209-config.json > SEAL.sha256.txt BEFORE any registered run.
Ledger P209.n appended before the run. Fictional names only. Bench =
base agent's v3 driver (fable_fix172b_benchv3); marks123 = stock CLI.
Each run < 25 min Mac CPU (OMP_NUM_THREADS=1 MKL_NUM_THREADS=1, uv
offline py3.12); daemon wrappers use idle_seconds=3600. Heavy suites one
at a time. Never write to the repo-root notebook/. Post-seal
code/config/case change => registered FAIL; driver-only fix reported
with diff, affected marks re-run in the open.
