# lis-318 blind second labeller brief

You label chat turns into JSON "frames" for a fact-reader's training data. Someone else labelled the same turns; you must NOT look at their labels. Label independently from the rules.

Read first (in /home/user/learner): design/v3/60-listener/frame-spec.md (the format: follow it exactly), design/v3/60-listener/frame-spec-notes-301.md (conventions: follow them exactly), design/v3/60-listener/relation-names.txt (the only allowed rel names, plus "other").
Key reminders: owner "me" for I/me/my, "we" for we/us/our; names and values copied exactly as typed (case and typos kept); a value that is not typed word for word in the turn is not a fact (for a short answer to the assistant's question, the value is in the turn and the owner/relation may come from the previous reply); one fact per value; corrections: the new value has mode CORRECT with "old" when the old value is named, and the old value is not listed as an ASSERT fact; "so X is Y" without "?" is a CHECK; reported claims are REPORTED; plans/hopes PLAN; pretend/what-if SUPPOSE; negations NEGATED; questions: act ASK with the "ask" object; a pronoun resolved only when this turn or the previous reply makes it clear (the reader cannot see earlier user turns), else keep it with mode UNCLEAR; casual chat that teaches nothing: act CHAT, facts [].

Input: {INPUT} (one JSON per line: id, prev_reply, turn). Do NOT open any file under the lis318data folder (it holds the other labeller's key). Never read any "panel" folder or /mnt/project-files/escrow-331.
Output: {OUTPUT}, one JSON per line: {"id": ..., "frame": {"act": ..., "facts": [...], "ask": ...}}, for every input row, in order. Write in chunks of about 50 rows. Then check with Python: same ids as the input, every line parses, every rel is in relation-names.txt or "other".
Never call WebFetch or any mcp__hearthbot__ tool. Do not run git. Final reply: row count and check results only.
