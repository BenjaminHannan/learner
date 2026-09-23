Building your QA checker and blind test panel — starting with rules and specs.
Both jobs are clearer now — the 264 checker slot is already sealed by another agent, so I'll verify without touching it and build the blind 270b panel fresh.
Disk is fine (11 GB free). Writing the canonical `make_panel.py` into the panel folder.
Self-check passed. Now verifying the panel independently and re-reading every item as a careful reader.
VERDICT: 270b blind panel DONE and sealed (100/100 turns, all quotas met, seal 2/2 OK). 264 builder subtask NOT executed: another builder already sealed, ran, and reported it in this worktree, so building again would break the additive-only and run-once rules.

270b panel marks (integer counts, all verified by running the sealed generator):

| Check | Bar | Got | Pass? |
|---|---|---|---|
| Total turns | 100 | 100 | yes |
| casual / casual_q / lower_trap / clean | 40 / 15 / 15 / 30 | 40 / 15 / 15 / 30 | yes |
| ids u270-001..100, family-block order | exact | 100/100 | yes |
| unique turns, exact schema keys | 100/100 | 100/100 | yes |
| casual_q gold = single ASK | 15/15 | 15/15 | yes |
| lower_trap gold = [] | 15/15 | 15/15 | yes |
| casual-family turns all lowercase | 70/70 | 70/70 | yes |
| clean turns capitalised | 30/30 | 30/30 | yes |
| s-ending owners (jamess/iris/tesss/marcuss/...) | >= 6 | 11 | yes |
| casual_q without "?" | >= 5 | 8 | yes |
| pet aliases include species + pet/animal/companion | all | 21/21 | yes |
| every subject/value word-for-word in its turn | all | all | yes |
| banned wordings (spec/task examples) | 0 | 0 | yes |
| deterministic re-run byte-identical, seal OK | 2/2 | 2/2 | yes |

Moves: created artifacts/claude-typepanel270b-20260923/{panel.jsonl, make_panel.py, SEAL.sha256.txt} plus an unsealed helper copy scripts/claude_typepanel270b_make.py. Misses: none on 270b. 264 moves by me: zero by design (see D1).

Deviations:
- D1: 264 slot already occupied (sealed 23 files, registered FAIL in RESULTS.md, ledger P264.1-P264.9 present). I verified its seal read-only: 23/23 OK. I added no 264 files and no P264 ledger lines; duplicates would corrupt the record.
- D2: no git push. OPUS-RULES forbids pushes, and artifacts/ is gitignored anyway; the sealed folder is left in place for the director (PUSH satisfied as files-in-place).
- D3: blindness kept by order. I wrote and sealed 270b before reading any code, results, or other panels. Never opened typepanel270, earpanel257/261/261b/264, or any TEST-ONLY panel; read only the two briefs, earpanel264-spec, and (after sealing) the 261b/264 PASSMARKS+RESULTS as tasked.
- D4: judgment call, disclosed in the generator header: no-apostrophe possessives keep raw stems in gold (e.g. subject "jamess"), which the scorer normalises; this is the only reading that satisfies the word-for-word span rule.
- D5: no heavy compute. Load was ~48-60, disk 11 GB free; panel generation is milliseconds, no GPU/BensPC touched, no secrets printed.

What it means: the 270b test panel is ready for the ear-line builder — 40 casual typo-style facts, 15 casual questions, 15 lowercase traps, 30 clean controls, all fictional names, sealed and reproducible.
What it doesn't mean: it does not grade anything — no arm was run and no scores exist. It also does not change exp 264, which stays a registered FAIL (5 wrong saves, 81/125 recall) on the other builder's sealed run.
