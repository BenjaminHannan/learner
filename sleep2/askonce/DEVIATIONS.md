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
