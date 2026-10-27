# 21 — From the number toy to a teachable assistant: an independent review

**Fable reviewer, at Ben's request, 20 September 2026 — not an Astra document.**
Design and opinion only. Nothing was trained, no existing file was changed, nothing was committed.
Evidence labels: **shown** = I read it in a saved result or in source today; **suggested** = my
interpretation; **untested** = nobody has run it. "W" = this worktree.

What I read: `reviews/2026-09-17-contract/candidate-facts-first-bridge.md`, the head of
`reviews/astra-deep-dive-2026-09-19/report.md`, `design/v3/17`, W `design/v3/19-development-readout…`,
W experiment-19 `RESULTS.md` + `report.txt`, dispatcher v3/v4 preregistrations, the operator-swap report,
the story-size stress report, the predictions ledger, `design/06-step1-pilot-results.md`, the operator
source (`scripts/premonition_token_memory.py`) and the memory notes. I did **not** re-run any audit
and did not read the 150 kB evidence digest in full.

---

## 0. The blunt version first

1. **The present toy cannot, by construction, do what Ben asked for.** It has 16 entity tokens, so a
   world holds at most 64 facts (shown: stress report, "all 64 facts a world can hold"). Nothing
   persists between episodes. There is no "I don't know" answer anywhere in the operator's training
   (shown: no such token or target in the operator scripts). "Learn facts as it grows" is outside
   the toy, not just unproven inside it.
2. **The project has spent most of a day on a problem that is not on Ben's critical path.** The
   count-to-3 ceiling is about following four or more *identical* LINK tokens and stopping by
   itself with the bookkeeping removed. It is a legitimate science question, and the literature
   says it is a generically hard one (length generalisation; §7). But the learned controllers
   are **at or near 64/64 on the ≤3-step cells, held-out endings included**: `reg+ctx` 64/64 on all
   of them in 3/3 seeds (shown: ledger P46), v3 likewise, experiment-19 awake D ≥ 61/64; the weakest
   case I found is the `reg` arm, seed 1, at 57–61/64 on three held-out short cells (shown: its
   score log). People almost never type questions with four
   chained possessives. Reasoning *breadth* at ≤3 steps (unknowns, corrections, reverse questions,
   comparisons, taught definitions) matters far more for an assistant than depth 8, and none of it
   has been tried.
3. **Even the "working" learned controller is not dependable.** The hinted v3 dispatcher passed all
   25 cells in 3/3 seeds; the v4 `v3-repro` arm (same recipe, same seeds, same operator, computation
   checked identical on one batch) passed 12, 14 and 21 of 25 — 0/3 (shown: ledger P41). I could not
   find the cause in the artifacts. Until someone explains it, the honest summary of learned
   control beyond three calls is "3 of 6 runs", i.e. a lottery, with or without the hints.
4. **Almost everything is development evidence on reused panels.** The only sealed confirmation I
   found is for the plain-transformer baseline's fit cells. Nothing about the operator + controller
   system has been confirmed on fresh panels.
5. **What is genuinely solid** (development evidence, but broad): the 79,316-parameter lookup
   operator, trained "clean and small", reads stories 28× larger than it trained on (shown: 94.5–100 %
   in 2/3 seeds up to 678 rows; one seed slid to 84 %), passed 48/48 seeds in the GPU reliability
   population, and with a fixed loop around it follows chains to 8–10 steps and tracks edited facts.
   That reader is the asset. The roadmap below is built on it.
6. **The interface was parked for a good reason but is now parked for a bad one.** It was parked
   to debug the core. It is still parked because the core's *hardest optional* problem is unsolved.
   The English shell does not depend on that problem (§3).

---

## 1. Ben's goal as five testable capabilities

