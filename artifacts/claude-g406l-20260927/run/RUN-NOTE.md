# g406b-L run note (written 2026-09-27 03:57 UTC, date -u)

- Sealed in 36e6710b8. SEAL.sha256.txt has 24 lines and all verify from an archive; the mu-405b judge files match g406-2's seal.
- Job handoff/queue/madeup-g406l-mac.md is queued. It runs on Ben's Mac through a Zen builder, and the job calls claude_luna_codex.py (sha 342a0fb7) there. It pilots on 10 packets, then runs the rest in the background, with 1 Luna call at a time.
- Not started when this note was written. The watcher's start time and the job's own date -u lines will be in run/RESULTS.md.
- Labeller: Luna (gpt-6-luna). The blind judges are the yardstick only.
- Update 05:51 UTC (date -u): the watcher logged "launch madeup-g406l-mac" at 01:28:01 local = 05:28:01 UTC 09-27 (status push on builder-outbox, 05:28:09 UTC). It runs on Ben's Mac through a Zen builder. No PIDs are visible from this thread. Expected: a pilot on 10 packets, then about 230 more packets with one Luna call at a time, then the count. The finish is an estimate: about an hour after launch.
- Update 06:43 UTC (date -u):
  - Results are pushed and copied to main (756fdd302). The pilot passed. The full run stopped on its 45-minute cap with 220 of 240 packets done and 0 failed.
  - The resume job madeup-g406l-resume-mac is queued (ADDENDUM-1-resume.md).
- Update 08:23 UTC (date -u): madeup-g406l-resume-mac launched at 07:25:58 UTC. Both builder passes stopped at their
  first model call on "Rate limit exceeded", rc=1, and nothing was pushed to run2/ (c858cb577). It is queued again as
  madeup-g406l-resume2-mac, with the same steps plus a restart rule (ADDENDUM-2-relaunch.md).
- Correction (08:24 UTC, date -u): the "Update 08:23 UTC" line above was typed ahead of the clock. It was committed at 08:22:42 UTC (a2b9585f3).
- Update 08:24 UTC (date -u): the Thread manager agreed with ADDENDUM-2 on one condition, now in ADDENDUM-2: at most 2 more launches of the resume, none after 16:00 UTC, then INCONCLUSIVE. Launches that made no Luna call: madeup-g406l-resume-mac, rc=1.
- Update 08:44 UTC (date -u): resume2 never launched: the watcher held it on its builder cap. I moved it to handoff/held/
  and queued madeup-g406l-resume3-mac on the BASH-ONLY route (no builder). This is launch 2 under ADDENDUM-2.
- Update 09:21:39 UTC (date -u): madeup-g406l-resume3-mac (BASH-ONLY) launched at 08:44:42 UTC. The resume ran
  08:44:51-08:50:21 UTC, and the results were pushed at 08:51:19 UTC with rc=0. The start hash matched (19889ed2...),
  the seal was OK, all 4 selftests were ok, 20 packets were written with 0 failed, and 240 of 240 packets are usable.
  run2/ is copied to main, with the job's files in run2/job/. I recounted here: best_b, verdict_b and arms_b are
  identical. A blind recount comes next, then VERIFY.md. Launches that made no Luna call: madeup-g406l-resume-mac,
  rc=1 (resume2 never launched).
