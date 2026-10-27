# 236 -- questions that use only a first name (Opus)

Problem: after "Ysolde Marr's employer is Kestrel Works.", loop221 answers "Who is Ysolde's
employer?" with "I don't know anyone called Ysolde." because a question must use the full stored
name. This caused 6 of 7 answerable misses on exp 231's blind panel and one on 221c's.

One change (scripts/claude_loop236_agent.py, FirstName236Mixin outermost on Loop221Ears):
on a question turn (ends in "?"), a capitalised single word T that is not followed by another
capitalised word, not part of a full stored name already written, and not itself a stored
name or value is looked up against the first words of stored subject names (2+ words):
- one match: hear the question with the full name in place of T (reply names the full name);
- two or more: "Which T do you mean: A or B?" (up to 3, alphabetical), no value, no write;
- none: unchanged.
Writes are never touched; surnames alone are out of scope. "Ysolde Kane" never resolves to
Ysolde Marr (the next capitalised word blocks it). 228 guard installed.

Marks, bars and predictions: artifacts/claude-firstname236-20260922/PASSMARKS.md.
Results: artifacts/claude-firstname236-20260922/RESULTS.md.
