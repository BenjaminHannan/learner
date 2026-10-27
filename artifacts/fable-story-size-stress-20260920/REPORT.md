# How big can the story get before the lookup model breaks?

**2026-09-20 · Track A · evaluation only — nothing was trained, nothing was written into any
checkpoint folder.**

Preregistration: `PREREGISTRATION.md`,
sha256 `ab4f3c0db0f84524486a6c3fc27132388e7d702f0c8344541741372d54a5c4f4`
(written and hashed before any stress cell was evaluated).
Raw numbers: `raw/<checkpoint>.json` · grid geometry and exclusion audit: `geometry.json` ·
checkpoint hashes: `manifest.json`.

**This is exploratory development evidence, not a confirmation run.**

---

## The short answer

**It holds essentially all the way to the biggest story we can build, and the small amount
of breaking that does happen is a per-seed weakness in one relation, not a size wall.**

The models under test were trained *only* on tiny stories: 16 fact rows, no filler at all,
2,500 updates, and then never trained again. We showed them stories up to **678 rows and
about 5,100 tokens** — roughly **15x more rows than the ordinary story** they already
handled, and **28x more rows than anything they ever trained on** — with all 64 facts a
world can hold, including 40 rows about ten people the question is not about.

* Two of the three arm-A seeds stayed at **94.5%–100%** attribute accuracy in **every** cell,
  including the biggest.
* The weakest seed (seed 2) slid from **99.6% -> 84.2%**. That slide is *gradual*, it is
  concentrated in **one relation (token 10)**, and even at its worst it is 13x chance.
* The six `grow-blind` checkpoints — the ones that did see growth during training — were
  **100% in 59 of 60 cells**, and their **two-call two-hop execution was 100%** everywhere
  too.
* The never-learned control (arm D) sat at chance in every single cell, exactly as it
  should.

So "where does it break?" has an unsatisfying but honest answer: **inside this grid it
mostly doesn't.** The measurable cost of a 28x bigger story is a few percentage points on
one seed and one relation.

---

## What we actually did

We built 64 **full 16-person worlds** — 64 fact rows each, the most this toy's vocabulary
can hold. In each world a fixed **6-person subset** carries all the questions, so the
*same* 512 attribute questions, 256 LINK questions and 256 two-hop questions are answerable
in every cell of the grid. Then we varied two things and nothing else:

| axis | settings |
| --- | --- |
| **facts** | `F24` = only the subset's own 24 fact rows · `F64` = all 64 (10 extra people as distractors) |
| **filler** | 0x, 1x, 3x, 10x, 30x the generator's own filler-and-gap rows (1x = its normal amount) |

The bigger filler sets *contain* the smaller ones (they are nested), the fact rows and their
order never change along the filler axis, and the questions and answers are bit-identical in
all ten cells. That is what "paired" means, and it is the correction the design owner asked
for after the old size sweep drew different worlds for every size and never tested a full
64-fact world.

Story sizes that produced:

| cell | rows / story | tokens / story |
| --- | ---: | ---: |
| F24 / 0x | 24 | 139 |
| F24 / 1x | 44 | 297 |
| F64 / 1x | 84 | 543 |
| F64 / 10x | 269 | 1,964 |
| **F64 / 30x** | **677** | **5,114** |

For comparison: an arm-A training story was 16 rows with no filler at all.

---

## Table 1 — `factorial-A` (trained only on 16-fact, filler-free stories)

Attribute accuracy, per seed, never averaged. Chance = 0.063.

| filler | F24 s0 | F24 s1 | F24 s2 | F64 s0 | F64 s1 | F64 s2 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 0x | 1.000 | 0.994 | 0.996 | 0.998 | 0.963 | 0.992 |
| 1x | 1.000 | 0.994 | 0.975 | 0.998 | 0.963 | 0.969 |
| 3x | 1.000 | 0.994 | 0.961 | 0.998 | 0.965 | 0.957 |
| 10x | 1.000 | 0.992 | 0.910 | 0.994 | 0.961 | 0.918 |
| 30x | 1.000 | 0.955 | **0.842** | 0.994 | 0.945 | **0.844** |

LINK accuracy (same checkpoints; see the correction note below — these models *did* train on
one-call LINK):

| filler | F24 s0 | F24 s1 | F24 s2 | F64 s0 | F64 s1 | F64 s2 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 0x | 1.000 | 0.996 | 1.000 | 1.000 | 0.984 | 1.000 |
| 1x | 1.000 | 0.996 | 1.000 | 1.000 | 0.984 | 1.000 |
| 3x | 1.000 | 0.996 | 1.000 | 1.000 | 0.984 | 1.000 |
| 10x | 0.992 | 0.996 | 1.000 | 0.992 | 0.984 | 1.000 |
| 30x | **0.934** | 0.996 | 0.992 | **0.922** | 0.984 | 0.996 |

