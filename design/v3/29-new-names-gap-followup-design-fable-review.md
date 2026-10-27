# 29 — "New names" after the 2/3 result: what holds seed 2103 back, and the one experiment to run next

**Fable reviewer (independent design review), 20–21 September 2026 — not an Astra document.**

Status: a NEW file. I edited no existing file, made no commit, trained nothing, used no cloud machine and
no BensPC. Nothing here amends or re-runs experiment 27: that registration is closed and its verdict
(PARTIAL, arm F 2/3, control 3/3, no claim) stands.

Paths are relative to the worktree
`/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27`
unless they start with `BASE/` (= `/Users/ben-hannan/Desktop/projects/beautiful-model`, read only).

---

## 0. What I read, what I ran, what I have been exposed to

**Read:** `artifacts/fable-newnames27-20260921/{RESULTS.md, report.txt, FREEZE-NOTE.md, FABLE-PREDICTIONS.md,
gates.json, readouts/*.json, scores/*.json, runs/*/training.json, logs/waves.log, logs/train-*.log}`;
`design/v3/27-…-fable-review.md` (my predecessor); `design/v3/21-…roadmap…`, `28-all-problems-handoff-fable.md`
(section B); `scripts/fable_newnames27.py`, `scripts/fable_newnames21.py`, `scripts/fable_confirmation_panels.py`
(cell table); `BASE/scripts/fable_operator_startup.py` (`training_batch_blind`),
`BASE/scripts/fable_operator_variants.py` (`lr_at`), the frozen `toy_ladder.LadderSpec`.

**Ran (one probe, scratch folder outside the repo, 2 threads, under a minute, NO checkpoint loaded, NO seed
used):** a model-free look at the frozen panel files and the frozen code pool — how many people and story
lines each cell has, and how alike the closest two names in each test world are, for the trained-pool draw
and the reserved-pool draw. Everything else below is arithmetic on JSON files already on disk.

**What I could not do, by rule:** run any seed-2103 checkpoint. Experiment 27's score files keep totals per
cell, not a record per question (the scorer's per-question `records` are thrown away,
`fable_newnames27.py:867`). So "which questions did 2103 miss, and were they the look-alike-name worlds?"
cannot be answered from disk. Section 2.7 makes sure the next experiment can answer it.

**Exposure:** I have seen every experiment-27 number. My forecasts in section 4 are informed by them.

---

## 1. Diagnosis: what most likely limits seed 2103

### 1.1 The short version

Seed 2103 is not broken in some special way. **Every** new-names run makes about twice as many name mistakes
when a story has 12 people instead of 6 — and 12-person stories are *never* in training. Seed 2103 simply
has the highest basic mistake rate of the three seeds (about 1.5× the others, in both arms), crowding doubles
it, and the doubled number lands just under one strict cutoff. The "fails only on never-trained names" label
that fired is mostly a coin-flip that happens to any seed sitting near a cutoff (section 1.5). The basic
mistake rate was still falling when training stopped.

### 1.2 Fact: 12-person worlds are not "under-represented" in training — they are absent

`training_batch_blind` draws every training world from `LadderSpec()` whose default is 6 people, and asserts
it (`assert len(world.ents) == 6`; the accounting line `twelve_person=0`). From my panel probe:

| cells | people in the story | story lines (mean) | closest pair of names *present in the story* (mean cosine) | worlds whose closest pair is > 0.45 |
|---|---|---|---|---|
| c1–c6, s3 | 6 | 44.4 | 0.25 | 1 % |
| p12-1, p12-2, p12-3 | 12 | 68.4 | 0.335 | 4–5 % |
| training (full-length stories) | 6 | 44.75 | — | — |

So the p12 cells are a double stretch for the model: twice as many names to tell apart, and stories 54 %
longer than anything it has trained on. The ordinary fixed-name control shrugs this off (512/512) because its
16 names are hand-tuned rows it has met thousands of times. The new-names arm has to match *random* vectors,
some of which look alike, by content.

