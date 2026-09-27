# Exp 255: fixed-reply text pass — pass marks (registered before the seal)

**Agent:** `scripts/claude_loop255_agent.py` with `artifacts/claude-fixedtext255-20260922/loop255-config.json`.
**Base:** 138m (`scripts/claude_loop138m_agent.py`, `artifacts/claude-merge138m-20260922/loop138m-config.json`).
**The one change:** `scripts/claude_fix255_text.py`, installed as the outermost turn wrapper (`turn255` around 138m's `turn224c`). It rewrites a reply line only when the WHOLE line fully matches one of 60 fixed templates (T01–T60). It never reads or writes the notebook and never changes routing.
**Unit tests:** `scripts/claude_fix255_test.py` (60 templates, 0 failures at seal time). For each template it checks: the rewrite id; no `USER`, em dash, ` -- `, mode name, `?.`, Oxford comma, bare zero count, "1 <plural>", double space or doubled full stop; a capital start and an end mark; idempotence; and that every frozen anchor family gives the same answer on old and new text (224a `is_decline`, bench121 `_ABSTAIN_RES`, redteam143 `ABSTAIN_MARKERS`, session152 `CLARIFY_BITS`, "i have no record"). Unchanged strings pass through untouched.
**Driver:** `scripts/claude_255_runall.sh artifacts/claude-fixedtext255-20260922/run <scratch work dir>` (one heavy step at a time; `uptime` before each; waits while load1 > 60).
**Scorer:** `scripts/claude_255_score.py` (M2, M4, M5, M6, M7), `scripts/claude_255_m2check.py` (field-by-field M2 check), `scripts/claude_255_m3changes.py` (M3 changes file, ungraded), `scripts/claude_255_m1gen.py` (M1 renders).
**Predicted moves:** `predicted_moves255.json` (machine) and `predicted-moves255.md` (every move by id with its template, and the 138m and 255 texts for M4 and M6). They were built from the full pilot (scratch `w255/pilot2`, 229 s), which passed every mark below.
**Blind:** the 239 panel (`artifacts/claude-convpanel239-*`) has not been opened. It is opened only for M3, after this seal. No other test panel was opened.
**S1:** no scorer version is added. Every frozen anchor is kept (unit tests plus the M2 suite gate), so S1 does not apply.

## Marks (all bars fixed now)

The verdict is PASS only if M2, M4, M5, M6 and M7 pass here, and the director's graders pass M1 and M3.

- **M1 fixed-text grammar.** `scripts/claude_255_m1gen.py artifacts/claude-fixedtext255-20260922/fixedtext.jsonl`, seed 2550922 (sealed in the file).
  - Every slot template (T30–T60) gets 5 distinct renders with fresh fictional fillers, passed through the real `rewrite255`.
  - A template whose text cannot vary (T01–T29, T54, T59) is rendered once.
  - Every unchanged swept template (U01–U57) is rendered once.
  - The pilot gives 232 rows: 175 changed and 57 unchanged. Rows are `{id, template_id, text}`, shuffled.
  - The file is sealed into SEAL2, then the director is messaged.
  - Bar (director's graders): 100% of changed-template renders are GRAMMATICAL for both graders. Unchanged grades are reported with no bar.
- **M2 suites.** `fable_suitediff218 --only rt136,rt143,sessions152,bench` on 255, against `base138m-rows/`:
  - rt136, sessions152 and bench are 138m's registered rows, copied unchanged.
  - rt143: 138m has no registered suitediff rt143 rows (138m used the rt143 no-gate method), so the base is a same-session 138m suitediff run from the pilot. See the deviations.
  - Bar:
    - the gate is `GATE: clean` and no suite is skipped;
    - every field difference, "seconds" aside, is an exact 255 rewrite of the 138m text;
    - so there are 0 verdict, status, store or fact-write changes;
    - the move list equals the predicted 162 ids exactly: rt136 48, rt143 42, sessions152 25, bench 43 (bench132_4hop 4, edit200 37, new_121_4hop 5, old_s2fresh 1).
  - Extra, same rule: the rt143 no-gate rows vs 138m's saved `rt143nogate-m.json` must show exactly the 45 predicted reply-only moves.
  - Flips toward an abstain are impossible under this rule, because verdicts are compared field by field and the suitediff gate counts them.
- **M3 239 panel (TEST-ONLY).** Run once, after this seal:
  - `claude_convpanel239_run.py` on 255, 30 conversations;
  - changes file against 138m's panel transcripts via `claude_255_m3changes.py`;
  - then message the director.
  - The director's bars:
    - 0 changed turns graded less correct, except where Judge A rule 8 now credits the decline as "I don't know";
    - ≥ 90% of changed turns grammatical;
    - 0 store changes.
  - I also predict 0 unexplained changes: every changed turn is an exact template rewrite.
- **M4 verifier probes** (`artifacts/claude-verify-20260922/138m/probes.json`, `probes-supp.json`), 138m and 255 run in the same session:
  - 38 changed replies are predicted: probes 36, supp 2. Bar: exactly those, with 0 store or event changes.
  - Labels are mechanical and fixed now, so I do not grade my own text:
    - an exact template rewrite is labelled "same meaning";
    - anything else is labelled "worse (unexplained)".
    - Eight rewrites are pre-flagged "possibly worse on meaning, director rules": A06, B04, B05, B20, D02, D03, D04 and D08.
    - Why flagged: the brief's Q2 decline now opens with "I don't know that.", but in these turns the answer was already stored (B04, B05, B20: the user's name; D02, D03, D08: Tomas's boss), or it is the assistant's own name (A06), or the turn was a teach request (D04).
  - Bar: 0 "worse (unexplained)". The flagged eight are reported for the director and are not counted by me. If the director counts them as worse, M4 fails on them.
- **M5 sleep smoke.** 255's report equals 138m's saved `run/smoke-m.json` in every field except agent, config, label, seconds, root and report.
- **M6 restart and verifier dialogs** (138m's M6 files: 138j p3-dialogs, p3c-restart2, p3d-ghost; 138k v-dialogs, v-supp).
  - The comparison is against 138m's saved `run/probe/m-*` and against 138m re-run in the same session.
  - Bar:
    - the same dialog counts;
    - identical events, turns and stored sets;
    - `dup_ok_all` on every dialog;
    - 0 ghosts (a ghost is a changed reply that is not an exact template rewrite);
    - the changed replies are exactly the 17 predicted, with the predicted texts: T02 6, T05 5, T39 4, T38 2.
- **M7 latency.** Alternating processes m, 255 × 3, 2 reps each, same session (`claude_merge138k_latency.py`). Bar: median per-turn delta ≤ +2.0 ms. The pilot gave +0.20 ms.

## Deviations (declared before the runs)

1. **Guard order.** SrcGuardMixin228 cannot be listed first in `Loop255Daemon`'s bases, because Python's MRO rejects it: 138m's daemon already carries it inside Loop138kDaemon. Instead:
   - the 228 guard is installed at import and first thing in `Text255DaemonMixin.__init__`;
   - `_check255` fails the build if it is missing;
   - SrcGuardMixin228 stays in the MRO exactly where 138m has it.
2. **rt143 base rows.** See M2: they come from a same-session 138m run, not a registered 138m file. The two 138m runs (pilot control) matched each other exactly, with 0 moves.
3. **Base folder location.** `base138m-rows/` lives under artifacts/ because suitediff218 ignores any base path containing "scratch".
4. **M1 renders.** Templates with only one possible text are rendered once, not 5 times, because five copies would be identical.
5. **Out of scope and left unchanged:**
   - the label forms "Saved:", "Updated:" and "Forgotten:": these are 241 mouth scope, and "forgotten:" is a 224a never-decline prefix;
   - the multi-value ask "X's R is A and B. Which one do you mean?" and "(I also have …)": 241 scope, and 154b probes match these texts.
   - T58 only renders "USER's" as "your"; the "Updated:" label stays.
6. **T59** drops the machine error code, e.g. "(E17)", because the style sheet bans machine text. The meaning ("I could not save that; the notebook reported a problem") is kept.
7. **Where Q2's "I don't know that." can be wrong.** It fires on misread questions. When the misread question asks for a fact that is stored, the new first sentence is not literally true. This wording is the brief's item 1. See the M4 flags.

## Templates changed: before (138m) and after (255)

One sample per template (the unit-test sample). The slot templates are regex rules, and the fillers vary.

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


## Unchanged swept templates (rendered once in M1; no changes)

| id | text |
|---|---|
| U01_ALREADY | I already have that. |
| U02_NONAME | You never told me your name, so I do not know it. |
| U03_DONTKNOWREL | I don't know Maelis's brother. |
| U04_THANKS | You're welcome! |
| U05_NOBODYWHOSE | I don't know anyone whose boss is Quilla. |
| U06_YOURNAME | Your name is Tavik. |
| U07_MAKER | Ben built me. |
| U08_NONAMEYET | I don't know your name yet. |
| U09_WHAT | I'm a small program that keeps what you teach me in a notebook and answers from it. When I don't know something, I say so instead of guessing. |
| U10_APOLOGY | No worries! |
| U11_DONTHAVE | I don't have Ammet as Zarek's mother. |
| U12_NOTHINGSAID | I haven't said anything yet. |
| U13_UNKNOWNNAME | I don't know anyone called Wistan. |
| U14_WHICHONE | Pellam's boss is Odo and Brannoc. Which one do you mean? |
| U15_CHANGEQ | I have Hesk's mother as Sabeth. Do you want me to change it to Ysolt? |
| U16_CHANGENAME | I have your name as Liesl. Do you want me to change it to Venn? |
| U17_HERE | I'm here and ready to learn. Tell me something, or ask me about what you've told me. |
| U18_HIHERE | Hi! I'm here and ready to learn. Tell me something, or ask me about what you've told me. |
| U19_NAME | My name is Premonition. |
| U20_FAVOURITES | I do not have favourites. |
| U21_LAUGH | Haha, nice! |
| U22_BYE | Bye! |
| U23_ACK | Got it! |
| U24_SAVED | Saved: your job is weaver. |
| U25_SAVEDALSO | Saved: Tavik's friend is Rennick. (I also have Brannoc.) |
| U26_UPDATED | Updated: Oriane's teacher is Mirelle Quast (it was Corvane). |
| U27_FORGOTTEN | Forgotten: Talwyn's teacher. |
| U28_FORGOTTENONE | Forgotten: Dorwin's mother Isbet. |
| U29_NOTAUGHT | You haven't taught me anything yet. |
| U30_NORECORD | I have no record of that, so I do not know it. |
| U31_HEARSAY | Do you know that yourself, or did you hear it somewhere? I only save facts you tell me directly. |
| U32_NOTSLEPT | Nothing. I have not slept yet. |
| U33_NOTFORGOT | I haven't forgotten anything you taught me. |
| U34_CITYNOTSURE | I have no record of that city, so I cannot be sure. |
| U35_NOTHINGOPEN | Nothing is open. Every question you asked was answered. |
| U36_ALLFROMYOU | No. Every taught fact came from you. |
| U37_NOWEB | I haven't filed anything from the web. |
| U38_DONTKNOWCALLED | I do not know that. I don't know anyone called Ulla. |
| U39_NOWHY | You never told me why. I only store what you state, not reasons. |
| U40_NOOPINIONS | I have no opinions. |
| U41_AGE | I don't have an age. I'm a program, so I don't measure my life in years. |
| U42_HOME | I don't live anywhere. I'm a program that runs on a computer and keeps a notebook file. |
| U43_LEARN | I learn when you tell me facts in plain sentences, like "Kim lives in Oslo." I save each one and answer from my notes. |
| U44_NAMEYES | Yes, my name is Premonition. |
| U45_NAMENO | No, my name is Premonition. |
| U46_NOTNEG | OK, Venn's brother is not Wistan. I don't have another brother for Venn. |
| U47_PRETEND | OK, I'll treat that as pretend, so I won't save it. |
| U48_DESCRIPTION | That sounds like a description, not a name, so I didn't save it. What is Rennick's mother's name? |
| U49_NOTWAITING | I wasn't waiting for an answer. |
| U50_NOTCATCH | I didn't catch anything. |
| U51_LEFTIT | Okay, I left it as it was. |
| U52_YESNO | Yes, Galen Thorne's city is Ostwick. |
| U53_SOURCETOLD | You told me: Fenwyn's job is fisher. |
| U54_FALLTHROUGH | I didn't understand that. Could you say it another way? |
| U55_ONLYONLINE | No. Web rows are quarantined and never answer questions. Only what you teach me answers. |
| U56_NOTHINGNEW | Nothing new was installed while sleeping. |
| U57_EMPTYLOG | Just before that I did nothing; the log is empty. |
