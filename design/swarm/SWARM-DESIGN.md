# A swarm inside one model: desks and a board (design, 2026-10-17)

**Status: DRAFT until the coordinator code-reviews it.** Written by the Opus layer of an Ultracode SOLVE
session (environment `beautiful-model`), branch `claude/swarm-thinkers`. $0 work only: design, code,
tests, run cards. Nothing here books a GPU.
Labels: **shown** = read in code or result files; **suggested** = reasoned; **untested** = never run.

Files: this design, `IMPLEMENTATION-SPEC.md` (the build contract), `RUNCARD-S0.md`, `RUNCARD-S1.md`,
`FUNDING-BID.md`, the prototype `premonition/swarm.py`, tests `tests/test_premonition_swarm.py`.

---

## 0. Before the design: three mismatches between the brief and the repo

I checked the brief's premises against the code. Three do not hold as written. I did not stop over
them; I resolved each one as below, and the run cards cannot be sealed until the coordinator accepts
or changes these resolutions.

1. **Which model is "the main model".** The brief names `premonition/model.py` and describes it exactly:
   a Think stack, registers, ASK into a card store, a gated binder, HALT (**shown**,
   `premonition/model.py:200-257, 446-496`). But the resource figures (about 3M parameters, launch-bound,
   GPU idle about a third of the time, the $50/week Vast cap) come from the **B3G2 3M** line in
   `custom_io/` (**shown**: `results/8a-g/speedup/launch/PREREG-launch-defer.md` on
   `claude/launch-bound-solve`, model "B3G2 3M", prediction P6 "R ≈ 0.63", money section "$50/week Vast
   cap"). Premonition D is **2,013,140** parameters (v1 tokenizer) or 2,102,228 (v2)
   (`tests/test_premonition_model.py:139`, `premonition/config.py:13-14`). B3G2 has no card store or
   binder (`design/architecture-2026-10-09/FINISHED-MODEL-2026-10-09.md` on `claude/learner-new-g2`).
   **Resolution:** I built the swarm in `premonition/model.py`, as the brief directs, and the design is
   written for D. The resource argument still holds for D. Its weights are about 8 MB in fp32, and the
   desks share one weight set, so extra desks cost activations, not weights (**suggested**). What has
   **not** been shown is that D's training is launch-bound. Nobody has measured it, so the funding bid
   (§C0) measures it first.
2. **"Far held-out join" does not exist** under that name on any branch I searched (main,
   `claude/learner-new-g2`, `claude/launch-bound-solve`, `claude/premonition-launch-recovery-96c708`).
   **Resolution (PROVISIONAL):** the primary ruler is the `far_deep` cell (`premonition/slices.py:150-151`).
   That cell is a knowable question with an evidence line outside A's window and derivation depth ≥ 2: a
   fact far back has to be joined with at least one more. Design/06 already makes it the kill cell
   (`design/06-premonition-mini-spec.md:187`). It is scored on the held-out **validation** villages, whose
   names are split from train (`slices.py:5`), and the test split is kept for a later verdict.
3. **"DEV slip under the house family rule"** is not defined for Premonition anywhere. The only "family
   rule" in the repo is `≥ 2 of 3` (`scripts/fable_dispatcher_probes26.py:977-983`,
   `artifacts/fable-dispatcher-probes26-20260921/AUDIT-26.md:306-307`). **Resolution (PROVISIONAL):** DEV
   is the validation split's `near` and `overall` cells. A slip is a drop of more than
   `policy.MIN_EFFECT` = 3 points against the single thinker. The guard fails when a slip shows on
   ≥ 2 of 3 seeds.

## 1. What already exists (read in code, not from summaries)

* **D's thinker** (**shown**, `model.py:221-245, 410-496`). Each question gets a 76-row tensor: 40
  question rows (the reader's last 40 states up to `[answer]`), 16 entity slots (the entity embeddings,
  valid only for mentioned names), 16 card rows (FIFO, filled by ASK) and 4 registers. One 2-layer
  bidirectional block, with shared weights and a loop-step embedding, runs up to 8 times. All questions
  in a batch are already stacked as one tensor `[ΣQ, 76, 128]` (design/06 §3). Register 0 drives a query
  into the card store, an ASK logit, and HALT. A fetched card becomes a row (value + age + type), and
  the **binder** gates its value into the slot of every entity the card's line mentions
  (`model.py:469-481`). That is where a name gets attached to a fact. The decoder cross-attends to all
  76 rows (`model.py:278-291`), and `L_ans` deep-supervises every loop (`model.py:571-588`).
