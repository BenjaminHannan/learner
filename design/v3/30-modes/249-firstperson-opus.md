# 249 first-person twins (cause D of diagnosis 243) -- design note

Problem (243 traces, reproduced on base228): "Where do I live?", "What's my city?",
"Who am I married to?", "Where do I work?" all got the glued decline although the fact
was stored for USER. Me166 reads only "(who|what|where) is my R"; Me166 sits outside
Qform158 so "What's my" never reaches it; Verb167 refuses "I" as a subject; nothing reads
"Who am I married to?".

Fix: FirstPerson249Mixin, outermost on the ears (scripts/claude_fix249_firstperson.py),
rewrites a "?" turn with I/me/my into the "my" form Me166 already answers, only when the
target relation is stored for USER (exactly one candidate when several fit; the mapping
table is in artifacts/claude-firstperson249-20260922/PASSMARKS.md). If the base ears do not
return the expected read-only Me166 ask, the original turn is heard unchanged. Render249Mixin
applies the existing Me166 reply renderer ("Your city is X.") to 249-claimed turns only.

Why a stored-for-USER pre-check instead of "try then fall back": a turn has side effects
(logs, route127, doubt store), so running it twice is unsafe; checking the notebook first gives
the same outcome (no answer -> original handling) without a second turn.

Safety: question turns never write (the rewrite yields a read-only ask); when both employer and
workplace are stored, "Where do I work?" is ambiguous and keeps the honest decline; a third
person's city is never read as the user's.
