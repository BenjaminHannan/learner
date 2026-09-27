# mu-406 ADDENDUM 1: how many launches the long Luna steps may take

"Making things up about you" thread. Written 2026-09-27 10:48 UTC (date -u), after the test panel was sealed and before any practice
chat or teaching reply exists. Marks, data rules, prompts and scripts are unchanged (SEAL.sha256.txt).

## Why
- PASSMARKS says a step that "cannot finish within 3 launches" is INCONCLUSIVE. I wrote that for launches that fail.
- The panel job measured about 16 s per chat at 2 Luna calls at a time (78 chats in 20.7 minutes). Every BASH-ONLY
  job must finish in 75 minutes, so each writer stops itself at 50 minutes.
- So step 3 (practice chats: the first 240 candidates) needs about 2 launches. Step 4 (1,100 teaching-reply calls)
  needs 2 to 4, depending on the time per call, which is not measured yet. Each such launch writes new chats and
  keeps the old ones.

## Rule (replaces the "3 launches" line for steps 3 and 4 only)
- A launch that writes at least one new chat is progress. A launch that writes none (it dies before its first call,
  or every call fails) is a failed launch.
- A step is INCONCLUSIVE after 2 failed launches in a row, after 6 launches in all, or if it has not finished by
  2026-09-28 18:00 UTC.
- Every launch is listed in run/RUN-NOTE.md with its rc and how many chats it added.
- Steps 2, 6 and 7 keep PASSMARKS' limit of 3 launches.

## Review
- The Thread manager accepted this addendum (message at 10:49:18 UTC, read at 10:49 UTC). It asked that each launch
  also report its time per chat, so a slowdown shows early. The run note lists that for every launch.
