# Why B2 barely scales, and what to test

Noise note: B2's +1.64 is one seed with paired sd ≈1.4, so by itself it spans roughly −1 to +4. Combined with the old 6-seed CI (−0.74 to +1.72) it is fair to say "B2 gains little from depth" is **shown**; everything about *why* is at best **suggested**.

## 1. Ranking the explanations

**1st — The thinker has nothing left to learn from the signal it gets, and the answer path can't express the remaining answers.** (Your "answer path" reading, sharpened.)
- Program loss ≈ 0 at 3M (**shown**). The 3M controller already fits every teacher-forced step in training. Extra parameters cannot lower a loss that is already zero, which is why total train loss moves 0.011 with 2.8× params, in both ladders (**shown**).
- Where the misses are: 51% in `variant` (unseen structures), and 859 of 1,630 in nine families needing lookup, rule induction, conditionals or selecting among many items (**shown**). The fixed 8-op calculator + slot pointer + one-shot GEN has no way to write "if ≥12 then…", "find the pair matching the query", or "argmax over a table, then name its word" as a program (**suggested**). fewshot_number_rule at 17/160 when the answer is often literally in the prompt is a pointer/selection failure, not a calculation failure (**suggested**).
- PT, whose output is free text, gained with size on exactly these families in the old ladder (**shown**).
- `frame` and `vocab` sit at 86–91%, equal to `in_dist` (**shown**), so B2 generalises across wordings fine; it fails across *structures*. Your "memorises the same wordings" guess is contradicted by this.
- `answer` 72 vs `in_dist` 86 despite an exact calculator (**shown**) means program choice depends on the digits — the controller pattern-matches values rather than reasoning (**suggested**). Capacity amplifies pattern-matching; it does not cure it.

**2nd — Depth-only growth inside the shared 12-round loop is the wrong axis or trains badly.** 2→8 blocks × 12 rounds is 24→96 sequential block passes at the same lr (**shown** config). Old probe: wider (384, 3 blocks) gave +1.57/+0.46 vs depth mean +0.49 (**shown**, 2-seed screen). Train loss didn't rise, so it's not catastrophic (**shown**). Whether width closes the gap is **untested** — and it matters because the planned 100M is 21–37 blocks deep.

**3rd (mine) — Most of the gradient flows through a head that cannot use capacity.** 62% of rows are web fill-ins with no program target; the controller learns from them only through WORD/GEN (**shown**). GEN is ~75% of the loss and essentially flat with size (**shown**). A parallel, non-autoregressive character writer has a high entropy floor on an open-vocabulary blank — it must commit to one word through 36 registers and cannot condition character k on character k−1 (**suggested**, standard non-autoregressive behaviour). For PT the same rows are character-level language modelling, which scales hard (pure LM +15.8, **shown**). So B2 spends most of its compute on a signal size can't improve. This subsumes your "GEN writer can't use more capacity"; it's partly right, but GEN-answered skill families aren't the main miss bucket (**suggested**).

**4th — "Near a ceiling."** Wrong as a hard ceiling: 27 points of headroom (**shown**). Right in the weak sense that the headroom is in rows the interface can't reach — which is #1.

**5th — "Practice rows are the limit."** Weakened: PT gains +3.77 on identical rows (**shown**); loss ≈ 0 means 3M already fits all of them (**shown**); and DS adds rows from the *same* generators, so it cannot supply the unseen structures that make up half the misses (**shown** by construction).

**6th — "Gemma does the reading."** Weakened: the old ladder without Gemma was just as flat (**shown**). Gemma raised the level (73 vs ~? old), not the slope.

Missing fact that would change this: per-file **program-step accuracy on dev** (teacher-forced) at 3M and 10M, and a split of misses into "wrong program" vs "right program, wrong mode/pointer". That is CPU-minutes on saved checkpoints. If most `variant` misses are "wrong program", the controller's structural generalisation is the limit and G2f's writer alone won't fix it; if "right program, wrong pointer", the answer heads are, and G2f is exactly right.

## 2. Decision rule for PT 10M, seed 400 (paired sd ≈1.4)