### 1.3 Fact: crowding doubles the mistake rate in every run, and 2103 has the highest starting rate

First-step "who is X linked to?" mistakes on never-trained names (from `readouts/*.json`, attention section):

| run | 6-person cells (of 3,072) | 12-person cells (of 1,024) | ratio |
|---|---|---|---|
| F-2103 | 2.5 % | **7.2 %** | 2.9× |
| F-2104 | 1.6 % | 3.2 % | 2.0× |
| F-2105 | 1.6 % | 2.5 % | 1.6× |
| L-2103 | 2.8 % | **5.1 %** | 1.8× |
| L-2104 | 1.9 % | 3.6 % | 1.9× |
| L-2105 | 1.8 % | 3.0 % | 1.7× |

Going from 5 other people in the story to 11 is 2.2× as many wrong candidates; the mistake rate goes up
1.6–2.9×. That is what "each extra person in the story is one more chance to grab the wrong line" predicts.
A two-step 12-person question at the 487/512 mark allows about 25 misses; with roughly one miss coming from
the second step, the first step must stay under about 4.5 %, which needs a 6-person rate of about 2 % or
less. Seeds 2104/2105 are at 1.6–1.9 %. Seed 2103 is at 2.5–2.8 % in **both** arms. That is the whole gap.

Where the misses happen: in only 19–39 % of the 12-person misses was the model looking at the right story
line (and then said the wrong name). The majority are **wrong-line** misses — it found the wrong person's
fact. So the pointer head (M1c), which only repairs "right line, wrong name", would not fix most of this.
Its pre-named trigger (`copy_side_failure`) did not fire, and I agree it should stay parked.

The second step is fine: given the right middle person, the final attribute look-up is 506–512 of 512
everywhere (`terminal_oracle`). All the damage is in finding-and-saying names.

### 1.4 The five suspects, one by one

