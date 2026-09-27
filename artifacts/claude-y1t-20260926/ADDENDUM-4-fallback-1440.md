# y1t addendum 4: a fallback if the opencode route stays down (Answering-from-memory thread, DRAFT 2026-09-27 03:12 UTC, for the Thread manager's review before sealing; no gate sample has been drawn and no gate judge has run)

**When it applies (and only then):** the Director is ready to start benspc-y1t on BensPC and Ben's opencode route is
still down (it hit its usage limit at about 00:57 UTC, per the Director at 03:06 UTC). In every other case the resume
job runs and ADDENDUM-3 applies unchanged. Today benspc-y1t is held behind 151-fixsleep-dl9pc-b, 155-claude-sleep-358spc,
175-rv393-pencil-pc, 260-claude-sleep-358t3pc and k1f-benspc2, with 170-rv390-358i2-pc running (handoff/queue names,
checked 03:09 UTC).

**Disclosed: this fallback was chosen after a counts-only preview.** The preview merged the 645 first-run rows with the
1,440 top-up rows and ran lis-320's check, y1t's items step and the G1b filter, counts only (no item text read, no gate
sample drawn). It gave 1,514 train and 260 dev items from the items step, and 1,502 and 257 after G1b. ADDENDUM-2's bar
is 1,500 train items from the items step (ADDENDUM-2-shortfall.md:11).

**Which rows the items come from:** 2,005 parsed dialogs: 645 from the first run and 1,360 of the top-up's 1,440 rows.
The top-up's 80 unparsed rows give no items. The 315 dialogs the resume would have worded are not in the set.

**What the fallback does:** the gate (GATE-data.md with GATE-ADDENDUM-1: G1b filter, G2/G3 on seed 4034, G4 on seed
4036, sealed marks) runs on that 1,440-top-up merge, built exactly as ADDENDUM-3 rule 4 says, into glm2/. The missing
315 dialogs are a disclosed deviation from ADDENDUM-3 rule 3. They are not worded later for y1t.

**Branches, fixed now (already sealed, restated here, not chosen after any gate result):**
- G2 or G3 fails: y1t is not run on these items (GATE-data.md:20, GATE-ADDENDUM-1:48).
- G4 fails: every name-only twin is dropped and y1t trains on clean twins only; G4 does not stop y1t
  (GATE-ADDENDUM-1:46-47). The preview puts the train set at about 1,370 then (1,502 minus 132 name-only twins).
  That is under 1,500, and y1t goes on with what exists: the drafts step repeats rows so about 1,500 pass through
  training (claude_y1t_data.py:53, 177; ADDENDUM-3 rule 6). No further top-up, no third route, no change to any mark.
- All pass: y1t runs on glm2's items, as ADDENDUM-3 rule 5 says.
