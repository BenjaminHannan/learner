# y1t data gate: GATE-PASS (Answering-from-memory thread, scored 2026-09-27 11:09 UTC)

Marks: GATE-data.md (sealed in SEAL-gate.sha256.txt) and GATE-ADDENDUM-1.md (G1b and G4, sealed in SEAL-gate2.sha256.txt),
both fixed before this data existed. Data: glm2/, built as ADDENDUM-3 rule 4 says, with ADDENDUM-4's route filter and
ADDENDUM-5's Luna rows. Seal checks here: SEAL-gate 2 of 2 OK, SEAL-gate2 7 of 7, SEAL-y1t-add4 2 of 2, SEAL-y1t-add5
8 of 8. SEAL-y1t.sha256.txt has 16 of 19 OK: its three lis-320 scripts (seed, GLM, check) have changed since. SEAL-NOTE.md
(17:18 UTC 09-26) records the GLM and check changes; the seed script's current version is the one SEAL-y1t-add5 pins,
and the seeds it makes match the sealed sha256. y1t's BensPC job checks SEAL-y1t-rental.sha256.txt (the other 16).
The lis-320 check version used is named below.

## Verdict
| Check | Bar (sealed) | Result | |
|---|---|---|---|
| G1 as written (code) | at most 5% of twins still contain the value | FAILED on the first-run items (GATE-ADDENDUM-1); on glm2 train: 178 of 888 before G1b, 164 of 874 after | stays FAILED on the record; replaced by G1b |
| G1b (code filter, every twin) | filters, no bar | train twins: 874 of 888 kept (710 clean, 164 name only, 14 dropped for "role word with the name"); dev twins: 145 of 146 kept (122 clean, 23 name only, 1 dropped); no answerable item dropped | applied |
| G2 (blind: the last message asks for the fact) | at least 54 of 60 | 60 of 60 | PASS |
| G3 (blind: earlier messages state the value as the current answer) | at least 54 of 60 | 60 of 60 | PASS |
| G4 (blind: a name-only twin says who the person is) | "yes" on at most 6 of 60 | 3 of 60 | PASS |

**GATE-PASS.** By GATE-ADDENDUM-1, G4 PASS means the name-only twins stay (no drop-name-only step). y1t trains on
glm2/items/ (the G1b-filtered files): 1,762 training items (888 answerable, 874 never-told) and 291 practice-dev
items (146 answerable, 145 never-told). The items step gave 1,776 training items before G1b, above ADDENDUM-2's bar of
1,500 (ADDENDUM-3 rule 6 is not needed).

| file | sha256 |
|---|---|
| glm2/items/items_train.jsonl | 47e2e2955bf085816abcda50fdfc4230d0030cbe72b5d8df4109e704858c79e4 |
| glm2/items/items_dev.jsonl | c0288f2cb7a5b764f974f49d1bfeb5b8ddb0de68e8ce63fffc6cc4d0a3d407e4 |

## How the data was built (glm2/BUILD-glm2.sh; every count below is its printed output)
- Inputs, all from origin/builder-outbox: glm/raw.jsonl (first GLM run), topup/raw_new.jsonl (GLM top-up, 1,440 rows),
  luna/rest3/raw_luna.jsonl (all 315 Luna rows, ca50d8897, sha256 b49327ce...e56e). Seeds regenerated with seed 4027 and
  checked (sha256 42b344fb...0f43).
- split: 2,400 seeds, 645 first-run rows parsed and kept, 1,755 to redo.
- Route filter (ADDENDUM-4): first run 645 kept of 645, GLM top-up 1,440 of 1,440, Luna 315 of 315 (0 empty, 0 marker
  rows, 0 repeated texts in each).
- merge: 645 from the first run + 1,755 redo rows (1,675 parsed) = 2,400 dialogs, one row per dialog. The 80 unparsed
  top-up rows had their one try (ADDENDUM-3 rule 6) and give no items.
- lis-320 check (claude_lis320_check.py, sha256 5a3148be..., main's version since dc2b7f7f7, the same one used for the
  top-up preview and the Luna pilot): 2,400 dialogs, 80 unparsed, 16,816 turns, 14,686 kept, 1,578 dropped.
- y1t items step (claude_y1t_data.py items, seed 4027, sealed ee349fbe...): 1,156 asks kept, 1,034 answerable and 1,034
  never-told items, 61 corrected asks, 122 asks skipped (no current fact); 1,776 train and 292 dev items.
- G1b (claude_y1t_gate2.py filter) on items_train and items_dev, as in the table.
- Python 3.12.3 here, run with -S -B (the scripts use the standard library only). The Mac jobs use 3.12.14.
- Files: glm2/ holds BUILD-glm2.sh, check.json, items_unfiltered/ and items/. raw_merged.jsonl (6.2 MB), kept.jsonl
  (24 MB), drops.jsonl and the three route-filtered raw files are not committed; the script rebuilds them from the
  pushed rows (two preview runs gave identical files). gate/inputs.sha256.txt lists the sha256 of all of them and of
  the scripts, to check a rebuild against.

## How the gate was run
- G2/G3: `claude_y1t_gate.py sample --items glm2/items/items_train.jsonl` (60 answerable items, seed 4034), then
  splits and score. G4: `claude_y1t_gate2.py sample` on the same file (pool 164 name-only twins, 60 drawn, seed 4036),
  then splits and score. Keys: gate_key.json, g4_key.json. Results: gate_result.json, g4_result.json.
- Judges: four fresh blind Opus agents, one per folder (judges/judge_a, judge_b, g4_judges/judge_a, judge_b). Each got a
  copy of only INSTRUCTIONS.md and batch.jsonl in its own randomly named directory and was told to read nothing else, to
  judge every item by reading it (no code deciding labels) and to quote no item. The first line of every prompt said
  never to use WebFetch or any web tool. Their batch files were checked byte-identical to the sampled ones before the
  labels were copied back.
- Both pairs agreed on every item (G2/G3: 60 of 60 on both questions; G4: 60 of 60, both said "yes" on the same 3
  items), so `splits` found 0 disagreements and no third judge was needed.
- This thread did not read any item text for the gate.

## Report only
- Items by writer (training, after G1b): first GLM run 286 answerable and 284 never-told; GLM top-up 479 and 467;
  Luna 123 and 123. Dev: 48/47, 74/74, 24/24.
- G2/G3 sample by writer: first run 26, top-up 24, Luna 10. G4 sample: first run 20, top-up 28, Luna 12. The 3 G4 "yes"
  items: 2 from the first GLM run and 1 from the GLM top-up, none from Luna (too few to compare writers).
- A code count on the 60 G2/G3 items (not a mark): every gold value appears in an earlier message (60 of 60), no
  question contains its own answer (0 of 60), and 46 of 60 last messages contain a question mark (the others are
  requests such as "remind me ...").

## Deviations (disclosed)
- Writer mix: GLM wrote 2,085 dialogs and GPT-6 Luna wrote 315 (ADDENDUM-5, sealed before any Luna call).
- The Luna rows came from three jobs: the pilot (60), y1t-luna-rest2-bash (160 more) and y1t-luna-rest3-bash (the last
  95), each resuming from the previous one's rows with the same runner; one try per dialog, 0 failed calls. An earlier
  job, y1t-luna-rest1-bash, stopped at its running-job check with no Luna call. The old builder job y1t-luna-rest-mac
  never ran a command or made a Luna call; its rows, if it ever made any, would not be used.

## Next
The thread asks the Director to release handoff/held/benspc-y1t.md, repointed at glm2/items on origin/main with these
sha256 values. y1r then runs on the same items.
