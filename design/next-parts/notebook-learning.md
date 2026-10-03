# Notebook learning: design for the part after fair scaling

Status: DESIGN ONLY. Nothing here has been run, trained, launched or queued, and nothing here is launch authority.
Written 2026-10-03 (UTC) by the notebook-learning design thread. Execution stays with the single "Premonition execution owner".

Labels used throughout: **shown** (a receipt or file in the repo says so), **suggested** (my reasoning), **untested**.
The small card experiments (`memorylab/`, `premonition/store.py` CardStore, the village model) are kept out of this file.
This design is about the Premonition model: frozen LFM2.5-1.2B, contextual reader, 4-loop ~9M core, 8 prefix vectors.

## 0. What I could and could not read

- Read: branch `claude/premonition-launch-recovery-96c708` at `a163a3163` (pushed state), including `artifacts/cap256-launch/notebook48-v1`, `noteadapt-initial-v2`, `noteadapt-continue40-v1`, `noteadapt-crossroute-v1`, `noteadapt-fresh-NX8-v1`, `scripts/sol_nextdemo_dev_v1.py`, `scripts/sol_nextdemo_runtime_v1.py`, `scripts/cap256_launch/notebook_poc.py`, `scripts/fable_notebook_contract.py`, and the older `design/v3/30-modes/382-memory-store-interface.md` and `design/research/lead-sweep-2026-09-29/angle-6-memory.md`.
- NOT available: `docs/premonition-status/CURRENT.json` and the integrated design document v5. They are not on the pushed branch (only `docs/premonition-recovery/` is). This design is therefore "built against the pushed state, not v5". Section 11 lists what must be reconciled against v5 before anything freezes.
- Not read, by rule: reserved user or blind panels. The consumed worlds (NE8, POC4, NX8) are named only through their published receipts.

## 1. Summary for Ben (plain language)

A notebook is a list of short notes that sits outside the model. The model is only "using" it if its answer changes when the notes change. So the main test is simple: ask the same question twice with two different notebooks, where the right answers differ. A model that learned the answers into its weights would give the same reply both times and get at most one of the two right. A model that reads the notebook can get both right. We call that a **pair**, and the whole design counts pairs.

Earlier work already tried a first version. It showed that the machinery works (notes go in, answers come out, controls are clean), but the model did not read notes on new problems: 0 of 8 fresh cases in every setting, and inline (facts typed into the question) failed just as much as the notebook. So the problem is not only "the notebook". The model has not learned to use new facts at all yet. The plan therefore climbs a ladder, one rung at a time: read one exact fact, read among distractors, read then use the calculator, read a corrected note, write a note, write a correction, then keep a notebook across sessions and as it grows. Each rung has a pass mark fixed before it runs, and a result that would prove the idea wrong.

Two things need your decision (section 10): whether notebook write/read/edit may be added as extra tool calls in the existing calculator-call style (no change to the reader, core or prefix), and what to do only if exact writing through the prefix turns out too hard.

## 2. What already exists (evidence)