| Suspect | Verdict | Evidence |
|---|---|---|
| **Undertraining** | **Most likely the lever. Supported, not proven.** | The story-growing curriculum only reaches full-length stories at update 3,000, and the learning rate starts gliding down at 4,000 (`lr_at`: flat to 4,000, linear to 1e-4 at 6,000). So the model gets just 1,000 full-speed updates on full-length stories. Training-batch link accuracy, pooled over the six F/L runs in 500-update windows from 3,000 on: 0.947, 0.961, 0.966, 0.981, 0.975, 0.986 — still climbing at the end, no flat stretch. F-2103 ran 1–6 points behind the average of the other two F seeds in every window from 2,500 to 4,000. What I cannot tell: how much of the late gain is real learning and how much is just the smaller learning rate calming the noise, and whether there is a floor (see "geometry"). |
| **Too few distinct names/worlds seen** | **No.** | 96,000 training worlds × 16 names from 3,072 codes = each code met ~500 times, always in new company. The average cost of a never-trained name versus a trained one, over all 60 run-cells, is 2.6 questions in 512 (0.5 of a point). Names generalise. |
| **12-person worlds missing from training** | **True, and it is why the p12 cells are the weak spot — but it is the amplifier, not the root.** | Section 1.2–1.3. The amplifier is roughly the same ×2 for every seed; what differs between seeds is the basic rate it multiplies. Lowering the basic rate fixes p12 without touching the training data; adding crowded worlds to training would also work but changes what the p12 cells mean (section 2.2). |
| **Code-pool geometry (max cosine 0.676)** | **Not the cause of the 2103 gap; possibly a floor for everyone. Cannot be settled from disk.** | The 0.676 is the closest pair among all 4,096 codes; it matters for the open-set read-out (each code's nearest neighbour among 4,096 has cosine ≈ 0.52, which is why "pick among all 4,096" is only 0.55–0.64). Inside one 16-name world the closest *present* pair averages 0.25–0.34. The reserved draw is not unluckier than the trained-pool draw (p12-2: 25 vs 20 look-alike worlds; p12-3: 18 vs 22), and all seeds share the same draw, so geometry cannot explain why 2103 differs. One hint of a floor: on c2 with trained-pool names, **all six** runs score 505 or 506 — about seven questions nobody gets, and about five c2 worlds have a look-alike pair. Whether those are the same questions is exactly what the missing per-question records would show. |
| **Shared world stream (Q1)** | **Cannot explain 2103.** | All seeds and arms see the same worlds, so the stream cannot make one seed worse than another. What F-2103 and L-2103 share that the other seeds do not is the starting weights, the curriculum's random stream and the name stream. Q1 limits how far a *claim* stretches (section 3), not this diagnosis. |

### 1.5 The "reserved gap" that fired is mostly threshold-straddling, not a generalisation failure

`reserved_gap` means "passes all ten cutoffs with trained-pool names, fails with reserved names". For a seed
whose p12-2 score sits near 487, that is close to a coin toss, for two reasons visible in the table of
paired differences:

* There is a small **common offset shared by all six runs** on some cells (c5: −8, −7, −3, −6, −5, −5; c2:
  −7, −3, −2, −8, −5, 0) and none on others (c6, s3, c1, p12-1 all near 0). Six different models agreeing
  cell by cell points at the particular frozen draw of panel names, or a small real cost of novelty — one
  draw cannot separate the two; a fresh panel draw will.
* The 12 paired differences on p12-2/p12-3 have mean −5.9 and spread (sd) 6.6. The −13 mark therefore sits
  about one spread from the average: roughly one p12 cell-seed in seven or eight crosses it by luck at experiment
  27's error level. L-2103 — same starting weights as F-2103 — shows −7 and 0 on the same two cells. A real
  "cannot handle unseen names" defect in that seed would not vanish like that.

So: the honest reading of F-2103's −15/−19 is "a weak seed near a cutoff, plus about 1.7 spreads of bad luck
on two neighbouring cells, on top of a real but small (≈ 1 point) novelty cost on crowded chained cells".

### 1.6 What cannot be told from disk

(i) Whether misses concentrate in look-alike-name worlds. (ii) Whether 2103's handicap comes from its starting
weights, its curriculum stream or its name stream. (iii) Whether the late-training gain is learning or
learning-rate calming. (iv) Whether the common offset is the panel draw or a novelty cost.

---

## 2. Decision: (a) — one fresh registration with ONE change: more full-speed training (10,000 updates)

### 2.1 Why not (b) "move on"

For a 6-person, ≤ 3-step demo, experiment 27's checkpoints are already good enough (97–99 % per step on new
names) and nothing below should block M0, M2 or the talker — run this in parallel. But the weakness is on the
*crowding* axis, and the roadmap's M3 ("grow past 16 people", which M1 exists to unlock) is nothing but
crowding. A mistake rate that doubles from 6 to 12 people is the early form of M3's failure. It is worth two
free Mac waves to find out whether plain extra training halves the basic rate before building on it.

### 2.2 Why not the other single changes

