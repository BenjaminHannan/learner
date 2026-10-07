# Data pool plan (roadmap stage 8b), written Oct 6, ~10 PM ET

Status: plan and measurements only. No pool has been built, nothing was trained, no GPU used. Labels: **shown** = measured here
(script and result file named); **suggested** = my estimate or recommendation; **untested** = not run.
Unit: LFM2.5 tokenizer tokens ("word pieces"; rows measured with the pinned tokenizer, web text by FineWeb's own `token_count`,
which is within 1.1% of the LFM count on 2,400 docs, shown).

## 1. Answer in four lines

1. **Targets can be reached.** 60M / 190M / 600M unique tokens: our generators plus the 1.2B teacher can carry the 60M rung almost
   alone (90% own text); the 190M and 600M rungs need free web text for 62% and 84% of the tokens (suggested mix, section 4).
2. **Web set: FineWeb-Edu `sample-10BT`** (ODC-By, human-written, 14 shards, 755M tokens per shard, shown). One shard is 21 s to download.
   Filter by reading grade, because it is hard text (median grade 13.2, shown): grade <= 12 keeps 34% of tokens, grade <= 10 keeps 12%.
   Slices needed: 0.02 shard (60M rung), 0.5 shard (190M), 2 shards (600M).
3. **Our own generators do not run out of unique rows but do run out of variety** (shown): millions of unique rows, but only ~1.7M
   digit-shape-unique skills rows, and English passages collapse to ~19k skeletons per 60k draws. So the plan counts only a capped
   amount of generator text per rung and lets web text grow the rest.
4. **The teacher cannot feed the token budget.** 18,300 kept rows/PC hour as run (32,000 clean), but the rows are short (18.9 tokens):
   ~0.35M tokens/h as run, ~0.6M clean. It adds breadth, not volume (section 5).

13-gram check: built and tested (4 tests). Result: 0 hits in TEACH (148,694 passages); one full web shard (726,000 docs) had
**7 documents, 45 windows** hit; the three true held-out English sets have 0 overlap with GEN and TEACH (shown, section 6).
Protected panels (GOLD-PRIVATE, reserved, blind) are NOT yet cleared: I did not open them (section 6).

## 2. What our own generators can make before repeats (shown; scripts in `data_pool/measure/`, results in `data_pool/results/`)

**Skills curriculum** (`skills_curriculum`, 34 train families; draws are train-clean items only, 400,000 draws per family):

| measure | value |
|---|---|
| unique prompts | 3.93M rows (4.84M kept draws) = 338M chars = ~108M tokens (3.13 chars/token, 26.9 tokens/row) |
| unique after masking digits ("shape-unique") | 1.70M rows = ~46M tokens |
| families already repeating (> 5% duplicate draws) | 12: copy_word 67k unique, letter_ops 86k, digits_parity 100k (231 shapes), arith_bare 129k, div_exact 71k, seq_next 63k (1.4k shapes), seq_cycle 179k, prop_eval 42k, verify_claim 199k (231 shapes), backward_solve 68k, distance_units 97k, percent_rate 71k. Together 1.17M rows. |
| open families | 22; birthday-collision capacity estimates run from 1.4M (object_track) to > 1e9 (cipher_map, chain_ops, group_induct, table_*, story_chain3, word_filter) |

So row-level uniqueness is not the limit up to ~100M tokens; digit-and-name variety is. Families with few digit-shapes at 400k draws ("the same problem with new numbers"): group_induct 77, digits_parity 231, verify_claim 231, odd_one_out 308, backward_solve 462, compare_numbers 769, list_stats 923, fewshot_number_rule 1,009, arith_bare 1,078, seq_next 1,592.

**English generator** (`gen_english`, 12 kinds, 300,000 draws): 299,677 distinct passages (duplicate draws 0.1%; event_ordering the only
family with real repeats, 2.4% at 50k, est. capacity ~1M). 6-kind version: 298,755 distinct. Skeleton count (names and pool words masked,
60,000 draws): **18,947** across 12 kinds, still rising for event_ordering, agent_action and descriptive_reference, flat at 12 for `feeling_state`
and 190 for `two_simple_relations_combined`. So thousands of distinct sentence shapes, not millions. (A mask built from pool lists can only undercount
skeletons that differ in words I did not mask, so treat 19k as a lower bound; shown for the masked count only.)

**Existing stock** (tokens, shown): skills 200k rows 5.4M; TEACH 171,940 rows 3.25M; GEN 200,000 rows 5.69M; total ~14.3M (roadmap estimated ~12M).
The 60M rung therefore needs +46M, 190M needs +176M, 600M needs +586M.

