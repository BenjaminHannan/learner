# own-O0a ORACLE-COVERAGE CHECK — RESULTS (registered run, 2026-09-23)

## Verdict first

**Pown0a.1 FAIL (67.6% < 85% bar). Pown0a.2 71.0% (report only). Pown0a.3 PASS
(0/76).** Even with a PERFECT reader, the strict v0 write rules let through only
about two thirds of real facts in ordinary chat. No ear training can recover
facts the writer refuses on principle, so the rules must change before any GPU
hour is spent. This is the outcome the PASSMARKS predicted (65–75%).

## Marks table (integer counts)

| Mark | Bar | Got | Result |
|---|---|---|---|
| Pown0a.1 auto-writable share of ASSERT/CORRECT/DENY gold facts, WE not allowed | >= 85% | 184/272 = 67.6% | **FAIL** |
| Pown0a.2 same, WE allowed | report only | 193/272 = 71.0% | report |
| Pown0a.3 writable among no-save-mode (ASK/CHECK/SUPPOSE/PLAN/REPORTED) facts | = 0 | 0/76 | **PASS** |

Fixed denominators (sealed with the data): 300 turns (180 statement, 80 no-save,
40 mixed); 272 ASSERT/CORRECT/DENY gold facts (258 ASSERT + 6 CORRECT + 8 DENY);
76 no-save-mode gold facts (26 ASK + 21 CHECK + 11 SUPPOSE + 10 PLAN + 8 REPORTED).

## Reason table, WE not allowed (88 non-writable of 272)

| Reason | Count | Share of 272 |
|---|---|---|
| no-relation-cue (relation in table, but no name/alias word in the turn) | 58 | 21.3% |
| relation-OTHER (no table entry fits) | 12 | 4.4% |
| WE-owner (WE->ME not allowed) | 10 | 3.7% |
| typo (intended value spelled wrong in the turn) | 5 | 1.8% |
| value-not-span (DENY of an old value not repeated in the turn) | 2 | 0.7% |
| owner-not-span ("toms" for Tom: missing apostrophe) | 1 | 0.4% |
| no-save-mode facts writable | 0 of 76 | 0% |

WE allowed: 193/272 = 71.0%; non-writable 79 (9 WE facts become writable;
"we live in Fernbrake" moves from WE-owner to no-relation-cue).

What the 58 no-cue facts are: 26 list facts with plural cues ("sisters",
"brothers", "friends", "cats", "dogs", "colleagues", "neighbours" never match
the singular table words); 18 verb facts ("lives in", "works at/for",
"employed by", "studied at", "goes to", "works as", "married to", "mentors",
"founded", "wrote", "manages", "moved to", "grew up in", "was born in",
"speaks", "turned 30"); 8 bare possessives ("Mira's Pip", "belongs to",
"is where Bram ended up"); 3 copula ages with no "age" word ("is 34/50/40");
1 relation-word typo ("broter"); 2 bare corrections ("Fig, not Moss." names no
relation word, so BOTH its CORRECT and DENY facts fail).

## Every non-writable fact (dev turns, quoting allowed)

WE NOT ALLOWED (88). Format: id | reason | owner | relation | value | mode | turn.

no-relation-cue (58):
S086 | Mira sister Mira ASSERT | "Mira and Tal are my sisters."
S086 | Mira→ME sister Tal ASSERT | same turn
S087 | ME sister Mira/Tal/Oona ASSERT x3 | "My sisters are Mira, Tal and Oona."
S088 | ME brother Kwame/Yaw ASSERT x2 | "Kwame and Yaw are my brothers."
S089 | ME brother Kwame/Yaw ASSERT x2 | "My brothers are Kwame and Yaw."
S090 | ME cousin Sanna/Aino ASSERT x2 | "Sanna and Aino are my cousins."
S091 | ME friend Anouk/Lotte/Bram ASSERT x3 | "My friends are Anouk, Lotte and Bram."
S092 | ME uncle Jesper/Petteri ASSERT x2 | "Jesper and Petteri are my uncles."
S093 | ME aunt Saskia/Linnea ASSERT x2 | "My aunts are Saskia and Linnea."
S094 | ME cat Pip/Button ASSERT x2 | "Pip and Button are my cats."
S095 | ME dog Pip/Biscuit ASSERT x2 | "My dogs are Pip and Biscuit."
S096 | ME colleague Daan/Pieter ASSERT x2 | "Daan and Pieter are my colleagues."
S097 | ME neighbour Emil/Daan ASSERT x2 | "My neighbours are Emil and Daan."
S100 | Ingrid age 34 ASSERT | "My teacher, Ingrid, is 34."
S106 | Pieter age 50 ASSERT | "My uncle, Pieter, is 50."
S111 | Ada age 40 ASSERT | "Ada's son is Bo and she is 40."
S120 | Kwame city Accra ASSERT | "Kwame lives in Accra."
S121 | Ama employer "Halden Mills" ASSERT | "Ama works at Halden Mills."
S122 | Efua employer "Brackle & Sons" ASSERT | "Efua works for Brackle & Sons."
S123 | Zola employer "Mintvik Shipyard" ASSERT | "Zola is employed by Mintvik Shipyard."
S124 | Nia educated_at "Koli College" ASSERT | "Nia studied at Koli College."
S125 | Tamati school "Larrow Academy" ASSERT | "Tamati goes to Larrow Academy."
S126 | Aroha occupation nursing ASSERT | "Aroha works in the field of nursing."
S127 | Fenna occupation nurse ASSERT | "Fenna works as a nurse."
S128 | Jeroen spouse Lotte ASSERT | "Jeroen is married to Lotte."
S129 | Daan mentor Saskia ASSERT | "Saskia mentors Daan."
S130 | Cosimo founder "Brackle & Sons" ASSERT | "Cosimo founded Brackle & Sons."
S131 | Renata notable_work "The Saltmeadow Light" ASSERT | "Renata wrote The Saltmeadow Light."
S132 | Kwame boss Aldo ASSERT | "Aldo manages Kwame."
S133 | Bram city Fernbrake ASSERT | "Bram moved to Fernbrake."
S134 | Wren hometown Saltmeadow ASSERT | "Wren grew up in Saltmeadow."
S135 | Holly place_of_birth Owlkirk ASSERT | "Holly was born in Owlkirk."
S136 | Ivy language Dutch ASSERT | "Ivy speaks Dutch at home."
S137 | Ash age 30 ASSERT | "Ash turned 30 last week."
S156 | ME brother Yaw ASSERT | "my broter is Yaw"
S157 | Mira pet Pip ASSERT | "mira's Pip keeps stealing my socks"
S158 | Mira pet Pip ASSERT | "Pip is Mira's, you know"
S159 | Mira pet Pip ASSERT | "that Pip of Mira's is a menace"
S160 | Mira pet Pip ASSERT | "Mira's Pip chewed my shoe again"
S161 | Ada son Bo ASSERT | "Bo is Ada's, the little one with spots"
S162 | Oona pet Fig ASSERT | "Fig belongs to Oona now"
S163 | Aldo car Volvo ASSERT | "the Volvo belongs to Aldo"
S164 | Bram city Rook ASSERT | "Rook is where Bram ended up"
S165 | ME cat Fig CORRECT | "Fig, not Moss."
S165 | ME cat Moss DENY | "Fig, not Moss."

