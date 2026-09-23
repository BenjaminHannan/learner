# 138 — Tonight's agent: stacking the verified pieces (Muse)

Loop138 is an integration, not new science. It stacks tonight's verified
pieces as mixins/wrappers in one new file
(`scripts/fable_loop138_agent.py`); no existing file is edited.

## What is stacked, and how

- **Base: loop134.** `Loop138Ears(Loop134Ears)`, `Loop138Mouth(Loop134Mouth)`,
  `Loop138AgentLoop(Loop134AgentLoop)` — loop121 teach phrasings plus the
  three loop117 fixes (F5 please-forget space, M5 shouted possessives,
  underscore-free replies), inherited unchanged.
- **Punctuation (129).** The exact 129b pattern: ears `hear()` sanitizes
  outgoing teach/correct actions, and loop `_act()` sanitizes again just
  before the notebook write (covers the inner-chain delegate path).
  Relation keys, forget/ask/clarify paths untouched.
- **Partial-frame gate (113c).** Loop134's "?" side is exact loop113b, so
  `Loop138Ears.hear` replaces the question branch with the 113c branch
  verbatim (same hearsay screen, both composers, same loop102 fallback),
  calling the frozen `frame_consumes_question()` from
  `scripts/fable_loop113c_agent.py`. A frame that does not consume every
  relation phrase/qualifier falls through to the unchanged loop102 chain.
  Teach side is `super().hear()` (loop134). 113e/135/137 are NOT included:
  no RESULTS.md saying PASS existed when layer 1 closed.
- **Self router (127).** `Loop138AgentLoop.turn()` runs the notebook path
  first and maintains Self99-shaped live state (turn log, mode log, fact
  origins). A notebook-missed turn (empty records, or every record a
  clarify containing "didn't understand"; hearsay and MISSING_FACT never
  route) goes to the self path: `route127` non-DECLINE serves
  `Self99Agent.answer_self` over that live state (via a facade bound to
  the loop's notebook/counters/logs — no loop90 is built); DECLINE serves
  the loop138 decline (frozen HONEST_DECLINE + "Could you say it another
  way?", zero names/numbers). Notebook answers always win; no content is
  ever served on DECLINE. Rationale for the decline wording: the bare
  notebook clarify fails the self decline checks, and the bare
  HONEST_DECLINE fails the redteam abstain-bits; the combined sentence
  passes both while claiming nothing.
- **Live sleep (131).** `build_agent138` calls the frozen
  `retrofit_sleep131`: the reasoner becomes `Sleep131Reasoner` over the
  qualifier-aware reasoner (taught rows beat installed derivations) and
  the sleeper becomes `Sleep104Sleeper` (exp-46 recipe, episode feed from
  the loop's own bare-word questions). Uninstalled, both delegate
  identically, so fresh dirs behave like the lower layers.
- **Exactly-once daemon (108).** `Loop138Daemon` = loop134 mailbox shape +
  the frozen `boot_reconcile` (drops the loop.inbox crash artefact,
  finish-moves ids whose reply is already durable) and a per-turn receipt
  in `process_file`. Routing info is tagged onto the daemon log record.

## Why this order

Each layer only narrows behaviour the layer below left open: punct
cleans spans the base stored dirty; the gate quiets confident prefix
frames; the router speaks only where the notebook stays silent; sleep
only adds derivations where nothing was taught; exactly-once only
touches boot and receipts. If any layer had required changing a lower
layer's behaviour, the build would have stopped there (it did not).

## What it means

One daemon serves notebook questions, honest self-answers about its own
state, sleep-installed derivations that still lose to taught facts, with
exactly-once replies across kills.

## What it does not mean

No new understanding: the ears are still templates, the router still
blind to near-intent blends (Q078), the 3 fresh teach-gap wrongs and the
rt81 UNCLEAR drifts remain, and 113e/135/137 are still out.
