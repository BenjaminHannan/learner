# Scratchpad or bookmark? — Sol architecture discussion, 2026-09-27

Ben requested a fleet of Sol subagents to answer whether latent cards should help continue the current attempt or restore an earlier one. Three GPT-6 Sol agents examined scratchpad, bookmark, and skeptic/hybrid perspectives independently. This is a design discussion, not registration, a training result, or approval for the joined build. The baseline diagnostic continues on MPS; no card candidate has been trained.

## Shared recommendation — SUGGESTED

All three recommend a continuation scratchpad as the first experiment. A write at one round can improve the next round's answer. A full bookmark also requires learning when an attempt failed, which earlier state to restore, and how to continue differently. Existing answer and halt losses do not directly label those decisions. This argument concerns ease of learning; it does not establish that a scratchpad will work or that bookmarks cannot work.

The proposed external store has eight learned slots, 16-dimensional keys and values, learned read/write gates, three biasless 256-to-16 projections, and a value decoder tied to the value projection. Its calculated cost is 12,930 added parameters, 0.7853% of the 1,646,494-parameter baseline. This budget remains to be checked on an implementation after the baseline gate. Card contents reset per puzzle. What, when, and which slot are learned; no arithmetic addressing rules or solver card labels are supplied.

## Strongest objection from each perspective — SUGGESTED

- Scratchpad: the core may memorize practice pairs and ignore the cards. Soft writing to many slots can blur them together. A useful write receives loss gradients only through a later read in the same graded window.
- Bookmark: a pooled vector may lose which input positions were already used. A compressed per-token snapshot would retain position-specific features. Any restore should preserve some current controller state; restoring precisely the same complete state and input with a deterministic transition would reproduce the same continuation.
- Skeptic/hybrid: low-rank cards may not preserve enough context. Shared-transformer scratch tokens are another low-parameter proposal, but also add attention computation and do not inherently implement rollback. Parameter matching is not compute matching.

The inherited recipe samples 1–16 total rounds and at most six graded rounds. Free-round state is detached. For a card variant the memory must follow the same detach boundary, limiting feedback across a long write–read interval. Evaluation uses 48 rounds, making long-run drift a further development diagnostic.

## What Ben's wiping comparison establishes

SHOWN from the cited prior toy report, not this puzzle experiment: final-answer-only selection among look-alike cards reached at most 182/512. That result motivates checking useful retrieval; it does not predict the outcome here.

Planned intervention: score the same frozen candidate on the same puzzles with intact cards and with card keys/values zeroed immediately before every read. Keep learned controllers and the rest of the computation intact. Wiping only at puzzle start is insufficient because the normal store already resets then.

SUGGESTED interpretation: a reliable score drop establishes dependence on the stored contents under this intervention. A separate paired baseline comparison is needed to establish improved performance. Neither alone proves arithmetic representations or backtracking, and wiping can induce an internal-state distribution shift. Attention/gate traces are descriptive evidence only.

The proposed N5 marks already recorded in REVISION-NOTE.md are unchanged. Agent suggestions for development falsification do not add an unregistered stopping rule or authorize selectively withholding sealed results after a registered experiment begins. No architecture or PASSMARKS is made immutable by this discussion.

## Decision still to make

SUGGESTED first candidate: learned latent scratch cards whose retrieved content modifies the current attempt. Full restoration and per-token snapshots remain alternatives for a separately scoped experiment. UNTESTED: whether any of these designs learns useful card selection or generalizes to unseen number hands.
