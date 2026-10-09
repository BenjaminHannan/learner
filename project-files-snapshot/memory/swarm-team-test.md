---
name: swarm-team-test
description: Ben's 32-model swarm idea (10-05): tested 3 ways, none helped on twisted (variant) questions; PARKED; PR #40
metadata:
  type: project
  modified: 2026-10-05T23:09:07.745Z
---

Ben 18:35 UTC 10-05 (2:35 PM ET) asked about a swarm of ~32 small models trained to work together and learn in different ways; 19:01 UTC "see if they can be trained together". Thread cmsg_01GSLCHTCnZxn7DhV19qcDvMLoxLPxaJR9u2hABz3Gm55X. PR #40 (branch claude/project-thread-oetnc2, stacked on #39). Write-up custom_io/RESULTS-TEAM.md (also /mnt/project-files/swarm/). PARKED, told Ben 23:25 UTC.

Shown (2-seed screens, marks fixed first):
- Free: CRDC 6-seed vote variant 49.2 -> 53.7, all six miss 95/280. Small recipes: different recipes miss the same twisted Qs as a 2nd B2 copy (B2-mistakes shared 92.7 vs 93.3).
- Team screen (team.py, coach routes practice, BensPC, s100): ON 31.2 vs OFF 31.4 variant, VOID (final coach moved 1% of sampling, TV 0.010 < 0.05): coach drifts to uniform once members fit practice rows (~98% right). s101 stopped to free GPU.
- Selector (selector.py, GPT's idea: frozen members, coach sees answers vs masked, 16k fresh rows): variant aware-B2 mean -0.57 -> STOP; in_dist +2.5 over B2 (aware 0.7 over blind).

Tools built: custom_io/fastgen.py (KV-cached decode for plain_tf/plain_tf_steps, identical answers, ~30x faster on CPU), team_alloc.py, `team:` lines in local_runner. GPT prompt reviews/gpt-swarm-team-2026-10-05.md.

**Why:** if Ben revisits swarms/teams, these are the negative results and the untested options (DivDis/D-BAT disagreement, members messaging, routing that stays alive, beating a ~10M B2).
**How to apply:** don't rerun these as-is; lever is the shared failure (Qs every member misses). Related: [[chain-of-experts-paper]], [[ultracode-blocker-findings]].
