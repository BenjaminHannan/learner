# y1t data gate, addendum 1: G1 counts the wrong thing for "who is my <role>?" (Answering-from-memory thread, DRAFT 19:43 UTC 2026-09-26, sent to the Thread manager for review before sealing; the combined GLM set does not exist yet and no gate judge has run)

## What happened (disclosed in full)
- At about 19:40 UTC I ran the sealed G1 code check (claude_y1t_gate.py audit) early, on the first GLM run's items
  (566 train, 102 dev; ADDENDUM-3 tops them up). It is not the gate run; the gate runs on the combined set.
- G1 failed on both: 64 of 283 training twins and 9 of 51 dev twins still contain the gold value (bar: 5%).
- Counted by code (claude_y1t_gate2.py classify), all 73 are "who is my <role>?" items (owner "me", a lis-320 role
  relation such as landlord or best friend), where the answer is a person's name. 134 of 283 training items are
  such role questions. The other 149 training twins: none contains the value.
- To see why, I read the gold value, the question and one matching kept turn for 18 of these twins (GLM text from
  the training data; no TEST-ONLY panel; I am not one of the gate's judges). In 15 the person is only mentioned
  elsewhere (their cat, their job, a look-alike turn) and the chat never says they are the user's landlord, boss or
  brother, so the twin still does not tell the answer. In 3 a kept turn names the person together with the role word
  ("my husband neorn actually lives in orketon"): those are real leaks.
- So G1, as sealed, flags a twin as leaking whenever the person is mentioned at all. For these questions that is the
  wrong test: it would fail the gate on valid twins, and a blanket drop would remove the hard cases y1t most needs
  (a person is mentioned, their role is not; the right answer is "you haven't told me").

## Change (GATE-data.md's own fail rule: "the fix labels from the text itself (code or GLM) ... and gets a new seal")
- F1 replaces G1 as a code filter on every twin (scripts/claude_y1t_gate2.py filter), before the gate sample:
  - no kept turn contains the value: keep ("clean");
  - role question, and no kept turn with the name also has the role word: keep ("name only");
  - otherwise drop ("role word with the name", or "value present" for other questions). Answerable items are kept.
  - On the first-run items (preview): training twins keep 282 of 283 (219 clean, 63 name only, 1 dropped);
    dev twins keep 49 of 51 (42 clean, 7 name only, 2 dropped).
- G4, a new blind check on the class F1 lets through by code: a sample of up to 60 name-only twins (seed 4036), two
  blind judges and a fresh third on disagreements, the same way as G2/G3. Question: do the earlier messages say that
  this person is the user's <role>, in any words? PASS if "yes" on at most 10% of the sample (6 of 60).
  - PASS: name-only twins stay.
  - FAIL: every name-only twin is dropped too (claude_y1t_gate2.py drop-name-only), disclosed. y1t is not stopped by
    G4; it trains on clean twins only.
- G2 and G3 do not change (sealed marks, seed 4034, 54 of 60 each). Their failure still stops y1t.
- F1 is applied to items_train and items_dev. Both y1t and y1r read the filtered files.

## What would show this change is wrong
- G4 fails: the role word test misses real leaks, so code cannot tell name-only mentions from leaks, and the
  name-only twins are dropped.
- If G4 passes but y1t's DEV eval shows the model saying "don't know" to role questions it was told, the name-only
  twins taught it to ignore the person. This is a report row, split by role vs other questions, not a new mark.

## Plain summary for Ben
Some practice questions ask "who's my landlord?". To make a "you never told me" copy, code deletes the message that
said who the landlord is. The first check then complained whenever the landlord's name still showed up anywhere,
for example "Saorn's cat is Fipip". That doesn't tell you Saorn is the landlord, so the copy is still fair. The new
check drops a copy only when the name appears next to the word "landlord". Two blind readers then check 60 of the
kept copies, to make sure the code isn't missing leaks.
