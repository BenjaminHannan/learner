# 240 — The mouth: a fluent, faithful reply writer (DESIGN ONLY, Opus 5.5, 2026-09-22)

Nothing was trained, run on the GPU, or changed in code. Every number below
comes from a file in the repo; the file is named next to it. Guesses are
labelled as estimates.

Ben's targets: "Grammar should be 99%+" and "Talking with it should be as
fluent as with a person, or as close to as possible. It shouldn't make simple
mistakes."

---

## 0. What exists today (history and the current reply path)

### 0.1 Earlier mouth attempts

| exp | what | raw unfaithful (before brake) | after brake | status right | where |
|---|---|---|---|---|---|
| 53 | borrowed SmolLM2-360M-Instruct, body frozen, 57.0M trainable adapter (10 record tokens + last block + untied head) | 296/500 | 0/500 | 426/500 (FAIL, bar 480) | artifacts/fable-mouth53-20260921/RESULTS.md, score.json |
| 120 | OUR talker (talker101: 10 layers, d=512, 8 heads, vocab 4096, about 23M params by my count from `CFG` in scripts/fable_talker101_model.py:16) + copy head, fine-tuned on record→sentence pairs | 313/500 | 0/500 | 486/500 | artifacts/fable-talker120b-20260922/RESULTS.md |
| 120b | same, one-character mask fix (`pos > pre` → `pos >= pre`) and retrain | 172/500 | 0/500 | 489/500 | artifacts/claude-talker120b-run-20260922/score.log |
| 120d | statuses the talker never learned go straight to the contract template, not the talker | — | — | routing PASS by diagnostics; the registered runs were BLOCKED (checkpoint missing at the time) | artifacts/fable-talker120d-20260922/RESULTS.md |

What went wrong with the learned mouths:
- **Loops and junk.** 53's raws repeat phrases ("I could not use that: I could
  not use that question: …").
- **Broken names.** 120's copy head copies 1–2 BPE pieces of a 3–4-piece
  name, then drifts: "Fara", "Gide", "Ximenaenaenain". 10 cases were
  truncation-only and 139 had both truncation and boundary bugs.
- **Lost status anchor.** 53's O2 gap is 74 raws that passed the brake word
  by word but lost or changed their status anchor. One of them caused a real
  missed abstention in replay: turn 29, "I found it: Ana's mother's
  mother's…". **The brake only checks words. It does not check meaning.**

### 0.2 The brake as it exists (exact)

`brake_check(sentence, record)` in scripts/fable_mouth53_mouth.py:176. It is
copied almost unchanged into scripts/fable_talker120_mouth.py:211.
1. Records whose kind is not `answer` pass straight through without a check.
2. An empty sentence fails.
3. Every word, lower-cased, with `'s` stripped and quotes trimmed, must be
   in `record_content_words(record)` or in the fixed `FUNCTION_WORDS` list
   (about 600 words, mouth53:48). `record_content_words` takes the words
   from `name`, `relations`, and `fields.{answer, subject, relation, value,
   name, choices, reason, trail, ids, source}`, with underscores turned
   into spaces.
4. A digit token is allowed only if the record has exactly that token.
5. For status OK, the answer string must appear somewhere in the sentence
   (a case-insensitive substring match).
6. If any check fails, the sentence is replaced by `TemplateMouth.say(record)`
   (scripts/fable_wire51_adapters.py:182).

What it does **not** check: the status or dialog act (the 53 O2 hole),
negation ("not" is in FUNCTION_WORDS, so "X is not Y" passes for OK), the
direction of a relation ("Mira is Ana's mother" and "Ana is Mira's mother"
use the same words), whether a slot was dropped (only the OK answer is
required), counts written as words, repetition loops, or length.

### 0.3 How 138i builds replies today

There is **no single place** where a (dialog act, facts, flags) frame
becomes text. There is one place for *structured answers* and one place
that *every string* passes through:

