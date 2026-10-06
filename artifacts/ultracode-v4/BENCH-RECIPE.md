# The 1.2B test bench: reference recipe (parked 2026-10-06)

Ben parked the bench at 11:20 PM ET on Oct 5 ("Park it" on the whole-model roadmap card). The last three tests (CRDW, T1, T2) were already running and finished as planned. No new bench tests will run unless one answers a question about B2. This file is the reference: what the bench is, the best recipe, what was tried, and what B2 should take from it.
Labels: **shown** = measured with marks fixed before the run; **suggested** = reasoned from measurements; **untested** = a guess.
Detailed marks and per-seed tables: `SCREEN-v4.md` (real model) and `DIAG-v4.md` (planner alone). Raw results: `results/<job>/`.

## For Ben

The bench is the old "sandwich": a borrowed 1.2B language model reads the question and writes the answer, and our small thinker sits in the middle. We used it to learn what makes a thinker useful before building our own model.

What it taught us, in order of size:
1. **Let the thinker plan, and let an exact calculator do the sums.** On chain questions the thinker now decides every answer: give it another question's plan and the score drops from 156 to 2 out of 160. B2 already works this way.
2. **Don't squeeze the paths in and out of the thinker.** Widening both from 32 to 2048 numbers added about 15 held-out questions out of 320 on 6 seeds. B2 already has no squeeze.
3. **Slow the learning rate down at the end.** It took the planner from 83% to 98%. B2 already does this.
4. **Many ideas did nothing:** two-hop pointers, wider attention, per-round routers and a wider planner reader all hit the same ceiling on the four lookup-style kinds. Merging the Hearer and Reader and making the thinker's notes quiet both made it worse (quiet notes by a lot: 227 vs 287 held-out).

So the bench mostly confirmed what B2 already does. The one open question it passes to B2 is in "Port to B2" below.

## What the bench is

- **Hearer and Talker:** one frozen LFM2.5-1.2B. The Hearer reads the question; the Talker writes the answer. Its weights never change, so no English check is needed for any run here.
- **Reader:** per token, LayerNorm(2048) -> Linear(2048, 32) -> GELU -> Linear(32, 256), on the Hearer's last hidden states. "Door in" = the 32 in the middle.
- **Thinker (core):** `N.Net('loop')` from `scripts/claude_fewex_net.py`, d = 256, 8 heads (heads 0-3 see only +-1 token), 8-expert UpcycledMLP, 4 loops. About 9.0M parameters, but only about 1.6M are live: the routers are exactly 0 and experts 0 and 1 are identical (model audit, `/mnt/project-files/model-audit/AUDIT-ranked-2026-10-05.md`).
- **Exit (StatePrefix):** 259 -> 32 -> 2048, pooled to 8 vectors that the Talker reads before the question. "Door out" = the 32.
- **Copy path** (`--copy-path`): the Talker also sees the question's own words.
- **Parent checkpoint:** main2 (branch `claude/real-pipeline-checkpoints`, `git hash-object` ef708d0d2209f0202da28ea3090ab752bbdea2e7).
- **Data:** the 200k seed-1 skills curriculum (train hash 010af67124544bda, in_dist f975d9fb312c02d7, CRLF-normalised).

### The screen everything was judged on
- The 8 families main2 did worst on ("worst-8"): chain_ops, state_update, chain_story2, var_chain (the 4 **chain** kinds) and cipher_map, seq_cycle, fewshot_number_rule, group_induct (the 4 **other** kinds).
- Training uses 2,000 fixed rows x 3 passes = 6,000 updates at batch 1.
- **Fit** is scored on 320 of those training rows. **Held** is scored on the 320 in_dist held-out rows of the same 8 families.
- Marks are written before each run, and a winner needs 6 paired seeds.
- Never scored on GOLD-PRIVATE; reserved and blind panels were never touched.

## The reference recipe

Best confirmed recipe: **CRDC** (6 seeds, shown): fit 297.3 / 320 (92.9%), held 287.0 / 320 (89.7%).
Adding the 2048 doors on top (CRDW) did not stack by its marks. It got held 291.5 and was ahead on only 3 of 6 seeds. That run also widened the planner's reader by accident, so it is not a clean test; see the ladder.

