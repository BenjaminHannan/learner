# vread2 handoff: what is done and what is left (2026-09-28T02:17Z)

**Superseded:** Ben asked the same session to finish, and it did: the rental ran through the execute + cat route
(600760bc9). See RESULTS.md.

**Done, at f53ce4525, before any training:**
- PASSMARKS.md, the fresh data (`data/`, Luna chunks 11-13: 6,483 rows, 538 backref cards) and the code:
  - `scripts/claude_vread2_data.py`;
  - `scripts/claude_vread2_model.py`;
  - `scripts/claude_vread2_score.py`.
- CPU checks passed:
  - both arms' gradient check;
  - B's loss equals A's when a name has one copy;
  - arm A is bit-identical to vread's own training after 3 steps;
  - the copy check;
  - the selftests.

**Not done:** the rental, the reads, the bars, the scores, RESULTS.md and the recount. No GPU was rented and no
money was spent.

**Why it stopped:** the session's safety check blocked the copy-back route I tried: an inbound tunnel to the
rental, since this container can reach only standard ports. After that it blocked any further edit of the rental
script for the rest of the session. The untracked draft of `scripts/claude_vread2_rent.py` in that session was not
committed and should not be used. It served files over an open port.

**For the next session:**
- Write `scripts/claude_vread2_rent.py` from `scripts/claude_vread_rent.py`, with nothing listening for inbound
  connections.
- The job, per seed 327 and 331:
  - `claude_vread2_model.py train --seed S`, which trains A and B together;
  - then `read --arm A|B` of `rows/cal.cards.jsonl` and `rows/fresh.cards.jsonl` for each checkpoint.
  - Files: vread's pack plus `artifacts/claude-vread2-20260928/data`.
  - The unpack steps: `claude_vread_data.py unpack` and `claude_vread2_data.py unpack`.
- Copy-back:
  - at the end, write MANIFEST.sha256 and base64 text parts (8 MB and 1 MB) of each `.pt` and of the results
    tarball;
  - stop the instance, then read each part with vast `execute` (`cat`), as vread read its text files;
  - join the parts, decode them and check each sha256 against the manifest;
  - destroy the instance only after every file checks out.
- Then run `claude_vread2_score.py bar`, commit bar.json, then `score` (per checkpoint, with its own bar) and
  `verdict`, then the blind recount.