1. **The mouth call.** `said = [self.mouth.say(r) for r in records]` in
   `_listening_tick`, at scripts/fable_loop90_agent.py:345 (and in the
   original scripts/fable_agent_loop.py:330). The 138i mouth is
   `Label167eMouth(Loop138bMouth())` (scripts/fable_loop138i_agent.py, in
   `build_agent138i`). The layers are:
   - Label167eMouth, which regex-rewrites relation slots (fix167e_label.py:149)
   - ScreenTextMouth148b, which gives fixed screen texts
   - Loop134Mouth, which replaces `_` with a space
   - FakeMouth (fable_agent_loop.py:155)

   **FakeMouth only composes `kind == "answer"` records.** For those it
   writes the OK line as `"'s ".join([name] + relations) + " is " + answer`,
   which is where "Juniper Lane Books's owner is Silas Wendt." comes from.
   Everything else is `C.Result(status, fields).say()` using `TEMPLATES`
   (scripts/fable_notebook_contract.py:76–87). Records of kind
   `write`/`clarify`/`note` arrive as **finished text**, which the mouth
   passes through unchanged (Saved/Conflict/Forgotten from
   fable_listening_m1.py, 154b multi texts, clarifies, hearsay).
2. **Rewrites after the mouth,** in `Loop138hAgentLoop._listening_tick`
   (fable_loop138h_agent.py:~205–247). These are the 173 user-name rewrite,
   the 166 "me" rewrite and the 166c Title-case pass. The 154d yes/no tick
   is added in 138i.
3. **Turn-level replies that skip the mouth.** `Loop138AgentLoop.turn`
   (fable_loop138_agent.py:~229–275) returns either self99/168 live-state
   answers ("I know {n} people: {…}.", fable_self99.py:425, which is the
   "I know 0 people: ." bug) or `HONEST_DECLINE + DECLINE_SUFFIX`.
   Loop138h.turn then scrubs the raw USER key. Later bases add more of
   these: 221 table asks ("(worked out backwards)"), 224 declines, 226
   "who told you", 227 identity sheet, 233/234 polite and small talk.

The 238 inventory (artifacts/claude-grammar238-20260922/codetemplates.jsonl)
already lists **788 template strings in the code**. Most are made up of
self99 (114), bench73 (72), decline224 (60) and 221c (26).

**The one place a mouth can sit today without editing any file:** a mixin at
the front of the *outermost* loop class's `turn()`. By then every reply
string exists. `self.last_records` and the turn text are available, and
nothing downstream changes the strings again. There it can:
(a) build a frame directly from structured `answer` records, and
(b) **parse back** the known template shapes (the same regex technique
167e already uses on 5 templates) into frames. Lines it cannot parse pass
through byte-identical and are counted as *unframed*. Later, layers can
emit frames natively (`record["frame240"]`) and the parse-back shrinks.

---

## 1. The interface: the meaning frame

### 1.1 Frame (input), JSON

```json
{
  "act": "ANSWER",                     // enum, table 1.3
  "subject": {"text": "Juniper Lane Books", "kind": "organization",
              "role": "third|user|self", "id": "E0012"},
  "relation": {"key": "owner", "path": ["owner"], "table_row": "owner"},
  "values": [{"text": "Silas Wendt", "kind": "person", "id": "E0031"}],
  "polarity": null,                    // "yes" | "no" for yes/no acts
  "count": null,                       // int for counts (0 allowed)
  "inverse": false,                    // true => keep "worked out backwards" meaning
  "provenance": "taught",              // taught | worked_out_backwards | chain | web_verified | sleep_derived
  "abstain_reason": null,              // missing_fact | unknown_entity | broken_chain | ambiguous |
                                       // not_understood_question | not_understood_statement |
                                       // hearsay | screened | bad_request | not_allowed | error
  "choices": [],                       // [{text, id}] for AMBIGUOUS
  "old_value": null, "new_value": null,// CONFLICT / CORRECTED
  "also_have": [],                     // 154b "(I also have ...)" list
  "chain": [],                         // shown path for chain answers [(subject, relation, value), ...]
  "notes": [],                         // e.g. "dropped_question"
  "user_wording": {"wh": "Where", "verb": "live", "text": "Where does Kestrel live?"},
  "fixed_text": null,                  // FIXED acts: pre-approved literal (identity sheet, small talk)
  "legacy_text": "Juniper Lane Books's owner is Silas Wendt."  // today's string, last-resort fallback
}
```

