# The research phase

Research has two jobs: ground the benchmark in how the field measures this problem, and fill the hypothesis queue with ideas that have a real mechanism behind them. The loop is only as good as the queue. Random edits to a training script plateau fast; ideas from papers keep it moving.

## Search plan

Cover each angle. If you can run subagents, give each one angle, and ask for sources with links plus a two-line takeaway each.

1. **Names.** What the field calls this problem, and its neighbors. The user's words ("overwriting old skills") rarely match the literature's ("catastrophic forgetting", "stability-plasticity", "continual/lifelong learning", "knowledge retention").
2. **Surveys**, preferably from the last two to three years, to get the map and the standard taxonomy of approaches.
3. **Benchmarks and metrics.** How papers measure it, and which settings are considered meaningful.
4. **Strong simple baselines.** What papers struggle to beat. There is almost always one, and it goes in as a reference point and an early card.
5. **Recent methods with code.** Check the repo's activity and open issues to see whether it works.
6. **Negative results.** "Why X fails", reproducibility studies, and reviewer criticisms on OpenReview. They save the loop from re-running known dead ends.
7. **Fit to constraints.** Methods that work at the user's scale: a single GPU, a small model, a short budget. Many headline methods only pay off at scale.

Good sources:
- arXiv, for recent work
- Semantic Scholar, to follow citations forward from a key paper
- OpenReview, for reviews that expose weaknesses
- GitHub, for implementations and their issue threads
- authors' blog posts, for the intuition that got cut from the paper

## Reading for implementation

For each idea you might implement, extract:
- the exact mechanism
- the key hyperparameters and their reported sensitivity
- the extra compute or memory it costs
- the setting it was tested in

If you only saw the abstract, say so in notes.md and treat the details as unknown. Never invent a citation or a number.

## Hypothesis cards

Use the template in `.research/hypotheses.md`. Each card needs:
- the idea and its mechanism: why it should help **here**, not just in the paper
- the source
- the expected effect, with direction and rough size
- the cost, in implementation effort and runtime
- the main way it could fail

Rank the cards by (expected gain × fit to constraints) / cost, while keeping the queue diverse. Mix cheap one-line tweaks, well-supported mid-size methods and a few bold redesigns. A queue made only of tweaks plateaus; one made only of redesigns burns the night on crashes.

A literature trial implements the top untried card. Mark each card as kept, discarded, near-miss or crash, with its trial id(s). Never delete a card, because failures are findings.

## Research refreshes

The harness requires a refresh every 10 trials, and whenever 8 trials pass without a keep. A refresh is short and targeted, not a restart:

1. Read `.research/summary.md`.
2. For each recent keep, ask what mechanism explains it, and search for ideas that push the same mechanism further.
3. For repeated failures, search for why that family fails ("X hurts when Y"), and retire or rewrite the cards it affects.
4. Add at least two new cards, re-rank the queue, and record what changed with `refreshed --note`.

## Optional: evolutionary search for small components

If one piece of the system is a small, self-contained function with a cheap, reliable score, a program-evolution tool can explore it more efficiently than one-at-a-time edits. Examples are an update rule, a loss term or a routing heuristic, and example tools are ShinkaEvolve and OpenEvolve. Only reach for this when the user has agreed and such a component exists. It is a sub-experiment, and its result still enters the main loop as a single trial.
