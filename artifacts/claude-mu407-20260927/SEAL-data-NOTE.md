# mu-407 SEAL-data note

"Making things up about you" thread. Written 2026-09-27 06:46 UTC (date -u). This comes before the smoke run and
before any talker call. No talker reply exists yet. Nothing in the marks changes.

## Where the data came from
- Mac job madeup-mu407-luna-mac. Its results were pushed to builder-outbox at 06:41:54 UTC (411d55e94) and copied
  byte for byte to prep/ here.
- The job worked from a `git archive` of main at 6c90c5e71. SEAL-prep (7 files) and SEAL-luna (3 files) both checked OK
  there.
- Writer: Luna (gpt-6-luna), through scripts/claude_luna_codex.py (sha256 342a0fb7…), with 1 call at a time.
  Claude wrote no chat or frame text.

## Pilot and write (ADDENDUM-1)
- The frames passed check_frames on attempt 1.
- All 3 smoke chats passed check_chat, and the scan found 0 hits. The pilot is PASS (exit 0).
- The full write kept all 78 chats, with no errors, in 29.3 minutes. 74 chats passed on attempt 1, 2 on attempt 2
  and 2 on attempt 3.
- `select` kept 60 panel chats plus the 3 smoke chats. claude_mu405_check found no problems: 63 chats, 189 session-1
  turns and 315 session-2 turns.

## My checks here, all code
- `facts` rebuilt from seed 4070 gives the same facts_all.jsonl sha256 (7f8fe48f…).
- `select` re-run on the Mac's raw.jsonl gives the same panel/items.jsonl (e8219746…) and facts.jsonl (26dc7e90…).
- claude_mu405_check on the panel: no problems. `scan` result: 0 hits for every SCAN string.

## Repeats (reviewed; kept)
- `scan` found 26 user messages that each appear in 3 or more of the 78 chats, the largest in 12. Among the 63 kept
  chats, the count is 21, the largest in 11. I read only those lines.
- None is error, limit or refusal text.
  - 19 are session-2 turns. They are greetings of the smalltalk kind ("hey, back again!" and near copies), plus
    "ask" turns that ask the same fact slot the same way ("can you remind me where I grew up?").
  - 7 are session-1 fact lines, repeated because code picked the same value more than once, e.g. "i grew up in
    galway."
- In the kept 63 chats, smalltalk turns have 18 distinct texts, ask turns 32, and feelings, advice and followup turns
  are all distinct (63 each).
- The rule in ADDENDUM-1 removes error or refusal text only. So no chat is removed, and `select` is not re-run.
- Every arm gets the same chats, so these repeats are not a difference between the arms compared. The one effect
  worth noting (a guess, report only): with smalltalk openers this alike, the smalltalk replies may vary less than
  mu-405b's.

## Seal
- SEAL-data.sha256.txt covers this note and prep/: facts.jsonl, facts_all.jsonl, frames.json, panel/items.jsonl,
  raw.jsonl, smoke_facts.jsonl, write.log and the job's RESULTS.md.
- Next: the smoke run on the 3 smoke chats, then N, U0 and U1 on the 60, on this container's CPU.
