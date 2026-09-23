Building ability-list fix 280 — reproducing the failure, then piloting the cap.
Failure confirmed in the probe rows — now tracing where the self-reply comes from.
Base behavior mapped. Now checking for a panel-writer schema and the suite tooling.
No panel schema on file — scorer will need to be schema-flexible. Checking the mixin pattern to mirror.
Pattern clear. Starting step 1: formal repro on 260, saved to the new artifacts dir.
Repro saved — failure confirmed live on 260. Moving to dev dialogs.
Ability scores are in. Verifying the single-phrasing subsets before finalizing the table.
Subsets confirm the table. Reading the install mechanics to mirror them.
Now building the fix — the sealed ability table plus the outermost mixin.
280 agent live. Piloting dev on 280 and scoring.
Dev pilot clean. Now scanning frozen suites for predicted moves.
Load is 75 — waiting on heavy runs. Using the time to study the suitediff comparator.
Now the flexible panel runner (schema unknown until the writer seals).
Piloting the panel toolchain on a mock panel (own wording, both shapes).
Toolchain verified. Checking load for the heavy suite pilot.
Load clear. Running the full suite pilot (same code path as the registered run, into pilot/).
Exactly the 3 predicted moves. Fixing the rt136 base-dir to match 260's method.
All pilots pass. Checking what 260 sealed to mirror the seal surface.
Seal surface mapped. Writing predictions file and PASSMARKS.
Seal 15/15 OK. Appending ledger predictions.
Sealed and ledgered. Entering the panel wait (poll every 2 min).
Panel sealed and present. Verifying my seal is untouched, then running the registered suites.
14/15 sealed files intact (only the scorer changed — driver-only fix, diff on record). Running the blind panel once per arm.
Schema mapped (36 dialogs; labels match the spec counts). Fixing the loader — driver-only, agent untouched.
Toolchain fixed and backward-compatible. Archiving the void attempt, then the one valid panel run.
Verdict determined. Writing RESULTS.md.
**Verdict: FAIL (M1b 9/12; everything else PASS).** The honest ability list works exactly as predicted except 3 panel general wordings outside the closed list still get the clarify line.

**Marks table (integer counts)**

| mark | 280 | 260 arm | bar | verdict |
|---|---|---|---|---|
| M1a panel: replies claiming unsupported abilities | 0 | 7 | 0 on 280 | PASS |
| M1b panel: general items listing ≥3 abilities | 9/12 | — | every item | FAIL |
| M3 panel: write diffs 280 vs 260 | 0 | — | 0 | PASS |
| M3 panel: question/self turns with writes on 280 | 0 | — | 0 | PASS |
| M2 sessions152 (180 units) | 3 reply-only moves, all predicted | — | exactly predicted, GATE clean | PASS |
| M2 rt136 (145 units) | 0 field diffs | — | 0 | PASS |
| M2 rt143 (124 rows) | 0 moved | — | 0 | PASS |
| M2 bench (4×200) | 0 moved | — | 0 | PASS |
| Verifier probes (98 + 12) | 0 changes | — | 0 | PASS |
| Dev same-as-base (72 ability turns) | 0 diffs | — | — | — |

**Every move (9 panel + 3 suite, all toward the honest text, 0 against)**
- Panel: 9 general dialogs now get the sealed `CAN280` text (6 table-backed abilities each); 7 of them replace old-sheet replies that trip the claim scan on 260. canyou 20/20: 0 forbidden, 0 moves. Control 4/4: 0 moves.
- Suites: S2-casual-friends#1, S3-teachers-correction#0, S4-pets-identity#9 — old reply → `CAN280`, verdict UNHELPFUL→UNHELPFUL, stored identical, 0 writes.

**Every miss**
- G06, G11, G12: 280 reply byte-identical to 260's clarify line (keyword count 0, no false claim either arm, 0 writes). Mechanism: general wordings outside the closed 16-form set that also don't emit the old sheet on 260, so neither layer fires. This was the registered known limit and P280.3's predicted likeliest failure.

**Deviations**
1. Scorer-only fix after seal: rt136 check read the vs-138j GATE string (NOT clean on either arm — 260's own summary shows the identical 16 inherited moves); now compares vs-base labels to 260's (identical ± timing) plus 0 field diffs. Only the scorer re-ran.
2. Runner+scorer fix after seal: the blind panel is flat turn rows, not setup/turn items — first pass mapped everything to id `?` (VOID; outputs kept in `pilot/void-attempt/`). Added shared `panel_group` (group by `dialog_id`, scored turn = last row; `gold` never read). Panel then ran ONCE per arm correctly (36 dialogs). Only keys/counts/labels inspected; item text never read, nothing tuned.
3. No schema gate (brief gave no exact schema; registered in PASSMARKS pre-seal). Seal now 12/15 (3 fixed drivers differ); agent, config, cases, PASSMARKS untouched. Ledger P280.1–P280.5 appended; P280.3's PASS lean was wrong, failure mode right.

**What it means:** the agent stopped bragging — 9 of 12 ability questions now list only test-proven abilities with the exact wordings that work, the 7 false boasts are gone, and nothing else it does changed (suites move only where predicted, zero new writes).

**What it doesn't mean:** not every phrasing works (3 of 12 still get "I didn't understand" — honest but unhelpful), and the agent learned no new skills — correcting, forgetting and two-step questions behave exactly as before; only the description became truthful.
