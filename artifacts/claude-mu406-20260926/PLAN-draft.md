# mu-406 (DRAFT, not sealed): does practice on its own clean replies stop the talker making things up about the user?

"Making things up about you" thread. Written 2026-09-26 19:29 UTC by date -u while mu-405 runs. Not sealed: the panel, the input
format and the labels are fixed by mu-405's and g406's verdicts, then this folder gets its own PASSMARKS, sealed before
any training run. Free routes only (BensPC through the queue, GLM through Ben's opencode); a rental needs an ELI5 plan
and Ben's yes.

## Why this test is next
OBVIOUS FIX FIRST (19:24 UTC). Four textbook fixes. Three are tested or running: a prompt line (mu-403 FAIL), the 1B's
own check before speaking (AUC 0.54 vs bar 0.65), and the user's own words as input (mu-405). The untested one is
training: faithful-dialogue fine-tuning, done here in its simplest form, rejection-sampling fine-tuning (the model
samples replies, a marker keeps the clean ones, the model is trained on what was kept).
Brain (a guess): children learn to keep their stories about other people apart from what those people said through
correction; a check that has been practised becomes automatic, which is what training does to the talker. Silicon
improves on it: each practice reply can be checked against the exact words the user said.

## Draft design (one change: the LoRA trained on its own clean replies, vs the same plain 1B)
- Talker and input: plain MiniCPM5-1B (87179e5c) with 0.2d's W input (the user's own words, y1f's L1 lines), as in
  mu-405's arm W; the input choice follows mu-405's verdict.
- Practice chats: GLM-written two-session chats (GLM writes the user turns only), code-chosen facts from
  scripts/claude_mu405_facts.py's slots under a new seed range, fictional names, no Claude text anywhere.
- Practice replies: the 1B samples 4 replies per session-2 turn (temperature 0.7), history built from the kept reply.
- Labels: g406 PASS -> GLM marks with the two-session rubric (after g406b); g406 FAIL -> code only (a reply is dropped
  when it names a code-chosen value the chat never gave). A turn with no clean sample is skipped.
- Training: LoRA on the kept replies only (the 1B's own words), on BensPC through the queue, torch 2.11.
- Test: a fresh 60-chat two-session DEV panel (never used for practice), greedy, the same four checks as mu-405:
  blind claims judges (two per packet), pair judges for chat quality, stored-fact asks right, and a small
  MMLU-Redux + GSM8K no-harm check.
- Draft marks: PASS when made-up flags drop by at least 10 and to at most 0.67 x the plain 1B's (per-chat sign test
  p <= 0.05), pair judges do not prefer the plain 1B, asks right do not drop by more than 3, and benchmarks stay within
  2 points. Proved wrong: the trained talker's flags are at or above the plain 1B's.
- FAIL fallback (named now): preference training on the same samples (kept vs dropped replies of the same turn, DPO),
  one change on the same data.
