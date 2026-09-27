# g406b-L run note (written 2026-09-27 03:57 UTC, date -u)

- Sealed in 36e6710b8. SEAL.sha256.txt has 24 lines and all verify from an archive; the mu-405b judge files match g406-2's seal.
- Job handoff/queue/madeup-g406l-mac.md is queued. It runs on Ben's Mac through a Zen builder, and the job calls claude_luna_codex.py (sha 342a0fb7) there. It pilots on 10 packets, then runs the rest in the background, with 1 Luna call at a time.
- Not started when this note was written. The watcher's start time and the job's own date -u lines will be in run/RESULTS.md.
- Labeller: Luna (gpt-6-luna). The blind judges are the yardstick only.
- Update 05:51 UTC (date -u): the watcher logged "launch madeup-g406l-mac" at 01:28:01 local = 05:28:01 UTC 09-27 (status push on builder-outbox, 05:28:09 UTC). It runs on Ben's Mac through a Zen builder. No PIDs are visible from this thread. Expected: a pilot on 10 packets, then about 230 more packets with one Luna call at a time, then the count. The finish is an estimate: about an hour after launch.
- Update 06:43 UTC (date -u):
  - Results are pushed and copied to main (756fdd302). The pilot passed. The full run stopped on its 45-minute cap with 220 of 240 packets done and 0 failed.
  - The resume job madeup-g406l-resume-mac is queued (ADDENDUM-1-resume.md).
