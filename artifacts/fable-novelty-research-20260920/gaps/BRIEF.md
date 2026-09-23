# Shared brief for the six "is this really missing from AI?" checks (2026-09-20)

Research only: web search + reading. Create ONLY your own output file. Do not edit anything else. Do not invent citations — every reference must be one you
found and checked; if a detail (year, venue) is unverified, say so. Paraphrase; no quote over 15 words. Reader: Ben, a high-school senior — plain words, short,
lead with the answer. Be sceptical: the claim you are checking came from Fable's memory, not from a search, and may be wrong.

## Our model (so proposals are concrete)
Toy world: stories of fact rows (person, relation, value) + LINK rows (person -> person); 16 entity IDs; relations 8/9/10 + LINK. Questions: "follow LINK k times
from X, then read relation r". Parts: a learned LOOKUP OPERATOR (~79k params, attention over rows) and a learned DISPATCHER/controller (15–24k params, RLOO
reinforcement, trained on 1–3 hop chains) that picks the next lookup, feeds results forward and decides when to stop. Reusing one operator per step gives
held-out-combination transfer a plain transformer lacks (plain transformer: 8/25 cells; our system with two hand-supplied bookkeeping hints: 25/25).
Known bug: with the hints removed, the controller learns "make 3 calls then stop" (its longest practised chain) — 64/64 up to 3 hops, 4/64 beyond.
A plain transformer fails the same way. The system only recombines one known operation; it never invents anything.
Already proposed separately (do not re-propose): an offline "dream phase" (splice own traces -> verify with frozen operator -> compress into macros), and a
stall-triggered gain head. Constraints: Mac + one consumer GPU, each experiment < 30 min, pre-registered pass marks, one change at a time, toy first.

## Your output file: sections
1. **Verdict (<= 80 words):** is this brain mechanism really absent from AI architectures? Choose: "genuinely open" / "tried at small scale, not mainstream" /
   "already well covered" / "tried and mostly didn't help". 
2. **What the brain does** — the actual evidence, with its quality (strong / moderate / speculative; say if correlational or contested or failed to replicate).
3. **What AI has already done** — the closest 4–8 works, prioritising 2023–2026 (name, year, link, one line on what it showed and at what scale). Include negative results.
4. **The real gap** — precisely what has NOT been done, if anything.
5. **Smallest version for our model** — module, inputs/outputs, what is learned vs fixed, rough params; a falsifiable toy experiment (task, controls incl.
   matched-compute, pass mark, what would show it doesn't help, main artefact risk). Say honestly if it does not fit our toy.
6. **Priority score 1–5** for us (5 = do soon) with one sentence why.
7. References with links.

Final reply to Fable: sections 1, 4, 6 condensed + file path.
