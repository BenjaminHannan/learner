Read the shared brief FIRST and follow its required report structure exactly: /private/tmp/claude-502/-Users-ben-hannan-Desktop-projects-beautiful-model/a6cbbe20-5a16-4ad6-87ee-2f54ff4ef5c6/scratchpad/agents/brief.md
Then read the four files it lists. Write your whole report in ONE final message.

You are Reviewer 5 of 5: EXPERIMENTAL AND RESOURCE AUDITOR. Your assigned research question: would the proposed comparisons and protocols produce interpretable, fair, adequately powered results within the stated compute and storage limits, and could a failure be explained by inadequate training rather than by the design?

Challenge specifically:
- Fairness of the four core conditions (no persistent writes; fixed-rule writes; learned writer at equal memory capacity; ordinary gradient updates with replay): what differs between them beyond the intended variable, what tuning each needs, and what "equal capacity" should mean for a matrix memory vs. gradient updates.
- Leakage: tasks.py uses disjoint numeric seed ranges per split but shares templates, entities, and the answer space; the teaching input and the query input can be identical strings; replay contains answers; the writer receives the target. Which of these leak, and how would you detect leakage empirically?
- Confounded controls: "known-good keys," "memory zeroing," "between-world swaps," "paired continuation," full-trace vs final-state vs output-only writer inputs. Which of these are confounded as described in RESEARCH_REVIEW.md, and how to fix them?
- Statistical power: chance is 1/8; there are 24 entities per world. For B and D effect sizes you consider meaningful, estimate how many worlds, queries, and seeds are needed, and whether that fits in ten-minute runs. Analyze the E[max(0, eps)] > 0 bias in D and propose an unbiased or paired alternative.
- Reward noise for writer training: how much signal per write does R = B - lambda D carry, and what audit frequency makes the estimate usable?
- Compute and storage accounting: VRAM for differentiating through functional writes over unrolled episodes; activation memory vs the 16 bytes/parameter figure; checkpoint, trace, and optimizer peaks against the 100 GB hard limit and 80 GB target; note that run.py currently passes 10 GB / 8 GB defaults while the constants say 100 GB / 80 GB. Is the ten-minute cap compatible with training the encoder, reader, and writer from scratch at all?
- Inadequate training vs design failure: what positive controls and sample-size calculations would let a null result be attributed correctly? What pilot measurements should be frozen before any confirmatory run?
- Reproducibility: what exactly must be saved so a latent trajectory can be replayed (the review says generator seeds alone do not suffice)?
