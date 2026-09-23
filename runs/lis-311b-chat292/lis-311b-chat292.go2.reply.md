Resuming lis-311 — checking what the last run left behind.
Seal checks out and the first run left partial outputs — now tracking down the original task spec.
Sealed code looks complete. Setting up the run plan.
Stub checks pass 10/10. Launching the real-model try-out.
First conversation done, model responding. Waiting for the rest.
Two conversations done — waiting on the last one.
Try-out finished — verifying rows and starting the server.
Server answers on 8767. Gathering numbers for RESULTS.md.
First run's server turn confirmed in the transcript. Writing RESULTS.md.
VERDICT: PASS. lis-311 (re-run lis-311b) passes all three bars. The first run had sealed the files, written the ledger predictions, and served one server turn before the Mac slept; I verified the seal 5/5 OK, kept every sealed file untouched, did not duplicate predictions, and re-ran all steps from the sealed code.

Marks table (integer counts):

| Mark | Bar | Got |
|---|---|---|
| P311.1 every stub scenario passes | 10/10 PASS, exit 0 | 10/10 PASS, exit 0 |
| P311.2 base-chain writes in blocked-write test (T7) | 0 writes over 5 turns | 0 writes over 5 turns |
| P311.3 server on 8767 answers a turn | GET / 200 + POST /turn 200 with reply | GET / 200 + POST /turn 200 with reply |

Every move:
- Preconditions: disk 21 GB free, weights sha 112880d6…e8285324 matches lis-300 record, seal 5/5 OK.
- T1 two-facts-save: PASS, 2 triples, exact base confirmation reply.
- T2 whose-ask: PASS, exact "Whose dog is Pip, yours or someone else's?", 0 triples.
- T3a ask-back + yes: PASS, exact ask-back, "yes" saved exactly 1 triple.
- T3b ask-back + no: PASS, 0 triples, "Okay, I won't save that."
- T3c ask-back dropped by other turn: PASS, next turn saved normally (1 triple).
- T4 negation: PASS, 0 triples, base clarify reply.
- T5 CHECK: PASS, "I already have that.", triples unchanged (1), 0 new events.
- T6 question: PASS, answered from notebook, 0 new events.
- T7 blocked five: PASS, each turn verified teachable on raw 292 first, then 0 events / 0 triples under 311. Base-chain writes: 0.
- T8 unparsed: PASS, exact sorry-reply, 0 triples.
- Step 3 real-model try-out (report-only): 30 scripted + 4 adaptive "yes" = 34 rows in real-rows/rows.jsonl; device mps; ms median 2826.6, p90 15567.1, max 59429.6. 4 ask-backs, all resolved.
- P311.3 server: GET / 200; POST /turn 200, reply "Saved: your sister is Mira.", +1 triple; server left running; 8765 untouched (ready true); 8766 no answer (pre-existing, untouched); transcript shows first run's turn (index 0) plus mine (index 1).
- Wrote RESULTS.md (new file) and appended 2 ledger OUTCOME lines (P311.4, P311.5); predictions not duplicated; seal still 5/5 OK after run.

Misses: 0. Deviations on the bars: 0 — every sealed prediction matched exactly.

Step-3 observations (no bar, reported as-is): A#7 mouth said "I didn't save it" yet the triple was written; A#8 ASK missed a just-saved lowercase fact ("I don't know anyone whose dog is pip"); C#4 correction left zoe with 2 cats; small talk saved 0. Consistent with the known lis-300 recall weakness.

What it means in plain high-school English: the notebook guard moved onto the new 292 base without breaking — normal facts save, unsure ones get a check-back question, and the five turn types that must never write wrote nothing. The chat page on 8767 works with the real model and is still running for Ben; his old pages were untouched. What it doesn't mean: the model does not recall well (about half of true facts get asked back), the slowest casual turn took ~59 s on the loaded Mac, and no graded test panel was touched.

PUSH: artifacts/claude-lis311-20260923 scripts/claude_lis311_agent.py scripts/claude_lis311_try.py scripts/claude_lis311_server.py scripts/claude_lis311_start.sh artifacts/fable-predictions-ledger.md
