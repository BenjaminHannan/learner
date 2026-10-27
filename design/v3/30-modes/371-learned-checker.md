# rd-371: a learned "am I sure?" checker (plan and CPU preview, 2026-09-25 10:00 UTC, reading thread)

Status: preview only. Nothing registered, no GPU used. Road map: 370-reading-roadmap.md.

## Why (verified counts)
- lis-318 panel (sealed readpanel318, scorer counts only): the old reader reads 239/255 facts right before the gate but saves 111;
  lis-318 reads 237 and saves 132. The fixed 0.995 min-token cutoff is where most right facts are lost.
- Per-fact preview on DEV (lis-318 reader on its own dev set, 1,181 turns; a fact counts when it passes the structural check; gold
  = the per-fact checkable gold facts; scratch script, report only):

| cutoff | right facts kept (of 948) | wrong facts kept |
|---|---|---|
| none | 948 | 17 |
| 0.90 | 882 | 7 |
| 0.95 | 844 | 5 |
| 0.99 | 737 | 3 |
| 0.995 | 673 | 2 |
  lis-301 on its dev: none 743 right / 10 wrong; 0.90 701 / 5; 0.995 534 / 2.
- The wrong facts that survive a high cutoff are mostly role swaps and type clashes, which min-token probability can't see:
  "Bo speaks the language of Ressic" -> Ressic/language/Bo; "Yola created the mural" -> Yola/creator/mural; "oddny has a horse called
  Storm ... she's 80" -> Storm/age/80; "My father died in Sare" -> me/father/Sare; "Laila's birthdya is Agust 3" -> place_of_birth.
  A few are near-synonyms the bank labels differently (city vs work_location, hometown vs country_of_origin).

## The one change (proposed)
Replace the min-token cutoff with a learned verifier: the same MiniCPM5-1B base with its own small LoRA, asked
"Turn (+ last reply): ... Fact: <owner> <rel> <value> (<mode>). Stated by this turn? yes/no", gate = P(yes).
Training rows, all from existing agreed training data (never DEV, panels, bank A/B, LoCoMo or LongMemEval):
- yes: every agreed gold fact (o0b, opus300/301, chat318, hist319);
- no, made by plain code from the same turns: owner/value swapped, owner moved to another name in the turn, value moved to another
  span in the turn, relation changed to a different relation of the same owner type, mode flipped (PLAN/SUPPOSE/REPORTED/NEGATED
  read as ASSERT), the "we" owner read as "me";
- no, real: the reader's own wrong writable facts on its TRAINING rows at sampling temperature 1.0 (GPU step).
Cutoff chosen on DEV by the lis-300 rule (0 wrong-save turns), per-fact release as in the live stack.

## Test (to be registered before any training)
A fresh blind panel (readpanel371, written and blind-labelled like readpanel318, but with more chat shaped like the 330 DEV bank:
second facts in one turn, role-swap traps, reported/planned facts). Arms on the same reader reads: A = min-token 0.995, B = verifier.
Draft marks: B saves >= A + 30 right facts; B wrong-save turns <= A's + 1 and <= 2; no-fact turns with a save <= 1; B adds <= 400 ms
median. Proved wrong if B saves <= A + 10 at its dev cutoff.
