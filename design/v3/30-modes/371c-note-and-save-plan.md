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
2. SAVE CHECK SEES THE READER'S WINDOW (lis-319d). DEV RESULT 12:15 UTC (133 lis-319 dev history rows, report only):
   | rule for an owner found only in earlier user turns | right saves at 0.995 / 0.98 | wrong rows |
   |---|---|---|
   | today (blocked; they go to ask-back) | 55 / 65 | 0 / 0 |
   | naive: accept any earlier-turn name | 71 / 93 | 1 / 3 |
   | only if no other person name in the window | 55 / 65 | 0 / 0 |
   | only if the last named turn names just the owner | 56 / 66 | 0 / 0 |
   Real chats name several people, so no simple code rule links the person to the claim: the safe rules gain ~0, the
   naive one adds role-confusion saves. So step 2 cannot be done by code alone; person attribution for history facts
   moves into step 3's verifier (person-swap near-misses over the reader's window). Original step 2 text kept below.
   (was:) owner may come from an earlier USER turn in the reader's window only
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

## Change of order, 12:10 UTC (Ben's pasted report, checked against the data)
The whole-claim wrong saves are systematic label problems, not random slips: former jobs saved as current (the modes
cannot say "used to"; training labels teach it), "works in" vs "lives in" when a job and a place share a sentence, and
a missing label (orthodontist). A verifier trained on the same labels would copy them, so step 3 is PAUSED. Next save
change = lis-319f (a FORMER mode: code relabel + code-made rows; marks artifacts/claude-lis319f-20260926/PASSMARKS.md,
fresh sealed panel readpanel371c with ~45 former rows). After it: one rule for job + place, then re-decide the bar.
Step 4 (note writer): Ben chose "Cut only" (12:02 UTC): corrections may only delete the untrue part of the writer's
own note. Its own true-vs-untrue note pairs (497 in the rd-371b judged drafts) add no new words either.

## Step 4 order, 12:55 UTC: usefulness first, then the cut-only writer
rd-378's finding test searched inside one 12-16 turn dialog, so top 10 was most of the dialog (heard-only found 150/150)
and it could not show whether notes help. Before spending on making notes truer, measure whether they help search at all:
- 4a (no training): the rd-378 writer writes notes over the LoCoMo PRACTICE conversations (whole multi-session chats,
  one pair of speakers each); evidence recall_any@k across the whole conversation, heard only vs heard + notes (notes
  resolve to their cited turns), with bm-393's retrievers (scripts/claude_bm393_evrecall.py). Development use of LoCoMo
  only, never trained on. Marks to be fixed before the run: heard+notes >= heard + 5 points recall_any@10 overall, no
  category more than 3 points below; proved wrong if <= +1. If notes don't help, notes are dropped and 4b is skipped.
- 4b (only if 4a passes): Ben's "Cut only" (12:02): continue training the writer on its own drafts with every note the
  blind judges marked not ok deleted (rd-371b judged drafts: 2,526 drafts of 1,263 turns; 868 ok / 993 unsupported
  notes); more drafts judged the same way if needed. Marks (from the 12:00 report): untrue share on a fresh sealed note
  panel drops >= 15 points vs rd-378; missed memorable items rise <= 10%; proved wrong if the drop is < 5 points.

## 13:55 UTC: problem split and corrections (reading thread)
Ben 13:30: one thread per problem. Notes (step 3 checker, step 4a rd-378L, 4b cut-only writer) moved to the
"Trustworthy notes" thread. This thread keeps saves, now including corrections heard but not saved (0.2c ME1).
Next save changes, one at a time: lis-319f FORMER (running on a rental), lis-319k corrections at 0.95
(artifacts/claude-lis319k-20260926/PASSMARKS.md; bar change only, one read of a fresh blind correction panel),
then the job + place rule, then 0.98 vs 0.995 for ASSERT.
