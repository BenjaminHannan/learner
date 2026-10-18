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

## Part 2: the data addendum, sealed before the first arm runs (not yet sealed)
Section 9 also lists the run script, the train and validation cache files, and the value of N. None of them
exists yet: the caches and the run script belong to Stage 1, which is not booked. As the card says (§3), they
are hashed into this file before any arm runs, and N = `span_cards.tokens_per_line(train cache)` is computed
once from the sealed train cache. The pilot value is 11.17 (256 visits); Stage 0 measures it again on its own
caches, but that measurement is a check, not the sealed value.

## Not sealed (on purpose)
`scripts/span_stage0.py` (sha256 c4a9a5082cfe13208511ca097f1366850323758df181c53aa3d93f60f8bf0191 at the same
commit) is the Stage 0 measurement, not a registered run. Its hash is recorded so that the Stage 0 report can be
tied to the exact code it ran. The design (`01-design.md`) is not in section 9 either.
