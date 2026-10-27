# Angle 5: continual learning and sleep at scale (research only)

Written 2026-09-29 (`date -u` = 01:56 UTC) by an angle agent (Claude). Nothing was run, trained or edited. Labels: shown (measured in the cited source or a repo file) / suggested (my reasoning) / untested. "Abstract only" = I read the arXiv abstract page, not the paper. Every source result is the authors' own unless I say a second group reproduced it (I found no independent reproduction for most). Small card experiments and the village model are left out of every claim.
Not repeated (already in standing 03/06, MAP, TESTS): WiSE-FT, soups, task arithmetic, LoRA forgets less, RL's Razor, DER, OGD, EWC, LwF, DGR, pseudo-rehearsal, MIR/GSS, MoE forgetting, sleep length.

## 1. Plain-language summary for Ben
- Bigger models forget less only in one situation: when they were pretrained well first and the new job is close to what they know. Trained from scratch, or in a "rich learning" regime, bigger can forget more. So "the real model will be bigger, so sleep gets easier" is half supported. lf-8 in our repo fits the good half.
- For puzzle kinds, Premonition can make unlimited fresh old-kind puzzles with code. That is a big lever, and the older night tests already used it (see 3). The current maze-day ruler does not: it sleeps on a fixed 16 or 128 store. That mismatch may be the main reason small-store sleep collapses. It is a fair test only for puzzles. Real user data has no generator, so the honest real-world version is the model writing its own replay (SSR-style), which our solver cannot do yet.
- "Improves with use" means many days. The literature says nets slowly lose the ability to learn new things after many tasks (loss of plasticity). Nothing in this repo measures that across 5+ day/night cycles. One test below does.

## 2. Strongest sources (5), each with mapping

### S1. Effect of scale on catastrophic forgetting (Ramasesh, Lewkowycz, Dyer, ICLR 2022)
Link: https://research.google/pubs/effect-of-scale-on-catastrophic-forgetting-in-neural-networks/ (abstract only).
- Shown (authors): large pretrained ResNets and Transformers forget far less than the same nets trained from scratch, and the effect grows with model size and with pretraining data size. Suggested by authors: class representations become more orthogonal in big pretrained nets.
- Counter-evidence: https://arxiv.org/abs/2407.00176 (abstract only): ResNets on SplitCIFAR-10, online class-incremental, larger models did not forget less and adapted worse. Wide-net result (Mirzadeh et al., https://arxiv.org/abs/2110.11526, from memory not re-read) says width helps but depth and same-size comparisons are mixed.
- https://arxiv.org/abs/2506.16884 (abstract only, theory plus experiments): width helps in the "lazy" regime (features barely move) and can hurt in the "rich" regime (features move a lot); there is a best amount of feature learning that carries across sizes. Suggested for us: if the big model adapts by huge feature change (full fine-tune on mazes at lr 1e-3) it may not forget less; small updates are the safe direction. This fits the H6 finding that a long night at full step size hurt.
- Mapping: Premonition's premise leans on this. Shown in repo: lf-8 (3.9x weights) kept old grids 181/177 vs 120/61 of 200 after mazes (artifacts/claude-lf8-20260927/RESULTS.md), but size and depth are mixed; "deep or just big" is queued and is the right same-size check. Not shown: that forgetting keeps shrinking as the model grows further. Our net is trained from scratch on generated puzzles, not pretrained on a broad corpus, so the Ramasesh mechanism (pretraining) may not carry over. Untested.

### S2. Continual Learning via Sparse Memory Finetuning (Lin et al., Meta, Oct 2025)
Links: https://arxiv.org/abs/2510.15103 (abstract only); follow-ups https://arxiv.org/abs/2604.05248 and https://arxiv.org/abs/2605.03229 (abstract only; different authors, small Qwen-2.5-0.5B retrofit).
- Shown (authors): with memory-layer models, updating only memory slots that the new data uses much more than pretraining data does: NaturalQuestions F1 dropped 11% (vs 89% full fine-tune, 71% LoRA) at the same new-fact gain. The follow-ups (other groups, but on a 0.5B model and on facts, no scale sweep) report the same direction: small gain on the target, forgetting near baseline, while LoRA and full fine-tune drift. That is partial independent support, at small scale only.
- Caveat: task is learning facts, not skills or procedures. Not shown for reasoning skills. The gain is modest on the new task in the follow-up (+2.5 points).
- Mapping: it is the "decide where NOT to write" idea. Ben approved sparse MoE and many layers (another thread); sparse memory slots are a different thing (huge key-value table, a few rows written per update). For skills, the loop's 2 shared blocks have no slots to select. Nearest cheap analogue is a gradient mask on the day update (Test 2). Suggested / untested.

