---
name: vast-rl-loop-box
description: Vast 5090 54663402 for the fast-sleep C2 research loop, 11:18 AM-5:05 PM ET 10-07, DESTROYED after copy-back; spent ~$2.9 of $4 cap
metadata:
  type: project
  modified: 2026-10-07T18:30:18.145Z
---

Ben tapped "Vast 5090" (10:57 AM ET 10-07) for the C2 research loop (fast sleep thread), cap $4 of the ~$5.22 credit (keep >= $1).
Credit read $9.02 at 1:28 PM ET 10-07 (someone topped up); the $4 cap still counts from the start.
Boxes 54660834 and 54661566/54662416 were destroyed (no curl in the image; trycloudflare 429). Live box: 54663402 (offer 51325614, California, $0.471/h),
from about 15:22 UTC. Reached through a cloudflared quick tunnel + token job server; start script retries the tunnel and falls back to localhost.run.
Files: ~/rl/vast/ in that session (box.py helper, url, token).

**Why:** both of Ben's machines were busy; the loop needs many trials.
**How to apply:** stop by $4 spent (about 23:30 UTC); destroy only after results are copied back and checked; never touch other instances.
Lesson: pytorch runtime images have no curl; download with python urllib; quick tunnels can 429, so retry with backoff.

Destroyed 21:05 UTC 10-07 after all logs were local and pushed (fd4677be7). At that time 11 other 5090s (cio-*, fl8a-*, g8-3M-*) ran at ~$5.7/h against $4.89 credit.
