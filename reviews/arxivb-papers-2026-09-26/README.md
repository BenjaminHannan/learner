# arXivBangers paper review, 2026-09-26

Ben's three links (thread cmsg_01FuvegZXjMmeUzStiEFVnEW2VXUgGbqcLbVMyQweRdsaS, 02:15 UTC): an X post, arXiv 2609.28654, and the arxivb.org published list (30 papers). Reviewed 02:15-02:40 UTC against Premonition's seven open problems. This was an opinion-only review: nothing was registered and nothing was spent.

Files here:
- `review.html` is the source of the published page https://claude.ai/artifact/DkY9CCYjCU4zM2ieQipAfo. It holds the 12 full reads, the 18 one-line verdicts, and test ideas A to E with pass marks.
- `abstracts.md` holds the arXiv title, authors and abstract of all 30 papers on the list.
- `handoff-looped-flows.md` is the brief sent to Sleep research at 02:36 UTC.

The full paper texts (12 PDFs converted with pdftotext, plus the BDM README and appendix) are kept out of the repo. They are in the project files at `research-2026-09-26/papers/`.

## What the links are
- **arxivb.org** is "arXivBangers", a site independent of arXiv. A Gemini 3.7 Flash "editorial judge" scores only the title, authors and abstract, and the site posts 2 arXiv papers a day to X. "Certified banger" is not a review. All 30 IDs resolve on arxiv.org.
- **The X post** (@p0rc314in, Block Delta Memory) is a code repo with no paper. It tests models of 15-17M weights over 3 seeds. Recall roughly matches attention on 1-hop, span and overwrite tasks. On 2/4/8-hop pointer chasing every model fails, including attention: full-suite exact scores are BDM 58.7 and attention 59.0. It has no bearing on Premonition.
- **2609.28654** (object permanence in video world models) has no bearing. Its exam comes from the same generators as its training data, and it has no before/after test of the base model.

## Verdicts
- **Changes a plan:** Looped Flows (2609.11801) uses the same shape as the 358a loop (2 layers, width 512, 5-7M weights). It adds a noisy answer and a time input, lowers the noise over the steps, and puts a loss on every step. On Sudoku-Extreme, trained on 1,000 puzzles, it scores 97.9 ± 0.4 over 3 seeds, against TRM's 87.4 and FPRM 7M's 94.2. Caveats: its baselines are copied from other papers, it never tests bigger puzzles than it practised on, and with 8 steps it scores 74.5. My pick for the next reasoner change after 358a, ahead of a 3x scale-up. It was handed to Sleep research to register after 11:00 UTC.
- **Explains:** 2609.19107, Appendix B.4. Tied loops get worse when run for more passes than they trained with. Training with a random pass count only flattens that. 358a trains on 1-16 rounds, grades the last 1-6, and tests up to 48.
- **Confirms dl-3:** Never Give Up (2609.13443), Fig. 14, shows items stop improving and decay once they are no longer practised. None of the 30 papers measures forgetting of general answers.
- **Reader problems 1-4:** nothing useful. PSD (2609.23449) trains on LoCoMo's own chats, which breaks our rule, and it is scored on about 123 test questions.
- **Benchmarks note:** the published same-size Sudoku-Extreme score is now 94.2 (FPRM 7M) or 97.9 (looped flows, ~5M). bm-394's registered S1 mark (beat TRM-Att 7M's 74.7) is unchanged; only the report-only comparison line moves.

## Test ideas (queued; not registered)
- **A. Looped-flow objective on the 358a loop** (Sleep research; handed over). Pass: the flow loop beats plain by at least +20/300 on at least 2 of the 3 bigger tests, on both seeds, and loses at most 10/300 on any practised size. Proved wrong: +5/300 or less on all three bigger tests, on both seeds.
- **B. Learned stop vs a random stop matched to mean rounds**, plus per-round counts of cells fixed and broken (Sleep research, evaluation only). Pass: the learned stop is at least 5 points above the random stop on the bigger tests. Proved wrong: 1 point or less.
- **C. Adaptive blurt budget**, taken from Never Give Up (Fix sleep). Pass: the hard third gains at least 6/100, total right is at least the control's, both seeds, and at most 3/200 general answers lost. Proved wrong: a hard-third gain under 2/100 even with at least 1.5x as many hard wins.
- **D. Code-made one-step hints for puzzles with zero hits**, taken from PSP 2609.29051 (Creative). Pass: the hard third gains at least 8/100 over control, and the wrong-hint placebo gains at most 3/100. Proved wrong: +3/100 or less, or the placebo matches it.
- **E. Swap retrieved chat lines for another conversation's lines** (Benchmarks, evaluation only). Run only if the notebook first beats no notes by at least 3 F1. Pass: the swapped lines recover at most a quarter of the notebook's gain. Proved wrong: they recover half or more.
