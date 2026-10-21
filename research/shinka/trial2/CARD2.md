# CARD2: trial 2 pass card (DRAFT, NOT SEALED)

Drafted 2026-10-21 by the Stage 0 build worker from `TRIAL2-PLAN-OPUS.md`. **Do not seal yet:**
G0 (below) FAILED its pre-written mark, so by this card's own rule the trial stops before any ideation
spend unless the coordinator and Ben rule otherwise. If they rule to go on, resolve the open items
(section 9) first, then seal by committing this file unchanged under a tag; nothing after sealing edits it.

Labels: shown = measured or read in the repo; suggested = inferred; untested = not checked.

## 1. The single change under test
Ideas are checked in words against the literature BEFORE any code is written (plan section 2).
The toy, frozen reader, isolated scorer, 20,000-number cap, evolution seeds 0/1/2 and KNOWN.md are
unchanged from trial 1. Everything runs on the CPU toy in `research/shinka/`; nothing under
`premonition/` is touched.

## 2. G0, the $0 headroom gate (sealed before any API spend)
Method and pass mark: `G0-PASSMARK.md` (committed before the probe was run, commit 086ab7259).
Pass iff: mean novel-line person-position accuracy >= 0.60, every probe seed >= 0.50, and controls
valid (familiar-held-out >= 0.90, shuffled-label <= 0.20). FAIL stops the trial.

**Result (shown, `results/trial2/g0.json`, probe seeds 100-102, controls valid): FAIL.**

| probe seed | novel-name lines | familiar held-out (C1) | shuffled labels (C2) | info: probe trained on novel names |
|---|---|---|---|---|
| 100 | 0.327 | 1.000 | 0.103 | 1.000 |
| 101 | 0.345 | 1.000 | 0.106 | 1.000 |
| 102 | 0.623 | 1.000 | 0.160 | 1.000 |
| mean | **0.431** (mark 0.60) | 1.000 | 0.123 | 1.000 |

Reading (suggested, not tested): the position is plainly findable *when the probe has seen the names*
(1.000), but a probe trained on 16 names mostly learned those names' vectors, and does not carry over
to 8 unseen names in 2 of 3 reader seeds. The pass mark was not changed after seeing this.
The probe has labels the real writer does not get, so a pass would only have been necessary, not
sufficient; a fail on a labelled probe is the stronger signal.

## 3. Bar sizing (shown, `results/trial2/bar_sizing.json`)
Rule: `G0-PASSMARK.md`. Data: novel-name accuracy, seeds 100-104 only, paired by seed.
- Largest paired-difference sd involving multi-head: 0.045 (two_pool - multihead). SE over 6 seeds = 0.0186, **2 x SE = 0.037 < 0.05. The +0.05 bar stands.** It is not lowered.
- Caveat: with only 5 pairs the 95% interval on that sd is 0.027 to 0.131; at the upper end 2 x SE would be 0.107. The estimate is rough.
- **Pre-declared tightening (sealed with this card, only ever raises the bar):** before Stage 1, run the baseline and multi-head on noise seeds 105-109 (CPU only, about 5 minutes, plan section 4). Recompute the paired sd over all 10 seeds with the same rule. The sealed bar is `max(0.05, 2 x SE rounded up to the next 0.005)`. It is never below +0.05.
- Pairing did not shrink the spread (paired sd 0.045 vs single-writer sd 0.045), so the "well under 0.02" hope in the plan (suggested) is not supported: the SE of the mean difference is about 0.019.

## 4. Pass card
Copied from plan section 6, with BEST-KNOWN = best of {multi-head pool, its Stage 4 and Stage 5 known-only
tunings} by evolution score, paired by seed on fresh seeds 2001-2006.
WINNER needs all of:
1. NOT KNOWN twice: NOT FOUND from the Stage 3 judge on the idea card AND from the Stage 6 judge on the finalist code, and the run-time hand check (section 7) agrees.
2. Mean (finalist - BEST-KNOWN) novel-name accuracy >= **+0.05**, positive on >= 5 of 6 seeds.
3. Mean familiar-name accuracy no more than 0.02 below BEST-KNOWN; within 20,000 numbers; passes every scorer check.
4. The finalist code still does its card's core operation (Opus fidelity check plus hand read).
Reported in four groups as in trial 1: both / better-but-known / novel-but-not-better / neither.
Proved wrong by: G3b fails; G4 fails; fresh seeds fail after G5; leak audit finds clear prior art for more than half of NOT FOUND families.

