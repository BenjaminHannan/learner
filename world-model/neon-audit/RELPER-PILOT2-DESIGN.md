# Rel-PER Second-Pilot Design

**Status:** PINNED DESIGN ONLY — UNTESTED. No training was run for this design. This file authorizes no scored Rank 8 run.
**Outcome:** Decide whether one domain-general sampler adjustment can keep Rel-PER's rare-event gains while restoring the wall gate.
**Single adjustment:** Change Rel-PER's mixture from **50% uniform / 50% prioritised** to **75% uniform / 25% prioritised**. Nothing else changes.

## Scope and claim labels

- `shown` = directly measured from the saved pilot scores, sampler logs, or read-only CPU checks of saved checkpoints.
- `suggested` = causal interpretation of shown measurements; not proved.
- `untested` = the proposed adjustment, its projected behaviour, and its odds.
- Read-only analysis used M3 CPU under `nice -n 10`, PyTorch CPU with four threads and `torch.no_grad()`. No MPS, lock, training, dev set, sealed set, secret, SSH-key, Keychain, auth file, environment file, or private directory was read.
- The score filenames contain `dev`, but their inputs are only the pilot's held-out **train-source** worlds `3072..3079`. The actual dev file `wm-harness/data/heldout.npz` was not opened.

## Evidence provenance (`shown`)

Saved M3 artifacts under `~/learner-ops/seven-problems-m3/PROBLEM-7/wm8p/runs/`:

| Run | score SHA-256 | sampler-log SHA-256 | model SHA-256 |
|---|---|---|---|
| `s7_uniform` | `e7ace6b2cf34c0a178e25708edd331466df2335e0100e74f20ca7d5e8fea6520` | `e3d787325f5800e439959c9da00db7427e8ff5ebb92ce581201a1ee471957007` | `dcd2c72190e16f36b146037d179ae03d4f9d77e511956fc4596e29376b8e355e` |
| `s7_relper` | `84197d6b8e78c30fff7ef47acad9b4fbd35502263c230ce5fdfa43c994ffacf5` | `75c8bcb792e4210fa74e9d998b2977f6953c3e01bc963e135fabfa841cb48797` | `c2e9eaec5c00a2e34ed0804b311e817e86d375776745b0a5a3c7699dcfe5052d` |
| `s8_uniform` | `9dbc0a52a439f9c0023b30b86c5b6eb18b3fd23064f1e97d82c1576dc2eef8cd` | `b294eb019db2e532ab61c07cfc5dc380e020cd234a98cebcd82348292c454e7e` | `29be84bcd81980b66bb68fb92eb11398f8115fded8ede076ac1c79130aea897d` |
| `s8_relper` | `6fddb24598d3b1d82e99a77b501a93a7c15c6c6eadf4f034cc3b1befff796c4e` | `0a7f580ce7229fa3d973e4fd67a6532bb98d38f9543bfd5aad04f4223692d073` | `be9e8a63fa39e9e18dde3349add6f108920898bbecd0b7cf18fa32e3e8aa78ca` |

The pilot data hashes remain those pinned in `forecast8-pilot/PROOF.md`:

- Train worlds `3000..3071`: `e6b497be18d98d92d32f4cec82e11bd6984902e43b362d8bedd380bdd314c90f`.
- Eval worlds `3072..3079`: `545870b81493e098fcaefb2b58798c803c45a5fb5c2ac205bcaebda620b7da8c`.

## 1. Why did wall error rise?

### 1.1 The share of moves did not fall (`shown`)

The final cumulative `[SAMPLER]` record after 3,000 steps covers 192,000 sampled windows per run.

| Seed | Uniform move share / draws | Rel-PER move share / draws | Change |
|---|---:|---:|---:|
| 7 | 60.599% / 116,351 | 63.223% / 121,389 | **+2.624 pp / +4.33%** |
| 8 | 60.728% / 116,597 | 63.263% / 121,464 | **+2.535 pp / +4.17%** |

So “Rel-PER took away wall practice” is **not supported by aggregate move exposure**. The extra rare-event practice came mainly from awake `do` and stay-asleep windows, not from moves:

| Event share at step 3,000 | Seed 7 uniform → Rel-PER | Seed 8 uniform → Rel-PER |
|---|---:|---:|
| `wake_e89` | 0.207% → 1.117% (**5.40x**) | 0.210% → 1.074% (**5.12x**) |
| `wake_hurt` | 0.286% → 1.211% (**4.23x**) | 0.259% → 1.187% (**4.59x**) |
| `sleep_stay` | 14.509% → 12.222% (**-15.8%**) | 14.511% → 11.979% (**-17.4%**) |
| `do_awake` | 12.070% → 10.553% (**-12.6%**) | 11.969% → 10.688% (**-10.7%**) |
| `place` | 2.034% → 2.038% | 2.068% → 2.042% |

### 1.2 Evaluation used identical wall samples (`shown`)

