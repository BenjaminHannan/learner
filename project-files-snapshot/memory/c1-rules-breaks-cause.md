---
name: c1-rules-breaks-cause
description: Why B2's C1 tries break the rules (step 2 re-reads a used number; B2 never records which slots a step read) and the used-number mask fix, PR #45
metadata:
  type: project
  modified: 2026-10-06T11:32:02.190Z
---

Thread "Ultracode: creative rules blocker" (cmsg_01GSLCHTCnZxn7DhV19qcDvMVvBdQbebHXubLAwjALLGX3, Opus), 10-06 (~7:30 AM ET). DEV only, s100 + s101, 1,500 rung with replay; CPU re-makes match the Mac exactly.
- SHOWN cause: 51% of tries break first at step 2 re-reading a number step 1 used, 16% step 1 same number twice. Constants/ops/target ~0% on warmed parents (the roadmap's constants guess is wrong). Skills prior is not it (reuse only in list_stats, 4.3%). Mechanism: a B2 step feeds back op + result value but not which slots it read, so used numbers look fresh; sampling/branching makes step 1's real pick differ from what B2 "meant".
- Fix tested: `creative/legal.py` level-4 mask (unused operands only, + - x /, k-1 steps, answer = last result, exact division; never reads the target). s100: legal 0.29->1.00, luck 4.7->13.1%, reach@4 16->42%, first try 10.2->18.8%, variety 5.7->16.2 at T 0.7; s101 luck 4.6->13.4%. Aim kept (own vs twin about 3x).
- PR #45 (branch claude/project-thread-4aqhtv, base = PR #44's branch), report creative/results/legal-probe/REPORT.md and /mnt/project-files/creative-pilot/rules-breaks-diagnosis-2026-10-06.md. Skills data rebuilt in this container's scratchpad (hash-checked) via custom_io.local_runner setup with skills_curriculum from branch claude/project-thread-y0sxwe.
- ADOPTED 10-06 ~7:35 AM ET by the roadmap thread as disclosed test scaffolding for C1 (commit 5e3e5bea58 on claude/project-thread-yf9vko, roadmap sec 6); marks accepted as met on s100+s101; build thread wires it in. C2 does NOT inherit the mask. Learned alternative (a "used" mark on workspace slots) belongs to the B2 owner and is untested.

**Why:** C1's legal share and variety were both low because of this one cause.
**How to apply:** don't re-diagnose; any C1/C2 sampler change starts from legal.py. C2 needs its own mask or the learned mark. Related: [[creative-roadmap]].
