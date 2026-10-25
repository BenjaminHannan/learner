# Deviations from the INVENT-1 "Pick 1" build plan

Source of truth for the pre-registration is `mechanism/INVENT-1.md`, "Pick 1". Everything here is deliberate or a forced consequence of
building it; the pass marks, arms, metrics and stop rules are unchanged. Items 1-3 are the three required deviations.

## Required deviations

1. **All Claude text is generated up front (container, Message Batches); the GPU jobs never call the API.** Kaggle jobs cannot get the key.
   - Models: `claude-sonnet-5-5` for the persona and the request texts, `claude-haiku-5-5` for phrasings (env var `LEARNER_ANTHROPIC_API_KEY`; the key is never printed or shipped).
   - The user simulator on the GPU is deterministic code (`user_sim.py`). An answer to an ASK and a correction are triggered by code (slot mismatch vs the persona)
     and use pre-generated phrasings: 3 answer + 3 correction phrasings per slot, 2 pre-written chosen-side questions per slot (naming the slot with the true value and the
     most likely wrong one, order varied), 8 fact paraphrases per slot and per background fact. "Annoyed" replies are a fixed prefix list (`config.ANNOY_PREFIX`).
   - Grading of eval ASKs to slot IDs is done in the container after the outputs are pulled: Haiku Batches job, Sonnet regrade of 60 for kappa (`grade.py`).
   - Because of this, "Haiku 5.5 user sim, 2 Batches rounds per day" is replaced by code + frozen phrasings; the Batches spend shifts from "user sim 10 rounds" to the pre-generation.
2. **The full ab_ob_b4_nb sleep recipe is not re-implemented** (the recipe code was not found by name; `sleepb.py` is a large script tied to the names/dream pipeline). The shared part, identical in
   every trained arm and not under test, is: SFT on fact sentences made from Ben's answers/corrections (4 pre-generated paraphrases each per night, plus the day's 8 background facts)
   + corrected-action SFT on tagged regret turns, LoRA r16 / alpha 32 on q,k,v,o,gate,up,down, KL anchor (0.1 x KL(base || LoRA) on one of 100 pre-generated general prompts per optimizer step),
   5 nights, the adapter carried from night to night (fresh AdamW + cosine LR each night, lr 1e-4, a fixed number of optimizer steps per night, same in all arms).
   Only the 15% slice differs between arms. `compute_ledger.py` counts token-passes (trained token = 3, reference-forward token = 1; the anchor teacher forward counts 1) and
   `build_night_data.py` / `night_train.py` assert equality within 5% (the next night is refused otherwise; actual units are checked against the plan).
   There is no "dream" or "names re-read" stage; the seed changes LoRA init and data order only. "Cut dream and re-read counts equally" is realised by `ASKONCE_NIGHT_SCALE`.
3. **Two Kaggle jobs.** Job 1 = base K2 day logs for days 1-5 (deterministic sim in the loop, shared by all arms) + eval of arm P. Job 2 = nights + eval for A+, B, B-sft; seed 1 on GPU0, seed 2 on GPU1
   (one process per lane, `CUDA_VISIBLE_DEVICES`). Between them, in the container: tagger (rule pass + optional Haiku Batches pass), oracle labels, tagger precision/recall report, `build_night_data.py`.
   Arm P is deterministic (greedy, no training), so it is evaluated once.

## Other deviations / choices (all arms affected equally)

- **File name:** `requests_gen.py`, not `requests.py` (a module named `requests` shadows the HTTP library).
- **Request gold is built by code, text by Sonnet.** Code fixes each item's tool, slots and literals (so the gold is exact and the composition is exactly the prereg's);
  Sonnet only writes the natural message; code rejects texts that miss the reference word, leak a value, or omit a literal, and re-requests them (up to 4 Batches rounds).
- **Tools carry only slot-bearing args** (send_email(to), draft_email(to), create_event(attendees, duration_min), move_event(event_id), open_file(path), share_file(path, with)); no subject/body/dates.
  The checker compares tool name + those args after NFKC / case / list-order normalisation. The prereg's "date" slots are not in its persona list and are not used.