| # | Capability | Demo (Ben types → it answers) | Evidence today |
|---|---|---|---|
| C1 | **Told once, remembered later**, including people it has never heard of, across a restart | Monday: "Mira's friend is Oren." *(quit, reopen Tuesday)* "Who is Mira's friend?" → "Oren." | **None.** One-hop lookup *within one episode, 16 fixed names* is strong (48/48 seeds, development). Persistence: none. New names: none (the only earlier test, the village baseline, got 0 % and that was a tokenizer bug — so still no evidence). Re-worded questions: negative so far (village pilot 23 % on held-out wording). |
| C2 | **Combines facts it was taught separately** | Taught on different days: "Mira's friend is Oren." / "Oren's shoes are red." → "What colour are Mira's friend's shoes?" → "red." | **Partial.** Chains to 8–10 steps with a *fixed* loop; learned control dependable to 3 steps only; all facts in context in the same episode; program structure read off the question by supplied code. Development panels only. |
| C3 | **Corrections win, and flow through chains** | "Actually Oren's shoes are blue now." → same question → "blue", never "red" again. | **Indirect.** Edited-pair cells pass (answers causally follow the facts), but those compare two *separate* stories. No test has ever put an old and a new version of a fact in one memory. The operator's memory is an unordered set of rows (shown: positions are within-row only), so it *cannot* know which row is newer without a change. |
| C4 | **Says "I don't know"; stays accurate as facts pile up** (tens → thousands) | "What colour are Pell's shoes?" (never taught) → "I don't know." After 2,000 more facts, Monday's fact is still right. | **None** for unknown. Scale: good to 64 facts / 678 rows; nothing beyond, and impossible beyond until names are open-ended. |
| C5 | **Gets better at reasoning with practice, without losing old skills** | After a practice session it handles a question shape it used to fail, and still gets the old ones. | **Weak and mixed.** Experiment 19: uniform practice moved the ceiling from 3 to 4–6 unevenly; 0/72 at 6–8; one seed lost short held-out questions (64→27). |

C1, C3-as-stated and C4 — the three that make it *teachable* — have no evidence. C2 has the most.

---

## 2. Shortest honest path: six milestones

**Memory mechanism I recommend first: an external notebook that the learned reader reads.**
Concretely: (a) an append-only **diary** on disk (time, raw sentence, canonical fact row, source) that
is never edited; (b) a **current view** = the latest row per (subject, relation), which is what the
operator sees as its "story"; (c) a **symbol table** mapping each name to an internal code. This is
the diary + cards half of the store Ben already agreed to on 18 September; the "slots consolidated in
sleep" half is deliberately left for later.

Why this first, and not fast weights or fine-tuning:
- **It is what the toy already is.** The operator already answers from rows supplied in context.
  Making those rows come from a file instead of a generator is engineering, not research. Persistent
  memory therefore enters at **M0**, at zero training cost.
- **Corrections propagate for free.** Two-hop answers are computed at question time by chained
  lookups, so nothing stale is cached. This is the MeLLo design (facts kept outside, model frozen,
  question decomposed), which beat weight-editing methods by a wide margin on exactly this test;
  weight editors that recall an edited fact 96 % of the time answered 7 % of the multi-hop
  consequences (MQuAKE; already cited in the 17 September contract).
- **Zero forgetting of facts by construction**; whatever degrades with growth is the *reader*, which
  is measurable (below).
- **Weights-first has a bad record, here and outside.** Here: the A3 teacher-delay stage failed its
  safeguards; the token-memory successor failed transfer. Outside: models fine-tuned on A→B and B→C
  separately fail A→C without thinking aloud (two-hop curse); a July 2026 study of sequential fact
  writes into Qwen3 weights reports bare-statement facts falling to about 1 % after twenty later
  writes while the same fact supplied in context recovers to 77–80 % (O'Neill, arXiv 2607.11020 — I
  read only a machine summary of the abstract; treat the numbers as unverified). Sparse
  memory-layer fine-tuning reduces forgetting a lot (−11 % vs −89 % for full fine-tuning) but in
  billion-parameter pretrained models, not at 80k parameters. Titans/ATLAS-style test-time memories
  compress one long context; they are not evidence about correctable cross-session facts. A
  delta-rule matrix at width 48 holds on the order of 50 associations before interference.
- **Honesty for Ben:** a notebook is *not* "learning in its own weights". It is the hippocampus half
  of his design. Consolidating facts into weights is a later, separate experiment, to be run with the
  notebook as ground truth and rollback (his own "sleep as a transaction" rule) and to be justified
  by something the notebook cannot do (speed, or abstraction across facts).

