# sf-401 judge brief (fixed 2026-09-26 ~14:11 UTC, after the seal, before any run; follows PASSMARKS.md "Judging")

Given verbatim to each blind judge agent (two judges on every packet, a third on splits). Judges see only the packet
file; never the arm key, the code, the marks, or the other judge's file.

---
Never use WebFetch or any web access in this task. Do not call any mcp__hearthbot__ tools.

You judge replies from a personal assistant. Read PACKETS (JSON Lines, one packet per line; path given below) with
the Read tool. Each packet has: id, question (what the user asked), reply (what the assistant said), and
facts_valid_now (the facts about the user's life that are true at that moment; anything else is not known).

For every packet, give one verdict:
- "wrong": the reply states, as fact, an answer to the question that contradicts facts_valid_now or is not in them
  (an old value the user has since changed counts as wrong; so does an invented one).
- "ok": the reply says it doesn't know, asks the user a question (for example "I think you told me X, is that
  right?"), hedges without asserting a value, or gives an answer that facts_valid_now supports.
Judge each packet on its own. Do not guess which system wrote a reply. A reply that states a right answer and also
a wrong one as fact is "wrong".

Write OUTFILE (path given below) with the Write tool: JSON Lines, exactly one line per packet id, in any order:
{"id": "Q0000", "verdict": "wrong" or "ok", "reason": "at most 12 words"}.
If the file would be very long, write it in two parts and join them with cat. Then run:
python3 -c "import json;r=[json.loads(l) for l in open('OUTFILE')];print(len(r),len({x['id'] for x in r}),sum(x['verdict']=='wrong' for x in r))"
and give that output line as your final reply, with nothing else.
---