* **The register loop** (`custom_io/models/register_loop.py`, branch `claude/custom-reader-talker-4x309r`
  at 611ed3f4f). 16 slots (9 answer registers + 7 scratch) run weight-shared rounds of slot
  self-attention plus cross-attention to the reader. There is no halting, and a tied talker reads the
  registers. Its verdict was **NO-GO**, and the reason matters here: the round-1 register interchange
  matched the counterfactual on **1.8%** of rows against a 40% bar. The rounds re-derived everything
  from the prompt and carried nothing forward (custom_io `REPORT.md` row 3, `PASS-MARKS.md`).
  **Lesson applied below:** a channel between thinkers will be ignored whenever the receiver can
  recompute the same thing from the question. The board has to carry something the receiver cannot
  get alone, and a lesion has to check that it is actually used.
* **Prior verdict on "swarms"** (`design/research/2026-09-18-novel-mechanisms.md:202`): "It costs N
  times the compute for roughly what self-consistency already gives. Samples from one small model
  share the same mistakes." That critique is of *sampling* N copies and voting. This design differs on
  the two points it attacks. The desks are forced to fetch *different* evidence (§4). The merge is a
  learned join over bound facts, not a vote (§5). The critique still stands for S0 unless S0's
  diversity report shows the desks really differ.

## 2. The design in one picture

```
              ┌────────────── one question, one round (all desks of all questions = ONE tensor) ─────────────┐
 card store ──┤ desk 0  [question 40 | slots 16 | cards 16 | registers 4 (+desk 0 id)] + board rows (read)  ├─► ASK₀ ─┐
 (per visit)  │ desk 1  [question 40 | slots 16 | cards 16 | registers 4 (+desk 1 id)] + board rows (read)  ├─► ASK₁ ─┤ each desk's
              │ desk 2  …                                                                                   ├─► ASK₂ ─┤ cards go to
              │ desk 3  …                                                                                   ├─► ASK₃ ─┘ ITS desk only
              └───────────────┬──────────────────────────────────────────────────────────────────────────────┘
                              │ register 1 of every desk = its NOTE;  every newly fetched card = a POSTED card
                              ▼
                 BOARD (S1 only): M note rows (one per author) + 16 posted-card rows (FIFO)   ◄── the ONE switch
                              │
                              ▼
 COMBINER = the existing decoder, cross-attending to every desk's rows (bound-slot merge mask) + one board copy
                              │
                              ▼  L_ans deep supervision every round, here and only here
                           answer
```

