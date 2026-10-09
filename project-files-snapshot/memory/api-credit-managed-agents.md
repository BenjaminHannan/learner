---
name: api-credit-managed-agents
description: Ben has $200/month Anthropic API credit (not usable for Claude Code); Managed Agents built in PR #55, waiting on Ben's keys
metadata:
  type: project
  modified: 2026-10-09T01:49:03.023Z
---

Ben (9:45 PM ET 10-08): "$200 of api credit on everything but claude code ... per month". Renews monthly. It cannot pay for Claude Code / project threads, but covers Messages API and Managed Agents.

Ben said yes 9:50 PM ET 10-08 (Opus as reviewer). Built in PR #55, ops/managed-agents/ (README has setup; ma.py = setup/status/job/review/cost; IDs go in ids.json). Waiting on Ben: API key as env var LEARNER_ANTHROPIC_API_KEY, self-hosted env pc-worker + key via mac/setup.sh in Terminal, read-only GitHub token LEARNER_GITHUB_RO_TOKEN. Then a fresh thread runs ma.py setup --env-id, check-now, unpause. New Mac local session session_01FeL9Gkp2MwSCRgmwRuhwAe (Haiku, 10-09; old session_018qt3j4biYuC1uFu7tzHb4A retired) checked 8:21 AM ET 10-09: ~/learner-ma present and pulled, ssh -o BatchMode=yes benspc rc=0, Mac arm64, brew at /usr/local/bin (Intel brew), ant not installed yet (setup.sh installs it). G1 owner already wrote job card g1e.md on the PC (log: is the quiet runner log; live log = newest stdout.txt, pc-operator told to read it).
Thread "Managed Agents uses" cmsg_01GSLCHTCnZxn7DhV19qcDvMWKKfaxSiUeAnvk6tZgXXUD plan:
1. PC job babysitter: Managed Agents self-hosted worker (`ant beta:worker poll`, outbound-only) on the Mac, Haiku 5.5 agent, cron deployment or free watchdog script that wakes it on OOM/stall/PC offline; writes status to a GitHub branch. ~$7/mo at 30-min checks (estimate).
2. Threads hand PC jobs to that worker directly if an API key is put in the cloud environment secrets (api.anthropic.com reachable from thread containers, checked 10-08).
3. Routine Haiku work billed to the credit instead of Ben's plan; Opus 5.5 read-only repo reviewer for outside opinions (Ben chose Opus over Fable 10-08; ~$1-3/review est.).
Limits: no GPUs (cloud sandbox CPU, 8 GB); cannot post in project or read /mnt/project-files; worker needs macOS/Linux (WSL on PC); beta. Pricing (checked 10-08): Haiku 5.5 $0.10/$0.50 per MTok, session runtime $0.08/h while running, web search $10/1k.

**Why:** shifts routine token use off Ben's Claude plan (see TOKENS in MEMORY.md) and removes Mac relays.
**How to apply:** caps are $0.50/check, $1/job, $3/review (ma.py sets them). PC job owners write job cards (ops/managed-agents/job-card-template.md) at C:\Users\benja\pc-jobs\; the operator only acts as cards say. Related: [[deployed-autonomy-rule]] (this is ops tooling, not the model).