| Item | What it is | Label |
|---|---|---|
| `scripts/fable_notebook_contract.py` | Plain-software notebook: append-only JSONL with hash chain, stable entity ids, source tags (taught / proposed / inferred / web-quarantine / sleep-derived), corrections supersede not delete, conflict refusal, idempotent events, fsync plus read-back before "saved", torn-last-line recovery; `--selftest` runs a 30-sequence lifecycle suite and a naive last-write-wins dict must fail it | shown (file; I did not run it) |
| `design/v3/30-modes/382-memory-store-interface.md` | Older village-stack store: `remember()` / `recall(k, sources)` with cited ids, MiniLM retriever, verifier before stating | shown (draft spec, older stack) |
| Sleep rules (git log: slp-360/361/368/369) | Sleep cannot write to the main notebook (write lock, scrap layer, byte-exact restore) | shown (commit messages) |
| Runtime notebook channel (`sol_nextdemo_runtime_v1.py`) | `tokenize(..., max_question=48, max_context=512)` returns separate `ids/valid` and `notebook_ids/mvalid`; `answer(question, context, intervention)` with interventions `full`, `no_notebook`, `zero_final`, `reverse_final`, `reader_only`; truncation prohibited; 4 rounds; decoder sees FinalLatent only | shown (file) |
| Host harness (`sol_nextdemo_dev_v1.py`) | `Session` is a host append-only log (teach / correct / reset). Measures: before, corrected, missing_fact, fresh_multihop. Model-selected writes are recorded as `null`: the model has never chosen a write | shown (file) |
| notebook48-v1 POC | 4 consumed worlds, 2 seeds, full vs no_notebook, 48 native calls, 0 updates. Supported 0/8 vs 0/8, corrected 0/4 vs 0/4, missing-fact abstention 0/4 vs 0/4, both seeds. All 48 outputs ended in valid EOS. No benefit | shown (RESULTS.md, independent recount) |
| noteadapt-continue40-v1 | Fit on 32 TRAIN cases, 1,280 updates. Native exact+EOS: notebook 24/32 (seed 0), 20/32 (seed 1); inline 32/32, 32/32 | shown |
| noteadapt-crossroute-v1 | Same checkpoints, other placement: every cross condition 1/32 | shown |
| noteadapt-fresh-NX8-v1 | 8 fresh initial-fact worlds, both routes, both seeds: full 0/8, empty 0/8, 0 qualifying pairs. Saved TRAIN pairs: notebook 9/16 and 7/16, inline 16/16 | shown |
| LongMemEval-style research (angle 6) | For big readers, retrieval quality dominates and fancy memory architectures tie plain retrieval once the embedder matches; no number for a 1-2B reader | shown (secondary, unreproduced; second-hand numbers) |

### What the evidence does and does not say

- shown: with this recipe and 32 TRAIN cases, the notebook route fits TRAIN worse than the inline route, and each route is specific to the way it was trained (cross-route 1/32).
- shown: on fresh worlds neither route reads new facts (0/8 each). Because inline fails equally, "the notebook is the problem" is not supported.
- Two plausible explanations, both untested: (a) too little and too narrow training (32 cases, one narrow arithmetic family), so the model memorised cases and learned no reading skill; (b) the combination of reading plus arithmetic is beyond the current core, so reading cannot show up. These predict different things: (a) says exact-lookup with many varied worlds should work; (b) says lookup works but lookup-plus-arithmetic does not. The ladder below separates them by design (rung N1 has no arithmetic; N2 adds it).
- untested: whether 8 prefix vectors can carry an exact short string (a name or a 4-digit code) at all. The "plain 1B failed at copying a grid" note in angle 6 is a different setup, but is a warning.

## 3. What counts as "notebook learning"

Five separate abilities. A result may claim only the ones it measured.

1. **Read**: the answer follows the notebook's contents (including notes the model never saw in training).
2. **Edit-read**: when a later note corrects an earlier one, the answer follows the correction and does not emit the stale value.
3. **Write**: the model itself chooses what to write and writes the exact fact.
4. **Edit-write**: the model itself writes the correction.
5. **Persist and grow**: facts written in one session are used in a later one, and accuracy holds as the notebook grows, with no weight change.

Not claimed by this design: general reasoning over notes, multi-hop chains over many notes, sleep consolidation of notes into weights (that is the sleep part), learned retrieval for notebooks larger than the 512-token window.

## 4. Fit with the current architecture

```
write path:  statement turn -> reader -> 4-loop core -> 8 prefixes -> frozen LM -> text "NOTE{fact}"
             -> HOST validates -> appends event to the log (hash chain, fsync, read-back) -> "saved"
read path:   host renders log -> notebook text (<=512 tokens)  \
             question text (<=48 tokens)                         > contextual reader (query + notebook channels)
                                                                 -> 4-loop core -> 8 prefixes -> frozen LM -> answer / calculator call
tool path:   calculator call -> host runs it -> result is encoded as before -> final answer (unchanged)
```