### S3. Self-Distillation Enables Continual Learning (SDFT; Shenfeld, Damani, Hubotter, Agrawal; arXiv Jan 2026, ICML 2026 poster)
Link: https://arxiv.org/abs/2601.19897 (abstract only).
- Shown (authors): the model, given a demonstration in its prompt, acts as its own teacher; training on its own on-policy outputs beats plain fine-tuning at keeping old skills while learning the new one, and in a sequence of skills it accumulated several with no regression. Cost about 2.5x FLOPs, 4x wall clock. The authors report it needs in-context learning ability: at 3B it lost to plain fine-tuning on one task. So it seems to improve with scale. Author-only; I did not find a reproduction.
- Mapping: our reasoner has no in-context "demonstration" channel, and the repo already showed self-distillation on the stored items adds little (+4.5 / +9.75 of 200, bar 20; standing 03). Verdict: not a cheap fit for the small net; the scale-dependence is exactly why it is a later-model idea. Untested for us. I do not propose a test.

### S4. Self-Synthesized Rehearsal (SSR; Huang et al., ACL 2024) and its relatives
Link: https://arxiv.org/abs/2403.01244 (abstract only). Survey context: https://arxiv.org/abs/2603.12658 (abstract/summary only).
- Shown (authors, peer reviewed at ACL, not independently reproduced as far as I found): the LLM writes its own replay inputs by in-context generation, the newest model relabels them, and a diverse subset is kept. Matches or beats replay of the real stored data with less of it, and keeps general ability. Model sizes and buffer sizes not read.
- Mapping (question b below): this is the real-data version of generator replay. For our puzzles the generator is code; for user data it must be the model itself. Suggested: SSR-style needs the model to write questions, which the reasoner cannot do, so it belongs to the talker or a new head.

### S5. Loss of plasticity (Dohare et al., Nature 632, 2024) and a scale follow-up
Links: https://www.nature.com/articles/s41586-024-07711-7 (search-result summary; I did not open the full text); https://arxiv.org/abs/2606.24752 (abstract page read).
- Shown (authors of Nature paper; the effect has since been reproduced by several groups): plain backprop nets trained over a long sequence of tasks slowly learn each new task worse, eventually no better than a shallow net. L2 regularisation plus weight perturbation eased it; continual backprop (re-initialise a small fraction of the least-used units each step) kept plasticity.
- Shown (arXiv 2606.24752, one group, GPT-style 5M to 314M non-embedding params, multilingual sequence): larger models delay measurable plasticity loss, onset grows only sublinearly with size, and it appears even in stationary training. So scale helps a little but does not remove it. This is the direct answer to "does the bigger model fix many-days learning": no, not alone.
- Mapping: Ben's premise is exactly a long task sequence. Our practised loop already survived one sequence (sums, grids, mazes) but nothing here checks nights 2 to 5 for learning speed. See question (c).

