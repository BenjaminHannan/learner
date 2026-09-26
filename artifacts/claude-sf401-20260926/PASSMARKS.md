# PASSMARKS sf-401: the stale-fact guard (registered 2026-09-26, before any run)

Owner: the wrong-as-fact thread (0.2c row H1, "wrong answers stated as fact"). Written and committed BEFORE the
panel exists and before any run. Sealed with SEAL-sf401.sha256.txt at registration; never edited after. Any later
change goes in a dated addendum below the seal line and never moves a bar.

## Why (counts only; bank D is TEST-ONLY and no item was read)
0.2c bank D, judged wrong-as-fact answers: X 8, G 5. 10 of the 13 are questions after a correction; all 13 name a
value that was in the notebook at that moment; 8 name the old, corrected value. At X's 30 edit asks the notebook held
the new value 7 times and still held the old value 12 times. DEV mechanism (readable): the lis-319 reader reads 9 of
10 DEV corrections with the right person and new value but below 0.995 (0.25 to 0.98); lis-314 parks the new value
and only uses it when the notebook has no answer, so the old value is stated.

## One change
A = claude_e2e02c:build_02c exactly as 0.2d-r's X' (sealed 0.2c code, artifacts/claude-e2e02c-20260926/SEAL-code;
lis-319 merged reader sha256 e688e1b2...6a76 through claude_readersha_wrap.py; 0.2c sleep adapter sha256 a33211dc...
with its sidecar). B = A + the stale-fact guard, claude_sf401_agent:build_02c_sf401 (scripts/claude_sf401_agent.py,
installed right after the listener stack; nothing else differs). CPU tests scripts/claude_sf401_test.py 13/13.

## Test set
corrpanel401 (artifacts/claude-sf401-20260926/PANEL-SPEC.md): 24 fresh lives in the 331 bank format, written blind
by a separate agent into escrow, audited by a second blind agent, copied unread and sealed before the run. At least
60 edit asks, 60 corrections in six wording styles, 30 decoy turns (near a fact but changing nothing), and at least
124 asks about facts never corrected. TEST-ONLY: builders see category counts only.

## Run
BensPC, one job (handoff/queue/007s-sf401-benspc.md), $0: A then B on the panel with scripts/claude_e2e336_run.py,
then scripts/claude_e2e336_score.py on both. Blind judging in the cloud afterwards (below).

## Marks
Counts are over the panel's asks. "Judged wrong" = a WRONG_CANDIDATE ask (336 scorer) that the blind judges call a
wrong answer stated as fact (both judges, or the third on a split). "Right" = RIGHT + RIGHT_CONFIRM (336 scorer).
"Control asks" = every ask whose ask_type is not "edit" or "never_told" (answerable, never-corrected facts).

| Row | What | Bar |
|---|---|---|
| M1 | judged wrong answers stated as fact, all asks | B ≤ A − 4 |
| M2 | right answers on control asks | B ≥ A − 2 |
| M3 | right answers on edit asks | B ≥ A |
| M4 | "don't know" on control asks (scorer ABSTAIN) | B ≤ A + 2 |
| M5 | judged wrong answers on control asks | B ≤ A + 1 |

sf-401 PASSES only if every row passes. INCONCLUSIVE (M1 undecided, the rest still reported) if A has fewer than 5
judged-wrong edit asks: the panel then has too few stale answers to show the change. A FAIL stays a FAIL.

## Judging (fixed now)
Packets: every WRONG_CANDIDATE ask of A and B (score/judge_asks_A.jsonl, judge_asks_B.jsonl), mixed under neutral ids,
shuffled with seed 4011 (scripts/claude_sf401_judges.py prep). Each packet shows the user's question, the reply, and
the life's facts valid at that moment; never the arm, the code, or the other arm's reply. Two blind Opus judges each
answer per packet "wrong" (the reply states, as fact, an answer that contradicts the valid facts or is not in them)
or "ok" (it says it doesn't know, asks, hedges, or is right); a third blind judge decides splits. Keys are applied by
script. A blind recount agent recomputes every row from the files before the report. Ben grades nothing.

## Report only
The guard's counters for B (doubts by rule a/b/c, fired, confirm vs hedge, offers answered yes/no, skipped as
explained by another fact); confirm questions asked per arm (Ben's attention cost); facts saved and new triples whose
owner and value are not on the truth sheet, per arm; edit asks right and judged wrong by correction style; right
answers on the asks that check a decoy; never-told answered "don't know" per arm; ms per turn.

## What the result would mean (fixed now)
- M1 fails while the guard fired at least as often as A's judged-wrong edit asks: the wrong answers come from a path
  the guard does not see (for example a reply that names the old value in other words); look at fired vs wrong by
  correction style.
- M1 fails and the guard fired rarely: most corrections leave no trace the guard can use (the reader misses the
  person or the relation), which is Reading facts' line; the doubt counters by rule show which.
- M2, M4 or M5 fails: false doubts; the decoy breakdown shows which kind.
- A PASS says the guard cuts stale answers in the joined assistant on fresh lives. Joining it into a build is
  Month-end's call, and the 0.2c/0.2d-r H1 verdicts are not changed by this run.