- **Unchanged**: frozen LM, contextual reader, four loops, eight 2048-d prefixes, the decoder seeing only the prefix plus its own generated history, calculator-return encoding, token IDs/masks/EOS/numeral spans, no truncation, no LM fine-tuning, no causal-mask change.
- **Read is already supported**: the reader has a second input channel for notebook text (`notebook_ids`, `notebook_mask`). Placing the same information inline versus in the notebook is therefore a data placement choice, not an architecture change. This is how rungs N1 to N3 run.
- **Write, edit and the host are new to the model, not to the system**: they use the same generated-text-then-host-acts pattern as calculator calls. The host (not the model) owns durability, hash chain, conflict refusal and supersede semantics via the existing contract. The model proposes; the host validates and writes. Needs Ben's yes (Q1) because it adds tool vocabulary to the trained behaviour.
- **Decoder blindness is the main risk**: the output LM sees neither the question nor the notebook, only the 8 prefixes. Every exact value (name, number) must pass through that bottleneck. This is why N1 starts with the simplest exact values and why N2 scores the calculator call's *arguments* separately from the final answer.
- **Large notebooks**: the window holds 512 notebook tokens. Beyond that, host-side deterministic selection (e.g. BM25 as in `premonition/lookup.py` for the village stack) is the default; learned retrieval is out of scope here. Selection happens before the reader, so it changes no model component. It is a scaling-part question; flagged in section 10 as Q3 for later.
- **Placement choice**: train both placements in one mixed run from the start. The cross-route result (1/32) says single-placement training does not transfer between routes. Mixed training is a data-mixture change; NX8 selected data-mixture/generalization work in general, and choosing mixed placement specifically is this design's own suggestion, not shown.

## 5. The ladder (one change per rung, pass marks fixed now)

Common rules for every rung:
- Two matched seeds per arm; matched parent, initialization, optimizer, question exposure (the English pilot's matching rule).
- Scoring is strict, as in the existing runs: exact accepted text (or numeric) AND an actually emitted terminal EOS. A missing EOS scores wrong.
- Primary unit is the **pair**: one query, byte-identical, with two notebooks that differ in exactly one stated fact, and two different targets. A pair **qualifies** if both members are answered correctly. A model that ignores the notebook, or that has the answers in its weights, produces identical output for both members, so it qualifies on 0 pairs. This is true by construction for a deterministic decoder; I would still verify it on the empty-notebook arm.
- Panel: 32 pairs per rung per evaluation (64 notebooks), fresh, single use. Earlier panels were 4 to 8 worlds; at that size nothing separates from noise.
- Pass marks (**suggested**, to be frozen before any data is drawn): **PASS** = at least 16 of 32 pairs qualify in each seed. **PARTIAL (use shown, not reliable)** = 8 to 15 in each seed. **FAIL** = fewer than 8 in either seed. Reasoning: a true pair rate of 0.25 reaches 16/32 only 0.2% of the time and a true rate of 0.5 reaches it 57% of the time (exact binomial; computed, not run on the model). So PASS is hard to reach by luck, and PARTIAL still rules out "no use" with the control arms.
- Every rung also reports the control table in section 6. A PASS with a failing control is void.
- Each rung lists the single result that would prove the idea wrong at that rung.

### N0. CPU only: format, renderer, host contract (no model, no GPU)

Change: define the English entry grammar, the renderer from log to notebook text, and token budgets; run the existing contract selftest and new tests.
- Entry grammar (suggested): one fact per line, "Subject: relation is value." plus supersede lines "Correction: subject: relation is now value." Raw append-only rendering for N1 to N3 (the model must resolve corrections itself); a resolved "current view" rendering is available only for N4 and for ablations.
- Tests: persistence across process restart; torn last line ignored; duplicate event idempotent; correction supersedes; second differing fact without a correction refused as CONFLICT; "saved" only after read-back; token audit that every rendered notebook is at most 512 tokens and every query at most 47 plus EOS with the actual tokenizer; naive last-write-wins dictionary must fail the edit suite (a test a naive version passes tests nothing).
- Pass: all tests green; the actual-tokenizer audit has zero overflows and zero truncations.
- Wrong if: entity or value strings do not survive tokenization round-trip (the pair design then cannot be scored exactly).

### N1. Read exact facts, no arithmetic (separates explanation (a) from (b))

Change: exact-value lookup from a notebook of 1 to 8 entries, with distractor entries.
- Tasks: "What is Mara's locker code?" with the notebook stating it. Three difficulty bands: 1 entry, 4 entries (same entity type), 8 entries. Answer is a short name or number. Companion missing-fact items: the notebook lacks the fact and the accepted answers are the existing frozen four ("I don't know", "I don't know.", "Not enough information", "Not enough information.").
- Training: mixed placement (inline and notebook), many generated worlds with disjoint entity and value pools from eval, more than one template family. Size to be set by the execution owner from measured throughput; my proposal is on the order of thousands of worlds and at least six template families, with one family fully held out for a secondary transfer readout (**suggested**).
- Primary: pairs, notebook placement. Secondary: held-out family pairs; missing-fact abstention; inline placement for the same information.
- Pass: PASS at the 32-pair rule above on the band with 4 entries, in both seeds.
- Wrong if: even the 1-entry band is below 8 pairs in a seed. Then exact strings cannot cross the prefix bottleneck by ordinary training, and Q2 (section 10) is triggered. Do not proceed to N2.

### N2. Read, then compute with the calculator

Change: the notebook supplies the givens; the model emits a calculator call using them.
- Primary readout: the call's arguments are correct (this isolates reading from arithmetic and from the final-answer step). Secondary: final answer correct. Context (from Ben's execution brief; not re-derived here, and CURRENT.json shows the same pattern per checkpoint, e.g. 11 correct calls but 2 correct finals out of 16): in the eight-checkpoint evaluation, 86 of 128 outputs had a correct calculator call but only 15 had a correct final answer, with 71 correct-call-then-wrong-answer. Those items are consumed and are not reused.
- Pairs: same query, notebooks with one different given.
- Pass: PASS on call-argument pairs in both seeds. Final-answer pairs reported but not gating.
- Wrong if: N1 PASS but call-argument pairs below 8: reading exact facts works but the tool-call route does not use them; look at how the call is composed, not at the notebook.

