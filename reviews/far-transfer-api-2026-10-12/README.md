# Far transfer: outside opinions from Fable 5.1 and Opus 5.5 (12 Oct 2026)

Brief: `reviews/api-far-transfer-2026-10-12.md` on branch `claude/project-thread-94a956` (commit 0e00a7b08), written by the Far transfer thread.
Sent through the normal Anthropic Messages API (streaming, effort xhigh, adaptive thinking with summaries, max_tokens 128,000), one turn, no tools.

| answer | model | returned (ET) | input / output tokens | cost (list prices) |
|---|---|---|---|---|
| far-transfer-fable-2026-10-12.md | claude-fable-5-1 | 9:39 AM | 3,709 / 22,121 | $1.14 |
| far-transfer-opus-2026-10-12.md | claude-opus-5-5 | 9:46 AM | 3,678 / 50,775 | $1.03 |

Total $2.17 of Ben's API credit. Thinking summaries sit next to each answer.

**One change for Opus (disclosed):** Opus 5.5 refused the verbatim brief three times (stop_reason `refusal`, category `cyber`,
a false positive). Bisecting showed the trigger was the sentence telling the model it has no access to our code, files or machine.
Opus got the brief with that sentence replaced by "Everything you need is below; please answer from it directly." and the
title's "(no code or file access needed)" removed (`prompt-as-sent-to-opus.md`). Everything else is byte-identical. Fable got the verbatim brief.

Not judged here: the Far transfer thread checks both answers against the code and reports to Ben.
