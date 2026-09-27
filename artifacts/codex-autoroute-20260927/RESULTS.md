# Replay allocation result

**Verdict: FAIL (not proved wrong).**

The independent full recount passed. Moving grid replay later improved mean final grids by **28.17/200** and total score by **30.00/600**, but missed M1's retention requirements and M3's required +40 total gain. Seeds 42, 44 and 46 retained 158, 159 and 147 grids, below the per-seed floor of 160. This is not a solution to persistent forgetting.

## Shown

Each score is exact items correct out of 200 at the model's own stopping rule. T is grids5 + sums4 + maze7 after C, out of 600. All threshold decisions used integer sums.

| Seed | A grids base / late | B sums base / late | C grids base / late | C sums base / late | C maze base / late | T base / late | ΔT | Minutes base / late |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 41 | 196 / 199 | 200 / 200 | 158 / 185 | 197 / 195 | 153 / 153 | 508 / 533 | +25 | 11.82 / 11.46 |
| 42 | 193 / 193 | 200 / 200 | 129 / 158 | 195 / 195 | 150 / 134 | 474 / 487 | +13 | 11.37 / 10.90 |
| 43 | 195 / 197 | 200 / 200 | 126 / 167 | 195 / 197 | 150 / 130 | 471 / 494 | +23 | 11.63 / 11.44 |
| 44 | 198 / 195 | 200 / 200 | 125 / 159 | 191 / 198 | 111 / 121 | 427 / 478 | +51 | 11.53 / 11.48 |
| 45 | 199 / 193 | 200 / 200 | 173 / 186 | 191 / 196 | 142 / 154 | 506 / 536 | +30 | 11.34 / 11.40 |
| 46 | 198 / 197 | 200 / 200 | 122 / 147 | 189 / 199 | 115 / 118 | 426 / 464 | +38 | 11.47 / 11.54 |

Mean C grids: **138.83 baseline / 167.00 late**; mean B sums: **200.00 / 200.00**; mean C mazes: **136.83 / 135.00**; mean C T: **468.67 / 498.67**. Late replay won T on **6/6** seeds.
Mean recorded minutes: **11.53 baseline / 11.37 late**.

| Registered check | Pass | Exact integer comparison |
| --- | --- | --- |
| M1 mean grid C ≥180 | False | 1002 ≥ 1080 |
| M1 every grid C ≥160 | False | Per-seed rows above |
| M2 mean sums B ≥195 | True | 1200 ≥ 1170 |
| M2 maze within 10 | True | 810 ≥ 821 − 60 |
| M3 T +40 | False | 2992 ≥ 2812 + 240 |
| M3 T wins ≥5/6 | True | 6 ≥ 5 |
| M4 integrity, MPS, precision, size and exact budgets | True | All 12 run files validated |

Phase counts checked in every file: baseline B 250 grids/2250 sums, C 75 grids/75 sums/1350 mazes; late B 125 grids/2375 sums, C 200 grids/75 sums/1225 mazes; A 2500 grids in both. Each arm used 6500 steps and 400 replay batches per seed, with batch 64 and 1,646,750 parameters on float32 MPS. All 12 runs report software commit `01a7a61b02c4877d4a41232b93e3fe2b6add6527` and passing initial/final M4 controls.

Report-only learned-context agreement (diagnostic-majority map applied to final inputs; correct kind / 600): s41 204 / 211, s42 241 / 261, s43 224 / 227, s44 389 / 397, s45 389 / 317, s46 400 / 427.

## Suggested

A score difference may suggest that moving a fixed replay budget later changes retention. The registered checks determine whether it did so without the specified learning cost; they do not identify a general optimal replay schedule.

## Untested

Other replay allocations, other tasks, larger models, language-model behavior, and ambiguous or reformatted requests are outside this grade. Both arms use learned context and mixed single-request inference, but its causal benefit versus oracle or other routing is not isolated. The grader relies on saved scores and M4 audits; an independent prediction recount is a separate check.

## Plain words

The two models got the same amount of practice. One moved some old grid practice from the middle stage to the last stage. The table shows whether that helped it remember grids while still learning sums and mazes. The verdict follows the rules fixed before training.

## Independent verification and provenance — shown

[RECOUNT-FINAL.json](RECOUNT-FINAL.json) reports **OK**, no missing files and no errors. [recount.py](recount.py) independently selected the own-stop round and checked all 21,600 saved A/B/C request records. It loaded each of twelve final checkpoints and reran 600 mixed requests per checkpoint on MPS: all **7,200 requests** matched their saved predictions, stop probabilities and context probabilities exactly. It also checked panel/source/raw/checkpoint hashes and independently reconstructed diagnostic context agreement. There were zero mismatches in every checkpoint.

