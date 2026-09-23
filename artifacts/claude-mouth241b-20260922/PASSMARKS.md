# Exp 241b PASSMARKS: the mouth, stage A v2 (grammar layer fixes + cheaper rule 7)

Written by the finishing 241b builder on 2026-09-23 before the seal. Brief:
handoff/kit/briefs/241b-mouthA2.txt (registered; follow exactly). Rules:
OPUS-RULES.txt. 241's registered FAIL stays FAIL; this is the one
diagnosis-driven follow-up. The first 241b builder stopped before sealing
(account limit) and left unsealed code; the finisher reused it by import,
added two dev-only _r copies (D13), ran the dev pilot, and seals here.

## 0. What is being tested

- **Base:** scripts/claude_loop228_agent.py with
  artifacts/claude-determinism228-20260922/loop228-config.json (138i plus the
  228 source guard; SrcGuardMixin228 first in the bases).
- **241b agent:** scripts/claude_loop241b_agent.py (Loop241bDaemon), same
  config. Class order `SrcGuardMixin228, Mouth241bMixin, <228 daemon>`.
  The mixin runs after the whole base turn and rewrites only the outbox
  reply text. It never calls the notebook and never writes.
- **No existing file is edited.** The first builder's 241b files are
  read-only and reused by import. Two dev-only copies carry the _r suffix
  (D13); neither is sealed and neither is on the registered path.
- **Code, all new (sealed, 17 files):**
  - scripts/claude_mouth241b_morph.py (morphology, unchanged 241 helpers)
  - scripts/claude_mouth241b_reader.py (round-trip reader over the 229
    reader, plus inv_of_are for REVERSE "are"; lru_cache on patterns)
  - scripts/claude_mouth241b_say.py (say table v2 + rendering: say_kind
    column, conflict_value, cap_name with particle exemption,
    plural_looking, uniq dedup, ambiguous_names, BROKEN_CHAIN tail)
  - scripts/claude_mouth241b_parse.py (lossless parse-back, 241 logic)
  - scripts/claude_mouth241b_brake.py (brake v2 rules 1-9 + exact memos +
    rule-7 SHAPE cache; confirm_key241b via claude_confirm241b)
  - scripts/claude_loop241b_agent.py (mixin + agent; AMBIGUOUS identical
    names pass through, counted as ambiguous_identical)
  - scripts/claude_confirm241b.py (shared norm_value / confirm_match:
    casefold + one leading article stripped)
  - scripts/claude_fix172b241b_benchv3.py (the ONE new scorer version, D2)
  - scripts/claude_mouth241b_test.py (unit tests, 29/29 pass at seal)
  - scripts/claude_mouth241b_sweep.py (M1 sweep generator, sealed seed
    `SEED241B = 241_0922_83`)
  - scripts/claude_mouth241b_pairs.py (M4 sampler, sealed seed
    `PAIRS_SEED241B = 241_0922_97`, 24 dialogs, 120 pairs, key label 241b)
  - scripts/claude_mouth241b_suites.py (M3 / M2(b,c) suite driver;
    --scorer241b swaps in the new 172b version for v3 splits only)
  - scripts/claude_mouth241b_check.py (M2 a/b/c, M3, M5 checks; --wall241b)
  - scripts/claude_mouth241b_score.py (sealed M1/M4 scorer, 28 sub-marks)
  - scripts/claude_mouth241b_s1.py (S1 anchor identity check)
  - scripts/claude_mouth241b_rer241.py (report-only 241 re-render; runs in
    dev through the _r copy against /tmp material, D13)
  - scripts/claude_mouth241b_rerender238.py (report-only harvest re-render)
- **Say table v2:** artifacts/claude-mouth241b-20260922/say_forms.json,
  version "241b-A-2".
  - 150 rows, 32 with verb forms, 0 forms dropped by the build round trip.
  - New column say_kind (name / common / number / date / free); generic
    rows are 'free' (never re-cased).
  - Rebuilding from the sealed code gives a byte-identical file (checked
    at seal: `claude_mouth241b_say.py --build` leaves `git status` clean).
