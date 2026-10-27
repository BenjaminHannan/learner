# Exp 250 (Opus): verb questions with lowercase or multi-word names (243 cause B, fix 5)

## Problem
"Where does brannick live?" and "Where does Joren Hale live?" get the glued "I don't know"
even though the city is stored. Verb167 (scripts/fable_fix167_verb.py) turns
"Where does X live?" into "Where is X's city?", but its subject check (`_subject_ok`, :117)
re-matches X case-sensitively against one capital-lead token (`_NAME`, :83). 167d
(scripts/fable_fix167d_verb.py) reuses the same `_NAME` for "Where does X work?" and
"What language does X speak?", so it has the same wall.

## The one change
`VerbSubj250Mixin` (scripts/claude_fix250_verbsubj.py) is a Verb167Mixin subclass that takes
Verb167's exact slot in the 138i ears stack (scripts/claude_loop250_agent.py swaps that one
base class; every other stage and its order stay as they are).
- Only "?" turns. Only when both the Verb167 and Verb167d parses claim nothing.
- Five shapes, case-insensitive: Where does X live / Who does X work for / Where was X born /
  Where does X work / What language(s) does X speak, with an optional leading "hi/hey/hello,"
  and/or "please," and an optional trailing ", please". X = 1-4 words.
- Name gate: X is not closed-class (150c), does not start with my/your/the/..., resolves by its
  own stored name to exactly one notebook entity (nb.resolve OK, not an alias), is not USER, and
  is the subject of at least one active taught fact (so a city or other value-only entity is
  never asked about). A lowercase common word that is not a stored entity is never a name.
- Base first: the original turn is heard by the unchanged stack. If it claims anything (any
  action that is not a clarify miss), that result is returned unchanged. Only on a miss is the
  twin ("Where is Brannick's city?", STORED spelling) handed to the same inner stack Verb167
  uses; it is kept only when every action is read-only and one is an ask/answer. Otherwise the
  original handling is returned.
- Statements are never touched; the fix owns no save, ask or mouth code.

## Decision logged
Covering 167d's two question shapes as well as Verb167's three: the panel family is
"verb questions with a lowercase or multi-word name", and 167d shares the same `_NAME` wall.
It is the same check in the same slot, not a second mechanism.

## Known risk
The answer names the subject ("Joren Hale's city is Selwick."). If the subject's name is also a
stored value on another fact (e.g. someone's spouse) and the panel does not list it in
allowed_mentions, the literal wrong-value rule would count it. Base possessive answers have the
same shape.
