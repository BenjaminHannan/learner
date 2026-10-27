# uw-2: can a trained note-update step apply corrections that the save path drops?

Drafted 2026-09-26 20:33 UTC (`date -u`) by the wrong-as-fact thread (0.2c row H1). The Thread manager reviewed it
(no blocking objection; three points written in below). Registered and sealed 2026-09-26 20:36 UTC (SEAL-uw2.sha256.txt).
At sealing, no training card, no trained model and no test panel exists.

Any change after sealing goes in a dated addendum and never moves a bar. A FAIL stays a FAIL. It joins no build
without Ben's yes.

## Why (counts, with sources)
- H1: the joined assistant states old corrected values as fact (0.2c X 8 vs G 5; 0.2d-r X' 12 vs G 6).
- In sf-401's run, 28 of 42 missed correction questions never got the new value into the notebook
  (BLAME-after-verdict.md, da3294a87). The notebook held both values at only 1 of 74.
- lis-319f saved 4 of 60 corrections (lis-319k VERIFY.md:17-21). The largest cause is owner_not_span, 14 of 60: the
  owner was named only in an earlier turn ("sorry, she's 13").
- The compiler rejects such an owner by rule (scripts/claude_lis300_compiler.py:54-55). So a better reader alone
  cannot save these corrections in the 0.2d path (Reading facts, 20:31 UTC).
- How many facts are out of reach: on lis-320's sealed reader panel, 22 of 52 corrections and 93 of 96 backref facts
  are unreachable for any reader under the sealed compiler (lis-320 ADDENDUM-5, 6c6313a94; counts by code). This is
  the number that justifies this test.
- Textbook fix: supersede on write. The writer sees the old note and updates it (Mem0's UPDATE step; Zep/Graphiti
  invalidate the old edge).
- A note pointer takes the owner from the note, which was checked when it was first saved. Only the new value needs
  checking in the new message.
- Brain (a guess at the mapping): reconsolidation. A reactivated memory that meets a mismatch is rewritten, and it
  keeps its identity.
- Untrained, this fails. uw-1 DEV (DEV-zero-shot.md, 6cf418e5a): pointing at note numbers, the plain 1B got 0 of 47
  DEV corrections right, with 22 false changes in 200 other turns. In the owner form it got 2 of 47, with 188 false
  changes in 522.
- The plain fix for a small model that cannot do a task zero-shot is to train it on that task. That is the one
  change here.
- What this test can and cannot move: the notes are oracle and complete, so the test measures using a note, not
  finding it or having it. A PASS moves H1 only where the save path already holds the old note. In sf-401's B arm
  (BLAME), 28 of 42 missed correction questions never got the new value into the notebook. 12 of those still held
  the old value: that is exactly the case this step acts on. The other 16 held no value for that fact at all, so they
  are outside it. The 14 answer-step misses (new value held) are also outside it.

## One change
- A: the plain MiniCPM5-1B, snapshot 87179e5c (BensPC's BASE). It uses the note form of
  scripts/claude_uw1_cards.py: messages(card, "B", "note"), parse_note, greedy, 40 new tokens, thinking off.
- B: the same model and prompt with a LoRA trained on uw-2's training cards (below), merged. The recipe is
  scripts/claude_bm398r_train.py unchanged: rank 16, alpha 32, q/k/v/o, 1 epoch, AdamW 2e-4, 8 cards a step, seed
  3992. The loss is on the answer tokens only.
- The prompt text (system line, question, output form), the parse and the grader are shared by A and B. They are
  fixed before training in scripts/claude_uw1_cards.py, whose sha256 is in the seal. So B's gain cannot come from a
  prompt change.
- Nothing else differs.

## Disclosed stand-ins (hand-written scaffolding)
- The system line, the question text and the output form ("UPDATE note number | new value" or "NONE") are
  Claude-written prompt text. They stand in for a learned supersede step inside Ben's reasoner.
- In the test, the notes are the true facts just before each turn (oracle, from truth.jsonl), all shown, in taught
  order. Finding the right notes (retrieval) is not tested. Using them is.
- No reader is in the loop. Reading facts' condition 1 (fix the reader in advance) is therefore met trivially. The
  end-to-end effect on H1 is untested until a later, separate test.

## Training cards (fixed now, built by code)
- Source: lis-320's GLM-worded kept dialogs from its full run on seed 324 (seed_cr, with correct_ref turns; lis-320
  ADDENDUM-5). The wording comes from GLM 5.3 Flash. Seeds, labels and checks come from code.
- Seed 322, the stopped OpenRouter run, is never used.
- Conditions agreed with Reading facts (20:34 UTC):
  - Rows are taken only after lis-320's DATA.md is written, and they are pinned by the sha256 it records (kept.jsonl,
    or raw.jsonl.gz rebuilt with scripts/claude_lis320_check_cr.py).
  - scripts/claude_lis320_rawcheck.py runs on the raw file first.
  - The rows are training only, never test items.
- Never the pilots (seeds 320 and 321 are uw DEV). Never claude-readpanel320. Never any sealed panel.
- Cards are built by claude_uw1_cards.cards_dev320's rules: notes = the gold ASSERT/CORRECT facts of earlier kept
  turns; dropped turns are skipped; implicit changes and "former of a current note" turns are left out and counted.
