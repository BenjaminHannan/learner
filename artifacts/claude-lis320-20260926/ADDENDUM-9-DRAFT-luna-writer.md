# lis-320 ADDENDUM-9 (DRAFT, not sealed): the wording writer moves from GLM to GPT-6 Luna; Luna pilot 7 first
# (draft for the Thread manager's review; sealed only after that review and after the Director's Luna helper exists)

Drafted 2026-09-27 03:49 UTC by the reading thread.

## Why
Ben's opencode Go plan hit its usage limit about 00:57 UTC 09-27, during full-run chunk 1 (launched 00:48 UTC). Ben
(03:47 UTC, goals page lines 110-116): "just have luna rewrite all the training data. It's so so cheap". Owners switch
by an addendum plus a small Luna pilot through their existing quality gate; sealed marks do not change; GLM data already
written is kept, not redone; Claude-written or Claude-judged data stays banned.

## The one change: the writer
Every wording call goes to GPT-6 Luna through the Director's Codex text-call helper (a new file; pinned here by path and
sha256 once it is committed and has passed the Director's probe). New wrapper scripts/claude_lis320_luna.py swaps only the
call, exactly as claude_lis320_glm_oclow.py swapped it for opencode: the prompt (claude_lis320_glm.build_prompt), parser,
key guard, batch/stop logic (claude_lis320_glm_oc.run_batches), seeds (claude_lis320_seed_cr.py) and checks
(claude_lis320_check_we2.py) are unchanged. Rows record the Luna model id and temperature null (whatever Luna's route
sets is disclosed, not tuned). New scripts/claude_lis320_rawcheck2.py is rawcheck with the allowed model id as an argument
(the sealed rawcheck asserts the GLM id).

## Luna pilot 7 (seed 327, 60 dialogs) before any full-run chunk
Pass (all of), unchanged from ADDENDUM-7: PILOT-THRESHOLDS items 1-5 (every family including correct_ref at 40% or more
kept; item 5 = 20 random kept rows outside correct_ref, up to 20 kept correct_ref rows, 20 dropped, more than 2 of 20
kept wrong fails); at least 54 of 60 parsed; at most 6 of 60 failed or timed out; rawcheck2 OK with the Luna id.
Added route checks (not quality marks): no reply text repeated in 3 or more rows, and no row whose text is an error or
limit message (both come from the Director's 03:16 warning about the helper returning error text on exit 0).
If it fails, one thing changes, it is named, and the pilot re-runs on seed 328.

## Full run after a passing pilot 7
Seed 324, 6000 dialogs, as before. Chunk 1's GLM rows (if it pushes) are kept when they parse, are not empty, carry no
error or limit text and are not a text repeated in 3 or more rows; every other seed-324 dialog is worded by Luna. So the
training set has two writers: the GLM share is small (chunk 1 did real work for about 9 minutes, an estimate until it
lands). DATA.md reports rows, kept rows and kept_by_family per writer (report only; the verdict marks are on the whole
reader). Chunks: at most 70 wording minutes each (the Mac agent's shell kills a command after 80), a 1-call probe before
each chunk, per-chunk new-row files as in chunk 1, and the 85%-parsed stop rule.

## One question for the Thread manager before sealing
Item 5's hand read is done by a fresh Claude agent. It writes no row and selects no row for training; it only decides
whether a 60-dialog pilot passes. I read "Claude-judged data stays banned" as not covering this gate. If it does, the
alternative is a fresh Luna reader for item 5 with the same instructions, which I would name here before the pilot runs.
