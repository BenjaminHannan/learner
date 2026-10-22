# Run card SC-1: seal

Sealed 2026-10-18 under the coordinator's round-3 close-out ruling. The Q20 review gate is satisfied: the
final re-review (of bd28adcd7) shows no blocking finding (`04-review-log.md`, round 4 and its close-out). The
files below are hashed at commit **f317420f9add344ad2f797766a010305554435a6** (branch `span-cards-solve`), with
`sha256sum` (the same digest as `shasum -a 256`). Nothing listed here may change. A change to any of these files
means a new card.

## Part 1: the card and the code (section 9), sealed now

| sha256 | file |
|---|---|
| 9d28907542a4792917c2f1aab8036493d61d11ae60bc637fc68279191af09373 | design/span-cards/02-run-card.md |
| 57dc98def4e1c0e28d12bd5d444f1845edacbb9e3161553875526d7cd78ddb3a | premonition/span_cards.py |
| df403f8b2c4ce9d4fb285e02b9ec6f242bbd0ba9728a05e08c4dfa3bdbc19ef1 | premonition/reflow.py |
| f6d8c36093f8d392a7a680db3ab46b5dc6b28bee3475d6cb9e3e58be6404fda5 | premonition/model.py |
| 62c75d70b369daf61cf862b28f87aa64bf6037314dd1a39a7df994b81d2b9531 | premonition/store.py |
| f7b945f080807c5dc4a5d91325d7ae3c760ea2de75c7bdf13c6da4c254f4deb9 | premonition/train.py |
| 3b8ce41ceca5e298d334232551ebd084b20af4b08dacfb042c5daa714b96db4c | premonition/data.py |
| 7277264da80842a4c2610daf043363c335f8122f7dd22d2e5874c0f9ac6ca127 | premonition/slices.py |
| 9789bfb0f7d5f7b964fa16ee5d4a6d8ef1ed0eee51c604a3a1776ead638ac78c | premonition/exp1.py |

Q21 fills in the sealed card: the term mappings of section 2 as confirmed (primary ruler `far`; `far_deep`
secondary only); P_s built fresh inside Stage 1; `newline_id = 23` (v2-fallback tokenizer).

## Part 2: the data addendum (sealed 2026-10-18, before any arm runs)
Built independently on the three Stage 1 boxes (seeds 0, 1, 2) by `scripts/span_stage1.py` at commit 707bdce90;
every box reported the same hashes and counts.

| item | value |
|---|---|
| run script | `scripts/span_stage1.py`, sha256 47577a35969c83f70f900e4d3845bf1ff8973644b664a67091d4ca92cdd6d127 (commit 707bdce90) |
| code digest (premonition, learnlab, memorylab, span_stage0, span_stage1) | 5c2b92374a40d16ea984926d769b3cf491275aa1e7c48f1fe0817ee0d809ca95 |
| `premonition/span_cards.py` | sha256 57dc98def4e1c0e28d12bd5d444f1845edacbb9e3161553875526d7cd78ddb3a |
| data tag | large-seed0-53292765806d |
| tokenizer | 2c9d06aed330932b48bb1b173e42952f4bba6ec752e4781c6a253f63cec0973a |
| name detector | ef6b1d4dc52dd6f03b4f2c3ee036cc56ef7fa9668fb84d3aa15b698eaad17f22 |
| train cache | `data/village/stream/cache/large-seed0-53292765806d/premonition-v2-2c9d06aed330-ef6b1d4dc52d-9add8e2fded1/train.pt`, sha256 a53ab45bba46f71190a40e91eb386d3dab9363dba87fd874c0312d8d62bc6cd9 |
| validation cache | same folder, `validation.pt`, sha256 762082f1d2fb28c7a49d35301368fc2e2166d5eda027f63732bab0413d333549 |
| visits / questions | train 100,000 / 855,962; validation 1,000 / 8,675 |
| tokens | train 112,736,485; validation 1,165,078 |
| newline id | [23] (as filled in the card) |
| **N** | **11.155539** |

N is the card's quantity, `span_cards.tokens_per_line(train cache)` (mean tokens per non-question line). The script
computes it from the integer counts in float64 and rounds it to 6 decimals (`exact_n`), so every box gets the same
digits. The float32 mean in `tokens_per_line` can differ only below the 6th significant figure. The pilot value was
11.17 (256 visits). The go file repeats N and both cache hashes, and each box refuses a go that does not match its own.

## Not sealed (on purpose)
`scripts/span_stage0.py` (sha256 c4a9a5082cfe13208511ca097f1366850323758df181c53aa3d93f60f8bf0191 at the same
commit) is the Stage 0 measurement, not a registered run. Its hash is recorded so that the Stage 0 report can be
tied to the exact code it ran. The design (`01-design.md`) is not in section 9 either.
