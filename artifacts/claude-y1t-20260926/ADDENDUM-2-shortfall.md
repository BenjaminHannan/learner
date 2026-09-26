# y1t addendum 2: what if the Mac job's GLM calls ran out of money? (Answering-from-memory thread, 2026-09-26 18:57 UTC, before y1t-glm-mac has pushed and before any chat is read)

**Why:** the Thread manager (18:56 UTC): the OpenRouter key ran out of funds at about 18:29-18:33 UTC, and lis320-full-mac
got 60 "402 Payment Required" failures after that. y1t-glm-mac (launched 17:28 UTC) uses the same key. lis-320's GLM
script retries a failed call 4 times, then writes the dialog with nothing parsed; lis-320's check keeps no turn of
such a dialog. So the items will come from fewer than 2400 dialogs.

**Rule, fixed now, before the counts are seen:**
- Counted from the Mac job's RESULTS-mac.md and files: dialogs with a parsed GLM reply, items in items_train.jsonl and
  items_dev.jsonl, and the number of 402 lines in glm_0..3.log.
- If items_train.jsonl has at least 1500 items and items_dev.jsonl at least 100: y1t runs on what exists, after the
  data gate (GATE-data.md). The drafts step's 3000-item cap and 1500-row repeat already handle a smaller set. The
  shortfall is disclosed in the results as a deviation from PLAN step 1's 2400 dialogs.
- Otherwise the missing dialogs are written through Ben's opencode route (GLM 5.3 Flash, Ben 18:47 UTC) once the
  Director's helper exists. An addendum naming the route and the dialog ids comes first, and the data gate runs on the
  combined set. The failed dialogs are the ones redone; no dialog that parsed is redone.
- Either way nothing else in PLAN.md changes.
