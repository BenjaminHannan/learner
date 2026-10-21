# Review status (scripts are DRAFT until a round comes back clean; at most 2 rounds)

Round 1 (built-in code-review, effort high, on `research/shinka/trial2`): 10 findings, all addressed:
1. web_search tool without `max_uses` priced as zero searches -> now refused (`MoneyStop`).
2. caching asked for in the request but not priced -> TTL now read from the request; dearest TTL used.
3. check not atomic across processes -> `hold()` checks and reserves under one file lock; reads are locked; 8-thread race test.
4. batch hold released before charging; double charge on re-collect -> hold shrinks per charge, dropped last; charges keyed by batch/custom_id.
5. batch create timeout invisible -> hold written before create; unknown failure keeps it as spend.
6. mutation harness vacuous (missing file, any non-zero exit counted) -> copies prosecute.py, checks the unmutated copy passes, requires a real assertion failure.
7. 429 charged as unknown -> 429 and clean 4xx released; 408, 409, 5xx, timeouts charged at worst case.
8. `parse_case` brace counting, truncation unflagged -> JSON decoder scan; `parsed` and `truncated` flags returned.
9. plumbing script KeyError and different worst-case payload -> uses `.get`, shares `build_params` with the real call.
10. bar +0.05 kept on a point estimate; sd interval wide -> not a code bug; CARD2 now carries a pre-declared, raise-only tightening on seeds 105-109 before Stage 1.

Round 2 (same reviewer settings, after the fixes above): **NOT CLEAN, 9 findings. STATUS: PARKED.** No code was changed after round 2 (rule: at most 2 rounds). All scripts stay DRAFT.
1. `make_client` uses the SDK default `max_retries=2`; a retried attempt that was billed is invisible to the tally. One-line fix: `anthropic.Anthropic(max_retries=0)` and retry through the Guard. **Must be fixed before any real call.**
2. G0 gate: the probe memorises the 16 training names (C1 = 1.000) and may not measure "can a per-line writer find the person". Multi-head already gets person right on roughly 57% of novel lines, above the probe's 0.431. The FAIL stands under the pre-written mark, but the reviewer argues the probe is not an upper bound and that a role-structure probe ("the token that is not fill, relation or value") was not tried. Any new probe needs its own pass mark written first.
3. `bar_sizing.py` is hard-coded to seeds 100-104 and n=5 in the interval table, so the pre-declared 105-109 tightening cannot run unchanged.
4. A 529/5xx/408 that fails before generation is probably not billed; charging the full hold may drain Stage 0 ($0.28 hold, $0.50 cap) on a transient error. Deliberately conservative; a decision for the coordinator.
5. When `pause_turn` continuations run out, the card is reported `parsed=False` and would count as KNOWN. Needs a `paused_out` flag.
6. Mutation check covers only the 5 tagged lines; the round-1 guards (max_uses refusal, key idempotency, hold-before-send, unknown charge, cache TTL, release on clean 4xx) are not mutation-tested. The "all 5 caught" claim is exactly that.
7. `charge` rereads the whole ledger twice under the lock (slow for large batches).
8. `input_upper` (chars / 2) is a heuristic, not a guaranteed bound; the 15,000-token-per-search figure is an assumption. The hold is weaker than "guaranteed".
9. `batch_collect` polls with no deadline and drops the hold even if some custom_ids never came back.

After round 2 (UNREVIEWED edits, made so the plumbing test could run safely): `make_client` now uses `max_retries=0` (finding 1 of round 2); the prosecutor prompt now requires at least 3 web searches (the first plumbing call searched zero times). Findings 2-9 are still open.

## Extra review round (Ben's allowance, 2026-10-21; blocking findings only: wrong spend numbers, a way to exceed the cap, guard silently off)
Reviewed: the open round-2 findings 2-9 and the Stage 1 path (batch submit / collect, no tools, no caching).
- Finding 1 (hidden SDK retries): fixed earlier (`max_retries=0`), re-confirmed in `prosecute.make_client`. Stage 1 uses that client.
- **New (required by the ruling): Stage 1 cap $5.00 with a $4.50 stop.** `pricing.json` stage 1 = cap 5.00, stop_usd 4.50; `Guard.stage_stop` is used in the pre-send check (tagged GUARD-stage, so the mutation check covers it); a charge past the hard cap still raises MoneyStop. Two new tests. 39 tests pass; mutation check: all 5 guards caught.
- Not blocking for Stage 1, left as is: 2 (superseded by G0b), 3 (done differently: `bar_sizing_10.py`), 4 (a 5xx charges the full hold: over-counts, so safe; a transient error stops the run and needs a human look), 5 (`paused_out` only matters for prosecute, Stage 3), 6 (mutation coverage), 7 (speed), 9 (poll has no deadline: costs no money; a never-ending batch keeps its hold).
- Finding 8 (worst case is a heuristic): the margin between the $4.50 stop and the $5.00 cap is the backstop. Stage 1 uses no web search, so the 15,000-token-per-search figure does not apply. Estimated Stage 1 worst case: pass 1 about $3.07 held (released as results are charged), expected actual about $1-2.
- Result: **no blocking finding open for Stage 1.** Scripts for Stages 3+ stay PARKED/DRAFT. No further round.
