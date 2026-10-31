You are checking a pre-registered result before it is reported to Ben (a high-school senior). Label every claim shown / suggested / untested. Keep this toy test separate from any claim about a real assistant. Reply in at most 250 words, then exactly 2 plain sentences for Ben.

SETUP. "Hops bed": each question is a chain of 1-10 links (key in box, box in bag, ... where is the key?), 7 chains per row, chance 14.3%. A small model (Qwen3.5-0.8B + LoRA) loops layers 8-11 ("laps"). Trained on depths 1-4; "near" = unseen depths 5-6 (marked); "far" = 7-10 (no mark). Stop rule ("answer-stable"): stop at the first lap whose answer repeats the previous lap's, else 12; it cannot stop before lap 2. Marks fixed in advance: WORKS = F1 near(lap 6) - control >= +5 with CI > 0, and F2 trained >= -2. STOPS ITSELF = S1 near(stop rule) - control >= +5 CI > 0, S2 trained >= -2, S3 Spearman(depth 1-6, laps used) >= 0.5 with CI above 0.3 (proved wrong <= 0.1). Fresh rows (4000, never seen) are scored once as a check: each mark "held / did not hold".

ARMS. hloop = random lap count in training, answer-only loss. hloopi = hloop + feeding the question back in each lap. hloopd = hloopi but training lap count = depth + random 0..2 (uses depth labels in TRAINING only). hloops = positive control from a paper: laps = depth AND each lap graded on the right hop (needs hop labels). Controls: hplain / hplains (no loop, same compute).

RESULTS (validation, then fresh; seed 0 unless said):
- hloopd: F1 +35.1 [31.6, 38.5] / fresh +33.8; S1 +27.8 [24.1, 31.1] / fresh +26.1; S3 Spearman 0.81 [0.80, 0.83] / fresh 0.81. STOPS ITSELF: PASS, every mark held on fresh. Laps used by depth d1..d10: 2.00 2.19 2.90 3.01 3.30 3.56 3.69 3.68 3.68 3.73. Accuracy at fixed laps, far: r6 64, r12 87 (still rising); answer-stable far only 38.7; max-confidence pick (runs all 12 laps) far 65.7. W=0 lesion (no question feedback): near 97.9 -> 86.1.
- hloopi: WORKS only (S3 0.44 FAIL); feedback hurt vs hloop (near at lap 6 -17); held on fresh.
- hloop (br) pair A: replicates on 2 seeds, held on fresh; stop rule Spearman 0.43 (s0) / 0.36 (s1): does not stop itself.
- hloops (positive control): passes 2 seeds, held on fresh (Spearman 0.99-1.00).
- One-change readouts (no marks): hloopd - hloopi near +18.6 at lap 6, Spearman 0.81 vs 0.44; hloops - hloopd far -40 at lap 6.

Pre-registered next step for this outcome: "laps tied to depth give the stop, but real data has no depth labels: a new addendum, a lap count the model can set without depth labels (e.g. a curriculum that adds laps only while answer loss still falls)". hloopd has one seed.

QUESTIONS. (1) Is "hloopd stops itself" fairly stated as a one-seed lead, and is anything in the numbers a red flag (e.g. the stop rule capping laps near 3.7 while far accuracy keeps rising to lap 12)? (2) What is the cheapest single next test, with its pass mark and the result that would prove it wrong? Name only one.
