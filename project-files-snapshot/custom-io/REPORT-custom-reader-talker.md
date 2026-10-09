# Custom reader and talker: ranked designs and results (2026-10-05)

> **Superseded (2026-10-09).** This is the 10-05 report and its next steps are out of date. The B2 six-seed confirm in 'Recommended
> next steps' item 1 already ran (queue 33, seeds 200-205): PASS-1; PASS-2's outside-model comparisons were never run
> (custom_io/results/CONFIRM-ANALYSIS.json). Do not queue it again. B2's integer executor inside the model is no longer the design: in
> T1SDR the calculator is an outside tool the model calls by writing text, and it matched B2 over six seeds (pooled-5 +0.62, CI -0.23
> to +1.46; chain-5 99.6-99.8; with the calculator off, program questions score 0.0). The hand-written number and word splitters are
> still on the path and are planned to go (FINISHED-MODEL sec. 4). Ben ruled on 10-08 (3:27 PM ET) that there is one big proven run and
> no more small tests. The finished design is architecture/FINISHED-MODEL-2026-10-09.md.

Thread: "Custom reader/talker". Code and raw results are on branch `claude/custom-reader-talker-4x309r` in `custom_io/`.
Labels: **shown** = measured here, **suggested** = reasoned from measurements, **untested** = a guess.
Times are US Eastern (ET).

## For Ben

You asked for a model where the thinking part does the work, built without the two borrowed 1.2B language models, and
judged by whether it beats models of a similar size.

We built three small designs from scratch, about 3.3 million numbers each, with nothing pretrained. We trained them on
the same 200,000 practice questions as two plain transformers of the same size. One of those transformers writes out its
worked steps, and it was the hardest to beat.

The winner so far is **B2**. Its thinker writes a tiny program ("add these two numbers, then multiply"), and an exact
calculator runs it. Its talker can then copy letters and words out of the question. On 2 test runs, B2 scored
73.7% across five kinds of held-out questions. The step-writing transformer scored 67.7%, the plain transformer 54.4%,
and the old B design 68.6%. On the practised question types B2 gets 89-90%. Today's 1.2B sandwich gets 74.6% on the
same questions, though that was measured on a different model in a different way.

We checked that the thinker really decides the answer. If you give B2 another question's notes, it gets 4% right. If
you take away its calculator, the program questions drop to 1%. If you swap the calculator's plus and minus, 99.9% of
answers follow the swapped program.

One check failed by a little. With the thinker switched off, B2 still answered 6.8% of questions on one of the two
runs, and our pre-set limit was 5%. Its new word-finder can sometimes guess the right word without any thinking. By our
own rules that makes B2 a "no-go", so I'm asking you whether to run the 6-run confirmation anyway.

It still can't do brand-new kinds of question (about 1%). Nothing here fixes that.

## The question and the bar

Ben's ask: replace the two borrowed 1.2B language models around the reasoner with something custom, ideally nothing
pretrained, so the reasoner has to do the thinking. Success = the whole model (reader + reasoner + talker) beats models
of a similar size by a clear margin.

How it was tested (marks fixed before any training, `custom_io/PASS-MARKS.md`):
- Every model trains from scratch on the same 200k skills rows (seed-1 build), in the same order, for 24,000 updates
  (batch 256, lr 1e-3, bf16).
- Each design is compared with transformers of the same size, counted in full with nothing borrowed:
  - **plain_tf** answers directly (3.24M);
  - **plain_tf_steps** writes the worked steps, then the answer (3.26M);
  - **C1'** is plain_tf_steps with a calculator filling in each step at answer time.
- Scores:
  - **pooled-5** is exact match over five dev splits: in_dist, new answers, new sentence frames, new words and new
    wordings (6,040 rows);
  - **chain-5** is 5 multi-step families (1,000 rows).
- Lesions check that the reasoner, not the talker, decides the answer.
- The screen uses 2 seeds. A design that passes it goes to a 6-seed confirm against the same baselines, plus
  pythia-31m (fine-tuned, 30.5M) and 8-shot SmolLM2-135M.
- Nothing touched GOLD-PRIVATE, reserved or blind panels.

## Ranking (2-seed screen, shown)

| # | Design | Whole size | pooled-5 | vs plain_tf_steps | chain-5 | Verdict |
|---|---|---|---|---|---|---|
| 1 | **B2**: thinker writes programs, exact executor runs them, copy talker | 3,302,481 | **73.7** | **+5.9** (both seeds +) | 99.7-99.8 | NO-GO by one leak check in one seed; recommended for the confirm |
| 2 | **B**: the same, content-free talker | 3,252,368 | 68.6 | +0.8 | 99.5-99.7 | NO-GO (a donor check it cannot pass by construction) |
| 3 | **A**: register loop, one worked-step value per round | 3,217,708 | 64.5 | -3.3 | 63 | NO-GO, and its mechanism was shown wrong |
| 4 | A0: A without step targets | 3,217,708 | 60.5 | -7.2 | 43 | NO-GO |
| 5 | L2x2: plain_tf, 2 layers looped twice | 1,665,024 | 49.0 | -18.8 | 26 | NO-GO |
| - | plain_tf_steps (baseline) | 3,260,928 | 67.7 | 0 | 94 | the bar |
| - | C1' (baseline + calculator) | same | 68.9 | +1.1 | 96 | |
| - | plain_tf (baseline) | 3,244,544 | 54.4 | -13.4 | 34 | |

