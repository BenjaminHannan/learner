# Whole-model roadmap: from today to Minecraft (revised 2026-10-06, size goal; audit corrections 2026-10-09)

Asks:
- Ben, 9:27 PM ET 10-05: "roadmap for the whole model. What progress was made today?"
- Ben, 3:43 PM ET 10-06 (size goal): the shipped model should be "pretty big, at least hundreds of millions of
  parameters", big enough that "scaling up is beneficial", and still in a range "where we can train" on cost.
- Ben, 10:48-10:49 AM ET 10-07, in the architecture page thread (relayed): the thinker should take in more than 9
  letters at a time; it should "loop as many times as it deems necessary" and be "as deep as possible"; and "the
  calculator should be an external tool call that the talker makes", with the reader taking in its output.
- Ben, 1:23 PM ET 10-07, in the no-hard-coding thread (relayed): "I need you to demonstrate scalability with a model
  that is good enough though. do u understand?" Same minute (card): "Start now" on growing before the leak check ends.
- Ben, 2:45 PM ET 10-07 (relayed; now in the project instructions): "everything that you do should be able to be done
  by the model autonomously while it's deployed." Hand code runs only as outside tools the model chooses to call; no
  researcher choices at run time. Section 4.1 lists what still needs a model-driven version.
- Ben, 10:16 AM ET 10-08 (relayed): "It should scale more than a plain model. so from increased parameters, the benefit
  should be more than the plain model. Also, the model should have the gemma embedder as it's main inputting/ecoder [...]
  it should just be in our plans for the finished model. [...] if the reader being good is part of the model, that's
  fine. It's just that the thinker should learn more and be the driving intelligence. You don't have to ban any help from
  the gemma reader. Also, I don't care if you use the fineweb-edu text. [...] For the three cals waiting on me, just do
  what you want".

Versions:
- First version, 9:55 PM ET 10-05. It revised the Oct 3 day plan and "Ben's Model Ideas" (09-30), and is published at
  the Oct 3 page's link: https://claude.ai/artifact/BkhCvfRLpBmrbWrJAWpUdc.
- The night version is kept as `whole-model-roadmap-2026-10-05-night.md`.
- This revision answers the size goal and folds in what Ben decided on Oct 6:
  - EmbeddingGemma 2 may sit inside the model.
  - B2's letter-window reader should go (replaced: Ben chose "Keep" for the small window under Gemma, 9:29 AM ET 10-09).
  - No new teacher model.
  - The bench is parked.
- Morning update, 4:30 AM ET 10-07: the overnight results (B2 confirm on 6 seeds, the reader test, Test B1, Test LR).
- Design update, 11:00 AM ET 10-07 (2c split into 2c1 and 2c2 at 11:50 AM ET): Ben's three design changes (section 1.5), with new tests before growth (2c1, 2c2, 2d)
  and a depth-first 8a.
- Good-enough update, 1:31 PM ET 10-07: 8a gets two "good enough" marks (spec addendum A), may start before the
  protected-panel check, and grows B2 until B3 is ready. 1:40 PM ET: addendum B (enough training, rows that fit, speed
  check first), after Ben's "you can spend the gpu money" (1:27 PM ET). 1:45 PM ET: addendum C moves 8a to the home PC.
- Deploy-rule update, 2:50 PM ET 10-07: Ben's rule recorded (section 4), with the parts that still need a model-driven
  version before ship (section 4.1) and the 8a and 8c rows updated.
- Size-ladder update, 4 AM ET 10-08: the 8a results (3M and 10M rungs, shape probe) and the 30M question
  (`8A-10M-RESULT-2026-10-08.md`).
- Scaling-bar update, 10:30 AM ET 10-08: Ben's new bar (gain more from size than a plain model), the Gemma embedder as
  the finished model's main input, reader help allowed, 30M held, and the next growth test 8a-G
  (`8AG-GEMMA-GROWTH-SPEC-2026-10-08.md`).
- Audit update, 1:15 PM ET 10-09: corrections from the architecture audit (section "Latest: where the plan stands").

Labels:
- **shown**: measured in this repo.
- **suggested**: reasoned from results or papers.
- **untested**: a plan or a guess.
- **proposed**: any pass mark not copied from a sealed spec. It gets sealed in its own spec, by the thread that runs it,
  before any run.

Times are US Eastern (ET).

## Latest: where the plan stands (Fri Oct 9, 1:15 PM ET; audit corrections)

The architecture audit (`/mnt/project-files/architecture/AUDIT-2026-10-09.md`, 12:20 PM ET) checked this roadmap against
Ben's rules and the source of truth (`/mnt/project-files/architecture/FINISHED-MODEL-2026-10-09.md`). Where they disagree,
the source of truth wins. The fixes are made in place below and marked "corrected 10-09" (findings B02-1 to B02-17).
- **Who does what (B02-1, B02-2).** The talker writes only the final answer. After each round a small call writer reads
  the thinker's first control vector and writes a calculator call or nothing. The reply is read as a short new string in
  later rounds; the question is not re-read. One learned stop ends the whole answer, so the talker makes no
  call-or-answer choice. Ben's 10-07 words were "an external tool call that the talker makes"; the built code files the
  call writer under the talker (`tool.py:15`), but it reads the thinker. Shown in T1SDR (6 seeds at 3M).
- **Thinker shape (B02-3, B02-17).** 100M is about 21 blocks at width 512 (97.1M). 30 blocks at 512 would be about
  139M. The whole model is about 397M with the Gemma adapter and the letter window counted.
- **Data (B02-4, B02-5).** No new teacher rows: only the existing 171,940 TEACH rows, our code generators and
  FineWeb-Edu (rule of 10-08). Web text enters as fill-in-the-blank rows, so run-1 teaches reading English, not writing
  it. How the 25M talker learns to write English belongs to Ben's separate "talking from scratch" session.
- **Compute (B02-6).** Mac and PC only; no Vast or other rentals (Ben, 10:43 AM ET 10-09). Rented-GPU costs below are
  history.
- **Size ladder (B02-8, B02-15).** No more 2-seed screens of 2c1, 2c2 or 2d (Ben, 3:27 PM ET 10-08: one big proven run,
  no more little tests). The path is gate G1 first (8a-G with the register fix, 3M and 10M, running on the PC). Then
  B3 climbs its own ladder on the PC: 3M, then 10M with both build groups, then 30M. Each rung is paired with a plain
  model at the same caps. The 100M thinker stays (Ben, 10:49 AM ET 10-09: "Hundred").
- **Reader (B02-7, B02-10).** EGE's 6-seed confirm is in: +2.67 over B2 on 6 of 6 seeds. It missed its zero-round leak
  mark (6.6 against a 3.6 limit); Ben allows reader help (10-08). Ben chose "Keep" for the small letter window under
  Gemma (9:29 AM ET 10-09), which replaces his 10-06 "the letter window should go".
- **Longer inputs (B02-9).** Run-1 trains on inputs up to 2,000 letters (Ben, 9:29 AM ET 10-09; built in B3 group 1,
  `caps_b3.json` max_prompt 2000).
- **Training through the rounds (B02-14).** H1's code back-propagates through every round with checkpointing
  (`tool_h1.py`). The PC fit check decides whether that fits 16 GB at 100M.
- **New kinds (B02-13).** L1 and ST1 replace the hand rewrite of worked steps in B3 group 2, before the big run.
  Learning brand-new kinds from its own checked tries after shipping is not in run-1.
- **The race (B02-11).** Ben's goal is to beat 1-2B models at whole size. Stage 10's race against 350M-600M models is
  our first gate, not his goal; we narrowed it, he did not.
- **Eyes (B02-16).** A distilled eye needs a teacher encoder. Check that against the no-new-teacher rule before vision
  restarts (vision is paused).
- **Open for Ben, not urgent (B01-11).** His bar says "more than the plain model" without naming one. G1 and B3's ladder
  use the plain step model. The plain LLM recipe gained more from size in 8a (+15.8 against +3.8 from 3M to 10M) but
  starts 26 points lower. The 8a-G spec addendum P records this.

## Latest: the size ladder (Thu Oct 8, 4 AM ET)

- **3M rung** (6 seeds, rented 5090s): B2 72.3 pooled-5, so "starts good" (>= 72.0) passed narrowly. Plain step model
  (PT) 66.2, plain LLM 46.6 (shown).
- **10M rung:** B2 72.8, a gain of **+0.5** (95% CI -0.7 to +1.7); PT gained +3.8 and the LLM +15.8 (5 seeds). Mark 1
  (+3.0 per step) fails, so 8a cannot pass with today's B2 (shown). B2 is still ahead of both at 10M (lead over PT 6.1
  -> 2.9).
- **Shape probe** (2 seeds, addendum J): a reader grown to 23 layers was flat (+0.7, -1.5) and broke the letter-code
  questions; a wider B2 was unclear (+1.6, +0.5), slightly ahead of the deep one, far from +3 (shown).