- Target for a correct or correct_ref turn whose old (owner, rel) is note N: "UPDATE N | v". Here v is the new
  value exactly as typed in the message (a case-insensitive whole-word span). A card whose value is not a span is
  dropped and counted.
- Target for every other kept turn: "NONE".
- Mix: all correction cards, and every look-alike card (former, plan, hypothetical, someone_else, question, doubt,
  confirm, negation_only, ambiguous_pronoun). Other NONE cards (teach, backref, jobhome, ask, smalltalk, ack and yes
  after ask) are sampled with seed 4052 so that NONE cards total 4 per correction card, or all of them if fewer.
- Minimum to train: 300 correction cards, at least 80 of them correct_ref. Fewer means no training and a report.
- Hygiene rule 1: the targets are a fixed structured label, like lis-320's JSON frames, not a sentence frame
  (disclosed).

## Data gate (rule 2; before any training, like y1t's GATE-data.md)
- Draw 60 training cards with seed 4053: 30 corrections (15 of them correct_ref) and 30 look-alike NONE cards.
- Two blind judges (fresh agents, each reading only its own folder; never trained on, tuned on or quoted) answer
  from the notes and the message: "Does this message change note N to v?" or "Does this message change no note?"
- A fresh third judge settles any disagreement.
- PASS if at least 54 of 60 agree with the code label. Otherwise no training, and the labels are fixed from the text
  by code or GLM, never from the judges.
- The judges' 60 cards come from the training cards only. No judge, panel writer or auditor sees the uw-1 DEV cards,
  the lis-320 seeds or the test panel (beyond the panel writers' and auditor's own work).
- The judges only decide whether the data is used. Nothing trained on is written or judged by Claude (Ben 16:39).
- Reported beside the card counts: the value-span drop count, the implicit-change and former-of-current skips, and
  the dropped-turn count.

## DEV stop rule (before the test panel is used)
- After training, B runs on the 569 uw-1 DEV cards (pilots 320 and 321, readable).
- If B has more than 5% false changes on DEV's non-correction cards, or fewer than 10 of 47 DEV corrections right,
  the test panel is not spent. The DEV counts are reported, and uw-2 is marked FAIL (DEV).

## Test set (TEST-ONLY)
- A fresh blind corrections panel written to artifacts/claude-sf401-20260926/PANEL-SPEC.md, plus one addendum: at
  least 30 of the at least 60 corrections are about a named person or pet who is referred to in the correction
  message only by a pronoun or role word. These are the earlier-owner corrections, spread over styles 1-6.
- Single blind writers, a blind audit, copied unread and sealed before any run.
- Every user turn becomes a card (claude_uw1_cards.cards_bank). Scripts print counts only.
- "Earlier-owner" is defined by code: a correction card whose owner is not the user and whose owner's name is not a
  whole word in the message.

## Marks
Let E be the number of earlier-owner corrections, C all corrections and O all other cards. Right, WRONG_CHANGE,
FALSE_CHANGE and UNPARSED are claude_uw1_cards.grade with the note form. A right answer points at the corrected
note, names the new value and does not name the old one.

| Row | What | Bar |
|---|---|---|
| U1 (main) | earlier-owner corrections right | B >= A + max(10, ceil(E / 3)) |
| U2 | all corrections right | B >= A + max(15, ceil(C / 4)) |
| U3 (hard cap) | false changes on the O other cards | B <= ceil(O / 100) |
| U4 (hard cap) | false changes on decoy and nosave turns | B <= 2 |
| U5 | wrong changes on correction cards (wrong note or wrong value) | B <= ceil(C / 10) |
| U6 | unparsed, all cards | B <= ceil((C + O) / 50) |

- PASS only if all six pass.
- INCONCLUSIVE (U1 undecided, the rest reported) if E < 30.
- Proved wrong ("training teaches the 1B to apply earlier-owner corrections from notes"): B <= A + 2 on U1.
- Report only:
  - corrections right by style;
  - A's U3-U6 counts;
  - DEV counts;
  - lis-319f's 4 of 60 from another panel, with the note that it is not comparable.
  Reading facts' condition 3 (corrections that never reached the notes) does not arise: the notes are oracle. Its
  end-to-end share stays theirs (C1).

## Machine and cost
- BensPC ($0): data build, gate prep, training, DEV check and the panel run for both arms.
- Mac: none beyond lis-320's own GLM run, so no extra GLM calls.
- Blind judges and the panel writers are Claude agents in the cloud (sealed-test and gate use only).
- No rental and no new model download on Ben's machines.

## Plain summary for Ben
When you correct something about a person you mentioned earlier ("sorry, she's 13"), our assistant usually drops the
correction. The reading step can't tell who "she" is, and a safety check then refuses to save it. The standard fix
in memory systems is to show the writer its old note and let it update that note. That keeps the person the note
already names. Out of the box, the small model can't do this: it got none of 47 practice corrections right. This test
trains it on GLM's practice chats, where code knows the right answer. It then checks, on fresh test chats, whether
it fixes those corrections without changing notes it shouldn't: at most 1 wrong change per 100 ordinary messages.
