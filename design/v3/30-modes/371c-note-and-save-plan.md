# 371c: next steps for notes and saves after the 09-26 overnight FAILs (plan, 2026-09-26 ~12:00 UTC)

Source: Ben's pasted outside review (11:50 UTC). Every number it gave was re-checked here:
- Save check (claude_lis300_compiler.check_fact) sees only the current turn + last reply. On readpanel319c the reader found
  37 history-dependent facts; all 37 were blocked (35 owner_not_span, 2 rel_not_in_table). Confirmed (count-only script).
- Whole claim at 0.999: 71 right, 1 wrong turn (vs 134/5 at 0.995, 180/7 at 0.98). Confirmed. Diagnostic only.
- Note checker AUC 0.813 dev / 0.831 test; contract defects above. Confirmed (rd-371b VERIFY recount).
- Writer data (scripts/claude_rd378_data.py) drops every turn with any non-ok note or a missed item. Confirmed.

## Order (one change per experiment, marks fixed first, fresh sealed confirmation sets)
1. CONTRACTS (code only, no GPU): one judge brief with four separate judgments per note (supported, right person,
   time, cites) that uses exactly what the checker sees; checker prompt v2 shows `when` and marks cited turns; hypothetical-
   as-fact counts as unsupported; one population definition for dev and test; bar rule v2 returns NO USABLE CUTOFF unless
   the dev-picked bar keeps >= 80% of ok AND the one-sided 95% upper bound on unsupported-among-accepted is <= 5%
   (needs >= 59 accepted with 0 errors); dialogs, not notes, are the resampling unit for intervals.
2. SAVE CHECK SEES THE READER'S WINDOW (lis-319d): owner may come from an earlier USER turn in the reader's window only
   when that turn names exactly one person the claim could be about; otherwise the fact is asked back, never saved
   silently. Dev preview of the naive version: +28 right, +3 wrong (all role confusion), so the naive version is not the
   candidate. Needs a fresh panel with back-references and two-candidate role-confusion rows. GPU: one read (~15 min).
3. VERIFIER ON MEANING-CHANGING NEAR-MISSES: same names and values, changed relation / time (used to) / negation / plan /
   reported speech / person, taken from the reader's dev mistakes plus code-made swaps; every source has supported and
   unsupported rows. Judged by the whole-claim scorer under the original absolute wrong-turn limit.
4. WRITER ON CORRECTED OWN DRAFTS: the biggest lever (half of notes are untrue; an 80%-keep/5%-error filter would need
   to reject ~96% of untrue notes at AUC 0.81). Open question for Ben: corrected targets written by Claude agents break the
   "Claude-written text is not training text" rule; options are minimal edits limited to copied source spans, the GLM
   teacher writing corrections, or deletion-only corrections (drop the unsupported clause).

Answers keep coming only from original messages; notes only point to them (Benchmarks' store: heard-only by default).