## 3. Web set and slice sizes

- **Pick:** `HuggingFaceFW/fineweb-edu`, config `sample-10BT`, shards in file order (`sample/10BT/000_00000.parquet` first). ODC-By licence (credit it). Human-written
  web pages; its quality filter was a classifier trained on Llama-3-70B labels (a judge, not Claude, and it only selects, never writes text). Keep int_score >= 3 (already all rows, shown).
- **Not used:** Cosmopedia, SmolLM-corpus synthetic parts, TinyStories (written by models; against "no Claude/new teacher text" in spirit, and not human-written).
- **Shard 0 measured end to end** (726,000 docs, 754.9M tokens, shown, `measure/web_shard_stats.py`, summary `results/web_shard0_summary.json`): int_score 3: 87%, 4: 13%; reading grade quantiles 5/25/50/75/95% = 8.6 / 11.2 / 13.2 / 15.5 / 19.4.

| filter | docs kept | tokens kept per shard |
|---|---|---|
| grade <= 10 ("plain") | 13.5% | 90.0M (11.9%) |
| grade <= 12 | 34.6% | 256.7M (34.0%) |
| grade <= 14 | 60.0% | 466.3M (61.8%) |

- **Rule (suggested):** bulk web = grade <= 12; the grade <= 10 subset is the plain-English text for talker probe 4b and the talker stage.
- **Nested slices** (documents taken in file order; the small slice is the first part of the bigger one, so bigger rungs only add):

| rung (thinker) | web tokens | raw shards read (grade <= 12) | if grade <= 10 only |
|---|---|---|---|
| 10M | 5.7M (grade <= 12 slice; its grade <= 10 part is the plain subset) | 0.02 | 0.06 |
| 30M | 117M | 0.46 | 1.3 |
| 100M | 503M | 1.96 (2 shards) | 5.6 |

  Plenty of room: 14 shards = 10.6B raw tokens. `data_pool/web_slice.py` builds the slices, applies the 13-gram gate and writes a manifest with hashes (tested on shard 0 with small budgets; **untested at full size**).

## 4. Pool per rung (suggested; tokens, millions, unique)

| source | now | 10M rung (60M) | 30M rung (190M) | 100M rung (600M) |
|---|---|---|---|---|
| skills generator | 5.4 | 36 | 46 | 60 |
| English generator (12 kinds) | 5.7 | 15 | 20 | 30 |
| 1.2B teacher (TEACH rows) | 3.25 | 3.3 | 6.6 | 6.6 |
| web (FineWeb-Edu) | 0 | 5.7 | 117.4 | 503.4 |
| **total** | 14.3 | **60.0** | **190.0** | **600.0** |
| own-text share | 100% | 90% | 38% | 16% |

Why these caps: skills 46M is what 400k draws per family gave in shape-unique tokens (shown); 60M at the 100M rung needs ~1.1M draws per family and
the shape curves are still rising for the open families (untested, verify with a 1.2M-draw run before relying on it). English generator beyond ~15M tokens is mostly repeated structure (section 2),
so its 30M at the top rung is the weakest line in the table. Teacher: capped by what it can write (section 5).

Things the owners of 8a and 8c must decide (I did not):
- **Rung names.** The roadmap's stage 8a uses thinker sizes 3M / 10M / 30M at 20 tokens per trained number and no row more than 4 times = 15M / 50M / 150M unique. Stage 8b's targets (60 / 190 / 600) are for 10M / 30M / 100M. The nested pool serves both: 8a takes prefixes of 15M, 50M, 150M; the 15M and 50M prefixes are all own text, the 150M prefix needs ~80M web.
- **Mix changes with size** (web share goes 10% to 84%), so a bigger rung is "more data and different data". If 8a wants size to be the one change, it can hold the mix fixed at a web-free control up to the 50M prefix (own text reaches 54M) and treat the 150M prefix as a documented mix change.
- **How web text is used.** It is plain text, not questions. Whether the thinker trains on it with a language-model loss, or only the talker does, is the 8a / stage 9 design. The pool only supplies it.

## 5. Teacher rows per PC hour (shown from the PC log, relayed from the Mac session)

Run: 8 rounds, HF backend, RTX 5070 Ti shared for part of the run, batch size unconfirmed (script default 128).

| | items | seconds |
|---|---|---|
| written (8 rounds) | 430,105 | 26,929 |
| answered (self-check, 8 rounds) | 362,889 | 6,840 |
| total | | 33,769 (9.38 h) |