### N3. Edit-read: the model resolves a correction in the raw log

Change: the log contains an original fact and a later correction line.
- Pairs: (log with correction, target = new value) versus (log without correction, target = old value), same query.
- Scored: new value emitted, old value not emitted.
- Controls inside the rung: **distractor-after-correction** (an unrelated note appended after the correction, target unchanged) guards the shortcut "use the last number"; **correction-for-other-entity** (target stays the old value) guards "any correction wins".
- Pass: PASS on edit pairs in both seeds AND both guard controls at least 24 of 32 correct in both seeds.
- Wrong if: the guard controls fail while edit pairs pass: the model learned a position shortcut, not editing.

### N4. Write and edit-write: the model chooses the writes

Change: the model emits `NOTE{...}` (and `CORRECT{...}`) as text; the host validates and appends. First time `model_selected_correct_writes` and `model_selected_wrong_writes` become real numbers instead of `null`.
- Inputs: short statement turns (some contain a fact worth keeping, some are chit-chat, some contain a correction).
- Scored on the host's log: exact fact written (normalized equality with the gold entry), no junk writes on chit-chat, no duplicate or contradictory writes, correct supersede on corrections. Write error taxonomy: wrong value, wrong entity, missing write, invented fact, duplicate.
- End-to-end: model-written notebook then model reads it, versus the same questions with an oracle (host) writer, versus no notebook.
- Pass: exact-write at least 80% on fact turns, junk writes at most 10% on chit-chat, and end-to-end pair PASS (16/32) in both seeds using the model's own notebook.
- Wrong if: exact write rate under 50% in either seed while reading (N1) passes: writing through the prefix is the bottleneck. This triggers Q2.

### N5. Persist and grow

Change: sessions separated by a real process restart, and notebooks from 1 to the 512-token ceiling, with no weight change between sessions.
- Persistence: fact written in session A, asked in session B after restart; the log hash chain verified on load.
- Growth curve: pair rate at 4, 8, 16, 32 entries (stopping at the token cap). "Improves with use" here means: accuracy does not collapse as entries accumulate and no retraining is needed.
- Pass: the persistence pair rate is within 4 pairs of the N1 value in both seeds, and the 16-entry band is at least half of the 4-entry band. Fixed in advance (suggested).
- Wrong if: pair rate falls below 8 at 16 entries: the window or distractors dominate, which is then a retrieval-selection question for the scaling part.

