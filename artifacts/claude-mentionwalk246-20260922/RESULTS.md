# Exp 246 RESULTS: mention-guided walk fallback (cause A)

**Result: FAIL.** The one registered mark that failed is M1a: the compose family got 10/16 right, and the bar was 15/16.
Every safety mark held: 0 wrong values added, 0 question writes, 12/12 controls unchanged, no other
family lost an item, and there were 0 new direction leaks. Dev, the frozen suites and the sleep smoke all passed exactly as
predicted. Seal: artifacts/claude-mentionwalk246-20260922/SEAL.sha256.txt (6/6 OK after all runs;
no file was edited after the seal). The 228 guard was installed: SrcGuardMixin228 comes first in Loop246Daemon, and install_srcguard228() runs at import.

## Marks (registered runs, each once)
| mark | result | count |
|---|---|---|
| M1a compose right | **FAIL** | 10/16 (bar >= 15/16) |
| M1b wrong values, as sealed | PASS | 0 (base228's own direction leaks listed, not counted) |
| M1b split (director ruling) | - | inherited 6 (q243-085..090, my reply byte-identical to base228), ADDED 0 |
| M1c question writes | PASS | 0/124 |
| M1d control byte-identical | PASS | 12/12 |
| M1e other families / untaught / direction | PASS | 0 losses; untaught 10/10; 0 new leaks |
| M1f combo (no bar) | - | 0/8 right, 0 wrong values (all 8 unchanged declines) |
| M2 dev | PASS | cause 30/30, keep 14/14, trap 12/12, 0 writes |
| M3 frozen suites | PASS | GATE clean; moves = rt143 P1, P2, Q1, Q2 (MISSED -> OK), exactly as predicted; rt136 0, sessions152 0, bench 0 |
| M4 sleep smoke | PASS | sleeps 1, installed 1, probes 5/5, wrong 0, taught 50/50, ow 0, 82.8 s |
| M5 added time | PASS | median -0.89 ms per question (mine 5.87 ms, base 7.20 ms) |

Other families (ANSWER, right/total, mine = base228): no_apos 0/16, whats 0/12, first_person 0/12,
verb_subject 0/12, my_relation 0/16. The same-session base228 rerun matched base228.jsonl on 124/124 items.

## Every panel move (10 items, all compose, all decline -> right)
q243-001 "Who is Kydora married to?", 002 "Who's Vudix married to?", 003 "Who is the spouse of Dorna?",
004 "To whom is Zethin married?", 005 "Whom is Nuvith married to?", 007 "who is Mernix married to?",
011 "What country is Gelva a citizen of?", 012 "Which country is Muskix a citizen of?",
014 "Who employs Vrindett?", 016 "Who is Helva Zaeskel married to?". No other item changed.

## Compose misses (6), one-line diagnosis each
- q243-006 "Who is Hamar married with?": the walk found the spouse, but "with" is not in the leftover function-word list (I kept it out on purpose, as the "work with" trap guard), so it declined.
- q243-015 "What company employs Zaeth?": the leftover word "company" is not in the function-word list, so it declined.
- q243-008 "Who is Pyrvin's husband?", 009 "...Thaetora's wife?", 010 "...Juskund's partner?",
  013 "What is Laskyn's nationality?": the base's possessive reader already claims these and replies
  "I don't know X's husband". That is a claimed missing-fact reply, not a "didn't understand" miss, so by design
  my fallback never runs. Fixing these needs a relation-alias change on the possessive reader
  (husband/wife/partner -> spouse, nationality -> country_of_citizenship), which is a different change from this one.

## Dev and suite moves
Dev: exactly the 30 cause items moved (decline -> answer). All 14 keep items were byte-identical. All 12 traps, including the
"found", "work with", "work for", "employ" direction, passive "employed by" and "Spellman" substring traps, stayed value-free.
Suites: rt143 P1, P2, Q1, Q2 only.

## Deviations
- Pilot change before the seal: a first version walked several hops, and it made rt143 S1 and S5 answer where the suite expects an abstain.
  So the sealed walk takes one hop only and has a 2-cycle guard (this is in PASSMARKS).
- Before the seal I relabelled four dev items (d246-007, 008, 030, 032) from cause to keep because the base already
  answered them. I also added a dev-only "echo" rule: a stored value that the question itself names is not a leak.
- My first registered dev command failed at the shell ("command not found": a zsh variable held the
  whole command). Nothing ran and no rows were written. I then ran the same command written out in full, once.
- M1b is reported as sealed. On the director's ruling I also give the inherited/added split: the 6 inherited leaks are
  base228's own direction leaks, and my replies on those items are byte-identical to base228.

## What it means
When a person has more than one fact saved, Premonition can now answer "Who is X married to?",
"What country is X a citizen of?", "Who employs X?" and similar one-step questions. Before, it said "I don't know"
to them. The change never gave a wrong value and never saved anything from a question. It changed no other kind of question.
It also stayed honest on the tricky wordings ("Who does X employ?", "Who does X work with?").

## What it doesn't mean
It did not reach the 90% bar on the blind panel. Six compose wordings still decline: "married with", "What company
employs", and the possessive "X's husband/wife/partner/nationality". It handles only one-step questions. Two-step
questions about a person who has several facts still decline. The panel and dev cases use made-up names and a small
set of wordings, so these counts show which walls are gone, not how often real users will get an answer.
