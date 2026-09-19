# Step 3 — Remaining issues and decisions

2026-09-18. Ben's answers to the twelve open issues, plus the measured training speed. All items were agreed by Ben on 2026-09-18.

## Measured: training speed on the RTX 5070 Ti

A plain causal transformer, sequence 512, vocabulary 2,048, bf16, fused AdamW, batch 32-128 (`design/pilots/gpu_throughput.py`):

| Model | Parameters | Tokens/s | Tokens per 10 min | Tokens per day | Peak GPU memory |
|---|---|---|---|---|---|
| small | 4.3M | 1.24M | 0.75B | ~107B | 1.0-4.0 GB |
| medium | 12.4M | 0.54M | 0.32B | ~46B | 1.9-7.1 GB |
| large | 27.6M | 0.28M | 0.17B | ~24B | 3.1-11.4 GB |
| base | 88.6M | ~99k | 59M | ~8.5B | 2.9-7.1 GB |
| big | 307M | ~32k | 19M | ~2.8B | 8.8-12.4 GB (batch 8-16) |
| huge | 687M | does not fit | — | — | 17+ GB |

Measured 2026-09-18 (`design/pilots/gpu_throughput_big.py`). **Trap:** past about 15 GB, Windows spills GPU memory into system RAM instead of failing. The 307M model at batch 32 (19.5 GB) fell to 1.8k tokens/s, and the 687M model to about 1k tokens/s. Every run must check peak GPU memory stays under 14 GB and abort otherwise.

This is the upper bound for a plain network. The library, fast memory, thinking loop and sleep will all slow it down. Hardware for world simulation: BensPC has a Ryzen 5 7600X (6 cores / 12 threads) and 47 GB RAM; the Mac (M1 Pro, 32 GB) runs the Bonsai teacher.

## Decisions by issue

1. **Forgetting vs stiffness (agreed).** Detect early instead of waiting: log health gauges from day one (dead units, weight size, effective rank, how fast the model learns a fresh task) and run a fast stress test (tasks that change every few thousand steps, which make small networks stiffen within minutes). Fixes to compare: continual backprop (periodically reset the least-used units), L2-Init, the sparse library, and replay. At the measured speed, the small model reaches the ~30B tokens where stiffening was reported in about 7 hours, so an overnight "life" test moves much earlier.
2. **Reusable pieces (agreed).** Push toward reuse three ways: the world builds tasks from shared sub-skills; the library has a limited piece budget; training spans many villages. Measure it with the transfer test and by checking whether related tasks use the same pieces.
3. **Childhood phase (agreed).** Before fast learning is expected, the model learns the village language and basic world rules the ordinary way. At the measured speed this is minutes to hours, not weeks.
4. **One memory, searched by cosine similarity (agreed, from Ben's idea).** One library searched by similarity (attention), with two kinds of slots: *episode slots* written instantly from one exposure, and *knowledge slots* learned gradually. Similarity is computed on the **key** (what a memory is about, e.g. "Nera + where"), not the whole sentence, so "Nera is in the barn" updates "Nera is in the mill" while "Mira is in the barn" becomes a new memory. Sleep turns episode slots into knowledge and frees them.
5. **Following instructions: copying (agreed).** Imitation: the teacher demonstrates following a rule step by step and the model learns to reproduce each step. Thousands of different made-up rules are used, and the model is always tested on rules it has never seen demonstrated. Direct step-by-step training rather than one reward at the end, plus a copy mechanism for moving names from the instruction into working memory.
6. **Correcting consolidated facts (agreed).**
   - *Versions:* every memory is time-stamped; for the same key, the newest wins at recall.
   - *Contradiction detection:* a new memory whose key matches an existing one (high key similarity) but whose value differs is a correction. The new one is stored and linked to the old one.
   - *Reconsolidation in sleep:* corrections get priority replay. Training raises the new answer and explicitly lowers the old one, editing mainly the few library slots that key activates.
   - *Relapse test:* teach, consolidate, correct, consolidate, keep learning other things, then ask. It must give the new answer, and the old one must not come back. The world supplies changing facts (people move, village rules flip).
   - *History is kept (agreed):* the old version stays, marked as past ("Nera used to live in the mill").
7. **Checking its work (agreed in principle).** A checker head, trained from the world's right/wrong feedback on the model's own attempts, predicts whether an answer is right; checking is usually easier than solving. It also learns checking strategies: re-derive another way, compare with memory, plug the answer back in. Only checked practice results get consolidated; uncertain ones go to the teacher. Calibration is measured: when it says 90% sure, it should be right about 90% of the time.
8. **Deciding how long to think: the model decides (agreed).** The decision to stop comes from the model's own thinking: while thinking, it can emit a "done" token whenever it judges the answer good enough. It still needs to learn *when* that is. The lesson it learns from is to stop at the first step after which more thinking no longer improves the answer (its answer is scored at every step), with no flat per-step penalty. Later, reward from getting answers right refines the timing further. A hard maximum stays only as a safety net against infinite loops. Measured: accuracy versus thinking steps, and whether it thinks longer on harder questions.
9. **Always compare against simple baselines (agreed).** Every experiment includes a plain network with the same compute and plain text lookup. A component counts as working only if it clearly beats them.
10. **Leaks (agreed).** The two leak detectors run automatically on every test set from day one; they cost seconds.
11. **Speed (done).** Measured above. The world simulator must produce about 1.2M tokens/s to keep up; it runs on BensPC's 12 CPU threads with many villages in parallel in its 47 GB RAM.
12. **Real English (agreed path).**
    - (A) Widen the village language gradually with Bonsai-written stories and dialogues. Small models trained on simple, varied, model-written stories (TinyStories) learned fluent simple English.
    - (B) Real child-level text (BabyLM corpora, 10-100M words). Ben approved the path; the exact file, source and size will be confirmed with him before downloading.
    - (C) Conversation practice with Bonsai as a partner, using the feedback system.
    - Realistic target: fluent simple English. Adult-level knowledge would need far more model and data than one GPU provides.
