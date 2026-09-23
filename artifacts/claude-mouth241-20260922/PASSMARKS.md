# Exp 241 PASSMARKS: the mouth, stage A (grammar layer and say forms)

Written by the 241 builder on 2026-09-22 before the seal. Spec: design/v3/30-modes/240-mouth-design-opus.md
(sections 1, 3.1, 4 and 6 are binding). Brief: 241-mouthA.txt. Rules: OPUS-RULES.txt.

## 0. What is being tested

- **Base:** scripts/claude_loop228_agent.py with artifacts/claude-determinism228-20260922/loop228-config.json. This is 138i plus the 228 source guard; SrcGuardMixin228 is first in the bases.
- **241 agent:** scripts/claude_loop241_agent.py (Loop241Daemon), with the same config. The class order is `SrcGuardMixin228, Mouth241Mixin, <228 daemon>`, so Mouth241 sits at the front of the outermost loop class.
- **What the mixin does:** it runs after the whole base turn and rewrites only the outbox reply text. It never calls the notebook and never writes.
- **No existing file is edited.**
- **Code, all new:**
  - scripts/claude_mouth241_morph.py (morphology)
  - scripts/claude_mouth241_reader.py (round-trip reader over the 229 reader)
  - scripts/claude_mouth241_say.py (say table and rendering)
  - scripts/claude_mouth241_parse.py (parse-back of legacy templates into frames)
  - scripts/claude_mouth241_brake.py (brake v2, rules 1–9)
  - scripts/claude_loop241_agent.py (mixin and agent)
  - scripts/claude_mouth241_test.py (unit tests, 18/18 pass at seal)
  - scripts/claude_mouth241_sweep.py (M1 sweep generator, sealed seed `SEED241 = 241_0922_07`)
  - scripts/claude_mouth241_pairs.py (M4 pairwise sampler, sealed seed `PAIRS_SEED = 241_0922_31`)
  - scripts/claude_mouth241_suites.py (M3 / M2(b,c) suite driver with passive capture hooks)
  - scripts/claude_mouth241_check.py (M2 a/b/c, M3 and M5 checks)
  - scripts/claude_mouth241_score.py (sealed M1/M4 scorer)
- **Say table:** artifacts/claude-mouth241-20260922/say_forms.json.
  - 150 rows: one per relation of relation_table_v1_1.json plus the extra relations the base uses.
  - 32 rows have verb forms. 0 forms were dropped by the build round trip.
  - Rebuilding from the sealed code gives a byte-identical file (checked at seal).
- **Fallback on failure:** when brake v2 rejects every candidate, the line falls back to the base's legacy text and is logged as sev-1. Fixed acts and unframed lines pass through byte-identical.

## 1. Scorer anchors (every substring the frozen scorers and 224a's decline detector match on)

A forms must keep each anchor exactly as the legacy line had it. Brake rule 9 enforces this on every line: it computes each anchor on the legacy line and on the candidate, and any difference rejects the candidate. No scorer change is pre-registered.

1. **fable_decline224.is_decline (224a shared detector).**
   - Matching: lower-cased; a line starting with `saved:` or `forgotten:` is never a decline; otherwise it is a decline if any DECLINE_MARKERS224 substring appears.
   - bench121 ABSTAIN_PHRASES:
     - "i don't know", "i dont know", "was that a question"
     - "i didn't understand that", "i did not understand", "i didn't catch anything"
     - "i can take one fact at a time", "could you split that", "do you know that yourself"
     - "i only save facts you tell me directly", "i can only follow", "please say it like"
     - "i can only handle one-word names", "i didn't get the value", "which is not someone i can look up"
     - "i know more than one", "which one do you mean", "please answer with"
     - "please answer yes or no", "i wasn't waiting for an answer", "i couldn't read that message"
     - "do you want me to change it to"
   - redteam143 markers:
     - "don't know", "not someone", "didn't understand", "could you say"
     - "split that", "only follow", "didn't catch", "couldn't read"
     - "only handle one-word", "could not use that", "didn't get the value", "not allowed"
     - "do you want me to change", "i only save facts", "i wasn't waiting for an answer"
   - session152 CLARIFY_BITS: "another way", "which one", "do not know", "unknown", "unsure", "missing", "1 to 3".
   - redteam110: "wasn't waiting", "left it as it was", "not someone i can look up", "could not save".
   - S105: "i have no record".
   - Census families:
     - "i could not store", "couldn't save", "i could not save"
     - "i won't save it", "so i won't save", "i didn't save it"
     - "i can't answer that", "cannot answer that", "i do not understand that question"
     - "not sure what you", "please say it again without"
     - "which is right?", "which one is wrong", "which one should"