relation-OTHER (12): S138 ME "My star sign is Leo."; S139 Mira "Mira's lucky
number is 7."; S140 Bo "Bo's shoe size is 44."; S141 ME "my wifi password is
badger42"; S142 Tal "Tal's blood type is O negative."; S143 Oona "Oona's
favorite song is Starling Road."; S144 Kwame "Kwame's star sign is Aries.";
S145 Ama "Ama's bus route is the number 12."; S146 Jesper "Jesper's license
plate is Rook 441."; S147 Linnea "Linnea's coffee order is oat latte.";
S148 Sanna "Sanna's wedding song is June Waltz."; S149 Petteri "Petteri's golf
handicap is 18."

typo (5): S150 ME sister "Mira Still" ("my sister is called Mira Stil");
S151 Mira dog Pip ("Mira's dog is called Pippa"); S153 Ada son Bo ("Ada's son
is called Boe"); S154 ME mother Linnea ("my mom is called Linnae");
S155 Kwame city Accra ("Kwame's city is Acrca").
owner-not-span (1): S152 Tom boss Renata ("toms boss is Renata").
value-not-span (2): S166 ME boss Renata DENY ("no, my boss is Tal now" — old
value not repeated); S168 Mira city Larrow DENY ("no, Mira's city is Rook").
WE-owner (10): S173 "our dog is Pip"; S174 "Our boss is Tal."; S175 "our city
is Rook"; S176 "we have a cat called Fig"; S177 x2 "our mom is Linnea and our
dad is Petteri"; S178 "we live in Fernbrake"; S179 "our favorite color is
blue"; S180 "our car is a Volvo"; M014 "Our city is Rook. Have you been?"

## Deviations and choices

- None from the task order: turns+golds written first, sealed (SEAL-data),
  then PASSMARKS + compiler, sealed (SEAL.sha256.txt 4/4 OK after the run),
  then one run, then RESULTS + ledger. No TEST-ONLY panel or
  artifacts/claude-*panel* folder opened; no templates copied; CPU only, no
  model, no downloads; fictional names only; additive only (3 new files:
  artifacts dir, compiler script, ledger lines appended).
- Compiler strictness choices (documented in PASSMARKS before the run):
  case-insensitive exact whole-word matching; possessive splits in
  tokenisation; NO plural/stemming fold; cue = relation name/alias only (verb
  paraphrases and teach-patterns do not count); reason priority
  mode > OTHER > owner > value/typo > WE > cue.
- "Even if" arithmetic (no re-run, sealed script untouched): folding plural
  cues would rescue only the 26 list facts -> 210/272 = 77.2%, still below 85%;
  WE allowed AND plural folding -> 219/272 = 80.5%, still below 85%. The
  conclusion does not hinge on the strictness choices.
- Misses found while listing (reported, not fixed — data is sealed): bare
  corrections and copula ages carry no cue word, so they fail even when stated
  plainly; this widens the gap rather than narrowing it.

## What it means (plain high-school English)

Think of the write rules as a bouncer with a guest list. We gave the bouncer a
perfect photo of every guest (the right answer for all 300 chats). He still
turned away 1 in 3 real facts: people say "sisters" but the list says "sister";
they say "lives in" but the list says "city"; they say "Mira's Pip" without
saying the word "dog"; they mistype a name; they correct with "Fig, not Moss."
without repeating the word "cat". Better glasses (a smarter reader) cannot fix
a bouncer who rejects the right photo. The list itself must change.

## What it doesn't mean

It does NOT mean the ear design is bad, or that small models can't learn these
sentences, or that 85% recall is impossible for the system. It means only this:
UNDER THESE EXACT WRITE RULES, the ceiling is ~68% (71% if "our" counts as
"my"), so the rules — cue matching, OTHER relations, typo handling, bare
corrections — have to be loosened or supplemented before training anything.
