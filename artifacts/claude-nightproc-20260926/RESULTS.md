# night-proc acceptance: PASS (A1-A6), CPU, 2026-09-26 ~02:50 UTC

Command: `python -B scripts/claude_night_proc.py --accept --model MiniCPM5-1B@87179e5c --out <scratch>`. It ran on the
Fix-sleep session's CPU and was run once. Raw results are in accept_results.json. Each mark was checked against its
raw fields, not only the ok flags.

- **A1: PASS.** The learning night exited 0 and wrote v0001 with its record accepted. ACTIVE points to v0001.
  - E1: the weights changed.
  - E2: lost 0 of 12 on the cut panel.
  - E3: the largest logit difference from the plain base was 5.125.
- **A2: PASS.** In a fresh process, v0001 loaded from ACTIVE and its fingerprint matched the record.
- **A3: PASS.** The night with no eligible examples left ACTIVE and the version list unchanged.
- **A4: PASS.** The child was killed by exact PID after 45 s and exited with -9. ACTIVE was unchanged, v0001 still
  loaded with a matching fingerprint, and there were no half-written versions.
- **A5: PASS.** A record naming another base was refused at load.
- **A6: PASS.** The stand-in live-notebook folder was byte-identical before and after all nights.

Deviations: none. The A4 kill landed before the candidate save. The exact stage inside the child (panel scoring vs
training) was not logged.

Limits:
- This is plumbing, not learning; dl-2 is the learning claim.
- CPU and tiny sizes.
- The kill test covers one moment only. Month-end owns the joined interruption test (before, during and after
  save/activation).