```
P=<pipeline root>; D=<skills data>; M2=<main2 checkpoint>
S=$P/scripts/cap256_launch/skills_pretrain_v1.py
W8=chain_ops,state_update,cipher_map,chain_story2,var_chain,seq_cycle,fewshot_number_rule,group_induct
FIT="--families $W8 --updates 6000 --eval-every 3000 --dev-n 320 --eval-at-start --fixed-rows 2000 --passes 3"
python $S --root $P --data $D --parent-path $M2 --no-checkpoint --minutes 170 \
  --copy-path --gen-fix $FIT --steps --steps-rich --seq-steps-v2 \
  --plan-route 17000 --plan-cosine --final-lesions --save-texts --sample-seed <seed>
```

What each part does:
- `--gen-fix` (shown, required): generation sees the training layout `[pooled][prompt][BOS]`. Without it the prompt went in twice at answer time, and every older copy-path score is low (main2 in_dist 68.5% -> 74.6% with the fix).
- `--steps --steps-rich --seq-steps-v2` (**SR2**, shown): the training target is the worked steps, then " # answer". Fit went from 66.6% to 86.1% on 3 seeds and was confirmed at 85.5% fit / 81.3% held on 6.
- `--plan-route 17000 --plan-cosine` (**CRDC**, shown): this is the thinker-plans route.
  - A fresh planner core is pretrained on 17,000 chain rows. It writes a start number, ops and operand pointers, with `--op-attend` on (the op reads the state at its operand).
  - An exact calculator runs the plan, and the Talker says the value.
  - Its lr decays along a cosine to 0.
  - Fit 92.9% / held 89.7% on 6 seeds, against SR2's 85.5 / 81.3.
- `--final-lesions` (shown, the check that matters): family_mean, shuffle_same_family, global_mean, plan_swap, and note_drop with `--plan-talk`.

## The ladder (each step confirmed on 6 paired seeds unless noted)