**Corrections:** a corrected fact is appended to the diary and replaces the old row in the current
view (exact match on subject code + relation). This is *supplied* code and must be declared as such.
A learned alternative needs an age tag on rows, because the reader has no row-order signal; I would
not spend effort on that yet.
**Unknown:** an explicit UNKNOWN answer trained into the operator (M2); the loop returns UNKNOWN if
any step returns UNKNOWN.
**Measuring forgetting as facts accumulate:** two separate things. *Fact side:* a fixed probe set
(the first 32 facts taught) is re-asked after every doubling of the notebook (64, 128, … 4,096);
report the full accuracy-after-each-block matrix, the **signed** change per probe (never clipped),
old-answer rate after corrections, confabulation rate on untaught questions, and whether the probe's
person has newer same-person rows. *Skill side:* whenever reasoner weights change (M5), the retained
and held-out short cells from experiment 19b, with the same "no cell loses ≥7/64" guard. A
**wipe-notebook test** (empty store → every fact question must become UNKNOWN) shows the knowledge
lives in the notebook and not in the weights.

| # | The single change | Pass mark (each seed separately) | Main risk | Compute | Would show / would not show |
|---|---|---|---|---|---|
| **M0 Notebook demo v0** | Story rows come from a persistent diary/current-view instead of the episode generator. Rule-based template reader and printer ("Mira's friend is Oren." ↔ fact row; 16 names, one friend link, three attributes). **No training**: frozen grow-blind operators seeds 0–2 + the fixed loop. | 64 scripted teaching sessions per operator seed, facts taught one at a time. One-hop and two-hop ≥ 95 % at every notebook size 1, 2, 4 … 64; after a correction new answer ≥ 95 %, old answer ≤ 2 %, untouched facts unchanged; answers bit-identical after kill-and-reload. Descriptive only: how confident it is on untaught questions. | Tiny notebooks (1–15 rows) were never trained on. I expect them to be easier, but it is unmeasured. | Mac, minutes. $0. | **Shows:** a learned reader can sit behind a persistent, correctable notebook; Ben gets a first thing to type into. **Does not show:** any learning of language, unknowns, new names, more than 64 facts, or learned control. Asking an untaught question will produce a confident wrong answer — record that as the baseline failure. |
| **M1 New names** | Entity embeddings stop being 16 trained vectors and become fixed random codes, re-drawn per world from a large pool with a reserved never-trained part (§5). | §5. | Highest-risk step: the start-up lottery may get worse when names cannot be tuned. | Mac, one 6-process wave < 30 min. $0. | **Shows:** the reader binds to symbols it has never seen — the precondition for growing past 16 people. **Does not show:** spelling (that lives in the symbol table), English, scale. |
| **M2 "I don't know"** | Add an UNKNOWN answer; ~20 % of training queries are unanswerable (no such row; or person absent). | Answerable cells keep their current marks (487/461 of 512); unanswerable → UNKNOWN ≥ 487/512; two-hop with a missing second fact → UNKNOWN ≥ 461/512. | "Always say UNKNOWN" is an easy early rut and could interact with the start-up problem; introduce unanswerables on a fixed schedule after onset, fixed before looking. | Mac, one wave. $0. | **Shows:** in-distribution honesty. **Does not show:** calibrated doubt about noisy or contradictory teaching. |
| **M3 Growth** | Evaluation only: notebooks of 64 → 4,096 facts (needs M1). Arm (a) the reader sees the whole current view; arm (b) the store hands it only rows that mention the queried name plus a fixed number of random other rows (supplied index). | Probe-set accuracy ≥ 95 % at 1,024 facts and signed change from the 32-fact level ≥ −3 points, arm (a). 4,096 and arm (b): report only. | Attention thins out over tens of thousands of tokens; random codes at width 48 begin to collide (worst-case cosine ≈ 0.6 at 4,096 names). If (a) breaks, (b) rescues the demo, but then be honest that the reader is only choosing among a handful of rows. | PC GPU, < 30 min. $0. | **Shows:** where the learned reader actually breaks, and the interference curve. **Does not show:** anything about weights-based memory. |
| **M4 Tiny-English ears** | Replace the rule-based reader with a small learned one: syllable-level sentence (≈120-token vocabulary) → sentence type (fact / correction / question) + name spans (copied, not classified) + relation sequence. Trained on synthetic templates, 8 train / 2 validation / 2 never-seen per relation, as in the 17 September contract. The printer stays rule-based. | Exact canonical parse ≥ 98 % on fresh sentences from training templates, ≥ 90 % on never-seen templates; end-to-end teach-then-ask within 3 points of the rule-based system. | Never-seen wordings — exactly the wall the village pilot hit (23 %). Mitigation: many more templates, with Qwen used offline as a paraphrase *generator* only. | PC GPU, minutes per seed. $0. | **Shows:** it understands a small closed English. **Does not show:** open English. A learned *decoder* is not worth building: the answer is one symbol whose spelling is in the symbol table; a neural net for that is theatre. |
| **M5 Learned control, improved by practice** | Swap the fixed loop for the learned dispatcher once 19b-style marks are met, re-validated against the M1/M2 operator; practice sessions may change dispatcher weights under the retention guard. | Astra's 19b marks, then fresh confirmation panels. | This is the long pole and may stay open for weeks. It must not block M0–M4. | Mac. $0; keep the ~$27 for one confirmation population at the end. | **Shows:** the step-choosing is learned and survives practice. **Does not show:** length extrapolation, unless lengths stay unpractised. |

