# Which forgetting guard should ship: early-but-fragile or slow-but-durable? (no code or file access needed)

You are an expert in continual learning, catastrophic forgetting, natural-gradient / K-FAC methods and experimental design. You have **no access** to my code, files or machine; everything you need is pasted below. Do not ask me to run anything before you answer; reason from what is here. If a fact you need is missing, say exactly what it is and how it would change your answer. Mark every claim as **shown by the data below**, **suggested**, or **untested**. Two seeds is a screen; four seeds is still small.

I am a high-school senior building this with AI help. Please end with a plain-language summary I can follow.

## 1. The setting

A small trained language-style model (the "parent") already answers 34 families of short reasoning questions (number rules from a few examples, next number in a sequence, table lookups, story arithmetic, ...). It is then fine-tuned on a new skill. Without protection it forgets badly: accuracy on the old questions drops 57 points.

- **Old-knowledge test (the ship instrument):** 6,800 held-out old questions, 200 per family. The parent scores 90.62%.
- **House family rule:** a run FAILS if the mean drop is > 1.5 points, OR any family drops > 5 points with a paired bootstrap 95% bound that excludes 0. For this work I add "near zero": mean drop <= 1.0. Call the combination **C1**.
- **New-skill score (HO):** % correct on 420 held-out new-skill questions. The unguarded model reaches **41.6%** (mean of 4 readings at 6k and 8k updates). Bar = 41.6 - 5 = **36.6%**.
- **Pre-set rule (written before any run):** T* = the first reading step (4k, 6k, ..., 16k updates) where mean HO over seeds >= 36.6. SUCCESS = T* exists and C1 holds on every seed at T*. If several guards succeed, **ship the one with the earliest T*** (ties: lower max drop at T*). A success must then be confirmed on two fresh seeds at the same T* (fixed in advance).

## 2. The guard (shared by every arm)

Every update: (a) a gradient mask from K-FAC factors measured on a 4,096-row "diary" of old-task examples. Directions that carry the top `energy` fraction (default 0.99) of input-side energy are protected; protection is graded, M = min(1, tau/(s*p)), where p is a direction's importance and tau is the importance of the least important protected direction, so **raising energy also lowers tau and hardens every protected direction**. Factors are re-measured every 500 updates on the current model. (b) 41 tensors are frozen. (c) KL replay: each update adds weight x KL(parent || child) on 32 random diary rows. Baseline (L11): energy 0.99, s = 1, KL weight 10.

## 3. Results (6,800-row test; HO in %)

| arm (one change vs L11) | T* | C1 at T* | after T* | HO |
|---|---|---|---|---|
| L11 baseline, to 16k | 8k | FAIL on 1 seed (seq_next) | fails at every reading 6k-16k on one seed, 10k-16k on the other; mean drop grows to 1.1-1.2 | 43.8 @8k, plateau 45-55 |
| **G1: KL weight 30** | **8k** | pass both (0.71 / 0.65) | fails on seed A at 10k, 14k, 16k; seed B at 14k, 16k (seq_next 5.5-6.5, fewshot 5.5) | 37.1 @8k, 45.6 @16k |
| G2: K-FAC factors fixed at the parent | 10k | FAIL (cipher_map) | - | - |
| **G3: energy 0.999** | **14k** | pass both (0.57 / 0.63) | **passes at every reading 6k-16k on both seeds (worst family <= 4.5)** | 22.7 @8k, 42.7 @14k, 46.0 @16k |
| G4: hard mask + KL30 | 10k | FAIL (fewshot 5.5, grows to 8.0 by 16k) | - | 46.7 @16k (one seed) |
| H1: half the replay steered to families with high KL on the diary | 8k | FAIL both (seq_next) | fails every reading | not slowed |

G1 confirm on two fresh seeds at its fixed 8k: drops 0.68 / 0.78, nothing fired (seq_next 4.5 on both, i.e. 0.5 below the family line); 4-seed mean HO 43.15. **G1 is CONFIRMED by the pre-set rule.** G3's fresh-seed confirm at 14k is still running (container restarts keep killing the 12-hour runs).

Item-level facts (shown): the old questions lost under a fixed guard are almost the same set across seeds (Jaccard 0.82-0.88), so the residual loss is structural, not noise. The failing families are always the same two: `fewshot_number_rule` and `seq_next` (both answer from the readout with no tool call). At 14k, G3 loses 75-76 old items vs the baseline's 121-122 on both seeds (paired drop difference -0.53 [-0.88, -0.18] and -0.51 [-0.85, -0.18]). At 8k, G1 loses 92-94 items on the new seeds; G3 loses 65-68 at 8k on its seeds.

## 4. Questions

1. The pre-set rule ships G1 (earliest T*). G1 passes at its stop step but leaks once training continues; G3 is slower but holds at every reading. Is "earliest T*" a sound ship rule for a guard whose leak grows with training? If you think the rule is wrong, say what rule you would have written **before** seeing data, and whether it is legitimate to apply it now or only to the next round.
2. Mechanism: why would a stronger KL anchor (G1) delay the readout leak but not stop it, while a wider protected subspace (G3) stops it? Which of these explanations is the data most consistent with: (a) the leak lives in low-energy directions that 0.99 leaves unprotected; (b) G3 is just "slower everything", and its leak would appear later (after 16k); (c) something else. What single measurement would separate (a) from (b)?
3. Propose **one** next change (one variable) aimed at a guard that is both early (T* <= 10k) and durable (C1 at every reading to 16k). State its pass marks **before** running, and the result that would prove it wrong. Candidates I have considered but not run: energy 0.995 (between G1's and G3's), KL30 + energy 0.999 combined (two changes), an energy schedule that hardens over training.
4. Is anything in the setup or statistics above likely to mislead me (e.g. reading C1 at many steps without correction, the 1.0 "near zero" clause, using the first-crossing step)?

Please finish with a short plain-language summary for Ben (a high-school senior): what was found, which guard you would ship and why, and what to try next.