| step | change | fit / 320 | held / 320 | what the lesions say |
|---|---|---|---|---|
| main2 | parent, `--copy-path --gen-fix`, no steps (3 seeds) | 213.0 | 154.0 | - |
| SR2 | + LM-written worked steps | 273.5 | 260.0 | thinker = family switch (family-mean lesion <= 5.3 pts) |
| CRDC | + thinker plans, calculator computes | **297.3** | **287.0** | plan_swap: chain held 156 -> 2-3 on every seed |
| WDC | SR2 + both doors 2048 (no plan route) | 287.0 | 274.8 | family-mean lesion 0.9-8.1 pts |
| CRDW | CRDC + both doors 2048 (the planner's reader got 2048 too) | 294.2 | 291.5 (ahead 3 / 6: does not stack) | other-4 held +8.0 (never behind); chain -3.5 (planner worse); family-mean lesion 10-30 rows |

LMDC is the control (shown, 3 seeds). With the same 17,000 chain rows and decay, the LM's own worked steps reach 158 / 160 on held chain rows, level with the plan route. So the plan route's value is that the thinker decides the answer, not that it is more accurate at equal data.

## Tried and dropped (shown, marks fixed before each run)

| test | what changed | result |
|---|---|---|
| PLR | one router per planner round (Chain-of-Experts) | WRONG: 131.2 vs 132.5 / 160, ahead 2 / 6 |
| PX | the 4 other kinds as pointer plans | 77 / 160 held |
| PXW, PXW2048 | wider planner reader (256, 2048) | 75, 77: same per-family numbers as PX |
| PXH | two-hop content-addressed pointer | WRONG: 76, content pointers 44 / 120 (+0) |
| T3 | all planner heads see the whole question | WRONG: 78, content pointers 46 |
| MH | Hearer and Reader merged (Reader -> one Linear) | WORSE: held 278.8 vs 287.0, ahead 2 / 6 |
| CRT | Talker writes `calc(note)` from the thinker's note | works, LEVEL: chain 471 vs 470 / 480 (3 seeds); copies a swapped note 79-96% |
| T2 | quiet notes: exit vectors word-sized, learnable length | HURTS: held 226.5 vs 287.0, behind on 6 / 6; other-4 held 71.0 vs 130.7 |
<!-- T1-ROW -->

Earlier, from the plateau thread (PR #34), these were also ruled out: stiffness, core size, truncation, too little practice, wider input pipe, 8 loops, lr 3e-4, pointer, wider exit (as a single change then).

## What still holds (shown)
- **On chain kinds the thinker decides.** plan_swap takes chain held to 2-3 / 160 on every CRDC seed. The planner alone gets 154-159 / 160 plans right.
- **On the other 4 kinds the thinker is mostly a family switch.** The family-mean lesion costs under 10 points on every seed of every arm, including the wide doors. The Talker reads the question and does that work itself.
- **Five planner designs hit the same ceiling on the 4 other kinds:** PX, PXW, PXW2048, PXH and T3 give the same per-family numbers, even on practised rows (group_induct 26 / 40 held in all five, cipher_map 0-2). The limit is upstream of pointer form, door width and attention range. Suggested, untested: the planner learns one fixed position rule that is right on a fixed subset of rows.
- **Practice beats the route at equal data** (LMDC above).

## Port to B2
B2 = the custom reader/talker thread's 3.3M from-scratch model (branch `claude/custom-reader-talker-4x309r`, `custom_io/models/ledger.py`).
Checked in its code: its thinker writes programs that an exact int64 executor runs; it is d = 256 throughout, with no narrow door; and it uses warmup + cosine lr to 10% with AdamW wd 0.1 (`custom_io/train.py:11`).

**Already in B2, nothing to port:**
- plans plus an exact calculator;
- wide paths;
- an lr that decays;
- lesions that swap or drop the thinker's state.

<!-- PORT-LIST -->

**Do not port:**
- per-round routers;
- two-hop pointers;
- all-global attention for this purpose;
- replacing a real reader with one Linear;
- quiet notes (no analogue in B2: it has no frozen LM to talk to).

**Warning for B2's next step.** B2's report proposes "a program language for rules and lookups" for the families it loses (fewshot_number_rule, rule_apply, group_induct and others). On the bench, the pointer-program version of that idea flat-lined at 77 / 160 on cipher_map, fewshot_number_rule, group_induct and seq_cycle, across five designs (shown). A B2 version should try something other than pointing at a position. One option is to save per-row outputs first, which would show whether the program picks a fixed position (untested).

**Talker bypass looks the same in both models** (suggested). CRT's Talker mixed question numbers into a swapped note (it copied the note 79-84% on 2 of 3 seeds), and B2's copy talker answers 6.8% of in_dist rows with the thinker off (seed 101). In both, the talker can reach the question without the thinker. B2's own proposed fix fits both: make the word pointer's query come only from the reasoned state.

**One check worth doing once in B2:** score a few hundred training rows through the eval path and the training path, and confirm they agree. On the bench, the prompt was fed twice at answer time but once in training. Every score was about 6 points low until `--gen-fix`.

## Open, untested, not queued
- Which door carries the wide-door gain: the reader alone or the exit alone. It needs one run each on CRDC.
- Why the 4 other kinds flat-line. Saving per-row plan outputs in `uc_diag_v4.py --mode plan` would show it.
- T5: folding the identical MoE experts into one (exact, CPU only).

## Files
- Code: `scripts/cap256_launch/skills_pretrain_v1.py` (real model) and `scripts/cap256_launch/uc_diag_v4.py` (planner alone).
- Cloud boxes: `scripts/cap256_launch/ultracode_box.sh` and `ultracode_vast.py`, with queues in `artifacts/ultracode-v4/queue/<box>/`.
- PC set-up: `PC-SETUP-files.md`.
- Marks and results: `SCREEN-v4.md`, `DIAG-v4.md`, `PANEL-v4.md`, and `results/`.
- PR #38, branch `claude/ultracode-learning-blocker-gh011t`.
