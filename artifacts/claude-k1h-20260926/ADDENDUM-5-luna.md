# k1h ADDENDUM 5: Luna writes k1h's answers, after a 40-chat pilot (Creative answers in chat thread, sealed 2026-09-27 04:03 UTC)

This is the sealed version of ADDENDUM-5-luna-DRAFT.md (fa890db24), which stays on file as it was. The Thread manager
approved the draft at 03:52 UTC and gave the fill-ins used below. Written before any Luna call for k1h, and before I
have read any k1h-glm2 output from after 20:38 UTC. It changes the teacher and nothing that is marked. The marks, arms,
panel, recipe, gates 1 to 3, the size floor of 600 and ADDENDUM-4's route-loss rule stay as sealed. Registered FAILs
stay FAILs.

## Why
- Ben's opencode Go plan hit its usage limit at about 00:57 UTC (the Director, 03:06 UTC). The GLM route that k1h's
  data was using is blocked, and no reset time is known.
- Ben, 03:47 UTC, card cmsg_01FuvegZXjMmeUzStiEFVnEWXB5YaHqBJfNGxiQTxBNbz6: "Allow Luna" (GPT-6 Luna, through his Codex
  plan, may write training data).
- Ben, 03:47:41 UTC (cmsg_01FuvegZXjMmeUzStiEFVnEWDj4nGsmBa5Vwmx8geQnSH6): "just have luna rewrite all the training
  data. It's so so cheap".
- Both are recorded on the goals page (cd475e141, 5ed7dcad9). A sealed experiment switches only with a written addendum
  and a small quality pilot first.

## The change: every training answer (target) comes from Luna
- Luna answers all of k1h's practice chats, including the 240 k1e chats that GLM already answered. One teacher writes
  all the targets, so a result reads "taught from Luna's answers", not a mix of two teachers' styles.
- GLM's 240 answers (k1h-glm2 step 4) stay on file. They are not deleted and not trained on. Any k1h result will say
  that they exist and were not trained on (the Thread manager, 03:52 UTC).
- Chats (the inputs) stay as written. These are the 240 k1e chats (GLM-written in k1e), plus the chats GLM wrote in
  k1h-glm2 if the salvage brings a chats.jsonl back. Luna writes the rest (see "Full run"). Inputs from GLM and from Luna
  may be mixed (the Thread manager, 03:52 UTC).
- Every chat has a chat writer, fixed by its id prefix:
  - kt- is GLM in k1e;
  - kh- is GLM in k1h-glm2;
  - kl- is Luna, and those rows also carry "chat_writer": "luna".
  Gates 1 and 2 are also reported split by chat writer. That split is report only
  (claude_k1h_luna.py split).

