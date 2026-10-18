# Span cards: code-review log

Status: DRAFT, unsealed, nothing booked. The review is Claude Code's built-in `/code-review` on branch
`span-cards-solve` (diff `main...HEAD`). Each round's verdict is my classification; the coordinator rules.
Latest: the round-3 close-out (below). The final re-review of bd28adcd7 shows no blocking finding; the card is
sealed (`05-seal.md`). Stage 0 ran with the reviewed script (5b9033460) and passed its three gates;
the readout is in `06-stage0-report.md`. Stage 1 is not booked.

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

## Round 3 close-out (coordinator ruling, 2026-10-18)
The ruling asked for the re-review's verdict to be recorded. It was already recorded in round 4 above (commit
c502b2caa), which the ruling did not yet see; this section summarises it.

- **What the re-review of the fix diff found.** The review was run three times, each on the diff as it stood.
  (A) On 07e57591e it found finding 1 incomplete: wall starts where the gate also fires (every line after a
  question line) were not marked forced and still got rate gradient. It also found minor 4 incomplete (dropped
  cards kept real tags, ents and lines), plus three wrong statements in the docs. (B) On ff1718222 it found
  finding 1 still incomplete for the cap (a gate-chosen start exactly on a `max_span` cap position), and the
  logged `gate_mean` was not the loss's G.
- **What was fixed in response.** e2a50ff1f: every wall start is forced; dropped cards carry -1.
  ff1718222: the docs. bd28adcd7: the start rule became `hard_starts`, with `forced` defined as "a start whatever
  the gate does at that token" and checked by brute force; the logged `gate_mean` is the loss's G. Each fix has a
  test that fails on the commit before it.
- **Final verdict:** re-review C of bd28adcd7 (10 findings): **no blocking finding.** Eight repeat deferred or
  waiting items; two new ones, not blocking (reflow cache provenance, which matters before Cell B; reflow
  efficiency). Tests: 86 passed, 1 skipped (pre-existing).
- **Correction to round 4.** Re-review B (b) said the design "will be sealed". It is not: section 9 of the run
  card does not list `01-design.md`. The §3.5 FLOP note mismatch therefore does not block the seal; it stays an
  open documentation item.
- **Consequence.** The Q20 review gate is satisfied. Run card SC-1 is sealed at f317420f9 (`05-seal.md`; the
  data addendum follows before Stage 1's first arm). Stage 0 is booked under Q22 (on-demand box only, hard stop
  $0.50). Its outcome is in `06-stage0-report.md`. (Superseded by Q129: the Stage 0 script waits for review; see below.)

## Erratum E1 to the design after the seal (coordinator ruling Q129, 2026-10-18)
§3.5 of `01-design.md` described a banded per-chunk surrogate, and §4 listed a `SpanConfig.chunk` field.
Neither exists in the code (re-review B (b), re-review C #6). Both passages are corrected in an erratum commit
that references the seal record (`05-seal.md`, seal commit f317420f9), with an Errata section at the end of the
design. The design is outside the seal's scope (run card §9), so no sealed hash changes. The per-token FLOP
estimate falls from about 33k to about 1.5k; the real cost is the about 150 MB gather, which Stage 0 measures.

## Stage 0 script: filed for the coordinator's review (Q129, 2026-10-18)
**Filed for review:** `scripts/span_stage0.py` at **b045f55c4**, sha256
**1066b2c822e2c25f644b244d010bf62cec6674d26bfb9f3a71759d3a0230d3f9**. Status DRAFT: it does not run until the
coordinator's review passes. The sealed code it imports (`span_cards.py`, `model.py`, `train.py`, `data.py`) is
unchanged since the seal commit f317420f9.

- **What it does** (in order; every result is a `STAGE0 {json}` line in the box log, which is the only channel
  back): (1) builds label-free v2 caches from the step-1 simulator (seed 0; 3,000 train and 256 validation
  visits; v2-fallback tokenizer; fitted name detector), checks that `"\n"` is id 23, and measures N at that size;
  (2) **pre-flight branch-point check** on fresh weights; (3) seconds per step for LINE and SPAN in gold, teacher
  and own (p_own 0.75) mode, on the same real batches (max_tokens 55,000, max_visits 48), 2 warm-up and 8 timed
  steps each, with peak GPU memory, the FLOP fit and one validation pass, then the Stage 1 projection (F =
  3.15e16, curriculum shares 5/25/70%, 3 parents plus Cell A: LINE and SPAN x 3 seeds x 95%, validation every
  1,000 steps); (4) the **branch-point check** again, with SPAN loaded from the LINE model as trained by the
  timing steps; (5) a 200-step `SpanTrainer` smoke from fresh weights through the whole curriculum, with
  finiteness checked on every logged loss and gate statistic.
- **The branch-point check (Q129 addition):** on the first 64 DEV visits, SPAN loaded from LINE (gate
  re-initialised) must give identical `answer()` (tokens, lengths, loops, first_top, fetched), write exactly the
  parent's cards (`valid == card_end`), **and have `card_economy.line_aligned == 1`** (also reported: merged,
  split_lines, newline precision and recall, the largest key difference). Any failure stops the run (run card
  §3: the pairing is broken), so nothing after it is paid for. Local check: it passes with `newline_id = 23` and
  fails with a wrong id (`line_aligned` 0.0097).