## 6. Controls and ablations (what rules out "it is in the weights")

| Control | What changes | Prediction if the notebook is really used | If it fails |
|---|---|---|---|
| Fresh worlds | Entity and value pools disjoint from all TRAIN data by hash and n-gram collision checks | Weights cannot hold these facts | Contamination: void the panel |
| Counterfactual pair | Same query bytes, notebooks differ by one fact | Both answers correct (qualify) | A weights-only model qualifies on 0 |
| `no_notebook` | Notebook emptied (`intervention=no_notebook`, exists) | Near 0 pairs; supported correct near 0 | If high: the query alone determines the answer, so the panel is leaky |
| Swapped notebook | Notebook from another pair-world of the same family | Answer follows the swapped notebook, not the world's own value | Own-value reproduction means a query prior or memorisation |
| `pre_correction` | Notebook before the correction (exists) | Answer returns to the old value | Same answer means the correction is not what is read |
| Entity rename | Rename entity consistently in query and notebook | Answer unchanged in structure | Failing means string memorisation |
| Weights-only arm (train-time) | Same training facts delivered as plain QA, no notebook slot, same updates | Does well on seen worlds, 0 pairs on fresh worlds, cannot be edited without more training | Shows what the notebook adds: new facts and edits with zero updates |
| Inline placement | Same information in the question | Reference; notebook need not beat it (the existing rule) | Notebook far below inline means a route-specific fit, as in crossroute |
| Oracle writer (N4 only) | Host writes the gold entry | Upper bound for N4 end-to-end | Gap = write errors |

Sleep link (suggested, not part of this design): sleep must keep the main notebook read-only (existing slp rules), and the notebook doubles as the replay source for verified experience, which is the next part.

## 7. Fresh evaluation, independently checked

- Authored by a writer different from the checker. A script (extending `numeric_episodes` validation and `verify_numeric_semantics.py` in notebook48-v1) checks bounds, byte-identical queries inside a pair, exactly one changed fact, distinct targets unequal to every stated value, and that the notebook contains the givens and no answer or intermediate. A separate reviewer checks wording and semantics. Pins with SHA-256 for notes, targets, verification receipt, and verifier source.
- Actual-tokenizer audit before any model call: query at most 47 plus EOS, notebook at most 512, answer within the cap. Truncation prohibited.
- Collision audit against all prior TRAIN, EXPERIENCE, consumed (NE8, POC4, NX8) and exclusion metadata, by metadata and hashes only. Never open reserved user or blind panels.
- Whole worlds are reserved at the moment of first use, all variants together, and are never reused for training, tuning or a second "fresh" claim.
- Gold targets live only in the scorer; the model receives only the query, the notebook text and the disclosed intervention.
- The scorer is recounted by an independent script that makes zero model calls (the pattern used for notebook48 and NX8).
- Arithmetic and word-problem semantics are checked by someone other than the author (project rule on numerical data and Luna problems).
- Independence caveat that applies to every earlier panel as well: collision checks cover literal and numeric-masked matches, not semantic family independence. Do not claim more.

## 8. Resources and sequencing

- Everything in N0 is CPU. Rungs N1 to N5 need GPU; none is requested. Sizing from receipts, for planning only: an earlier 1,152-update fit took about 270 s per arm on the RTX 5070 Ti, and native generation ran about 1.1 to 1.9 calls per second including model loads. A 32-pair rung is 64 notebooks, plus controls roughly 5 to 6 views each (about 350 calls per seed, **estimate**), which is minutes of generation. Training size is the open cost and is set from the English pilot's measured throughput.
- Order: after the English pilot result (this rung's parents should be the pilot's matched parents or its best arm; **suggested**) and after fair scaling fixes the size comparison. The notebook rungs reuse the English passage-and-question format with the passage moved to the notebook slot.
- No new spending authority is assumed. Storage and free-space rules are unchanged.
- Maintain one queue and one owner. This document adds nothing to the queue.

## 9. Risks