- Kept 171,940 rows of 430,105 written items (40%). **As run: ~18,300 kept rows/PC hour.** Clean-GPU estimate (writes 35.6 items/s, answers 53 items/s, not measured end to end): ~5.3 h, **~32,000 kept rows/hour** (suggested).
- Rows are 18.9 tokens (shown), so ~0.35M tokens/h as run, ~0.6M clean. 100M tokens of teacher text would be ~7 PC days clean, which is why the table caps it at 6.6M (2x TEACH, about 11 clean hours, but see next line).
- TEACH stopped at 171,940, not 200,000: the quota was 3,334 rows per kind over 60 kinds, and every kind ended below 3,500; the later rounds shrink (r0 120,000 items written, r7 22,977). More rows means more kinds (new
  kind definitions) or a bigger per-kind quota with a lower keep rate, not more rounds. So 2x TEACH is a design task (about 60 new kinds), not only compute. Without it, TEACH stays 3.25M tokens.
- `teach_clean` (the version with unsupported yes/no rows dropped) is 94,831 rows, 1.83M tokens.

## 6. 13-gram overlap check (tool: `data_pool/overlap13.py`, 4 tests pass)

How it works: lower-cased words, punctuation dropped. Panel text of >= 13 words contributes every 13-word window, 8 to 12 words contributes the whole text, under 8 words is ignored. A pool document that
shares any hashed window is dropped whole. The index and report hold hashes, counts and document ids only. `index` reads only the text fields named in the spec (passages, paraphrases, questions, prompts) and **refuses** any
path or name containing gold-private, reserved or blind. No answer field was read; answers are not in the index (a test greps the index bytes for a planted answer).

Panels checked (550,139 hashes; `data_pool/panels/README.md`): English eval R3, R5, R6, GEN-HELDOUT-R4; skills dev 40-per-cell and 200-per-cell (the 40-per-cell build reproduces `FULL-BUILD-MANIFEST-200k-seed1.json` hashes, shown); ARC-Easy test question stems; GSM8K test questions; bAbI test passages and questions.