* **"Same again, fresh seeds" (design 27's pre-named PARTIAL path).** I depart from it, on arithmetic from
  27's own six new-names runs: p12-2 scored 479, 485, 490, 494, 497, 498 against a 487 cutoff. About a third
  of runs fall short, so three fresh seeds all clearing it is roughly a 0.3 chance, before the paired mark.
  The likeliest outcome is PARTIAL again, having learned nothing.
* **Add 12-person worlds to training.** It would probably work, but it turns the p12 cells from a stretch
  test into a seen-it-before test (a weaker claim than the control earns), changes the shared world stream
  and so the control's recipe, and is a real data-pipeline change. It is the right *next* step if more
  training does not help (section 2.9), not the first.
* **Gate arm L instead of F.** L is the cleaner sentence ("only the start value changed") and scored the same.
  But swapping the gated arm is a second change, and L keeps a small collapse risk a 3/3 gate would pay for.
  F stays gated; L runs again as a descriptive arm and gets its own forecast.
* **Pointer head, bigger pool, wider model:** no trigger fired; most misses are wrong-line, not wrong-name.

### 2.3 Experiment 29 / "M1-F10": the one change

Relative to experiment 27: **the full-speed part of the learning-rate schedule is 4,000 updates longer.**
Warm-up over 100 updates, 1e-3 held through update 7,999 (was 3,999), then the same 2,000-update straight
glide to 1e-4; **10,000 updates in all** (was 6,000). Everything else is 27's recipe byte for byte: hint off
at 1,000, stories grow 1,500 → 3,000, 16 visits, frozen scale 1.2, AdamW, clipping, loss, model, pool,
scorer. Time at full speed on full-length stories goes from 1,000 updates to 5,000. The change applies to the
control too, so the arms stay budget-matched. Updates 1–4,000 are identical to 27's schedule, so every
50-update bit-identity proof from 27 carries over unchanged.

Why 10,000 and not 12,000: the clock, decided before any data. 27 measured 693 s per F run and 0.131–0.146 s
per late (full-length) update with six jobs running. 10,000 updates ≈ 21 min training + 2.5 min scoring;
12,000 ≈ 25.7 + 2.5 min, inside the 28-minute trainer cap only if nothing else touches the machine. If five
times more full-speed practice does not show the effect, six times would not either. The number is not to be
re-tuned after any outcome.

### 2.4 Arms, seeds, waves

| Arm | What | Updates | Gated? | Seeds | Wave |
|---|---|---|---|---|---|
| control | fixed name table, 27's control with the longer schedule | 10,000 | VOID rule only | 2106, 2107, 2108 | 1 |
| **F** | re-drawn codes, scale frozen at 1.2, longer schedule | 10,000 | **yes — the verdict** | 2106, 2107, 2108 | 1 |
| L | re-drawn codes, scale learned from 1.2, longer schedule | 10,000 | no — descriptive | same | 2 |
| F6 | **exactly 27's arm F** (6,000 updates, 27's schedule) | 6,000 | no — descriptive | same | 2 |

F6 is the arm that makes the result interpretable. With fresh seeds, a 3/3 pass alone cannot separate "more
training helped" from "these three seeds were luckier" (a ~0.3 event). F6 shares F's starting weights,
curriculum stream and name stream, so per seed it is a same-everything comparison of 6,000 against 10,000
updates. Free built-in check: F and F6 must have the **same fingerprint at update 4,000**.

Seeds 2106–2108 are fresh (2100–2105 spent, 9 is the fixture); 2109–2111 stay unspent. Both waves are
registered and hashed together before wave 1; the wave-1 verdict is sealed before wave 2's scores exist.
Wave 1 ≈ 23.5 min; wave 2 (F6 done at ~11.5 min, L at ~20) ≈ 23 min. Six single-thread jobs each. $0.

### 2.5 Data, marks and verdict rules

* **Pool:** reuse the frozen 3,072 / 1,024 pool by hash-checked reference. Reserved codes are still untrained.
* **Panels:** a FRESH ten-cell suite, new namespace and seed base, same generator, 512 units per cell, 16
  bound codes per world; fresh panel-code namespace, seed-independent so trained-vs-reserved stays paired.
* **Streams:** `random.Random(1101)` worlds, shared (section 3); new name-stream namespace
  `newnames29/train-codes:<seed>` shared by F, L and F6; forbidden check (registered exclusion ∪ the fresh
  panels) at every one of the 10,000 updates.
* **Marks — unchanged from 21/27, per seed, never averaged:** reserved-name scoring ≥ 487/512 on c1, c2,
  p12-1, p12-2 and ≥ 461/512 on c3–c6, p12-3, s3; paired reserved-minus-trained ≥ −13 on every cell, with
  the two-sided warning line. Final checkpoint only, no selection, run once.