- **Fallback on failure:** when brake v2 rejects every candidate, the line
  falls back to the base's legacy text and is logged as sev-1. Fixed acts
  and unframed lines pass through byte-identical. AMBIGUOUS lines whose
  listed full names are not all different pass through unchanged
  (route passthrough, counted; owner: ambiguity handler).

## 1. Scorer anchors and the new scorer versions

A forms keep each frozen anchor exactly as the legacy line had it, except
the two registered changes below. Brake rule 9 enforces the rest on every
line. New versions (copies; the old files are never edited):

- **NEW-1 scripts/claude_fix172b241b_benchv3.py** (with helper
  scripts/claude_confirm241b.py). Reason: the CONFLICT new value is now
  rendered as a value in running English ("the euphonium", "Shethgean"),
  so the frozen byte-verbatim needle (`new_val in sent`) no longer
  matches; the new version matches case- and article-insensitively
  (confirm_match). On verbatim values it answers exactly as the frozen
  driver (unit test b241_confirm_match_version). Used only for the 241b
  suite run's v3 splits (--scorer241b); the 228 base runs use the frozen
  driver.
- No other new scorer version. The BROKEN_CHAIN tail keeps the frozen
  abstain anchor "i can only follow" (bench121 ABSTAIN_PHRASES, rt143
  "only follow", 224a decline marker) and adds no sessions152 clarify bit
  ("don't know" never appears), so bench121 / rt143 / 224a / session152
  verdicts are unchanged by construction. AMBIGUOUS keeps "I know more
  than one" and "Which one do you mean?". The CONFLICT question keeps
  "Do you want me to change it to". "Saved:" / "I already have that." /
  " is " / " are " extracts are unchanged (REVERSE keeps the "the R of S"
  shape; plural-looking common values use "are", which the reader reads
  back via inv_of_are).

Kept-anchor inventory (frozen modules imported read-only by brake v2):
fable_decline224 DECLINE_MARKERS224, bench121 ABSTAIN_PHRASES, rt143
abstain_markers, session152 CLARIFY_BITS, redteam110 markers, S105
"i have no record", census families, teach_accepted ("Saved:" /
"I already have that."), value extract after last " is "/" are ".

## 2. 238 bug classes and the mechanical sub-marks (all must be 0)

Covered by A (sub-mark of M1, mechanical detectors in
claude_mouth241b_score.py, 22 C marks): RELATION_NOT_VERB (with a
number-CONFLICT exemption: no units the user never gave),
PLURAL_NAME_POSSESSIVE, VALUE_LIST_AGREEMENT (dedup-aware),
NO_ARTICLE_JOB, NUMBER_AGREEMENT, NUMBERS_0_9_AS_WORDS, EMPTY_LIST,
BARE_NAME_LIST, SELF_PEOPLE_USER_AS_YOU, COLON_LABEL, LOWERCASE_START,
LOWERCASE_NAME_ECHO (now includes the CONFLICT new value),
DOUBLE_TERMINAL_PUNCT, MISSING_ARTICLE_THE, STACKED_POSSESSIVE,
WORKED_BACKWARDS_TAG, BAD_RELATION_PHRASE, plus the five 241b/style-v2
marks ENTITY_CODE (no "(E…)" codes), REPEATED_LIST_ITEM (no exact repeat),
SOMEONE_NON_PERSON ("someone/who" only for people), TITLE_THE_LOWERED (a
title keeps its "The"), VALUE_SUBJECT_AGREEMENT (a plural-looking common
value never takes "is"; names/numbers/dates/free never count as plural).
Outside A (unchanged from 241): DECLINE_SPLICE + ROBOTIC_DECLINE (224c),
DOUBLE_DASH / QUESTION_NO_QMARK / TEACH_ME_LIKE (fixed-act owners),
ANYONE_CALLED_THING (221/ears), SPELLING (bench data),
WRONG_REFERENT_AGE (168), RAW_RELATION / PRETEND_PAREN + SAY_FRAGMENT /
PLACEHOLDER_LEAK / GARBLED_READBACK (older/self/229 owners).
Required zeros S1-S6 (240 §6): s's on plural common nouns, a/an by sound,
empty list slots, bare "0 X", raw underscores/keys, dangling
"(worked out backwards)".