2. **redteam143 abstain_markers** (from the case file, lower-cased substring):
   - "don't know", "not someone", "which one do you mean", "didn't understand"
   - "could you say", "was that a question?", "split that", "only follow"
   - "do you know that yourself", "didn't catch", "please say it like", "couldn't read"
   - "only handle one-word", "could not use that", "didn't get the value", "not allowed"
   - "do you want me to change", "i didn't catch anything", "i can take one fact at a time"
   - "i only save facts", "i wasn't waiting for an answer"
3. **bench121 abstain regexes:** each ABSTAIN_PHRASES item from item 1, wrapped as `\b...\b`, on the lower-cased reply.
4. **session152 is_clarify:** any CLARIFY_BITS substring, lower-cased.
5. **teach_accepted (bench121 and redteam143):** the reply starts with `Saved:`, or equals `I already have that.`.
6. **Value extract (bench121 / redteam143 extract_answer):** the text after the last " is " / " are ", normalised (lower case, punctuation removed, a/an/the and "and" dropped).
   - For VALUE_ACTS (ANSWER, ANSWER_LIST, REVERSE, YESNO_YES, YESNO_NO, YESNO_NOTKNOWN, BROKEN_CHAIN), A keeps both the presence of " is "/" are " and the normalised extract.
   - Declared exception, REVERSE only: the extract is "the R of S", so the relation words may differ ("educated at" becomes "alma mater"). The words of the path noun and its display noun are removed from both extracts before comparing; the names must still match exactly.
7. **session152 `want in reply` (lower-cased substring)** is protected by brake rule 2 (every frame slot must appear) and by rule 9's extract.
8. **Bench v3 confirm needle (scripts/fable_fix172b_benchv3.py, dialog driver):**
   - The driver finds "Do you want me to change it to" and takes the text after it, stripped of "?.! ".
   - It answers "yes" only when that text occurs verbatim in the taught sentence.
   - So A keeps the new value byte-equal to the stored value: no "the", no capitalisation. Rule 9 anchor `confirm172b` enforces this.
   - This anchor was found in pilot 241b: adding "the" to "United Kingdom" gave 8 new WRONG in bench. It is fixed, and the anchor was added before the seal.
9. **Never touched:** "worked out backwards" (A never emits it; brake rule 8 bans it without inverse provenance), "more than one" (AMBIGUOUS keeps "I know more than one ...", "Which one do you mean?"), and "not someone I can look up" (BROKEN_CHAIN keeps it).

## 2. 238 bug classes: in or out of A

Each class covered by A is a sub-mark of M1 and must be 0 on the sweep (mechanical detectors in claude_mouth241_score.py).

