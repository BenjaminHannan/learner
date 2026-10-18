# Span cards: code-review log

Status: DRAFT, unsealed, nothing booked. The review is Claude Code's built-in `/code-review` on branch
`span-cards-solve` (diff `main...HEAD`). Each round's verdict is my classification; the coordinator rules.
Latest: round 4 (below). The final re-review of bd28adcd7 shows no blocking finding (my classification), which is
the ruled condition for sealing and for booking Stage 0. Neither has been done; both wait for the coordinator.

## Round 1: review of 4b49ec92d (10 findings)
Blocking: (1) per-call tensors left on the model made every `read_only` evaluation raise (reproduced);
(2) the gate read undetached reader states, so the surrogate and rate loss trained the reader (an A/B
confound). Correctness: (3) cap-forced starts leaked in the soft surrogate; (4) reflow could push a question
past MAX_GOLD silently. Items 5-10: efficiency and cleanup (deferred by ruling).
**Fixed in fb97fe9db** with one regression test each (read_only evaluation plus a trainer with eval hooks;
reader gradient equals the hard pool's; cap starts hard in the surrogate, with the old stay shown to leak;
reflow gold_over_max counted). Tests: 92 passed, 1 skipped (pre-existing).

## Round 2: review of fb97fe9db (10 findings)
Blocking (new): the teacher loop budget and gold-mode preload width count gold LINES, while span gold counted
every overlapping card, so split layouts could need more fetches than the schedule allows (an A/B confound).
Small: `ages()` base signature; reflow `line_ents_over_max` undercount; `span_newline_precision` reads below
1 at init; the cap splits lines longer than 64 tokens at init. The rest repeated deferred items.
**Fixed in 0f8222ea1** (ruled rule: one gold card per evidence line, the card holding most of its tokens,
ties to the later card, so `|G_cards| <= |G_lines|` and the schedule and FLOP charge are unchanged). Tests:
unequal splits pick the larger piece; a merged card is gold once; on cap-split layouts every told question
has gold cards <= gold lines, and gold and teacher mode fetch every gold card within the planned loops. The
old rule broke `cards <= lines` on every told question of those batches (18/18, 20/20, 19/19), so the test
discriminates. **Cleanup 9b8fdb87d** (separate commit, as ruled): `ages()` accepts the base signature for a
single-visit store and still raises for several. Tests: 94 passed, 1 skipped (pre-existing), then 28/28
span-card tests after the cleanup.

## Round 3: review of 9b8fdb87d (10 findings): verdict NO NEW BLOCKING FINDING (my classification)

| # | Finding | Class | Reasoning |
|---|---|---|---|
| 1 | The rate loss counts forced starts (walls, cap) in F and the gate's p at forced positions in G, so the gate gets rate gradient where its output cannot change the layout | **new, should-fix, not blocking** | Since fb97fe9db the rate loss reaches only the gate's three parameters, so it cannot change the reader, pool or think loop; it cannot tilt the comparison against LINE. N is tokens per non-question line, so a per-line layout (walls included) sits exactly at F = 1/N, and the coupling does not move the target. The effect is on the gate's own learning signal: forced positions dilute G and add same-sign gradient to `newline_weight` and the bias. Proposed fix: compute F and G over gate-decided positions only (cardable and not forced), with N rescaled to match. One function, with a test. |
| 2 | The 64-token cap splits lines over 64 tokens at init, so "exactly one card per line" fails for them | repeat (round 2 small item, waits) | Measured village lines: 6-26 tokens. The branch-point identity holds on real data (12 visits, full size). Needs a docstring caveat, or a pre-flight assert that no non-question line exceeds max_span. |
| 3 | `forward` adds `w_rate * rate` whatever `weights` the caller passed (also in gold mode) | **new, minor** | The rate gradient reaches only the gate, so other parameters are unaffected; the reported `loss` differs by about 0.03. The run card's bars use accuracy, not loss. Fix: take the weight from `weights.get("rate", w_rate)` when `weights` is given. |
| 4 | The span writer drops `CardStore.write`'s `card_end` rule, so a line truncated by the batch still gets a card | **new, minor** (the builder had noted it) | `collate` always holds whole visits and `crop_to_windows` keeps whole lines before the question, so this pipeline never produces a truncated line. Fix: invalidate segments whose last line has no `card_end` in the batch. |
| 5 | `soft_pool` materialises `[cards, max_span, d]` (about 160 MB at about 5k cards) | repeat (deferred) | The memory and FLOP note is already recorded; Stage 0 measures it. |
| 6 | reflow `line_ents_over_max` skips question lines | repeat (waits) | |
| 7 | double insert recording and a discarded card_stats on tracked steps | repeat (deferred) | |
| 8 | `card_stats_from_sets` duplicates `train.card_stats` | repeat (deferred) | |
| 9 | `card_economy` reads and writes twice per batch | repeat (deferred) | |
| 10 | the gold loop runs over all MAX_GOLD columns, plus host syncs | efficiency (new code, not blocking) | Restrict the loop to columns with `present.any()`. |