## 5. Gates (plan section 4, unchanged)
G1 >= 60 parseable cards stating fits_interface yes. G2 >= 15 distinct families pass the screen.
G3a planted known cards called KNOWN in >= 4 of 5. G3b >= 1 real family NOT FOUND.
G4 a novel family within 0.05 of BEST-KNOWN on evolution seeds. G5 a finalist beats BEST-KNOWN by >= 0.03 on evolution seeds.
Any failed gate ends the trial; nothing after it is spent.

## 6. Money stop (in code: `trial2/money.py`, `guarded.py`, `pricing.json`)
- **Every paid call goes through `GuardedClient`.** Cost is computed from each response's own usage (input, output, cache write by TTL, cache read, web-search count) at rates in `pricing.json`, checked 2026-10-21 against the claude-api reference. Unverified rates are flagged in that file (web search $10 per 1,000 searches; Haiku cache read).
- **Before sending**, check-and-reserve is one locked step: a call's worst case (all input uncached, x write multiplier if caching is asked for, all of `max_tokens` as output, every allowed search used and each adding 15,000 result tokens) must fit in what is left of its OWN stage and, separately, under the whole-trial hard stop. Else `MoneyStop`, nothing sent. The worst case is written to the ledger as a hold before the call, so parallel workers cannot both spend the last dollars; it is replaced by the real charge from the response's usage. A web-search tool without `max_uses` is refused; a request that asks for caching is priced at its dearest TTL.
- **Batches**: the summed worst case (no batch discount) is held before submit and shrinks only as each result is charged (once per custom_id); it is dropped after the last one. A failed collect leaves the hold in place.
- **A request that fails in an unknown way is charged at its worst case.** A clean rejection (400, 401, 402, 403, 404, 413, 422, 429) is not charged; 408, 409, 5xx and timeouts are.
- **A charge that ends over a cap raises `MoneyStop`**, and later calls are then refused.
- Stage caps: 0 = $0.50, 1 = $8, 2 = $4, 3 = $16, 4 = $6, 5 = $8, 6 = $3. **Whole-trial hard stop $45, warning $40**, far under Ben's $100 ceiling. No stage borrows from another. (The caps sum to $45.50, so in the unlikely case every stage runs to its cap the hard stop bites first, by $0.50.)
- Ledger: `results/TRIAL2_LEDGER.jsonl`, re-read under a file lock on every check, so separate processes agree.
- Tests: `test_money.py` (33 tests, fake client, no network). `mutation_check.py` switches off each of the 5 guard lines in a copy and requires a real assertion failure (not an import error), after first checking the unmutated copy passes: all 5 are caught.
- Plumbing test (one prosecutor call, Stage 0, cap $0.50): written, **NOT RUN** (no API key in the build session). Worst case for the call is $0.28.

## 7. Who does the hand check at run time
A **fresh Opus 5.5 reviewer session**, started for this purpose, that reads `KNOWN.md` and the card or finalist code
and gives its own KNOWN / NOT FOUND call **before** it sees any judge verdict or score. It is not the design
session (it wrote the plan and is not independent) and not the build worker. Disagreement with the judge
counts as KNOWN. The coordinator names the session when each stage that needs it starts.

## 8. KNOWN.md section C (Ben's ruling)
**Ben chose, on 2026-10-21, to KEEP section C strict** ("a direct combination of two known items is
known"). KNOWN.md section C is not changed. The final report must **list separately which idea cards
died to section C alone** (the prosecutor/judge called them known only because they are a combination of
two known items), so Ben can see what the strict rule cost.

## 9. Open items before sealing
- G0 FAILED: the coordinator and Ben decide whether the trial stops here (this card's rule) or whether a redesigned G0 is allowed. A new G0 would need its own pass mark written first and must not be tuned on this result.
- Plumbing test still to run once `ANTHROPIC_API_KEY` exists; its measured cost goes into section 6.
- Scripts for Stages 1, 2, 4, 5 (`ideate.py`, `screen.py`, `implement.py`, `refine.py`) are NOT built; only the money guard, the guarded client and `prosecute.py` are. They wait for the go/no-go on G0.
- Code review of the scripts: see `REVIEW-STATUS.md` (scripts stay DRAFT until it says clean).