- **Lookup block.** For an underspecified request the prompt carries a `[Lookup]` block listing the candidate values for the referenced slot (what a directory search would return).
  Fully specified requests carry none. This is a cue available identically to all arms.
- **Slot memory** is rebuilt at the START of each day from the diary of earlier days and is fixed during the day (batching). Eval prompts use the memory of days 1-5. Entries are Q/A and correction lines only (not background facts).
- **Single-slot requests only** (a request needs at most one slot). Days 1-5: 20 underspecified (each of the 40 training+silent slots 2-3 times) + 20 fully specified per day.
- **Silent slots:** 5 of the 40 training slots are never corrected by sim-Ben; the 20 silent-wrong eval items are 4 per silent slot. Right move on them = exact ACT or an ASK naming the slot.
- **Knowable items** whose slot never got into the diary (the model guessed right every time) are flagged `knowable_effective=false`; the pass marks use all 80, the flag is reported.
- **Tagger sees only diary-visible fields** (text, logged lookup refs, logged memory). The slot of an event is the lookup reference; the corrected action in the SFT/chosen sides is taken from the request gold
  (a real pipeline would derive it from Ben's correction text). Annoyance pairs show the already-known answer in [Memory] (inserted from the earlier diary entry if retrieval missed it).
- **Fact recall** is closed-book (no memory in the prompt) on 60 slot + 40 background questions; the report gives the taught subset and the all-100 rate.
- **Oracle:** regret = first move ACT with a wrong, correctable slot value; annoyance = an ASK on a fully specified request or about a slot Ben already answered/corrected on an earlier day;
  an ask-then-wrong-act is a `copy_error`, not a regret.
- **Generation** is batched HF `generate` (left padding, bs 8, halves on OOM); vLLM was not tried (not installable here, and the HF path is the fallback the brief requires).
- **Day-log sampling** T=0.7 with a fixed per-day seed; eval is greedy.
- **Unverified on real K2 here (no GPU / no K2 weights in the container):** fp16 numerics, memory on a T4, speed, `trust_remote_code` loading on Kaggle's transformers version, batched generate with K2's cache.

## Late changes (sizing and data)

- The shared fact part is repeated `repeat` times per night. It is auto-chosen (cap 20) so typical pairs fit in the 15% slice. Override with ASKONCE_REPEAT.
- Default optimiser steps per night is 30 (ASKONCE_OPT_STEPS).
- Under the scripted sim only about 3-11 pairs per night exist, so statistical power is limited. Real K2 logs may differ.
- Persona split clashes (new-slot key words appearing in train slots) are repaired by swapping with a clash-free train slot of the same kind.
- Extras (extra request fields) are used in training on only 4 paths.

## Review fixes (before launch)

- **Regret events whose [Memory] already shows the answer are dropped from the slice for ALL arms.** The chosen side 'ASK ...' was built from the original prompt; in a full-scale scripted run every regret pair on nights 3-5
  had `memory_has_answer = True`, which would train B to ask in exactly the knowable case marks 3 and 4 penalise. That is a copy failure (like the oracle's `copy_error`), not 'should have asked'.
  `night_material` tests `memory_has_answer(orig_user.split('[Lookup]')[0], slot)`; such events give no pair, no chosen-SFT, no top-up item and no top-up facts (so A+ and B-sft lose them too).
  The shared corrected-action SFT on tagged regret turns is unchanged (identical in all arms). The count per night is in `plan.json` (`n_regret_dropped_memory_has_answer`) and in the report. Fewer pairs remain, so power is lower.
- **Leakage scan widened** (`leakscan.py`, run by `phrasings.py` before freezing, by `tests/test_askonce.py`, and over the night files in `build_night_data`). It scans the SYSTEM prompts, every rendered day 1-5 prompt including [Lookup], gold actions,
  the answers / corrections / questions / paraphrases of train and silent slots, the 40 background facts and their paraphrases, and the 100 anchor prompts, for each held-out slot's key token, reference phrase, long reference words, candidate values and candidate names.
  It found 'Sam', 'Mom', 'grandma', 'grandmother', 'orthodontist', 'driving', and also 'study', 'debate', 'planning', 'lab', 'concert', 'birthday', 'pizza' (all in labels or facts of OTHER slots). No new-slot value (address, path, event id) leaked.
  Fixed by hand-editing the frozen text with `fix_leaks.py` (deterministic regex renames, no API call): e.g. contact_21 "Ana Rivera (Sam's mom)" -> "(Theo's aunt)" with address theo.rivera.aunt@, meeting_09 "little brother Sam" -> "Theo",
  meeting_02 "for Mom" -> "for Aunt Rae" and "Orthodontist adjustment" -> "Braces adjustment", contact_19 "(study group)" -> "(book club)", "debate" -> "forensics", "Garcia's Pizza" -> "Garcia's Grill", "lab report due" -> "write-up due",
  "Band concert travel permission" -> "Band trip ...", "Grandma's landlord" -> "Nana's landlord", fact_18 grandma(mother) -> nana, fact_27 birthday -> date of birth, fact_32 orthodontist -> braces doctor, fact_39 driving -> behind-the-wheel,
  one anchor prompt ("how to study for" -> "how to prepare for") and the SYSTEM example ("lab results" -> "test results"). Only wrong-candidate labels/values of non-held-out slots changed, never a gold value; `requests.jsonl` is unchanged.
  `persona.json` and `phrasings.json` were re-frozen (new sha256 files). Some edited paraphrases read a little stiffly ("the date of Ben's date of birth"); they are identical across arms. The scan now reports 0 hits and `ACCEPTED` in `leakscan.py` is empty.
  Not covered: text the model itself writes on day logs (its own questions in memory lines); `build_night_data` records any such hit in `plan.json -> leak_hits_in_night_files` and warns.
- **The B slice is not a fixed 15%.** `auto_repeat` sizes the shared part on the median night, so the real B slice share is below 15% on most nights (8.9-14.6% in the full-scale scripted run) and a night can drop pairs (night 3 dropped 5 of 8).
  It is equal across arms; the report prints the share and the pairs used per night.
- **Pass-mark wording choices.** Mark 2's ask rate on fully specified requests pools H_full + R_full (the prereg names Split R only). Mark 3 pools H_know + R_know. Mark 2's accuracy part pools all of Split R. Marks use all 80 items per seed even when `knowable_effective` is false.
- **B-sft adoption rule coded.** Marks 1-4 are a function of the arm; B-sft is tested against A+. adopt = B-sft if it meets marks 1-4, else B if all five marks hold, else none. The report also prints a slot-clustered bootstrap CI for B - A+ on new ambiguity,
  `knowable_effective` counts, the tagger label-noise flag (precision < 0.8), the per-night DPO margin / anchor KL, and the slice shares. An arm skipped by the job 2 deadline is reported as missing (the report stops with a clear message if A+ or B is missing).
- **fp16 safeguards.** K2's checkpoint is bf16 and runs in fp16 on the T4. `run_night` raises on any non-finite SFT/DPO loss or anchor KL and when GradScaler skipped more than 20% of the steps. Job 1 and job 2 check that one forward gives finite logits after loading.
  Job 1 aborts after day 1 if more than 50% of first moves are OTHER (unparseable). The pilot records and asserts sft_loss, anchor_kl, skipped_steps and peak_mem_gb (< 14 GB), and projects from the largest planned night plus the measured eval time.
- **Budget caps.** Lane deadlines are 1.2 h (job 1) and 2.5 h (job 2, which also skips an arm that cannot finish by 95% of that). Packages are pinned (transformers 5.20.2, peft 0.21.2; a failed pip install aborts). Models load straight to the GPU (`device_map`).
- **Gate after job 1.** `build_night_data` (CLI) stops if fewer than 5 regret+annoyance events per night were tagged on average (`--min-events`, `--force` to override), the same threshold as the prereg's Step 0.
- **Grader.** `grade.api_map` re-requests a chunk whose JSON does not parse (3 rounds) and raises if it still fails, instead of grading those ASKs as wrong.
- **Not changed:** `add_hf_token_note` in `job_common.py` is still never called (the Kaggle box removes the API keys from the environment anyway).