## 3. Predicted moves by act

Wording only; no status, verdict, storage or event change anywhere. Suite
reply-text moves may occur only on lines A rendered (route A) of: SAVED,
DUPLICATE, CONFLICT, CONFIRM_RESULT, FORGOTTEN, FORGOTTEN_ONE, NOT_HAD,
ABSTAIN_MISSING, UNKNOWN_ENTITY, AMBIGUOUS, BROKEN_CHAIN, YESNO_YES,
YESNO_NO, YESNO_NOTKNOWN, REVERSE, ANSWER, ANSWER_LIST, SELF_PEOPLE,
SELF_FACTS, SELF_SLEPT, SELF_TURNS, SELF_ANSWERED. Passthrough lines never
change (M2b, M3).
- **SAVED:** as 241 ("Saved: " + affirm form). Exact repeats said once,
  also across the saved value and the "also have" list.
- **CONFLICT:** "My notes say <affirm OLD>. Do you want me to change it to
  NEW-as-a-value?" NEW rendered with article/units/capital (say_kind
  name, all-lowercase only; particles van/von/de/da/di/du/der/la/le/bin/al
  exempt; internal capitals kept). Stored value never changes. Number rows
  use the bare noun form (no invented units).
- **FORGOTTEN_ONE:** "OK, I've forgotten that <affirm-lowered>." The value
  is never the subject of "is"; the bare "{NP} is {V}." clause is always
  available; a title keeps its "The".
- **NOT_HAD / FORGOTTEN / ABSTAIN_MISSING / ANSWER / YESNO_* / REVERSE:**
  as 241, plus REVERSE "are" for plural-looking common values.
- **BROKEN_CHAIN:** "<NP> is <V>. I have nothing saved about <about>, so I
  can only follow the chain this far." with <about> = the value for kind
  name, "that" otherwise. Correct for person/place/organisation/thing/
  date/number. Keeps "i can only follow", no clarify bit.
- **AMBIGUOUS:** "I know more than one X: <full names, no codes>. Which one
  do you mean?" Identical-name lines pass through unchanged and are
  counted (owner: ambiguity handler).
- **ANSWER_LIST / YESNO_NO / YESNO_NOTKNOWN / SAVED also-have:** exact
  repeated items said once ("rowing and rowing" -> one item; with one
  distinct value the list becomes singular "is").
- **SELF_PEOPLE:** as 241, plus a base "you" in place is the user (said
  "you", listed first, never capitalised mid-list).
- Brief item g (optional) is NOT done: "Saved:" keeps its capital
  (238 LOWERCASE_START requires it) and s/x/z names keep the of-form
  (possessive gave "Electronic Arts's"-type risk on suite lines).
- Dev-pilot counts (dev material, not registered): 241 sweep re-rendered
  through A v2 changed 209 lines (SAVED 1, CONFLICT 20, FORGOTTEN_ONE 67,
  BROKEN_CHAIN 80, YESNO_NO 3, YESNO_NOTKNOWN 2, ANSWER_LIST 6,
  AMBIGUOUS 30); all 1205 frames route A; sub-marks 0. Dev suite moves
  (241b vs 138i): rt136 45, rt143 24, sessions152 60, bench 623, all
  reply-only, GATE clean; changed reply lines by act SAVED 3953,
  CONFLICT 721, ANSWER 673, ABSTAIN_MISSING 7; 0 legacy, 378 passthrough.
  Dev sweep render of the FRESH seed (--dry): 1205 items, all route A,
  0 unused rows.

