# 217 — Relation table v1 (design)

Date 2026-09-22. Author: Claude (Opus subagent). Status: **table + checker built, no agent code changed.**

Files:
- `artifacts/claude-relationtable-20260922/relation_table_v1.json` (the table)
- `artifacts/claude-relationtable-20260922/build_table_v1.py` (the readable source it is built from; the audit trail)
- `scripts/claude_relationtable_check.py` (the checker; pure Python, about 8 s)
- `artifacts/claude-relationtable-20260922/check_output.txt` (the checker's output: 6/6 PASS)

## 0. What this is, in one paragraph

Today every English shape the agent understands comes from its own small hand-written piece, and each piece has its own list of relation words. The lists do not agree: "manager" is in none of them, "born in" is stored as `place_of_birth` by one piece and as `birthplace` by another, and the "of" rewrite knows 13 words. The table puts one list in one place. For each relation it gives the canonical name, the value kind, whether it is single- or multi-valued, its true aliases, the keys older code has already stored it under, and simple readable templates for teaching, asking, yes/no, and working out the answer backwards (inverse). The table can be used as rules by the hand-written reader now, and as labels for a learned reader later.

Facts are always `(X, R, Y)` = "X's R is Y". "Blue Rain's composer is Ada Pell." is `(Blue Rain, composer, Ada Pell)`.

## 1. Inventory summary (read-only; no suite was run)

Scope: the 145-module import closure of `scripts/fable_loop138i_agent.py` plus the layer-C pieces (180b, 187, 188, 189/189b, 190/190b, 192, 193, 164b, 154f, 154g). I found it by AST import walk, then read the relation vocabularies. The checker re-reads the 27 named constants below from source by AST on every run, so the inventory cannot silently go stale.

**How the 138i reader works.** The base is `FakeEars` (`scripts/fable_agent_loop.py:109`). It is **open-vocabulary**: any `X's R is Y.` (`:96`) and any `Who/What/Where is X's R?` (`:94`) works, with the key made by `_relation` (`:151`: lower-case, spaces to `_`). Every other piece adds shapes on top, each with its own closed word list:

| Piece (file:line) | What it knows | Live in 138i? |
|---|---|---|
| `fable_agent_loop.py:91` PERSON_RELATIONS | 12 person relations (mother … partner) | yes |
| `fable_bench73_english_arm.py:73` STATEMENT_PATTERNS | 36 bench templates ("The capital of X is Y", "X is the composer of Y" → `composer_of`, "X was composed by Y" → `composed_by`, …) | yes (bench composer stage) |
| `fable_bench73_english_arm.py:131,139` REV_OF_NOUNS / REV_BY_VERBS | reversal questions over `_of`/`_by` keys | yes |
| `fable_bench73_english_arm.py:153`, `fable_bench92_english_arm.py:72` cue maps | question cue substrings per bench relation (recall-biased, **not synonyms**) | yes |
| `fable_bench92_english_arm.py:58` | employer ("is employed by"), occupation, child, head_coach, broadcaster, director_manager | yes |
| `fable_fix167_verb.py:63,70` | lives in → city, works for → employer, was born in → place_of_birth; 3 verb questions | yes |
| `fable_fix167d_verb.py:67,72` | works at → employer, speaks → language; 2 verb questions | yes |
| `fable_fix166_me.py:62,71` | "my R" asks; mom/mum/dad/… → mother/father | yes |
| `fable_fix174_chainof.py:50` REL174 | "Who/What is the R of X?" for **13 words only** (no manager, employer, composer, …) | yes |
| `fable_fix154_yesno.py:64,84,85,89` | yes/no shapes; 11 relations where "No" is allowed | yes (via 154d) |
| `fable_fix154c_allowlist.py:37`, `fable_fix154e_allowlist.py:27` | 22 + language multi-valued keys | yes |
| `fable_fix171_nameval.py:48` NAME_KEYS | 21 keys whose value must be a name | yes |
| `fable_fix139e_tail.py:57` LISTED_RELATIONS | 22 person/place keys | yes |
| `fable_fix153_reverse.py:75-88` | "Whose R is Y?" and similar | yes |
| `fable_loop158c_agent.py:84` (called at `fable_loop138g_agent.py:225`) | "What city/town does X live in?" → city | yes |
| `fable_loop158b_agent.py:77-95` | **When** is X's birthday/anniversary, How old, Where from, Where live | **no** (`fable_loop138g_agent.py:231-236` says the table is absent) |
| `fable_fix155_inverted.py:91-95` | "Y is X's R", "Y is the R of X", "The R of X is Y" | **no** (loop155 kept out, `fable_loop138i_agent.py` header) |
| `fable_fix190_reverse.py:69,103` | 25 reverse relations; "Who has Y as their R?", "Who lives in Y?", "Who was born in Y?" | layer C |
| `fable_fix193_apos.py:64` | PERSON_RELATIONS + city | layer C |
| `fable_fix135_office.py:62` | 8 office relations | yes |
| `fable_listening_english.py:171` RELATION_MAP | 58 surfaces → 13 keys (Qwen listening path, not the 138i FakeEars path) | not the 138i path |
| `fable_reasoner50.py:76` CORE8 | best_friend, doctor, neighbour, … | reasoner tests |

Layer-C pieces 180b, 187, 188, 189/189b, 192, 164b, 154f and 154g hold **no relation vocabulary of their own**. They handle known-name matching, self-question routing, the statement fallback, "say again", correction wording, "about X", negation and "No," corrections. They reuse `FakeEars._relation` and the sets above.

**Disagreements the table has to settle:**
- `born in` is stored as `place_of_birth` (167) and as `birthplace` (138g/190/listening).
- `from` is stored as `origin` (listening) and as `hometown`/`home_town` (FakeEars).
- `town` is its own key in 139e but is folded into city by listening and 158c.
- Bench stores creative works three ways: `composer` (possessive), `composed_by` (passive), and `composer_of` (the "X is the composer of Y" template, with **subject and value swapped**). The saved junk "Ada Pell's composer of is Blue Rain." is exactly an `(Ada Pell, composer_of, Blue Rain)` fact rendered by the chat mouth.
- The listening map folds sister/brother into `sibling` and "best friend" into `friend`. Both lose information, so the table does **not** adopt them.

**Suites and bench data** (structured relation fields in `data/open/bench65,92,103,121,132`, plus English turns in `artifacts/fable-redteam136-20260922/cases136.json`, `artifacts/fable-redteam143-20260922/fable_redteam143_cases.json` and `scripts/fable_session152_sessions.py`, which is read as strings and never imported) give 142 keys. The table covers all of them, apart from 16 listed exclusions with reasons: placeholders `never_taught_rel_*`, plurals, one typo, and fragments of relative-clause questions. The speed170 case file that `fable_fix138i_suites.py:152` reads is not present in this worktree.

## 2. The table (v1)

- **101 relations**: 93 known (named in code or data) and **8 NEW** (parent, grandmother, grandfather, painter, designer, architect, nickname, date_of_death). "NEW" means no code or data names the relation. Any relation already works through the open-vocabulary possessive, so for most relations the NEW part is the *shapes*, not the relation.
- **52 aliases** (true synonyms only), **15 extra storage keys**, **13 inverse storage keys**.
- **222 written templates**: 16 generic plus 206 relation-specific (51 of them inverse). By status: 59 live today, 3 layer C, 12 in repo code but not in 138i, **148 NEW**. Expanded over surfaces and question words, that is 3,004 concrete patterns.
- **Generic families** (`possessive`, `my`, `of_form`, `inverted`, `reverse`) apply to every relation that lists them, with `{R}` ranging over the canonical word and every alias. For example, 174's "What is the R of X?" becomes available for all 101 relations instead of 13.
- **Rules carried in the file:**
  - Taught facts win.
  - Inverse phrasings are `never_store` and labelled "worked out backwards".
  - Aliases are true synonyms only.
  - `narrower` is one-way: a wife fact may answer a spouse question, not the reverse.
  - Every storage key is read at question time. If two keys disagree, the reader asks and never picks one.
  - Verb facts are relations (Ben's rule).
  - The open-vocabulary fallback stays.
  - Self questions ("your …") are left to the self router.
- **Decisions worth checking:**
  - `boss` has alias `manager`. `employer` is separate (value kind organisation).
  - "X works for Y" is employer. The rule that a known *person* Y means boss instead is written as a value guard for build 2 only.
  - `director` reads bench `director_manager` (organisations and films). "manager" is **not** an alias there.
  - wife/husband are *narrower* than spouse, not aliases. partner is separate.
  - `city` keeps its historical key and means "place X lives". bench65 `lives_in` is a read-only storage key.
  - `home` and `country` are deliberately not aliased (both are ambiguous).
  - `birthday` ≠ `date_of_birth`: a birthday has no year, and nothing is derived at write time.
  - Date relations carry `strip_leading: [in, on]` and a When question. "born in May" goes to date_of_birth and "born in Oslo" to place_of_birth, decided by a value guard.
  - `occupation` does **not** take "X is a nurse." (too ambiguous; 173b already treats such copulas as non-names).

## 3. Checker result

`OMP_NUM_THREADS=1 python3 scripts/claude_relationtable_check.py` → **PASS on all 6 checks**:
- C1 unique names
- C2 no key owned by two relations
- C3 inverses: `never_store` set, labelled, and every narrower/generic reference exists
- C4 coverage of the 125 code keys and 142 suite/bench keys
- C5 222 templates well formed; date relations carry the rule
- C6 no concrete pattern shared by two relations unless both carry a value guard

Self-test: a deliberately broken copy of the table (a duplicate relation, `boss` as an employer alias, a missing `never_store`, a dangling narrower, `coach` removed, a `{Z}` slot, and a template shared without guards) failed every one of C1–C6 as intended.

Info section: a **table-only** matcher (not the agent) reads each evidence sentence from the task exactly once and correctly:

| Sentence | Table reading |
|---|---|
| "Sam is the boss of Kim." | `(Kim, boss, Sam)` |
| "Lena is the mother of Theo." | `(Theo, mother, Lena)` |
| "Ada Pell is the composer of Blue Rain." | `(Blue Rain, composer, Ada Pell)` |
| "Who composed Blue Rain?" | composer ask |
| "What did Ada Pell compose?" | composer inverse, `never_store` |
| "When is my birthday?" | birthday ask on the user |
| "Pia's birthday is in May." | value "May" |
| "Who works at Acme?" | employer inverse |
| "Tom was born in May." | date_of_birth only |
| "Who is Kim's?" | no reading |

This shows the table *can* represent these turns. It is not evidence about the agent.

**Limits of the checker.**
- Coverage is only as good as the extraction: 27 hand-listed constants plus three simple regexes over suite English. A relation named only in some other module would not be flagged.
- The matcher ignores capitalisation and name-shape constraints, which the real reader will need.

## 4. Pieces the table subsumes

Each piece's word list becomes table data:

| Existing piece | Becomes in the table |
|---|---|
| 167 and 167d verb tables (statements + questions) | teach/ask rows on city, employer, place_of_birth, language |
| 174 REL174 | generic `of_form` ask for all relations |
| 166 `_SYNONYMS` | mother/father aliases |
| 154 SINGLE_VALUED_154 | `yesno_can_say_no` |
| 154c/154e allow-lists | `cardinality` |
| 171 NAME_KEYS, PERSON_RELATIONS, 139e LISTED_RELATIONS | `value_kind` |
| 153/190 reverse sets and shapes | generic `reverse` family + per-relation `inverse` |
| 158b When/How-old/Where-from/Where-live table | date_rule + asks on birthday/anniversary/age/hometown/city |
| 158c wh-city | city asks |
| 193 static relation set | the full table |
| 135 office list | office relations |
| bench73/92 statement patterns and REV maps | teach rows + `inverse_storage_keys` (the bench machinery stays; the table records it) |

**Not subsumed:**
- 132 relative-clause rewriter (multi-hop composition, `fable_loop138b_agent.py:205`).
- The bench cue maps. They are recall-biased substrings ("made", "where", "based") and must never become aliases.
- Hearsay/hypothetical frames (137c/d).
- Value/subject screens (139b, 150, 167b, 171).
- The self router.

## 5. Where a table-driven QUESTION reader plugs in (exact sites)

1. **Ears, outermost.** Add a new mixin before `ChainOf174Mixin` in `Loop138iEars` (`scripts/fable_loop138i_agent.py:336`). Copy the two proven shapes:
   - `ChainOf174Mixin.hear` (`scripts/fable_fix174_chainof.py:112`): make a candidate, probe `super().hear(candidate)`, and accept only if the base returns an `ask`.
   - `Reverse190Mixin.hear` (`scripts/fable_fix190_reverse.py:219`): fire only on an all-clarify base result (`is_all_clarify`, `:200`), read `self.nb` read-only, and reply with **clarify actions only**, so `_act` never writes.
2. **Notebook peeks for alias and storage-key choice.** Use `nb.resolve` (`scripts/fable_notebook_contract.py:235`), `nb.current` (`:244`), and the live taught triples `L90.notebook_triples` (`scripts/fable_loop90_agent.py:101`, which already excludes inferences and superseded rows). Inverse lookup reuses `reverse_subjects190` (`scripts/fable_fix190_reverse.py:149`) generalised to a table key group, and the reply wording of `answer_reverse190` (`:189`) plus the label.
3. **The ask itself stays unchanged.** A forward reading is emitted as the normal `{"act": "ask", "name": X, "relations": [key]}`, so `Loop138bAgentLoop._ask138b` (`scripts/fable_loop138b_agent.py:257`) → reasoner → `notebook.ask` (`scripts/fable_notebook_contract.py:390`) answers or abstains exactly as today. `"my"` subjects use `USER_KEY` like `Me166Mixin` (`scripts/fable_fix166_me.py:49,219`).
4. **Misroutes disappear without touching the router.** `notebook_missed` (`scripts/fable_loop138_agent.py:162`) only lets `route127` (`:247`) fire when every record is a "didn't understand" clarify. Any table reading (an ask, or a labelled inverse clarify) counts as understood. So "Who composed Blue Rain?" can no longer reach "I do not have favourites." and "When is my birthday?" can no longer reach the age text (`scripts/fable_fix168_ground.py:66`).
5. **Later retirement, not in build 1.** These become redundant once the table reader is proven:
   - the question regexes in `fable_fix167_verb.py:96-101` and `fable_fix167d_verb.py:94-97`
   - `rewrite_chainof` (`fable_fix174_chainof.py:61-99`)
   - `rewrite_whcity` (`fable_loop158c_agent.py:84`)
   - 153 reverse frames
   
   Build 1 leaves all of them in place and only adds.

## 6. FIRST BUILD (one change): questions read through the table; writes untouched

**The change.** One outermost ears mixin, `TableAsk217Mixin`, loads `relation_table_v1.json` once. For turns ending in "?" it does two things, both write-free:

- **(a) Base miss.** If the full 138i stack returns all-clarify, it matches the table's ask/yesno/inverse templates.
  - Forward reading → a normal `ask` action.
  - Inverse reading → a clarify action whose text is forward-style sentences plus " (worked out backwards)". Example: "Blue Rain's composer is Ada Pell. (worked out backwards)". Nothing is stored.
  - No reading, or two readings → the base clarify, byte-identical.
- **(b) Base ask on an empty key.** If the base returns an `ask` whose relation key has no current taught value for that subject, but exactly one key in the same table group (canonical, alias or storage key) has one, the relation is swapped to that key. This is how "Who is Kim's manager?" answers from a `boss` fact. If two keys hold different values, it replies with both and asks. It never picks one.

**This fixes (in principle; to be measured):**
- verb questions ("Who composed X?", "Where does X come from?", "When was X born?")
- When questions (birthday, anniversary, dates, including "my")
- aliases (manager/boss, mum/mother, birthplace/place_of_birth, town/city)
- the "of" form for all relations
- answer-time inverses ("What did Ada Pell compose?", "Who works at Acme?"), labelled "worked out backwards"

**Pass marks.** Write them into PASSMARKS before any run. The probe set must be written fresh with fictional names by someone who has not seen the 208 panel.
- **P1 correct answers.** A fresh probe set of ≥ 60 question turns, each after a teach in a shape the agent stores today, covering five families (verb, When, alias, of-form, inverse), ≥ 10 per family. Pass: ≥ 90 % correct, **0 wrong values**, and 100 % of inverse answers carry the label.
- **P2 zero writes.** The notebook fact set (ids + hash) is identical before and after every question turn in P1 and in the suites.
- **P3 no regression.** rt136, rt143, sessions152, the bench121/v3 splits and the 138i G-suites (`scripts/fable_fix138i_suites.py`) give replies byte-identical to sealed 138i. The only exceptions are cases listed *before* the run as predicted moves. Any unpredicted diff is a FAIL.
- **P4 misroutes gone.** In P1, the self router fires on 0 turns that the table claims. The four task evidence question turns are answered from the notebook.
- **P5 honest abstention.** Questions on untaught relations still get the normal MISSING reply. Turns with no relation word ("Who is Kim's?") and self questions ("What is your name?") stay on their current path.
- **P6 cost.** Median added time ≤ 5 ms per turn on the Mac (patterns compiled once, indexed by first word).

The natural-English 100-turn panel (26/100 today) is a secondary measurement for the director only. I have not seen it and make no prediction for it.

**Why writes are untouched.** Build 1 emits only `ask` actions and clarify text, so the teach/correct/forget paths and all value/subject screens are exactly as sealed. The new wrong-write risk is zero by construction, and P2 checks it.

## 7. SECOND BUILD: teaches

`TableTeach218Mixin` sits **inside** `ValueScreen167bMixin`, so 167b/171/139b/150 still screen every table teach. It adds:
- the `inverted` teaches ("Sam is the boss of Kim.", "Lena is the mother of Theo."), coordinated with exp 215, which is fixing the composer-of junk now;
- verb teaches ("Ada Pell composed Blue Rain.", "Blue Rain was painted by Ada Pell.");
- the date rule (store "May", not "in May");
- the born-in date/place guard;
- the works-for person/company guard (boss vs employer);
- canonical keys for new writes. Old facts stay readable through `storage_keys`. A correction through an alias must supersede the canonical slot.

**Pass marks.**
- Zero wrong writes on rt136 and a fresh teach red-team (name-words, month names, company-vs-person).
- Every table write is shown back as "Saved: …" (167e mouth).
- Corrections via aliases supersede, never duplicate.
- The same P3 regression rule.

Writes are where wrong-write risk lives, so this is a separate, later build.

## 8. The same table as training labels for a learned reader

- **Generation.** Every template × surface × question word × fictional slot fillers gives a labelled example: (turn, act ∈ {teach, ask, yesno, inverse, clarify}, subject span, canonical relation id, value span, value_kind, never_store). Spans must be copied from the turn, matching the listening-contract rule in `fable_listening_english.py`.
- **Negatives.** Ambiguous turns ("Who is Kim's?"), exclusions and self questions are labelled clarify or self.
- **Held-out test.** Hold out *whole templates and whole relations*, not just names, to test real generalisation. The table stays the output schema: relation ids are the classes and value kinds are a type head.
- **Validation.** Check the learned reader's outputs against the table: an unknown relation falls back to the open-vocabulary key, an alias is canonicalised, and an inverse is never written.
- **Caution.** A reader trained only on template sentences will mostly learn the templates. Natural paraphrase data (Qwen-written, as already allowed) is needed on top, scored against the same labels.

## 9. Risks

- **Missing relation word.** "Who is Kim's?" has no reading and must stay clarify (the matcher shows 0 readings).
- **Names that are months or words.** "May is Tom's sister." (month as a name; the date guard only applies to date relations), "June's birthday is in June.", a town called May ("born in May" would read as a date), and names such as Rose, Hope, Bill or Will.
- **One word, two meanings.** "manager of Arsenal" is an office, while "Kim's manager" is a boss. "director" covers organisations and films. "works for Sam" (a person) vs "works for Acme" (a company). "country" can mean residence or citizenship. "home" can mean city or address.
- **Greedy spans.** Lazy `{X}`/`{Y}` spans on long turns: "Ada Pell is the composer of Blue Rain and Red Sky", chains inside slots ("the mother of Kim's boss"), relative clauses (the 132 rewriter owns those). The real reader needs name-shape rules (capitalised, known entity) that the table does not yet encode.
- **Precedence.** Base-first order means a bench composer frame that already answers wins. That is intended, but it means table aliases never override an existing reading.
- **Keys that disagree.** Alias keys keep being written until build 2. Reading all storage keys handles it, and a disagreement must ask, never merge.
- **Labels and suite diffs.** Inverse answers for multi-valued relations can list several subjects. The label must survive the 167e mouth and any suite diffs.
- **Size and cost.** 3,004 concrete patterns need compiling and indexing once. A naive loop per turn would be slow.
- **Incomplete inventory.** The checker's coverage depends on the constants list; new pieces must add their constants to `CODE_SOURCES`.
- **The table is v1.** The 8 NEW relations and 148 NEW templates are my proposals, not measured needs. The fresh probe set in build 1 is the first real test.
