# lispanel301 key audit (2026-09-23)

The panel and its key were written blind by one Opus agent, from the spec, SPEC-COUNTS and frame-spec-notes-301 only. A second Opus agent relabelled all 240 turns blind (label_B.jsonl), seeing neither the key nor any training data. The comparison uses `scripts/claude_lis300_agree.py`, which checks saved facts after the compiler, whose-asks, acts and ask objects. The listener thread saw counts and ids only; no item was read.

- **First pass:** 239 of 240 agreed on everything. The 1 disagreement (p301-094, tell-self) was on saved facts.
- **Adjudication:** a third blind Opus agent looked at that one row only and sided with label_B (ADJUDICATION.md). The rule was that every mentioned fact is listed, and an unlisted relation gets rel "other", which makes the compiler save nothing on that turn. `key_v2.jsonl` is key.jsonl with only that row changed.
- **After adjudication:** key_v2 agrees with label_B on 240 of 240.

The registered lis-301 run grades against **key_v2.jsonl** (sealed in SEAL-key.sha256.txt).

**Overlap check:** exactly one panel turn also appears as a training turn (lis-300 or lis-301 Opus rows, compared case-insensitively). It is p301-202, a 2-word chat turn that saves nothing. It is kept; the check saw the family and word count only.