## 4. Registered marks (bars from the 241b brief)

- **M1 grammar ≥ 99%.** Fresh sweep (≈1,200 replies, SEED241B, same strata
  and act blocks as 241: 13 row acts × 80 + DUPLICATE 4 + CONFIRM 4 +
  UNKNOWN 30 + AMBIGUOUS 30 + SELF_PEOPLE 40 + 1 director case +
  SELF_FACTS 20 + SELF_SLEPT/TURNS/ANSWERED 12 each; fillers without
  replacement inside each reply; ≥ 30 AMBIGUOUS; no identical-name
  AMBIGUOUS since the base cannot produce them, D14). Graded by the
  director's independent graders with the style sheet in §6.
  **Bar:** ≥ 99.0% grammatical overall AND ≥ 97% in every act stratum,
  plus every mechanical sub-mark (§2) at 0.
- **M2 unfaithful = 0.** (a) Fresh sweep: every reply route A and passing
  brake v2 rules 1-8 (rule 9 re-run and reported); any sev-1 fails.
  (b) Frozen suites: legacy(frame) == base line on route-A lines and
  re-render gives the 241b line; unframed/legacy lines byte-identical
  (identical-name AMBIGUOUS passthrough counts as passthrough).
  (c) Notebook event logs identical after D1 normalisation.
  Tool: claude_mouth241b_check.py m2a / m2b / m2c.
- **M3 frozen suites: only predicted moves.** fable_suitediff218 --only
  rt136,rt143,sessions152,bench --base 138i through
  claude_mouth241b_suites.py (--scorer241b for the 241b run only).
  0 correct→wrong, 0 flips toward abstain (any flip run alone 5×).
  Moves only reply-only on route-A lines of §3 acts. GATE clean.
  241b rows scored with NEW-1, base rows with the frozen versions.
- **M4 naturalness.** 120 fresh pairs (PAIRS_SEED241B, stratified by act),
  fresh judge. **Bar:** 241b wins ≥ 70% of non-tie pairs AND loses ≤ 10%
  of all pairs. Meaning-change flags investigated under M2.
- **M5 latency.** Render median ≤ 2 ms and p99 ≤ 20 ms (1 thread) over the
  fresh sweep; suite wall within +5% of 228 under the D6 protocol (median
  of 3 alternated runs; check load first). Dev: sweep-render median
  0.180 ms p99 1.423 ms; in-suite mean 0.239 ms/line (sum 1.83 s over
  7646 lines); dev wall 241b 29.0 s vs 228 31.5 s (single runs, load ~100).
- **S1 anchor identity: 100%.** NEW-1 reproduces the frozen verdicts on
  every saved protocol-v3 bench row it replaces (228's rows and 241b's
  rows; counts listed, every difference listed). Protocol-v2 rows are
  counted and skipped (not replaced). Dev: 800/800 v3 rows identical
  (721 needle replies), 0 differences, on 241's saved rows.
- **Sleep smoke** (fable_sleepsmoke206.py): identical to 228 except
  agent/label/seconds.
- **Report-only, no bar:** the 241 sweep re-rendered through A v2 (42 old
  misses listed fixed-or-not as mechanical statuses; the builder never
  grades); the rerender238 counts.
- **Verdict:** PASS iff M1, M2 (a,b,c), M3, M4, M5, S1 and the sleep smoke
  all pass. M1 or M4 not scorable (SCHEMA-MISMATCH, exit 3) is VOID.

## 5. Declared interpretations and deviations (fixed before the seal)