* **Desk** = one thinker: a private, complete copy of today's 76 rows, with its own registers, card rows,
  entity slots and fetch history. **Every desk shares D's weights.** The only new parameters are a desk
  embedding (M × d, added to that desk's registers) and two board row types (2 × d). At M = 4,
  d = 128 that is 768 parameters, +0.04%.
* **Concurrency** is literal. Each round, `model._step` runs once over a `[Q·M, rows, d]` tensor, the
  same launch count as one thinker's loop, M× the rows. The prototype tests this
  (`ConcurrencyTest`).
* **Board** = the single communication channel. Turning it off (`swarm_board=False`) gives S0. While a
  round runs, board rows are read-only extra rows on every desk. Between rounds, each desk's register 1
  is posted as a note, and every card any desk fetched is posted once.

## 3. The six questions, resolved

### Q1. Communication: a shared board, not all-to-all register reading

**Choice: a board.** It holds one note per desk, written from a dedicated post register (register 1),
plus the posted cards. Every desk reads it between rounds.

* **Bandwidth.** All-to-all register reading would add (M − 1) × 4 rows to every desk: 12 at M = 4, 28 at
  M = 8, growing with M². The board adds M + 16 rows. It carries one deliberate message per desk per
  round, and the posted cards are lossless: a posted card is the exact card value, not a summary.
  All-to-all gives more raw bandwidth but no exact facts, so a fact found by desk 1 would reach desk 2
  only as whatever desk 1's registers happened to hold.
* **Legibility.** On the board, every note has one known author (the author embedding is added) and every
  card has a known line. "Who said what" and "which fact was shared" can be read off directly. With
  all-to-all, every register could be a message, so nothing is a message for sure.
* **Ablation.** One switch, and three eval-time lesions on a trained S1: `board`, `notes`, `cards`.
  All-to-all has no clean "off" that keeps the desks' own computation intact.
* **The register-loop lesson.** Desks keep their *fetched cards private*. The only way desk 2 learns
  what desk 1 fetched is the board. So the channel carries information the receiver cannot recompute
  from the question, which is exactly what the register loop lacked. The S1 card requires the `board`
  lesion to cost at least 3 points (§S1 bars), so a board that goes unused fails.
* Cost of the choice (**suggested**): the board is a broadcast, so every desk reads the same thing.
  That pushes toward consensus and is a collapse pressure. §4 is the counterweight.

### Q2. Who talks to the card store: every desk asks

**Choice: every desk has its own ASK** (register 0, the existing heads). The division of labour comes
from *what* each desk asks for (§Q3), not from forbidding some desks to ask.

Reasons:
1. A parallel ASK is the main way concurrency can replace loop depth. Today's single thinker issues
   **one** query per loop and takes its top 4 (`model.py:493`). A join needs cards about two different
   entities, and one query vector tends to retrieve around one of them. M desks issue M different
   queries in the same round. (This is the mechanism being bet on: **suggested**, **untested**.)
2. An ASK is cheap: a dot product against at most L keys per desk.
3. Dedicated non-asking "workers" would make the S0 ablation degenerate. With no board, a worker desk
   sees nothing but the question and adds no breadth by construction. S0 would then test a strawman.
4. Ben's picture ("some could work on researching") is still possible. A desk can learn to keep its ASK
   logit low and work only from the board. The guard measures each desk's ASK rate and reports such
   desks as "silent desks". If a later rung wants roles enforced, `asks` can be masked per desk in a
   few lines. That would be a separate change with its own card.
5. Redundant fetches: in S1 every posted card is visible to all desks, so re-fetching it gains nothing.
   Training-time assignment (Q3) also splits the needed cards. The fetch-overlap number in the
   diversity report measures what is left.

### Q3. Roles: assigned and trainable, with one forced-diversity mechanism

**Choice: assigned identities, a trainable desk embedding per desk index**, extending D's row-type
embeddings. On their own, these break the symmetry, but only weakly: with shared weights, the same
inputs and a 0.02-scale embedding, M desks start as near-copies. An unforced committee collapses. Two
things force diversity:

1. **Balanced assignment of the needed evidence (training only).** Each round, the cards the swarm still
   needs (gold minus the union of everything fetched) are split among the desks. The split is a
   capacity-capped greedy matching on each desk's own ASK scores, at most ⌈|need| / M⌉ per desk. Each
   desk's set cross-entropy is computed only over its assigned cards, and its ASK target is "I have
   something assigned". In teacher mode, the teacher fetches each desk's assigned cards for that desk.
   This is *multiple-choice learning* (Guzman-Rivera et al. 2012; stochastic MCL, Lee et al. 2016):
   the desk already best placed for a card is trained to take it, and the capacity cap stops one desk
   from taking everything, even when the desks are identical (`AssignmentTest`). The assignment reads
   gold labels and runs only in training. At inference no information passes between desks in S0. It
   is **identical in S0 and S1**, so S1 − S0 still isolates the board.
2. **Private cards.** A desk holds only the cards it fetched, in its own rows and its own slot bindings.
   Desks that were assigned different evidence therefore have different contents, not just different
   ids.

What stays emergent is how desks specialise: by entity, by hop, by age of evidence, or not at all. I do
not force a particular split. The diversity report (§4) says what happened.

### Q4. Rounds and budgets

* **Rounds.** The swarm runs a **fixed** `swarm_rounds = 4` in teacher, own and eval modes (2 in gold).
  The single thinker keeps its schedule: ⌈|G|/4⌉ + 3 in teacher mode, up to 8 with HALT in own mode and
  at eval. Communication needs rounds: a note posted after round r is read in round r + 1, so 4 rounds
  give three exchanges. Concurrency replaces depth only partly: 4 rounds × 4 desks instead of up to 8
  loops × 1.
* **Matched wall-clock (primary for the screen).** Both arms train for the same seconds on the same box
  (`MiniTrainer.train(max_seconds=…)`, with the FLOP budget set out of reach). Both are evaluated with
  the same eval code. The swarm's FLOPs are reported, not matched: it spends about M × 4 / (mean loops)
  times the think FLOPs. Whether that is "close to free" depends on D being launch-bound, which is
  measured in §C0 before any screen run.
* **Matched total parameters (reported separately).** The swarm adds M·d trained parameters (desk
  embeddings), plus 2d with the board: S0 +512 and S1 +768 at M = 4, d = 128 (v1 tokenizer: S1 is
  2,013,908 against 2,013,140). They are matched within 0.04% with no
  adjustment, and both arms stay inside design/06's parameter band (tested).
* **FLOP-matched** is *information only* and gets no run of its own. Every report carries
  FLOPs/question and seconds/step, so nobody mistakes a wall-clock win for a free lunch.

### Q5. The speaker and where supervision attaches

**The speaker is the combiner**: today's decoder, unchanged in weights, cross-attending to the union of
every desk's rows plus one copy of the board. It is not a designated speaker desk, because in S0 a
single desk would know only its own cards and could not join across desks. It is not the board alone,
because S0 has no board. The combiner is identical in S0 and S1.

**Supervision.** `L_ans` is applied at **every round through the combiner, and nowhere else**. There is
no per-desk answer loss. A per-desk answer loss would train every desk to solve the whole question
alone, which is the gradient that makes copies. Each desk instead gets the ASK loss for its assigned
cards. HALT is trained on the mean of the desks' HALT logits against "the combiner is right this round".
The "have every gold card" scale for `L_ans` uses the union of the desks' fetches. This keeps the
signal honest. The only path from evidence to answer runs through desks fetching and the combiner
joining, and the swarm cannot score without at least one desk fetching what the question needs.

### Q6. Halting

The screen uses fixed rounds; the swarm does not halt early at eval. HALT logits are still trained, so a
later rung can switch on a **swarm-level halt**. That halt would be the mean, or a learned pool, of the
desks' HALT logits against the combiner's correctness, stopping all desks of a question together. Two
refinements are left for later: (a) a desk-level "idle" (a desk whose ASK and note no longer change
stops being run, which saves compute without ending the question), and (b) letting the board carry a
"done" vote. Neither is built.

## 4. Collapse risk, head-on

**The risk.** M desks with shared weights, near-identical inputs and one broadcast board converge to the
same registers, the same queries and the same fetches. The swarm then becomes one thinker with M×
compute and a combiner that averages copies.

**What pushes against it.** (1) The balanced assignment trains desks to want different cards, with a
capacity cap that splits even identical desks. (2) Private cards and bindings: different evidence
gives different contents. (3) Desk embeddings break the symmetry. (4) There is no per-desk answer loss,
so no gradient asks each desk to be a whole solver.

**How we would know.** `premonition.swarm.diversity()` runs on every eval:
* `fetch_overlap`: mean pairwise Jaccard of the desks' fetched sets per question (NULL excluded);
* `register_cos`: mean pairwise cosine of the desks' final register blocks;
* `ask_rate` and `fetch_count` per desk, and `silent_desks` (ASK rate < 5%).
* **The pre-registered collapse line:** `register_cos > 0.95` **and** `fetch_overlap > 0.8` →
  `collapsed = True`, and the readout must print "COLLAPSED: the desks are copies" in its verdict line.
  A collapsed swarm cannot PASS a screen, whatever its accuracy. Any gain would then come from extra
  rows or compute, not from a swarm. Test: identical desks report collapsed; disjoint fetches report
  overlap 0.

## 5. Merge-point binding risk, head-on

**The risk.** In S0, a join's two facts can sit on different desks: desk 1 has "A's mother is B", desk 2
has "B lives by the mill". Whatever combines the swarm's work must still pair each name with its fact
across desks, or the answer mixes up whose fact is whose.

**Why the design keeps binding intact at the merge.**
1. **Binding happens on the desk, at fetch time, keyed by name.** The existing binder writes a card's
   value into the slot of every entity the card's line mentions (`model.py:469-481`). A slot row starts
   as that entity's embedding, the same vector on every desk. So a bound slot is a (name, fact) pair
   already, and the combiner never has to re-bind. It reads pairs that are already labelled by name.
2. **Bound-slot merge mask.** If the combiner showed every desk's copy of slot e, the unbound copies
   would dilute the bound one: three "B, nothing known" rows against one "B, lives by the mill". The
   mask shows a desk's slot e **only if that desk bound e** (it fetched a real card whose line mentions
   e). If no desk bound e, only desk 0's copy is shown, so the name stays visible. Test:
   `MergeMaskTest`.
