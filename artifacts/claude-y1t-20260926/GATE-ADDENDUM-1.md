# y1t data gate, addendum 1: G1 failed as written; G1b and G4 registered for "who is my <role>?" twins (Answering-from-memory thread, 2026-09-26; draft 19:43 UTC, revised 19:46 UTC after the Thread manager's review, sealed in SEAL-gate2.sha256.txt; the combined GLM set does not exist yet and no gate judge has run)

## Verdict on the record: G1 FAILED as written
- At about 19:40 UTC I ran the sealed G1 code check (claude_y1t_gate.py audit) on the first GLM run's items
  (566 train, 102 dev; ADDENDUM-3 tops them up).
  - Train: 64 of 283 twins still contain the gold value.
  - Dev: 9 of 51.
  - The bar is 5%. **G1: FAIL.** This stays on the record; nothing below changes it.
- What the failures are, counted by code (claude_y1t_gate2.py classify):
  - All 73 are "who is my <role>?" items (owner "me", a lis-320 role relation such as landlord or best friend),
    where the answer is a person's name. 134 of 283 training items are role questions.
  - The other 149 training twins: none contains the value.
- To see why, I read the gold value, the question and one matching kept turn for 18 of the 73 (GLM text from the
  training data; no TEST-ONLY panel; I am not one of the gate's judges).
  - In 15, the person is only mentioned elsewhere (their cat, their job, a look-alike turn). The chat never says
    they are the user's landlord, boss or brother, so the twin still does not tell the answer.
  - In 3, a kept turn names the person together with the role word ("my husband neorn actually lives in
    orketon"). Those are real leaks.
- So G1 counts a twin as leaking whenever the person is mentioned at all. For role questions that is the wrong
  test.

## Why not simply drop all 73 (the reason for registering new checks)
A blanket drop removes exactly the hard cases y1t most needs: a person is mentioned, their role is never stated,
and the right answer is "you haven't told me". Training without them teaches that a mentioned name is the answer.

## New checks, registered under GATE-data.md's own fail rule ("the fix labels from the text itself (code or GLM) ... and gets a new seal")
- **G1b, code, every twin, filters the data** (scripts/claude_y1t_gate2.py filter), before the gate sample:
  - no kept turn contains the value: keep ("clean");
  - role question, and no kept turn that contains the name also contains the role word: keep ("name only").
    - "Beside" means the same kept turn, with no token window.
    - The role word is the relation with "_" as a space ("best friend"), matched case-free at a word start, so
      "landlord's" counts. Only that one form is used, the one lis-320's seeds ask GLM to write.
  - Otherwise drop: "role word with the name", or "value present" for other questions.
  - Answerable items are never dropped.
  - Preview on the first-run items: training twins keep 282 of 283 (219 clean, 63 name only, 1 dropped); dev twins
    keep 49 of 51 (42 clean, 7 name only, 2 dropped).
  - **Smoke on the 18 I read:** G1b drops all 3 real leaks (Kanuir, Neorn, Ganvenith: "role word with the
    name") and keeps all 15 name-only twins as "name only".
- **G4, blind, decides whether name-only twins stay.** The sample is up to 60 name-only twins from the gate's
  items_train, with seed 4036, fixed now. Two blind judges answer (fresh agents, each reading only its own folder;
  never trained on, tuned on or quoted), and a fresh third judges any item where they differ.
  - Question: do the earlier messages say, in any words, that this person is the user's <role>?
  - **PASS if "yes" on at most 6 of 60** (10%; with fewer than 60 name-only twins, at most 10% rounded down).
  - A G4 FAIL is a live possibility. The code test only sees the exact role word, so paraphrases ("the guy I rent
    from") pass it. In my hand reading, 3 of 18 mentions stated the role, although G1b catches those 3.
  - If G4 FAILS: every name-only twin is dropped (claude_y1t_gate2.py drop-name-only), disclosed. y1t then trains
    on clean twins only. G4 does not stop y1t by itself.
- G2 and G3 do not change (sealed marks, seed 4034, 54 of 60 each). Their failure still stops y1t.
- G1b (and a G4 drop) apply to items_train and items_dev. Both y1t and y1r read the filtered files.

## What would show this change is wrong
- G4 fails: code cannot tell name-only mentions from leaks, and the name-only twins go.
- If G4 passes but y1t's DEV eval shows the model saying "don't know" to role questions it was told, the name-only
  twins taught it to ignore the person. This is a report row, split into role and other questions, not a new mark.

## Plain summary for Ben
Some practice questions ask "who's my landlord?". To make a "you never told me" copy, code deletes the message that
said who the landlord is. The first check complained whenever the landlord's name still showed up anywhere, for
example "Saorn's cat is Fipip". That check failed, and the record says so. But that message doesn't tell you Saorn
is the landlord, so the copy is still fair. The new check drops a copy only when the name and the word "landlord"
are in the same message. Two blind readers then check 60 of the kept copies. If more than 6 of them do say who
the landlord is, all of those copies are dropped.