| 238 class | status |
|---|---|
| RELATION_NOT_VERB | covered by A (rows with a verb form use it at 1 hop in SAVED, CONFLICT, FORGOTTEN_ONE, FORGOTTEN, ABSTAIN_MISSING) |
| STACKED_POSSESSIVE | covered by A (3+ hops never stack the whole chain as 's) |
| DECLINE_SPLICE + ROBOTIC_DECLINE | outside A (owner: 224c) |
| BAD_RELATION_PHRASE | covered by A for every relation with a say row, inner hops included ("founded by" becomes "founder"); relation phrases with no say row pass through unchanged (owner: 242 / table growth) |
| LOWERCASE_START (+ LOWERCASE_NAME_ECHO) | covered by A. Declared exception: the CONFLICT new value is echoed verbatim (bench v3 confirm needle, section 1 item 8) |
| DOUBLE_DASH | outside A (owner: fixed-act owner, fable_screen148 mixin) |
| PLURAL_NAME_POSSESSIVE | covered by A (plural-looking names, e.g. "... Works", "... Books", and 'the' names, always take the of form) |
| QUESTION_NO_QMARK | outside A (owner: fixed-act owner, loop188 clarify text) |
| TEACH_ME_LIKE | outside A (owner: fixed-act owner, fix156b small talk) |
| OFF_TOPIC_NO_OPINIONS | outside A (owner: ears / opinion screen) |
| COLON_LABEL | covered by A ("Forgotten: ..." becomes "OK, I've forgotten ...") |
| VALUE_LIST_AGREEMENT | covered by A |
| NO_ARTICLE_JOB | covered by A (occupation says "is a/an J" in SAVED, ANSWER, CONFLICT, FORGOTTEN_ONE, YESNO_YES/NO, BROKEN_CHAIN) |
| DOUBLE_TERMINAL_PUNCT | covered by A |
| NUMBER_AGREEMENT | covered by A (self counts) |
| MISSING_ARTICLE_THE | covered by A for the closed list of 'the' names. The sweep's fictional fillers never hit the list, so this class is checked by the unit test render_the_names (also a detector on the sweep) |
| ANYONE_CALLED_THING | outside A (owner: 221 / ears; A keeps "I don't know anyone called X") |
| SPELLING | outside A (owner: bench data, fable_bench92) |
| WRONG_REFERENT_AGE | outside A (owner: 168 / self router) |
| RAW_RELATION | outside A (owner: older agents only; none in scope; A never renders raw keys, see sub-mark S5) |
| PRETEND_PAREN + SAY_FRAGMENT | outside A (owner: 137d pretend handler) |
| WORKED_BACKWARDS_TAG | covered by A (A never emits the tag) |
| EMPTY_LIST | covered by A ("I know 0 people: ." becomes "You haven't told me about anyone yet.") |
| BARE_NAME_LIST | covered by A ("I know two people: Max and Silas.") |
| PLACEHOLDER_LEAK | outside A (owner: self99 forget-turn text) |
| GARBLED_READBACK | outside A (owner: 229 read-back) |
| Director input: "I know 1 people: USER." | covered by A ("I know one person: you."). Unit test render_director_case, plus the sweep's SELF_PEOPLE stratum with USER and one fixed director case |

## 3. Predicted moves by act

The prediction, per 240 §6: every framed line whose relation has a say form changes wording only. There is no status, verdict, storage or event change anywhere.

- Suite reply-text moves may occur only on lines A rendered (route A) of these acts:
  - SAVED, DUPLICATE, CONFLICT, CONFIRM_RESULT
  - FORGOTTEN, FORGOTTEN_ONE, NOT_HAD, ABSTAIN_MISSING
  - UNKNOWN_ENTITY, AMBIGUOUS, BROKEN_CHAIN
  - YESNO_YES, YESNO_NO, YESNO_NOTKNOWN
  - REVERSE, ANSWER, ANSWER_LIST
  - SELF_PEOPLE, SELF_FACTS, SELF_SLEPT, SELF_TURNS, SELF_ANSWERED
- Passthrough lines (fixed acts, unframed text) never change. This is checked by M2(b) and M3.
- Per act, the wording moves are:
  - **SAVED:** "Saved: X's R is V." becomes "Saved: " plus the row's affirm form. Examples: "Mira lives in Oslo", "Jon is a baker", "Silas Wendt owns Juniper Lane Books". Other forms: "The R of S is V" for s/x/z and plural names, and "You live in Lima" for the user.
  - **CONFLICT:** "I have NP as OLD. Do you want me to change it to NEW?" becomes "My notes say <affirm OLD>. Do you want me to change it to NEW?". NEW stays verbatim.
  - **FORGOTTEN:** "Forgotten: NP." becomes "OK, I've forgotten where/what/who ..." or "OK, I've forgotten NP."
  - **FORGOTTEN_ONE:** "Forgotten: NP V." becomes "OK, I've forgotten that <affirm>."
  - **NOT_HAD:** "I don't have NP V." becomes "I don't have V as NP, so there was nothing to forget."
  - **ABSTAIN_MISSING:** "I don't know NP." becomes the row's abstain form ("I don't know where Mira lives.") and keeps "I don't know".
  - **ANSWER / ANSWER_LIST / YESNO_* / REVERSE / BROKEN_CHAIN:** only the noun phrase changes. The changes are possessive to of-form, plural agreement ("friends are"), display noun, articles on count-noun literals ("a hamster") and on 'the' names. The value, and the " is "/" are " extract, are unchanged.
  - **SELF_PEOPLE:** "I know N people: A, B." becomes "I know N-in-words people: you, A and B." "I know 0 people: ." becomes a 0-count sentence.
  - **SELF_FACTS / SLEPT / TURNS / ANSWERED:** 0–9 as words, count agreement, and 0-count sentences.
  - **DUPLICATE / CONFIRM_RESULT / UNKNOWN_ENTITY / AMBIGUOUS:** rendered from the frame, and textually identical to legacy except that a lower-case name is capitalised in UNKNOWN_ENTITY. An ears misread such as "my sister" is kept verbatim.
- Pilot counts (pilot 241d, not registered): changed reply lines by act were SAVED 3953, CONFLICT 721, ANSWER 673, ABSTAIN_MISSING 7.
  - Suite moves: rt136 45, rt143 24, sessions152 60, bench 623. All are reply-only; GATE clean.
  - 0 legacy fallbacks, 378 unframed lines.

## 4. Registered marks (exact bars from 240 §6)

- **M1 grammar ≥ 99%.**
  - Sweep: every act in table 1.3 × every relation row that act can take (150 rows, plus 4 generic nouns) × 4 tricky-filler classes (sxz, vowel, multi, lower). Stratified to 1,205 replies: 13 row acts × 80, plus the fixed acts (DUPLICATE 4, CONFIRM 4, UNKNOWN 30, AMBIGUOUS 30, SELF_PEOPLE 40 + 1 director case, SELF_FACTS 20, SELF_SLEPT/TURNS/ANSWERED 12 each). Fillers are fictional, from the sealed seed.
  - Graded by an independent grader, launched by the director, that has not seen the code or the say table, using the style sheet in section 6.
  - **Bar:** ≥ 99.0% grammatical overall **and** ≥ 97% in every act stratum.
  - **Also required, 0 each (mechanical, claude_mouth241_score.py):**
    - "s's" on plural common nouns
    - "a" before a vowel sound, or "an" before a consonant sound
    - empty list slots ("people: .")
    - bare "0 X" counts
    - raw underscores or keys
    - a dangling "(worked out backwards)"
  - **Plus the covered 238 classes, 0 each:**
    - RELATION_NOT_VERB, PLURAL_NAME_POSSESSIVE, VALUE_LIST_AGREEMENT
    - NO_ARTICLE_JOB, NUMBER_AGREEMENT, NUMBERS_0_9_AS_WORDS
    - EMPTY_LIST, BARE_NAME_LIST, SELF_PEOPLE_USER_AS_YOU
    - COLON_LABEL, LOWERCASE_START, LOWERCASE_NAME_ECHO
    - DOUBLE_TERMINAL_PUNCT, MISSING_ARTICLE_THE, STACKED_POSSESSIVE
    - WORKED_BACKWARDS_TAG, BAD_RELATION_PHRASE
  - Pilot: 0 on every sub-mark on 3 pilot seeds (9191, 4242, 777).
- **M2 unfaithful = 0.**
  - **(a)** On the sweep, every A reply passes brake v2 rules 1–8 against its frame, including the round trip (rule 7) for every triple act. A sev-1 fallback on the sweep counts as a failure.
  - **(b)** On the frozen suites, every framed line's parse-back frame equals the frame A rendered: legacy(frame) == base line, and re-rendering the frame gives the 241 line. Every unframed line is byte-identical to the base.
  - **(c)** The notebook event logs of base and 241 are identical on every suite run (see declared interpretation D1).
  - **Bar:** 0 failures in each of a, b and c. Tool: claude_mouth241_check.py m2a / m2b / m2c.
- **M3 frozen suites: only predicted moves.**
  - Run `scripts/fable_suitediff218.py --only rt136,rt143,sessions152,bench --base 138i` for the 241 agent, through claude_mouth241_suites.py.
  - Correctness verdicts: **0** correct→wrong, and 0 flips toward abstain or "Was that a question?". The guard is installed. Any flip is run alone 5 times and reported.
  - Reply-text moves are allowed only in the classes of section 3.
  - The GATE line must read clean. Tool: claude_mouth241_check.py m3.
- **M4 naturalness, blind and pairwise.**
  - A separate judging agent (not the builder, not the grader) sees 120 pairs, stratified by act. Each pair has one user turn, the base reply and the 241 reply in random order labelled X/Y, and the frame's facts.
  - The judge picks the more natural reply, or a tie.
  - **Bar:** 241 wins ≥ 70% of non-tie pairs **and** loses ≤ 10% of all pairs.
  - Any meaning-change flag is investigated under M2 and counts as unfaithful if confirmed.
- **M5 latency.**
  - Mouth overhead per reply on the Mac CPU (1 thread), measured over the sweep's render_line ms: median ≤ 2 ms and p99 ≤ 20 ms. This includes rule 7's parser call.
  - Suite wall-clock ≤ base + 5% (protocol in D6).
- **Also:**
  - The sleep smoke (fable_sleepsmoke206.py) is identical to the base on its summary fields: sleeps, installed, probes right/wrong/abstain, broken, taught, overwritten.
  - The unframed-line count on the suites is reported (no bar).

**Verdict:** PASS iff M1, M2 (a, b, c), M3, M4, M5 and the sleep smoke all pass. M1 or M4 not scorable (SCHEMA-MISMATCH, exit 3) makes the run VOID, not FAIL.

## 5. Declared interpretations and deviations (fixed before the seal)

- **D1, M2(c) "byte-identical".** Raw event logs differ even between two base runs: each event id carries a uuid4 suffix (fable_listening_m1._eid), and "prev" is a hash chain over those ids. So M2(c) compares logs after normalising:
  - event ids are replaced by their order of first use, and "prev" is dropped;
  - rt136 case directories carry a random mkdtemp suffix (`C001_f3i14a99`), which is dropped from the log name, and same-name logs are compared as multisets.
  - Raw byte identity is reported as well. Pilot: 1016/1016 normalised identical, 0/1016 raw identical. Base vs base is also 0 raw identical.
- **D2, M3 base.** The diff is against 138i's sealed rows (`--base 138i`), because 228 had 0 moves against 138i on every suite in 228's own run. The 228 reference run (pilot) is also 0 moves, so every move is attributable to 241.
- **D3, M2(b) method.** The mixin logs, per reply line, `in` (the base's own line from the same turn), `out` (the 241 line), the route and the frame (MOUTH241_LOG). The check re-renders with the notebook names removed; names can only remove candidates. A different pick is reported as a failure and never silently accepted.
- **D4, M4 pairs come from a single 241 run.** "in" is the base line, and "out" is the 241 line of the same turn. This is valid because the mixin runs after the whole base turn and cannot write (M2(c)).
  - The judge sees no earlier dialog context, because earlier replies would reveal which side is 241.
  - The source is 24 fictional 33-turn dialogs from PAIRS_SEED. The sample is 120 changed lines, round-robin by act.
- **D5, rule 7 reader.** Rule 7 uses the 229 table reader (claude_loop229_agent.table_teach_readings229) plus possessive / of / my / inverted generic readings. Three frame-derived aids are used:
  - frame names that contain a period / ! / ? / ; or a "you" word are read as placeholder names ("J. K. Rowling", "Apple Inc.", "Within You Without You");
  - an occupation value missing from 229's closed job list is read as a stand-in job word;
  - X == Y (e.g. "Luxembourg ... Luxembourg") has no direction and skips the reversed-reading test.
- **D6, M5 wall protocol.** The Mac is shared, so single walls are noisy (pilot: 228 46.0 s, 241 38.2–52.8 s at load 8–11). The registered wall is the median of 3 runs each of 228 and 241, alternated (228, 241, 228, 241, 228, 241), using the same suite command with each agent. The 241 runs are the M3 runs: the first 241 run is the registered M3 / M2(b,c) run, and runs 2–3 are timing-only and reported.
- **D7, sev-1 fallbacks** on the suites are allowed by the spec: the legacy line is kept, it is safe, and it is counted. They are reported by act. On the sweep, a fallback fails M2(a).
- **D8, display noun.** A verb-phrase relation display (for example "educated at", "founded by", "date founded") is said as the row's first plain-noun surface ("alma mater", "founder", "founding date"). The brake's content lexicon includes these frame-derived nouns.
- **D9, CONFLICT new value verbatim** (section 1 item 8). A lower-case new value stays lower-case, and a count-noun value gets no article after "change it to". This is a known grammar risk, and the grader will see it.
- **D10, the repeated 3-gram rule (brake rule 1)** ignores grams made only of relation-path words, "the", "of" and "s" (e.g. "the friend of the friend of"). Masked name slots are ignored as before.
- **D11, (e) re-render of 238's harvest.** It is report-only (no bar). The re-render script (scripts/claude_mouth241_rerender238.py) is written after the seal, because harvest.jsonl may be read only after the seal. It is not sealed and changes no mark.
- **D12, registered run order.**
  1. (a) sweep, (b) pairs, (c) SEAL2 + message.
  2. (d) M2(a) and M5 latency on the sealed sweep; M3 + M2(b,c) (228 capture run, then the 241 run), the extra wall runs, M3 check; sleep smoke 228 then 241.
  3. (e) rerender238.
  4. (f) scoring when the grader and judge outputs arrive.

## 6. Grader style sheet (for the director's independent M1 grader)

Mark each reply grammatical: true/false with a short reason. Judge English grammar and punctuation only, not truth or style preference. The names are invented and may look odd; do not mark a reply wrong for an unusual name.

1. The possessive of a singular name is X's, including names ending in s ("Silas's"). The "of" form ("the city of Silas") is also correct. A plural-looking name ("Juniper Lane Books") needs the "of" form or a verb, never "Books's".
2. Lists have no Oxford comma: "A, B and C".
3. Numbers 0–9 are written as words in running text. 10 and above may be digits. Digits inside names, dates, addresses and codes are fine.
4. "a"/"an" follow the sound of the next word.
5. Count agreement: "one person", "three people", "1 fact" is wrong.
6. A reply may quote an unknown or odd phrase the user typed, in the user's own casing (e.g. "I don't know anyone called my sister."). Judge the sentence around it.
7. A value the user is asked to confirm ("Do you want me to change it to X?") is echoed as stored.
8. Entity ids in parentheses, e.g. "(E2153)", are a deliberate choice list in "I know more than one ..." replies; they are not an error by themselves.

Output schema (exactly these keys, one line per sweep id, every id exactly once): `{"id": str, "grammatical": bool, "reason": str}`.

Judge schema (M4, exactly these keys, every pair_id once): `{"pair_id": str, "pick": "X"|"Y"|"tie", "meaning_change": bool, "note": str}`.

A schema mismatch makes the scorer print SCHEMA-MISMATCH and exit 3 (VOID).

## 7. Predictions (also appended to the ledger as P241.n)

- **P241.1:** M2(a), (b) and (c) each have 0 failures.
- **P241.2:** M3: GATE clean; every suite move is reply-only on a route-A line of a section-3 act; 0 verdict changes; 0 flips toward abstain.
- **P241.3:** M5 latency passes (median under 2 ms, p99 under 20 ms). The wall is within +5% of 228 under the D6 protocol; I am less sure of this (p ≈ 0.7) because of machine load.
- **P241.4:** M1: every mechanical sub-mark is 0 on the sealed sweep (p ≈ 0.8).
- **P241.5:** M1 grader bar (≥ 99.0% overall and ≥ 97% per act) passes with p ≈ 0.45. The acts most at risk are CONFLICT (verbatim lower-case new values, D9), AMBIGUOUS (entity ids), REVERSE and NOT_HAD (long relation nouns), and SAVED/ANSWER with odd relation nouns ("language of work or name").
- **P241.6:** M4 passes with p ≈ 0.65: win rate ≥ 70% of non-tie pairs, and losses ≤ 10%.
- **P241.7:** The sleep smoke is identical to 228: sleeps=1, installed=1, probes 5/5, wrong 0, broken=abstain, taught 50/50, overwritten 0.
- **P241.8:** 0 sev-1 fallbacks on the suites; the unframed-line count equals the pilot's 378.