3. **Training teaches the cross-desk join from the start.** In the gold phase, a question's gold cards
   are dealt round-robin across desks. So from step 0 the combiner learns to answer from facts spread
   over desks, not only from facts on one desk.
4. **What is not solved (untested).** Two desks may bind *conflicting* values to the same name (one
   desk has an older card about B, another a newer one). Both copies are shown. The age embedding
   distinguishes them, but whether the combiner prefers the newer one is untested. The S1 readout
   reports the `changed` slice for this reason. In S1, posted cards also reach every desk, which helps.

## 6. What the prototype does (flag `thinkers`, default 1 = OFF)

`MiniConfig(thinkers=M, swarm_board=False|True, swarm_rounds=4, board_cards=16)`. When `thinkers == 1`,
the model is **bit-identical** to `73b8e0224`. This is tested against a frozen copy of the old
`model.py`: same initial weights, losses, gradients and greedy answers, in all three modes and all
three variants (`FlagOffBitIdentityTest`). The swarm path reuses `_start/_step/_insert/_teacher_cards/
_greedy` unchanged, so `address_reader` and `direct_reader` compose with it (not exercised at size).
See `IMPLEMENTATION-SPEC.md` §11 for the full test list.

## 7. Known limits (declared before any run)

* D has no recorded full-size result on the village data in this repo, so the screen trains its own
  single-thinker baseline (D1).