| scanned | result |
|---|---|
| TEACH passages (148,694) | **0** hits, all panels |
| teach_clean (92,147) | 0 |
| GEN passages (100,017) | 296 hit **GEN-HELDOUT-R4 only** (that set shares GEN's own name and noun pools by design, "read, not judged"); 0 against R3, R5, R6, ARC, GSM8K, bAbI |
| skills train 200,000 prompts | 21,830 hit the skills dev panels (11%, almost all 13-word template frames in the same family: prop_eval 5,027, object_track 3,888, state_update 2,222, rule_apply 1,665, distance_units 1,537, ...); 0 against English, ARC, GSM8K, bAbI |
| FineWeb-Edu shard 0 (726,000 docs, 755M tokens) | **7 docs, 45 windows** (0.001%) |
| FineWeb-Edu random 2,400 docs | 0 |

Reading it: for **web text and teacher text the check is a hard gate** (any hit drops the document) and it is essentially free. For **generator rows** the skills hits are by construction (dev is the same generator with one shift held out) and the
English hits are the intentionally shared GEN-HELDOUT set. Dropping them would remove 11% of skills rows and bias away from long-prompt families, so my suggestion is: generator rows rely on the existing hold-out splits, and the 13-gram result is reported, not gated. The
8a/8c owners can overrule this.

**Not yet cleared:** GOLD-PRIVATE-v1.json and every reserved or blind panel. I did not open them. Their owner (custom reader/talker thread for 8a marks, or whoever holds GOLD) runs `overlap13.py index` on their side and gives back only the .npz of hashes; `merge` adds it; the 7 hit documents and any new ones are dropped by the slice builder. The pool must not be used for training until that merge is done.

## 7. MiMo-V2.6 RL environments (Ben's 9:09 PM ET suggestion)

What they are (shown from the dataset card and files, `XiaomiMiMo/MiMo-V2.6-RL-oss`): 7,780 tasks, **Apache-2.0** (the weights are MIT), 7.76 GB, 41,292 files. Five groups, all **agentic** (an agent works in a Docker image with tools, files and a checker):

| group | tasks | what a task is | verifier |
|---|---|---|---|
| code | 2,698 | a (often Chinese) GitHub-issue style problem statement inside a real open-source repo image | executable tests |
| cyber | 1,000 | a fuzzer crash report; reproduce the vulnerability | rule checks |
| general | 989 | long office or forensic job with fake company tool servers, databases, PDFs, spreadsheets | rubric items judged **by an LLM** (`method: "llm"`) |
| webdev | 2,093 | "build me this web page", in many languages | visual grading |
| music | 1,000 | write a piece in ABC notation to a spec (mostly Chinese) | rule checks |

Human or model written? **Not stated on the card.** Signs say model-assisted: the code statements use a fixed "Problem Statement / Expected outcomes" template, the general tasks sit on invented tool servers and databases (`mimoagent/general_agent`), the music prompts are templated from a tag, BPM and meter table, and the grading is partly by an LLM. I cannot prove authorship, so treat as **model-written and model-judged**.

Fit: **not usable in the pool, and I did not include them.** (1) They are model-written, which Ben's rules exclude ("no new teacher", "no Claude text", and these come from a large model). (2) They are not small checkable questions: each needs a container, tools and long multi-step work, far beyond a 10M to 100M thinker, and most prompts are Chinese, Arabic or code, not plain English. (3) Only the cyber prompts (8.6 words) and music (67 words) are small, and neither is a skill we train. 13-gram check on all five prompt sets against every panel: **0 hits** (7,780 prompts; `data_pool/results/mimo_*`). Possible later use (untested, not for this pool): the idea of tiered, mostly-executable verifiers (tests and rule checks first, an LLM judge last) is a good model for our own C2 and C5 tasks, and the Craftax or Minecraft rungs may want agentic RL environments, where the MiMo harness (`github.com/XiaomiMiMo/verl`) is a reference to read, not data to train on.

## 8. What would prove this plan wrong

- Pool cannot reach 190M unique: **no**, web alone gives 0.46 shard of 14 (shown), so it passes on count.
- The thing that would actually bite: the generators' variety. If an 8a diagnostic ("a quarter of the unique data scores within 1 point of full data") passes, then variety, not size, is the limit and the generator lines in section 4 are overstated; the web share should rise and the generator share fall.
- A hit from the not-yet-merged protected panels: drop those documents; if more than 0.1% of a slice is dropped, re-draw the slice from the next shard.

## 9. Next steps (each one change, CPU first)

1. (Panels' owners) hash GOLD-PRIVATE / reserved / blind text with `index` and share only the .npz; merge; re-run `scan` on shard 0. Pass: 0 windows left in any kept document.
2. Run `web_slice.py` on shard 0 and shard 1 on the PC or Mac CPU (about 25 min per shard at 550 docs/s with 4 cores); pass: manifests hash-stable on a re-run; rung-10 slice is a prefix of rung-30. Proved wrong: any nested-prefix violation.
3. 1.2M-draw skills yield run to check the 60M generator line (pass: 60M shape-unique tokens at <= 10% duplicates).
4. Decide whether to pay for TEACH 2x (about 60 new kinds); until then the teacher line stays 3.3M.

Files: `data_pool/` on branch `claude/data-pool-8b`: `PLAN.md`, `overlap13.py`, `web_slice.py`, `measure/`, `results/`, `panels/`, `tests/`.

## 10. Update Oct 7 (8a spec sealed): what was built
- **Web slices** (FineWeb-Edu shard 0, grade <= 12, panel-checked against the current hash index, 0 documents hit): `rung3` 12.4M, `rung10` 37.2M, `rung30` 117.8M GPT-2 tokens (62% of the 8a pools 20M / 60M / 190M), nested (checked: rung3 is a prefix of rung10 is a prefix of rung30). 95 exact duplicates dropped, 224,832 too hard, 48,920 quality. Manifest `data_pool/built/web_slices_8a_MANIFEST.json`; file `/mnt/project-files/data-pool/built/web_slices_8a.tgz` (sha256 686dd25c...).
- **Own text** (`gen_own_text.py`, 72.0M LFM tokens, 12 existing English kinds + 34 skills families + all 171,940 TEACH rows, no new kinds or teacher): every row has `rung` and `pos`; prefixes by tokens: 7.6M (rung 3), 22.8M (rung 10), 72.0M (rung 30), same mix in each (skills 65%, English 31%, TEACH 4.5%). Exact duplicates 0%. **Digit/name-shape duplicates: 20.5% / 23.2% / 25.7%** (arithmetic-style families repeat shapes with new numbers; this is the variety limit from section 2, not fixable without new kinds). TEACH could not be raised (3.24M tokens, section 5), so its share is 4.5%. Manifest `data_pool/built/own72_MANIFEST.json`; file `/mnt/project-files/data-pool/built/own72.tgz` (sha256 85dc19b3...). Regenerable byte-for-byte with the command in the script header.
- Protected-panel hashes are not merged yet (Ben chose "start now" for 8a; the check must pass before 8c).
