# Swarm: review fix round 2, report (2026-10-18)

Branch `claude/swarm-thinkers`. Coordinator ruling, round 2 (SWARM): GO on the second review's items 1-5. **Code stays DRAFT.
Nothing books, seals or runs a paid step.**

## 1. Fixes (commit d58a18ada)

| item | fix | regression test (each fails on 9a3579adc, passes now) |
|---|---|---|
| 1 card lost from the board within a round | `Board.post` walks the M*K columns in desk order exactly as a one-by-one FIFO: a card is new unless it is on the board at that moment, so a card evicted earlier in the round is posted again. `slot_card` is the only state; `posted` is derived from it | `test_card_evicted_within_a_round_and_refetched_is_on_the_board` (the review's counterexample: [A,B] + X,Y,A → [A,Y]); `test_post_matches_a_one_by_one_fifo_including_row_contents` |
| 2 false "no host syncs" | only whole-tensor `where` updates: no boolean-mask indexing, host `.any()` or `F.one_hot` | `NoSyncTest` records every aten op and every bool-index call in `post`; it fails on the old code |
| 3 stale docs | IMPLEMENTATION-SPEC §6, §7, §11 and SWARM-DESIGN updated to the new posting and latest-gold preload | n/a |
| 4 row contents untested | the equivalence test checks every board row's embedding (value + age + card type + author desk), exactly | as item 1 |
| 5 silent out-of-range entity id | `entity_table` raises `ValueError` on an id ≥ n_ent | `test_out_of_range_entity_id_raises` |

Dry-run T is 120 s in the box script (procedural, per the ruling). The manifest is regenerated.

## 2. Tests

`python -m unittest tests.test_premonition_swarm tests.test_premonition_swarm_screen tests.test_premonition_model
tests.test_premonition_train`: **103 run, OK (1 pre-existing skip)**. Discover over `test_premonition_*.py`: 263 run.
The same 4 import-time errors (interface_probes, memnn, token_evidence, token_memory) occur on unmodified 73b8e0224.

## 3. Built-in review of the new diff (e64b0a5cf..d58a18ada): 7 findings. **NEW BLOCKING ISSUES, so I stopped and did not patch.**

Blocking (both confirmed in code):
1. **The item-5 range check adds a host sync to every forward** (`int(ents.max())` in `entity_table`, `swarm.py:112`).
   The comment "as one_hot did" is wrong on CUDA: `F.one_hot` with `num_classes` skips its min/max check there. This
   regression is mine, and it lands in the C0 timing. Proposed fix: `torch._assert_async(ents.max() < n_ent)` plus a
   test that the check raises.
2. **BOX-SPEC.md still says the dry run uses T = 30** (lines 51, 113), while the kit runs 120. The pinned spec and the
   kit disagree. Proposed fix: update both lines and state the reason (one CPU step is about 2% of 30 s, the size of
   M5's whole ±2% band, so a 30 s dry run trips M5 on a single step).

Non-blocking:

3. `post` rewrites the full [Q, C, d] board once per column (efficiency, S1 only; it inflates S1's C0 time, and S1 is
   information-only). Proposed fix: run the loop on the [Q, C] ids only, then write the board once with one gather.
4. `NoSyncTest` covers only `post` on CPU, through a private API.
5. Its bool check also flags bool *values* of `index_put`, which would be a false positive.
6. `posted` is now read only by tests.
7. The box script's T = 120 comment states its reason badly.

## 4. Dry run at d58a18ada (T = 120 s), `artifacts/claude-swarm-screen-20261018/dryrun-d58a18a/`

Exit 0 after 1,760 s; 33 steps rc 0; HEAD == PIN; 18-file manifest OK; train seconds within +0.25% of T. **Every mark
of both cards was computed, with no VOID**, and the `--min-items 1` passes reached FAIL (M3) and KILL-COMM. These are
tiny-model artifacts with no meaning for the screen. The 9a3579a VOID is closed as ruled: it was a timing-guard trip,
not a kit failure.

## 5. Status against the Q28 gates

Review passed: **no** (two new blocking issues above, awaiting a ruling). Card sealed: no. Dry run at the sealed commit:
not yet, since the sealed commit will follow the next fix round. C0 stop-and-ask rule: in force (box script exits 3).
**C0 does not book.**