Lower-ranked, read only via search summaries: continual model merging (https://arxiv.org/abs/2501.09522 and the ODE-view paper https://arxiv.org/abs/2605.19409): performance falls as more experiences are merged; TIES slightly beats DARE and plain averaging; these are dense-net vision/LLM results, no scale law found. Suggested: merging is a WiSE-FT cousin (already covered) and shows the many-days problem, since each merge dilutes the last. PackNet / Piggyback: from memory, freeze-and-mask methods that cap capacity; not searched; they conflict with "improve with use" because capacity runs out.

## 3. Key questions

### (a) Which methods have evidence that forgetting shrinks as models grow?
- Shown, scale helps: Ramasesh (pretrained nets), Mirzadeh (width), our own lf-8 (one PASS, 2 seeds, size and depth mixed). SDFT works better with in-context ability, i.e. larger models (authors say so; suggested for us).
- Shown, scale alone is not enough: online CL ResNets (2407.00176), rich-regime theory (2506.16884), LLM plasticity loss only delayed (2606.24752).
- No source gives a scale law for EWC, SI or MAS. Suggested reasons they fail at scale (from the general literature, memory, not re-read): a per-weight penalty needs importance estimates per task that go stale, cost grows with parameters, and nets learn with big feature changes that a quadratic pull cannot hold. In our repo the untested weaker relative is the weights blend (queued).
- Replay and merging: replay works at scale but needs data; merging degrades with number of merges.
- Best fit for "bigger model later": keep updates small and local (sparse write, low step size, blend), plus replay that scales for free (generator replay for skills). Suggested.

### (b) Is generator-based replay already done in this repo? Answer: partly, and not in the current ruler.
Shown in code:
- Ruler / distill / KS harness: `scripts/claude_fewex_data.py` `replay_old()` builds a FIXED store: `E.make_sum` x128 and `latin_legend` x128 from one seed, then the tests take the first 16 or 128 (`[:16]`). Sleep draws from this fixed list. The old-kind panels are also fixed (`old_panels`). Kinds have generators, but the harness freezes them into a small list.
- KS PASSMARKS (Lead 2, blend) also use "the first 16 stored", so they stay store-limited by design.
- Older night tests (`scripts/claude_slp358n3_nights.py`, line ~278): rehearsal draws from `R.Source(100 + seed, ...)`, "the reasoner's own practice stream, fresh seed", i.e. fresh generator puzzles, unlimited. That thread's night kept old skills with 0 lost of 300 in 24 cells (artifacts/claude-dir-h6-sleeplen-20260928/DESIGN.md, S arm) on a different reasoner (358u, d512) and a different day set. So generator replay evidently works there. Not the maze-day ruler, so not comparable to the 128 / 16 numbers.
- Proposed but not run: T1 in sleep-design TESTS.md (fresh questions, labels = the pre-maze net's own answers). It removes the store but keeps the teacher labels. My Test 1 below isolates the other half: fresh inputs with TRUE code-made labels.
Two cases kept separate:
1. Puzzles (sums, grids, mazes, graph, rank): a generator plus a solver exist, so replay is unlimited and exact. A big lever, but a disclosed advantage: it assumes the kind's generator is known.
2. Real user data: no generator. Options are a real store (small, collapses at 16 per kind per the repo), the model writing its own inputs (SSR, needs a question-writing ability), or a retrieval store. Not testable on this reasoner today. Suggested: state clearly in any claim that puzzle results with generator replay are an upper bound for case 2.

### (c) Loss of plasticity over many nights: is anything measuring it?
- Shown in repo: multi-night runs exist but only 3 nights (H6 design, `slp358n3`: night-to-night SD about 11; L lost a little; S lost 0) and no measure of learning speed on a NEW kind after each night. The old repo notes list Dohare et al. as "add a plasticity arm only if ..." (design/research/2026-09-19-overnight-research-note.md:323-324), never run. I found no result file with "plasticity" in artifacts RESULTS.
- The ruler itself measures adaptation from one pre-maze net, so plasticity loss would be invisible to it.
- Untested: whether nights 4 to 5 slow the loop. A 2-layer looped net with shared weights and AdamW wd 0.1 could plausibly resist or suffer; I have no evidence either way.

## 4. Tests (one change each; harness gates reused)
Common: practised loop, seeds 0 and 1 (2+ seeds), 3 sleep draws, margin max(6, 2 x SE) with SE = SD of the comparator draws / sqrt(3), plain-net row, bars above noise (F_eq bar +8.0, F_few +10.5, sleep bar 20 of 200). Dev panels only. Marks below are fixed now, before any run; the sealing helper should confirm noise from the H6 S-vs-S re-run as MAP/TESTS item 1 asks. Costs are my estimates (untested), scaled from lf-8 (6.6 min per 8-layer run on a 5090, $0.13) and 3.8 min for the loop2 arm.

### Test MD1 (preferred): five day/night cycles, fresh generator replay vs fixed 16 store
Ben's premise made a test. Not H6 (night length is fixed at the harness's 512 updates each night), not T1 (labels are TRUE, not teacher).
- Schedule: 5 days, a new kind each day. Days 1 to 3 = maze, graph, rank once H1 lands (if H1 gives only two, use maze 9x9, graph, rank, then 11x11 maze, then the second-best available new kind; state the substitute before running). Old kinds sums and grids plus all earlier days' kinds count as "old". Each day = adaptation on k = 64 examples of the new kind (2,048 updates as the ruler), then one night.
- One change between arms: what the night rehearses. Arm A (control, existing recipe) = fixed 16 stored per kind, kept from when each kind was learned. Arm B = fresh code-made puzzles of every earlier kind each update, true labels, same batch size and same number of updates (512), same mix of the day's puzzles. Plain-net row: the same 5-cycle schedule on the plain 8-block net with arm A (and B if time).
- Measure after each night d: old-kind scores (x of 200 each; 300 for maze) and a plasticity probe, no training carryover: from a COPY of the net, adapt on 64 new mazes (same 2,048 updates, fixed probe seeds) and score F_few at k = 64. Log the probe after nights 0 to 5 (night 0 = practised net). That is the improve-with-use curve.
- Pass marks (fixed now): B passes if, after night 5, every earlier kind is at least A + 20 of 200 (or 30 of 300 for mazes), mean of 3 sleep draws with the margin above, on both seeds; AND the plasticity probe after night 5 is not more than 8 F_eq points below the probe at night 0 (the noise-sized bar, 8.0 is the repo bar) on both seeds; AND the plain-net row cannot pass it (plain probe at night 5 at least 10 below its night-0 value, or plain kept-old below A + 20). If the plain net passes too, say "not architecture-specific".
- Proved wrong: (1) B is within 5 of A on all earlier kinds on both seeds, i.e. store size is not the limit; then generator replay is not the lever and the collapse is about the update, not the data (points to Test 2 and to H6 arm B); or (2) the probe falls by more than 15 in both arms, i.e. plasticity loss is real regardless of replay (then continual backprop / shrink-and-perturb becomes the next single change).
- Cost: 2 seeds x 5 cycles x (2,048 + 512 updates) x 3 draws x 2 arms plus plain row and probes. Estimated about 2 to 4 GPU hours on one 5070 Ti; a Mac CPU would take days, so use the GPU. Cheap pilot: 3 cycles first (maze, graph, rank), about 1 to 2 hours.
- Reads: shown or not-shown for the two-case split in section 3(b): B success = puzzles only, upper bound for real data.

### Test SM (cheap, CPU-feasible): write only where the old kinds do not read
One change: after the maze day (k = 64 and 16,384, the KS cells), replace full fine-tuning by masked fine-tuning where only the top 10% of weights by ratio (maze-gradient size / old-kind-gradient size, computed once from the 16 store on the pre-maze net) are updated. No sleep in either arm. This is the "don't write over what the old kinds use" idea of sparse memory finetuning, transplanted onto dense weights. It is a cousin of MAS/SI and of Lead 0 (localisation), so run it after KS Lead 0 returns; if Lead 0 says ENTANGLED, expect this to fail.
- Pass: on both seeds, old kinds after the day are at least 60 of 200 each without any sleep (full fine-tuning gives 0), AND 9x9 F_eq within 8 of full fine-tuning (bar 8.0), AND F_few not lower than full fine-tuning minus 10.5, AND the plain net (same mask rule) does not pass the old-kind gate. Then sleeping on top is a second test, not this one.
- Proved wrong: old kinds under 20 of 200 on both seeds, or F_eq drops more than 8 with old kinds under 60.
- Cost: one adapt run per cell, 2 seeds x 2 rungs, about 5 to 10 min each on a 5070 Ti; feasible on Mac CPU in hours (the ruler's sleep harness already ran on CPU, $0).

### Not proposed (with reasons)
- SDFT: needs in-context demos, no channel in our reasoner; self-distillation in sleep already tried (+4.5 / +9.75, bar 20).
- Continual backprop, shrink-and-perturb, L2-init: hold until MD1's probe says plasticity actually falls. Adding them now would be a fix without a symptom. If MD1's plasticity probe falls by more than 15, the next single test is L2-init (pull toward the current night's start) since it is one line and has a Nature-paper record (Dohare et al.).
- EWC, SI, MAS successors: already have EWC in the covered list; I found no scale evidence for the successors.
- Merging (TIES, DARE): no scale evidence, degrades per merge; overlaps the blend.

## 5. Suggested reading order of results
1. Test MD1 pilot (3 cycles): tells whether store size or step size is the limit, and gives the first plasticity curve.
2. KS Lead 0 result, then Test SM if not ENTANGLED.
3. Deep-or-just-big (queued) for the size question; add MD1's plasticity probe to it if cheap (suggested), because a bigger net should show a later onset if 2606.24752 holds here.

## 6. Cautions
- Almost every scale result above is on pretrained nets. Ours is trained from scratch on generated puzzles, so Ramasesh-type gains are not guaranteed. lf-8's gain is shown but only 2 seeds.
- Sparse memory finetuning evidence is on facts (NaturalQuestions) and small retrofits; skill retention is not shown.
- I read abstracts or search summaries for all 2024 to 2026 papers; none of my mapped claims come from full-text reading.
- Generator replay must be labelled a disclosed advantage in any write-up; it does not transfer to user data.