Rules:
- `user_wording` may only be used to **choose a surface form** (for example,
  answer "Where does Kestrel live?" with "lives in", not "city is"). Its
  words are allowed in the reply only if they are in this relation's table
  surface list. It never adds content.
- Values are always lists. Single-valued relations have length 1, which
  keeps list joining in one code path.

### 1.2 What it returns

```json
{"text": "Silas Wendt owns Juniper Lane Books.",
 "route": "A" ,               // A | B | C | legacy | passthrough
 "brake": {"ok": true, "fails": []},
 "frame_id": "sha256 of canonical frame"}
```
The mouth is a pure function: frame in, text out. It has no notebook
handle, so it **cannot write**. It is deterministic for a given frame and a
given `variant_seed`, which is 0 by default.

### 1.3 Every reply type the base produces, and its frame

| # | act | today's example (source) | frame slots used |
|---|---|---|---|
| 1 | ANSWER (1 hop) | "Mira's city is Oslo." (FakeMouth) | subject, relation, values, provenance |
| 2 | ANSWER multi-hop | "Tom's dentist's best friend is Zed." | subject, relation.path, values |
| 3 | ANSWER_CHAIN (path shown) | 231 chain replies | chain, values |
| 4 | ANSWER_INVERSE | "Oslo is the city of Quilla." (138i reverse) / "Quilla's city is Oslo. (worked out backwards)" (221) | subject=asked value, relation, values=found subjects, inverse=true |
| 5 | ANSWER_LIST (multi-valued) | "Saved: …" + "(I also have X and Y.)" (154b) / language lists | values[], also_have[] |
| 6 | ANSWER_YESNO | 154d grounded yes/no; 230/230b name check | polarity, subject, relation, values (the stored value) |
| 7 | ANSWER_WEB | "… (I read that online; you didn't tell me.)" | provenance=web_verified |
| 8 | ABSTAIN missing_fact | "I don't know Ada's place of birth." | subject, relation |
| 9 | ABSTAIN unknown_entity | "I don't know anyone called Zed." | subject |
| 10 | ABSTAIN broken_chain | "Ana's city is Porto, which is not someone I can look up." | subject, relation, values |
| 11 | CLARIFY ambiguous | "I know more than one Priya: … Which one do you mean?" | subject, choices |
| 12 | SAVED | "Saved: Mira's city is Oslo." | subject, relation, values |
| 13 | DUPLICATE | "I already have that." | (subject, relation, values if known) |
| 14 | CONFLICT_CONFIRM | "I have X's city as Oslo. Do you want me to change it to Bergen?" | subject, relation, old_value, new_value |
| 15 | CONFIRM_RESULT | "Okay, I left it as it was." / corrected | polarity, subject, relation, value |
| 16 | FORGOTTEN / NOT_HAD | "Forgotten: Ada's city." / "I don't have …" (154b) | subject, relation, values? |
| 17 | NOT_SAVED hearsay | HEARSAY_MSG (loop102:70) | abstain_reason=hearsay |
| 18 | NOT_SAVED screened | 148b / 171 / 209 screen texts | abstain_reason=screened, subject?, relation? |
| 19 | DECLINE | HONEST_DECLINE+suffix, 224b decline family, "Was that a question?" | abstain_reason=not_understood_* |
| 20 | BAD_REQUEST / NOT_ALLOWED / ERROR | contract :86–87, "I could NOT save that…" | abstain_reason, reason (fixed phrase) |
| 21 | SELF_STATE | "I know {n} people: …" (self99:425), facts taught, mode | count, values[] |
| 22 | USER_NAME | "Your name is Juno." / "You never told me your name." (173/219) | subject.role=user, values / abstain |
| 23 | SOURCE | 226 "Who told you that?" | provenance per fact |
| 24 | FIXED | identity sheet 227/227b ("My name is Premonition."), small talk 234, polite 233 | fixed_text only |
| 25 | NOTE prefix | "(I dropped my earlier question.)" | notes[] |
| 26 | PROMPT | "Please answer yes or no." / "pick <ID>" | fixed_text |

