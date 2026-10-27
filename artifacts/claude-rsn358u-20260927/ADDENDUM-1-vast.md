# rsn-358u addendum 1: the machine can be one vast rental instead of BensPC (sleep research thread, written 2026-09-27 13:05:00 UTC, before any run)

Additive. PASSMARKS.md, PASSMARKS-draft.md and SEAL-code.sha256.txt are unchanged. Nothing of rsn-358u has run anywhere yet.

**Why:** BensPC has not answered ssh since 12:30 UTC 09-27. Ben, 12:45 UTC (via the Thread manager): "Just use vast for now". The Thread manager (12:48 UTC) asked for a held rental that runs all 8 runs on ONE machine with torch 2.11 pinned.

**What changes, only if Ben says yes to the money and the Director releases handoff/held/rent358u-1-start.md:**
1. Machine: one vast.ai RTX 5090 (reliability >= 0.98, >= 16 CPU cores), not BensPC's RTX 5070 Ti. All 8 runs (loop and plain, seeds 13-16) train on that one machine at the same time, as rsn-358i's 8 runs did on a 5090. So loop and plain still share one machine, and every mark compares arms within this run.
2. torch 2.11.0+cu128 is installed on the rental and checked before anything runs (BensPC has the same version). torch 2.8 had the autocast bug that broke 358i's loop nets; 2.11 is what 358i2 and 358i3 used.
3. Commands, seeds, order, marks: unchanged. Train: `python -B scripts/claude_rsn358u_run.py train --arm <arm> --seed <s> --out W/<arm>-s<s>`. Each final.pt is sealed (sha256 into SEAL-run.sha256.txt) before anything reads it, then V1 poison once, then eval once on artifacts/claude-rsn358i-20260926/tests. The code comes from the pinned commit and must pass SEAL 20/20, the selftest and check-mask on the rental first.
4. Records: the rental's own progress file, torch check, checks and rental list go to run-vast/ (instead of run/RUN-NOTE-bo.md). runs/<R>/ holds the same files the BensPC kit collects.
5. The BensPC jobs handoff/held/165-170 (358u on BensPC) must not also run: whichever machine starts first is the only one. The vast start refuses if SEAL-run.sha256.txt or runs/ already exists on main or builder-outbox. The BensPC kit has no such check, so the Director should move 165-170 to handoff/held/superseded/ when releasing the rental.

**What this can and cannot move:** the verdict marks (V0, V1, G0-G3) compare loop and plain trained side by side on the same machine, so a machine change hits both arms alike. The report-only line "drop from 358i3" compares with BensPC nets; it was already "suggested only" (different seeds), and now also differs by machine. Say so in RESULTS.md next to it.

**Money:** cap $4 for this whole task, re-rents included (Ben's standing cap per job; the Thread manager's 12:48 limit). A guard on the Mac stops everything at $3.60 or 4 h 30 min from the first rental: it copies back what exists, destroys the instance by its exact id and confirms it is gone. Estimate: rsn-358i took about 1.6 h on one 5090 at $0.49/h ($0.78). With the extra poison check, about 1.7-2 h, so about $0.80-1.40 at $0.45-0.70/h, plus up to about $0.20 if a host fails to start. The Director's ledger records the real figure.

**Kit:** handoff/kit/sleep358uv/ (vstart.sh, vguard.sh, vcollect.sh, vcommon.sh, box/drive.sh). It was tested against a fake vast and a fake rental: the normal path, a run that dies, the budget stop, a stall, a failed create and a second start (refused).
