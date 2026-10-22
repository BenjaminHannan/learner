# Shared brief: reasoner architecture for maximum critical thinking (DESIGN ONLY)

Repo: /home/user/learner (branch claude/project-thread-knhc46). Read-only research. Do NOT run training, tests, GPU jobs, or edit repo files. Write your output ONLY to the file path given in your task. Do not call any mcp__hearthbot__ tools.

## Ben's request
"Design an architecture that would squeeze out the most critical thinking skills out of our reasoning model." Philosophy (Ben): pretrain the model for SKILLS and the strongest possible critical thinking first; facts are baked in later (unlike a traditional LLM). After all training it should generalise well enough to learn a new thing from just a few examples. Idea: teach the core English first, then teach it how to work through questions (staged curriculum).

## Current system (facts, check them in code)
- Frozen LFM2.5-1.2B LM (borrowed parts OK this phase), a contextual reader, a ~9M latent reasoner core looped 4 times, 8 prefix vectors back into the LM. The LM never sees the question text on the output side: the output path is 256+3 -> 32 -> 8 prefix vectors (scripts/sol_translator_english_v6.py:15-46, 83-95). The reader squeezes frozen LM embeddings through a 32-wide layer (scripts/sol_translator_grounding_v6.py:46-50).
- Ben's rule: talker/translator is thin both ways; the reasoner does everything. Sparse MoE + many layers approved earlier (09-29). Scaling width/experts/reader/loops needs no approval; the "no extra reasoning depth" rule is removed; a larger checked TRAIN set may be authored.
- Earlier history in repo: design/research/ (reasoner-idea-harvest r1-r5, huginn plan, moe plan, lead-sweep synthesis), ARCHITECTURE_DECISION.md (older depth-recurrent transformer + delta-rule memory), design/v3, design/pilots.
- The calculator/tool code and saved outputs live only on Ben's Mac, not in this repo. Do not assume you can read them.

## Evidence so far (brainstorm thread)
- Fresh-question panel of 128: 86/128 had the right calculator setup, only 15/128 the right final answer. Breakdown: 71 right call but wrong final answer, 38 picked the wrong operation. Core was trained on only 32 practice problems (all 32 fit).
- Memorising is SUGGESTED, not proven. Squeeze loss at the 32-wide reader/prefix bottleneck is also plausible and untested.

## Ground rules for the output
- Label EVERY claim shown / suggested / untested ("shown" = measured in this repo or cited result you checked; "suggested" = literature or reasoning; "untested" = our guess).
- Keep the small card experiments and the village model separate (do not mix their numbers).
- Propose changes ONE at a time with pass marks fixed in advance and the result that would prove each wrong.
- Judge designs by whether they improve with use and scale up, not today's absolute scores.
- Never touch reserved/consumed eval sets; design fresh eval forms only as descriptions (authoring subagent, independent checker, sealed by hash).
- Verify code/line claims by actually reading the file. Keep output under ~2500 words, plain language, a short section at the end "Plain-language summary for Ben (a high-school senior)".