A natural M1b, if M1 passes: make *relation* tokens random codes too. If the reader has truly learned
"match the two key symbols, copy the third", a brand-new kind of fact would work the first time it is
taught. That would be the most striking cheap result available. Untested; do not bundle it with M1.

---

## 3. Does English have to wait for count-to-3? No.

The contract between the two halves already exists: a fact row, and the canonical question
`[question, subject, op…, answer]`. Anything that only *produces* or *consumes* that form cannot
confound the reasoning experiments, because it never touches the operator's or dispatcher's training.

**Safe to do in parallel now:** the diary / current-view / symbol-table store and the wipe and restart
tests; the template grammar with rule-based reader and printer; the frozen teach-then-ask panels; M0
(evaluation only on frozen checkpoints); the dictionary and Qwen baselines of §4; training the M4
reader on the PC while the Mac runs 19b. Only contention is machine time: 19b wants the Mac's six
slots.
**Must wait:** any end-to-end training *through* the reader into the operator (it would re-expose the
start-up lottery with more moving parts — do it only after the M1+M2 operator recipe is frozen);
plugging the learned dispatcher into the demo (after 19b, and after re-validation on the M1 operator,
since the dispatcher embeds entity tokens itself); any sentence containing "reasons well" (after fresh
confirmation panels).

**Yes, the fixed loop gives Ben a usable demo sooner — M0 needs no training at all.** What it would
prove: a tiny learned reader answers from a persistent notebook, its chained answers are *caused* by
the notebook (change a link and the answer changes), to about ten steps. What it would not prove:
that the model works out the steps, their number, or when to stop; the loop reads those off the
question. It is a calculator with a learned memory reader. There is a middle option worth stating:
the **learned** dispatcher capped at three steps is already at or near 64/64 on ≤3-step cells
(`reg+ctx` and v3: 64/64 in 3/3 seeds, development panels), so after re-validation the demo can honestly say "it chose the steps itself, for questions up
to three steps". That covers nearly everything a person would type.

---

## 4. How is this different from a small pretrained model with retrieval?

**Honestly: as a product, it is not, and it will be worse.** Qwen with the diary pasted into its
prompt would very likely score ≥ 95 % on every C1–C4 demo at tens to hundreds of facts today, with
free-form English, and iterative retrieval would carry it to thousands. A 30-line Python dictionary
plus the rule-based reader scores 100 % on the closed grammar. M0–M4 reproduce, in a learned tiny
system, what those two already do.

**It is different only if X:**
- **X1 — the procedure is learned and transfers at tiny size.** The policy that turns a question into
  memory reads is learned from outcomes and works on question shapes it never practised, at under a
  million parameters, where a same-size ordinary transformer given the same notebook in context does
  not. Evidence today is suggestive only (one qualifying transformer seed; development panels). The
  cheap test is the comparison already under way, but with at least three qualifying baseline seeds
  under the clean-start recipe and fresh confirmation panels.
