# k1h data gate: GLM's answers must pass before any training (Creative answers in chat thread, written 2026-09-26 19:32 UTC)

Written before any k1h chat or answer exists (the Mac job handoff/queue/k1h-glm.md is queued with this file). Fixed now;
not changed after any answer is seen.

## What k1h is (the plan; its pass marks are sealed separately, before any registered run)
The textbook fix the Thread manager asked for (19:33 UTC, "obvious fix first"): teach the creative writer from a
stronger teacher's answers (distillation / instruction tuning). GLM 5.3 Flash (Ben 16:39 "Use GLM"; route: his opencode
plan, 18:47) answers about 900 practice chats; a LoRA adapter on the k1f writer (LFM2.5-1.2B-Instruct @0f604ada) is
trained on BensPC to write those answers from the writer's exact prompt; the adapted writer (arm H) is compared with
the plain LFM writer (arm F) on the sealed k1fpanel. Why LFM and not MiniCPM5-1B: the build's MiniCPM writer shares the
model that carries the sleep adapter (scripts/claude_e2e02c.py:59-72), so a second adapter there would be two changes.
Brain picture (textbook-level; the mapping to our parts is a guess): songbirds and children first copy a tutor, then
refine with reward. k1c, k1d and k1e worked on the second stage (picking) without the first.

## Data (GLM's words only)
- Chats: the 240 GLM practice chats of k1e (artifacts/claude-k1e-20260926/train/items.jsonl) plus about 650 new ones
  written by GLM with the same recipe and words (claude_k1h_glm.py chats, 12 new subject areas).
- Answers: one GLM answer per chat (claude_k1h_glm.py answer): the writer's own instructions (SYSTEM333D), the user's
  messages, the request; plain text, under 120 words, ending with end punctuation. Zero-shot: no example answer.
- Not seen by GLM: the build's short replies to the user's earlier messages (the writer sees them at run time).
- opencode may add its own system text and sets its own temperature; neither can be changed on this route.

## Code filters (the build's own code, no new rule)
Keep an answer only if it is non-empty, claude_chat338_agent.trim leaves it unchanged (it ends with end punctuation,
so the target is what the writer would deliver), and claude_cre333d_agent.guard333d passes it with the request and the
user's messages as known words (G4 over 140 words, G5 refusal, G1 memory claim, G2 an unknown relative's name).
Counts per reason are reported.

## Gate 1: no fixed sentence frame (test-hygiene rule 1)
Over the kept answers: no opening (first 3 words, lowercased, punctuation removed) in more than 25% of them, and no
sentence (lowercased, whitespace squeezed) in more than 2% of them. Computed in code; the top openings and their counts
are reported.

## Gate 2: a blind sample check (test-hygiene rule 2)
60 kept answers drawn with seed 4611, in one packet with JUDGE-k1f.md's words and line format (ids G....), judged by
blind Opus judges 1 and 2 in private folders, judge 3 on the lines they split on (useful, or made-up >= 1).
Pass: useful on at least 48 of 60, and at most 3 of 60 with made_up_user_facts >= 1. The judges' verdicts are used
for this pass/fail only. No answer is dropped or kept because of a judge's verdict (Claude labels never train).

## Gate 3: size and overlap
- At least 600 kept answers; if fewer, a second answer chunk runs (resume) before anything else.
- No practice chat may be a near-copy of a test item. The DEV chats (readable) are compared in code (same request
  after lowercasing and removing punctuation, or 80% or more of the request's words shared). The sealed k1fpanel is
  compared by a separate blind agent that reads both and returns only the ids of practice chats to drop, with a count.
  Dropped chats are removed from training; the panel is not changed.

## If a gate fails
No training on this set. Gate 1 or 2 failing means the next single change is to the answer instructions (sealed
before any new answer is made), and the Thread manager is told first.