Not built:
- Typed Word-Slot Workspace: "later", because A and B cover its parts.
- Re-Reading Latent Loop and StreamPonder: dropped by the judges (`design/SYNTHESIS.md`).

All sizes are whole models, counted in full. B and B2 also use a hand-written number and word splitter and an int64
executor; neither has any parameters. For scale only: the current sandwich is about 1.2B (a frozen LFM2.5-1.2B plus a
roughly 9M core) and scores 74.6 on the same in_dist split. B2 scores 89.0 / 90.1. That comparison is not paired, and the
sandwich number comes from one checkpoint.

Per-run numbers: `custom_io/results/RESULTS-SCREEN.md` and `SCREEN-ANALYSIS.json`.

## What we learned

1. **Exact intermediate values beat latent ones (shown).**
   - B, B2 and plain_tf_steps all put each step's value somewhere exact, and they lead.
   - A keeps step values in latent registers. The register interchange matched the counterfactual on only 1.8% of rows
     (mark 40), so A's rounds recompute from the prompt instead of carrying values forward. That is the sandwich's
     failure in miniature.
2. **The talker was B's bottleneck, and fixing it was the biggest single gain (shown).**
   - B2 is one change from B: a pointer-generator copy path, plus content in the word keys. It adds +5.1 pooled-5
     (both seeds +).
   - On the five copy-target families it scores 76.4 against B's 59.6.
   - Turning the copy off costs 33 points on those families. Turning the word-content term off costs 18 points
     pooled-5.
   - Biggest family gains over plain_tf_steps: cipher_map +31, object_track +25, arith_bare +20, seq_cycle +18,
     backward_solve +17, table_calc +16, var_chain +16 (pooled over the five splits, 2-seed mean).
3. **In B2, the reasoner's state decides the answer (shown).**
   - A donor's state gives 3.8% in_dist, and a shuffled state gives 7.9%.
   - With no executor, the program families score 0.6%.
   - Swapping ADD and SUB in the executor gives the swapped program's value on 99.9% of rows.
   - With one iteration, chain-5 is 0-0.1%.
4. **The copy talker leaks a little (shown).** With zero reasoning iterations, seed 101 still gets 6.8% in_dist (the
   mark is 5%; seed 100 gets 0%). All the hits are word-pointer families (copy_word, object_track, prop_eval,
   order_chain): a fixed query can still find a plausible word by its content.
5. **Place codes alone do nothing for plain transformers (shown).** Adding them changes pooled-5 by +0.8 for plain_tf
   and -0.8 for plain_tf_steps. So A's +10 over plain_tf comes from its loop and registers, not from its reader.
6. **Where B2 still loses to plain_tf_steps (shown).** fewshot_number_rule -9, rule_apply -6, and a few points each on
   digits_parity, group_induct, order_chain and state_update. These families have no program in the data, so the
   arithmetic or the rule must happen in latent space. That was forecast in `design/design-B2.md`.

## What is not solved

- **New kinds of task.** Every model here, ours and the baselines, scores 0-4% on held-out families (shown). Learning a
  new kind of task from a few examples needs task diversity or episodic training, and none of these designs addresses
  that (suggested).
- **Free-form English.** These models read and write the curriculum's short prompts and answers, character by
  character. They do not chat. A custom talker for open text is a separate, larger build (untested).
- **Programs only exist where the data has worked steps.** B2's thinker learns to write programs from teacher-forced
  step text, and only 11 arithmetic families have it.

## Recommended next steps

1. **Run the B2 confirm**, with the leak flagged (needs Ben's OK, because the screen verdict is NO-GO by the letter).
   - B2, plain_tf and plain_tf_steps on seeds 200-205; pythia-31m fine-tuned on 200-202 at the best of three lrs;
     8-shot pythia-31m and SmolLM2-135M.
   - PASS-1 / PASS-2 marks unchanged. The loops:0 check is reported on all 6 seeds.
   - Queued for BensPC (`custom_io/queue_local/33-pc-confirm-b2.txt`, then 30) and the M1 (31). Nothing has run on
     them yet, because Ben's Mac session has been offline since 12:01 AM ET.
2. **If the leak matters:** make the word pointer's query come only from the reasoned state, with no constant part,
   and re-screen at 2 seeds (one change, untested).
3. **For the families B2 loses:** give the thinker a program language for rules and lookups, as the blocker thread's
   planner does for chains (suggested).

## Files

- Designs and judging: `custom_io/design/` (SYNTHESIS.md, JUDGES.md, design-B2.md).
- Pass marks: `custom_io/PASS-MARKS.md` (addendum 1: place codes; addendum 2: B2).
- Results: `custom_io/results/RESULTS-SCREEN.md`, `SCREEN-ANALYSIS.json`, and a `RESULT.json` per run.
- Where B loses: `custom_io/diag_ledger.py` (per-family talker-path diagnosis).
- Checkpoints (all 18 screen runs, never deleted): `/mnt/project-files/custom-io/checkpoints/`.
