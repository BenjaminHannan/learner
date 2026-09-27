# Exp 255: fixed-reply text pass — results (finishing agent, 2026-09-22)

## Result first

**Registered FAIL on M4.** The sealed scorer's mechanical labels pass (38 changed
replies, 30 "same meaning", 8 pre-flagged, 0 unexplained, 0 store changes), but
the director's ruling is registered and final: the 8 flagged probes (A06, B04,
B05, B20, D02, D03, D04, D08) are WORSE on meaning, because the new decline
opens with "I don't know that.", which is false there (the fact is stored, or
it is the assistant's own name, or the turn was a teach request). So M4 FAILS,
and exp 255 is a registered FAIL.

## Marks table (integer counts)

| Mark | Verdict | Counts |
|---|---|---|
| M1 fixed-text grammar | Graded by the director; see M1-director.md in this folder (written by the director) | fixedtext.jsonl: 232 rows (175 changed-template renders, 57 unchanged), sealed in SEAL2 (verified OK). M1-director.md was not present in this folder at the time of writing; the director grades M1 separately |
| M2 suites vs 138m | PASS (sealed scorer) | Reply-only moves 162 (rt136 48, rt143 42, sessions152 25, bench 43); 0 verdict, 0 status, 0 store, 0 write changes; GATE clean; move list equals the 162 predicted ids exactly. rt143 no-gate: exactly the 45 predicted reply-only moves |
| M3 239 panel runner | Runner done, judging not run because the verdict is already FAIL | 30 conversations, 244 rows, 0 empty, 0 errors. Changes vs 138m: 244 turns compared, 153 changed turns, 0 unexplained, 0 store changes, 0 missing. Paths: artifacts/claude-fixedtext255-20260922/m3-reg/transcripts-255.jsonl, transcripts-255.md, changes-255-vs-138m.jsonl, changes-255-vs-138m.md, changes-255-vs-138m-summary.json |
| M4 verifier probes | FAIL (director ruling) | 38 changed replies: 30 same meaning, 8 flagged "possibly worse, director rules" (probes:A06:t00, B04:t01, B05:t01, B20:t01, D02:t01, D03:t01, D04:t00, D08:t01); 0 worse (unexplained), 0 store changes. Director counts the 8 as worse, so M4 fails on them |
| M5 sleep smoke | PASS (sealed scorer) | Differing fields only: .agent, .config, .label, .seconds; 0 bad fields |
| M6 restart/dialogs | PASS (sealed scorer) | 17 reply changes (exactly the 17 predicted), 0 ghosts, 0 failed duplicate checks, 0 bad writes, both vs 138m saved and vs same-session 138m |
| M7 latency | PASS (sealed scorer) | median 138m 2.693 ms, median 255 2.713 ms, delta +0.019 ms (bar ≤ +2.0 ms); n 624 + 624 |
| S1 identity check | Not applicable | No new scorer version was added; all frozen anchors kept |

Seals: `shasum -a 256 -c` on SEAL.sha256.txt (19 lines) and SEAL2.sha256.txt
(fixedtext.jsonl) — every line OK, exit 0, before any run.

## Every template changed, before (138m) and after (255)

One sample per template (the unit-test sample), as in PASSMARKS.md.

| id | before (138m) | after (255) |
|---|---|---|
| T01_Q1 | I don't know that yet — you haven't told me. | I don't know that yet. You haven't told me. |
| T02_Q2 | I didn't understand that question — could you say it another way? | I don't know that. I may have misread your question, so could you say it another way? |
| T03_S1 | I didn't understand that well enough to save it — could you say it another way? | I didn't understand that well enough to save it. I may have misread it, so could you say it another way? |
| T04_GLUE | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? | I don't know that, and I have no record of it. I may have misread your question, so could you say it another way? |
| T05_F188 | I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee." | I couldn't save that as a fact. I don't know that kind of sentence yet. Could you say it another way? For example: "Kim's boss is Lee." |
| T06_NEG148 | I didn't understand that. I only know current facts and I can't do 'not' -- could you say it without that part? | I didn't understand that. I only know current facts, and I can't handle 'not' yet. Could you say it without that part? |
| T07_TIME148 | I didn't understand that. I only know current facts, not years or 'as of' -- could you say it without that part? | I didn't understand that. I only know current facts, not years or 'as of' dates. Could you say it without that part? |
| T08_SPLIT | I can take one fact at a time — could you split that? | I can take one fact at a time. Could you split that up? |
| T09_UNREAD | I couldn't read that message -- please send it as plain text. | I couldn't read that message. Please send it as plain text. |
| T10_SAYLIKE | Please say it like "Mira's city is Lisbon.". | Please say it like this: "Mira's city is Lisbon." |
| T11_PICK | Please answer with: pick <one of the IDs I listed>. | Please answer with "pick" and one of the IDs I listed. |
| T12_WEBACTOR | That write is not allowed from web. | That write is not allowed from the web. |
| T13_SELFFALLBACK | I do not understand that question. Ask me about what I know, where it came from, or what I am doing. | I do not understand that question. Ask me about what I know, where it came from or what I am doing. |
| T14_GREETING | Hi! Teach me like "Tom's boss is Ann." Ask me like "Who is Tom's boss?" | Hi! I'm Premonition. You can teach me a fact, for example: "Tom's boss is Ann." Then you can ask me about it, for example: "Who is Tom's boss?" |
| T15_187MAKER | Nobody taught me who made me, so I do not know it. I am plain software you are teaching: a notebook, a lookup loop, and fixed rules. | Nobody taught me who made me, so I do not know it. I am plain software you are teaching: a notebook, a lookup loop and fixed rules. |
| T16_187WHAT | I am plain software you are teaching: a notebook, a lookup loop, and fixed rules. I can only tell you what you taught me. | I am plain software you are teaching: a notebook, a lookup loop and fixed rules. I can only tell you what you taught me. |
| T17_187NAME | You never gave me a name, so I do not have one. I am plain software you are teaching: a notebook, a lookup loop, and fixed rules. | You never gave me a name, so I do not have one. I am plain software you are teaching: a notebook, a lookup loop and fixed rules. |
| T18_FEELINGS | I do not have feelings. I am plain software: a notebook, a lookup loop, and fixed rules. | I do not have feelings. I am plain software: a notebook, a lookup loop and fixed rules. |
| T19_CAN | I can: save what you teach me in my notebook; answer questions from my notes, following one or two steps; correct a fact or forget one when you ask; say I do not know instead of guessing; tell you where each fact came from; hold web text in quarantine without believing it. | I can save what you teach me in my notebook. I can answer questions from my notes, following one or two steps. I can correct a fact or forget one when you ask. I can say I do not know instead of guessing. I can tell you where each fact came from. I can hold web text in quarantine without believing it. |
| T20_CANNOT | I cannot: feel feelings or have favourites or opinions; guess, predict the future, or explain why things are so; believe the web on my own; remember anything nobody taught me; know anything from outside our turns, like yesterday; dream. | I cannot feel feelings or have favourites or opinions. I cannot guess, predict the future or explain why things are so. I cannot believe the web on my own. I cannot remember anything nobody taught me. I cannot know anything from outside our turns, like yesterday. I cannot dream. |
| T21_AGETHEIR | You never taught me their age, so I do not know it. | You never taught me that person's age, so I do not know it. |
| T22_SRCTHAT | I'm not sure what "that" means — I haven't just told you a fact. | I'm not sure what "that" means. I haven't just told you a fact. |
| T23_SRCNOTRACK | I can't say where that came from — I didn't keep track of which notes that reply used, so I won't guess. | I can't say where that came from. I didn't keep track of which notes that reply used, so I won't guess. |
| T24_SAYBARE | (I'm treating that as pretend, so I won't save it.) | I'm treating that as pretend, so I won't save it. |
| T25_IDLETHINKING | Right now I am idle, in THINKING mode. I am waiting for your next turn. | Right now I'm idle and thinking, waiting for your next message. |
| T26_WEB0 | No. I hold 0 web rows. | No. I don't hold any web rows. |
| T27_SLEPT0 | No. I have slept 0 times. | No. I haven't slept yet. |
| T28_CORRECTED0 | You corrected: . | You haven't corrected anything yet. |
| T29_PEOPLE0 | I know 0 people: . | I know no one yet. |
| T30_MODE | Right now I am back in LISTENING mode, waiting for your next turn. | Right now I'm listening, ready for your next message. |
| T31_SAYECHO | my name. (I'm treating that as pretend, so I won't save it.) | Okay, I'll say it: "My name." I'm treating that as pretend, so I won't save it. |
| T32_FIRST | The first thing you taught me was: your name is Marek. | The first thing you taught me was that your name is Marek. |
| T33_LAST | The last thing you taught me was: Ilse's city is Brell, in turn 4. | The last thing you taught me, in turn 4, was that Ilse's city is Brell. |
| T34_FORGOT | I forgot: Tomas's boss is Ilse. You asked me to forget it in turn ?. The old row is kept but retired. | I forgot that Tomas's boss is Ilse. You asked me to forget it earlier. I still keep the old row, but it is retired. |
| T35_CORRECTED | You corrected: Tomas's boss from Wend to Oda. | You corrected Tomas's boss from Wend to Oda. |
| T36_SRCTOLD | You told me: USER's city is Varn. | You told me that your city is Varn. |
| T37_SRCPUT | I put together things you told me: USER's boss is Tamsin; Tamsin's city is Brell. | I put together things you told me: your boss is Tamsin; Tamsin's city is Brell. |
| T38_FACTS | I know 3 facts you taught me. I also hold 0 web row, which I do not believe. | I know three facts you taught me. I don't hold any web rows. |
| T39_PEOPLE | I know 5 people: Kestrel, Lorcan, Maudry, Nimue, Pentony. | I know five people: Kestrel, Lorcan, Maudry, Nimue and Pentony. |
| T40_WEBN | Yes. I hold 1 quarantined web row. I filed it but I do not believe it. | Yes. I hold one quarantined web row. I filed it, but I do not believe it. |
| T41_SLEPTN | Yes. I have slept 3 times. | Yes. I have slept three times. |
| T42_SLEEPDERIVED | None. 0 of my facts are sleep-derived. | None of my facts came from sleep. |
| T43_TURNS | We have had 1 turns. | We have had one turn. |
| T44_ANSWERED | I have answered 1 questions. | I have answered one question. |
| T45_SAVEDN | I saved 0 times through our turns. | I haven't saved anything yet. |
| T46_REFUSED0 | No. I understood all 7 turns; I asked for clarification 0 times. | No. I understood all seven turns, and I never asked for clarification. |
| T47_REFUSEDN | Yes, 20 times I asked for clarification instead of saving. | Yes. I asked for clarification 20 times instead of saving. |
| T48_GUESSES | 0 guesses are waiting for your approval. | No guesses are waiting for your approval. |
| T49_RULES | 0 of my facts came from rules. | None of my facts came from rules. |
| T50_BARECOUNT | 0. | None. |
| T51_DREAM | I do not dream. I have slept 0 times and hold 0 sleep-derived facts. | I do not dream. I haven't slept yet, and I hold no sleep-derived facts. |
| T52_YESTERDAY | I have no record of yesterday. My log starts with our first turn here and holds 4 turns. | I have no record of yesterday. My log starts with our first turn here and holds four turns. |
| T53_NOBODYELSE | Nobody besides you has spoken to me. All 9 turns are yours. | Nobody besides you has spoken to me. All nine turns are yours. |
| T54_C5NOTURN | You did, in turn ?. | You did. |
| T55_UNSURE | I am unsure about: Tomas's boss. | I am unsure about Tomas's boss. |
| T56_DONTKNOWEX | I say I do not know instead of guessing. Like when you asked: Who is Nell's boss? | I say I do not know instead of guessing, like when you asked "Who is Nell's boss?" |
| T57_JUSTBEFORE | Just before that, in turn 3, you asked: Who is Tomas's boss? I replied: Tomas's boss is Ilse. | Just before that, in turn 3, you asked "Who is Tomas's boss?" I replied "Tomas's boss is Ilse." |
| T58_UPDATEDUSER | Updated: USER's city is Varn (it was Brell). | Updated: your city is Varn (it was Brell). |
| T59_NOTSAVED | I could NOT save that: the notebook reported a problem (E17). | I could not save that, because the notebook reported a problem. |
| T60_NEWUNSTORED | You told me something new about I Believe I Can Fly's country of origin that I could not store. I can take one fact at a time — could you say it again as one fact? | You told me something new about I Believe I Can Fly's country of origin that I could not store. I can take one fact at a time. Could you say it again as one fact? |

Unchanged swept templates U01–U57: rendered once in M1, no changes (see
PASSMARKS.md for the full list).

## Moves, misses and deviations

- M2, M5, M6, M7: every count above matches the sealed predictions exactly; 0
  misses, 0 unexplained moves, 0 store changes anywhere.
- M4: the only "moves" are the 38 predicted changed replies; the 8 flagged ones
  are the registered failure (director ruling).
- M3: 153 changed turns, all explained by a 255 template, 0 store changes. The
  panel was never read item by item, never tuned on, and nothing was graded or
  judged here.
- Deviation 1 (mine): the folder already contained a full M3 runner output in
  `m3/` (dated 2026-09-22 18:20–18:21, after the seal), although the handoff
  said M3 had not been run. I left every file in `m3/` untouched and wrote my
  once-only M3 run to the new additive folder `m3-reg/`. My run's 244 replies
  are identical to the `m3/` run's 244 replies, and both changes files report
  153 changed, 0 unexplained, 0 store changes.
- Deviation 2 (mine): my changes file compares against 138m's registered panel
  transcripts (`artifacts/claude-convpanel239-138m-20260922/transcripts-138m.jsonl`);
  the pre-existing `m3/` run had compared against a same-session 138m re-run.
  Both give the same counts (153/0/0).
- Declared pre-seal deviations (from PASSMARKS.md, unchanged): guard order
  (SrcGuardMixin228 installed at import, kept where 138m has it in the MRO);
  rt143 base rows from a same-session 138m run; base138m-rows/ under artifacts/;
  single-text templates rendered once in M1; out-of-scope texts left unchanged;
  T59 drops the machine error code; Q2's "I don't know that." can misfire where
  the answer is stored (this is the M4 failure).
- Out of scope / not mine (routing and reading, with examples from the brief):
  "hello there" gets a save-failure reply; "Hi! What's your name?" gets the
  user-name reply; "Say my name." goes to pretend; name questions blocked by the
  212/216 gates; "I'm Sabella." is not saved; "Please, Kestrel's job is fisher."
  saves a junk person; "Who lives in Oslo?" gets "I have no opinions.".

## What it means (plain high-school English)

- The text cleanup worked as code: 60 canned replies were rewritten, nothing
  else moved. Every test suite shows only the planned reply-text changes, no
  wrong answers appeared or disappeared, nothing was stored differently, and the
  agent runs just as fast.
- But one new sentence is dishonest in 8 cases: saying "I don't know that."
  when the answer is actually in the notebook (or is the assistant's own name,
  or the user was teaching, not asking). The director ruled those 8 worse, so
  the experiment fails even though the grammar may be fine.

## What it doesn't mean

- It does not mean the agent got worse at answering: 0 verdict changes on all
  suites, 0 store changes everywhere, 0 new wrong answers.
- It does not mean the conversation panel judged anything: the M3 judges never
  ran, so the 153 changed conversation turns carry no correctness or grammar
  grades here.
- It does not mean M1 failed: the director grades the fixed-text renders
  separately.