* **Verdicts (arm F):**
  * **PASS** — all three seeds meet all ten cutoffs **and** the paired mark on every cell.
  * **PASS-WITH-GAP** *(new tier, declared now)* — all three seeds meet all ten reserved-name cutoffs, but
    at least one cell-seed breaks the paired mark. Licenses only the narrower sentence in 2.8.
  * **PARTIAL** — exactly two seeds meet all ten cutoffs. No claim. **FAIL** — one or none. No claim.
  * **VOID** — the control meets the ten cutoffs in fewer than 2/3 seeds.
  * **INVALID** — the arm-F/F6 scale buffer is not exactly 1.2 at the end; a run records the wrong number of
    updates, any override, or a different source fingerprint; the logged learning rate differs from the
    declared schedule at any logged row; F and F6 fingerprints differ at update 4,000 for any seed; the
    forbidden check trips.
  * A wave killed by the time cap may be re-run once, unchanged, only if no score file has been opened.
    No amendment after launch.

Why I add a tier instead of moving the −13 line, decided BEFORE data: the two marks answer different
questions. The ten cutoffs ask "can it do the job with names it never trained on?" — that is milestone M1.
The paired mark asks "is a new name any harder than a familiar one?" — a cost-of-novelty question. Section
1.5 shows the paired mark, at 27's error level, is tripped by luck in about one p12 cell-seed in seven.
Loosening a mark straight after it bit would be the wrong precedent, so −13 stays and PASS still needs it;
the tier just stops a noisy secondary mark from erasing a true primary result, and forces the gap to be
printed next to the claim. The coordinator may strike this tier at freeze; then 27's rule applies unchanged.

### 2.6 Pre-named failure signatures (mechanical, descriptive, never move a verdict)

27's six, same definitions and precedence: `scale_collapsed` (L only), `name_blind` (+ sub-label),
`never_started`, `copy_side_failure`, `reserved_gap`, `unnamed`. Added, as non-exclusive tags:

| Tag | Definition | Meaning |
|---|---|---|
| **crowding_only** | a seed that misses any mark meets all seven 6-person reserved cutoffs (c1–c6, s3) and both paired marks there; every miss is on a p12 cell | more practice did not cure crowding → next step is crowded worlds in training (2.9), not more updates |
| **straddle** | a seed meets all ten reserved cutoffs and breaks only the paired mark | the PASS-WITH-GAP case; read the per-question records |
| **late_instability** | training-batch link accuracy averaged over updates 9,000–10,000 is more than 2 points below its 5,000–6,000 average in any run, or a control seed misses a cutoff | the long flat phase hurts; stop and think |
| **undertraining_supported / _refuted / _unclear** (experiment-level) | pooled first-step link mistake rate on p12-2 + p12-3, reserved names, per F seed (27's F seeds: 7.2 %, 3.2 %, 2.5 %). *supported*: all three ≤ 2.5 %. *refuted*: the median ≥ 3.2 %. Otherwise *unclear*. The F-vs-F6 same-seed comparison is printed beside it | whether section 1's main suspect was right |

### 2.7 Logging to add (all proven inert)

27's 100-update trace plus the learning rate actually used; a weight fingerprint at update 4,000 (F, F6);
and — the gap that blocked this review — a compact **per-question record** for every coded run, cell and pool
(question index, right/wrong for the whole question and for the first link step, which name was chosen,
cosine between the right and the chosen name, and the closest other present name to the asked person and to
the answer). Descriptive table fixed now: mistake rate in the tenth of worlds with the closest look-alikes
versus the rest, and an exact paired test (same world, trained vs reserved names) per seed. Open-set and
attention read-outs as in 27. If the panel generator accepts 16 people with no code change, one descriptive
`p16-2` cell (prediction from 1.3: mistake rate ≈ 3× the 6-person rate); otherwise skip it.

### 2.8 What a pass would and would not license

* **PASS:** *"On this toy, with one shared stream of training worlds and three seeds, an operator trained for
  10,000 updates with every name re-assigned at random in every world — and the loudness of names fixed by
  hand at 1.2 — answers one-, two- and three-step questions about 1,024 names it never trained on, choosing
  among the 16 names bound in the story, including 12-person stories half as long again as any it trained
  on, to the marks the ordinary fixed-name version is held to, and no more than 13/512 worse than with
  familiar names."*
* **PASS-WITH-GAP:** the same sentence **without** its last clause, **plus** "on cell(s) X, seed(s) Y, never-
  trained names scored Z/512 below trained names."
* **Not licensed by either:** "open vocabulary" or anything about choosing among thousands (open-set stays a
  read-out; 27 measured 0.55–0.64); "a learned loudness works" (arm L is descriptive); "more training was the
  cause" as a registered finding (F-vs-F6 is descriptive, three seeds); anything about text names, English,
  the dispatcher or the talker; anything beyond 12 people; anything about other world streams.
* **PARTIAL / FAIL / VOID / INVALID:** no claim.

### 2.9 What happens next, fixed now

PASS or PASS-WITH-GAP → freeze the 10,000-update recipe as the M1 operator and go to M2; do not polish.
Anything else with `crowding_only` → one design (30): mix 12-person worlds into training, relabel the p12
cells as seen-in-training, add a 16-person stretch cell. `copy_side_failure` → pointer head, as in design 27.
`late_instability` or a 6-person cell failing → stop and think. **No third "same again" registration**: if
more practice does not do it, more seeds will not.

---

## 3. Should the shared world stream (Q1) be lifted in this follow-up? No — lift it at confirmation time.

* **What lifting buys:** the claim could drop "with one shared stream of training worlds", and the three
  seeds would be fully independent repeats. It would *not* have helped seed 2103 (section 1.4).
* **What it costs:** the control's proof today is the strongest kind — the registered runs *are* the
  registered recipe, `random.Random(1101)` included, tensor for tensor. Give each seed its own stream and that
  becomes "same code path, shown on a fixture with stream 1101; the registered runs use a different number" —
  still sound, but one link weaker, and no registered control could be compared with any earlier control. It
  is also a second change in an experiment whose point is to attribute one. Risk of leakage is unaffected
  either way (the forbidden check runs at every update).
* **How much it probably matters:** little. A run sees 160,000 worlds; two such streams are two huge samples
  of the same generator. Differences between seeds are dominated by starting weights.
* **Ruling:** keep 1101 and the limitation sentence in 29. Lift Q1 once, for all arms, in the confirmation
  population when the M1+M2 recipe is frozen: world stream keyed by seed, arms within a seed still sharing it,
  bit-identity shown on the fixture with 1101.

---

## 4. Calibration note and forecasts

**What went wrong with `reserved_gap` (0.05 and 0.12; it fired).** Both forecasters priced the *story* behind
the label — "matching fails to generalise to unseen codes", which really is unlikely after 3,072 random
training codes — instead of the *definition*: "clears every cutoff with trained names, misses one with
reserved names". That fires whenever a seed sits within a few questions of a cutoff and the two scorings land
on opposite sides. The same forecasters gave 0.45 to "some seed fails just under a cutoff" (`unnamed`) and did
not notice that `reserved_gap` outranks `unnamed` in precedence, so a near-miss is *relabelled* whenever the
trained-pool score is a few questions higher — which a −3 to −6 common offset makes the usual case. A fair
price was 0.2–0.3. Rule for next time: for every named signature ask "what is the *cheapest* way this label
fires?" and price that from the noise arithmetic (spread of a paired difference ≈ √(sum of the two miss
counts); distance of the weakest plausible seed from the cutoff), not from the mechanism in its name.

