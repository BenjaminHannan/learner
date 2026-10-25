# Sleep-B addendum 3: gentler whole-model sleep, and targeted sleep that changes specific regions (written 2026-10-24 ~17:05Z, before any addendum-3 run)

Labels: shown / suggested / untested. Same model, week, tests, scoring, seed (1), step schedule (AB stage 1) and open-book
rehearsal as addendum 2. Not the village model, not the card experiments.

## Why (Ben, 16:54-16:55Z)
Ben asked: "What happened to the real human like sleep?" and "What if you also created a system for changing specific regions?
Isn't that how the human works".

Addendum 2 (shown, one seed, seed 1):

| arm | recall C2+C4 | ARC-Easy | diary pooled | integration |
|---|---|---|---|---|
| add-on control (ab_ob) | 56 | 92.4 | 82 | 47 |
| every weight at lr 2e-5 (ab_ob_full) | 57.5 | 82.2 | 47 | 33 |

Brain (suggested):
- Only synapses that were active during learning get "tagged" and later strengthened (synaptic tagging and capture, Frey & Morris 1997).
- Learning-made spines are local, and they persist (Yang, Pan & Gan 2009).
- Sleep downscaling acts broadly and in proportion (de Vivo 2017).

So the brain learns in a few places and trims everywhere. Our every-weight arm let learning land everywhere.

## Arms (each one change from ab_ob_full)
- **ab_ob_full_s, "gentler step":** the same as ab_ob_full except lr 5e-6, 4x smaller.
- **ab_ob_local, "change specific regions":** before each night's training, run 8 batches of that night's practice examples, with the RNG restored afterwards so the training stream is unchanged. Sum |gradient| for every weight in every LoRA-target matrix. Only the top K weights may change that night. K = the add-on's parameter count, so both have the same number of plastic connections.
  - lr is 2e-5, the same as ab_ob_full.
  - The change is trimmed element by element each night: x 0.85, then entries below 5% of the module's largest are dropped. This replaces the SVD trim, which would spread a sparse change everywhere.
  - Earlier nights' changes stay and keep shrinking. Only the current night's tagged weights can grow.
- Fold-in (ab_ob_merge, addendum 2) runs separately on Ben's PC.

## Pass marks (fixed now; control = seed-1 ab_ob above)
- **L1 no harm:** ab_ob_local ARC >= 87.6 and diary pooled >= 77.
- **L2 memory:** ab_ob_local recall >= 61 (control + 5).
- **L3 targeting protects:** ab_ob_local ARC >= ab_ob_full ARC + 5 (>= 87.2), at the same lr.
- **S1, S2:** the L1 and L2 marks for ab_ob_full_s.
- **Wrong if:**
  - ab_ob_local ARC < 84.6: targeting does not protect at this step size.
  - Or ab_ob_local recall < 46: a sparse change cannot hold the facts.
- **Reported, not marked:**
  - Where the tagged weights sit, by layer and by module type. This tests the "mid-layer MLP" idea from fact-editing work, and it is exploratory.
  - The number of nonzero change entries after each night.
- One seed. Any gap under 4 points (the seed spread seen in addendum 2) is not called shown.

## Compute
Both arms keep an fp32 change, its gradient and AdamW state for about 1.4B weights, so each needs more than 30 GB. That rules out
the free 16 GB cards (Kaggle T4, Ben's 5070 Ti). Plan: Vast A100s, with a cap set with the coordinator. Destroy each box as soon as
its result reaches the label.