- **Best guess** (suggested): B2 is near 100% where its calculator works and flat on the rule and pattern questions,
  which its fixed ops and one-shot answer writer may not be able to express; the plain models gain there with size.
- **30M is held** (Ben left the call to us, 10:16 AM ET; today's B2 fails his new bar). The two outside-opinion prompts
  are ready (`reviews/gpt-diagnose-b2-no-growth-2026-10-08.md`, `reviews/astra-diagnose-b2-no-growth-2026-10-08.md`).
- **Ben's new bar (10:16 AM ET):** every size step must give our model a bigger gain than the plain model gets. The
  Gemma embedder is the finished model's main input; reader help is allowed, but the thinker must drive. FineWeb-Edu
  text is fine.
- **Next growth test, 8a-G** (`8AG-GEMMA-GROWTH-SPEC-2026-10-08.md`, marks fixed before the build): EGE (B2 with Gemma in
  front) against the plain step model with the same Gemma front, 3M -> 10M, 2-seed screen (about $12) then 6 seeds.
  Pass: our gain minus the plain gain above 0 with CI above 0, and the thinker carries at least half the gain. Our
  prediction (suggested): it stops at the screen, which would point the fix at the thinker (B3), not the reader.
- **8a-G status (2:50 PM ET 10-08):** Vast credit hit $0 mid-screen; one of eight arm-runs finished (Gemma-fronted B2,
  3M seed 400: 72.42, vs 71.59 for the letter-reader B2). Ben (2:39 PM ET): "just use benspc for now". The screen now runs
  on BensPC, sharing the GPU with the reader/talker jobs; about two days of PC time (our guess). Spec addendum B.
  **On hold 3:28 PM ET** (Ben 3:27 PM ET: big money only on one run that demonstrably works, no more little tests; addendum C).
- **Bug, 3:40 PM ET 10-08:** every 8a B2 run (and 8a-G's one finished arm) had 9 register tokens instead of 36 and GEN targets
  cut to 8 letters (`caps.apply` skipped the lazily imported ledger; found by Ben's 8b session, reproduced here). So 8a's fail is
  untested for the B2 as designed. **Gate G1** = 8a-G re-run with the fix, BensPC only, marks unchanged (addendum D); it is the
  one gate of the big-run plan (`/mnt/project-files/big-run/PLAN.md`).
- What it changes: 8c's entry is Ben's bar. B3 must beat the plain model's 3M-to-10M gain before the ship build.

## Next 48 hours (from Wed Oct 7, 4:30 AM ET)

Overnight results (shown; details in section 2):
- The B2 confirm passed PASS-1 on 6 seeds: +20.3 vs the plain transformer and +6.9 vs the step-writing one, ahead on
  6 of 6.
- Every reader without B2's letter window lost to plain B2. EGE, which adds EmbeddingGemma 2 in front of the window,
  gained +1.6 and +2.1 but missed 2 of its 5 marks.
- Test B1 (the teacher's practice) was proved wrong. Test LR failed its marks.

On the PC: the 6-seed EGE confirm (queue 39, seeds 202-207), running since 2:56 AM ET. The custom reader/talker thread
expects it to end about 9 PM to midnight ET. Its result picks the reader for every Phase 3 rung.

On CPU, no GPU needed:
- Seal the marks for the bigger-is-better check (stage 8a). It is also Plan B's next step (Ben chose "wait for web
  text").
- Data pool (8b): the web slices from shards 0-1, the 1.2M-draw generator check, and the protected-panel hashes from
  their owner (now in parallel; they must pass before 8c).
- Write the talker probe spec (stage 4b).
- Write the specs for the two design tests: the calculator as a tool (2c; the architecture thread is designing it) and
  the learned stop (2d).

Decided (Ben, 9:32 AM ET 10-07): wait for web text. No ~100M student runs on the teacher's questions; Plan B's next
result comes from the 8a 10M rung.

The 8a spec is sealed (`8A-SPEC-2026-10-07.md`, PR #50). Ben first chose rented GPUs (1:08 PM ET), then asked for the
home PC (1:35 PM ET; addendum C). The 3M rung starts on the PC after q39, q40 and U0, once the web slices are built and
the 8a code is written. Ben chose "Start now"
(1:23 PM ET), so it does not wait for the protected-panel check, which must pass before 8c. It does not wait for the design tests (2c1, 2c2, 2d), which run at 3.3M on the PC.

## 0. For Ben

- **Size: aim for about 400 million numbers in the shipped model** (suggested). The parts are:
  - EmbeddingGemma 2's text part as the reader: 271M, borrowed and frozen. Every arm that dropped B2's letter window
    lost, so the candidate is EGE (Gemma in front of the window), pending its 6-seed confirm.
  - Our own thinker, grown from 3.3M to about 100M.
  - Our own talker, about 25M.
- **Why that size.** It is the biggest model one training run can reach on your machines:
  - About 6 days of your PC, or about 2.5 days on one rented 5090 for about $30 (no renting now: Ben, 10:43 AM ET 10-09).
  - The next size up (about 650M) costs about 7 weeks of the PC or about $260 per run, too slow to iterate.
  - Game models that worked were in this range: VPT, about 0.5B as reported, crafted diamond tools.
  - Trillion-parameter chat models fail at Minecraft because they never trained on the game, not because they are too
    small (suggested).
- **The catch is data, not size.** All our practice data together is about 570,000 questions, 14.3M word pieces
  (measured by the data-pool plan, PR #47).
  - That feeds a model of only about 2M trained numbers. It is why making the old core 4 times bigger gained just
    +1.9 (PR #18).
  - A 100M thinker needs about 50 times more unique text.
  - Without a new teacher, that text comes from our generators, the 171,940 TEACH rows we already have (no new
    teacher rows, rule of 10-08), and free human-written web text (Ben said yes, 8:57 PM ET 10-06).
  - The data-pool plan (PR #47) shows all three sizes can be fed. Web text is 62% of the 190M pool and 84% of the
    600M pool, because our generators repeat the same question shapes and the teacher writes only short rows.
- **Your three design changes come first (Ben, 10-07; section 1.5).** Each gets a cheap test at today's 3.3M size before
  anything grows:
  - The calculator becomes an outside tool, and the model reads its answer (stage 2c; shown as T1SDR. Corrected 10-09: a call writer reads the thinker and writes the call; the talker writes only the final answer). Ben's bar (11:35 AM
    ET): outside must work just as well as inside, because needing it inside would mean the reader, thinker or talker
    chain is broken at the input or output.
  - The thinker loops until it decides it is done (stage 2d), and grows deep: more blocks, not wider ones (stage 8a).
  - The reader gives the thinker more than 4 letters each side (the architecture thread is researching it). The thinker
    already attends to every letter of the question each round (shown, `custom_io/models/ledger.py`); the window only
    limits what each letter's own state knows before the thinker reads it.
- **How we prove bigger is better before paying for it** (updated 10-09). Gate G1 first: today's model with the Gemma
  front at 3M and 10M, against a plain model with the same front (running on the PC). Then B3, the all-learned design,
  climbs its own ladder on the PC: 3M, then 10M with both build groups, then 30M, each beside a plain model at the same caps.
  - At each step our gain from size must beat the plain model's gain (Ben's bar, 10:16 AM ET 10-08).
  - Only then do we build the 100M version (Ben, 10:49 AM ET 10-09: "Hundred").
- **Where we are (shown).** B2 beats same-size transformers by +20.3 and +6.9 points on held-out skills, ahead on 6 of
  6 seeds. It still scores 0-4% on kinds of question it never practised. The teacher's 171,940 rows did not fix that
  (Test B1 proved wrong): every student learned its own practice by heart and scored about 11% on new kinds.
- **The ladder still has four phases:**
  1. Prove our own brain: confirm, reader, breadth.
  2. Learn like a person: few examples, notebook, sleep, creative only when stuck, an early talking test.
  3. Grow and race: the bigger-is-better check, then the 400M build, then a race against 350M-600M models (our first gate; Ben's goal is 1-2B models).
  4. Senses and worlds: eyes, ears, hands, Craftax, then Minecraft. The Minecraft model is the 400M model plus about
     35M of senses and hands.

## 1. The size goal

### 1.1 Recommendation (suggested)

| part | numbers | trained by us? | note |
|---|---|---|---|
| Reader: EmbeddingGemma 2 text part | 271,002,624 | no (frozen) | Ben's pick (1:10 PM ET 10-06). Window-free arms all lost, so it sits in front of the letter window (EGE; its 6-seed confirm gained +2.67 over B2 on 6 of 6 seeds but missed the zero-round leak mark, 6.6 vs 3.6; Ben kept the window 10-09); 134,217,728 of it is the word table |
| Thinker: B2's looped planner, grown deep | ~100,000,000 | yes, from scratch | 30x today's 3.3M; about 21 blocks at width 512 (97.1M; corrected 10-09: 30 blocks would be about 139M); loops until one learned stop ends it |
| Calculator: exact, outside the thinker | 0 | no learned parts | a tool (Ben, 10-07); a call writer reads the thinker and writes the call, and the reply is read in later rounds (shown, T1SDR; corrected 10-09) |
| Talker: ours, open English | ~25,000,000 | yes, from scratch | writes only the final answer; how it learns English is Ben's separate talking-from-scratch session |
| **Whole model** | **~397,000,000** | about 127M trained | every weight that runs counts (Ben's rule), the Gemma adapter and letter window too (corrected 10-09) |
| Later, for Minecraft: our eye, ear and action head | ~+35,000,000 | yes | eye distilled from a teacher encoder (check against the no-new-teacher rule before vision restarts); ear 0.52M (PR #25) |

The thinker is 80% of what we train but 25% of the whole model, because the reader is borrowed. The lesion checks
(donor state, loops:0) still have to show the thinker decides the answer at every size.

### 1.2 Why this size and not another

| thinker | whole (with EG2 reader) | training word pieces | PC (5070 Ti) | Mac (M1 Pro) | one Vast 5090 |
|---|---|---|---|---|---|
| 3M (today) | ~275M | 0.08B | 0.4 h | 0.3 days | 0.2 h, ~$0.10 |
| 10M | ~284M | 0.25B | 2 h | 1.5 days | 1 h, ~$0.50 |
| 30M | ~308M | 0.75B | 15 h | 10 days | 6 h, ~$3 |
| **100M (recommended)** | **~396M** | **2.5B** | **6 days** | 100 days (no) | **60 h, ~$30** |
| 300M | ~646M | 7.5B | 52 days | no | 22 days, ~$260 |
| 1B | ~1.5B | 25B | 1.6 years | no | ~$2,900 |

How the table was made (our estimate, could be off 2x either way):
- Training math = 6 x (thinker x 8 rounds + talker) x word pieces, plus 2 x 137M x word pieces for the frozen reader's
  forward pass.
- Word pieces = 20 per trained number (the usual compute-optimal rule, suggested).
- Assumed real speeds: PC 25, Mac 1.5 and 5090 60 trillion operations a second, about a third of each chip's
  spec-sheet peak.
- Vast price $0.50 an hour. Live single-5090 verified offers were $0.45-0.50 at 3:45 PM ET; the median was $0.58.
- With 4 rounds instead of 8 (Amazon's looped model found 4 matched 8), the 100M run drops to about 3.3 days of the PC
  or about $16.
- B2's real runs at 3.3M are slower than the math says because small models are overhead-bound. The 10M rung measures
  the real speed.

Reasons:
1. **In Ben's range.** Hundreds of millions in the whole model, with the part we train 30 times bigger than today.
2. **The biggest size we can iterate on.** One run is days on the PC or about $30 rented. One size up is 7 weeks or
   about $260 per run, and every idea would need several runs.
3. **Game models that worked sit here (suggested):**
   - OpenAI's VPT is about 0.5B as reported (arXiv 2206.11795). After fine-tuning it crafted diamond pickaxes in 2.5%
     of 10-minute episodes.
   - Dreamer 4 is 2B and found diamonds in 0.7% of tries (arXiv 2509.24527).
   - Training on the game mattered more than size.
4. **There are rivals to race at this size:** SmolLM2-360M, LFM2-350M and Qwen3-0.6B.

### 1.3 The catch: bigger only helps with more data

- **What we have.** The skills curriculum (200,000 questions), TEACH (171,940 kept rows) and GEN (200,000). Measured by
  the data-pool plan with the real tokenizer: 5.4M + 3.25M + 5.69M = 14.3M word pieces (shown; this roadmap first
  estimated about 12M).
- **How much data can be reused.** A model learns about as well from data seen up to about 4 times as from new data,
  and extra passes after that add little (Muennighoff et al. 2023, "Scaling Data-Constrained Language Models";
  suggested).
- **What that means for size.** Today's data feeds about 50M useful training word pieces, which supports a model of
  about 2M trained numbers. That is B2's size now. It explains why the 4x bigger core gave only +1.9 (PR #18, shown).
- **Unique word pieces each rung needs** (proposed: no row seen more than 4 times):
  - 10M thinker: at least 60M.
  - 30M thinker: at least 190M.
  - 100M thinker: at least 600M.
- **Where it comes from, without a new teacher model (Ben, 3:11 PM ET):**
  1. Our generators. They are code and give unlimited fresh questions in the families we have; new families are new
     code.
  2. The 171,940 TEACH rows the 1.2B teacher already wrote. (Corrected 10-09: this line used to allow more rows from the
     same pipeline; the rule of 10-08 allows no new teacher rows.)
  3. Free human-written web text for plain English, such as FineWeb-Edu. It is needed by the 30M rung and for the
     talker. **Ben said yes** (8:57 PM ET 10-06).
- **The rule stays.** No Claude-written or Claude-judged text.

### 1.3b The data-pool plan (stage 8b, PR #47, CPU only, nothing trained)

Pool per size (millions of unique word pieces; suggested mix from the plan):

| source | now | 10M thinker (60M) | 30M thinker (190M) | 100M thinker (600M) |
|---|---|---|---|---|
| skills generator | 5.4 | 36 | 46 | 60 |
| English generator | 5.7 | 15 | 20 | 30 |
| 1.2B teacher (TEACH) | 3.25 | 3.3 | 6.6 | 6.6 |
| web (FineWeb-Edu) | 0 | 5.7 | 117.4 | 503.4 |
| **own-text share** | 100% | 90% | 38% | 16% |

Corrected 10-09 (no new teacher rows): the TEACH line stays at the existing 3.25M. The 6.6M at 30M and 100M predates
that rule; the difference is about 1% of the 100M pool.

What it found (shown unless marked):
- **Web text: FineWeb-Edu `sample-10BT`.** It is free and human-written, with 14 shards of 755M word pieces each. Its
  text is hard (median reading grade 13.2), so only grade 12 and below is kept, which is 34% of tokens. The 190M pool
  needs about half a shard and the 600M pool about 2 shards.
- **Our generators never run out of new rows, but variety is thin.**
  - The skills generator has only about 1.7M rows that differ beyond their digits (about 46M word pieces).
  - The English generator repeats its sentence shapes past about 15M.
  - So generator text is capped per size and web text fills the rest. The 60M skills line for the 100M pool is
    untested until a 1.2M-draw run.
- **The 1.2B teacher adds breadth, not volume.**
  - It keeps about 18,300 rows per PC hour as run, or about 32,000 on a free GPU. Its rows are short, so that is only
    0.35-0.6M word pieces an hour.
  - Doubling TEACH means designing about 60 new question kinds, not just running longer.
- **Overlap check `overlap13.py` is built.** It found 0 hits in TEACH and 7 documents in web shard 0 (0.001%), which are
  dropped. It never opens GOLD-PRIVATE, reserved or blind panels.
- **Protected panels, in parallel:** whoever owns them must hash them on their side (`overlap13.py index`) and share
  only the hash file. No thread here may open them. Ben chose "Start now" (1:23 PM ET 10-07): 8a may train before this
  check, and it must pass before 8c (spec addendum A1).
- **Left out:** MiMo-V2.6 RL environments. They look model-written and agentic, and most prompts are not plain English.

Two design calls for 8a, with the defaults this roadmap picks (suggested):
- **Keep the mix the same at every 8a size, so size stays the one change.** Use the 30M pool's mix, about 38% our own
  text and 62% web, at 3M, 10M and 30M alike. The pools are about 20M, 60M and 190M unique, and both arms get identical
  data. The 100M build then moves to 16% own text; that mix change is documented and judged by the race, not by 8a.
- **How web text is used** (corrected 10-09). Web text is plain text, not questions. It enters our model as
  fill-in-the-blank rows (one word of 3-12 letters blanked, `cloze.py`), and questions keep their answer loss, so the run
  teaches reading English, not writing it. Only the plain LLM arm trains next-word on raw web text. (This line used to put
  a next-word loss on the talker; 8a has no English talker, and how the 25M talker learns English is Ben's separate
  talking-from-scratch session.)

### 1.4 If the Gemma reader fails

- The EG-only arms failed (shown, 10-07). If EGE (EG2 added to the letter reader) passes its 6-seed confirm, keep
  that; the whole model is still about 400M.
- If both fail, train our own word-piece reader of about 30M. The whole model is then about 155M at a 100M thinker.
- Reaching hundreds of millions would then need a ~300M thinker: about 27 days of the PC with 4 rounds, or about $140
  rented.
- Decide after the 30M rung shows whether bigger helps at all.

### 1.5 Ben's design changes (10-07) and where they go

1. **Calculator as a tool.** Today the exact calculator runs inside the thinker's loop: each round writes one step and
   the calculator fills in its result. Ben wants it called as a tool with the inputs, and its result read back (his words: "an
   external tool call that the talker makes"). As built (T1SDR; corrected 10-09): after each round a small call writer
   reads the thinker's first control vector and writes a call or nothing. The reply is read as a short new string in
   later rounds, and the question is not re-read. One learned stop ends the answer, and the talker writes only the final
   answer. Related work: Toolformer (arXiv 2302.04761) and program-aided models (arXiv 2211.10435).
   - Correction (architecture thread, 11:43 AM ET, checked in `custom_io/models/ledger.py`): today B2 never reads or
     writes digits itself. A hand-written pattern (a regex, `NUM_RE`) pulls the prompt's numbers into the calculator's
     slots, and hand-written code prints the answer's digits. An outside calculator needs the model (the call writer) to write the
     numbers of each call and the reader to read the result's digits, so 2c is two changes, tested in order: learned
     number reading and writing with the calculator still inside (2c1), then the calculator outside (2c2).
   - Training transcripts can be built from the generators' gold steps, so no Claude text is needed.
   - Each call costs more thinker rounds, not another pass through the reader (corrected 10-09: the question is read
     once; FINISHED sec. 3).
   - Stage 2c tests it at 3.3M against today's B2. Ben, 11:35 AM ET: "It has to be able to work just as well when it's
     outside." So the bar is a match within seed noise, not just "it works". If it falls short, the gap points at a
     broken link (the call writer, or the reading of the reply), and that link gets fixed.
2. **Loop as long as it needs.** The thinker runs until it decides it is done, with a safety cap, instead of a fixed 8
   rounds. Known ways: a halting head with a cost on extra rounds (PonderNet, arXiv 2107.05407), training on random round
   counts and back-propagating only through the last few (Geiping et al. 2025, arXiv 2502.05171), and per-token depth
   (Mixture-of-Recursions, arXiv 2507.10524) (suggested).
   - The loop probe found that extra rounds hurt today's short questions (-1.1 and -0.8 at 16 rounds) and that B2's
     no-op step already works as a stop (shown, `custom_io/design/LOOPS-probe.md`). So stage 2d needs questions longer
     than 7 steps, where a fixed 8 rounds cannot finish.
   - One stop ends the whole answer (corrected 10-09; `tool_h1.py`): the talker makes no call-or-answer choice.
3. **As deep as possible.** At the same size, more blocks of a narrower width. Small language models did better deep
   and thin (MobileLLM, arXiv 2402.14905, about 30 layers at 125M) (suggested). Rough shapes (the 8a owner fixes them by
   counting parameters): 3M about 5 blocks at width 192; 10M about 10-12 blocks at 256; 30M about 16 blocks at 384;
   100M about 21 blocks at 512 (counted 10-09: one block at 512 holds 4,624,281 numbers, so 30 blocks would be about 139M). Each block also runs every round, so the thinker's real depth is blocks times rounds.
   - Cost at the same size is the same math, but a deep thin model runs slower on a GPU (smaller multiplies), maybe up
     to about 2x (our guess). The 10M rung measures it.
   - A learned stop makes the cost follow the average rounds used: an average of 16 instead of 8 doubles the 100M run
     to about 12 PC days or about $60 (our estimate). The safety cap and the cost on rounds bound it.
4. **More than 9 letters.** The architecture thread is researching the reader. EGE (Gemma in front of the window) already
   gives each letter whole-sentence meaning; its 6-seed confirm is running.

## 2. Progress since the first version (Oct 5 night to Oct 7, 4:30 AM ET; shown)

Overnight, Oct 6-7 (sources: `custom_io/results/CONFIRM-ANALYSIS.json`, `RESULTS-EG2.md`, `RESULTS-B1.md` at e10ea0232
on `claude/custom-reader-talker-4x309r`):
- **B2 confirm, 6 of 6 seeds: PASS-1.** Pooled-5 +20.3 vs plain_tf (CI 19.4 to 21.3) and +6.9 vs plain_tf_steps,
  ahead on 6 of 6. PASS-2's pretrained baselines (pythia-31m, 8-shot SmolLM2) have not run. The leak check (thinker
  off) was over 5% on seeds 201 and 203.
- **Reader test.** Every arm without the letter window failed (EGW, EGM, EGO, EGR), and R0 shows the window is what
  letter puzzles need (B2 ahead of R0 by 6.8 and 6.3). EGE, Gemma in front of the window, gained +1.59 and +2.12 with
  every split up, but missed 2 of 5 marks (unpractised sub-task split +1.70 vs +3.0; leak 18.1 on seed 200). Its 6-seed
  confirm runs now. EGT (Gemma as teacher only) failed (+0.18, +0.61). EGK (Gemma into the thinker only) crashed on
  seed 201.
- **Test B1: proved wrong.** TEACH minus GEN on new kinds was +0.78 (needed +15; under +5 proves it wrong); B1-c
  failed (-2.73). Each student scored 91-96% on held-out rows of its own practice and about 11% on new kinds, after
  seeing each row about 22 times. The Plan B thread recommends Plan B continue as stage 8a, with web text.
- **Test LR failed** its marks: pooled-5 +1.14 and +1.27, but the 16-round check dropped 0.51 on seed 200 (limit
  0.3) and the leak was 15.9 on seed 200.
- **Data pool plan done** (PR #47): see section 1.3b.

Oct 5 night to Oct 6, 4:30 PM ET:

- **Bench parked** (Ben, 11:20 PM ET 10-05). The last three tests all missed:
  - Wide doors on the plan route did not stack: 291.5 vs 287.0, ahead on 3 of 6, and confounded.
  - Learning-rate decay to 0 hurt: 276.2 vs 287.0, behind on 6 of 6.
  - Quiet notes hurt: 226.5 vs 287.0.
  - Reference recipe: `/mnt/project-files/bench/BENCH-RECIPE.md`. Nothing new to port to B2. Vast boxes were
    destroyed; credit is $8.84.
- **B2 confirm, 5 of 6 seeds** (queue 33):
  - Pooled-5 is +20.1 vs the plain transformer and +6.8 vs the step-writing transformer, ahead on all 5 seeds.
  - The leak check (thinker off) went over the 5% limit on 2 seeds: 10.8 and 5.7.
- **TEACH done:** 171,940 kept rows (PR #46). The B1 students are built and queued (queue 35).
- **Ben's decisions:**
  - EmbeddingGemma 2 may sit inside the model as its embedding ("don't care" about nothing-pretrained, 1:10 PM).
  - No Qwen or other new teacher; use the teaching we have (3:11 PM).
  - B2's letter-window reader should go (3:42 PM). EmbeddingGemma 2 as the whole reader (3:44 PM).
  - The shipped model should be hundreds of millions (3:43 PM).
- **Creative C1 retired** (seed 101 passed at 1.66x, seed 100 missed at 1.29x). C2 moved to a Mac DEV gate.
- **Loop probe:**
  - B2's arithmetic is right by round 8, and more rounds change nothing.
  - One idea from Amazon's looped model fits: training the answer at every round (Test LR, queued).

The Oct 5 progress list is in the night version.

## 3. Where the model stands

| | Our own model (B2) today | Ship target (this roadmap) |
|---|---|---|
| Reader | letter reader with a window of 4 letters each side, from scratch; numbers pulled out by a hand-written pattern | EmbeddingGemma 2 text part, frozen, in front of the window (EGE; 6-seed confirm in; window kept by Ben 10-09); inputs up to 2,000 letters |
| Thinker | looped controller, 2 blocks at width 256, writing up to 7 program steps, 8 rounds | the same planner at ~100M, deep (about 21 blocks at 512), looping until one learned stop ends it |
| Calculator | exact int64 executor inside the thinker's loop | the same calculator as an outside tool; a call writer reads the thinker and writes the call, and the reply is read in later rounds (shown, T1SDR) |
| Talker | copy talker (word pointers, letters); answer digits printed by hand-written code | open-English talker, ~25M, from scratch, writing only the final answer (unbuilt) |
| Whole size | 3,302,481 | ~396M |
| Best score | pooled-5 +20.3 over a same-size transformer (6 of 6 seeds) | race vs SmolLM2-360M, LFM2-350M, Qwen3-0.6B |

What our own model still lacks:
1. **Breadth.** It scores 0-4% on held-out families (shown). Teacher variety did not help (B1 proved wrong); the
   bigger-is-better check tests size plus data, including web text.
2. **A program language for more than arithmetic.** Its language cannot write dates or word edits (creative probe P0),
   and it trails on rule families.
3. **Open English.** This is the main risk to beating models of its size class.
4. **Few-example learning, memory and sleep.** None has run on it.
   - Those designs (notebook PR #20, sleep PR #19, reasoner PR #23, fair scaling PR #18) were written around the
     frozen 1.2B, so each must be re-posed first.
   - C1 sleep improved first answers on one parent only.
5. **Senses and hands.** No eyes, ears or actions yet.

## 4. Rules every stage keeps

- **One change at a time.** The pass mark, the proved-wrong result and a prediction are written before the run.
- **Seeds.** 6 or more paired seeds before any claim (noise rule, PR #29); 2-seed screens only decide whether to confirm.
  - Exception, proposed: the 100M build runs 1-2 seeds, because each seed takes days. Its noise band comes from the 30M
    rung's 6 seeds.
- **Lesions show the thinker decides:** donor state, loops:0 (the leak check), and an exact-tool lesion where there is
  one.
- **A harm mark on old skills** for anything that trains further (sleep, creative, growth).
- **Size counts every weight that runs when it answers, borrowed ones included.** Every claim is against a plain model
  of the same whole size, trained the same way on the same data.
- **Pretrained parts.** They may ship when Ben picks them (EmbeddingGemma 2, Oct 6). The thinker and talker stay ours,
  trained from scratch.
- **Training text:**
  - No new teacher model (Ben, Oct 6).
  - No Claude-written or Claude-judged training text.
  - The existing 171,940 TEACH rows (no new teacher rows, 10-08), code generators and human-written web text (Ben,
    10-06) may supply it.
- **Bigger only with more data:** no row is seen more than 4 times in any rung of Phase 3 (proposed).
- **Never score on GOLD-PRIVATE;** never touch reserved or blind panels.
- **Own machines only** (5070 Ti and M1 Pro, plus an M3 Pro Mac soon). No Vast or other rentals (Ben, 10:43 AM ET 10-09:
  "I can't do vast credit actually"); this replaces the 10-07 rule "Vast only when both are full".
- **The model does it all itself once deployed** (Ben, 2:45 PM ET 10-07: "everything that you do should be able to be
  done by the model autonomously while it's deployed"). Hand code runs only as an outside tool the model chooses to
  call, and no researcher choice runs while it answers. My reading (suggested; Ben can override): choices made once,
  before ship, stay ours, because none of them runs after ship. These are size, depth, the data mix, caps, the training
  schedule, worked examples, and tests and scoring. Anything that runs or is decided after ship moves to the model:
  answering, retrying, recalling, and choosing what to practice. Safety caps stay as guards, and the number of times
  each is hit is reported (target 0).

### 4.1 Before ship: what still needs a model-driven version

Run time (answering a question):

| # | Part | Today (who decides) | Model-driven version | Owner | Status |
|---|---|---|---|---|---|
| 1 | How long it thinks | Fixed rounds: 8 in q33, 12 in 8a (8a spec F4, G) | Learned stop: it runs until it decides it is done (safety cap 32) | 2d = H1 (architecture thread; the reader/talker thread builds it) | Built, never run; its first run is B3 group 1 at 3M after G1. 8a and G1 keep fixed rounds for the size test |
| 2 | Arithmetic | A Python executor runs inside every round; the model never chooses to call it | A calculator tool the model calls by writing text | 2c2 = T1 (no-hard-coding ladder) | Shown at 3M (T1SDR, 6 seeds, 10-09); joined with Gemma in B3 group 1 |
| 3 | Reading numbers and words | Regex number slots (16; 91 in 8a), a regex word splitter (64 words; 208 in 8a), hand digit codes | The model reads raw bytes itself | 2c1 and N1, P1, V1, then B3 | After T1 |
| 4 | Writing answers | Three hand renderers (`str()`, word slicing, reversed registers) | One learned writer that stops itself | O1, then B3 | After K1 |
| 5 | Retrying and search | We set the try budgets, temperature grids and "more tries where stuck" (creative D2, D5; job 8) | It decides when it is stuck, whether to try again and when to stop; checks go through tools it calls (D3 example checker) | Creative roadmap thread | Covered by its section 7c: try budgets, temperatures, stepping stones and the notebook switch each become a one-change test; job 9's arms carry autonomy labels |
| 6 | Memory recall | Hand gate on the notebook (theta 0.9 raised to the 0.99 quantile, boost c = 50; D6) | A learned gate, then a recall tool it calls | Creative roadmap and fast-sleep threads | Covered by creative 7b/7c. Nightly recall stays off until a learned gate passes |
| 7 | Text longer than its window | The reader's position table (280 letters in 8a and G1) | Run-1 reads up to 2,000 letters (Ben, 9:29 AM ET 10-09). Longer text, by carrying its vectors from one piece to the next, comes after run-1 | B3 group 1; later the running-summary note | 2,000 letters built (PR #56, `caps_b3.json`); first run B3 3M (corrected 10-09) |

After ship (it keeps learning on its own):

| # | Part | Today (who decides) | Model-driven version | Owner | Status |
|---|---|---|---|---|---|
| 8 | When to sleep and what to practice | We pick the rows, the nights, the replay mix and the harm check's panel (fast sleep; D8) | It logs its own tries, picks what to rehearse and when to sleep, and checks itself with tool replies (calculator, game) and its own past solved questions, not our gold answers | Stage 7, fast-sleep thread | Being rebuilt (fast-sleep thread, 10-07): replay from what the model saw, no C2 format filters, a temperature the model picks |
| 8b | New kinds of question | We write worked steps, and a hand rewrite turns "? + 5 = 12" into a subtraction (`progparse.py:42-51`) | It learns from the steps as written (L1), then from question-and-answer pairs only, keeping the traces of its own that check out (ST1) | No-hard-coding thread | L1 and ST1 are in B3 group 2, before the big run. Learning brand-new kinds after ship is not in run-1 (FINISHED sec. 6; corrected 10-09) |
| 9 | New program pieces | We add operations and pieces (stage 4) | It saves its own working programs as new pieces | Stage 4 | Open |
| 10 | Goals in a game | None yet | Its own goals and plans; our curricula only as teaching before ship | Stages 12-13 | Later |

What stays ours under this reading: size and depth (8a, 8c), the 38/62 data mix and the fill-in-the-blank builder, caps
from the data, the training schedule, the worked steps and teaching traces of the first training run (L1 and ST1
replace the hand rewrite in B3 group 2; learning new kinds after ship comes later), and every pass mark and test. The no-hard-coding plan reads the rule the same way (PLAN sec. 2a).

8a's B2 uses parts 1-4 as they are today (12 fixed rounds, calculator inside, regex slots, hand renderers). That is fine
for a size test, but B2 cannot ship. The size result reaches the ship model only through B3 (8a row). Parts 1-4 close
before the 8c build. Part 8b's L1 and ST1 close in B3 group 2, before the big run. Parts 5-9 close before any shipped model uses them, and part 10 comes with stages 12-13.

## 5. The ladder

Each stage lists:
- the one question;
- its test and pass mark;
- what proves it wrong;
- what it waits on;
- what runs next.

### Phase 1: Prove our own brain

| # | Question | Test and pass mark | Proved wrong | Waits on | Next |
|---|---|---|---|---|---|
| 1 | Finish the bench | **Done and parked.** CRDW 291.5 vs 287.0 (ahead 3/6, confounded), T1 276.2 (hurt), T2 226.5 (hurt); recipe in `BENCH-RECIPE.md` | n/a | n/a | n/a |
| 2 | Does our own small model beat same-size models? | **B2 confirm**, seeds 200-205, sealed in `custom_io/PASS-MARKS.md`. PASS-1: pooled-5 vs plain_tf >= +2.0 with CI above 0 on >= 5 of 6 seeds; chain-5 >= +8 (McNemar p < 0.01); in_dist >= -1.0. PASS-2 adds: vs plain_tf_steps >= +1.0; >= 2 above fine-tuned pythia-31m; above 8-shot SmolLM2-135M and pythia-31m. **Result (10-07): PASS-1**, +20.3 and +6.9, ahead on 6 of 6; leak over 5% on seeds 201 and 203; PASS-2's pretrained baselines not run | pooled-5 d < +1.0, or in_dist d < -2.0 | PASS-2: the pretrained baselines (queue 30) | Its parents feed C2; the Craftax probe (12a) can start |
| 2b | Which reader? (Ben wanted the letter window gone on 10-06; on 10-09, 9:29 AM ET, he chose "Keep" for the small window under Gemma) | **10-08: Ben allows reader help ("You don't have to ban any help from the gemma reader"), so EGE's one failed mark in its 6-seed confirm (the zero-round leak, 6.6 vs 3.6) no longer blocks it; the architecture thread re-scopes that mark. EGE is the reader for 8a-G.** **Queue 36**, 2 seeds each against plain B2, marks sealed before any run (EG2 doc addendum 4): pooled-5 >= +1 on both seeds; >= +3 on the unpractised-in-family split; no split drops more than 2; chain-5 >= 99; loops:0 and donor <= 5. Arms: EGE (EG2 added to the letter reader, whole 274.5M), EGT (teacher only, ships 3.3M), and window-free arms (EGW, EGM, EGO, EGR). **Result (10-07):** every window-free arm failed, and R0 shows the window carries letter puzzles; EGT failed; EGE +1.59 / +2.12 with every split up but missed 2 of 5 marks (sub-task split +1.70 vs +3.0; leak 18.1 on seed 200). EGE's 6-seed confirm (queue 39, seeds 202-207): +2.67 over B2 on 6 of 6 seeds; it missed the zero-round leak mark (6.6 vs 3.6), allowed as reader help (10-08) | an arm drops pooled-5 or misses the leak marks (B2's own values are reported beside it, since plain B2 also leaked on 2 seeds) | queue 39 on the PC | The winner is the reader for every Phase 3 rung |
| 2c1 | Can it read and write numbers itself? (needed before 2c2) | One change: the hand-written number pattern (`NUM_RE`) and the hand-written digit printer are replaced by a learned digit reader and a learned digit writer; the calculator stays inside. 2 seeds as a screen, then 6 paired seeds against today's B2. Pass (proposed, Ben's bar): learned minus hand-written on pooled-5 has its 6-seed 95% CI inside +-1.0; chain-5 within 1 point; numbers copied from the question exactly right >= 99%; leak and donor checks <= 5 | more than 2 below today's B2 on the 6-seed mean | the architecture thread's spec; PC after the EGE confirm | Pass: 2c2. Short: the chain is breaking at input or output (Ben, 11:35 AM ET); find which side with per-step logs and fix it |
| 2c2 | Does the calculator work just as well outside? (Ben, 10:49 and 11:35 AM ET 10-07) | **Shown as T1SDR at 3M (6 seeds, 10-09).** One change from 2c1: the calculator moves out of the thinker. A call writer reading the thinker writes a call (operation and numbers), the calculator runs it, and the reply is read in later rounds (the question is not re-read); one stop ends the answer, and the talker writes only the answer (corrected 10-09). Call transcripts are built from the generators' gold steps. 2 seeds, then 6 paired seeds against 2c1. Pass (proposed; the owner seals the band from seed noise, about 0.9 per seed on the B2 confirm): outside minus inside on pooled-5 has its 6-seed 95% CI inside +-1.0; chain-5 within 1 point; with the tool switched off, program questions fall below 5% (the tool is really used); leak and donor checks <= 5 | outside more than 2 below inside on the 6-seed mean, or its CI entirely below -1 | 2c1 | Pass: every later stage uses the tool loop. Short: find the broken link (the call writer, or the reading of the reply) with per-step logs, fix it, and re-run; the calculator does not go back inside |
| 2d | Can it decide how long to think? (Ben, 10:48 AM ET 10-07) | One change: fixed rounds become a learned stop (it runs until it decides it is done; safety cap 32), trained on random round counts with the answer read where it stops. Data adds longer chains (up to 16 steps) from the generators. Compared with the same model that always runs 32 rounds, 2 seeds, then 6. Pass (proposed): practised skills within 1 point of the fixed-round model; held-out longer chains within 2 of always-32; average rounds on 1-step questions at most half those on 12-step ones; leak checks hold | pooled-5 more than 2 below the fixed-round model, or it never stops early (average rounds within 10% of the cap on every family) | 2c2 | Pass: the stop goes into B3 and the 8c ship build (8a runs fixed rounds, disclosed). Now H1: sealed as required for B3 by the architecture thread (redesign-ideas sec. 8b) and built by the reader/talker thread (section 4.1 part 1). 10-09: no separate screen (no more little tests); its first run is B3 group 1 at 3M (mark B3-4) |
| 3 | Does a teacher give it breadth? (Plan B, B1) | Sealed in PR #41 and addendum 3. 10.9M B2 on TEACH vs B2 on GEN vs same-size plain_tf on TEACH; 2 seeds, then 6. **B1-a**: TEACH - GEN on new kinds pooled >= +15, both seeds. **B1-b**: donor <= 10% on new kinds. **B1-c**: B2 - plain_tf on TEACH >= +3. **Result (10-07, 2 seeds): B1-a PROVED WRONG** (+0.78); B1-c failed (-2.73); every student 91-96% on its own practice, about 11% on new kinds (`RESULTS-B1.md`) | B1-a < +5 | done | Wrong, so the bigger-is-better check and web text carry breadth (no new teacher, Ben). TEACH stays one part of the 8b pool. No 100M student on this data (Ben, 9:32 AM ET 10-07: wait for web text) |

### Phase 2: Make it learn like a person

| # | Question | Test and pass mark | Proved wrong | Waits on | Next |
|---|---|---|---|---|---|
| 4 | Can its program language say more? | Add rule, lookup, string and date operations as a small general base set, with a pieces library to grow the rest. Mark (proposed): practised skills within 1 point of the old language; the rule families reach the step-writer's level, 6 seeds | rule families still trail by more than 5 | custom reader/talker thread | C2 kinds, the crafting world, stepping stones |
| 4b | Can a small from-scratch talker write plain English? (early probe of the main risk) | A ~25M-class sentence talker on B2's exact answers, trained on teacher-written answer sentences (1.2B; no Claude text) and human-written web text. **Held 10-08:** new teacher sentences break the no-new-teacher rule, and Ben's separate talking-from-scratch session owns the talker. Pass (proposed): sentence answers keep B2's held-out score within 3 points; donor thinker state <= 10%; story-text loss vs a same-size plain LM is reported, not gated | sentence answers more than 10 points below the copy talker | B1 data; spec on CPU now | Settles the talker design before the 100M build |
| 5 | Does it learn from its own checked tries? (creative C1) | **Retired Oct 6**: seed 101 passed (1.66x), seed 100 missed (1.29x); bookkeeping (a "used" mark) is in B2's backlog | n/a | n/a | C2 |
| 6 | Can it learn a new rule from a few examples? (Ben's main measure; C2) | Creative roadmap sections 6-7: first try on held-out rule kinds W - N >= +15 and W - R >= +10; reach@4 and practised skills within 2. In-context ruler (PR #23): 8 examples >= 25 points above 0, and shuffled answers within 5 of 0. Proposed: a same-size plain net needs at least 4x our examples to match | W - R upper end below +3 | DEV gate on the Mac (MAC-JOB-4) | Creative floors C3-C9 |
| 7 | Does it keep facts exactly and get better overnight? (notebook PR #20, sleep PR #19, both re-posed) | Notebook: >= 16 of 32 one-fact-swap pairs on every seed (N1-N5). Sleep: S beats no sleep and plain fine-tuning on nights 1-5, keeps old skills, transfers, and the checker matters (P1-P6; margins from a noise run first) | Notebook under 8 of 32; sleep no better than none | a stage 3 parent; notebook code change | Sleep joins every later training loop |

### Phase 3: Grow and race (replaces the old 11M/30M/100M stage)

| # | Question | Test and pass mark | Proved wrong | Waits on | Next |
|---|---|---|---|---|---|
| 8a | **Is bigger better for our design?** (the bigger-is-better check) | **Result 4 AM ET 10-08: mark 1 FAILS at 10M** (B2 +0.49 pooled-5, CI -0.74 to +1.72; PT +3.77; LLM +15.77); mark 4 passed at 3M (72.34); shape probe: reader-grown flat, wider unclear; 30M held (Ben left the call to us, 10:16 AM ET 10-08; B2 fails his bar) (`8A-10M-RESULT-2026-10-08.md`). **Spec sealed 1:15 PM ET 10-07: `8A-SPEC-2026-10-07.md` (PR #50).** One change: size, with data growing in step. Today's B2 design (calculator inside, 8 rounds; 2c/2d tested separately, disclosed), reader from 2b. Rungs of 3.3M, 10M and 30M trained parameters, grown depth first. Arms per seed on one rented 5090: B2; plain_tf_steps (gate, same reader front and rows); a plain LLM recipe (next-word on raw web text plus question rows; reported); U0's BPE variant once U0 reports. Data: a fixed 38% own / 62% web mix, pools of 20M / 60M / 190M; web text enters B2 as fill-in-the-blank rows built by a script. 6 seeds per rung. Pass: B2 +3 pooled-5 per step with CI above 0; lead over plain_tf_steps not shrinking by more than 1; >= +3 at 30M on 5 of 6 seeds. Reported: B2 minus LLM per rung, b2t beside 10M, B1 new kinds, bAbI at 30M; depth check with B2-M at 10M; quarter-data diagnostic at 30M. **Good enough (addendum A, Ben 1:23 PM ET):** the 3M rung stays within 2.0 of today's B2 (pooled-5 74.0), and at 30M B2 beats a public model of about its whole size fine-tuned on the same question rows by 2.0 (pythia-31m; addendum F keeps the letter reader at every rung, and EGE, if it passes q39, is a 2-seed extra at 10M). Grows B2 now; B3 joins once it passes its 3M confirm. **Addendum B (1:40 PM ET):** every arm trains at least 24,000 updates (q33's recipe; 3M and 10M share rows), cloze rows fit B2's 208/8-letter limits, and one rented 5090 times all three sizes first. 3M cap $2.50 per box (about $10 for the rung); 10M and 30M caps come from the timing, and Ben sees the cost first if the total would pass $50. If only the reader pick is pending, 8a runs on the letter reader and EGE is a 2-seed arm at 10M. **Addendum C (1:45 PM ET, Ben: "can you just use the home gpu"):** all on BensPC, no Vast; estimated 3M about 9 h, 10M about a day, 30M about 4-5 days (Ben decides 30M with measured time). **Addendum D (1:53 PM ET):** the plain arm follows C0 (no 64-character cap on its steps, after D0b); 23% near-repeats in our own text accepted and reported. **Addendum E (2:07 PM ET, Ben 2:04 PM ET: "I don't think you should have it cut off long answers"):** every length cap in every arm is set to the longest case in its data; no answer-only fallback. **Addendum F (2:29 PM ET):** build rulings (PR #51): letter reader throughout, pythia-31m as the public model, one set of caps from the largest pool for every rung. **Addendum G (2:45 PM ET):** those caps stand (B2 gets 12 rounds, 36 answer registers and 106 slots), with no filter that skips rows. **Deploy rule (Ben, 2:45 PM ET):** 8a's B2 is a size test, not a ship design (section 4.1, parts 1-4) | B2's 3M-to-30M gain under +2, or its lead at 30M under half its lead at 3M, or B2 below the public model at 30M | q39 reader pick; web slices; generator rows for 10M and 30M; the build (spec section 10); Vast top-up for 10M and 30M | Pass: 8c. Wrong: do not grow; fix data variety first, then re-run |
| 8a-G | **Does a Gemma-fronted model gain more from size than a plain model?** (Ben's bar, 10:16 AM ET 10-08) | Spec `8AG-GEMMA-GROWTH-SPEC-2026-10-08.md`, marks fixed 10:30 AM ET before the build. One change against 8a: both arms read through the same frozen EmbeddingGemma 2 front. Ours = EGE (B2 + Gemma in front of the letter window); yardstick = 8a's plain step model with the same front (to build). 3M -> 10M, same pool and recipe as 8a. Pass: mean (our 10M-3M gain minus the plain gain) > 0 with 95% CI above 0; our gain CI above 0; the thinker carries at least half the score and half the gain (thinker-off check; reader help allowed); 3M >= 72.0; chain-5 >= 99. Screen on seeds 400-401 first: go on if the gain difference is >= +1.0 on both seeds, stop if <= 0 on both. Prediction (suggested): stops | gain difference below -1.0 with CI below 0 | built (PR #51, 612f5c5b01). **Status 10-08 2:50 PM ET: Vast credit ran out mid-screen (1 of 8 arm-runs done, G-B2 3M s400 72.42); the screen moved to BensPC (Ben 2:39 PM ET, addendum B). Old screen held (addendum C); 3:40 PM ET: re-run as gate G1 with the 9-register fix, BensPC only (addendum D)** | Pass: the Gemma-fronted design is grown. Stop: the fix is in the thinker (B3) |
| 8b | Can we feed a bigger model? (data pool, build step) | **Plan done (PR #47, section 1.3b):** 60M / 190M / 600M are reachable, with web text 10% / 62% / 84%. Next (CPU): `web_slice.py` on shards 0-1 (pass: hash-stable manifests, each smaller slice a prefix of the bigger one); 1.2M-draw skills run (pass: 60M shape-unique at <= 10% duplicates) ; protected-panel hashes merged in parallel (8a may start first; must pass before 8c) | any nested-prefix violation; a protected-panel hit left in a kept document | the protected panels' owner (hash file only), before 8c | Feeds 8a and 8c |
| 8c | The ship build: ~400M whole | Built only on a design that passes Ben's deploy rule for parts 1-4 and 8b of section 4.1: B3, which now includes the learned stop (H1) and self-taught traces (L1, ST1). Entry: B3 passes Ben's bar (10:16 AM ET 10-08) at 3M -> 10M: it gains more from size than the plain model with the same Gemma front (8a-G's marks). Thinker ~100M (deep, about 21 blocks at width 512, one learned stop; corrected 10-09: 30 blocks would be about 139M) + talker ~25M + EG2 reader (Ben, 10-08: the main input encoder; reader help allowed, thinker drives) + calculator as a tool (a call writer reads the thinker); inputs up to 2,000 letters (Ben, 9:29 AM ET 10-09); ~2.5B word pieces (>= 600M unique); 1-2 seeds (about 6 PC days each at 8 rounds on average, about double at 16 and about 4x at 32; PC only, no renting since 10:43 AM ET 10-09; asked first). H1's code back-propagates through every round with checkpointing; the PC fit check decides whether 100M fits 16 GB (untested; corrected 10-09). Sparse experts: test GX runs on the PC after G1, and experts join only if both GX stages pass (FINISHED sec. 5 item 10) | at 100M it is not ahead of the 30M model on pooled-5 and B1 new kinds | G1; B3's ladder beating the plain model's gain; 8b data; the protected-panel check; Ben's yes | Stage 10 |
| 9 | Can it talk in plain English, built from scratch? | Open-text talker that only translates the thinker's state (Ben, 09-29). Pass (proposed): on a sealed simple-English set, >= a same-size plain model + 3; talker-alone (donor thinker) <= 10% | talker-alone within 5 of intact | 4b result; 8b web text | Stage 10 |
| 10 | Does it beat its size class in a sealed race? | Sealed panel, never trained on, scored the same way for every model, whole size counted. Our sets: held-out families, B1 new kinds, C2 few-example kinds. Outside sets: bAbI (gate) and ARC-Easy and GSM8K (reported). Rivals: SmolLM2-360M, LFM2-350M, Qwen3-0.6B, fine-tuned on our practice rows where possible. Pass (proposed): ahead of every rival by >= +3 on our sets AND ahead on bAbI, with CI from the test-set size and the 30M rung's seed band | behind any rival on our sets, or behind on bAbI | 8c, 9 | Phase 4 on the 400M model. Ben's goal is beating 1-2B models at whole size: this 350M-600M race is our first gate, not his goal, and a 1-2B race follows if it passes (narrowed by us, not by Ben; flagged 10-09) |

### Phase 4: Senses, hands and worlds

| # | Question | Test and pass mark | Proved wrong | Waits on | Next |
|---|---|---|---|---|---|
| 11 | Can it see and hear? | **Ears** (PR #25, a 0.52M stereo ear from scratch): left/right >= 90%; onset F1 >= 0.8; >= 20 points fewer creeper explosions with sound. **Eyes**: our own ~30M eye distilled from a teacher encoder (SigLIP2 in PR #26; check against the no-new-teacher rule before vision restarts; Ben now allows a pretrained part to ship, so the frozen encoder itself is the fallback, counted in size). Pass (proposed): within 5 points of the teacher on the CPU probes at a third of its size or less, then E1 (8-way same-scene pick >= 50%) | mono ear within 10 points on left/right; our eye more than 10 points behind on hotbar digits | Ben restarting vision and audio (paused 10-03); after 8c | Stage 12 pixels |
| 12 | Can it plan and act in a world? | C5 text crafting world: unseen items >= +10 over no-sleep. Craftax-Classic, then Crafter pixels: >= 5 reward points over a same-size plain agent at equal steps; stretch: human level (65%) | C5 at random-plan level; at or below the plain agent | stage 4 ops; stage 11 eyes for pixels | Stage 13 |
| 12a | What breaks first when our thinker acts in a game? (probe, no pass mark) | Craftax-Classic symbolic view, B2 thinker plus a small action head, beside a same-size plain agent | n/a | stage 2 (JAX on the PC likely needs WSL, untested) | C10's spec |
| 13 | Can it beat Minecraft like a person? | First rung: more wooden pickaxes than a same-size plain agent at equal steps. Then stone, iron, diamond, the Nether, the Ender Dragon. Model: the ~400M model plus ~35M of eyes, ears and hands | first rung not above the plain agent | stages 11-12; Ben's definition of "like a person" | North star |

Proposed definition for stage 13 (Ben decides before Phase 4):
- Start from a fresh survival world.
- Only the screen and game sound go in; keyboard and mouse come out; no hidden game data.
- Kill the Ender Dragon.
- Report how many hours of play it needed next to a new human player.

## 6. What runs next (as of 10-07; for today see "Latest: where the plan stands")

1. The 6-seed EGE confirm (queue 39, PC, since 2:56 AM ET 10-07); its result picks the reader. Owner: custom
   reader/talker thread. PASS-2's pretrained baselines (queue 30) after it.
2. On CPU now:
   - Specs for 2c1 (learned number reading and writing), 2c2 (calculator as a tool; the architecture thread is
     designing both) and 2d (learned stop).
   - Seal 8a's marks, including the b2t baseline for the 10M rung and the depth-first shapes.
   - 8b plan is done (PR #47). Next: the web slices on shards 0-1 and the 1.2M-draw generator check; the
     protected-panel hashes from their owner run in parallel and must pass before 8c.
   - Write 4b's spec.
3. Dropped 10-08 (Ben, 3:27 PM ET: no more little tests): the 2-seed screens of 2c1, 2c2 and 2d. 2c2 ran as T1SDR; the
   learned stop's first run is B3 group 1 at 3M after G1.
4. 8a on BensPC (Ben, 1:35 PM ET 10-07: "can you just use the home gpu for this?"; spec addendum C): a 20-minute speed
   check right after q39, then q40 and U0, then the 3M rung (about 9 hours) and the 10M rung (about a day). The 30M rung
   (about 4-5 days on the PC, estimate) waits for Ben with the measured time: PC or rent for that rung.
   Before that, a first look (exploratory, 2 seeds, `FIRST-LOOK-10M-2026-10-07.md`): B2 deep at 10M (8 blocks) and a
   13-layer plain model on q33's data and recipe, beside q33's 3M runs. It runs after q39 and C0, not sharing the GPU;
   B2-10M results about 1-3 AM ET 10-08, the full readout with the plain 10M model about 7 AM ET. Its plain baseline is C0's uncapped recipe at both sizes (addendum D). It waits on the reader pick, the web slices and the 8a code, not on 2c/2d or the
   protected-panel check (Ben, "Start now", 1:23 PM ET).
5. B2 has confirmed, so the Craftax probe (12a) can run on a free machine.

## 7. Decisions for Ben

- **Default, for Ben to confirm or override (2:50 PM ET 10-07):** how his deploy rule reads (section 4). Choices made
  once before ship (size, data mix, caps, schedule, worked examples, tests) stay ours. Everything that runs or is
  decided after ship moves to the model (section 4.1). The 8c ship build uses B3 (learned stop and self-taught traces
  included), and starts only after B3 shows the 3M-to-10M gain.
- **Decided (Ben, 1:35 PM ET 10-07):** "can you just use the home gpu for this?" 8a runs on BensPC, no renting unless he
  asks again. 30M looks like about 4-5 days there; he chooses PC or rent for that rung when it is measured. (10:43 AM ET 10-09: no renting at all.)
- **Decided (Ben, 1:23 PM ET 10-07):** "Start now": 8a may train on web text before the protected-panel check
  finishes; the check must pass before 8c. And "demonstrate scalability with a model that is good enough": 8a grows
  B2, today's good model, and must show a good score as well as a gain (spec addendum A: within 2.0 of today's B2 at
  3M, and ahead of a public model of its whole size at 30M).
- **Default, told to Ben (he can override):** grow B2 now; the ladder switches to the all-learned B3 once B3 matches B2
  at 3M (no-hard-coding plan, section 3c). B3 then joins every rung not yet started and catches up on the finished
  ones, so its size gain is measured the same way.
- **Decided (Ben, 1:05-1:08 PM ET 10-07):** "just get more words for our model and make our model bigger"; rent GPUs for the
  growth ladder (about $30-50, after the overlap check). Withdrawn 10:43 AM ET 10-09: no renting. The 8a spec is sealed; the ~100M build is asked separately.
- **Decided (Ben, 10:48-10:49 AM ET 10-07):** the thinker loops as long as it decides and is as deep as possible; the
  calculator becomes an outside tool and its answer is read back (as built: a call writer reads the thinker; the talker
  writes only the answer); the reader should give the thinker more
  than 9 letters. Tests 2c and 2d check the first two at 3.3M before anything grows.

- **Decided (Ben, 8:57 PM ET 10-06):** the bigger rungs may learn plain English from free human-written web text
  (for example FineWeb-Edu). No Claude-written text, and the overlap check runs against every sealed test first.
- **Size target:** about 400M whole, thinker about 100M. This is our default; Ben can change it.
- **Decided (Ben, 9:32 AM ET 10-07):** wait for web text. No ~100M student on the teacher's questions; Plan B continues
  as stage 8a, and its next result is the 10M rung, shown beside b2t.
- **Later, asked when each starts:**
  - Withdrawn 10-09: Vast money for the 30M rung and each 100M build run (Ben, 10:43 AM ET: no renting; 10:49 AM ET: he may
    offer more compute after demonstrable results).
  - Vision and audio restart: default after 8c.
  - The written definition of "beat Minecraft like a person".

## 8. Risks and what would change the plan

- **Bigger may not be better for our design.** Fair scaling gave only +1.9 for a 4x core (PR #18). Stage 8a tests this
  with data grown in step before any big spend. The diagnostic arm says whether data or design is the limit.
- **Data, not compute, is the binding limit.** Web text (now allowed) makes up 62-84% of the bigger pools (PR #47).
  The generators' thin variety is the weakest line. If 8a's quarter-data arm scores within 1 point of full data, the
  web share should rise and the generator share fall.
- **The protected panels are not yet checked against web text.** Ben chose to start 8a anyway (1:23 PM ET). 8a never
  scores on them; the check must pass before 8c, and any web document it flags leaves the pool first.
- **A gain on a weak model would not convince anyone.** So 8a also gates on absolute level (addendum A). Today's B2
  scores 74.0 pooled-5 but only 34.7 on the unpractised sub-task (variant); that split is reported first at every rung.
- **Open English from scratch is the main risk in the race.** Every smaller talker so far lost:
  - A 350M LM as reader and talker scored 66.1% vs 92.6%.
  - A ~2M copy-and-gate talker scored 13.6% vs 78.2% on unseen kinds.
  - Stage 4b probes this early.
- **Moving the calculator out may cost B2's lead.** B2's +20 came with the calculator inside its loop, and a call
  through the tool is a longer path per step. Ben's bar is that outside matches inside; stage 2c measures it at 3.3M
  before anything grows, and a shortfall is treated as a broken link to fix, not a reason to move it back. T1SDR matched B2 at 3M (6 seeds,
  pooled-5 +0.62; shown 10-09).
- **Deep and adaptive costs more.** A very deep thinker trains slower and less stably, and a stop that keeps looping
  multiplies the cost. The safety cap, a cost on extra rounds, and the 10M rung's speed check bound it.
- **A big borrowed reader can do the thinking.** It did on the old sandwich. The leak and donor checks at every rung
  catch it. Plain B2 already leaks on 2 of 6 seeds, so the reader test reports B2's own values beside each arm. EGE
  leaked 18.1 on seed 200 (plain B2 1.4 there), and its 6-seed confirm missed the zero-round leak mark (6.6 vs 3.6).
  Ben allows reader help (10-08); the thinker-off check at every rung (G1, B3-2) shows whether the thinker still drives.
- **Cost estimates are rough, and the deep rungs may cost far more.** q33's B2 took 3.66 h for 24,000 updates on the PC,
  7.8x slower per update than plain_tf_steps (shown), and a deep B2 runs every block 8 times. A 20-minute speed check
  on the PC times all three sizes before the 3M rung (addendum C); the table gets updated then.
- **Small-model Minecraft is a research gamble.** The crafting world and Craftax are the honest near targets.

## 9. Sources

- Ben's messages, 10-06:
  - Size: cmsg_01GSLCHTCnZxn7DhV19qcDvM7uFtetWWcaxZWADqUzDTyu.
  - Letter window: cmsg_01GSLCHTCnZxn7DhV19qcDvM13zpjifU8DePavinpFtXB8.
  - EG2 as the reader: cmsg_01GSLCHTCnZxn7DhV19qcDvMKi2g5QYyRdjpyjM3n7y7pq.
  - EG2 OK: cmsg_01GSLCHTCnZxn7DhV19qcDvM71W581ZRkafQuVsGPFtXvo.
  - No Qwen: cmsg_01GSLCHTCnZxn7DhV19qcDvMNwbLt6Ad8CC3se6KevX1HL.
- Reader test: `/mnt/project-files/custom-io/EG2-and-loops-2026-10-06.md`; `custom_io/design/EG2-embedding.md` on
  `claude/custom-reader-talker-4x309r` (a5c050cff5).
- B2 confirm: `custom_io/results/33-pc-confirm-b2/` on the same branch (64bec1ce2). B2 runs at 3.3M took 1.8-4.4 steps a
  second at batch 256 on the PC, shared 3 ways.
- Data sizes: `custom_io/research/data.md`, `custom_io/README.md` (prompt mean 81 letters); TEACH 171,940 rows (PR #46).
- Bench: `/mnt/project-files/bench/BENCH-RECIPE.md`, PR #38.
- Data pool: `/mnt/project-files/data-pool/DATA-POOL-PLAN-2026-10-06.md`, PR #47 (branch `claude/data-pool-8b`).
- Design changes (section 1.5): Toolformer arXiv 2302.04761; program-aided models arXiv 2211.10435; PonderNet arXiv
  2107.05407; recurrent depth, Geiping et al. 2025, arXiv 2502.05171; Mixture-of-Recursions arXiv 2507.10524; MobileLLM
  arXiv 2402.14905. B2's thinker shape and cross-attention: `custom_io/models/ledger.py` (S and M configs, lines 1-12).
- Overnight 10-06/07 results: `custom_io/results/CONFIRM-ANALYSIS.json`, `RESULTS-EG2.md`, `RESULTS-B1.md` at e10ea0232 on
  `claude/custom-reader-talker-4x309r`; Plan B's reading in `design/thinker-first-split-2026-10-05.md` section 7 (42e5e9cfb, PR #41).
- Vast prices: live search of verified single-5090 on-demand offers, 3:45 PM ET 10-06.
- Data reuse: Muennighoff et al. 2023, arXiv 2305.16264.
- VPT: arXiv 2206.11795 and OpenAI's post (https://openai.com/index/vpt).
- Dreamer 4: arXiv 2509.24527.
- Craftax people's score: arXiv 2502.01591.
- Earlier sources: see the night version.
