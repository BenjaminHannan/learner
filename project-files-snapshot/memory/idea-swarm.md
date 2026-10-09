---
name: idea-swarm
description: Haiku idea swarm 10-07: STOPPED by Ben 6:33 PM ET as not worth its tokens; shortlist (19 run, 21 park, 11 cut, 5 unreviewed) in /mnt/project-files/idea-swarm/
metadata:
  type: project
  modified: 2026-10-07T22:34:36.017Z
---

Thread "Haiku idea swarm" (root cmsg_01GSLCHTCnZxn7DhV19qcDvMW8jPHbDEsvv3BoLQoKfer3). Ran 2:34-6:33 PM ET 10-07: 10 areas, 906 raw Haiku ideas -> 311 distinct -> 56 finalists through Sonnet-chaired Haiku critique panels.
- Ben 6:33 PM ET (cmsg_01GSLCHTCnZxn7DhV19qcDvM4knc3M7ebvaEBGt8LKHvUn): "the Haiku swarm is not worth the number of tokens it's taking up ... cut it to what it has now". All workflows stopped; no cross-area ranking. Explainer page (written by Opus, no agents, Ben asked 6:35 PM ET): https://claude.ai/artifact/U6afAWk4MLcQ2EmVnWSJbz
- Output: /mnt/project-files/idea-swarm/SHORTLIST-2026-10-07.md (run list sorted by panel score, park/cut one-liners, unreviewed list, code facts); raw/finalists-critiqued.json, raw/areas/<area>.json.
- Top run items (none started; tool-D3, reader-D4, talker-D1, tool-D2, newkinds-D1 are checks with no training; thinker-D3, reader-D1, reader-D3 train on the PC GPU): tool-D3 T1 write_copy link audit (7); reader-D4 variant-miss map (6.5); talker-D1 wrong-answer probe, thinker-D3 worked steps for fewshot/table_lookup, tool-D2, reader-D1 Gemma random-code control, reader-D3 table-only Gemma, newkinds-D1 few-shot donor-swap probe (6).
- Code facts checked by Opus: T1 write_copy sources() mislabels coincidental text matches as copies (relayed to coordinator ~6:10 PM ET for the T1 span-copy re-screen); loops:0 talker mode is row-independent (one route per checkpoint); diag_ledger.py:21 GEN column ignores copy path.

**Why:** Ben judged the token cost too high for the value.
**How to apply:** don't propose another large Haiku swarm without Ben asking; pick items from the shortlist file instead of re-generating ideas. Related: [[no-hardcoding]], [[t1-calculator-outside]], [[deployed-autonomy-rule]].
