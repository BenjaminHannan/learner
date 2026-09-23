# 246: mention-guided walk fallback (cause A of diagnosis 243)

Problem. "Who is Joren Hale married to?" and "What country is X a citizen of?" are read only by
the n-hop composer (scripts/fable_bench92_english_arm.py:198). It walks every single-relation
link to the end of the chain and demands every walked relation be mentioned. If Joren also has a
city, or his spouse has a citizenship, it gives up, and Premonition says "I don't know" about a
fact it has.

Fix (scripts/claude_fix246_mentionwalk.py, agent scripts/claude_loop246_agent.py). Only when the
composer gives up AND the rest of the base misses the question, start at the one entity named,
take the one relation the question mentions, and stop. Accept only if:
- exactly one known entity is named (whole words; "Spellman" does not name "Pell");
- every relation cue in the question is explained by that hop (scaffolding cues such as "where",
  "work", "spoken" ignored as 113c does), and the hop's cue appears in one place only;
- "who"-questions do not end on a place and "where"-questions do end on one ("Where was X
  founded?" does not give the founder);
- for relations where the answer is the doer (employer, founder, author ...), the cue comes
  before the name with no "by" between, so "Who does X employ?" and "Who is employed by X?"
  never return X's employer;
- no "whose", no "X the R of?" shape, no 2-cycle back to the start, and every other word is a
  small function word (so "Who does X work with?" and "X's friend" decline);
- the existing 113c gate and 113 compound guard still pass.
The result is the same "ask" action the base composer emits, so the reply wording is the base's.

Scope limit. One hop only. A two-hop walk from a star-shaped start answered rt143 S1, which the
frozen suite requires to abstain; multi-hop questions stay with the old composer.
Known remaining gaps: two-hop questions where the start or middle has extra facts; "Who does X
work for?" when only an employer is stored ("work for" is not an employer cue); "Who is X employed
by?" (declines by the direction rule).