- The prefix bottleneck may not carry exact strings. Detection: N1 1-entry band, N4 exact-write rate.
- A position shortcut ("last number wins"). Detection: N3 guard controls.
- Placement specialisation as seen in crossroute. Mitigation: mixed-placement training; detection: inline-versus-notebook gap on held-out families.
- Small panels. Mitigation: 32 pairs per rung; PARTIAL band stated.
- Generated worlds may be too templated. Mitigation: at least six families; one family held out.
- Write rights: only the model's `NOTE`/`CORRECT` calls and the user path may write to the main notebook; sleep, creative and teacher paths are read-only. The existing contract already encodes this.

## 10. Questions for Ben (defaults chosen under his autonomy note; he can overrule)

- **Q0 (default: yes, revised by section 11c)**: may the notebook runtime use the integrated design's per-loop calculator protocol (N2 depends on it)?
- **Q1 (default: yes, proceed on this design)**: May notebook write and edit be added as extra tool calls in the same generated-text-then-host-acts style as calculator calls? No change to the reader, core, loops or prefix, no LM fine-tuning.
- **Q2 (ask only if N1 or N4 fails the bottleneck test)**: If exact values cannot be written through the prefix by normal training, may the model choose a span of the heard text and the host copy it exactly (a pointer write)? This is close to the "forced answer copying" the brief forbids without approval, so it is not assumed.
- **Q3 (later, scaling part)**: For notebooks over 512 tokens, may the host select entries with deterministic BM25 before the reader?

## 11. Reconciliation against CURRENT.json (pushed 2026-10-03, commit 42552d9ee)

Checked: `docs/premonition-status/CURRENT.json` only. Integrated design v5, the ROOT handoff and the English TRAIN bank are not pushed yet (waiting on Ben to force-add past .gitignore), so the items below stay open.
- shown: status was `PREMONITION_GPU_HOLD_CPU_HANDOFF_READY_NO_NATIVE_DISPATCH` at the file's timestamp; Ben has since freed the GPU. Nothing here changes the queue.
- shown: English TRAIN bank `english_training_candidates_v3.json` (sha256 f2f5cce3...) is TRAIN-only; native token, worker and checkpoint qualification is still pending. Notebook rungs must wait for that qualification and may use the bank only as TRAIN material, never as fresh evaluation.
- shown: the approved curriculum entry has `interface_changes_authorized: false`. Adding notebook write/edit tool calls is an interface change. Ben's later autonomy note covers sensible rule-bending, but this one changes trained behaviour, so I keep it as Q1 with a default (see section 10).
- shown: CURRENT.json records `pointer_interface_supports_reverse_text_order` (source and stdlib evidence only, not learned performance). A pointer interface therefore already exists in the platform, which makes Q2 cheaper than I assumed. Whether it can copy notebook spans is untested.
- shown: current native outputs are scored with "all four loops". Ben has since lifted the extra-reasoning-depth rule, so the notebook rungs do not need to fix the loop count; a loop-count comparison can be added as one separate change. Still keep loops equal across arms inside a rung.
- Still to reconcile when v5 lands: the English input/output caps (brief: 64 and 48), the notebook-channel caps (runtime file: query 47 + EOS, notebook 512), the matched-parent checkpoints, whether the pilot reader keeps a notebook channel, and the exclusions list in section 7.

## 11b. Amendments from the Opus architecture review (supersede the text above where they differ)

Reviewer read the pushed files and found the following. Labels are the reviewer's, checked by me where noted.

Architecture
- shown (reviewer, from `sol_nextdemo_runtime_v1.py`): `Runtime.answer()` makes one generation pass with no tool loop and no tool-result encoding; "calculator" does not appear in the sol_nextdemo, sol_cloud or cap256 scripts. So rung N2 needs a calculator loop joined to this runtime. **New Q0 (default: yes, build it as a harness loop using the existing calculator-return encoding)**; N2 is gated on Q0 and is not started before it is built and CPU-tested.
- shown: the reader encodes the question and the notebook separately (two passes of the same reader); the core attends to the notebook memory (`fixed4(core, query, memo, notebook_mask=...)`). Read the section 4 diagram as: reader(question) gives the query; reader(notebook) gives the memo; the core attends to the memo.
- shown: generation is capped at 32 new tokens (`observe_generation`). Every answer, `NOTE{...}` and `CORRECT{...}` must fit in 32 tokens including EOS; N0's token audit must check this.
- Q1 is narrowed to **write and edit** tool calls. Reading stays host-rendered, so there is no model-chosen read (a model-chosen read would be a reasoning change).