- **PT ≥ +3.0:** data and the Gemma front are not the limit; explanations 1–3 stand; DS is dead. Run the width probe (§3), then the G2f ladder. Read PT per family: gains landing in the nine B2-losing families strengthen #1.
- **PT ≤ +2.0 (as flat as B2):** something shared now caps both — the frozen 271M reader doing the work (#6 revives) or the fixed 260M-piece budget. First check PT's train loss: if it fell like before (0.366→~0.33) but dev didn't, it's generalisation/data; if it didn't fall, it's optimisation. Run PT s401 10M (cheap) before any B2 decision. Only here does a bigger pool become live — and I'd screen it on PT (hours), not B2 (46 h).
- **+2.0 to +3.0:** undecidable on one seed. Queue PT s401 10M; run the width probe meanwhile, since it is informative in every branch.

## 3. Is DS worth 46 h? No.

(a) Its hypothesis is already weakened (§1, #5). (b) It cannot fix half the misses by construction. (c) It's confounded: 1.4 vs 4.3 passes lets the 3M underfit, widening the gap for trivial reasons; the mix also changes. (d) Pass +3.3 vs the current +1.64 is ~1.2 paired sd apart — a single seed can't separate them. (e) Even a pass wouldn't change the shipped design.

**Run instead — "WIDE": B2 at ~10M by width, not depth.** Width 512, 2 controller blocks, heads scaled 8→16, register width 512, lr 1e-3×256/512 = 5e-4 (the rule your old probe used), seed 400, same data and 24,000 updates. One change: shape.
- **Pass:** ≥ 76.3 (≥ +3.3 over 3M's 73.01, >2 paired sd) — depth was the problem; grow width in every rung and cut the planned 100M's depth.
- **Fail:** ≤ 75.0 (≤ +2.0) — no way of adding B2 parameters helps; #1/#3 stand and G2f becomes the only path to scaling.
- **Between:** run s401 wide.
- This is also the test that would prove *my* explanation wrong: if width scores ≥76.3, "the interface, not capacity, is the limit" is false.
- **Cost (untested estimate):** FLOPs per update ≈ the depth-10M run's, but 4× less sequential work and 2× bigger activations; with the GPU at 23% busy I expect 12–20 h. A fit check (minutes) will tell you the micro-batch count; if it needs 16 micro-batches, expect closer to 25 h.

Do the free diagnostic (§1, missing fact) first; it costs no GPU.

## 4. Does G2f address the first cause?

**Mostly yes.** It deletes the fixed op set, slot pointers and one-shot GEN; tool calls and answers become text from an autoregressive writer, so conditionals, lookups and rule induction are expressible (**suggested**); and every row — including the 62% web rows — now trains an autoregressive loss, the kind that scales (PT +3.77, LM +15.8, **shown**). It makes B3's output side look like PT's, which does scale.

**Two things in G2f stand in the way:**
1. **The writer attends only to the 44 thinker vectors — no copy path, no attention to the prompt or tape.** Every digit and every word the writer emits must be squeezed through 44×256 numbers. PT and real LLMs attend to the context directly when writing. Risk: G2f at 3M loses B2's copy strengths (copy_word, table_lookup word answers, passage_qa, long numbers off the tape). **Concrete fix:** let the writer's decoder block cross-attend to [thinker vectors; reader output (prompt characters + tape)]. Keep it learned (no hand-made pointer), but give it eyes.
2. **Depth-only growth in a shared loop** carries over from B2 (and the 100M plan: 512 wide, 21–37 blocks). Grow width/heads first, keep blocks modest, and consider un-sharing blocks across rounds at 30M+. The WIDE result decides this.

**Is a G2f 3M→10M step a better first test than DS?** Yes — it tests the first-ranked cause and builds the shipped model, where DS does neither — but only after G2f 3M clears a floor: ≥ 67 (PT's level); ≥ 71 means it kept B2's strengths. If G2f 3M lands near 60, fix the writer's visibility (point 1) before paying 1–2 days for its 10M. Order: WIDE (≤1 day) → G2f 3M (queued) → G2f 10M.

**The change most likely to make size help at 100M:** an autoregressive writer that sees the prompt, with a training signal that is not already at zero — i.e. #1 and #3 fixed together. Secondary: structural diversity in the generators (the `variant` gap, 37%, is the largest bucket and size can't buy it).

## 5. Plain-language summary

Your model is like a student who was given every worked solution to every practice problem and learned them all perfectly by the time it was "3M-sized". The bigger "10M" version got the same worksheets and the same solutions — and there was nothing left to learn from them, so it ended up about as good. The numbers show this: the part of the training error that measures "did it pick the right steps" is already zero at the small size, and the total error barely moves when you make the model bigger.

The questions it still misses are mostly of two kinds: problems laid out in a shape it never saw, and problems where the answer isn't a sum but a lookup, a rule to guess, or an "if-then". Your current model answers only through a fixed set of eight calculator buttons plus a few hand-wired pointers, so it literally has no way to write those answers, however big its brain is. The plain model writes its answer freely, which is why it keeps improving with size.

So: don't spend 46 hours giving it more of the same worksheets (test DS) — more of the same cannot teach new shapes. Instead, spend under a day checking one cheap thing: does the model improve if you make it *wider* instead of *deeper* (your old probe hinted it might)? If wide works, grow every future version wide. If wide also fails, you have confirmed the real fix is the one you already planned next: replace the fixed answer buttons with a small learned writer that spells out tool calls and answers as text (B3 group 2). One warning on that design: let the writer look at the question and the calculator's replies directly, not just at the thinker's internal notes, or it will struggle to copy words and numbers.

Finally, read the plain model's 10M score tonight: if it gained 3+ points, the data is fine and the problem is your model's output path; if it gained as little as yours, something shared (probably the frozen reader) is capping both, and you should check that before anything else.