- **Local dry run** (CPU, tiny preset, 120/40 visits): every step completes; both checks pass; smoke finite.
- **Box plan after a pass:** see `06-stage0-report.md`. On-demand only; the remaining budget is $0.411 after
  attempt 1 ($0.089, unreviewed script, stopped on Q129, no readout, does not count); there is a watchdog
  destroy, and I stop and come back if a rerun cannot fit.

## Stage 0 script: built-in review (coordinator ruling after the Q129 read, 2026-10-18)
The coordinator read draft b045f55c4 (sha256 1066b2c8...) and found the Q129 conditions met. The last gate before
the rerun was the built-in `/code-review` on `scripts/span_stage0.py`, with blocking findings fixed and
regression-tested. The rerun releases when the review shows no blocking finding and the filed hash matches the
reviewed version. The review ran nine times; each round's blocking findings were fixed before the next. Several
blocking findings in later rounds were regressions introduced by my own earlier fixes, and the table says so.

| Round | Reviewed | Blocking (my classification) | Fixed in |
|---|---|---|---|
| 1 | b045f55c4 | the `strict=False` load was never checked; identical `answer()` could pass without one card fetched; key differences were only logged | 2dd23bd82 (load check; an always-ASK pass that must fetch; key and value tolerance in `passed`) |
| 2 | 2dd23bd82 | with HALT left natural, the always-ASK pass could fetch nothing after training; GPU float near-ties could stop a correct run | 848b5fc6b (HALT saturated in the eager pass; the strict check runs on CPU, where the two pool codes are bit-identical; GPU answer differences reported) |
| 3 | 848b5fc6b | `branch_gate` had no `reasons`, so a failed gate raised KeyError and never named the failed condition | 527dc1d0e (also: GPU flips bounded at 1% of questions; smoke finiteness enforced) |
| 4 | 527dc1d0e | the smoke could pass without reaching the own phase; GPU halt gaps escaped the flip bound; an absolute value tolerance could fail trained cards | 4b88a6ffa |
| 5 | 4b88a6ffa | (regressions of round 4) float32 halt compared in logit space would count one-ulp noise as flips; the smoke's stop test was too strict | f8fc53e30 |
| 6 | f8fc53e30 | (a regression of round 5) GPU halt differences went unchecked | 95cce469f (an ulp-aware relative halt rule) |
| 7 | 95cce469f | (regressions of round 6) an uncapped smoke could outlast the box watchdog and lose the branch readout; the saturated eager HALT was counted as flips | ab17419f5 (the final branch check now runs before the smoke) |
| 8 | ab17419f5 | none | 5b9033460 (all 10 non-blocking items fixed anyway) |
| **9** | **5b9033460** | **none** | not changed: the script is frozen at the reviewed hash |

**Verdict: NO BLOCKING FINDING** on 5b9033460 (my classification). The round-9 items, all deferred to the Stage 1
run script:
- the smoke's reserved-memory baseline keeps cached blocks from the branch check. That over-states the smoke's
  reserved memory; it could only trip the 14 GiB guard if those blocks alone exceeded it, and a no-gradient
  `answer()` pass caches less than the training steps did;
- the docstring and `--smoke-seconds` help are stale about the smoke cap (1.5x the estimate can exceed
  `--smoke-max-seconds`) and about usage errors, which now exit 2 before the log protocol starts;
- the combined argument-error message mis-names `--warm`;
- `branch_gate` moves the caller's models to the CPU and back in place, not through state-dict copies;
- the data timing's "inside one epoch" guard fails when an epoch has fewer than 3 batches (the defaults give about
  70);
- the epoch batch count copies `pdata.batches`' RNG protocol; the dev batches copy `pdata.batches(seed=None)`.

