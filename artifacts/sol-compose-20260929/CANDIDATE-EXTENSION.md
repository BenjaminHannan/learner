# Candidate/filter extension boundary — API proposal only

Dedicated researcher owns dreamer/filter research. No literature search, training or change to this experiment. Relevant existing internal designs located/read:

- `design/v3/30-modes/creative-roadmap-2026-09-25.md`: reasoner tries, candidate generation produces attempts, filter keeps verified successes, sleep learns from them. Its old model-text/LoRA experiments are historical and NOT compatible training authority under today's no-model-authored-text constraint.
- `design/v3/30-modes/33-creative-stopping-mechanism-fable.md`: designed/unbuilt candidate→filter→checker and bounded stopping; differentiate a filter's preference from verified correctness. Old routing rules, hand-built proposers and text templates are NOT adopted.
- Other relevant file paths discovered (NOT reviewed/evidence): `design/v3/30-modes/gpt-xhigh-creative-mode.md`, `design/v3/30-modes/research-creative-2026-09-24.md`, `design/v3/30-modes/brd-13-reasoner-own-hits-proposal.md`, `design/v3/30-modes/50-reasoner-on-notebook-opus.md`. Do not infer implementation from titles.

Proposed reasoner-owned interface, compatible with `State.board` and NotebookState:

```python
CandidateBatch:
    proposed_board: FloatTensor[B,C,T,64]
    mask: BoolTensor[B,C]
    proposal_logprob: FloatTensor[B,C]
    parent_round: IntTensor[B,C]

propose(context, state, notebook_state, generator, candidate_cap) -> CandidateBatch
filter(context, parent_state, candidates) -> FilterScores[B,C]
commit(parent_state, candidates, learned_weights) -> State
```

All are learned modules inside the attention/sparse-MLP recurrent reasoner. Candidates are latent states, never English thoughts or prompts sent to an external LLM. Proposal generation consumes the same notebook vectors and shared board as composition. Learned filtering attends to parent/candidate states and notebook vectors; a differentiable weighted commit updates the shared board and makes a chosen candidate available to BOTH programs on the next round. Final output translator still receives only the resulting final board. Its wording cannot be the filter's evidence.

Verification boundary: on TRAIN, exact symbolic checker labels candidate consequences from independently generated raw tasks; the checker is not a model-time solver/routing rule. For real human facts, provenance verifier confirms exact source identity and permitted evidence, not arbitrary claim truth. Unverified candidate content remains a candidate and cannot become a taught notebook fact. Proposer training uses verified symbolic labels or verified human feedback; no model-authored natural-language targets/templates. Sleep replays original permitted input facts/targets alongside accepted latent trajectories, without converting generated English into training text. No final holdout may provide filter training labels.

Next separately sealed test should add only this reasoner-owned proposal/filter path, with same-compute random/unguided proposal, no-filter and existing composition controls, ≥2 seeds, source-matched measured noise and bounded candidate count. Filter generalization, anti-collapse, failure detection, sleep benefit and interruption must be evaluated separately. Nothing in this package measures them.
