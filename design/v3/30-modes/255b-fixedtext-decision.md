# 255b: the one follow-up to 255 (fixed-reply text). Director's note, 2026-09-23 02:45 UTC

255 is a registered FAIL and stays FAIL. This note is the diagnosis and the one change for 255b.

## Diagnosis (checked against the code, not from memory)

1. **M4, 8 untrue replies.** 255's T02 rewrite turns 138m's misread-question reply into
   "I don't know that. I may have misread your question, so could you say it another way?".
   T02 fires when the loop fails to *read* the question, not when the notebook lacks the fact. So on
   A06, B04, B05, B20, D02, D03, D04 and D08 the first sentence is false: the fact is stored, or it is the
   assistant's own name, or the turn was a teach.
2. **M1, "zero turns".** `claude_fix255_text.num()` returns the word "zero" for 0. T43 has no zero branch,
   so "We have had 0 turns." became "We have had zero turns." (row r141; both graders flagged it).
   The same hole exists in T52, T53 and T46, and in T40, T41 and T47 if a 0 ever reaches them.
3. **The wording planned on the board would break the frozen scorers.** I ran 255's anchor check
   (`claude_fix255_test.fam`) on "I couldn't find an answer to that. I may have misread your question, so
   could you ask it another way?". 138m's old text is (224a decline yes, bench121 abstain yes, redteam143
   abstain yes, session152 clarify yes, "i have no record" no). The planned text gives bench121 **no** and
   redteam143 **no**, so the frozen suites would score those declines as answers. The planned text is dropped.

## The one change (text only; same place as 255: one outermost reply wrapper on 138m)

255b = 255's rewriter with two corrections, as one new module `scripts/claude_fix255b_text.py` that imports
`claude_fix255_text` unchanged:

a. **T02 (misread question)** becomes exactly: `I didn't understand that. Could you say it another way?`
   It is true on every turn T02 fires on (the loop did not understand the turn), whether the turn was a
   question or a teach. Anchor check: (yes, yes, yes, yes, no), identical to 138m's text.
b. **No count is ever said as "zero".** A count of 0 uses these exact texts:
   - T43: `We haven't had any turns yet.`
   - T52: `I have no record of yesterday. My log starts with our first turn here, and it is still empty.`
   - T53: `Nobody besides you has spoken to me.`
   - T46: `No. I never asked for clarification.`
   - T40: `No. I don't hold any web rows.`
   - T41: `No. I haven't slept yet.`
   - T47: `No. I never asked for clarification instead of saving.`
   Every other template and every other count renders exactly as 255 does.

Why this counts as one change: both parts fix the two registered failures of the same single piece (the
fixed-text wrapper), and nothing else in 255's 60 templates moves. Director's decision, logged.

T04 (GLUE) keeps 255's text. Its claim ("I have no record of it") is 138m's own verdict, not new in 255.
M4 reports every T04 line so this can be checked.

## Pass marks (fixed now, before the build)

255's M1–M7 with 255's bars, re-run on 255b vs 138m, plus these changes:
- **M1** fresh render file (new seed 2550923), same generator rules. Graders: the director and one Muse
  grader, blind to each other. Bar: 100% of changed-template renders grammatical for both. Plus a mechanical
  sweep in the unit tests: every count template rendered for n = 0..12 contains no "zero", no "1 <plural>"
  and no "one <plural>".
- **M4** mechanical labels as in 255. The director's ruling is fixed now: the new T02 text is a same-meaning
  rewrite of 138m's T02 and is true on all 8 previously flagged probes. Bar: 0 "worse (unexplained)".
- **M3** (239 panel, TEST-ONLY) run once; changes file vs 138m's registered transcripts; bars as in 255.
- **Extra report (no bar):** 255b vs 255 on the M4 probes and M6 dialogs. The only differences must be T02
  lines and zero-count lines.

What would prove this wrong: any frozen-suite verdict change (M2 gate), any changed reply that is not an
exact 255b template, a grader flagging a changed render, or the new T02 text judged untrue on any probe.

## Registration: one piece, two parts, scored separately (added 02:47 UTC, before any build)

Part A = the T02 wording. Part B = the zero-count texts. They are kept in one experiment because they are the
two registered failures of the same wrapper, they touch disjoint templates (T02 vs T40/T41/T43/T46/T47/T52/T53),
and splitting them would force a third merge experiment before either could ship. To keep "one change" honest:
- every prediction in PASSMARKS is numbered and labelled Part A or Part B (P255b.n-A / P255b.n-B);
- every predicted move and every result is reported per part (M1 renders, M2/M4/M6 moves, M3 changed turns);
- a move that belongs to neither part is a failure of the piece;
- PASSMARKS says this choice and the reason above in one paragraph.
Provenance: the 8 untrue replies come from the 138m verifier probes (artifacts/claude-verify-20260922/138m/probes.json),
which are dev/verification data, not a TEST-ONLY panel. "zero turns" comes from 255's generated M1 render file.
The 239 panel was run for 255 but never judged or tuned on; 255b's change was derived without it.
