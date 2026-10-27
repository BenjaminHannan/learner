# PASSMARKS — Exp 216: DECLINE INTENTS NEED THEIR CUE (Muse)

Agent: `scripts/fable_loop216_agent.py` (+ drivers `scripts/fable216_panel.py`,
`scripts/fable216_suites.py`, `scripts/fable216_scan.py`, all 216-prefix, new
files only). Config:
`artifacts/fable-declinecue216-20260922/loop216-config.json`. Base: loop138i
(`scripts/fable_loop138i_agent.py` +
`artifacts/fable-agent138i-20260922/loop138i-config.json`, read-only).
Cases: `cases216-p1.jsonl` (40), `cases216-p2.jsonl` (30), frozen pre-seal.

THE ONE CHANGE (this file's agent only): the 138g notebook-miss branch calls
`L138._route127(text)`; `Loop216AgentLoop.turn` swaps in a cue-gated stand-in
for the turn (saved/restored, nests with exp 212's same-pattern wrapper). A
decline verdict Dk (D1-D10 of `fable_self105.CANONICAL`) is served only when
the turn holds Dk's cue words (one table in the agent file; stems allowed) or
a second-person word (you, your, yours, yourself, u, ur); else the turn gets
exactly today's DECLINE reply (`HONEST_DECLINE + DECLINE_SUFFIX`), never a new
sentence. Non-decline intents, DECLINE verdicts, ears/_act/reasoner/notebook/
sleep/daemon untouched. No writes added anywhere (replies only).

## M1 — P1: 40 world questions the notebook can't answer (shapes Who VERBed
NAME? / What did NAME VERB? / Which NOUN did NAME VERB?), incl. all four
director examples (P1-01..04). No P1 text carries any D cue or second-person
word (verified by the agent's own tokenizer pre-seal). Bar: loop216 serves 0
D-intent replies (every P1 reply is today's DECLINE text). Base count reported
beside: loop138i serves D-intent on 6/40 (P1-01, P1-02 -> D1 "I do not have
favourites."; P1-03, P1-04, P1-21, P1-32 -> D5 "You never told me why. ...";
remaining 34 already DECLINE). Pilot: new 0/40, base 6/40.

## M2 — P2: 30 genuine self questions, 3 per D intent (with-you / without-you
but cued / extra), incl. "What's your favourite colour?", "Do you feel sad?",
"Why does Pim live in Arden?", "Is Oslo better than Rome?", "How old is Pim?",
"Did you dream?". Every P2 text passes its routed gate (D6/D8 conjunctions
hold: D6b uses "your"; D8s use my/me). Bar: 30/30 replies byte-identical to
loop138i (reply + routed intent), 0 moves. Pilot: 0 moves (base routes D on
15/30, rest DECLINE/C; identical all 30).

## M3 — frozen suites vs sealed loop138i rows: 0 moves except the 4
pure-function-scan predictions below (`scripts/fable216_scan.py`, text+reply
only, no agent run; piloted pre-seal, pilot == scan exactly). 0 new WRONG /
WRONG-WRITE / junk writes everywhere; bench 0 new wrong.
- rt136 (145): 0 moves (scan 0; pilot 136 OK / 6 WRONG-WRITE / 3 MISSED,
  identical; stored facts identical all 145).
- rt143 (124): exactly 3 moves, all reply-only D-canned -> DECLINE, 0 new
  wrong: J8 (WRONG-ANSWER->MISSED), K9 (WRONG-ANSWER->OK), O5
  (WRONG-ANSWER->OK). Sealed replies were "I have no opinions." (D7, cueless
  questions); new replies are today's DECLINE.
- sessions152: 0 moves (165 OK / 15 UNHELPFUL identical), 0 new writes.
- bench v3 4x200: 0 moves, 0 new wrong every split (new_121_4hop 187/9/4;
  old_s2fresh_4hop 195/5/0; edit200 149/51/0; bench132_4hop 191/9/0).
- marks123 (stock CLI, 9 suites; the CLI offers no q4 suite): 0 moves except
  rt81 I_edges-03 (turn "Mira": sealed "I cannot predict." UNCLEAR -> DECLINE
  OK, facts_delta 0, no writes). p2/p3/p4/rt110/q1/bench/sleep/soak identical
  (sleep SKIP both; soak 2000 turns 0 lost/0 wrong). Blob search: no other
  sealed marks report contains any D-canned string. q4 (underscore-leak scan):
  no q4 CLI suite exists (same for exp 212); 0 `[a-z]_[a-z]` matches in any
  pilot reply (rt136/rt143/bench/panel), sealed q4 leaks [] stands.
- M4 (writes): the gate swaps only the served reply; notebook deltas identical
  (rt136 stored 145/145, sessions new_writes 0, rt81 facts_delta 0).

## M5 — sleep smoke (`scripts/fable_sleepsmoke206.py`, stock): passes
(sleeps>=1, maternal_grandmother installed, 5/5 new-people probes right, 0
wrong, broken-chain abstains, taught intact, 0 overwrites). Pilot: 1 sleep,
installed episodes=20, probes 5/5, wrong 0, taught 50/50, ow 0, 150.6 s.

## Common rules
Seal: `shasum -a 256 PASSMARKS.md cases216-p1.jsonl cases216-p2.jsonl
scripts/fable_loop216_agent.py scripts/fable216_panel.py
scripts/fable216_suites.py scripts/fable216_scan.py loop216-config.json >
SEAL.sha256.txt` BEFORE any registered run. Ledger P216.n appended before the
run (append-only). Fictional names only in P1 (P2 reuses the brief's canonical
self-question names). P3 (natural panel 208) TEST-only: never opened. Bench =
base agent's drivers. Each run < 25 min Mac CPU (OMP_NUM_THREADS=1
MKL_NUM_THREADS=1, uv offline py3.12); daemon wrappers idle_seconds=3600
(smoke 30.0 explicit). Heavy suites one at a time. Never write to repo-root
notebook/. Post-seal code/config/case change => registered FAIL; driver-only
fix reported with diff, affected marks re-run in the open.
