---
name: animation-storyboards
description: Ben's HyperFrames animation request (10-09): four ranked storyboards delivered, build waits for his pick; where files and source numbers live
metadata:
  type: project
  modified: 2026-10-09T17:19:58.902Z
---

Ben, 10-09 (thread cmsg_01GSLCHTCnZxn7DhV19qcDvM3kBfJWzZH9Wuk11G2gUbes): follow the Claude Motion guide (https://support.claude.com/en/articles/17454997-get-started-with-claude-motion), storyboard animations from real project content, rank them, build NOTHING until he picks, then build with HyperFrames (all text/numbers/timings in one data file; later edits touch only the one thing; draft render, 1 frame per second review, fix, 1080p MP4). No paid compute.

Delivered 10-09: /mnt/project-files/animations/storyboards-2026-10-09.md plus ELI5 page https://claude.ai/artifact/ESES6Fwr2BWCpEmDmioJoC. Ranking: 1 one question's trip (Tom's apples, 45 s), 2 thinking dial 73.01 -> 0.66 (40 s), 3 sleep v2 76.1 in 256 steps vs v1 71.3 (40 s), 4 learned stop + any-round calls (35 s, never tested). Project has NO landing page, onboarding flow or release notes (0 releases, 0 tags).
Source numbers for idea 2 were re-added from raw files on branch claude/8a-g-pc-results and saved at /mnt/project-files/animations/source-g1-3m-s400.json (loops 0/1/2/24 pooled-5 = 0.66/20.00/29.30/72.57; chain-5 0.0/0.0/1.1/99.9).
HyperFrames installs from npm (package hyperframes); chromium and ffmpeg already on the cloud box.

**Why:** Ben wants real numbers only and honest "built, never tested" labels.
**How to apply:** when he picks, build from the storyboard file; keep numbers in one data file so 8:30 PM ET seed 401 and the 10M G1 results (estimates) can be dropped in later. Found while checking: PR #56 body says four group-1 parts are switches that start off, but b3.py has only two real switches (eg_embed, any_round); the stop is built into the base and 2,000 letters comes from the caps file. Related: [[finished-model-source-of-truth]], [[eli5-every-reply]].

**Update 10-09 2:30 PM ET: long explainer (Ben asked for "a long animation explaining every part", Sonnet agents).** Built the HyperFrames kit, author guide, glossary, 15 chapter briefs and checker guide in /mnt/project-files/animations/model-explainer-build/ (see HANDOFF.md there). Only ch09 was written (unchecked). Stopped at once when Ben said he has 5% of weekly usage left and it must last until 7 AM ET 10-10. Do NOT restart agents or render until Ben writes after 7 AM; ask first because the full job is about 30 agent runs.
