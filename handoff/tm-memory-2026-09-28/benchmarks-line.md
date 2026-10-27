---
name: benchmarks-line
description: Public-benchmarks thread (Ben's /goal 09-25): bm-390..398r results/runs, rival bar, next steps, agreed integrations
metadata:
  type: project
  modified: 2026-09-27T14:08:00Z
---
Thread cmsg_01FuvegZXjMmeUzStiEFVnEWR1sgF3AM2qZsgpJyiCQBKU. Numbers bm-390..399. Harness scripts/claude_bm390.py (+_score.py). LoCoMo = dev; LongMemEval = untouched final exam (bm-399); never trained on.

- bm-390 FAIL (0.1): LoCoMo 1-4 F1: plain 1B whole chat T 27.50; Qwen3.5-2B Q2 47.87 (THE BAR); LFM2.5 19.01. MMLU/GSM8K of 300: T 50/191 (234 no letter, so MMLU 50 measures format), Q2 201/209.
- bm-397t (short-answer LoRA) FAIL (2a16636d4): F1 27.50->37.07 but GSM8K 191->42 (working dropped), blind A 112->107 (CI -8.2..+5.3). Gain = wording. Dev checker is word coverage only. Adapter ~/premonition-models/bm397t-adapter397t.pt. Follow-ups: design/v3/30-modes/398-benchmarks-followups-2026-09-26.md.
- bm-398d evidence diagnostic (56c71354c, recount agrees): blind A of 297 (judges see evidence): G right lines only 137, Qwen whole chat 138, GD 119, T whole chat 109, E20 88. With right lines the 1B still misses 160: dates 17%, multi-hop 23%.
- REDIRECT (Ben 16:04): no rule work; rivals = headline.
- bm-398i switch PASS CPU (60d4fc217) + GPU real adapter x2 (25d29e406). bm-398r FAIL + PROVED WRONG (84c414325): blind A TR 110 vs T 111, Qwen 142; F1 27.5->36.1 = wording; route stops; out of builds (Claude-written templates). bm-398n FAIL not proved wrong (15d492d52): blind A AN 252 BN 269 of 759, 83/66, p 0.19; suggested: B-only-found 9->43, both-found 219->208. bm-398u (d8078eda4): claim PASS (1B's own top 3 of store B's 20 = 236 vs store top 3 207, p 0.019) but FAIL vs all 20 (264, p 0.039); loss = evidence cut out of 3. bm-398v FAIL + PROVED WRONG (df149a5b8): own top 8 256 vs all 20 264 of 772 (LoCoMo 5-9), wrong +18; no cut of store B's 20 beats all 20; plain reranker stops.
- bm-398w STOPPED by Ben 13:57:41 09-27 ("Stop it" card: talker stays plain, no skill training; his 13:28 yes: talker gets no skill training). Never trained. Data kept on Mac D=.../T/tmp.oZGCMa5NMn + pushed data/ (170 train plans, 1,070/1,200 Luna sessions = 151 full chats, no questions; 26-chat panel 182/182, never read, TEST-ONLY). Stopped 14:03 by 000-bash-stop-bm398w (rc=0; 4d417fab0, 6a978b7e6); DO NOT RUN on held -b + benspc draft. TM 14:04 chose A: problem 4 PARKED, queue nothing until rsn-358k (sealed b04f9151f) reports G1k; B (text picker in reasoner slot) = architecture, needs Ben's yes, may be an unsealed draft, not to Ben before G1k passes; C only if G1k proved wrong. No new talker-training line without Ben's word. Gap (bm-398d): right lines 137, +look-alikes 119, store 20: 88 of 297.
- LESSONS: times from `date -u` run BEFORE writing. Before sealing a prompted format, count compliance on dev items; smokes never on test items. Judges' closing reports quoted item text as ruling examples (398u, 398v): prompt must forbid examples too.
- FROM 16:55 09-26 every PLAN carries a no-harm mark on blind D (wrong) and E (don't know) counts. Gap to Qwen = finding lines (bm-398d G 137 vs Q2 138; single facts 110 vs 111).
- NEVER REUSE bm-397t/bm-398r training data (claude_bm397t_data.py, claude_bm398r_data.py): Claude-written templates (Ben 16:39 rule). Rebuild any adapter from GLM chats + code-checked answers.
- Answering from memory owns the Y1 row.
- MONEY (Ben 18:47 + 18:54 09-26): $30 project pool (Director counts). No rental without Ben's own yes on an ELI5 plan sent via the Thread manager. BensPC/CPU/GLM-opencode need no plan. Spent before: $1.28.
- Rivals: scripts/claude_bmriv_rivals.py (601d86c46); Qwen needs 8192 tokens. Talker is LFM2.5-1.2B since Ben 19:27 09-27: next run adds plain LFM as the key same-size row.
- Overlaps: [[benchmarks-overlaps]].

**Why:** Ben wants genuine wins, no reward hacking, no targeted practice. **How to apply:** a registered FAIL stays FAIL; later builds use the same harness with run2 rivals as the bar; judges see evidence from now on.
