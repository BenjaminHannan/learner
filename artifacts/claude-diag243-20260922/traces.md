# Exp 243 traces (diagnosis only, 138i + 228 guard)

Tool: scripts/claude_diag243_trace.py wraps every `hear` / `_act` / `turn` in the
live 138i stack (in-process only, no file edited) and prints where the output changes.
Composer calls: scripts/claude_diag243_composers.py.

## Common tail: how a missed question becomes the glued decline
1. Ears order, outer to inner (scripts/fable_loop138i_agent.py:336): ChainOf174 > Typo165 >
   ValueScreen167b > Verb167d > Verb167 > Name173b > Name173 > Me166 > Plural162b > Copula172 >
   Multival154e > 171b/171 > Loop138gEars (... Qform158 ... Loop138Ears) > Loop102Ears >
   Loop96Ears > ChainEars > FakeStage/FakeEars.
2. Loop138Ears._hear_question (scripts/fable_loop138_agent.py:115). For "?" turns it tries
   B92.compose_n_hop (line 122) then B73.compose_question (line 138); when both give None it
   calls L102.Loop102Ears.hear (line 152) and the chain ends in FakeEars
   (scripts/fable_agent_loop.py:112). FakeEars only reads "who/what/where is|are X's R"
   (_QUESTION, line 94); everything else returns "I didn't understand that...".
3. Loop138gAgentLoop.turn (scripts/fable_loop138g_agent.py:323) sees notebook_missed, route127
   says DECLINE, and line 339 glues S105.HONEST_DECLINE + L138.DECLINE_SUFFIX = the long reply.
   There is NO "many facts -> ambiguity" guard; the decline is always an ears miss.

## Root cause A: the n-hop composer walks past the asked relation
"Who is Joren Hale married to?" and "What country is X a citizen of?" have exactly one reader:
B92.compose_n_hop (scripts/fable_bench92_english_arm.py:198). It walks from the mentioned
entity to the END of the chain (line 221-234) and then requires every walked relation to be
mentioned in the question (line 237-239).
- Star shape (subject has 2+ different relations): line 224 `if len(uniq) != 1: break` stops
  at step 0 -> rels empty -> None (line 235).
- Chain shape (subject has one relation but its object has more): the walk continues to
  country/capital, "capital" is not mentioned -> None (line 238).
Trace (spouse + citizenship stored): Loop138Ears -> Loop102Ears -> FakeEars clarify ->
decline. With spouse alone: compose_n_hop = ('Joren Hale', ['spouse']) -> answered.
"Who is Joren Hale's spouse?" works because FakeEars reads the possessive directly.
It is graph shape, not fact count, and not the correction ("Actually ..."): one extra fact
on Joren (city) or on Sella (citizenship) is enough.

## Root cause B: "Where does X live?" twin needs a capitalised one-word name
Verb167Mixin.hear rewrites "Where does X live?" -> "Where is X's city?" via parse_verb_question
(scripts/fable_fix167_verb.py:172). _ASK_LIVE (line 96) is IGNORECASE, but _subject_ok
(line 115-118) re-checks the name with `re.fullmatch(_NAME, name)` WITHOUT IGNORECASE, and
_NAME (line 83) is one capital-lead token. So "brannick"/"pell" (lowercase) and "Joren Hale"
(two words) are refused -> no twin -> FakeEars clarify -> decline. "BRANNICK"/"Brannick" work.
The brannick evidence case is this, not the stored "boss" fact and not name case folding in
the notebook (the notebook resolves case-insensitively).

## Root cause C1: missing-apostrophe repair only for person relations, one-word names
Typo165Mixin (scripts/fable_fix165_typo.py:154) repairs "Who is brannicks boss?" ->
"who is brannick's boss?" in rewrite_ask (line 131). Gate line 147: the relation word must be
in REL165 = PERSON_RELATIONS (line 50: mother, boss, friend, wife, partner ...). "city",
"spouse", "pet", "employer" are not in it -> no repair. _ASK165 (line 57) also takes a single
word W, so "Joren Hales boss" never matches. (138j's fix193 already repairs the one-word
cases; two-word names still decline on 138j.)

## Root cause C2: "whats" (no apostrophe) is read by nobody
Qform158 expands only "what's/who's/where's" with an apostrophe (_CONTRACTION_RE,
scripts/fable_fix158_qform.py:42). FakeEars needs "what is". Typo165 needs "what is".
So "whats Pell's city?" and "whats pells city?" both decline.

## Root cause D: first-person questions other than "what/who/where is my R"
- Me166 _ASK (scripts/fable_fix166_me.py:62) reads only "(who|what|where) (is|are) my R".
- "What's my city?": Me166 sits OUTSIDE Qform158 (which expands "what's"), so the expanded
  text never reaches Me166; the inner readers have no "my" -> decline.
- "Where do I live?": Verb167 _ASK_LIVE matches with X="I", but _subject_ok rejects it as a
  closed-class subject (fable_fix167_verb.py:120; is_closed_class_subject("I") is True);
  nothing maps it to USER/city.
- "Who am I married to?": no reader at all (compose_n_hop has no entity "I").

## Side findings (not "declines while stored" in the grid)
- "what is pells city?" on 138i -> "I have no opinions." (a wrong answer, not a decline):
  FakeEars gives the "1 to 3 steps" clarify, the chain turns it into "didn't understand",
  route127 then routes to an opinion reply. 138j answers it correctly (fix193).
- Lowercase two-word teach "joren hale's city is Selwick." is NOT stored (decline on teach);
  grid cells depending on it were excluded because the answer was not stored.
- "Tell me about Isolde." / "Who lives in Quellport?" decline too (p3 evidence); they are
  missing features (summary / reverse-city), not stored-fact lookups, so not graded here.
