# Brief: more model-shape ideas from online research (DESIGN ONLY)

Ben (13:29 UTC 10-03): "Look up online and come up with some more ideas for model shape."

Rules: read-only research. No training, tests, GPU, or repo edits. Do not call any mcp__hearthbot__ tools. Write ONLY to the output file named in your task.

## Read first
- /home/user/learner/design/next-parts/critical-thinking-reasoner-design.md (the current plan; do not re-propose what it already has: draft-answer registers, random-depth training, multi-start voting, plan head for operation choice, self-check pass, ordered notebook with role+modality ids, MoE held at 8 experts during skills phase).
- /home/user/learner/design/research/2026-09-28-reasoner-idea-harvest-r1-r5.md lines 1-40 (forbidden-to-re-propose list, e.g. fast weights / Hebbian), and skim design/research/lead-sweep-2026-09-29/SYNTHESIS.md so you don't repeat old ideas without saying so.

## Our model today (shown in code)
Frozen LFM2.5-1.2B LM. Reader: static LM word vectors -> 32 -> 256 per token. Core: ~9M stored / ~2.7M active, 2 shared width-256 attention blocks with 8-expert top-2 MoE MLPs, looped (4 rounds in training on the English path, random 1-16 on the puzzle path). Output: 8 prefix vectors into the frozen LM. Talker must stay thin; the reasoner does everything.

## Goals the shape must serve
- Most critical thinking per parameter: beat bigger plain models at the same size, and keep the edge as it scales (D=256/384/512 ladder).
- Skills first, facts later (facts arrive through a notebook / lookup, not baked into weights).
- After training, learn a new thing from a few examples.
- Modality-agnostic input (vision and audio threads plug in vectors). North star: play Minecraft from screen + keyboard/mouse, reading guides online (long horizon, closed loop).

## What to deliver (to your output file, under ~1500 words)
Up to 6 ideas. For each:
1. Name and one-line description.
2. Source: paper title, year, arXiv id or URL that you actually opened (say "abstract only" if that's all you read). Do not cite from memory without marking it.
3. Evidence label: shown (in that paper, with the number and setting) / suggested / untested for us.
4. How it maps onto OUR core (what changes, rough parameter cost).
5. Cheapest single-change test on our setup, a pass mark fixed in advance, and the result that would prove it wrong.
6. Risk or conflict with Ben's rules (thin talker, forbidden list, no fact-baking).
End with your top 2 and why. Plain language.
