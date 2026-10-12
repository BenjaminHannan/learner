# B3 group 2 handoff (10-09, 2:45 PM ET)

Branch `claude/project-thread-qtxfp4` (PR #56, base `claude/project-thread-f1to6a`). Specs and a snapshot of the big-run plan are copied into
`design/architecture-2026-10-09/`, because the cloud shared folder (`/mnt/project-files`) can't be read from a local machine. Read them in this order:
- `B3-GROUP2-BUILD-2026-10-09.md`: the spec, including Addenda A to D.
- `g2-integration-brief.md`: the integration job, items 1 to 14 plus the helpers' facts.
- `big-run-PLAN-snapshot-2026-10-09.md`, section 5, "G2 step 2b": the sealed marks.

## Done and tested
| What | Commit | Tests (CPU, stub Gemma) |
|---|---|---|
| B3 group 1 (any-round calls, Gemma + calculator, 2,000 letters, H1R learned stop) | e070556ce5 | test_b3, test_b3_run, test_tok_think ALL OK; test_g8a 17/17 |
| Fix: caps.apply had made H1's 32-round cap 109 | 425b036e8f | test_g8a test_caps_leave_the_round_cap |
| Fix: H1 'settled' stop loss only in batches that ran all 32 rounds (`stop_w`); new cap counter `steps_unparsed` | 8fce7247a8 | test_b3 ALL OK incl. check P and test_settled_needs_the_whole_turn; test_b3_run ALL OK |
| L1 traces as written (`models/progtext.py`: calls plus `note <step>` entries) and ST1 (`st1.py`) | cb19994b97, f6695cbd4a | test_progtext, test_st1 ALL OK |
| O1 ByteWriter (`models/writer.py`; `refine=k` trains on its own copy feedback, spec Addendum B) | f29cde4457 | test_writer ALL OK (645 s); toy exact 100 / 99.0 / 99.8% |
| V1 bytes, P1 no_place, N1 no_slots (default off = bit-identical to e070556ce5) | 5aab74a520 | test_g2_input, test_b3 (check P), test_b3_run, test_tok_think ALL OK |

The B3 group 1 PC run installs **8fce7247a8** (pinned in PLAN). The commits after it are group 2 and do not change group 1.

## In progress, untested: the integration (`models/b3g2.py`, class `B3G2(B3)`)
The commit `WIP B3 group 2 integration` (the one before this file) holds 634 lines of `b3g2.py`, `tests/test_b3g2.py`, `tests/test_b3g2_run.py`,
`g8a/caps_b3g2.json` (caps_b3 plus `le` 95), and edits to `analyze_8a.py`, `capcount.py`, `b3_cost.py`, `caps.py`, `configs.py`, `job.py`,
`models/__init__.py` and `tool.py`. **None of it has been run.** Start with `git show --stat` on that commit, read the diff, then finish it against
the brief.

## Left to do, in order
1. Finish B3G2 and make these pass: test_b3g2, test_b3g2_run, test_b3, test_b3_run, test_g8a (exit 0, no ALL OK line), test_writer,
   test_progtext, test_st1, test_g2_input. Run with `OMP_NUM_THREADS=1`; 4 threads were 10 to 100x slower on small models.
   test_tool_h1, test_tool and test_tool_span need the sk200k data.
2. Pre-PC checks (PLAN "G2 step 2b", items i to iv):
   - (i) The 3M trained count must be inside 3,941,991 to 4,102,889. If it isn't, trim the writer's MLP first, then the thinker's feed-forward ratio.
   - (ii) Bytes caps are done (Addendum C): both pool builders drop non-ASCII rows, so caps_b3 holds.
   - (iii) Record `b3_cost`.
   - (iv) The progtext pool scan is done (Addendum D): `progtext_pool_scan.py`, with 0 rows without a trace and notes up to 95 bytes.
3. **All-steps plain control, "PTS" / g2c3s (Ben chose "All steps", 2:28 PM ET 10-09). Not started.**
   - Add a cfg switch `all_steps` (default off = bit-identical) to `plain_tf_steps.PlainTFSteps` / `plain_lm.PlainStepsG`.
   - When on, the target is `'; '.join(steps) + ' # ' + answer` for every row with steps. There is no family list on that path, and it never falls back to the answer alone. Today only 11 families (`plain_tf_steps.py:14-15`) get steps.
   - `caps.measure/compute` get `all_steps`. Write `caps_b3s.json` with plain_target re-measured on own72, and make job.py's caps recompute use it for this arm.
   - Add arm `PTS` in configs/job, the same as g2c3 (G-PT 3M at caps_b3 on the B3 pool) except this switch.
   - Check: off-path parity; scoring after the last '#' (count steps that contain '#'); the PLAIN_BAND size.
   - It is one more 3M PC run before group 2's readout, after G1, and needs Ben's go.
4. Re-run the hand-code inventory on built group 2 (PLAN mark B3G2-7, target 0).
5. Update the PR #56 description, then hand the PC jobs (g2c3s, then group 2 at 3M seed 400) to Ben's queue.

## Facts to keep
- Real pool (own72 skills, 1,583,731 rows): group 1's `steps_unparsed` will show about 59% of skill rows (932,806). That is reported, not gated (Ben: "Run, disclosed"). Group 2 must reach 0, and does on the scan.
- Group 2 uses LE 95 / WCAP 96. Group 1 keeps LE 68.
- The scratchpad worktrees g2-writer, g2-input and g2-traces were merged here, and their branches exist only locally in the old cloud container. Everything is in this branch's history.