**Filed for the rerun:** `scripts/span_stage0.py` at **5b903346086906a05c225cb7f462afec905708c5**, sha256
**011336f99d6df2c086cf76c1690d4285219fe233471a3438046b99a3ef838d13** (the version reviewed in round 9). The
box fetches that exact commit and refuses to run if the script's hash differs. The sealed code it imports is
unchanged since the seal commit f317420f9. Tests: `tests/test_span_stage0.py`, 15 tests. Each blocking fix has
a test, and the round-1 tests were shown to fail under b045f55c4's rule.

What the script now checks at the branch point: SPAN is loaded from LINE with only the three gate weights
missing; there are cards, and `valid == card_end`; keys within 1e-4 and values within 1e-4 of their scale;
`answer()` is identical in a natural pass (exact fields, plus halt probability by an ulp-aware relative rule) and
in an always-ASK, never-HALT pass that fetches cards for every question; and `card_economy.line_aligned == 1`. All
of this is strict on CPU. On GPU the structure must also hold, and answer differences may touch at most 1% of
questions. The check runs as a pre-flight on fresh weights (a failure stops the run before any timing) and again
after the timing steps, before the smoke.

## Stage 1 script: built-in review (coordinator ruling after reading 5e3dfa7c, 2026-10-18)
The coordinator read the draft `scripts/span_stage1.py` at 6a5c8dffc (sha256 5e3dfa7c...) and passed it. The gate
before the release was the built-in `/code-review` on the script and its tests, with blocking findings fixed and
regression-tested. The review ran nine times; each round's blocking findings were fixed before the next. Round 1
ran on 6a5c8dffc, the version the coordinator read; the later rounds ran on the fixed versions.

| Round | Reviewed | Blocking (my classification) | Fixed in |
|---|---|---|---|
| 1 | 6a5c8dffc | the go rung was not checked against the box's own fitted rung; any pre-flight child fault counted as "does not fit" (a bug would shrink the batch); only the script was pinned, not the code it imports; the pre-flight saw first-epoch batches only | 12fcfe633 |
| 2 | 12fcfe633 | the code digest missed modules (core, policy, pointer); gold and teacher pre-flight steps were untracked; library OOMs stopped the box; `decode` crashed on a cut line; a go file without the rung was accepted | a6c76078f |
| 3 | a6c76078f | the arms reset the memory peak before their fp32 calibration; checkpoints were saved after evaluation; a larger go rung killed the box; slice tags were first built after the go wait | 80554323f |
| 4 | 80554323f | the parent reset its peak without emptying the cache; missing DEV slices did not stop the box | afe30bdf5 |
| 5 | afe30bdf5 | no slice masks left the box (G2 not computable from the log); the pre-flight's fp32 calibration on the heaviest batches could reject the sealed rung; a stale stop killed fresh boxes | 030afa48c |
| 6 | 030afa48c | (partly a regression of round 5) the run's calibration was not measured; an alignment check could cost the SPAN arm; a plain stop no longer stopped | 23bb21065 |
| 7 | 23bb21065 | an unaligned DEV readout could pass as good; a non-list `seeds` crashed; `to_cpu` dropped the state dict's `_metadata` | 8288396c4 |
| 8 | 8288396c4 | N was a float32 mean, which can differ in the last bit between boxes and stall the exact go gate | 707bdce90 |
| **9** | **707bdce90** | **none** | not changed: frozen at the reviewed hash |

**Verdict: NO BLOCKING FINDING** on 707bdce90 (my classification). The script is frozen there: sha256
**47577a35969c83f70f900e4d3845bf1ff8973644b664a67091d4ca92cdd6d127**. Round-9 items, deferred:
- `exact_n` computes N exactly (float64 from integer counts, 6 decimals). The sealed definition is
  `span_cards.tokens_per_line`, a float32 mean of the same quantity, which differs only around the 6th decimal;
  `span_cards.py` is sealed, so the addendum states the computation.
- A stop file carrying a different code digest is treated as stale. My go files carry the boxes' own digest, and
  a plain `{"go": false}` still stops every box.
- Log and gate robustness for situations this run does not produce: an undecodable local go file; two
  placeholder records for bad go files; sequence numbers unique per process only (each box runs one process per
  log); digests computed twice per process; a zero division in `exact_n` for a cache with no non-question lines.
- Test-only: the splice test depends on test order; there are no tests for an unparseable go file, a stale stop
  recognised by its code digest, or the size pin; the smoke test can leave grandchild processes after a timeout.

Tests at 707bdce90: 23 unit tests pass (`tests/test_span_stage1.py`), and the opt-in end-to-end smoke test
(`SPAN_STAGE1_SMOKE=1`, the whole box flow on tiny data in a subprocess) passes in 9 min. The Stage 1 release
condition is met: the boxes fetch commit 707bdce90 and refuse to run if the script's sha256 differs.
