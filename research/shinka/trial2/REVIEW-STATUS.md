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

Round 2: see the line below.
