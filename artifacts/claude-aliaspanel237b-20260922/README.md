# TEST-ONLY panel 237b: relation words and synonyms

TEST-ONLY. Do not tune on, pilot on or open before the builder's seal. Written blind by an independent writer on 2026-09-22 (no other panel, no relation table, no 237b builder code was opened).

A person teaches a fact in one wording, then asks about it in a different wording.

## Files

- `panel.jsonl` - 80 lines, fields exactly:
  - `id`: "a237b-001" ... "a237b-080", in family order
  - `family`: synonym (30), new_relation (20), date (10), trap (10), control (10)
  - `setup`: list of teach strings
  - `question`: string ending "?"
  - `expect`: synonym/new_relation/date = "ANSWER"; trap = "ABSTAIN"; control = "UNCHANGED"
  - `gold`: string; "A; B" means all parts must appear; null for trap
  - `note`: string
- `base221.jsonl` - 80 lines, same ids and order, fields exactly:
  - `id`
  - `base_reply`: string (reply of scripts/fable_loop221_agent.py with artifacts/claude-tableask221-20260922/loop221-config.json, one fresh work dir per item)
  - `stored_after_setup`: list of [subject, relation, value]
- `SEAL.sha256.txt` - sha256 of the two jsonl files, made from the repo root.

## Acceptance checks (all passed on base 221)

- every setup fact is stored after the setup;
- the question writes nothing (notebook triples identical before and after the question);
- all 10 controls are answered right by the base.

Base already right (gold in reply): synonym 14/30, new_relation 6/20, date 3/10, control 10/10. Base value leaks on traps: none.

## Replacements

- a237b-027, a237b-028: first teach wording "Pashko's dog is called Rufkin." / "Wendrel's cat is called Mivvy." stored the value as "called Rufkin" / "called Mivvy". Rewritten to "Pashko's dog is Rufkin." / "Wendrel's cat is Mivvy."; both then store the bare name. Questions and gold unchanged.

No other replacements. Car/bike/motorbike values are stored with the article ("a Voltane Rook"); gold is the name without the article, which appears inside that value.
