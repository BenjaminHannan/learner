# Exp 243 RESULTS: why stored facts get "I don't know" (diagnosis only)

**Result.** 301 of 539 grid questions whose answer WAS stored got the glued decline on 138i
(+228 guard). 0 got a wrong answer. Every decline is an **ears miss**: no reader claims the
question, so FakeEars says "didn't understand" and 138g glues on the honest decline
(scripts/fable_loop138g_agent.py:323/339). There is no "many facts -> ambiguity" guard.
Five root causes explain all 301. No file was edited and no fix was built.

## Grid (grid.jsonl, tally.txt). Counts = declines / questions with the answer stored
Factors: star/chain/me x 1/2/3/5 facts x taught case (title/lower) x asked case
(title/lower/upper) x one-word/two-word name x 12 question forms (10 first-person forms).

| form | declines | cause |
|---|---|---|
| Who is X married to? | 63 / 96 | A |
| Who is X's spouse? | 0 / 96 | - |
| Who is Xs spouse? | 96 / 96 | C1 |
| Where does X live? | 15 / 27 | B |
| What is X's city? / What's X's city? | 0 / 54 | - |
| What is Xs city? | 27 / 27 | C1 |
| whats X's city? / whats Xs city? | 54 / 54 | C2 |
| Who is X's boss? | 0 / 18 | - |
| Who is Xs boss? | 6 / 18 (two-word names only) | C1 |
| whats Xs boss? | 18 / 18 | C2 |
| Where do I live? (3 casings) | 12 / 12 | D |
| What's my city? | 4 / 4 | D |
| whats my city? | 4 / 4 | C2 |
| Who am I married to? | 2 / 2 | D |
| What is my city? / Who is my boss? / Who is my spouse? / Where is my city? | 0 / 13 | - |
| **Total** | **301 / 539** | |

Boundary for "married to": 0/24 declines with 1 fact; 63/72 with 2, 3 or 5 facts (21/24 at
each level, in both shapes). The 9 that still answered are lowercase two-word star cells
where the extra teaches were never stored, so the subject really had one fact. It depends on graph shape, not on
the number 3: a second relation on the subject, or any fact hanging off the spouse, is enough.
Case: asked case matters only for B (lowercase fails; UPPER passes). Apostrophe: all
no-apostrophe forms fail except one-word "boss" (a person relation).

## Root causes (details and traces in traces.md)
- **A.** scripts/fable_bench92_english_arm.py:221-239 `compose_n_hop` walks to the end of the
  chain and needs every walked relation to be mentioned; it stops at once when the subject has
  2+ relations (line 224). It is the only reader of "Who is X married to?" and
  "What country is X a citizen of?" (called at scripts/fable_loop138_agent.py:122).
- **B.** scripts/fable_fix167_verb.py:117 `_subject_ok` re-matches the name without
  IGNORECASE against a one-token capital-lead `_NAME` (line 83): lowercase and two-word names
  are refused.
- **C1.** scripts/fable_fix165_typo.py:147 repairs a missing apostrophe only for REL165 =
  PERSON_RELATIONS (line 50; no city/spouse/pet), and `_ASK165` (line 57) takes one word only.
- **C2.** "whats" without an apostrophe: scripts/fable_fix158_qform.py:42 expands only
  "what's"; no other stage reads "whats".
- **D.** scripts/fable_fix166_me.py:62 reads only "(who|what|where) is my R"; Me166 is outside
  Qform158, so "What's my" never reaches it; "Where do I live?" is refused as a closed-class
  subject (fable_fix167_verb.py:120); "Who am I married to?" has no reader.

## Proposed smallest fixes, ranked by user impact (none built)
1. **A: mention-guided walk fallback** (new mixin over Loop138Ears._hear_question, used only
   when compose_n_hop returns None): from the one mentioned entity, follow the outgoing
   relation that the question mentions, stop when none is, require all mentioned relations
   used, then keep the existing 113c `frame_consumes_question` gate. Sketch check
   (claude_diag243_composers.py): gives the right frame for all A cases and returns None for
   rt143 U3/U5/L4 (current abstain probes). Likely moves: rt143 **Q1, Q2, P1, P2** (decline ->
   answer). Risk: cue substrings over-count ("found", "work"); a two-hop "X's spouse's city"
   phrased with verbs could now answer a prefix only if the gate lets it through; rt143 H5/U3/
   U5/L4/T4 must stay as they are. Real users: hits almost every "married to" / "citizen of" /
   verb-form question once a person has 2+ facts, which is normal use. Highest impact.
2. **C1: widen apostrophe repair** (subclass Typo165: accept any relation already stored for
   the resolved entity, and multi-word names by resolving the words before the final "s" word).
   138j's fix193 already covers one-word names; porting 193 plus the two-word case is the
   smallest step. 129 grid cells. Risk: plural names ("The Toms") are already blocked by the
   165 gate (b2); keep it. Likely suite moves: none known in rt136/rt143 (no such probe).
   Users: very common in typed chat.
3. **C2: "whats/whos/wheres" -> "what is/who is/where is"** as an outermost mixin (above
   ChainOf174) so Me166, Typo165 and FakeEars all see the expanded form. 76 cells. Risk: a
   name spelled "Whats..." at the start of a statement; gate to "?"-terminated turns. Likely
   suite moves: none known. Users: common in casual typing.
4. **D: first-person twins** in a mixin outside Me166: "Where do I live?" -> "What is my city?",
   "Who am I married to?" -> "Who is my spouse?", "What's my" -> "What is my". 18 cells (+4
   shared with C2). Risk: low; only "?" turns with I/my. Likely moves: sessions152 only if it
   has such turns (not checked). Users: rarer, but it is a demo question ("Where do I live?").
5. **B: case-insensitive, multi-word subject check** in a Verb167 subclass, requiring
   nb.resolve(name) OK so a lowercase common word is never taken as a name. 15 cells. Risk:
   low with the resolve gate. Likely moves: none known.

## Deviations
- The grid ran on scripts/claude_loop228_agent.py (138i + 228 guard) as the rules require for
  new harnesses. 138j was checked only with the evidence dialogs (repro-138j.txt,
  repro-apos-138j.txt): same declines except that 138j answers one-word no-apostrophe forms.
- Frozen-suite ids are from reading the saved 138i rows plus the sketch, not from a suitediff
  run (no fix exists to diff).
- Diagnosis only: no PASSMARKS, no seal, no ledger lines (nothing registered).

## What it means
The assistant is not confused by having many facts. Its question reader is a stack of narrow
patterns, and several common ways of asking (verbs like "married to", no apostrophe, "whats",
lowercase names with "live", "I" questions) have no pattern that works. When nothing matches,
it says "I don't know" even though the fact is saved.

## What it doesn't mean
It does not mean the notebook lost or mixed up facts: every stored fact was still there, and
the possessive form ("X's spouse") answered 96/96. It does not show the fixes work; they are
proposals, and only fix A had a paper check. The grid uses a small set of fictional names and
forms, so the counts show where the walls are, not how often real users hit them.
