# Opus manager plan, written 2026-09-29 02:55 UTC (date -u), before any run by this session

Owner: outside Opus manager session (Ben's request). Files only under artifacts/opus-manager-20260929/. No sealed file, queue file or other folder is edited.

## Compute actually available
- vast.ai: NOT usable from this session. The repo is private, this box has no ssh out, and the session's permission guard refused every route for getting code onto a rented box (it read them as data leaving the box). Spend: $0.00 of $5.00. Ben can allow it; see REPORT.md.
- This box: 4 CPU cores, 15 GB, torch 2.14.0+cpu installed by pip (a library, not a model). No GPU. The qualified loop sources (qual-loop-s*/source.pt) sit only on Ben's Mac, so every test that starts from them (S1, S2, pond, trn, ks, dirlr) cannot run here faithfully.

## What runs here (problem 7, previous-states test)
The sealed History read test is the one open test that needs nothing from the Mac: it practises its own sources from code.
- Marks: artifacts/claude-dir-hist-20260929/PASSMARKS.md (sha256 prefix 0631e67bdb4c3b78), UNCHANGED. Verdict words are theirs (HISTORY HELPS / DOES NOT HELP / NOT SHOWN); mapped for my report as PASS / PROVED WRONG / NOT SHOWN.
- Steps: the commands of handoff/queue/hist-1-practice.md then hist-2-dev.md, run on this Linux box from a private archive of origin/main (~/opus-hist), outputs copied to artifacts/opus-manager-20260929/hist/ (never into the hist folder).
- Disclosed deviations (fixed now): Linux x86 CPU, not the Mac; python 3.11 with pip torch, not uv 3.12; practice runs all four at once with 1 thread each (the job used 2 threads); float results can differ in the last bits from a Mac run. Nothing else changes.
- Blind recount by a separate subagent from raw adapt.json and PASSMARKS only, before anything is called PASS.
- If the Mac also runs hist-1/hist-2, both runs are reported side by side; neither is chosen by its score.

## MoE (mxd-1..4)
Needs a GPU (CPU: about 17 h practice per source). NOT RUN here. It stays in the BensPC queue.

## Problems 1-6
Their tests are sealed and queued (S3 on BensPC; H1 kinds, pond, S2, trn, S1 on the Mac). I add no new tests tonight: none could run before morning, and more jobs would deepen the Mac queue. I check builder-outbox for results that land and blind-recount any that do.
