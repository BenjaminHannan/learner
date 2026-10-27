# Premonition in fourteen sentences

**Suggested:** this summary describes the proposed direction; every promised new capability remains untested, while references to completed probes/results are shown only in their recorded toy setting.

1. Premonition should first show that it can reliably use facts in a new little world, then show that it can keep learning about a world over time.
2. If Mira's friend is Oren and Oren wears blue shoes, answering “What shoes does Mira's friend wear?” requires following two facts.
3. The completed toy probes show that removing the stored cards destroys most successful answering, and restoring them restores every answer.
4. They also show that a pooled card, meaning one vector summarizing a line, can retain information about both Mira and Oren.
5. We should therefore start with a selector, meaning a learned mechanism that chooses which question or card information to use, before giving every word a separate workspace slot.
6. Separate key pooling, meaning learning the lookup address separately from the stored contents, reduced stalled runs in both completed comparisons but has not yet passed the stronger reasoning test.
7. That stronger test changes Mira's friend and checks that the answer follows the new friend, while unrelated changes leave it alone.
8. A matched control is another run with the same starting conditions and budget but only one design choice changed, so we can tell which choice helped.
9. The village track starts with a parser, meaning explicit rules that read the fixed sentence format, so we can study memory before claiming the model understands flexible language.
10. A versioned record keeps both when a fact applies and when the system learned it, so “Oren changed shoes yesterday” differs from “the earlier report was wrong.”
11. A known correction must override an old answer immediately, and missing correction records must cause an honest unavailable answer rather than revive the old one.
12. Consolidation means learning a stored fact into the model's weights, its learned numerical settings, and we will test it with the cards and every other factual hint hidden.
13. Replay means practicing previously observed facts, and any proposed improvement must beat a fair replay comparison after paying for its storage and computation.
14. Fable will identify the hardest evidence-backed problems, Astra will turn them into precise decisions or tests, and a frozen recipe must pass fresh-world checks before we call it dependable.