The registered marks were pushed in `cafb67a80d97a8ddc93fe211bfb2e913b9f63119`; all scientific trajectories used software `01a7a61b02c4877d4a41232b93e3fe2b6add6527`. The recount confirmed the marks were unchanged and all manifested source files matched. No thresholds, model code, schedule or seed changed during training. The final read-only audit found no additional code/metadata violation. The earlier [preflight](preflight-final.json) checked invariance, gradients and budgets with zero optimizer updates; the separate model unit suite passed 7/7 before scientific training.

The twelve trajectories, including their evaluations and controls, took **137.39 minutes** in total on the Mac's MPS GPU. The separate full recount took **6.03 minutes**, for **143.42 minutes** combined, excluding preparation/preflight. See [DRIVER-RUN-NOTE.md](DRIVER-RUN-NOTE.md), [driver.jsonl](driver.jsonl), per-run RUN-NOTE files and [RECOUNT-RUN-NOTE.md](RECOUNT-RUN-NOTE.md) for UTC times, machine and PIDs. No rented compute or model download was used.

To recount again from the repository root with the same installed runtime and a new output filename:

```sh
/Users/ben-hannan/premonition-chat/chatdemo-venv/bin/python -B - <<'PY'
import sys
import torch
torch.set_num_threads(4)
sys.path.insert(0, 'artifacts/codex-autoroute-20260927')
import recount
sys.argv = ['recount.py', '--out', 'artifacts/codex-autoroute-20260927/RECOUNT-REVIEW.json']
recount.main()
PY
```

The report path must not already exist. The registered recount remains unchanged; [recount-launch.sh](recount-launch.sh) records the original full recount's exact launcher and progress instrumentation.

## Retention during learning — shown

Final retention alone hides substantial mid-sequence damage. These are the same held-out grid5 requests at each phase boundary, never used to train or choose weights:

| Seed | Baseline A → B → C grids | Late replay A → B → C grids |
| --- | ---: | ---: |
| 41 | 196 → 182 → 158 | 199 → 176 → 185 |
| 42 | 193 → 169 → 129 | 193 → 110 → 158 |
| 43 | 195 → 172 → 126 | 197 → 117 → 167 |
| 44 | 198 → 178 → 125 | 195 → 89 → 159 |
| 45 | 199 → 184 → 173 | 193 → 153 → 186 |
| 46 | 198 → 177 → 122 | 197 → 110 → 147 |
| Mean | 196.50 → 177.00 → 138.83 | 195.67 → 125.83 → 167.00 |

The candidate lost more grids during B, then recovered some in C. It still ended about 28.67 answers below its own A-level mastery. It did not keep the skill intact throughout learning. Both arms scored zero on the later kinds before their corresponding practice; that limited observation does not establish general transfer.

## Limits and interpretation

- **Shown:** one same-size dense model accepted each mixed request without a supplied kind label, per-skill model snapshot or handwritten inference router. Exact scores above describe its behavior on these native puzzle encodings. The soft-context argmax agreement is report-only and does not prove clean semantic routing.
- **Shown limitation:** the six final/diagnostic panel files contain 5,400 within-seed-unique requests but only 4,478 distinct requests across seeds: 1,800 grids, 1,800 sums and 878 mazes. Maze inputs repeat across seeds. Do not describe the pooled maze scores as tests on 1,800 distinct mazes. See [PREPARATION-NOTE.md](PREPARATION-NOTE.md).
- **Shown limitation:** registered exclusion of held-out fingerprints rejected 16,468–19,157 maze practice draws per trajectory, 2–9 sums and zero grids. Results concern that filtered practice distribution. Each run's result.json contains its exact rejection counts.
- **Shown limitation:** identical phase-A configurations/seeds were not bitwise identical training trajectories on MPS. Both arm-specific A scores are reported, and no reruns or seed substitutions were made. Small observed numeric differences grew during training; their specific cause was not isolated. See [TRAINING-REPEATABILITY-NOTE.md](TRAINING-REPEATABILITY-NOTE.md). Inference reproducibility did pass exactly.
- **Suggested:** concentrating rehearsal nearer the final stage can improve this final retention/learning tradeoff. It does not show that timing alone is sufficient, optimal, or that any specific brain mechanism was reproduced.
- **Untested:** the [learned sleep controller](NEXT-CONTROLLER-DRAFT.md), [cached-gradient projection](PROJECTION-REVIEW.md), other MoE designs, lifelong retention, grid4 retention, language requests, the 1B model and the joined build. Research notes are proposals and literature reviews, not model results. AR2's separate marks and future results must not be pooled with this grade.

## Plain-language conclusion for Ben

The network can now receive these puzzles without somebody naming the skill, using one network of the required size. Moving its old-grid practice later helped every tested run's final total, but it still forgot too many grids—and forgot even more of them in the middle before recovering some. We found a useful improvement, not the lasting memory you asked for. The registered experiment failed its marks; reviewers can recheck every count from the saved answers and checkpoints.
