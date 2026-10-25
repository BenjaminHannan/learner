# Sleep-B addendum 2: sleep that changes the whole model (written 2026-10-24 ~13:45Z, before any addendum-2 run)

Labels: shown / suggested / untested. Same model, week, tests and scoring as `PREREG-sleepB.md` and addendum 1.
Not the village model, not the card experiments.

## Question (Ben, 13:33Z: "doesn't sleep in the human brain change everything though?")
In the brain, sleep acts on most of the cortex. In mice, about 18% of synaptic contact area shrinks across sensory and motor
cortex, mostly in small and medium synapses, while the largest are spared (suggested; de Vivo 2017). Replay strengthens
specific traces (shown in rodents). Sleep-B so far left the pretrained model frozen. Each night it trained only a rank-16
add-on (LoRA), and SHY shrank only that add-on.

Does letting sleep change every weight, or letting each night's add-on become part of the model, put more recurring facts into
memory without hurting note-reading or general knowledge?

## Arms
All three arms use seed 1, the same AB stage-1 step schedule (`data/ab_schedule_stage1.json`) and open-book rehearsal.
Each is one change from `ab_ob`.
- **ab_ob (control):** the addendum-1 winner, rerun on seed 1. Stage 1 used seed 0. This shows the seed-to-seed spread.
- **ab_ob_full, "every connection can change":** every attention and MLP matrix in every layer (the LoRA targets) gets a trainable full-rank change, and the LoRA is frozen at zero. The learning rate is 2e-5 (AdamW, cosine over each night, fixed now). LoRA uses 2e-4 because its update is low-rank.
  - SHY acts on each matrix's total change since the original model: SVD, singular values x 0.85, then drop any below 5% of the largest.
- **ab_ob_merge, "tonight's add-on becomes part of the model":** LoRA trains as in ab_ob. At SHY time each night, the add-on is folded into a full-rank change buffer and SHY is applied to that total change. A fresh add-on starts the next night, so the total change can grow past rank 16.
- In both new arms, the KL guard, dreaming, tagging and the morning gate's reference stay the **original** pretrained model, as in ab_ob. Only the change is stored differently.
- **Deliberate departure from the brain:** SHY shrinks the learned change, not the pretrained weights. Shrinking pretrained weights by 15% would alter the function of every layer (suggested). That variant is untested.

## Measures (weights only unless noted)
- recall: mean forward recall on C2 and C4.
- integration: mean of two-hop, routine and changed-new.
- C1 forward: Ben's rule says this should stay low.
- diary pooled: the slept model with BM25 diary search.
- ARC-Easy: test set, 500 questions. Base is 89.6.

## Pass marks (fixed now)
- **F1 memory:** ab_ob_full recall >= control + 10.
- **F2 notes:** ab_ob_full diary pooled >= control - 5.
- **F3 old skills:** ab_ob_full ARC-Easy >= 87.6.
- **F4 rule kept:** ab_ob_full C1 <= 10.
- **M1-M4:** the same four marks for ab_ob_merge.
- **Seed spread:** recall spread = |control recall - 60.0|, where 60.0 is the seed-0 ab_ob recall. If the spread exceeds 10, an F1 or M1 pass is labelled suggested, not shown.
- **Wrong if:** ab_ob_full scores <= control on both recall and integration, so changing every weight gives nothing over the add-on at equal steps. Also wrong if ab_ob_full ARC-Easy < 84.6, meaning whole-model sleep damages old skills at this step size.
- A fail at lr 2e-5 does not rule out other step sizes (untested).

## Compute
- Box: one Vast A100 80GB, hard cap $2. Coordinator OK at 13:37Z, under Ben's standing approval.
- Order: ab_ob_full first (the main question), then the control, then ab_ob_merge. If the cap stops the run early, ab_ob_full is compared with seed-0 ab_ob and labelled suggested.
- Self-stop, then destroy when the results are in. If training has not started within 20 minutes, destroy the box and wait for the Mac.
