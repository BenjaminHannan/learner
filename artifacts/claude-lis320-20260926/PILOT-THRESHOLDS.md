# lis-320 GLM pilot: what changes the plan (fixed before the pilot result exists)

Written 2026-09-26 17:01 UTC by the reading thread. At this time no pilot output exists on either branch.
DEV reference (claude_lis320_style.py on the everyday-chat DEV chats, 336 turns): lowercase start 1.0, apostrophe-less
contraction 0.253, turns over 20 words 0.131, words median 14 / p90 23, distinct shapes 99.1 per 100.

Any one of these changes the GLM instruction or the checks before the full run (and the pilot is re-run on new seeds):
1. Code-check pass rate under 60% of turns, or any single intent family under 40%.
2. Lowercase-start rate under 0.5, apostrophe-less contraction rate under 0.12, or share of turns over 20 words under 0.06
   (half the DEV rates): the wording is too clean or too short, so the messiness/length part of the instruction changes.
3. Distinct shapes under 90 per 100 turns: too templated.
4. Write facts sitting in turns over 20 words under 5%: facts are never buried in longer messages.
5. A look at 20 kept and 20 dropped rows (GLM text, not Claude text, may be read): more than 2 of the 20 kept rows whose code
   label is wrong (an extra unlabelled fact, a wrong owner, or a stated-as-true value on a lookalike) tightens the checks or
   adds the blind GLM re-read (plan step 4).
6. Cost over $5 per 1,000 kept rows: batching or a cheaper call is considered first, and anything over budget goes to Ben via the Thread manager.
If none trigger, the full run uses the same prompt and checks, on new seeds, with names from the test panels added to the avoid list by
a counts-only script.