- **X2 — teaching changes how it reasons, not only what it knows.** One taught definition ("a patron
  is the employer of one's landlord"; contract C) or a practice session changes later behaviour on
  held-out compositions, persists, and costs no old skill. Cheap test: a definition row in the
  notebook that the learned dispatcher must read and execute, held-out pairs, ~15 min per seed. With
  the fixed loop this would be a supplied macro and prove nothing, so it belongs after M5.

Two smaller true differences: every answer comes with an exact trace of lookups, and a model that
knows nothing has no prior beliefs to fight a correction. Both are real; neither is a reason to
build it rather than use Qwen.

**The yardstick (do this once, < 30 min, free):** one frozen teach-then-ask panel, three systems —
dictionary + rules, Qwen-with-diary on the PC, Premonition. Report accuracy per capability, old-answer
rate, made-up-answer rate on untaught questions, parameters and compute per answer. Expect to lose to
both on accuracy. The point is to know by how much and to keep every later claim ("per parameter",
"learned", "traceable") honest.

**Attach to Qwen, or train the tiny interface?** The strongest case for Qwen: language is the one
part that is solved elsewhere; the village pilot shows from-scratch language is a swamp; paraphrase
and new names would work on day one; Ben could use it daily, which produces real teaching data and
motivation; effort, not compute, is the scarce resource. **My recommendation is still the tiny
from-scratch interface for the system that claims are made about, with the rule-based reader
first.** Reasons: Ben's stated aim is his *own* learning model with language second; he already
rejected "a transformer with a layer on it"; a closed template grammar is a tractable supervised
problem, unlike the village's open wording; and once Qwen is inside, every success will be credited
to Qwen, correctly. Use Qwen for exactly three things: the yardstick above, offline paraphrase
generation for M4, and — if Ben wants to chat loosely — an optional, clearly labelled translator from
free English into tiny English that is never part of a scored run. (It also occupies ~15 GB of the
16 GB card, so it cannot run while the PC trains.)

---

## 5. The one experiment I would register next: "new names" (M1)

M0 can be built alongside it; it is evaluation-only. The experiment that most changes the plan if it
fails is this one, so it goes first.

- **Hypothesis.** The operator's lookup skill does not depend on a tuned embedding per person. If the
  16 entity tokens are represented by fixed random codes that are never trained and are re-drawn for
  every world, the same recipe reaches the same marks on worlds built only from codes it has never
  seen.
- **Arms (one change).** *Control:* the frozen clean-start grow-blind recipe exactly as is, new
  seeds. *Treatment:* identical, except entity embeddings (input, story and the tied output rows) are
  per-world draws from a pool of 4,096 random codes; 1,024 codes are reserved and never appear in
  training. One learned scale for the codes and one shared entity output bias replace the 16 trained
  rows and biases (fewer trainable parameters, not more). Pool, split and code scale rule hashed
  before training.
- **Data.** Same generator, six-person training worlds, per-seed world stream shared by both arms.
  Fresh ten-cell panel in a new RNG namespace with the usual exclusions (c1–c6, three-step stress,
  three 12-person cells; 512 units each), scored with the fixed loop. The treatment is scored twice
  on byte-identical panels: training-pool codes and reserved codes. Descriptive extra, treatment only:
  64-person worlds (256 facts) — the first look past the old ceiling.
- **Marks (per seed, no averaging).** Reserved-code panels: ≥ 487/512 on c1, c2, p12-1, p12-2;
  ≥ 461/512 on the other six. Reserved minus training-pool ≥ −13/512 on every cell, paired. The
  control must meet its own marks in ≥ 2/3 seeds or the run is void ("recipe did not reproduce").
  All-seed pass = 3/3; 2/3 is reported as partial with no claim.
- **Seeds and budget.** Seeds 2100–2102 × 2 arms = 6 runs = one Mac wave under 30 minutes, final
  checkpoint only, no replacements. $0.
- **My predictions (to be hashed):** treatment passes 3/3: 0.35; passes in ≥ 1 seed: 0.65; any seed
  passes on training-pool codes but fails on reserved codes: 0.05; control reproduces ≥ 2/3: 0.85.
- **Most likely failure.** The treatment never starts learning in two or three seeds — the known
  lottery, made worse because a person can no longer be recognised by a tuned vector, only by
  exact content match through the query/key maps. Second most likely: a scale mismatch — trained
  value embeddings grow during training, fixed codes do not, so value answers drown entity answers
  and LINK lookups fail while attribute lookups pass. That signature (attributes fine, LINK at
  chance) should be named in advance so it is read as a fixable scale bug and not as "binding is
  impossible". If it fails cleanly for other reasons, the fallback is the 17 September plan: names as
  two syllable tokens with a copy-style output, which is a bigger change to the operator.
- **What a pass would and would not mean.** It would mean the notebook can hold people the model has
  never met, removing the 64-fact ceiling. It would not show English, persistence, unknowns or scale.

---

## 6. Where I am unsure, and what would settle it

- **Why did `v3-repro` fail 0/3 when v3 passed 3/3?** One targeted check: run both scripts for 50
  updates from the same seed and find the first update at which parameters differ. If they never
  differ, the 6,000-update difference is thread-level non-determinism and the recipe sits on a
  knife-edge; either way it should be written down before 19b is interpreted.
- **Does the reader survive 1,000+ facts unaided?** Unknown; M3 settles it in one evaluation wave.
- **Is from-scratch tiny English really tractable on never-seen templates?** The village result says
  be worried; the closed grammar says be hopeful. M4's held-out-template mark settles it, and the
  rule-based reader means the demo never depends on the answer.
- **Is X1 real?** Needs ≥ 3 qualifying baseline seeds and fresh panels. Until then, do not say the
  decomposed system generalises better than a transformer.
- **Process cost.** For 80k-parameter runs that take fifteen minutes, multi-document rulings cost more
  than the experiments. Keep fixed marks, hashed predictions and every-seed reporting; for
  evaluation-only probes like M0, a one-page registration is enough.

## 7. Sources I relied on

Checked by web search today (titles, venues and headline numbers as returned by search summaries; I
did not read the full papers today):
[MQuAKE / MeLLo, arXiv 2305.14795](https://arxiv.org/abs/2305.14795) ·
[Two-hop curse / Lessons from studying two-hop latent reasoning, arXiv 2411.16353](https://arxiv.org/abs/2411.16353) ·
[Continual learning via sparse memory finetuning, arXiv 2510.15103](https://arxiv.org/abs/2510.15103) ·
[HippoRAG 2, "From RAG to Memory", arXiv 2502.14802](https://arxiv.org/abs/2502.14802) ·
[Titans, arXiv 2501.00663](https://arxiv.org/pdf/2501.00663) and [ATLAS, arXiv 2505.23735](https://arxiv.org/abs/2505.23735) ·
[KBLaM, arXiv 2410.10450](https://arxiv.org/abs/2410.10450) (facts as key–value tokens plugged into a pretrained model; the closest published cousin of "notebook + reader", at 8B scale) ·
[PropMEND, arXiv 2506.08920](https://arxiv.org/abs/2506.08920) (weight edits that propagate need a meta-trained hypernetwork and still only roughly double a low multi-hop score) ·
[O'Neill, "Can a language model learn facts continually in its weights?", arXiv 2607.11020](https://arxiv.org/abs/2607.11020) — **abstract seen only through a machine summary; numbers unverified** ·
[Looped transformers for length generalization, arXiv 2409.15647](https://arxiv.org/abs/2409.15647).

From memory, **not re-checked today**: Santoro et al. 2016 (per-episode label shuffling forces binding
into memory, the idea behind M1); Schlag et al. 2021 (delta-rule capacity ≈ key width); Wang et al.
2024, "Grokked transformers are implicit reasoners" (in-weights composition fails out of distribution);
that the looped-transformer result relies on the step count being supplied in training and on an
oracle or confidence rule to stop at test time — if true, it supports treating "learn to stop beyond
trained length" as an open research problem and not as a gate for the demo.

---

## 8. Five lines for Ben

1. Your model's best part today is a tiny "reader" that looks things up in a list of facts; everything
   else you want — remembering across days, new people, "I don't know", English — has not been tried yet.
2. The fastest honest route is to give that reader a **notebook on disk**: you teach it a sentence, the
   notebook keeps it forever, a correction replaces the old line, and answers are worked out fresh each
   time so corrections flow through. You could be typing to a first version this week, with no new training.
3. The problem everyone has been stuck on (it stops after three steps) matters for science but not for
   this demo; real questions rarely need more than three steps, and the English part does not have to wait for it.
4. The next real experiment is "new names": can the reader handle people it has never seen? If yes, the
   64-fact limit disappears; if no, the reader needs a redesign — better to find out now.
5. Be clear-eyed: a big pretrained model with the same notebook would beat this at being an assistant.
   Yours is worth building only if it shows that a tiny model can *learn how to reason* and be changed by
   teaching — so measure against that big model once, and never claim more than the numbers show.
