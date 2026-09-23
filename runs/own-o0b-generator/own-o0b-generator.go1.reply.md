Building frame data for the ear — pulling plan and formatting 200k clean rows.
Plan and ground rules are clear — now designing the generator.
Table mapped. Now writing the generator with frame-split design.
Generator drafted — now the independent checker.
The file write truncated mid-list — repairing the tail now.
Two bugs: ASK spans and `my's` rendering. Fixing both.
Now hardening the checker's act cascade to match every template shape.
Good — pilot caught real bugs. Debugging the span re-finder first.
Found it — possessive `'s` merges with names under norm. Mapping apostrophes to space instead.
Binding cue `lives in` isn't a table cue — switching binding to possessive `his/her hometown`.
Fixing `?`-in-text detection and the `So who` / `And...who` edge cases.
Span-finding needs word boundaries (e.g. `son` inside `Orson`). Inspecting the UNCLEAR case too.
Two fixes: whole-word span search in the generator, and safer noise (closer-only doubling, apostrophe-span extension).
Now the noise rewrite.
Span bugs cleared — now just act-classifier edges. Inspecting them.
All four edges understood. Applying fixes.
Three causes found: double-space noise vs `startswith`, `Suppose,` comma form, and one bad CHAT pattern. Fixing.
Audited all pattern lists against the cascade. Re-running larger pilot.
Zero mismatches on 20k pilot rows. Optimizing the checker for the full 210k sweep, then sealing.
Scripts frozen. Appending predictions to the ledger.
Ledger sealed. Running full generation.
Generation complete — all shards under 5 MB. Verifying marks.
Pown0b.1 passes on the registered sample. Now full-row integrity sweep.
One leak flag to chase: L1-pool tokens in 494 train rows.
Entity-level picture is clean (only the `Fern` string overlap, never as a person). Checking held-out closers and seal integrity.
All clear. Extracting examples and closing out.
One last full-row check: world surfaces must equal span texts everywhere (the 10k sample only covers a subset).
All green. Writing RESULTS.md.
**Verdict: PASS.** All four marks pass on the registered run; sealed scripts verified unchanged after the seal.

## Marks table (integer counts)

| Mark | Bar | Measured | Result |
|---|---|---|---|
| Pown0b.1 re-deriver mismatches, 10,000 sampled rows (seed 7) | 0 | 0 | PASS |
| Pown0b.2 L2 frame ids in train (all 200,000 rows) | 0 | 0 | PASS |
| Pown0b.3 non-whole-word spans (all 210,000 rows, every span) | 0 | 0 | PASS |
| Pown0b.4 smallest family share of train | ≥6,000 (3%) | 20,000 (10.0%) | PASS |

Extras on all rows: 0 question-schema violations, 0 count≠facts, world-surface==span-text 210,000/210,000, reserved names in train 0 rows, held-out opener/closer slots in train 0 rows, every file <5 MB (max 1,576,636 bytes), 3,597 L1 + 915 L2 frames, ≥44 core patterns per act × 6 relation kinds, L3 empty. PUSH paths ready: `artifacts/claude-own-o0b-20260923` `scripts/claude_own_o0b_gen.py` `scripts/claude_own_o0b_check.py` `artifacts/fable-predictions-ledger.md`.

## Every move
Pre-seal pilots (~10 small gens + checks, all debugging, failures fixed in code); 2×10k pilots at 0/10,000; PASSMARKS written, script hashes snapshotted, Pown0b.1–4 ledger predictions appended, scripts frozen. Registered run 1 (once): full gen — 200k train + 5k L1 + 5k L2. Registered run 2 (once): checker 10k sample, 0 mismatches. Read-only full-row sweeps after. **Misses: 0** in every registered run. No TEST-ONLY panel opened, tuned on, or quoted.

## Deviations (all disclosed in RESULTS.md)
- **D1**: L1 person-name "Fern" occurs in 494 train rows (419 as standalone work value, ~75 inside "Fern Clinic") — never as a person entity (0 owner/person-value hits). Cause D4: ORGS list got `.split()` into single-word fragments.
- **D2**: holdout is frame-id cells (915/4,512 = 20.3%), but surface patterns are drawn independently of idx, so L1/L2 share patterns. Pown0b.2 passes literally (0/200,000); wording-level holdout is follow-up work.
- **D3**: one edit via bash-python instead of the edit tool (pre-seal; seal verified after).
- **D5**: `ls`'d sibling `claude-own-o0a` dir before realising it's out of bounds; opened no file inside.

## What it means
We built a machine that writes 210,000 short made-up chat turns, each with an exact answer key (who, what relationship, what value, telling/asking/checking/supposing/planning/correcting/denying/chatting). A separately written checker re-did every answer from scratch: zero mistakes in 10,000 spot checks, zero bad highlights in all 210,000 rows. A fifth of the templates plus some greetings and names were kept out of training for later testing.

## What it doesn't mean
It doesn't mean a trained ear will read real English — these turns come from fixed templates, not real people. It doesn't mean the held-out split is a hard wording test (D2: patterns overlap). It certifies label-vs-turn agreement only, nothing about memory, reasoning, or answers.
