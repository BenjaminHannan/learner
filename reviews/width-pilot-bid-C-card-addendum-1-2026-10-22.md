# Bid C card, addendum 1 (2026-10-22): factual corrections found while writing the calibration drafts

The sealed card (`reviews/width-pilot-bid-C-card-2026-10-20.md`, commit e7841bb12, file sha256 ff242c50…) is **not edited**. This addendum lists what the drafts showed to be wrong or incomplete in it. **No bar, mark, seed or arm changes.** Items A1–A3 are corrections of fact. A4 changes a gate procedure and **needs the coordinator's acceptance**. A5 needs a ruling. The drafts are in [BenjaminHannan/learner#95](https://github.com/BenjaminHannan/learner/pull/95) (branch `claude/bidc-calibration-drafts`, base `claude/project-thread-2zeaoc`). All are DRAFT.

| # | Card said | Shown instead | Status in the drafts |
|---|---|---|---|
| A1 | "the ledger code needs no edit" (R1 default) | On the creative branch, `ledger.py` imports `MAX_ANS` **by value** (`from custom_io.data import EOS, MAX_ANS, …`, used at line 301), so GEN targets stay cut at 8 even with max_ans 35 | `ledger.GEN_MAX` and `data.set_max_ans` are now read at call time; a no-op at today's caps (68df7fa27) |
| A2 | (not mentioned) | `creative/sampler.py:19` (`N_NUM, N_REG = pp.N_NUM, 9`) and `creative/legal.py` re-run the ledger loop with **N_REG = 9 hard-coded**. Under 36 registers they would silently compute a different forward pass from `Ledger.run`, with no error | Both now read `ledger.N_REG` at call time (4b7da1db6); a test fails on the unfixed sampler. **Outside the card's §5 list, so it needs the coordinator to accept it into scope** |
| A3 | Caps overlay "sha 3da2dfbb" | Correct, but the source is `custom_io/g8a/caps.py` at ce03628be on `claude/project-thread-x2cm2v`, not on `claude/project-thread-f1to6a` (that branch's copy is sha d276fac0…, differing only in `compute_global`) | Ported as flat `custom_io/caps.py`, with `UPSTREAM_SHA256 = 3da2dfbb…` recorded. The verbatim upstream copy is committed first (d80fc2212) so the port's diff is reviewable |
| A4 | Load gate check (i): reproduce a C2b parent's "recorded per-row C2b-test score" on a fixed 64-row batch | That reads 64 rows of the **already-opened C2 test**, which R2 says is not re-read. Also, the committed per-row record has no floats, so only the right/wrong vector could be compared | **Proposed:** check (i) uses 64 rows of **C2 dev** (not test). It is recorded once on BensPC from the actual parent s200 with the unmodified code (the gate's `record` command), then reproduced through the caps-first path with `caps-old-defaults.json`, bit-identical on CPU (`torch.equal` on outputs). **Needs coordinator acceptance.** |
| A5 | (not mentioned) | `plain_tf` and `register_loop` also read the answer size by value | `train.py --caps` refuses any non-ledger model under non-default caps (`PORTED_MODELS = ('ledger',)`). Bid C uses only `ledger`, so this has no effect on Bid C |

**Also recorded (no ruling needed):**
- C2's MANIFEST records no seed. Redrawing C2 with `make_questions` at seed 0 reproduces all five splits row for row (tested), so the C2c collision check uses seed 0, and **93801 stays 93801** (no collision).
- The current representability search reaches all 52 affine instances, but C2's manifest marks three as not shown. `make_c2c` uses C2's own lists (49 usable affine) so the kind rules are identical, and records the difference.
- Dry run of the C2c generator at seed 4242 (not the real seed) in a temp dir: 512 rows, 0 prompt collisions, max answer 3 chars, max prompt 54. **The real C2c file is not generated** (`creative/data/c2c` does not exist).
- Fresh-built B2 params: 3,302,481 by default, 3,307,857 under `caps-bidc.json`. Only `reader.place` grows (16 → 37 rows), matching the card.
- Tests (CPU):
  - creative: 81 pass, 0 fail (52 existing plus 29 new). There is no baseline count from the unmodified branch, because that run did not finish.
  - custom_io: 36 pass, 13 fail. The same 13 fail on the unmodified branch, all for want of the skills data in this container.
- The custom_io port and `claude/project-thread-f1to6a`'s own `--caps` / `--max-ans` flags would need reconciling if the lineages merge.
