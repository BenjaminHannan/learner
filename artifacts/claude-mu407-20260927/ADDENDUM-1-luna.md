# mu-407 ADDENDUM 1: GPT-6 Luna writes the chats and frames instead of GLM

"Making things up about you" thread. Written 2026-09-27 03:56 UTC (date -u). The draft is ADDENDUM-1-luna-DRAFT.md
(3f6b497dd, d02b52699, 30fdf82fb). The Thread manager reviewed it at 03:52 UTC: OK to seal once the helper passes its live
test, with the fixes below. This addendum is sealed in SEAL-luna.sha256.txt before any Luna call. When it was sealed,
no mu-407 chat, frame or talker reply existed; the GLM prep job never launched and stays in handoff/held/.

## Why
- Ben's opencode Go plan hit its usage limit around 00:57 UTC, according to the Director at 03:06 UTC (relayed from
  Ben's Mac Claude). No GLM call has worked since.
- Ben ruled at 03:47 UTC (goals page design/v3/30-modes/ben-goals-2026-09-26.md:110-116, cd475e141 and 5ed7dcad9).
  - Luna may write training text, inputs and labels.
  - At 03:47:41 he said: "just have luna rewrite all the training data".
  - A sealed experiment that switches to Luna needs a written addendum and a pilot gate first.

## What changes: one thing, who words the text
- Writer: GPT-6 Luna, through Ben's Codex plan.
  - Helper: scripts/claude_luna_codex.py (Director, 24ca7a163), sha256
    342a0fb7e15ebf22da763c21eddecb0c58cfcbd43c74481d8421b5709023024e.
  - Its interface is call(text, model, timeout=300). It tries 3 times, then raises. An empty reply, or a short reply
    that looks like an error, counts as a failure and is never returned as text.
  - Its live check on the Mac passed: "selftest ok: model gpt-6-luna, output-file True", and 3 parallel calls returned
    in 10.9 s (handoff/replies/000-luna-helper-selftest.md on builder-outbox; Director 03:54 UTC).
- Luna replaces GLM 5.3 Flash (low) as the writer of:
  - the chats: the user's messages around code-picked facts;
  - the four frames: system line, memory header, line prefix and current-message label.
- Code: scripts/claude_mu407_prep_luna.py (new file).
  - It imports claude_mu407_prep unchanged and replaces only its module-level caller with luna_call.
  - luna_call pins the model to gpt-6-luna, so no other model id passes through.
  - When a Luna call raises, the prep's own handlers count it as one failed attempt of 3. For a chat, write_one records
    an ok:false row; for the frames, the frames loop tries again. The run continues. Selftest 11/11 checks both cases.
  - Added subcommands: `smokefacts`, `pilot` and `scan`. Everything else is claude_mu407_prep.main().
- Unchanged:
  - the prompts, chat_prompt and FRAMES_PROMPT, word for word;
  - the checks: check_chat, check_frames and claude_mu405_check;
  - the facts: seed 4070, 75 candidates plus 3 smoke;
  - the selection rule: the first 60 passing candidates, in id order;
  - ATTEMPTS, set to 3;
  - the talker, the arms, the judges, every mark and both predictions.
- Wherever PASSMARKS.md names GLM as the writer of chats and frames, read "Luna". The INCONCLUSIVE meaning becomes: "the
  Luna frames or system line already remove the failure U showed".
- Nothing Claude-written or Claude-judged is added. Claude writes no chat text and no frame text.

## Concurrency
- At most 1 Luna call at a time (`--workers 1`). The Director's 03:54 UTC share is 2 parallel calls for mu-407 and
  g406b-L combined, and this job takes 1 of them.

## Pilot gate (fixed before any Luna text exists)
- Order: `facts`, `smokefacts`, `frames`, `write` on the 3 smoke rows, then `pilot`. The smoke chats are never among
  the 60.
- The pilot has three results:
  - PASS (exit 0): the frames pass check_frames within 3 attempts, AND at least 2 of the 3 smoke chats pass check_chat
    within 3 attempts each, AND the scan finds no hit.
  - FAIL (exit 1): the frames fail, or fewer than 2 smoke chats pass. There is no full run. I report the failing check
    to the Thread manager, and no prompt is reworded to chase a pass.
  - REVIEW (exit 2): both checks pass, but the scan hits one of claude_mu407_prep_luna.SCAN ("usage limit", "rate limit",
    "error:", "as an ai", "openai", "codex", "i can't help with"; case ignored) in a kept text.
    - The job stops before the full run.
    - I read only the hit lines, which are smoke-chat or frame text.
    - If a hit is a real error or refusal, that is a FAIL. If it is ordinary user text (for example a line about code
      containing "error:"), the full run is queued as a resume. Either way, the reason is recorded in the run note.
- The pilot's frames are the frames used in the full run. `write` resumes, so the pilot's chats are kept.

## Full run and data seal
- On PASS, the steps are:
  1. `write` on all 78 rows, in the background, into the same raw.jsonl.
  2. `select`.
  3. claude_mu405_check.
  4. `scan`.
- Before SEAL-data, `scan` counts SCAN hits in every kept text, plus user messages repeated across 3 or more chats (the
  Director's 03:16 UTC advice).
  - Any hit or repeat goes to review, and I read only those lines.
  - "error:" can hit an ordinary line about code. A hit like that is kept, and the SEAL-data note says so.
  - Error or refusal text is removed by a rule written in the SEAL-data note before the talker runs. That rule is
    applied by item id and re-runs `select` without that item.
  - The counts and any removals go in the SEAL-data note.
- SEAL-data.sha256.txt comes before the smoke talker run, as sealed.

## Seal
- SEAL-luna.sha256.txt covers this addendum, claude_mu407_prep_luna.py and claude_luna_codex.py.
- SEAL-prep.sha256.txt still covers the prep script and its helpers. SEAL.sha256.txt (864313036) still covers the marks
  and the talk and judge code.

## Where and cost
- Job: handoff/queue/madeup-mu407-luna-mac.md.
  - A Zen builder on Ben's Mac runs it, and the job calls the helper there.
  - The Mac worktree is not on main, so the job fetches main and works from a `git archive` of it.
  - The job has no claude- prefix, and its long step runs in the background with polls under 80 minutes.
- Cost: 4 pilot calls, then about 75 more (at most 3 × 79 with retries). They run under Ben's Codex plan as ruled at
  03:47. No pool money is used and nothing is rented.
