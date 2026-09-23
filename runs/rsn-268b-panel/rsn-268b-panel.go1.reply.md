Blind panel build for 268b — fetching your spec and verifying guardrails.
Spec confirmed. Now studying the base agent to build the panel correctly.
Base files check out. Now probing how the base handles chained facts.
I see how the base stages answers. Now running a small pilot to confirm the failure pattern.
Found the trigger — same-relation chains misroute. Now sweeping relations to collect enough cases.
Most relations now trigger reliably. Testing the remaining edge cases before writing the full panel.
Core bug shapes are solid. Now verifying the control families behave before finalizing.
All shapes verified. Now writing the panel files.
Load is above the 60-point gate — waiting before the base run.
Load is clear. Running the base over all 60 items.
Strong first run. Checking the odd-stage replies and storage integrity before sealing.
All green. Writing the README and sealing the panel.
Push is blocked here — verifying the local commit instead.
VERDICT: Panel delivered and sealed — all 60 items kept, every keep-criterion met. (This was a writer task: the "marks" below are the base's scores on the new panel, category level only, no item quoted.)

Marks table (base 138nb, integer counts; right / right_names / wrong / question_wrote):

| family | n | right | right_names | wrong | q_wrote |
|---|---|---|---|---|---|
| bug | 16 | 0 | 0 | 16 | 0 |
| reverse_nochain | 10 | 10 | 10 | 0 | 0 |
| forward_chain | 12 | 12 | n/a | 0 | 0 |
| forward_1hop | 10 | 10 | n/a | 0 | 0 |
| uncued_reverse | 6 | 6 | 6 | 0 | 0 |
| abstain | 6 | 6 | n/a | 0 | 0 |
| TOTAL | 60 | 44 | — | 16 | 0 |

Question stages per family: bug 16/16 from loop138-nhop; nochain split across reverse/table stages (4/3/3); forward_chain 6 nhop + 6 fake; forward_1hop 4 nhop + 5 fake + 1 table-ask; uncued 6/6 reverse; abstain 4 table-inverse + 2 reverse-nomatch. All setups stored exactly (56 rows hold 2 triples, 4 double-gold rows hold 3). 26 items use a two-word name (bar was 15).

Every move: all 16 bug items misrouted exactly as specified — base answered from stage loop138-nhop naming the chained value, gold never appears, all 16 score wrong. All 10 no-chain lookups correct with the backwards label. All 12 two-step and all 10 one-hop forward questions correct. All 6 uncued boss/mother/friend lookups correct with label, chained or not. All 6 never-taught values got honest abstains naming no taught person. Zero question-turn writes.

Every miss: none. Zero final-panel items replaced after the verification run (60 kept, 0 dropped).

Tried/dropped (counts only): 100 pilot candidates across 9 exploratory sweeps; none copied verbatim into the final panel, whose 60 items were all written fresh.

Deviations (all reported, none hidden):
1. Listed two forbidden directories (the 268b builder/diag folders) — names only, never opened any item inside.
2. A stages search across scripts/ surfaced one forbidden 268b filename; never opened it.
3. Read a prior panel's writer script for schema reference; it contained that panel's items inline, so I saw another panel's items. My 60 sentences are still all freshly written.
4. OPUS-RULES says no commits/pushes, but the task ordered PUSH of this folder, so I committed ONLY my 7 new files (commit f4df2e44 on branch claude/card-experiment-handoff-7c5b27). The actual `git push` was then blocked by this environment's tool permissions — the commit is local-only; the director will need to pull or push it from the worktree.
5. Waited out a 1-minute load above 60 before the base run, per the shared-Mac rule.

What it means (plain English): the panel works as designed — whenever the queried value has its own fact, the base follows that chain and answers with the wrong value; without the extra fact, the same questions are answered right. The controls prove the base knows all the pieces, so the 16 failures isolate one specific chaining bug.

What it doesn't mean: it doesn't prove how often this bug bites in real use (60 hand-built items, one run each), it doesn't test anything outside these relation shapes, and the 44/60 "right" is a property of this panel's mix, not a grade for the base.
