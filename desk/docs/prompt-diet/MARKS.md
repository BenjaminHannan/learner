# MARKS: PROMPT-DIET (2026-11-05). Written before any code change or result.

**Problem.** At 15:29 Ben asked "can you check my grades?" and waited 113 s for the first token. The gateway logged
`system=3000 user=20807 assistant=7906 tool=261 tools=6410 msgs=21 (43,873 chars)`, which is 10,798 prompt tokens.
What was already found before this file was written (diagnosis only, no results): in that thread (tmw1jjdv0kmiv), user messages 55, 56 and 58
each carry the whole ~6.5k-char "Saved notes" block. Since 314ba6d18 (notes by relevance) the block changes with each message, so
`memSig === memBlock` fails and the full block is written into every turn again. The window cap is `contextTokens` 12000 (chars/3.5 ≈ 42k chars).
The gateway prewarms the system+tools prefix, so tool lists that change per turn would break the warm cache.

**Scope.** Glim's chat requests from the Desk to the M1 brain (Nanbeige4.2-3B 8-bit, MLX). This is not a toy experiment. One change at a time,
each with its own row in REPORT.md. Claims in REPORT.md are labelled shown / suggested / untested.

## How it is measured

- **Tokens:** the exact request the Desk would send (requestMessages + taskTools from the code under test) is rebuilt offline from Ben's real
  stored threads. It is counted with the Nanbeige tokenizer's own chat template, tools included. No model is loaded.
  - Replay set R: every Ben turn (not hidden, not a self-check) in the 4 most recent threads in userData/threads, as of this file's commit.
  - Parts are counted separately: system, tools, notes, history, the new turn.
- **Warm new tokens:** the tokens after the longest common prefix with the previous request of the same thread. That is what a warm cache still has to prefill.
- **TTFT:** time to the first streamed chunk (thinking or text) of a rebuilt request, sent to the gateway on 8090. The rules:
  - only while Ben is idle (no Desk chat request for ≥ 3 min, memory pressure normal, 1-min load ≤ 8);
  - under ~/learner-ops/bin/realmodel-lock.sh;
  - never with a second brain copy loaded.
  - Cold = the first request after a fresh brain start, with only the gateway's prefix prewarm. Warm = the next turn of the same thread right after.
  - 5 turns each, old code and new code, same turns.

## Pass marks (fixed now)

1. **Tokens (R, new code):** the median full request is ≤ 4,500 tokens, the 90th percentile is ≤ 6,000, and the maximum is ≤ 8,000.
   - Typical warm new tokens per Ben turn: median ≤ 800.
   - Reported: system + tools alone (they cannot shrink without the bench guard, see below).
2. **TTFT (idle, healthy memory):** warm median ≤ 5 s, cold median ≤ 15 s, with the new code on the same turns as the old code.
   If the Mac is never idle-and-healthy before the report, TTFT is reported **untested**, never estimated as measured.
3. **Quality guard A (agent bench, desk/test/agentbench, MARKS-agent-v1 rules):**
   - The AGENT1 baseline is 12, 12, 8 (mean 10.67). The accept threshold for a *gain* is 12.67. This change claims no gain.
   - First, a deterministic check: are the bench tasks' requests byte-identical under old and new code? (Bench tasks are one-turn threads.) If they are, the bench is unaffected by construction.
   - Either way, the run is wave.sh, the quiet gate, idle only. PASS: mean ≥ 8.67 (baseline minus the 2.0 noise band), and no task that passed ≥ 2/3 at baseline fails ≥ 2/3.
   - If byte-identical, one run is enough: pass at ≥ 9 of 20, with the guard tasks that failed listed. The 2-of-3 regression rule needs 3 runs, so it is not checked. Otherwise 3 runs.
4. **Quality guard B (10 chat turns):** 10 real-style multi-turn chats, built from Ben's real threads.
   - Each final question needs a fact from older history or from saved notes. The fact words for each are written in chat10.json before any run.
   - The real brain answers with old code and with new code, at temperature 0.2, idle only.
   - PASS: new keeps the fact in ≥ 9/10 **and** ≥ (old − 1).

**What proves it wrong:**
- the median request stays > 4,500 tokens;
- warm TTFT median > 5 s on an idle, healthy Mac;
- guard A mean < 8.67 or a guard-task regression;
- guard B below its mark.

A change that fails is reverted or left off behind a setting.

## Candidate changes, in order (each measured alone first)

- **D1.** Notes delta: when the notes block changed but a copy is still in the window, send only the note lines that are not already in the window.
- **D2.** A smaller history window (contextTokens for the Premonition preset; Ben's saved 12000, which equals the old default, migrates).
  The summary call that runs when the window moves must not add a model call to most turns. Mark: window moves on ≤ 1 in 3 Ben turns in R.
- **D3.** Only if the bench guard can be run: shorter tool text. Tool lists that change per turn are rejected up front, because they break the gateway's prefix prewarm and the warm cache.
- **D4.** The UI context count includes the system prompt and tools.

Not changed here: other sessions' uncommitted hunks (SWITCH-ON, ONE-GLIM). Nothing is spent or published.
