# Idea check: #5, #14 and #16 from ranked-ideas-v2 (reasoning thread, 2026-09-24)

Ben (01:11) said "sure" to the coordinator's proposal to check these three against their papers and our code. Labels: **shown** (checked in our code or results), **abstract** (read only in search listings or abstracts), **memory** (from my training knowledge, not re-read), **untested**.

**Full text was not reachable today.** This session's egress proxy returns 403 for arxiv.org, openreview.net, nature.com, aclanthology.org, semanticscholar.org and proceedings.neurips.cc (checked 01:15 UTC). So no claim below is full-text verified. The campaign2/ source files the ideas cite are not in the repo or in /mnt/project-files/.

## #14 Loop-ladder sleep

- **Evidence.** Lee et al. 2025, "Self-Improving Transformers Overcome Easy-to-Hard and Length Generalization Challenges" (arXiv 2502.01612, ICLR 2025 workshop):
  - a model labels slightly harder problems itself, filters those labels and retrains;
  - this pushes arithmetic length generalization far past training lengths (the ~10× figure: abstract/memory).
  Fan et al. 2024, "Looped Transformers for Length Generalization" (arXiv 2409.15647, NeurIPS 2024):
  - looping with an adaptive number of steps extrapolates on n-RASP-L tasks (abstract).
  Two parts of the idea are its own untested additions, not in these papers as far as I know (memory):
  - the "keep labels that agree across loop counts" filter;
  - the counterfactual checks.
- **Novelty.** Low to moderate. It combines two published lines. The filter is new but untested.
- **Fit.** It aims at our clearest gap: three-step questions were 0 in every 294 run (shown). Our setting also makes it stronger: a self-made answer can be verified exactly against the notebook, because the fact-check already checks the cited chain (shown, claude_rsn294_core.supported). So we don't need the consistency filters. The catch is that it needs a reasoner that already solves the rung below reliably. The 294 loop did not (D2), and the plain arm dropped to 6–11/30 on blind two-step questions (D1).
- **Verdict.** Good idea, wrong time. Do it after D1 and D2 are fixed.

## #16 Compositional sleep school (MLC)

- **Evidence.** Lake & Baroni 2023, Nature, "Human-like systematic generalization through a meta-learning neural network" (abstract/memory):
  - a standard transformer is trained on many small episodes, each with freshly invented words and rules;
  - it matches human systematic generalization on few-shot instruction tasks.
  This is well established and has been reproduced (the MLC code is public). The "modules only generalize when their training combinations are connected" theory is not identified in the listing, so it is untested here.
- **Novelty.** Low as a method. Using it as the nightly practice plan for a notebook reasoner is our own combination.
- **Fit.** High, and it matches 294's main failure:
  - 294 already uses half of MLC: names, values and relations are re-shuffled to fresh symbols every episode (shown, encode());
  - it lacks the other half: variety in how the episodes are built. It practised one generator's notebook style, scored 100/100 on that style and 6–30/30 on blind notebooks (D1).
  MLC's lesson is to vary the structure of the practice (which rows exist, how many per person, how chains and distractors combine), not only the symbols.
- **Verdict. Best fit. Proposed as 296.**

## #5 Calibrated "not in memory" answers

- **Evidence.**
  - Models lose accuracy when "none of these" is correct: shown in several 2024–25 papers at abstract level (e.g. WiCkeD, arXiv 2503.01550). The "30–50%" size is not verified.
  - Missing-mass estimates (Good–Turing) and search-stopping theory are textbook (memory).
- **Novelty.** Moderate. The three-way split ("I don't know" / "No, I'd know" / "No, I remember otherwise") is a clean framing.
- **Fit.** Lower than it looks. Our reasoner already abstains perfectly on missing facts: 30/30 on every run and 0 invented after the fact-check (shown). Yes/no already separates "no, the notebook says otherwise" from "I don't know". The new part, "No, I'd know if it were true", needs the notebook to mark a relation as complete (e.g. "those are all my kids"). That is a notebook and reader feature, not reasoner training. Calibration matters most for the reader's confidence (the listener line), not for exact notebook lookups.
- **Verdict.** Worth a small notebook feature later ("complete list" flag). Not a reasoner experiment.
