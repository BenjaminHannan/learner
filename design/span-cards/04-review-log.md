# Span cards: code-review log

Status: DRAFT, unsealed, nothing booked. The review is Claude Code's built-in `/code-review` on branch
`span-cards-solve` (diff `main...HEAD`). Each round's verdict is my classification; the coordinator rules.

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