## Table 2 — `grow-blind` (trained with growth, six seeds)

Attribute accuracy:

| filler | F24 s0–s5 | F64 s0–s5 |
| --- | --- | --- |
| 0x | 1.000 x6 | 1.000 x6 |
| 1x | 1.000 x6 | 1.000 x6 |
| 3x | 1.000 x6 | 1.000 x6 |
| 10x | 1.000 x6 | 1.000 x6 |
| 30x | 0.990, 1.000, 1.000, 1.000, 1.000, 1.000 | 0.990, 1.000, 1.000, 1.000, 1.000, 1.000 |

LINK accuracy is 1.000 in all 60 cells except `F24 / 30x` seed 4 (0.996).
**Two-call two-hop execution** (256 questions, same grid) is 1.000 in all 60 cells except
`F24 / 30x` seed 4 (0.996), where the single failure is in the LINK call.

## Table 3 — `factorial-D` (never learned; negative control)

| filler | F24 s0 | F24 s1 | F24 s2 | F64 s0 | F64 s1 | F64 s2 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 0x–30x (identical in every cell) | 0.051 | 0.043 | 0.066 | 0.051 | 0.043 | 0.066 |

Each arm-D checkpoint emits **one constant token** for every question in every cell, so its
"accuracy" is just how often that token happens to be the answer — chance, 1/16 = 0.063. The
control behaves exactly as a never-learned model should, which is what makes the arm-A and
grow-blind numbers meaningful.

## Where the attention goes

The obvious way for a big story to break a lookup model is that its attention gets spread
thinner as the story gets longer. **That is not what happens.** Mean attention mass on the
correct supporting row (averaged over 4 heads and 3 read steps) is almost flat, while the
mass you would get from spreading attention evenly over the story collapses:

| F64 cell | correct-row mass, A s0 | correct-row mass, A s2 | correct-row mass, GB s0 | uniform | A s0 / uniform |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0x | 0.543 | 0.485 | 0.609 | 0.0157 | 35x |
| 1x | 0.541 | 0.478 | 0.604 | 0.0111 | 50x |
| 3x | 0.540 | 0.470 | 0.598 | 0.0070 | 78x |
| 10x | 0.535 | 0.455 | 0.585 | 0.0031 | 178x |
| 30x | 0.526 | 0.435 | 0.566 | 0.0012 | **455x** |

Adding 600 junk rows costs the model about **3% of its attention** on the right row (arm A
seed 0: 0.543 -> 0.526). Relative to an unfocused reader it gets *more* selective, not less,
because there is more junk to ignore and it keeps ignoring it.

The answer-logit margin (how far ahead the right answer is) also only sags: arm A seed 0
5.89 -> 5.22 across the whole F24 sweep; seed 2 5.56 -> 3.89; grow-blind seed 0 stays near 13.

---

## What this means

* **The rule the short-story models learned is genuinely size-independent.** It is not a
  trick that happens to work on 45-row stories. It survives 28x more rows, 2.7x more facts,
  and ten extra people whose rows use the same relations and the same value pool.
* **The failure that does appear is not a length failure — it is a weak-relation failure.**
  In arm-A seeds 1 and 2 the errors pile into relation token 10: seed 2 at F24/30x is 0.906
  on relation 8, 0.906 on relation 9, and **0.713** on relation 10. Relation 10 is the toy's
  held-out two-hop relation, so in this training recipe it is the one relation that is only
  ever practised as a plain one-hop question, never as the second half of a link-then-look-up
  pair. It gets the least practice and it is the first thing to wobble.
* **Growth during training buys robustness, cheaply.** `grow-blind` — the same loss, the same
  architecture, the same 79,316 parameters, just trained through a story that grows — is
  perfect where arm A wobbles, and composes two calls perfectly at 678 rows.
* **Extra people are a mild cost; extra junk is a mild cost; together they are still mild.**
  Going F24 -> F64 costs arm A seed 1 about 3 points and seed 0 about 0.4; going 1x -> 30x
  filler costs seed 2 about 13 points. Neither interacts explosively with the other.

## What this does **not** mean

* **It is not a confirmation.** These are development checkpoints scored on a probe grid built
  for this question. Nothing here licenses a claim of "generalises to long stories"; that
  needs a registered confirmation panel on untouched data.
* **It is not a test of longer reasoning.** Every attribute and LINK question is **one call**.
  The only multi-step axis is the two-call two-hop executor, and only `grow-blind` was scored
  on it.