Pair design
- Put the target line at a random position in each notebook; add a control that changes only a distractor's value (the answer must not move).
- Shared-distractor leak: in each pair member, put the other member's target value on a distractor line for a different entity, so copying from the wrong entity fails one member.
- Determinism check: run every input twice and require identical output. (Under `no_notebook` the two members share an input, so equal outputs prove nothing by themselves.)
- Value pools: entity-to-value pairings are fresh, but value tokens may appear in training; report a **novel-value slice** separately, so a failure on never-seen strings is not mistaken for a failure to read.
- Checker rules are per rung. The "target unequal to every stated value, no answer in the notebook" rule belongs to arithmetic rungs only (N2); for lookup rungs (N1, N3) the target is a stated value and the checker verifies that it is the stated value of the asked entity and relation.

Pass marks
- Classify by the **lower** of the two seeds. Seeds that fall in different bands are PARTIAL at best.
- Power note (computed): at a true pair rate of 0.5, P(at least 16 of 32) is 0.57 per seed and about 0.32 for both seeds, so PASS is conservative, and a miss near the line is inconclusive, not a failure. At a true rate of 0.25 it is 0.002.
- A script computes simple shortcut scores per panel (first value, last value, a random value in the notebook); each band must beat them, and PARTIAL's "8 pairs" is not itself evidence of use without the controls.
- N1: the "wrong if" is confounded (too little training, or the notebook channel). Add a copy probe (the value in the question) and an inline 1-entry arm. Blame the prefix bottleneck only if both fail.
- N3: pair "correction to entity X" against "correction to entity Y" on the same query, so members differ by one fact, matching the common rule. The earlier "with versus without a correction line" pairing becomes a secondary control.
- N4: give denominators (32 fact turns, 32 chit-chat turns, 16 correction turns per seed). Add a forced-write sub-arm (the host says "write now") so value errors and when-to-write errors are counted separately. Between 50% and 80% exact writes is PARTIAL and is reported by sub-arm.
- N5: test persistence with logs the model wrote itself on the same panel, not only host bytes. Make growth marks mutually exclusive: PASS if the 16-entry pair count is at least half the 4-entry count and at least 8; otherwise report FAIL, with no overlap with the PARTIAL rule.

Other
- Loop count: now free to vary (Ben lifted the extra-depth rule); see section 11.

## 11c. Check against integrated design v6 working draft (commit c5cfd9176)

File read: `artifacts/cap256-launch/contextual-input-compare-v1/FRESH-TERMINAL-EVAL-PREPARATION-v1/DESIGN-WORKING-v6/Premonition integrated model design.docx` (the coordinator called it v5; the folder says DESIGN-WORKING-v6). Read by text search for notebook, calculator, interface and loop passages, not line by line.

Agrees with this design
- shown: the doc says to prove notebook retrieval, corrections, multi-hop use and missing-information abstention **before** reliable writing. N1 to N3 come before N4 here for the same reason; N4 stays gated on them.
- shown: the doc wants matched inline versus notebook renderings, a consistent renderer between training and evaluation, a small notebook given in full as the starting design, and original-wording records with provenance and version history. Same as sections 4 to 6.
- shown: both-correct pair scores are already the doc's metric (matched ADD/SUB pairs, zero in every endpoint); it also warns that matching removes one shortcut, not every lexical one. That is why the pair design here adds the position and distractor controls.
- shown: "missing evidence means cannot determine from the notebook"; measure unnecessary abstention on answerable cases too.