---

## 2. Three options compared

| | (A) hand-made grammar layer | (B) borrowed decoder (SmolLM2-360M + brake) | (C) our talker (120 line + brake) |
|---|---|---|---|
| Grammar | ≥ 99% is reachable, because each form is written and tested once; the risk is only in untested fillers | Fluent when it passes, but raws loop and truncate (53) | Worse English than B (about 23M params, SimpleStories-style pretraining); name truncation |
| Naturalness | Good, but repetitive (a few forms per act) | Best possible variety | Some variety, weaker English |
| Faithfulness risk | ~0 by construction, and round-trip testable (§4.7) | High raw (296/500); safe only behind the brake | High raw (172/500); safe only behind the brake |
| Mac CPU latency | < 1 ms (string functions; estimate) | **measured 0.85 s/reply amortised**: 423.38 s for 500 records at batch 8, 1 thread, ≤ 32 new tokens (fable-mouth53 score.json + PASSMARKS "OMP_NUM_THREADS=1"). A single unbatched reply (the demo case) will be slower than that; **estimate 1–2 s at 1 thread**, to be measured in that stage's pilot | **measured 0.33 s/reply**: 166.86 s for 500 records including brake and fallback, 1 thread (`torch.set_num_threads(1)`, talker120_mouth.py:381), no KV cache, ≤ 32 tokens (claude-talker120b-run score.log) |
| Build effort | Small–medium: a per-relation say table for 150 rows (50 already have teach verbs in relation_table_v1_1.json), morphology helpers, parse-back regexes | Medium: data + adapter retrain + brake v2; the old adapter exists | Medium: data + retrain on the GPU (18 s for 470 steps, train-summary.json) + brake v2 |
| Ben's own-architecture rule | Fully ours (plain software, no borrowed weights) | Placeholder only | Ours |

---

## 3. Recommended path, in stages

1. **Exp 241 = A: the floor.** Build a grammar layer plus per-relation say
   forms at the outermost `turn()`, with parse-back of known templates and
   the brake v2 run on A's own output as a self-check. It fixes the grammar
   Ben sees now, can't make up content, costs almost nothing in speed,
   and becomes the fallback every later stage needs.
2. **Exp 242 = native frames.** The most common reply layers (answer,
   saved, abstain, self99 counts, 221 inverse) attach `frame240` to their
   records directly, so parse-back shrinks to a legacy net. Measured by an
   "unframed lines" count that must fall.
3. **Exp 243 = C, delexicalised.** Our talker writes *slot templates*
   ("{S} lives in {V}, as far as I know from you."), not names. Code fills
   the slots and applies A's morphology. This removes the name-truncation
   failure entirely, and the talker's copy head is no longer needed. Brake
   v2 falls back to A on any failure. Train on the 5070 Ti.
4. **Exp 243b = B as a time-boxed comparison arm,** with the same
   delexicalised data and the same brake. It is used only if C's raw
   pass-rate stays under the bar and Ben wants the extra fluency for the
   demo. Labelled a placeholder, on the same interface.
5. **Later:** a variety knob (a seeded choice among vetted forms) and
   whole-turn joining (two facts in one sentence) only when brake v2's
   round-trip check covers joined replies.

Why this order: the learned stages can only be trusted when they fail
safely, and failing safely means falling back to something good. Today that
fallback is the robotic template. Build A first and every brake fallback
becomes a good sentence. A also defines the say forms and morphology the
delexicalised learned mouth reuses, and it gives the pairwise judge a
strong baseline. C comes before B because of Ben's rule and because C is
about 3–6× faster on the Mac (0.33 s measured vs 0.85 s amortised /
1–2 s estimated). Delexicalising removes C's worst weakness, broken names.

### 3.1 A in detail (what 241 builds)