| # | Statement (experiment 29) | Probability |
|---|---|---|
| R29-P1 | Arm F: PASS (3/3, ten cutoffs and paired mark) | **0.42** |
| R29-P2 | Arm F: all three seeds meet the ten reserved cutoffs (PASS or PASS-WITH-GAP) | 0.55 |
| R29-P3 | Arm F: at least two seeds meet the ten cutoffs | 0.85 |
| R29-P4 | Control meets the ten cutoffs in ≥ 2/3 seeds (not VOID) | 0.93 |
| R29-P5 | The paired mark is broken in at least one arm-F cell-seed | 0.30 |
| R29-P6 | `reserved_gap` in at least one F seed | 0.22 |
| R29-P7 | `reserved_gap` in at least one of the nine coded runs (F, L, F6) | 0.50 |
| R29-P8 | Every F seed that misses any mark is `crowding_only` (void if none misses) | 0.70 |
| R29-P9 | `undertraining_supported` (all three F seeds ≤ 2.5 % first-step link mistakes on p12-2+p12-3) | 0.35 |
| R29-P10 | `undertraining_refuted` (median ≥ 3.2 %) | 0.20 |
| R29-P11 | F has fewer total reserved-name misses over the ten cells than F6 at the same seed, in all three seeds | 0.60 |
| R29-P12 | Same, in at least two of three seeds | 0.85 |
| R29-P13 | F6 (27's recipe, fresh seeds) meets all marks 3/3 | 0.25 |
| R29-P14 | Arm L meets all marks 3/3 | 0.38 |
| R29-P15 | Arm L `scale_collapsed` in at least one seed | 0.05 |
| R29-P16 | Open-set B (all 4,096 codes) pooled ≥ 0.65 in every F seed | 0.35 |
| R29-P17 | The mean of arm F's 30 paired differences is negative (a real, small cost of new names, not just 27's panel draw) | 0.80 |
| R29-P18 | 12-person ÷ 6-person first-step link mistake ratio lies in [1.5, 3.0] in all three F seeds | 0.55 |
| R29-P19 | `late_instability` in any run | 0.07 |
| R29-P20 | Wave 1, training plus scoring, finishes within 27 minutes | 0.85 |

