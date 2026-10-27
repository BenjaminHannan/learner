# Exp 245 RESULTS: "my <relation>" as a question subject

**Result: PASS on every registered mark, as sealed.** On the blind ask panel 243, my_relation
went from 0/16 right (base228) to 15/16 right. There were 0 question writes, 0 added wrong values,
control stayed 12/12 byte-identical, and no other family moved. Suites showed 0 moves, sleep smoke
matched 138i, and the median added time was +0.03 ms per question. Each run was done once. The 228 guard
was installed (SrcGuardMixin228 first in the daemon bases, install_srcguard228() at import).

## Marks
| mark | bar | result | verdict |
|---|---|---|---|
| M1a my_relation right | >= 15/16 | 15/16 (base 0/16) | PASS |
| M1b wrong values, 124 items (as sealed: base228's own direction leaks listed, not counted) | 0 | 0 counted; raw 6, all inherited (see split) | PASS |
| M1c question writes | 0/124 | 0/124 | PASS |
| M1d control byte-identical | 12/12 | 12/12 | PASS |
| M1e other-family regressions / untaught no value / new direction leaks | 0 / 10/10 / 0 | 0 / 10/10 / 0 | PASS |
| M1f combo (no bar) | - | 0/8 right, 0 wrong values, all 8 byte-identical to base228 | - |
| M2 dev fix / keep / trap / writes | 34/34, 10/10, 9/9, 0 | 34/34, 10/10, 9/9, 0 | PASS |
| M3 suites vs 138i (predicted: 0 moves) | GATE clean, moves = predicted | GATE clean; rt136 0, rt143 0, sessions152 0, bench 0 moves | PASS |
| M4 sleep smoke | 138i marks | sleeps 1, installed 1, probes 5/5, wrong 0, taught 50/50, ow 0, 83.6 s | PASS |
| M5 median added ms/question | <= +5 | +0.03 (base 5.59 ms, 245 5.60 ms) | PASS |

**M1b split (director ruling 2026-09-22).** Raw wrong values over 124 items: 6 items, all on
direction q243-085..090 (for example "Who does Brylto employ?" -> "Brylto's employer is Gedund.").
**Inherited: 6** (245's reply is byte-identical to base228's base_reply). **Added: 0.**
The base228 arm in this session reproduced base228.jsonl base_reply on 124/124 items.

## Every move
Panel (15 changed replies, all my_relation, all decline -> right, 0 wrong values):
069 "Where does my sister live?" -> "Ditund's city is Grokek." · 070 "Who is my boss married
to?" -> "Jilvan's spouse is Stanyn." · 071 "Where does my brother work?" -> "Jadora's employer is
Denin." · 072 "Who does my brother work for?" -> "Thultan's employer is Yaembin." · 073 "What's
my sister's city?" -> "Quaele's city is Brixek." · 074 "Where was my mother born?" -> "Kerkett's
place of birth is Nigar." · 075 "What city does my friend live in?" -> "Peltyn's city is Vryrve."
· 076 "Who employs my father?" -> "Vraentel's employer is Rylvek." · 077 "What country is my
cousin a citizen of?" -> "Taethel's country of citizenship is Kraegek." · 078 "Who is the spouse
of my boss?" -> "Tharvith's spouse is Pithek." · 079 "Where does my doctor live?" -> "Trukek's
city is Kaeskyn." · 080 "Who's my sister married to?" -> "Faerkix's spouse is Nuga." · 081
"What's my friend's pet?" -> "Drothar's pet is Kraelow." · 082 "Who does my sister work for?" ->
"Traeltow's employer is Gyzyn." · 083 "Where does my neighbor live?" -> "Gantett's city is
Zyrvett." The other 109 items were byte-identical to base228.jsonl.

**Miss (1):** q243-084 "Who is my uncle's wife?" (setup: "Yaethar is married to Guthett.") ->
"I don't know Yaethar's wife." It is unchanged from base. Me166 already claims this form, so 245 leaves it alone by design, and
the notebook stores "spouse", not "wife". Answering it needs a wife-to-spouse synonym, which the brief ruled out.

Dev (m2-dev-score.txt): 34 fix cases moved from decline/garbled to right; 10 keep cases identical; 9
traps gave no stored value (for example "What's my sister's job?" -> "I don't know your sister's job
yet.", "Where does my brother live?" with no brother -> "I don't know who your brother is.").
Suites: 0 moves. Sleep smoke: no change.

## Deviations
- Before the seal, one dev case was repaired. "My coach is Tarn Hollis." is refused by the base
  teach (office head), so the coach question became trap t09 and a neighbor case replaced f32.
  This is recorded in PASSMARKS.
- Besides the two named code files, the runner (scripts/claude_run245.py) and scorer
  (scripts/claude_score245.py) are new files. Both were sealed.
- On its own path only, the mixin drops a leading greeting/"please" and a trailing ", please" before
  probing, because the base reads no greeting on any question. This is declared in the sealed design note. None of the
  panel's 15 moves needed it.
- The declines use the Me166 wording "I don't know your <relation>'s <asked> yet." when the
  relative is stored but the fact is not. The brief's "I don't know who your <relation> is." is
  used when no such relative is stored. The declared behaviour for 2+ relatives is one answer per person.
  The panel had no 2+ relative item, so that behaviour is tested on dev only (f27, f28).
- No re-runs. No file changed after the seal (the seal checked OK before the panel run).

## What it means
When you ask about "my sister", "my boss" and so on in the ways people usually talk ("Where does my
sister live?", "What's my friend's pet?", "Who is my boss married to?"), the assistant now
looks up who that person is in its notebook and answers the question about them. Before this fix, it
said it didn't know anyone called "my sister". On this panel it got 15 of 16 right. It
changed nothing else, wrote nothing on questions, and added no measurable time.

## What it doesn't mean
It doesn't mean every "my" question works. "Who is my uncle's wife?" still fails when the fact was
taught as "married to", because the notebook calls that "spouse" and no synonym was added. Questions
with no base reader even when the real name is used ("What does my uncle do?", "Can you tell me where
my sister lives?") still decline, and so does "married to" when the relative has several facts (cause A,
another builder's fix). The combo items ("whats my sister's city?", "my sisters") are still 0/8
until the other fixes merge. The panel's 16 items are a small, fictional-name sample, and the
several-relatives behaviour was checked only on dev.
