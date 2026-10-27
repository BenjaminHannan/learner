# GPT-6 Pro on prompt 2 (certifying < 1% wrong saves): adjudication (2026-09-23)

Ben pasted the answer in the research thread, project message cmsg_01FuvegZXjMmeUzStiEFVnEWXk7XtTPMnHMERtyLzZDeHZ (02:49 UTC).

## The answer in one paragraph

Certify against a **fixed, written-down population**, kept separate from the ever-harder discovery panels. Draw each certification turn independently: pick its family at random with fixed weights, and write each turn in a fresh context by one of four frozen writer set-ups. Pick the version to ship *before* the test.

The first run:
- **Turns:** 600, testing at level 0.025.
- **Safety:** pass if at most 1 turn has a wrong save.
- **Recall:** keep at most one randomly chosen fact per turn. Pass if at least 150 facts are kept and the exact 97.5% lower bound on recall is at least 85%.
- **Retries:** each later attempt gets half the previous budget (0.0125, 0.00625, …), so a false certificate stays under 5% over all attempts.
- **Grader:** confidence intervals that lean on the automatic grader's guesses can be invalid near 0%. The one safe shortcut is that a turn with an empty write log provably has no wrong save.

## Numbers re-computed (shown)

I re-computed these with an exact binomial calculation (bisection on the binomial CDF):

| Claim | My result |
|---|---|
| Upper bound, 600 turns, level 0.025: 0 / 1 / 2 failures | 0.6129% / 0.9251% / 1.1989% ✓ |
| Lower recall bound L(181, 200) and L(184, 200) at 0.025 | 85.5623% and 87.3335% ✓; L(180, 200) = 84.98%, so 181 is the minimum pass ✓ |
| Chance to pass with ≤ 1 in 600 at a true rate of 0.5% / 0.1% / 1% | 19.84% / 87.82% / 1.69808% ✓ |
| 0.99^150 (all-zero grader fools a normal interval) | 22.145% ✓ |
| Labels needed with zero errors at 0.025 | 368 ✓ |
| Audits to bound the reviewers' miss rate < 0.2% at 99% | 2,301 ✓ |
| The no-write shortcut: 0.612619 × 0.0155263 | 0.9512% ✓ |
| Four all-or-nothing panels of 150 → P(zero errors) | 0.99^4 = 96.06% ✓ |

The simulation table in the answer (seed 20260922) was not re-run. It is GPT-6 Pro's own run.

## Checked against how our panels are made (shown)

- **Our blind panels break the independence the arithmetic needs.** Panel 261 was written by one agent with fixed family quotas (its `make_panel.py` builds the families to fixed counts). The answer's point stands: a number like "0 wrong in 299" from panels like these is not a valid binomial certificate, because turns from one writing session can fail together. Our panels stay useful as **discovery** panels, which is what they are good at.
- **Recall counted per fact is too optimistic.** Our scorers count recall over every gold fact. Facts from one turn are correlated, so a per-fact binomial interval would be too narrow. The one-fact-per-turn sampling rule fixes this.
- **Grading by meaning, not by key string:** "a dog save is supported when the turn says dog; a 'pet' key doesn't make it wrong". This matches the director's 261b ruling (a narrower relation counts as a hit).

## Where it doesn't fit this project (untested; needs Ben)

- **Human reviewers.** The answer's reference standard is two independent human reviewers per turn plus an adjudicator: about 1,200 reviews for 600 turns. Ben is the only human, and he has asked not to run things himself. With agents as reviewers, the certificate is exact **relative to agent-adjudicated labels only**. The answer's formula for adding a reviewer-miss bound needs a stronger reference than the reviewers themselves, which we don't have. The honest wording would be "certified relative to the agent reference standard".
- **Cost.** 600 fresh turns written by four frozen writer set-ups, plus two agent reviews each: that is Muse builder time, not money. It is several times the work of one of today's 150-turn panels.

## What to adopt first (the answer's own advice, and my pick)

The first change only:
- write the "Reference Population v1" contract (family weights, four frozen writer set-ups, one turn per fresh context, fixed schema and grading rules);
- keep it separate from the discovery panels;
- leave the reader and the checker alone.

Nothing is certified until a frozen candidate exists. Right now 261 FAILs and 261b is running, so the certification run itself is not due yet.
