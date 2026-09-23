Writing your blind panel — fetching specs and checking the machine.
Load is high but workable and disk is fine. Now studying the base agent harness.
The base harness pattern is clear. Now probing which sentence forms the base actually stores.
Core forms mapped. Now checking relation coverage, broken-chain abstains, and statement controls.
All teach shapes verified. Now building the 80-item panel.
Panel validates. Now running the full base pass.
All setups store cleanly. Now writing the sealed scorer.
Scorer confirms the base picture. Writing the README and seal.
VERDICT: Panel delivered and sealed. 80/80 items built to spec, every setup stores on the base, base run complete, scorer sealed. Folder `artifacts/claude-chainpanel266-20260923/` holds the 7 required files; `shasum -c` passes on all 5 sealed files.

Base (138m) marks table, integer counts (right / wrong / abstain / other / question_wrote):

| family | n | right | wrong | abstain | other | wrote |
|---|--:|--:|--:|--:|--:|--:|
| chain_verb | 30 | 8 | 0 | 0 | 22 | 0 |
| chain_verb_three | 6 | 1 | 0 | 0 | 5 | 0 |
| chain_possessive | 10 | 10 | 0 | 0 | 0 | 0 |
| broken_chain | 12 | 12 | 0 | 0 | 0 | 0 |
| plain_control | 14 | 11 | 0 | 0 | 3 | 0 |
| statement_control | 8 | 8 | 0 | 0 | 0 | 0 |
| TOTAL | 80 | 50 | 0 | 0 | 30 | 0 |

Every move and miss (category level, no item text): all 10 possessive chains right; all 12 broken chains honest abstains; all 8 statements wrote nothing; 11 of 14 plain controls right. Of the 30 misses: 20 verb-chain misses plus 5 three-link misses are "did not understand" replies; 2 verb-chain misses are my-subject city questions the base does not parse; 3 plain misses are one two-word-name live question and two when-birthday questions the base does not parse. Zero wrong answers and zero question-writes anywhere on the base.

Spec compliance counts: 6 verb forms x 5 items each (max 6 per form met); 12 distinct first-link relations (min 8 met); 8 my-subject verb items met; 6 first-link-missing plus 6 second-link-missing/different broken items met; 20 two-word-name items met (minimum exactly); setups 1-3 turns each; all names fictional.

Deviations (all in my own unsealed files, pre-seal): (1) first draft of my two scripts computed a doubled path and wrote into a stray `artifacts/artifacts/` dir; fixed the two path lines and removed the stray dir. (2) Per the spec's replace rule, 3 first-draft setups that the base would not store were replaced and the panel/base rows regenerated: one my-subject relation the base rejects, and two verb teaches with two-word subjects the base rejects (possessive teaches accept two-word subjects; relation teaches accept them too). (3) `run_base.py` needed one path-line fix for the same reason as (1). No other agent's file, no sealed file, no archive/premonition/learnlab file, and no forbidden 266/relation-table/chat-demo/panel file was ever opened. Disk stayed above 16 GB free; one process at a time; CPU only.

What it means in plain English: the base is honest (never guesses, never writes on statements) and already handles possessive chains, so the panel can tell a real reasoning gain apart from luck. What it doesn't mean: the base failing verb chains does not prove the new agent will pass them; only the builders' sealed scorer run decides that.
