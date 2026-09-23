Building 255b — additive follow-up to 255, CPU only.
Files mapped — now pulling the 255 driver set and 138m base.
Load is 136 (must be ≤60 for heavy runs) — I'll do all light build work first, then pilot/register when the machine frees up.
Samples confirmed — none hit the zero branches, so the test needs dedicated zero-case olds. Writing the 255b text module now.
Unit tests green (60 templates, 519 sweep renders, 0 failures; T02 anchors identical). Now the agent/config/driver copies.
The double-sed hit (`255bb`) — fixing:
Load still 122 — staying with light work: agent smoke test + the extra-report script.
Agent builds and answers. Now verifying the T02 path end-to-end using a known T02-firing probe input (dev material, allowed):
Part A confirmed end-to-end. Checking tree cleanliness and M3 runner usage while waiting on load:
Ledger's 14 insertions are another agent's — I'll only append. Load is 133, so launching the pilot backgrounded (it self-gates on load ≤60 before each step):
The EXACT loop asserts 255's text — T02 needs its 255b expectation:
M1 generator validated (228 rows: 171 changed + 57 unchanged; T46 collapses 5→1 as designed). Pilot check:
Delta map good (48 lines: 1×A + 47×B). Now waiting on the pilot — polling at intervals:
Pilot is moving (M2 done, M4 in progress). Checking M2 pilot output:
M2 pilot matches 255's per-suite counts (48/42/25/43, GATE clean). Waiting for the rest:
Now writing PASSMARKS.md:
Seal 21/21 OK. Appending ledger lines (append-only):
M1 sealed (228 rows, sha `1740e0b9…`). Launching registered runs (self-gating):
Panel done once (244 rows, 0 empty, 0 errors). Mechanical changes files now:
All runs complete. Writing RESULTS.md:
**Verdict: PASS on every mark I score (M2, M4, M5, M6, M7), exactly as predicted in P255b.1–P255b.9.** Full exp PASS still needs the director's M1+M3 grades. No sealed file changed after the seal (both seals re-verified OK after all runs).

## Marks table (integer counts)

| Mark | Verdict | Counts |
|---|---|---|
| M1 grammar | director grades | 228 rows (171 changed + 57 unchanged), seed 2550923, sealed |
| M2 suites | PASS | 162 reply-only moves (rt136 48, rt143 42, sessions152 25, bench 47 = 4+37+5+1); 0 verdict, 0 status, 0 store, 0 write; GATE clean; 162/162 predicted ids (0 missing, 0 unpredicted); no-gate 45/45 |
| M3 panel runner | runner done, not judged here | panel run ONCE: 30 convs, 244 rows, 0 empty, 0 errors; 244 compared, 153 changed, 0 unexplained, 0 store, 0 missing |
| M4 probes | PASS | 38 changed, 38 same-meaning (20 T02 incl. all 8 ex-flagged probes), 0 worse, 0 store |
| M5 smoke | PASS | diffs only .agent/.config/.label/.seconds; 0 bad |
| M6 dialogs | PASS | 17 changes exact (6 T02 new text + 11 carryover), 0 ghosts, 0 dup fails, 0 bad writes, vs saved and same-session |
| M7 latency | PASS | 2.285 vs 2.293 ms, delta +0.008 ms (bar +2.0); n 624+624 |
| S1 | n/a | no scorer change |
| Extra 255b-vs-255 | PASS | 26 diffs, all Part A, 0 unexpected |

Paths + sha256: `artifacts/claude-fixedtext255b-20260923/fixedtext.jsonl` = `1740e0b96f6062acd2b655f46f4359224277509774d874abcb2c83537ff019a4`; M3 changes `artifacts/claude-fixedtext255b-20260923/m3-reg/changes-255b-vs-138m.jsonl` = `81c6f393350dce7d3b7d80d79fb0747ae0d08e1e17ebf1fd9a87b9ff320a63c5`.

## Every move, miss, deviation
- Per part: M2 52 [A] + 0 [B] + 110 [carry]; no-gate 37 [A] + 0 [B]; M4 20 [A] + 0 [B] + 18 [carry]; M6 6 [A] + 0 [B] + 11 [carry]; M3 62 [A] + 0 [B] + 91 [carry]. Part B (zero-count) lines occur 0 times in all live runs — Part B is proven by unit tests (60 templates + 519 sweep renders, 0 failures) and the M1 zero-case renders.
- Misses: 0 everywhere. Unexplained moves/differences: 0. Store changes: 0. The ~1-in-800 flake never appeared (registered runs matched the pilot id-for-id).
- Unit tests at seal: 60 templates, 519 renders, 0 failures; T02 anchors old and new both (yes,yes,yes,yes,no).
- Deviations (all pre-seal, in PASSMARKS): 228-guard install-at-import; rt143 base from same-session 138m run; base rows under artifacts; single-text templates rendered once (171 changed renders); bench prose corrected 43→47 (4+37+5+1); T04 keeps 255's text. Post-seal deviations: none. Panel run exactly once, never read item by item, never quoted, nothing graded here.

## What it means (plain high-school English)
- Both of 255's dishonest wordings are fixed: the confused-question reply no longer says "I don't know that" when the answer is in the notebook — it honestly says it didn't understand and asks you to rephrase; and no reply ever says "zero" for a count again.
- Nothing else moved: zero wrong answers added or removed, nothing stored differently, same speed.

## What it doesn't mean
- Not better at answering (0 verdict changes anywhere) — only the wording of canned replies changed.
- The 153 changed conversation turns carry no correctness/grammar grades here — the judges never ran.
- M1 is not passed here — the director grades the 228 renders separately.

PUSH: artifacts/claude-fixedtext255b-20260923 scripts/claude_fix255b_text.py scripts/claude_fix255b_test.py scripts/claude_loop255b_agent.py scripts/claude_255b_* artifacts/fable-predictions-ledger.md