* "Launch-bound" is shown for B3G2, not for D. If D at M = 4 is not near-free (§C0), matched wall-clock
  gives the swarm fewer steps, and the screen measures that honestly instead of assuming it away.
* A strong confound is not in the ladder: a single thinker with M × 4 registers and M × top_k fetches per
  loop ("wide single thinker"). If S0 passes, it is the natural next control.
* S0 as the kill screen tests "breadth without talk". A negative S0 does not prove that a communicating
  swarm cannot work. The brief's ladder still kills there, and the S0 card says what a kill does and
  does not show.

## 8. For Ben, in plain words

Today the model has one "thinker". It reads the question, goes to its filing cabinet (the card store),
pulls out up to 4 cards, thinks, pulls more, and answers. The new version gives the model **four desks
that think at the same time**, all using the same brain, so it costs almost no extra memory. Each desk
pulls its *own* cards from the cabinet. During training, the cards a question needs are shared out
between the desks, so they learn to look for different things instead of all grabbing the same card.
Between rounds, each desk can pin one note to a **shared board**, and every card anyone pulled is
pinned there too. At the end, the answer-writer reads all four desks and the board and writes one
answer.

We test it in two steps. First, **S0**: four desks with **no board**, so they can't talk. Do four desks
beat one thinker when both get the same training time? If not, we stop there and it cost a few dollars.
If yes, **S1**: the same with the board on. Does talking help beyond just having four desks? We also
check that the board is really used (S1 must get worse when we cover the board up), and that the four
desks didn't turn into four copies of the same desk (the "diversity report").