* **It does not say the model would survive a *different* kind of growth.** We grew the number
  of filler rows and the number of competing people. We did not change the fact grammar, add
  new relations, repeat facts, make facts contradict each other, or exceed 16 people — that
  last one is a hard ceiling of the vocabulary, not a choice.
* **Three seeds is three seeds.** Arm A's spread (1.000 / 0.945 / 0.844 at the hardest cell)
  is wide. The honest summary is "2 of 3 seeds hold; 1 of 3 erodes", not a population rate.
* **The 30x cell is not a limit we found — it is the limit we chose.** Nothing in the data
  suggests 30x is special; accuracy was still falling slowly at the edge of the grid for seed
  2 and still flat for seed 0.

---

## Predictions scored

The preregistration carries these verbatim. Brier score is (p - outcome)^2; lower is better.

| # | prediction | p | outcome | result | Brier |
| --- | --- | ---: | ---: | --- | ---: |
| **P31** | factorial-A reaches >=95% attribute accuracy at F24 / 10x filler in >=2/3 seeds | 0.60 | 1 | **HIT** — 1.000 / 0.992 / 0.910 -> 2 of 3 | 0.160 |
| **P32** | >=90% at F64 / 10x filler in >=2/3 seeds | 0.45 | 1 | **HIT** — 0.994 / 0.961 / 0.918 -> 3 of 3 | 0.303 |
| **P33** | some cell up to 30x filler drops below 80% for >=2/3 factorial-A seeds | 0.50 | 0 | **MISS** — worst cell is 1.000 / 0.945 / 0.842; 0 of 3 seeds below 0.80 | 0.250 |

**Total Brier 0.713, mean 0.238.** The two "does it hold" predictions were both under-confident
(the truth was better than predicted); the "it will break somewhere" prediction was wrong.

**The stated failure shape was right.** The preregistration said: *"gradual decline as filler
grows (attention spread over more tokens), not a cliff."* The decline is indeed gradual and
there is no cliff — but the stated *mechanism* is wrong. Attention did **not** spread out; the
correct-row mass barely moved (0.543 -> 0.526) while its advantage over uniform grew 13-fold.
Whatever erodes seed 2, it is not attention dilution.

---

## Deviations, judgment calls and things left unverified

1. **Correction to the brief's premise.** The brief stated that arm-A and arm-D checkpoints
   "were never trained on LINK". That is not right: the startup factorial inherits
   `grow-blind`'s record recipe verbatim, which emits a one-call `link` record
   `[4, a, 11, 5]` for every two-hop question in the generator's visit. Arm A's own final
   training probe reports `probe_link_acc = 1.0`. One-call LINK is therefore **in
   distribution** for arm A, and its LINK row in Table 1 is a real result rather than an
   out-of-distribution curiosity. Two-hop *execution* was still scored for `grow-blind` only,
   as preregistered.
2. **Subset-closed friend maps.** Each world's friend map is redrawn until every question
   person's friend is also inside the 6-person subset. Without this, a two-hop question could
   not be answered from the F24 rows and the grid would stop being paired. The consequence:
   for the 6 question people the friend is uniform over 5 candidates instead of 15. Values,
   row order, filler, and the other ten people are untouched. Declared in the preregistration.
3. **Uniform interleaving.** The generator shuffles its 4 distractor rows among the facts and
   appends its gap rows at the end; here every filler row is placed uniformly at random among
   the fact rows. This is what makes the cells nested. Fact-row order is the generator's.
4. **Exclusion audit ran and is clean.** 2,048 distinct question signatures were checked
   against the 6,656-entry registered forbidden set: **0 overlaps**. Because the signature
   ignores filler and row order, the filler axis cannot change a signature, so the two fact
   conditions are the only two distinct signature sets — noted rather than hidden.
5. **Unverified.** (a) Why seed 2 erodes and seed 0 does not — we measured that it is not
   attention dilution, but we did not identify what it *is*. (b) Whether the relation-10
   weakness is caused by the record recipe's practice imbalance; that is a plausible reading
   of the recipe, not a tested claim. (c) Nothing beyond 30x filler / 64 facts / 16 people was
   tested. (d) These checkpoints were selected by earlier development work, so their numbers
   here are not free of selection.

## Resource note

One evaluation process at a time alongside the six registered training workers. Three
invocations: 0.8 s to build the grid, 57 s for the six factorial checkpoints, 129 s for the
six grow-blind checkpoints (two-hop execution included). Peak RSS 601 MB.
`torch.set_num_threads(1)`, `OMP_NUM_THREADS=1`. Every checkpoint was opened read-only, its
sha256 verified against `manifest.json`, and its parameter fingerprint re-checked after every
cell to prove it was not modified.
