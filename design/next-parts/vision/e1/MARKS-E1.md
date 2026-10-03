# E1 run: pass marks and protocol, fixed before the run (2026-10-03, vast.ai thread)

Pass marks come unchanged from `DESIGN.md` section 4 (E1). Choices the design left open are fixed here, before any number exists.

**Pipe (today's path, as far as this repo lets a cloud box reach it):** frozen SigLIP2-B/16 @256 -> 2x2 pool to 8x8 -> GridAdapter(h=32, pos2d x0.1, as notebook)
-> looped core (copy of `scripts/claude_fewex_net.py` loop arm: width 256, 2 shared blocks, 4 rounds, CLIP=4 bias) with a learned 4x4 query grid standing in for the
text question -> 16 query states average-pooled in pairs to **8 prefix vectors** -> Linear(256, 2048) -> frozen LFM2.5-1.2B-Instruct -> caption loss.
Deviations, stated up front: the core starts from random weights (the trained card-task core is not reachable from the box); the question is a learned constant, not text;
captions are synthetic (colour, shape, 3x3 position) so same-scene distractors can be built exactly, not COCO.

**Data:** 2-4 coloured shapes (6 colours, 3 shapes) in distinct cells of a 3x3 grid; caption lists them in reading order. 12,000 TRAIN images, 1,000 held-out images from a different seed,
held-out captions removed from TRAIN. Same-scene distractors (for the 8-way pick): same number of objects and same shape multiset, colours and cells re-drawn.

**Arms (each 2 seeds, 2,500 steps, batch 32):** real (trained with its own image), shuffled (trained with another image's features each step), blind (no image tokens).
Plus a test-time shuffle of the trained real model. Controls = {shuffled-trained, blind, real model with test-time shuffle}.

**A (through the pipe):** held-out caption loss in nats per caption token.
**B (around the pipe):** after training, the core is frozen; head = two linear maps (core state mean over the 16 query positions, 256 -> 256; caption embedding = frozen LM mean last hidden state, 2048 -> 256),
dot-product softmax over 8 candidates, trained on TRAIN with fixed candidate sets, 40 epochs, no early stopping on held-out. Scored on held-out. Chance 12.5%.

**Pass (both seeds):** A: real loss <= (best control loss) - 0.15. B: real acc >= 50% and >= (best control acc) + 25 points.
**Proves it wrong (either seed):** A: real within 0.05 nats of the best control. B: real within 10 points of the best control.
Between: report as "inconclusive", no mark changes. Reading table (from DESIGN.md): B passes and A fails -> output pipe loses the image; both fail -> vision path problem; both pass -> fine.