- **Say table** (a new file, e.g.
  artifacts/claude-mouth241-20260922/say_forms.json), one row per relation
  in relation_table_v1_1.json (150 rows). Each row has:
  - `affirm`: 1–3 forms with slot roles. For example, owner:
    "{V} owns {S}." and city: "{S} lives in {V}."
  - `abstain_missing`: "I don't know who owns {S}." or "I don't know where
    {S} lives."
  - `inverse`: "{V} lives in {S}. I worked that out backwards from what you
    told me."
  - `yes`/`no` forms.
  - `user` forms (you/your) and a `self` form.
  - A `possessive_ok` flag.

  Direction (who owns whom) is written per row and **checked by the round
  trip** (§4.7), so no one has to trust it by eye.
- **Morphology helpers** (pure functions, unit-tested):
  - `a`/`an`: decided by sound, with an exception list (an hour, a
    university, an MRI, a one-off).
  - No article on proper names. The article for common nouns depends on
    `value_kind` (job: "a baker").
  - Possessive: `X's` for any singular name, including names ending in s
    ("Silas's"). Plain `'` only for plural common nouns. Prefer the verb or
    "of" form when a name ends in s/x/z ("the owner of Juniper Lane
    Books").
  - Lists: "A", "A and B", "A, B and C". A sealed style choice: no Oxford
    comma, matching join_and154b.
  - Counts: 0 → "I don't know anyone yet." or "You haven't taught me any
    facts yet."; 1 → singular noun and verb; many → plural. Numbers 0–9
    are written as words in running text and 10+ as digits; IDs and dates
    are copied verbatim.
  - Pronouns: only I/me/my (self) and you/your (user). **Never he/she/they
    for a third party.** Gender is knowledge the notebook doesn't have.
  - Sentence case and the final punctuation are fixed once, at the end.
    Title-case display overrides from 166c are respected.
- **Fixed acts** (identity sheet, small talk) pass through unchanged. They
  are still graded for grammar, and any failures there are listed for their
  owners, not rewritten.
- **Unframed lines** pass through byte-identical and are counted.

---

## 4. The brake, exact spec (v2; applies to B/C output, and to A as a self-check)

Input: the frame, a candidate text, and A's render of the same frame (the
reference). The text is tokenised by the same `_WORD` regex as today, plus
punctuation, with curly apostrophes normalised.

1. **Shape.** 1–2 sentences, ≤ 40 word tokens, no repeated 3-gram, no
   underscores, and no raw keys (USER, E-ids unless the act is AMBIGUOUS,
   `<…>` markers).
2. **Slot coverage.** Each *required* slot for the act (table 1.3) must
   appear as a whole-token match (ignoring case, `'s`/`'` allowed as a
   suffix): subject, every value, every choice name **and** its id, old and
   new values, and every chain element. Numbers must be exact (rule 4).
   Nothing may be dropped. With delexicalised B/C, each placeholder must
   appear **exactly once** before filling.
3. **No extra content.** Every token must be in: the frame's content tokens,
   the closed function-word list (today's list minus content-like words such
   as "taught", "online", "saved", which move into act lexicons), **this
   act's** phrase lexicon, or **this relation's** surface lexicon from the
   say table. Also:
   - Any capitalised token that is not at the start of a sentence and not
     in the frame fails.
   - Any entity name from the running notebook's entity list that is not
     in the frame fails. The brake gets a read-only name set; it never
     writes.
4. **Numbers.** Collect digit tokens and number words (zero…twenty, once,
   twice, none, no one, a couple, several, many, few). The set of numbers,
   after mapping words to digits, must equal the frame's (count, ids, date
   parts). Vague quantifiers are not allowed where the frame has a count.
5. **Negation and polarity.** Negators are: not, n't, no, never, nobody,
   nothing, none, neither, nor, cannot, without. The candidate's polarity
   class (affirmative or negative) must equal the reference's. For yes/no
   acts, the first word must be "Yes" or "No" and equal `polarity`.
