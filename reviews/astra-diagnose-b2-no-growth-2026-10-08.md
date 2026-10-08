# Astra: why doesn't B2 get better at 10M? (diagnosis only)

**Rules for this task:** read only. No edits, no commits, no training, no tests, no GPU use, no new data. Mark every claim as
**shown** (you read it in a file or result), **suggested**, or **untested**, with the file and line or result file it rests on.
This is about the B2 skills model and the 8a size ladder only; keep the small card experiments and the village model out of it.

## Where to look

- Spec and its addenda: `design/8a-bigger-is-better-2026-10-07.md` on branch `claude/project-thread-yha868` (PR #50).
  Section 7 has the marks; addenda I (section 19) and J (section 20) are the newest.
- Results: `results/8a-ladder/` (3M and 10M rungs; `analyze_8a-3M.json`, `analyze_8a-10M.json`; speed probe) and `results/8a-first-look-10m/`
  (2-seed first look on the skills-only data) on the same branch. 10M results (all 6 B2 seeds; PT and LLM 5 seeds, seed 404's box hit its time cap) are in
  `/mnt/project-files/whole-model-roadmap/8a-results/8a-10M-s*-{B2,PT,LLM,box,pool}/` if you can read the shared folder;
  otherwise use the table in `reviews/gpt-diagnose-b2-no-growth-2026-10-08.md` (same numbers).
- Code (build branch `claude/project-thread-f1to6a`, commit 50ee171632): `custom_io/models/ledger.py` (B2: reader ->
  workspace -> looped controller -> exact executor -> NUM / WORD / GEN talker), `custom_io/models/reader.py` (the 2-layer
  conv reader, kernel 5), `custom_io/models/plain_lm.py` (the PT and LLM arms), `custom_io/g8a/configs.py` (how each rung
  is sized: B2 grows `blocks` only), `custom_io/g8a/cloze.py` (web fill-in rows), `custom_io/train.py`.

## The finding

At 10M, B2 gains +0.49 pooled-5 over 3M (6 seeds: +0.03, +0.28, -1.11, +0.51, +0.73, +2.48; CI -0.74 to +1.72). The
plain step model (PT) gains +3.77 and the plain LLM +15.77 on the same pool (5 seeds). B2's training loss hardly moves (1.232 -> 1.208, mostly the GEN part,
0.844 -> 0.828). Mark 1 (+3.0 per step) fails at the first step. The two-seed shape probe (addendum J) is done; its results are in
`results/8a-probe/` on the same branch and in `/mnt/project-files/whole-model-roadmap/8A-10M-RESULT-2026-10-08.md`
section 4. R (reader grown to 23 conv layers, blocks 2): +0.73 / -1.46 vs 3M, flat, and cipher_map fell 97.9 -> 72.5.
W (width 384, blocks 3, lr x 256/384): +1.57 / +0.46 vs 3M, +1.54 / +0.18 vs the deep 10M, "unclear"; its loops:0 leak
rose to 10.9 / 12.4 (3M: 5.3 / 9.8).

## Questions

1. From the code, where does B2's 10M size actually go, and which parts of B2 limit (a) the five dev files and (b) the
   GEN loss on web fill-in rows? Check in particular: does any path let the controller's extra blocks change what GEN
   or WORD can output (GEN is a parallel per-register readout, not autoregressive)? Is anything in the loss or the data
   (e.g. mode targets for fill-in rows, `max_ans`, the register count) capping what a bigger B2 can learn?
2. Check the 10M B2 runs for signs of a training problem: learning-rate fit for 8 blocks x 12 loops, gradient norms if
   logged, loss curves in `stdout.events.txt` (3M vs 10M), and the copy gate share.
3. Rank the explanations (size in the wrong place; a ceiling in the test; the GEN head; optimisation; plain models only
   gain because they start lower; B2 saturated on its calculator families and unable to express the pattern / rule
   families, see the per-family table in the GPT prompt; anything else you find), and say what the R and W results do to
   each. Check whether W's small gain could come from the talker answering without the loop (its leak rose).
   For the rule families (fewshot_number_rule, seq_next, rule_apply, order_chain), trace in `ledger.py` exactly how B2
   would have to produce a correct answer (which mode, which ops), and say whether its op set and talker can express it.
4. Ben's updated bar (10:16 AM ET 10-08): the model must gain **more** from each size step than the plain model does;
   EmbeddingGemma 2 is the finished model's main input encoder; reader help is allowed but the thinker must drive.
   The planned next test is `/mnt/project-files/whole-model-roadmap/8AG-GEMMA-GROWTH-SPEC-2026-10-08.md` (8a-G: EGE vs
   the plain step model with the same Gemma front, 3M -> 10M). From the code, is it the right next test, and is its
   plain-arm front fair? If not, propose the one next change to test instead, with pass marks fixed in advance and the
   result that would prove it wrong. Say which part of B2 would have to change for it to out-scale a plain transformer.
5. End with a plain-language summary for Ben (a high-school senior): a few short paragraphs, no jargon.