- **D1-D12** as in 241's PASSMARKS (event-log normalisation; M3 base
  138i with 228 at 0 moves; M2b re-render with names removed; M4 pairs
  from a single 241b run with no dialog context shown; rule-7 reader aids;
  D6 alternating wall protocol; sev-1 allowed on suites, failing on the
  sweep; display nouns; repeated-3-gram relation-word exemption;
  rerender238 post-seal report-only; run order sweep → pairs → SEAL2 →
  M2a/M5 → M3/M2bc + walls → sleep → rerender238 → scoring).
- **D13, _r copies (dev-only, unsealed, not on the registered path):**
  (1) scripts/claude_mouth241b_rer241_r.py — copy of
  claude_mouth241b_rer241.py with --old-dir/--out flags, because the
  original hardcodes the sealed 241 dir (absent here); used for the dev
  pilot against /tmp material. (2) scripts/claude_mouth241b_devrender_r.py
  — new dev renderer (sweep-frames → 241b texts) feeding m2a/m5 on /tmp
  material. Reason for both: additive-only forbids editing the originals
  and the seal must stay free of dev outputs.
- **D14, identical-name AMBIGUOUS:** the 228 base cannot store two
  entities under the same full name (builder probe), so the generator
  emits no identical-name AMBIGUOUS lines; the passthrough is covered by
  unit tests (b241_ambiguous, b241_ambiguous_identical_counted_by_mixin).
- **D15, brief item g not done** (§3): optional, and both halves showed
  risk on suite lines, so omitted with no replacement.
- **D16, rule-7 cache safety:** the SHAPE cache reuses only PASS results
  keyed by template + slot shape; any MISS is recomputed through the full
  reader; a failed round trip still falls back to legacy_text as sev-1
  (unit test b241_shape_cache_equals_reader checks cache == reader over
  shared shapes; dev suites show 0 legacy lines).
- **Deviations at seal:** none. 29/29 unit tests pass under the uv prefix;
  say table rebuilds byte-identical; the fresh-seed --dry pilot renders
  1205/1205 route A with 0 unused rows.

## 6. Grader style sheet (the director's own file, copied verbatim)

STYLE SHEET v2 FOR GRADING GRAMMAR (exp 241b, M1). The director sealed it on 2026-09-22, before any 241b sweep existed. It is v1 (241-stylesheet.txt) plus the clarifications marked NEW, which make grading stricter or more consistent, never more lenient.

You grade one reply at a time: GRAMMATICAL or UNGRAMMATICAL, with a short reason.
- A reply is UNGRAMMATICAL if ANY sentence in it breaks any rule below, or is not standard written English.
- Grade grammar and word choice only. A stiff but correct sentence ("Tarno's city is Vell.") is GRAMMATICAL.
- Never judge whether a fact is true, or whether a value is sensible for its relation. Names and values are made-up words and may look odd; that alone is never an error.

House rules. Breaking any of these is an error.
1. Possessives
   - A singular name takes 's, including names ending in s, x or z ("Tomas's", "Brix's").
   - A bare apostrophe after a singular name ("Tomas' job") is an error.
   - A plural common noun ending in s takes a bare apostrophe ("the parents' house"); "parents's" is an error.
   - An "of" form or a verb form that avoids the possessive is fine.
2. Lists
   - Write "A and B" and "A, B and C". No Oxford comma: "A, B, and C" is an error.
   - No empty slots ("people: .", "A, , B", "and .") and no stray separators.
   - NEW: the same item twice in one list ("rowing and rowing") is an error.
3. Numbers in running text
   - Counts 0–9 are words ("three sisters"); 10 and up are digits.
   - Digits inside a value (a date, a year, an age, a phone number, an address, a code) are fine.
   - A bare zero count ("0 people", "zero people") is an error. Say "no one", "nobody", "none" or "I don't know anyone".
4. Agreement
   - Count and noun agree ("one person", "two people"); "1 people" and "2 person" are errors.
   - Subject and verb agree ("X lives", "they live"; "does X live", not "does X lives"). This includes a value used as a subject: "noodles is" is an error.
   - Verb forms are right ("was born", not "is born" for a birth; "has worked", not "has work").
