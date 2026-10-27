# 229 - relation-table build 2: TEACHES (Opus)

Base: 138i (`scripts/fable_loop138i_agent.py`, `artifacts/fable-agent138i-20260922/loop138i-config.json`).
Agent: `scripts/claude_loop229_agent.py`. Config: `artifacts/claude-tableteach229-20260922/loop229-config.json`.
Results: `artifacts/claude-tableteach229-20260922/RESULTS.md`.

## The one change

`TableTeach229Mixin` sits outermost on the 138i ears. It first calls the full 138i
ears. If 138i produced anything other than "I did not understand" (a base miss), the
138i result is returned untouched. So every statement 138i already saves goes
through exactly the old path and stores exactly the old triples.

Only on a base miss does the mixin try the relation table
(`artifacts/claude-relationtable-20260922/relation_table_v1.json`):

1. Reject the turn early if it has a `?`, more than one sentence, a negation / tense /
   hearsay / hypothetical marker (not, never, no longer, used to, former, ex-, if,
   would, maybe, thinks, said, wish, hope, will, ...), starts with a question word, or is shouted in all capitals (rt136 C142 treats that as nowrite).
2. Match the sentence (case-insensitive, whole sentence) against:
   - the table's own `teach` rows (verb forms and others),
   - the generic `inverted` family, "Y is the R of X", for every relation surface and alias,
   - a small set of extra shapes (EXT229): occupation "X is a/an J" (closed job list)
     and "X works as a J"; "Y is a/an R of X" and "X has a/an R called Y" (multi-valued
     relations only); "Y is my R"; and first-person forms ("I live in", "I work at",
     "I am N years old", ...).
3. Check the reading: the subject must look like a name (or USER), and the value must
   pass the table value type (person / place / organization / work / language / number /
   date / occupation lexicon / hobby phrase / nickname), including the table's
   date / not-date guards.
4. Zero passing readings: say plainly that nothing was saved and why. Two or more
   different passing readings: say nothing was saved because it could be read more
   than one way.
5. Exactly one reading: rewrite it as the canonical sentence "X's <canonical relation>
   is Y." (or "My <relation> is Y." for USER) and pass it through the full 138i ears.
   All base screens therefore apply unchanged: confirmations, re-teach asks,
   multi-valued add rules, typo screens, and so on. The 209 write screen
   (`screen_turn209`, imported, not edited) is then applied. The result is accepted
   only if it is teach / correct actions on exactly (X, a storage key of that relation,
   Y). Otherwise nothing is saved and the reply says so. A base clarify (for example a
   re-teach ask) is passed through with "I did not save that yet." in front.

The stored relation is always the table's CANONICAL name (grandma -> grandmother,
coworker -> colleague), per the director note. Relation words match case-insensitively
("Juniper Holt is a Friend of Marlo Quince."). Inverse facts are never stored.

## Cut / known misses

- **Cut family: of_form, "The R of X is Y."** The pilot showed it turned four rt136
  nowrite traps into WRONG-WRITEs ("The mother of Ann is Sue.", "THE CAPITAL OF PERU IS
  LIMA." and similar, which the frozen suite expects not to be written). It was cut
  before the seal. Dev items d229-046..049 are kept and marked `of_form_cut`.
- **Out of scope, as the brief says:** pronouns, appositives, two facts in one sentence,
  negations, and tense / "used to". All of these are refused.
- **USER plus a multi-word relation** ("My best friend is Tam Rook.", "I was born in
  Dunmore" -> place_of_birth). The base "My R is Y" teach path only takes one-word
  relations, so these get an honest "not saved" reply.
- **The subject kind is not checked** (only its shape is). For example "Kim Tolland is the
  capital of Norland" saves a capital fact.

## Deviations from the 217 table decisions

- EXT229 adds shapes that are not in the table's teach rows (occupation "X is a J",
  "a R of", "has a R called", first-person forms). The 217 design had left occupation
  "X is a J" out, because it can be confused with a category ("Rex is a dog"). Here it is
  limited to a closed job lexicon.