## The route (fixed now)
- Helper: scripts/claude_luna_codex.py (the Director's, 24ca7a163).
  - sha256 342a0fb7e15ebf22da763c21eddecb0c58cfcbd43c74481d8421b5709023024e.
  - Model gpt-6-luna.
  - Its live selftest passed on the Mac (runs/000-luna-helper-selftest on builder-outbox: "selftest ok", 3 calls at
    once in 10.9 s).
  - Each try runs `codex exec` in a fresh, empty temp folder with a read-only sandbox. No key is handled.
- Wrapper: scripts/claude_k1h_luna.py.
  - sha256 bcc214d1737ef8368ba0d8c2e6a12ef9a533aed7215231652255286cedc7683c.
  - Selftest: "k1h luna selftest 8/8 ok", with no network. It was also run end to end against a fake codex binary: 40
    ok rows; then 40 refused calls, which gave 120 errlike tries and 40 empty rows with no reply text in the log or the
    rows; then 2 chat calls, renamed kl-p0001 and on.
  - The sealed claude_k1h_glm.py runs unchanged through it, so the prompts, parsing, resume, failure stop and outputs
    are the same.
  - Rows record model "gpt-6-luna".
  - The timeout for each try is 300 s for an answer and 600 s for a 20-chat call. The helper makes up to 3 tries.
  - It logs one line per try: the time, the seconds, a kind (ok, timeout, exit, errlike, capped, raised or other), an
    exit code and the prompt's length. The log never holds prompt, reply or error text.
  - --cap-minutes is required. After the cap, no new try starts.
- Codex error markers: the helper's looks_like_error (the Thread manager asked that these be cited here). A reply
  counts as a failed try if it is empty, or if it is 400 characters or fewer and matches (case-insensitive):
  `usage limit|rate limit|quota|insufficient|unauthori[sz]ed|not logged in|please log ?in|authentication|error:|exceeded|temporarily unavailable|model .{0,40}not (found|supported|available)|stream disconnected`
  - After 3 failed tries the helper raises. claude_k1h_glm then writes an empty row that holds only the error's type
    ("RuntimeError"). The helper's message is never logged.
  - An empty row is a route loss, not a grade. A later resume asks the item again.
- Known cost of these markers: a real short answer that contains one of these words (for example "exceeded" or
  "insufficient") is refused as well and becomes a route loss. The per-try log's errlike count gives an upper bound on
  such losses.
- ADDENDUM-4's route filter (scripts/claude_k1h_routefilter.py, unchanged) still runs on every answers file before
  check.
- Calls at once: 1 in the pilot (the Thread manager). In the full run, the Director decides, and the wrapper allows at
  most 4 (claude_k1h_glm's own limit).
- Mac job agents stop any single shell command after 80 minutes, so every Luna command is capped to end well inside
  that.

## Pilot first (fixed now, before any Luna call)
- Items: artifacts/claude-k1h-20260926/luna/pilot_items.jsonl.
  - sha256 1cc00ffff46cea57ddaa3407bd8cba15238aaf4f93da471c66beba7e1e05a294.
  - 40 of the 240 k1e practice chats: 29 idea and 11 uses_facts, first kt-164, last kt-130.
  - Chosen by `claude_k1h_luna.py pilot-items` with seed 4614 (sort the ids, shuffle, take the first 40).
  - They are practice chats, not test items.
- Answers: `answer --items pilot_items.jsonl --workers 1 --cap-minutes 45`, then the route filter.
- P1, route: at least 36 of the 40 items have a non-empty answer after the route filter (`pilot-packet`).
- P2, code filters: at least 34 of the 40 answers are kept by the build's trim and guard333d
  (claude_k1h_train.filter_reason, via `pilot-packet`).
  - Change from the draft: the draft said "as in check". Check also drops a chat that is a near-copy of a DEV chat, and
    it does this before it looks at the answer.
  - One of these 40 chats is such a near-copy. I counted this before any answer existed.
  - So P2 applies the answer filters to all 40, and check's own counts on the pilot are reported beside it.
  - The full run still uses check as sealed.
- P3, blind check:
  - Judges: two blind Opus judges in private folders, and judge 3 on the lines they split on. They use JUDGE-k1f.md's
    words and line format.
  - What they judge: every answer that is non-empty after the route filter, whether or not the code filters kept it.
    The packet is shuffled with seed 4615 under ids L0000 and on (`pilot-packet`), and scored by `pilot-score`.
  - An item with no answer counts as not useful.
  - Pass: useful on at least 32 of 40, and at most 2 of 40 with made_up_user_facts of 1 or more. These are gate 2's
    proportions.
  - The verdicts decide pass or fail only. No answer is kept, dropped or labelled because of a judge. The Thread
    manager, 03:52 UTC: "P3's Opus judges on a data pilot are allowed as pass/fail only".
- Gate 1 on the pilot's answers is reported, not used as a bar.
- The answer pilot passes only if P1, P2 and P3 all pass.
- Chat pilot, run in the same job. Why now, and not only "if chats are needed":
  - run_chats writes chats.jsonl only when all of its calls have ended (claude_k1h_glm.py, the write after the call
    loop).
  - k1h-glm2's chat step had 11 of its 36 calls done at 23:33 UTC. The limit hit at about 00:57 UTC.
  - So the salvage is likely to bring back no GLM chats.
  - The run: `chats --existing <k1e items> --calls 2 --chunk p --workers 1 --cap-minutes 20`.
  - Pass: at least 30 of the 40 chats asked for are kept by run_chats' own checks (parse, recipe, not a repeat).
  - Pilot chats are not used for training; the full run writes its own.
- Any fail means no full Luna run. I report the counts to the Thread manager, and the next step is written down before
  any run.
- Pilot answers are part of the full data: the full run starts from the pilot's answers.jsonl and skips those items,
  because they are practice answers from the same prompt.

## Full run, only after the pilot passes
1. Chats. Let n_kh be the number of GLM k1h-glm2 chats the salvage brings back (0 if none).
   - Luna writes max(0, 36 - floor(n_kh / 20)) calls of 20 chats. That is the sealed 36 calls less what GLM already
     wrote.
   - The calls run in chunks of at most 12 (--chunk a, b, c), each with --cap-minutes 50.
   - Each chunk's --existing is the k1e items, the GLM k1h chats and the earlier Luna chunks, so no request repeats.
2. Answers. Luna answers every chat: k1e, GLM k1h and Luna.
   - The output folder starts from the pilot's answers.jsonl.
   - Chunks run with --cap-minutes 60, resuming each time, until every item has a non-empty answer or 6 chunks have
     run.
3. Then, as sealed: the route filter; `claude_k1h_train.py check` (the code filters, gate 1 and the DEV near-copy
   drop); gate 2 (60 kept answers, seed 4611, blind judges); gate 3 (size of at least 600, and no near-copy of a
   k1fpanel item, checked by a blind agent). Next come `claude_k1h_luna.py split` (gates 1 and 2 by chat writer, report
   only), and then training and the H arm exactly as sealed.
4. If fewer than 600 answers are kept, the size floor is not met, and I report to the Thread manager before anything
   else runs.

## Scope, updated
A k1h PASS would mean this: teaching the LFM writer from Luna's answers makes its creative replies more useful than
the plain LFM writer's on this panel. The chats come from GLM and Luna, and the split report says how many of each.
Otherwise ADDENDUM-1's scope stands: this is a finding about LFM on 0.2c's build, not a 0.2d part.

## What does not change
- The writer model and both prompts.
- The parsing and the code filters in check.
- Gates 1 to 3 (DATA-GATE-k1h.md) and the size floor.
- The training recipe, the arms, the panel, the marks and the scope (ADDENDUM-1 to 4).
