# chainpanel266: blind two-step chain panel (base 138m characterization)

80 items, all sentences writer-original, all names fictional.
Schema per item: id (c266-001..080), family, setup (1-4 teaching turns),
question, gold (list of strings; [] for abstain/control families), note.

Family counts: chain_verb 30, chain_verb_three 6, chain_possessive 10,
broken_chain 12, plain_control 14, statement_control 8.

Design categories (counts only):
- chain_verb: two-link chain subject plus a verb/when question. Six
  question forms x 5 items each. Twelve distinct first-link relations.
  8 items use a my-subject for the first link.
- chain_verb_three: three-link chain subject plus a verb question, all
  three links taught. 6 items.
- chain_possessive: same stored facts asked in possessive form. 10 items,
  including 2 my-subject items.
- broken_chain: 6 items with the first link missing, 3 with the second
  link missing, 3 where the second person has a different relation taught.
  Gold is empty; an honest abstain naming no untaught value is right.
- plain_control: the same verb question forms with a plain-name subject
  taught directly. 14 items.
- statement_control: a chain-containing statement as the last turn (no
  question mark). Gold is empty; right means the stored facts are
  unchanged. 8 items.
- 20 items use two-word names. Every setup was checked on the base and
  stores as expected (3 first-draft setups that did not store were
  replaced before the seal).

Base (138m) results from the sealed scorer (counts only, no item text):

| family | n | right | wrong | abstain | other | question_wrote |
|---|--:|--:|--:|--:|--:|--:|
| chain_verb | 30 | 8 | 0 | 0 | 22 | 0 |
| chain_verb_three | 6 | 1 | 0 | 0 | 5 | 0 |
| chain_possessive | 10 | 10 | 0 | 0 | 0 | 0 |
| broken_chain | 12 | 12 | 0 | 0 | 0 | 0 |
| plain_control | 14 | 11 | 0 | 0 | 3 | 0 |
| statement_control | 8 | 8 | 0 | 0 | 0 | 0 |
| TOTAL | 80 | 50 | 0 | 0 | 30 | 0 |

What it means: the base already answers possessive chains, stays silent
on broken chains, and writes nothing on chain statements. Verb-form chain
questions are mostly unanswered, which is the gap the reasoning line is
built to close. What it does not mean: these numbers say nothing about
any new agent; only the sealed scorer run by the builders decides that.
