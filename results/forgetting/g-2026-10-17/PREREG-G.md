# Round G: goal bars and pre-registration (written 2026-10-17 ~14:00Z, BEFORE any round-G run is launched)

DRAFT (coordinator review pending; nothing committed). Bars below are fixed now and are not moved after scores arrive.

## Goal (Ben, via /goal, Oct 17)
SUCCESS = a guard setup where both hold at once on the 6,800-row DEV (ship instrument, house family rule):
1. old knowledge barely moves (near-zero drop AND no family fails);
2. new learning is delayed, not capped (reaches the unguarded new-skill level given more training).

## Operational definitions (fixed)
- **C1(seed, step)** = house rule `domain/harm.py harm_measure(5.0, 1.5)` PASSES on the 6,800-row DEV (sha 3e3a5edb) AND in_dist drop <= 1.0.
  (Pass = drop <= 1.5 and no family with drop > 5 whose paired 95% bootstrap bound excludes 0. The extra <= 1.0 is the "near zero" clause.)
- **Unguarded level U** (from E2, already measured, fixed now): L7-LB HO% at 6k and 8k, both seeds = 43.1, 31.9, 46.7, 44.8 -> U = 41.6.
  SESOI 5 points -> **C2 threshold 36.6** (mean over the two seeds of HO% at a read step).
  S5 is reported beside HO but does not decide C2 (HO = held-out layout = the record's headline new-skill cell).
- **Read steps** 4k, 6k, 8k, 10k, 12k, 14k, 16k (16k = 2x the unguarded protocol: "given more training").
- **Stop rule, chosen on the NEW task only (no DEV peeking):** T* = first read step at which mean-over-seeds HO% >= 36.6.
- **SUCCESS(candidate)** = T* exists (<= 16k) AND C1 holds on BOTH seeds at T*.
- **Delay vs cap:** delayed = T* exists. Capped = no T* by 16k AND mean HO(16k) - mean HO(12k) < 2. Otherwise open (still rising).
- Seeds 93301 (shipped) and 31001 (E2's second seed). Parent s200, L5 rows, lr 1e-4, batch 64, CPU, free cloud sessions.
- Reported always (not deciding): 1,360-row harm, worst 6,800 family + its drop, lost-set Jaccard vs L11, C1 at every read step after T*.

## Existing guards scored against these bars (E2 + M0 data, already in hand)
| guard | T* | C1 at T* | verdict |
| L7-LB unguarded | 6k (HO 44.9) | drop 57-58 | FAIL C1 |
| A1F replay+freeze, no mask | none by 8k (HO 15.5 @4k, 21.0 @8k, s93301; s31001 futility-stopped @2k, drop 3.0) | drop 4.5-6.2, 5 families | FAIL C1 (and C2 unread) |
| L11 soft1 + KL10 | 8k (HO 46.4 / 41.2, mean 43.8) | s93301 FAIL (seq_next fired, 0.76); s31001 pass (0.76) | FAIL (one seed) |
| L13 soft10 + KL10 (shipped) | none by 8k (32.1 / 31.4) | 6,800 fails fewshot @8k both seeds | FAIL C1; C2 open (rising 14 -> 32) |
| L14 hard + KL30 | 4k only, one seed (HO 9.8) | 4k: passes (0.29) | C2 unread (no long run) |
| always-on add-on (L12-LA64 merged) | - | drop 88 | FAIL C1 |

## Round G arms (each ONE change vs L11 = kfsoft soft 1, KL10, 32 diary rows/update, factors re-measured every 500)
| arm | flags vs L11 | hypothesis | proved wrong if |
| **G0 = L11-16k** | none (L11 run to 16k) | reference: the trajectory of the one-change baseline past 8k | (reference, no hypothesis) |
| **G1 = KL30** | `--kl-weight 30` | a 3x stronger KL anchor stops the slow seq_next/fewshot readout leak without a learning tax (far: KL 10->30 moved HO 9.3->9.8 at hard mask; Main brain NK30 = best drop) | G1 fails C1 at its T* on either seed, OR T* is later than G0's by >= 4k |
| **G2 = parent factors** | `--guard-every 16000` (K-FAC factors measured once on the parent, never refreshed) | L11's slip GROWS with training (0.49 -> 0.76) because each refresh re-anchors the protected subspace to the already-drifted model; freezing it at the parent stops the accumulation | G2 fails C1 at T* on either seed, OR its 8k 6,800 drop is not below G0's 8k drop on both seeds |

Paired readings (item-paired, 6,800 rows, normal 95%): drop(G1) - drop(G0) and drop(G2) - drop(G0) at 8k and at T*.
If BOTH G1 and G2 succeed, the ship candidate is the one with the earlier T*; ties -> the lower max-over-seeds drop at T*.
If neither succeeds: next single change is decided from the round-G per-family lost sets, with bars written before launch.
Ship gate after a far success (unchanged from the solve doc): Main brain domain run (DM1/DM3) before any adoption; far success alone is not "ships".

## Addendum A (14:05Z, before any G1/G2/G3 launch; G0 launched 13:48Z with no change to its bars)
| **G3 = energy 0.999** | `--guard-energy 0.999` | the leak lives in the K-FAC energy TAIL: rare-family directions (fewshot_number_rule = 2.4% of the diary) fall in the unprotected last 1% of input energy at 0.99; protecting 99.9% covers them, and the soft-1 grading keeps the learning cost small | G3 fails C1 at its T* on either seed, OR T* is later than G0's by >= 4k |
Ship-choice rule extends to G3 unchanged (earliest T*, then lower max drop at T*).
Caveat recorded before G3 launch (from kf.py mask_for): the graded mask is M = min(1, tau/(s*p)) with tau = importance of the LEAST
important protected pair, so raising energy also lowers tau and hardens every protected pair's grade (like a larger s). G3 therefore
carries a real learning-tax risk (L13's soft 10 cost ~12 HO points at 4k); its C2 reading is as informative as its C1 reading.

## Addendum B (14:20Z, before launch): read the existing harder guard on both axes
| **G4 = L14-16k** | `--guard kfsoft --guard-soft hard --kl-replay-rows 32 --kl-weight 30` (the recorded L14 guard, unchanged) to 16k, both seeds | not a new arm: the goal requires every existing guard read on both axes; L14 was only ever read at 4k (HO 9.8, drop 0.29) | scored by the same SUCCESS rule. "Capped" if no T* by 16k and mean HO(16k) - mean HO(12k) < 2 |
L13 (shipped) is NOT extended: it already fails C1 on both seeds at 6k and 8k while mean HO(8k) = 31.8 < 36.6, so its T* is > 8k and
C1 would have to recover after failing; recorded as FAIL on the data in hand (re-opened only if G0 shows C1 recovering with training).

## Addendum C (15:10Z, before launch): per-family protection by KL-prioritized replay (draft code, coordinator review pending)
Motivated by diagnostic D1 (diag/README.md, measurement only, no DEV rows): fewshot_number_rule is lost even on the replayed diary rows
(9%), i.e. uniform replay (fewshot = 2.4% of the replay budget) loses the tug-of-war; seq_next is a coverage gap.
| **H1 = priority 0.5** | `--replay-priority 0.5 --replay-priority-every 500` (half the replay mass goes to diary families in proportion to their current KL to the frozen parent, re-measured every 500 updates on the diary only; the rest uniform) | per-family protection aimed where the drift is wins the tug-of-war on the readout families without extra total anchor weight, so no added learning tax | H1 fails C1 at its T* on either seed, OR T* later than G0's by >= 4k |
Mechanism check (reported, not a bar): 6,800 fewshot_number_rule family drop at 8k below G0's on both seeds; fewshot share of the
replay mass in the records rises above its uniform 2.4%.
Code: draft diff of domain/far/learn_probe.py (+139/-12), off path verified bit-identical to HEAD 62cf9ac36 (3 kfsoft updates, final
checkpoint sha 60ad8d75 both); 44/44 domain/far tests pass. Workers apply it as a patch; NOT committed or pushed.

## Addendum D (23:10Z Oct 17, BEFORE launch): confirm G1 on fresh seeds
Interim reading (from G SNAP lines; final reports pending): G1 meets the round-G SUCCESS rule at T* = 8k (mean HO 37.1 >= 36.6;
6,800 drop 0.71 / 0.65, nothing fired, both seeds). It is narrow (0.5 over the HO bar) and C1 fails at 10k on s93301
(fewshot_number_rule 5.5). Two seeds cannot separate a guard from a lucky pair, so before any "ships" verdict:
| **G1c** | G1 unchanged (`--kl-weight 30`, soft 1, 32 rows), seeds 31002 and 31003, 10k updates, reads 4k/6k/8k/10k |
Confirm bars (fixed now): the stop step is G1's T* = 8k, fixed in advance (no re-selection on new seeds).
- CONFIRMED if C1 holds at 8k on BOTH new seeds (6,800 house rule passes, drop <= 1.0) AND the 4-seed mean HO% at 8k >= 36.6.
- NOT CONFIRMED (G1 does not ship) if C1 fails at 8k on either new seed, or the 4-seed mean HO% at 8k < 36.6.
Reported: per-seed worst family at 8k and 10k; 4-seed mean HO and drop at 8k.

## Addendum E (02:50Z Oct 18, BEFORE G3-s31001's final report and before launch): conditional confirm of G3 on fresh seeds
Known at writing: G3-s93301 complete (C1 holds at every read 1k-16k, drop 0.44-0.63, worst family <= 4.0; HO 22.6 @8k -> 46.0 @16k);
G3-s31001 known only to 8k (HO 22.9, C1 pass). G3's T* (round-G rule) is therefore not yet known.
| **G3c** | G3 unchanged (`--guard-energy 0.999`, soft 1, KL10, 32 rows), seeds 31002 and 31003, 16k updates, reads 4k..16k every 2k |
Confirm bars (fixed now): stop step S = G3's T* as computed from the two ORIGINAL seeds (93301, 31001) by the round-G rule; S is not
re-chosen using the new seeds. If G3 has no T* by 16k on the original seeds, G3c is reported but cannot confirm anything.
- CONFIRMED if C1 holds at S on BOTH new seeds AND the 4-seed mean HO% at S >= 36.6.
- NOT CONFIRMED if C1 fails at S on either new seed, or the 4-seed mean HO% at S < 36.6.
Launched early only to save wall-clock (free cloud CPU); the bar does not depend on anything not yet observed.