6. **Act anchor.** A rule classifier (an extended `classify`) must read
   the candidate as the same act family as the frame. This closes the 53
   O2 hole. It also enforces:
   - abstain stays abstain;
   - an inverse answer must contain a backwards anchor from {"worked out
     backwards", "worked that out backwards", "worked it out backwards"};
   - a web answer must contain "online";
   - a hearsay or not-saved reply must say that nothing was saved.
7. **Round trip (meaning check).** For acts with a (subject, relation,
   value) triple: feed the candidate as a *statement* to the base's
   rule-based ears (the table teach parser) with a throw-away scratch
   notebook and a stub doorway that records the proposed triple but
   **writes nothing**. The recovered triple must equal the frame's, which
   catches reversed direction ("Ana is Mira's mother"). If the parser
   can't read the candidate, the candidate fails, because we then can't
   check its direction. Questions, abstains and fixed acts skip this
   check; rules 2–6 cover them.
8. **Banned claims.** No "I think", "probably", "I remember", "I guess",
   "maybe", or "as everyone knows". No "you told me" unless provenance =
   taught. No "I saved" unless the act is SAVED.

**Fallback:** any failure → A's render. If A's render fails its own check
(an A bug) → `legacy_text`, logged as a sev-1 bug. Every fallback records
(act, rule number, token) for the report. The brake is plain software and
fast (under 1 ms, excluding rule 7's parser call, which is the base's
existing rule ear).

---

## 5. Data plan for the learned stage (243/243b)

- **Frames are generated, not taken from notebook/ or conversations.** A
  generator samples every act × relation row × filler class from
  **fictional** pools (e.g. Kestrel Anwick, Juniper Lane Books, Tillmarsh,
  Zoë Quarrin), with train and test name/value pools disjoint (asserted, as
  120's data script does). Tricky fillers are included on purpose:
  - names ending in s/x/z
  - multi-word and "The …" organisations
  - names with an apostrophe or hyphen, and diacritics
  - vowel-initial common nouns ("engineer", "usher", "hour")
  - lowercase values
  - counts 0/1/2/7/12
  - lists of 1/2/3/5
  - user and self subjects
  - inverse and web provenance
- **Targets:**
  - (a) A renders, all variants.
  - (b) Paraphrases written by Qwen on BensPC, local, no internet. **Qwen is
    shown only the delexicalised A sentence** ("{S} lives in {V}."), so no
    real or notebook data can reach it, and it is asked for N rewrites.
  - (c) Every candidate goes through brake v2 with fillers substituted, the
    grammar grader (§6), and a dedupe; the rejects are logged.
- **Never used** for training or tuning:
  - repo-root notebook/
  - reading94 and reading94b
  - fable-naturalpanel208
  - claude-tablepanel221
  - the 239 conversation panel
  - the 221b/229/230b/236 blind panels
  - 238's sweep items
  - test.pt

  The data script machine-checks that no string from those files appears
  in train.jsonl (string-overlap scan, which reads hashes of n-grams only
  and never prints the panels).
- **Splits:** train, validation (same acts, held-out fillers), and a
  held-out *form* split (paraphrase templates never seen in training).

---

## 6. Registered marks for exp 241 (= A), to be sealed by a separate agent

Base: 138i + 228 guard (SrcGuardMixin228 first in the daemon bases), or the
newest accepted merge at seal time, named in PASSMARKS. Mouth241 is one
mixin at the front of the outermost loop class. No existing file is edited.

- **M1 grammar ≥ 99%.**
  - **Sweep:** every act in table 1.3 × every relation row that act can
    take (150 rows) × 4 tricky-filler classes. Stratified to about 1,200
    rendered replies, with fictional fillers from a pool the builder never
    tunes on (generated with a sealed seed after the say table is sealed).
  - **Grader:** an independent agent that has not seen the code or the say
    table. It marks each reply grammatical or ungrammatical with a reason,
    using a sealed style sheet: possessive `X's` for singular names, no
    Oxford comma, and numbers 0–9 as words.
  - **Bar:** ≥ 99.0% grammatical overall **and** ≥ 97% in every act
    stratum.
  - **Also required (0 each):** "s's" on plural common nouns, "a" before
    a vowel sound (or "an" before a consonant sound), empty list slots
    ("people: ."), bare "0 X" counts, raw underscores or keys, and a
    dangling "(worked out backwards)".
  - When 238 lands, its bug list for acts A covers becomes a sub-mark
    (every covered item fixed). Items outside A's scope are listed before
    sealing.
- **M2 unfaithful = 0.**
  - (a) On the sweep, every A reply passes brake v2 rules 1–8 against its
    frame, including the round trip (7) for every triple act.
  - (b) On the frozen suites, every framed line's parse-back frame equals
    the frame A rendered, and every unframed line is byte-identical to the
    base.
  - (c) Notebook event logs are byte-identical between base and 241 on every
    suite run, so the mouth caused no writes.
  - Bar: 0 failures in each of a, b and c.
- **M3 frozen suites: only predicted moves.** Run
  `scripts/fable_suitediff218.py --only rt136,rt143,sessions152,bench`.
  - Correctness verdicts: **0** correct→wrong, 0 flips toward abstain or
    "Was that a question?" (guard installed; any flip is run alone 5
    times and reported).
  - Reply-text moves are allowed only in classes pre-registered by act.
  - **Before sealing, the builder lists every substring the frozen scorers
    and 224a's shared decline detector match on** ("Saved", "I don't
    know", "not someone I can look up", "more than one", "worked out
    backwards", etc.). A forms must keep those anchors, or the move is
    pre-registered as a scorer change with an explanation. The GATE line
    must read clean.
- **M4 naturalness, blind and pairwise.**
  - A separate judging agent (not the builder, not the grader) sees 120
    pairs, stratified by act. Each pair is one user turn with today's base
    reply and the 241 reply, in random order, labelled X/Y, plus the
    frame's facts so it can flag meaning changes.
  - It picks the more natural reply, or a tie.
  - Bar: 241 wins ≥ 70% of non-tie pairs **and** loses ≤ 10% of all pairs.
  - Any meaning-change flag is investigated under M2 and counts as
    unfaithful if confirmed.
- **M5 latency.** Mouth overhead per reply on the Mac CPU (1 thread),
  measured over the sweep: median ≤ 2 ms and p99 ≤ 20 ms (rule 7's parser
  call included). Suite wall-clock ≤ base + 5%.
- **Also:** the sleep smoke is identical to the base, and the unframed-line
  count on the suites is reported (no bar in 241; 242 must lower it).

Predicted moves, to be registered: every OK/SAVED/abstain line whose
relation has a say form changes wording only; "I know 0 people: ." becomes
a 0-count sentence; possessives on names ending in s go to the verb or "of"
form; no status or storage changes.

---

## 7. Risks, and what this does NOT fix

Risks:
- **The say table's direction.** One wrong row gives a systematic
  unfaithful reply for that relation. The round trip (rule 7) is the guard.
  Rows the teach parser can't read fall back to the possessive form
  ("the owner of Juniper Lane Books is Silas Wendt"), which is safe but less
  natural.
- **Parse-back coverage.** Lines that aren't parsed pass through with
  today's grammar. M1 measures the framed acts, and the unframed count
  shows how much is left.
- **Scorer anchors.** Rewording can break the frozen scorers' substring
  checks and look like a regression. M3 requires listing them first.
- **Repetition.** A deterministic A can sound samey over a long chat. That
  is a later stage (a variety knob), and it is not in 241.
- **Learned stages:** the brake's word lists can still let through a
  subtle meaning shift that rules 5–7 don't model (for example tense:
  "lived" vs "lives"). Mitigation: tense words for other relations are
  outside the allowed lexicon, and anything new found is added as a rule
  with a test.
- **B:** borrowed weights (Apache-2.0) are a placeholder only. At 1–2 s per
  reply (estimate) it is noticeable in a live demo.

What it does NOT fix:
- **Misread requests.** Those are an ears problem: "Was that a question?",
  glued declines on turns the ears didn't read, two-word names in verb
  sentences (232), and "Say my name." hitting the pretend rule.
- Missing knowledge or reasoning errors. The mouth says exactly what the
  reasoner returned.
- Small-talk breadth, opinions and chit-chat beyond the fixed sheet.
- Coreference in *user* turns ("he", "she").
- Anything 239 finds that isn't grammar or wording.
