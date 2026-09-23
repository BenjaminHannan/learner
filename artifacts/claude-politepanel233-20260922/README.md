# Panel 233: polite negative questions (blind)

Written blind from the brief only (no code, relation tables, design docs or other panels read).
Generator: `make_panel233.py` (in this folder; deterministic, run from repo root). One-word invented names only; all towns invented.

## Families (60 items)
| family | items | expect |
|---|---|---|
| polite_taught | 24 | answer |
| polite_untaught | 12 | abstain |
| true_negation | 16 | no_value |
| negated_statement | 8 | abstain |

Expect split: 24 answer, 20 abstain, 16 no_value. 57 clear, 3 unclear.

## Judgement calls
- Setups use only "<Name>'s <relation> is <Value>." and "<Name> lives in <Town>.". Because "works at" is not an allowed setup here, no "where does X work" wordings are used; workplace-style asks use boss/manager instead.
- polite_taught wordings vary: can't/couldn't/won't/wouldn't/don't/do you not/can you not, plus "just", "please" and one "Surely you can't have forgotten ...". Some items add a distractor person or relation.
- polite_untaught includes one empty-notebook item. The reverse-direction item ("who Quill's neighbour is" after "Borro's neighbour is Quill.") is marked `clear: false`, because some people would treat neighbour as two-way.
- true_negation expects `no_value`: the assistant must not give a stored value as the answer. The two "Didn't X live in Y before?" items are marked `clear: false`: a past-tense yes/no is a different kind of question, and in one of them Y is the current town.
- negated_statement: only a negated home statement about that person (sometimes with an unrelated fact or another person living in that town); question is always "Where does <Name> live?"; must abstain and must not answer with the negated town.
- Each item is meant to run in a fresh notebook.