Every arm/seed has exactly **1,642 valid move windows**, with **1,142 truly open** and **500 truly blocked** windows. No seed or arm had fewer wall examples to score.

The scorer defines:

- `FB` = truly open moves predicted blocked, divided by truly open moves.
- `FO` = truly blocked moves predicted open, divided by truly blocked moves.
- `mean_err = 0.5 * (FB + FO)`.

### 1.3 Both error types rose; the dominant type changes by seed (`shown`)

| Seed | Arm | FB (count / 1,142) | FO (count / 500) | Wall `mean_err` |
|---|---|---:|---:|---:|
| 7 | uniform | 0.028897 (33) | 0.092000 (46) | 0.060448 |
| 7 | Rel-PER | 0.039405 (45) | 0.098000 (49) | **0.068702** |
| 8 | uniform | 0.021016 (24) | 0.078000 (39) | 0.049508 |
| 8 | Rel-PER | 0.024518 (28) | 0.098000 (49) | **0.061259** |

- Seed 7's increase is **mostly false-block**: FB contributes `+0.005254` of the `+0.008254` wall rise (63.7%); FO contributes `+0.003000`.
- Seed 8's increase is **mostly false-open**: FO contributes `+0.010000` of the `+0.011751` wall rise (85.1%); FB contributes `+0.001751`.
- Therefore this is not one simple “too cautious” or “too eager” shift. Both sides of the wall decision boundary became worse (`suggested`).

### 1.4 The regression is a larger held-out gap, not simply worse training-wall fit (`shown`)

A read-only CPU pass of each saved checkpoint over the same 25,200 pilot training windows gives:

| Seed | Train wall: uniform → Rel-PER | Held-out wall: uniform → Rel-PER | Held-out-minus-train gap: uniform → Rel-PER |
|---|---:|---:|---:|
| 7 | 0.029856 → 0.031796 (**+0.001940**) | 0.060448 → 0.068702 | 0.030592 → 0.036906 (**+0.006314**) |
| 8 | 0.029200 → 0.027639 (**-0.001561**) | 0.049508 → 0.061259 | 0.020308 → 0.033621 (**+0.013313**) |

Seed 8's training-wall score improved while its held-out-wall score worsened. Overall k1 E/B also improved (`0.2975 → 0.2680`, `0.2906 → 0.2629`). This is not a global learning collapse.

### 1.5 Best-supported reading

- **Shown:** aggregate move sampling increased; evaluation wall denominators are identical; both FB and FO worsened; the held-out wall gap grew.
- **Suggested:** the 50/50 online priority mix disturbed shared features or the wall decision boundary. Wake/hurt over-representation and stronger hard-example selection are plausible interference sources. The saved artifacts cannot distinguish those mechanisms.
- **Not supported as the primary explanation:** fewer wall samples. There is no logged blocked/open training-share split, so a within-move redistribution cannot be completely excluded, but it cannot rescue the false “fewer moves” story.
- **Important honesty check (`shown`):** action-5's P1 gain is not proof that awake chopping was solved. Non-wake action-5 full-frame std ratio rose (`0.212 → 0.723`, `0.238 → 0.427`), but its R² became worse (`-0.031 → -0.493`, `-0.035 → -0.165`). Much of the P1 amplitude gain is wake-driven.

## 2. Exactly one adjustment: uniform-heavy 75/25 Rel-PER (`untested`)

### 2.1 Exact change

Keep the existing action-normalised priority, cap, exponent, epsilon, EMA, refresh cadence, replacement sampling, unweighted loss, architecture, optimizer, schedule, data, scorer, and rollout unchanged.

Change only the two mixture constants:

```text
uniform_mix  = 0.75
priority_mix = 0.25

r_j = min(e_j / (v_{a_j} + 1e-4), 20)
q_j = (r_j + 1e-6)^0.7 / sum_k((r_k + 1e-6)^0.7)
p_j = 0.75 / N + 0.25 * q_j
```

Everything else remains exactly as `forecast8-pilot/PILOT-PLAN.md` specifies. The event labeller remains diagnostic/logging-only and never affects `p_j`.

### 2.2 Why this is the one knob

- It is domain-general: no action IDs, wall rules, pixel masks, game state, or outcome labels enter sampling.
- It damps the enlarged online-priority component that coincided with the held-out wall-gap regression, while retaining a non-uniform exploration/error-correction signal.
- It restores more ordinary sleep and awake-`do` practice instead of letting wake/hurt examples dominate the change from uniform.
- The first pilot's P1/P2 margins are large enough that halving the priority half is a reasonable retention bet: P1 was `0.753/0.651` against `0.30`, and P2 gaps were `0.0741/0.0730` against required `0.00329/0.00244`.

Using the final pilot relation `p_50 = 0.5*u + 0.5*q`, the **projected** 75/25 event shares are:

| Projected share | Seed 7: 50/50 → 75/25 | Seed 8: 50/50 → 75/25 |
|---|---:|---:|
| `moves` | 63.223% → 61.911% | 63.263% → 61.995% |
| `wake_e89` | 1.117% → 0.662% | 1.074% → 0.642% |
| `wake_hurt` | 1.211% → 0.749% | 1.187% → 0.723% |
| `sleep_stay` | 12.222% → 13.365% | 11.979% → 13.245% |
| `do_awake` | 10.553% → 11.311% | 10.688% → 11.328% |

These are **suggested, not guaranteed**: online priorities will change under the new mixture. The projection still gives wake examples about **3.1–3.2x** their uniform share and keeps move draws above uniform. That is the intended trade: less rare-event over-weighting, not abandonment of Rel-PER.

## 3. Second-pilot protocol and exact falsifier (`untested`)

### 3.1 Fixed protocol

- **Unscored pilot only.** No dev or sealed data.
- Source and split unchanged: train worlds `3000..3071`; held-out pilot eval worlds `3072..3079`; same pinned hashes.
- Seeds **7 and 8** only.
- Arms: unchanged `uniform` and single-change `relper_u75`.
- Run four serial runs in balanced order: `s7_uniform`, `s7_relper_u75`, `s8_relper_u75`, `s8_uniform`. Use a fresh output root so no pilot-1 artifact is overwritten.
- **3,000 steps per run**, batch 64, `R7conv`, two-frame input, `reencode`, AdamW `lr=3e-4`, `wd=1e-4`, `w_lat=0.05`, grad clip 1.0, warmup+cosine, unweighted loss, 6.5-minute loud cap, M3 MPS through the existing `withlock.sh` when the lead executes it.
- Pinned model/scorer/lock hashes and all data guards remain unchanged.

### 3.2 P1/P2/P3 — exactly as before

All three must hold on **both** seeds.

- **P1:** `relper_u75` k1 action-5 std ratio `>= 0.30`.
- **P2:** with the same visual labeller and `dBright` definition, `G_relper_u75 >= 3 * G_uniform`, where `G` is mean wake-minus-stay-asleep predicted terrain brightness change. Both groups must be nonempty.
- **P3:** relative to the same seed's uniform arm:
  - k1 E/B `<= uniform + 0.005`;
  - k3 E/B `<= uniform + 0.008`;
  - wall `mean_err <= uniform + 0.005`.

Using pilot 1's fixed uniform baselines, the numerical second-pilot limits are:

| Seed | P1 action-5 std | P2 wake gap | P3 k1 E/B max | P3 k3 E/B max | P3 wall max |
|---|---:|---:|---:|---:|---:|
| 7 | `>= 0.30` | `>= 0.003285568` | `<= 0.302498862` | `<= 0.416700799` | `<= 0.065448336` |
| 8 | `>= 0.30` | `>= 0.002440902` | `<= 0.295619094` | `<= 0.407272043` | `<= 0.054507881` |

### 3.3 Result that proves it wrong

**Any** of the following on **either** seed proves the adjustment wrong:

1. P1 is below `0.30`.
2. P2 is below `3 * G_uniform`, or either P2 group is empty.
3. P3 k1, k3, or wall exceeds its same-seed allowance.
4. A run is incomplete, invalid, leaks held-out worlds into training, or touches dev/sealed data.

Decision rule:

- Any miss → **NO scored Rank 8**.
- A second pilot miss records **Rel-PER 2 of 3** and parks this sampler line; it does not spend the scored last strike.
- All three marks on both seeds → eligible for the lead's separate scored-Rank-8 decision, not an automatic scored run.

## 4. Honest odds (`untested`)

- **30%** clean second-pilot pass: P1, P2, and all P3 components hold on both seeds.
- **50%** wall-only miss: rare-event gains survive, but wall remains outside the paired allowance.
- **15%** rare-event gain is lost: P1 or P2 fails after reducing the priority half.
- **5%** invalid/incomplete run or protocol failure.

Why not higher: the wall mechanism is not proved, seed 7's first Rel-PER wall score also exceeded the absolute Rung-1 bar (`0.068702 > 0.0659`), non-wake `do` R² worsened, and eight held-out worlds give a noisy wall estimate. Why not zero: the P1/P2 margins are large, 75/25 still projects roughly triple-uniform wake exposure, and k1/k3 already improved under Rel-PER.

## Plain-English summary for Ben — 5 lines

1. The new practice plan helped rare actions and waking up, but it made the brain worse at telling walls from open paths.
2. It did not practice walking less; it practiced walking a little more, so this looks more like the new mix confusing the brain than too little wall practice.
3. One seed said “wall” too often and the other said “open” too often, so the wall sense became shaky instead of shifting in one simple direction.
4. For the second test we will keep three quarters of practice ordinary and one quarter “surprising,” so wake-ups still get extra attention without taking over.
5. This is still a guess with about a 30% chance of passing; if it misses again, Rel-PER is two misses out of three and we stop spending the last try on it.
