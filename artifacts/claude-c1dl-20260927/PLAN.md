# c1-dl: does 0.2d's talker input cost LFM2.5-1.2B anything? (Everyday chat thread, plan written 2026-09-27T17:29:18Z)

Asked by the Thread manager (17:22 UTC 09-27) after c1-dev (artifacts/claude-c1dev-20260927/RESULTS.md): with MiniCPM5-1B
as the talker, 0.2d's talker path was level with plain MiniCPM (27-26) but lost to Qwen3.5-2B 3-57 and to LFM2.5-1.2B 0-60.
This is evidence for a possible talker swap. The swap itself is an architecture change and needs Ben's yes; this test
changes nothing in the build. Report only, on the DEV practice chats (artifacts/claude-chatdev-20260926, 60 conversations,
336 turns), never on chatpanel404.

## The one change

Arm DL is c1-dev's arm D command, unchanged (scripts/claude_c1dev_talker.py build_talker02d = claude_e2e02d.Agent02d's
talker with no reader and no reasoner, code tree 62a5944c8, SEAL-2 24/24), with --gen-model set to the pinned
LFM2.5-1.2B-Instruct snapshot (revision 0f604ada3f766f9f257460c4c9f0b5d6f69d431b) that c1-dev's arm L ran, in place of
MiniCPM5-1B. No code change and no new model.

- LFM takes the W block the way claude_e2e02d does: the Talker sends [system, chat...] to apply_chat_template, and LFM's
  pinned chat_template.jinja puts messages[0] with role system into its own "<|im_start|>system" block. The plain L
  twin already ran with a system message (claude_e2e336_twinb.py:26).
- Against arm L (plain LFM twin) the only difference is the W block in the system message. Every DEV chat has at most 6
  turns, so the talker's 6-exchange window never cuts, and both use greedy decoding, 160 new tokens, thinking off and the
  same "\nUser:" cut (claude_e2e336_twin.py:70, claude_e2e02d.py Talker.reply).
- Rivals: c1-dev's committed chat_T, chat_Q and chat_L (5a34cce3d, sha256 in c1-dev's RESULTS-vast.md). They are not re-run.
- T, Q and L are reused chats from 5a34cce3d, generated on a different card (c1-dev's RTX 4090); greedy decoding can differ
  slightly across GPUs. DL is new. (Thread manager, 17:24 UTC 09-27.)

## Run and scoring (fixed now)

- Kit handoff/kit/c1dlv on one vast card (copied from c1-dev's kit; DL only; downloads only the LFM snapshot). Money stop
  $1.00, task cap $1.50, inside Ben's $4 per job; estimate about 30 min on a 4090.
- `python3 -B scripts/claude_c1rival_run.py score --panel-dir artifacts/claude-chatdev-20260926 --out S --build DL` with S
  holding chat_DL and c1-dev's chat_T, chat_Q, chat_L. The sealed scorer pairs DL with T, Q and L (seeds 4061-4063,
  packets of 15), so this is C1's whole row with an LFM talker.
- 12 blind judges, one per packet, with c1-dev's judge brief; `marks --bar -12`; a blind recount from the keys and the
  judge outputs only; `scripts/claude_c1dev_noise.py --marks S/marksC1.json --bar -12`.

## Marks (bar: margin = DL wins - rival wins >= -12 of 60)

- RL, the question: margin(DL vs L) >= -12 reads "the W block costs LFM nothing large". Proved wrong if it is below -12.
- RT: margin(DL vs T) >= -12.
- RQ: margin(DL vs Q) >= -12.
- "C1's bar met with an LFM talker on the practice chats" only if RL, RT and RQ all hold; otherwise "not met against
  <each rival that fails>".
- Next to every margin, as in c1-dev: decisive conversations, the sign-test p, DL's share with its 95% interval, the range
  an equal pair lands in, and the reading (behind <= -14, ahead >= +14, else level).
- Also reported, no mark: made-up-about-the-user flags per pair (L had 3 against D's 24 in c1-dev), ask_known right of 8
  (L 4), "I don't know" on the 6 ask_unknown turns, median words, median ms per turn.

## Prediction (written before any DL reply exists)

RL holds with DL level with L. RT holds with DL ahead of T (margin >= +14). RQ holds. Basis: in c1-dev plain LFM beat
0.2d's MiniCPM talker 60-0 and Qwen beat it 57-3, while that talker was level with plain MiniCPM, so the W block did
not cost MiniCPM much. The prediction is proved wrong if any of the three margins is below -12.

## What this cannot show

A pass is evidence only. Swapping the talker is Ben's decision (design/v3/30-modes/ben-goals-2026-09-26.md:96).
An equal pair lands within about ±16 of 60, so the -12 bar can show only that the cost is not large, never that there
is none. One seed of generation, one judge model, DEV chats only. DL is the talker alone (no reader, no reasoner, SLEEP02D
off), not 0.2d. LFM's replies are shorter (c1-dev median 44.5 words on advice turns against D's 119); the judges see
length, so a win can partly be a length preference.