How P1 is built: I give 0.55 to "more full-speed practice cuts the basic mistake rate by a third or more".
If so, each seed clears the cutoffs about 0.93 of the time (0.80 for three) and the paired mark is kept about
0.88 of the time → 0.70. If not, 27's arithmetic applies: about 0.33 for three seeds and about 0.55 for the
paired mark → 0.18. Blend ≈ 0.47; I shade to 0.42 for things I have not thought of (three of my predecessor's
and the coordinator's misses were of that kind).

---

## 5. Builder brief (Opus implementer)

1. New files only: `scripts/fable_newnames29.py`, `tests/test_fable_newnames29.py`, `artifacts/fable-newnames29-<date>/{run_data.sh,run_train.sh,run_score.sh,BUILD-NOTES.md}`. Import `fable_newnames27` (and through it 21); copy nothing, edit nothing, `exist_ok=False` everywhere; never write into 21's or 27's folders.
2. Constants: seeds (2106, 2107, 2108); arms control+F (wave 1, gated), L+F6 (wave 2, descriptive); updates 10,000 (F6: 6,000); scale 1.2; namespaces `newnames29/train-codes` (one stream per seed, shared by F, L, F6), `newnames29/panel-codes`, fresh panel namespace and seed base; pool by hash-checked reference; worlds `random.Random(1101)`.
3. The one change, without touching frozen modules: learning rate = `V.lr_at(step)` for step < 4,000; 1e-3 for 4,000 ≤ step < 8,000; `V.lr_at(step − 4,000)` from 8,000 on. Hint and curriculum must keep seeing the TRUE step. F6 uses `V.lr_at` untouched.
4. Proofs on fixture seed 9 only (registered seeds refuse every override and any run before freeze): control-equivalence as in 27; arm F ≡ 27's arm F tensor for tensor over 50 updates; a unit test of the schedule over all 10,000 steps plus short fixture runs across updates 3,990–4,010 and 7,990–8,010 asserting the optimiser's actual learning rate; inertness of every new log.
5. Logging: 27's trace + `lr`; `fingerprint_at_4000` for F and F6; compact per-question records for every coded run/cell/pool (design 2.7) taken from `score_cell`'s `records` or a separate descriptive forward pass — never by altering the scorer; prove scores are identical with and without.
6. Gates: cutoffs and paired mark imported unchanged; verdict tiers exactly as design 2.5 (PASS, PASS-WITH-GAP, PARTIAL, FAIL, VOID, INVALID); signatures = 27's six + `crowding_only`, `straddle`, `late_instability`, `undertraining_*` (2.6), all mechanical from JSON; `gates --wave 1` seals `wave1-verdict/` before wave 2 trains.
7. `run_integrity`: exact update count per arm, one source fingerprint, no overrides, logged `lr` equals the schedule at every row, F/F6 fingerprints equal at 4,000 per seed, F/F6 buffer exactly 1.2.
8. `run_*.sh`: six single-thread jobs per wave, 27's watchdog caps (28/29 min), refuse to start if any score file exists, `waves.log` as in 27. Budget: wave 1 ≈ 21 + 2.5 min, wave 2 ≈ 20 + 2.5 min.
9. Data audit: fresh panels against the registered exclusion; forbidden check live at every update to 10,000 (the world stream is consumed 67 % further than ever before — confirm it never trips on the fixture replay).
10. Hard gates before freeze: all tests green; independent audit says FREEZE-READY; FREEZE-NOTE hashes design 29, script, tests, run scripts, panels, pool reference, both forecast files; forecasts hashed before any code.
11. Report prints every seed and cell, the paired table, the F-vs-F6 same-seed table, the look-alike table and the claim sentence chosen by the verdict tier — nothing averaged across seeds.

---

## 6. Five lines for Ben

1. **What holds 2103 back:** nothing exotic. Every new-names run makes about twice as many name mix-ups in a
   12-person story as in a 6-person one, and it has never trained on a 12-person story; 2103 just starts from
   the highest mix-up rate (2.5–2.8 % against 1.6–1.9 %), so its doubled rate slips under one strict mark.
2. **The scary label was mostly luck:** "fails only on never-seen names" fires whenever a run sits right on a
   cutoff; the same starting weights in the other arm showed no such gap. The real cost of a brand-new name
   is about half a point.
3. **What I would run:** the same experiment with one change — 10,000 updates instead of 6,000, all of the
   extra at full learning speed (the model was still improving and had only 1,000 full-speed updates on
   full-length stories). Fresh seeds 2106–2108, fresh test questions, same pass marks, two free Mac waves
   under 25 minutes each. A side arm repeats the old 6,000-update recipe on the same seeds, so we can tell
   "more practice helped" from "luckier seeds".
4. **Odds:** 42 % full pass, 55 % that all three runs clear every never-seen-name cutoff, 85 % at least two.
5. **Meanwhile:** the demo path is not blocked — 27's models are already good enough for small worlds. If more
   practice does not fix crowding, the next move is to put crowded worlds into training, not to try more seeds.

---

## 7. Claim limits of this file

* This is a design review, not a result. It trained nothing and scored nothing; it licenses no claim about
  the model beyond what `artifacts/fable-newnames27-20260921/RESULTS.md` already says.
* The diagnosis rests on totals per cell, six new-names runs, one frozen panel draw and one model-free probe
  of the panel files. "Undertraining is the main lever" is my best-supported hypothesis, not a finding; the
  ×2 crowding ratio is an observation on six runs, not a law; the "about seven questions nobody gets" floor
  is a hint I could not check.
* The statements about chance (one p12 cell-seed in seven; ~0.3 for a no-change replication) are rough normal
  arithmetic on 12 and 6 numbers. They are good enough to choose a design, not to quote.
* I did not examine any seed-2103 checkpoint and did not use seeds 2100–2105 in any computation.
* The PASS-WITH-GAP tier and the 10,000 figure are proposals fixed before data; the coordinator and the
  auditor may strike or keep them at freeze, but not after launch.
* My forecasts were written after seeing all of experiment 27. They are not blind.