Conflicts and changes this forces
1. **Calculator protocol (changes N2 and Q0).** The doc's implemented protocol is typed requests chosen by the reasoner on each of the four loops (an allowed operation plus ordered operand pointers into the input, at most one call per loop, host executes, result consumed by the next update). It is not generated text, and it rejects forced calculator copying. So N2 must use that protocol; my "build a harness loop" default is replaced by: **use the existing per-loop calculator protocol and read the call's operand pointers as the notebook-reading readout.** The runtime file I reviewed (`sol_nextdemo_runtime_v1.py`) does not contain it, so which code path carries it must be confirmed with the execution owner before N2 is scheduled. Q0 becomes: does the notebook runtime get the same per-loop calculator protocol (default yes, since it is the doc's own design).
2. **Write interface (changes N4 and Q1/Q2).** I proposed model-generated `NOTE{...}` text. The doc handles tool use as typed requests with pointers and treats learned reference selection as a literature option, not an approved repair, and requires separate decisions for new interfaces. Cleaner fit: N4 uses a **typed write request** (action write or supersede, plus pointer span(s) into the heard turn), validated and appended by the host. That makes Q2's pointer-write the main path, not a fallback. Ben's autonomy note covers choosing it, but it is an interface change, so it stays labelled as a decision with the pointer-write as the default, and the generated-text write is kept as the comparison arm. Untested which works.
3. **Multi-hop was out of scope; the doc puts it in the notebook proof.** Add **N3b**: two-hop reads (the doc's "Aster is in Room 4, Room 4 is on the second floor"), the same chain after a correction (old answer must not survive), and the chain with the second premise missing (answer is "the notebook does not establish it"). Same pair rule, same lower-seed classification. Pass mark kept at 16 of 32 pairs for the two-hop and correction items and at least 24 of 32 on the missing-premise items; fixed before data is drawn.
4. **Oracle versus actual retrieval.** The doc asks for matched inline, oracle-selected, and retriever-selected conditions. This design gives the model the whole small notebook (oracle selection). The retriever-selected condition is added to N5 once the notebook exceeds the window.
5. **Fresh panels.** The doc says reserved numerical-pair coverage is unknown and that bounded 16-question panels are the current practice. My 32-pair panels are larger than anything authored so far; the authoring and independent-check cost has to be agreed with the parent before N1 is scheduled, and N1 may start at 16 pairs per seed with classification by the lower seed (power is lower; say so in the result).
6. **Loops and size.** The doc still describes four loops and says architecture and reasoning-method changes need a separate decision, while Ben has lifted the loop and size rules for scaling. No effect on the notebook rungs; they inherit whatever configuration scaling selects.

## 11d. Calculator code path (read from branch claude/critical-thinking-data-128-outputs, `pipeline_code/`)

Read only `calculator_tools.py` and `calculator_runtime_depth_compare.py` (top docstrings and the begin/registry code). Nothing in that folder's answer key was opened or is used as a panel.
- shown: the typed request is real code. `build_registry` makes literal references with offsets into the original question string; `execute_integer_call` runs at most one bounded integer call per loop; four loops exactly; two pointer heads pick left and right operands.
- shown: references must lie inside the **original query tokens** and the registry holds at most 8 literals (`literal reference must belong to original query tokens`).
- shown: in this runtime the core's notebook channel is **already used**: `memo` is a fixed 8-slot block holding four value/status pairs for tool results, passed as `notebook_mask=ones((1,8))`. The 512-token text notebook of the `sol_nextdemo` runtime is a different channel use in a different core family.
- Consequence (suggested): as built, a calculator call cannot point at numbers that live in a notebook, and notebook text and tool-result slots would compete for the same memo channel. So N2 needs one of two code changes, both untested: (A) put notebook numerals into the query string, which erases the notebook-versus-inline difference N2 is meant to test; or (B) extend the registry so literals can come from notebook tokens, and keep tool-result slots separate from the notebook text (8 reserved positions plus up to 512 notebook positions). B is the design's choice. It is an interface change, so it is a decision with B as the default, and N2 is not scheduled until B exists and passes CPU fixtures.
- The same registry pattern (literal spans with offsets, validated by the host) is the template for N4's typed write request: spans in the heard turn instead of the question.
- N1, N3, N3b and N5 do not depend on the calculator and are unaffected.

## 12. Where this sits

English pilot (current-size capability) then fair scaling, then **notebook learning (this)**, then sleep replay from verified experience. The creative prototype and later learned-stopping/compressed-notes work remain after. This part produces the things sleep replay needs: a trustworthy log of exact, correctable, source-tagged facts and a measured reader and writer.