Request to the coordinator: rule whether finding 1 (and the minor findings 3-4) should be fixed before the card
is sealed. By my reading none of the three is blocking, but finding 1 does change what the gate learns from,
so I would fix it before Stage 1 at the latest. I have not patched anything after round 3.

## Round 4: the round-3 fixes ($0, CPU only) and their re-review
**Ruling (coordinator, round 3):** fix finding 1 (the rate loss counted forced starts) and minors 3-4 before
sealing, in one $0 round, then re-run the built-in review on the new diff. No seal and no Stage 0 booking until
a re-review shows no blocking finding. The rest of the round-2 ruling stands, so efficiency and cleanup items
stay deferred. This round was done by a continuation session; the original session's environment did not
reconnect. Before any change I checked the branch tip (80a735716) and PR #82: neither held any round-3 fix.

**Fixes, in four commits:**
- **07e57591e.** Finding 1, as built: F still counts every start. Forced starts are cards and use up the
  budget. In G a forced start is a constant 1, and only gate-decided positions contribute p. *Deviation from the
  proposed form* ("F and G over decided positions only, N rescaled"): that form uses
  N' = decided / (cardable/N - forced), which has a pole when the forced starts alone use up the budget. The
  per-line layout hits that pole exactly when every wall region is one line. Both forms have the same zero
  (chosen starts = cardable/N - forced) and the same gradient sign; a test checks this. Minor 3: the rate weight
  is `weights.get("rate", w_rate)` when the caller passes `weights`. With no `weights` it is `w_rate`, in gold
  mode too, because the rate loss reaches only the gate. Minor 4: a span card is written only if its last line
  has a `card_end` token in the batch (`CardStore.write`'s rule). The tokens of a dropped card are outside every
  card. Each fix has a regression test that fails on 80a735716.
- **Re-review A (of 07e57591e, 10 findings).** Finding 1 was still incomplete: `forced = start & ~chosen`
  called a wall start "chosen" wherever the gate also fires. That is every line after a question line, where
  p is about 0.98: 6 of 8 wall starts on a test batch, with rate gradient 5.9e-5 there. Minor 4 was also
  incomplete: dropped cards kept real tags, ents and lines. **e2a50ff1f** fixes both (every wall start is
  forced; dropped cards carry -1). **ff1718222** corrects three statements in the docs, with no code change. The
  module docstring still gave the superseded gold rule. `validate`'s recall@4 and `cards` block are invalid for
  span cards, not "approximate". No bar or guard reads them: the run card uses `card_economy`. Failure mode F3
  named a metric that does not exist; it now names `card_economy.first_ask_recall`. A new item, not blocking:
  `SpanConfig.newline_id` defaults to 23 and nothing checks it. The run card sets it to the v2 tokenizer's id.
  *Recommendation:* add a Stage 0 pre-flight check that `card_economy.line_aligned == 1` at the branch point.
  The rest were repeats (deferred or waiting).
- **Re-review B (of ff1718222, 10 findings).** Finding 1 was still incomplete for the cap: a gate-chosen start
  that lands exactly on a `max_span` cap position was treated as gate-decided, though the cap starts a card
  there anyway. That gave rate gradient there, and the surrogate leaked content across a cut the hard pool
  always makes (only once the gate merges up to 64 tokens). Also, the logged `gate_mean` was the raw mean p, not
  the loss's G. **bd28adcd7** moves the start rule into a pure function, `hard_starts`. `forced` is now every
  wall start plus every cap position, chosen or not. A brute-force test flips the gate at every token of 40
  random layouts and checks that `forced` equals "is still a start"; it fails on e2a50ff1f. `gate_mean` is now
  the loss's G (`soft_starts`); `gate_mid` still reads p. Two new items, not blocking: (a) `reset_parameters()`
  would wipe the gate's init. It is called only inside `PremonitionMini.__init__`, before the writer is swapped,
  so no live path reaches it. (b) Design §3.5's FLOP note describes a banded per-chunk surrogate and a `chunk`
  field. The code gathers `[cards, max_span, d]` and has no `chunk` field. This belongs to the deferred
  memory item, but the design will be sealed, so **the coordinator should rule whether §3.5 is corrected before
  sealing.**

**Tests (final, bd28adcd7):** 86 passed, 1 skipped (pre-existing) over the model, data, span-card, reflow and
train suites; the span-card file has 34 tests, all passing. Every new test was checked against the commit before
its fix and fails there at the intended assertion.

### Re-review C (of bd28adcd7, the final diff, 10 findings): verdict NO BLOCKING FINDING (my classification)

| # | Finding | Class | Reasoning |
|---|---|---|---|
| 1 | `validate`'s recall@4, chance baseline and `cards` block are wrong for span models, with no runtime guard | repeat (re-review A; documented in ff1718222) | No bar or guard reads them. P1-P6 use accuracy, and G1-G5 and §8 use `card_economy`. A runtime flag is cleanup. |
| 2 | reflow `line_ents_over_max` skips question lines | repeat (round 3 #6, waits) | |
| 3 | the cap splits lines longer than `max_span` at init | repeat (round 2, round 3 #2, waits) | Measured village lines are 6-26 tokens, under 64. |
| 4 | `span_newline_precision` reads below 1 at init (row-initial walls) | repeat (round 2 small item, waits) | A training log statistic only; `card_economy`'s precision is the reported one. |
| 5 | a reflowed cache keeps the original `preprocess` identity, so diagnostics cannot tell it from the original | **new, should-fix, not blocking** | It affects Cell B and E3 (Stages 1-2), not Stage 0. The seal list hashes the cache files, so a run's cache is identified anyway. Fix before Cell B runs: add the reflow to the identity. |
| 6 | `soft_pool` materialises `[cards, max_span, d]` twice | repeat (deferred; see re-review B (b)) | Stage 0 measures it. |
| 7 | the gold loop runs over all MAX_GOLD columns, with host syncs | repeat (round 3 #10, efficiency) | |
| 8 | double insert recording on tracked steps | repeat (deferred) | |
| 9 | `card_stats_from_sets` duplicates `train.card_stats` | repeat (deferred) | |
| 10 | reflow recomputes `ents_over_max` over unchanged lines in Python | new, efficiency | Offline cache build only. |

Requests to the coordinator: (1) confirm the verdict, which is the condition for sealing and for booking
Stage 0; (2) rule on re-review B (b), whether §3.5's FLOP note is corrected before sealing; (3) optionally add the
`line_aligned == 1` branch-point check to the Stage 0 pre-flight. This round ran the built-in review three times,
not once, because the first two re-reviews showed that finding 1's fix was incomplete.