5. Articles
   - Use "a" before a consonant sound and "an" before a vowel sound, going by sound ("an hour", "a university", "an MBA").
   - No missing article where English needs one ("X is teacher" is an error) and no doubled article.
6. Sentence form
   - Each sentence starts with a capital letter and ends with . ? or !
   - No doubled words ("the the"), no missing words, and no run-on sentences joined only by a comma (comma splices).
   - Brackets and quotes are balanced.
   - A question is phrased as a question and ends with "?".
7. Typography: no space before punctuation, no doubled punctuation ("..", "?.", ".,"), no double spaces, and no leading or trailing space.
8. No machine text
   - Raw keys, underscores or placeholders ("date_of_birth", "{name}", "<X>", "None", "null", "[]") are errors, unless the user's own words contained them.
   - NEW: internal entity codes such as "(E7563)" are machine text and an error.
9. "(worked out backwards)" follows the statement it qualifies, inside or right after the same sentence. A dangling, doubled or orphaned one is an error.
10. Pronouns
   - "I/me/my" for the assistant and "you/your" for the user are fine. Singular "they" is fine.
   - Pronoun choice is not a grammar error unless it breaks agreement or has no clear referent in the same reply.
11. NEW: Names and word choice
   - A value that is plainly a proper name (a person, place, organisation, or the title of a work) starts with a capital letter, even if it looks typed in lowercase. A title keeps its own capital "The" ("the Quiet Tide" inside a sentence is an error when "The Quiet Tide" is the title).
   - Other values (jobs, foods, hobbies, colours, dates) are not judged for case.
   - Words must fit what they refer to: "someone/who" for people, "something/which" for things, places, dates and numbers. "Krellwur Press, which is not someone I can look up" is an error.

Output for each reply: id, GRAMMATICAL or UNGRAMMATICAL, and a reason. The reason names the rule number (or "general" for other standard-English errors) and quotes the exact offending words.

## 7. Predictions (also appended to the ledger as P241b.n)

- **P241b.1:** M2(a), (b) and (c) each have 0 failures.
- **P241b.2:** M3: GATE clean; every suite move is reply-only on a route-A
  line of a §3 act (expect ≈ rt136 45, rt143 24, sessions152 60,
  bench 623); 0 verdict changes; 0 flips toward abstain.
- **P241b.3:** M5 latency passes with margin (dev median 0.180 ms,
  p99 1.423 ms). The wall is within +5% of 228 under the D6 protocol
  (p ≈ 0.8; dev single runs 29.0 s vs 31.5 s at load ~100, and the
  in-suite mean is 0.24 ms/line against a ~0.3 ms/line budget).
- **P241b.4:** every mechanical sub-mark (§2) is 0 on the fresh sweep
  (p ≈ 0.8; dev re-render 0/1205, but the fresh seed is untested).
- **P241b.5:** M1 grader bar passes (p ≈ 0.6): all 42 old misses changed
  with 0 sub-mark hits, but the director's graders have not seen the new
  wording. Riskiest: CONFLICT article/capital rendering (style rule 11),
  BROKEN_CHAIN "about X" phrasing, AMBIGUOUS names without codes.
- **P241b.6:** M4 passes (p ≈ 0.65): win ≥ 70% non-tie, losses ≤ 10%.
  241 scored 111/9; 241b wording is closer to natural except the kept
  "Saved:" capital and the of-forms the 241 judge already disliked in 8
  of the 9 losses.
- **P241b.7:** the sleep smoke is identical to 228 (all summary fields).
- **P241b.8:** 0 sev-1 fallbacks on the suites; unframed-line count 378;
  ambiguous_identical 0 on the suites (base cannot produce identical
  full names).
- **P241b.9:** S1 reproduces the frozen verdicts on 100% of the saved v3
  rows it replaces (dev 800/800 on 241's rows); v2 rows counted/skipped.
