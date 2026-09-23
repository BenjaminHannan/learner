# lispanel300 key audit (2026-09-23)

The key was written blind by one Opus agent. A second Opus agent relabelled all 240 turns without seeing the key (label_B.jsonl). The comparison uses `scripts/claude_lis300_agree.py`, which puts both frames through the write compiler and compares the saved facts, whose-asks, acts and ask objects. Both the listener thread and this note see counts only; no item was read.

- **Saved facts and whose-asks:** the two labellers agree on **240 of 240** turns.
- **Ask objects:** 5 two-hop questions differed only in format. The key used `rel` = first hop plus `"then"` = second hop, while the spec uses `rel` = final hop plus `"via"` = first hop. `key_v2.jsonl` converts those 5 mechanically to the spec form, and after that the ask objects agree on every turn.
- **Acts:** 6 turns with an ambiguous pronoun differ in act (UNCLEAR vs STATE). Both labellers save nothing on them, and the act is not scored except for ASK, so the key's act is kept.

The registered run grades against **key_v2.jsonl** (sealed in SEAL-key.sha256.txt).
