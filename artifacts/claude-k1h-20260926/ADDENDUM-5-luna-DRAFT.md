# k1h ADDENDUM 5 (DRAFT, not sealed): Luna writes k1h's answers (Creative answers in chat thread, drafted 2026-09-27 03:50 UTC)

DRAFT for the Thread manager's review before sealing. No Luna call has been made and no k1h-glm2 output has been read.
It will be sealed together with the Luna wrapper and the Director's Luna helper (by sha) once that helper exists. It
changes the teacher and nothing that is marked: the marks, arms, panel, recipe, gates 1 to 3, the size floor and
ADDENDUM-4's route-loss rule stay as sealed. Registered FAILs stay FAILs.

## Why
- Ben's opencode Go plan hit its usage limit at about 00:57 UTC (the Director, 03:06), so the GLM route that k1h's data
  was using is blocked with no known reset time.
- Ben, 03:47 UTC, card cmsg_01FuvegZXjMmeUzStiEFVnEWXB5YaHqBJfNGxiQTxBNbz6: "Allow Luna" (GPT-6 Luna through his Codex
  plan may write training data). Then, at 03:47:41 UTC (cmsg_01FuvegZXjMmeUzStiEFVnEWDj4nGsmBa5Vwmx8geQnSH6): "just have
  luna rewrite all the training data. It's so so cheap". Recorded on the goals page (cd475e141, 5ed7dcad9). A sealed
  experiment switches only with a written addendum and a small quality pilot first.

## The change: every training answer (target) comes from Luna
- Luna answers all of k1h's practice chats, including the 240 k1e chats that GLM already answered. One teacher for all
  targets, so a result reads "taught from Luna's answers" and not a mix of two teachers' styles. Gate 1 (no fixed
  frame) also then checks one teacher's habits.
- GLM's 240 answers (k1h-glm2 step 4) are kept on file, not deleted and not trained on. This follows Ben's "rewrite all
  the training data" and differs from the Thread manager's 03:48 note ("Keep the 240 GLM practice answers"). If the
  Thread manager wants them kept in training instead, say so before this is sealed, and the scope line below will
  change to "GLM's and Luna's answers".
- Chats (the inputs) stay as written: the 240 k1e chats (GLM-written in k1e) plus the new chats GLM wrote in k1h-glm2,
  if the salvage brings a chats.jsonl back. Inputs written by GLM are kept, not redone (the goals page, 03:48). If fewer
  than 600 answers can be kept, Luna writes more chats with the same instructions (claude_k1h_glm.py's T.WRITE words, the
  same 12 areas) until the size floor can be met, up to 36 calls.
- Same prompts, parsing, resume and outputs: the sealed claude_k1h_glm.py runs unchanged through a new wrapper
  (scripts/claude_k1h_luna.py, written after the Director's helper lands). The wrapper swaps only the call function,
  records Luna's model id in each row's "model" field, requires --cap-minutes, and logs one line per call (time,
  seconds, ok or failure kind, prompt length; no text), as wrapper v1.2 does.
- ADDENDUM-4's route filter runs on Luna's answers before check. Its markers name opencode's errors; if the Director's
  helper shows Codex error text, markers for it are added in the sealed version, before any answer is read.

## Pilot first (fixed now, before any Luna call)
- Items: 40 of the 240 k1e practice chats, chosen with seed 4614 (shuffle the sorted item ids, take the first 40).
  They are practice chats, not test items. Luna answers them through the new wrapper, then the route filter runs.
- P1, route: at least 36 of 40 answers are non-empty after the route filter.
- P2, code filters (the build's trim and guard333d, as in check): at least 34 of 40 are kept.
- P3, blind check: two blind Opus judges (private folders, JUDGE-k1f.md's words and line format, judge 3 on the lines
  they split on) judge every pilot answer that is non-empty after the route filter, whether the code filters kept it or
  not; an empty answer counts as not useful. Pass: useful on at least 32 of 40, and at most 2 of 40 with
  made_up_user_facts >= 1 (gate 2's proportions, 48 of 60 and 3 of 60). As in gate 2, the verdicts decide pass or
  fail only; no answer is kept or dropped because of a judge.
- Gate 1 on 40 answers is reported, not a bar (too few answers for the 2% sentence bar).
- Only if Luna must write chats: 2 chat-writing calls, pass when at least 30 of the 40 chats parse and pass
  run_chats' checks.
- Any fail: no full Luna run. I report the counts to the Thread manager, and the next step is written before any run.
- Pilot answers are part of the full data (the full run resumes and skips them), because they are practice answers
  from the same prompt.

## Full run, then the gates as sealed
Luna answers every practice chat, then the route filter, then claude_k1h_train.py check (the code filters, gate 1,
DEV near-copy), gate 2 (60 kept answers, seed 4611, blind judges), gate 3 (size >= 600; no near-copy of a k1fpanel
item, by a blind agent). Then training and the H arm exactly as sealed.

## Scope, updated
A k1h PASS would mean: teaching the LFM writer from Luna's answers makes its creative replies more useful than the
plain LFM writer on this panel. ADDENDUM-1's scope otherwise stands: a finding about LFM on 0.2c's build, not a 0.2d
part.

## Still to fill in before sealing
The Luna helper's file and sha (the Director's), Luna's model id, the per-call timeout and the number of calls at once
(the Director's Codex budget), the wrapper's sha and its selftest line, any Codex error markers for the route filter,
and the caps in minutes for the pilot and the full run.
