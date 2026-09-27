# mu-407 ADDENDUM 1 (DRAFT, not sealed): GPT-6 Luna writes the chats and frames instead of GLM

"Making things up about you" thread. Drafted 2026-09-27 03:50 UTC (date -u), after Ben's 03:47 UTC ruling (goals page
design/v3/30-modes/ben-goals-2026-09-26.md:110-116, cd475e141 and 5ed7dcad9). The ruling: Luna may write training text,
inputs and labels. A sealed experiment that switches to Luna needs a written addendum and a small quality pilot gate
first. At the time of writing, no mu-407 chat, frame or talker reply exists. The prep job never launched and has been in
handoff/held/ since 214e69905.

## Why
- Ben's opencode Go plan hit its usage limit around 00:57 UTC. This comes from the Director at 03:06 UTC, relayed from
  Ben's Mac Claude. GLM calls have failed since.
- mu-407's data is about 80 GLM calls.
- Ben's ruling at 03:47:41 UTC: "just have luna rewrite all the training data". The Thread manager reads this as
  covering mu-407's prep.

## What changes (one thing: who words the text)
- Writer: GPT-6 Luna through Ben's Codex plan, via the Director's Luna text-call helper. The helper does not exist yet.
  When it lands, its file, model id and settings are named in SEAL-luna.sha256.txt. Luna replaces GLM 5.3 Flash (low)
  as the writer of:
  - the chats: the user's messages around code-picked facts;
  - the four frames: system line, memory header, line prefix, current-message label.
- Code: a new file, scripts/claude_mu407_prep_luna.py. It imports claude_mu407_prep unchanged and replaces only its
  module-level caller (`call_low`) with the helper's call, then runs claude_mu407_prep.main(). It does nothing else.
- Unchanged:
  - the prompts: chat_prompt and FRAMES_PROMPT, word for word;
  - the checks: check_chat, check_frames and claude_mu405_check;
  - the facts: seed 4070, with 75 candidates plus 3 smoke;
  - the selection rule: the first 60 passing candidates, in id order;
  - ATTEMPTS, set to 3;
  - the talker, the arms, the judges, every mark and the predictions.
- Throughout PASSMARKS.md, "GLM" as the writer of chats and frames now reads "Luna". The INCONCLUSIVE meaning therefore
  reads "the Luna frames or system line already remove the failure U showed".
- Nothing Claude-written or Claude-judged is added. Claude still writes no chat text and no frame text.

## Pilot gate (fixed now, before any Luna text exists)
- Scope: `frames`, then `write` on the 3 smoke chats only, through claude_mu407_prep_luna.py. The smoke chats are never
  among the 60.
- Pass, when all of these hold:
  1. The frames pass check_frames within 3 attempts.
  2. At least 2 of the 3 smoke chats pass check_chat within 3 attempts each.
  3. A code scan of every kept text (the frames and all messages in the passing smoke chats) finds none of these
     strings: "usage limit", "rate limit", "error:", "as an ai", "openai", "codex", "i can't help with" (claude_mu407_prep_luna.SCAN). The
     scan ignores case.
- Fail: no full run. I report the failure and the failing check to the Thread manager, and do not reword any prompt to
  chase a pass.
- The pilot's frames are the frames used in the full run. The pilot adds no calls to the full run, and `write` resumes.

## Full run and seal
- After a pilot pass, the full run is `write` on all 78 rows, then `select` and claude_mu405_check, as in the held job.
- Before SEAL-data, a scan of raw.jsonl, the panel and frames.json looks for the pilot's strings. It also looks for any
  user message repeated across 3 or more chats (the Director's 03:16 UTC advice). The counts go in SEAL-data's note, and
  a hit stops the run for review.
- SEAL-luna.sha256.txt covers this addendum, claude_mu407_prep_luna.py and the helper file. It is committed before the
  first Luna call.
- SEAL-data.sha256.txt then comes before the smoke talker run, as sealed.

## Where and cost
- The job runs wherever the Director's helper runs; the Director's probe decides that. As before, jobs use no claude-
  prefix and long steps run in the background with polls under 80 minutes.
- Cost: about 80 Luna calls, at most 3 × 79 with retries, under Ben's Codex plan as ruled at 03:47. No pool money is
  used and nothing is rented.

## Update 03:58 UTC (date -u): helper and wrapper
- Helper: scripts/claude_luna_codex.py (Director, 24ca7a163). Its interface is call(text, model="gpt-6-luna",
  timeout=300). The model id answered "ok" in the Director's probe at 03:37 UTC.
  - The helper counts an empty reply as a failure. It also counts a short reply that looks like an error as a failure,
    so such text is never returned as a reply.
  - Its selftest job (000-luna-helper-selftest) is queued. This addendum is sealed only after that selftest passes.
- Wrapper: scripts/claude_mu407_prep_luna.py (offline selftest 8/8; claude_mu407_prep's own selftest 8/8 through it).
  - A fake-caller run of `frames` confirmed that the prep's main() uses the swapped caller.
  - Added subcommands: `smokefacts` (the 3 smoke rows, as the pilot's input for `write`), `pilot` (the gate above; exit
    0 on pass) and `scan` (the pre-SEAL-data scan).
  - I dropped "language model" from the scan list, since a system line may harmlessly say it. The list is
    claude_mu407_prep_luna.SCAN.
- Pilot order: `facts`, `smokefacts`, `frames`, then `write` on the smoke rows, then `pilot`. On a pass, `write` runs on
  all 78 rows into the same raw.jsonl (it resumes), then `select`, `claude_mu405_check`, and `scan`.

