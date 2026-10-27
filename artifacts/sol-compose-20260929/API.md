# Minimal composition interface — 2026-09-30 UTC

Diagnostic implementation: scripts/sol_compose_model.py. Target remains thin bidirectional translator + learned-stop recurrent transformer attention core with sparse MLP experts + sleep. Record/numeric GRU programs are diagnostic adapters, not a replacement architecture. No sleep change in this experiment.

Inputs: `InputBatch(tokens: int64[B,R,4], slots: bool[B,R,4], valid: bool[B,R,4])`. No labels, task IDs, family metadata, oracle intermediate values, routes or answers are accepted by the model.

- `encode(inputs) -> Context`: immutable per-call translated input; equality incidence, numerical vocabulary grounding, field and slot encodings only.
- `initial_state(context) -> State`: zeros for transformer board and private program state.
- `step(context, state) -> State`: one transformer round; attention reads program proposals; top-2-of-4 MLP experts execute per token; both diagnostic programs execute, without an order dispatch rule.
- `read(state) -> (logits[B,R,125], halt_logit[B])`: learned readout from board only. No source logits, operator answer heads or residual answer passthrough.
- Context/State `.select(indices)` supports removing stopped examples and batch permutations. Every call owns its tensors; no cached batch or route on model.
- `rollout(inputs, rounds=6)` retains all gradients and all round reads.
- `infer(inputs, cap=6, min_rounds=2, threshold=.5)` uses learned halt and removes completed rows. Last-state decoder can consume `State.board[B,R,64]`; slots remain external for selecting answer locations.

A future natural-language translator must produce equivalent input state without implementing lookup, increment or order interpretation. The stop head uses pooled board state only; correctness supervision is TRAIN-only and detached. Sleep is a later, separately sealed experiment.

TRAIN symbolic expressions apply lookup then increment. Dev expressions apply increment then lookup; dev also withholds table permutation cycle structures. The expression order is ordinary symbolic input syntax, never a route label. Cut-feedback ablation retains program exports and fusion but gives both programs zero shared feedback; it tests recurrent exchange, not whether a final fusion layer can combine independent programs.

## Ready joined extension (2026-09-30)

`NotebookState(translated[B,M,64], mask[B,M])` has no raw text/reference field. `Composer.encode(inputs, memory=notebook_state)` inserts memory into the reasoner's attention; symbolic table records serve as notebook facts by default. The query alone occupies the prompt lane. `read`/symbolic head consume only board. `BaseContextAdapter` provides source/SleepMoE-compatible learned memory attention, explicit state selection, stop and d64 export; this adapter is untrained and its source signature has only mechanics coverage. SleepMoE integration still needs its owner's check because it restores geometry on dispatch.

`sol_compose_run.py infer --checkpoint ... --input ... --memory ... --output ...` writes `sol_compose.final-latent.v1` with final_state and rounds. Input JSON contains tokens and slots only. Memory .pt, if supplied, contains translated and mask tensors only. Exact notebook raw bytes/provenance stay in NotebookStore outside the output translator. A trained symbolic checkpoint comes ONLY from the presealed queued run; none exists yet.

Dreamer/filter extension is proposed in CANDIDATE-EXTENSION.md, unimplemented and not researched here. Candidate commit writes shared board, connecting both programs on the following round. Current job's actual sleep replays code-generated notebook experiences; accepted latent candidate replay is a separate future test.
