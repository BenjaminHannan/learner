# lis-319 blind second labeller brief

Label chat turns into JSON frames, independently. Someone else labelled them; never look at their labels.
Read first (in /home/user/learner): design/v3/60-listener/frame-spec.md, design/v3/60-listener/frame-spec-notes-301.md,
design/v3/60-listener/relation-names.txt (only allowed rel names, plus "other").
ONE convention differs from the notes: read each dialog IN ORDER. A pronoun or reference ("she", "the kid", "her husband",
"my sister") is resolved to the named person when it is clear from this turn, the previous reply, OR the earlier turns of
the same dialog; owners resolved from history use the name as typed earlier. Only a still-ambiguous one (two or more
candidates) keeps the pronoun with mode UNCLEAR. Values are copied exactly as typed in this turn (short answers: this turn).
Other reminders: owner "me" for I/me/my, "we" for we/us/our; one fact per value; corrections: new value mode CORRECT with
"old" when named; "so X is Y" without "?" is CHECK; reported claims REPORTED; plans PLAN; pretend SUPPOSE; negations
NEGATED; questions act ASK with "ask" (owner resolved from history too); chat that teaches nothing: act CHAT, facts [].
Input: {INPUT} (rows with id, dialog, t, prev_reply, turn, in dialog order). Do not open anything under the lis319data
folder (the other key). Never read any "panel" folder or /mnt/project-files/escrow-331.
Output: {OUTPUT}, one line per input row: {"id": ..., "frame": {...}}. Write in chunks. Check with Python: same ids,
parses, rel names valid. Never call WebFetch or any mcp__hearthbot__ tool. Do not run git. Final reply: counts only.
