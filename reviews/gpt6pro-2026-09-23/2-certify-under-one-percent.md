I need a statistically honest way to certify that a system's rate of "wrong saves" is below 1%, and I think the textbook answer is not enough. Please design the procedure.

THE SYSTEM
A small assistant reads chat turns and saves facts into a notebook. A "wrong save" is any saved fact the turn did not assert (including saving from a turn that should save nothing). The goal is a certified wrong-save rate < 1% at 95% confidence. Correct refusals ("I didn't save that; did you mean ...?") are allowed but costly, so we also need recall (fraction of true facts saved) >= 85%.

HOW WE TEST NOW
- Every change is one sealed experiment: code and pass marks are hashed before the run.
- Test sets are "blind panels": ~150 turns written by a separate agent from a written spec (families such as plain statements, varied phrasing, corrections, turns that must save nothing, plural owners, appositives, plans and pretend turns). A panel is used once for a registered verdict and never trained or tuned on. Writing and grading a panel costs roughly half a day of agent time; gold labels come from the writer and are sometimes wrong.
- Plain binomial maths: 0 wrong in 299 turns gives a 95% upper bound just under 1% (1 wrong -> 473, 2 -> 628, 3 -> 773 turns); 0 in 150 only bounds it at 1.98%.
- Observed: fresh panels are harder than old ones, and each new panel adds risk categories the old one lacked, so "the rate" depends on who writes the panel. The answer key can also be wrong: on one panel, 6 of 9 scored "wrong saves" turned out to be right facts that the key had labelled with a broader relation word ("pet" where the reader wrote "dog").
- We run many experiments (dozens) against a sequence of panels and pick the version to ship from among them.
- We have a strong local model that can act as an automatic grader of wrong saves, and a large supply of unlabeled synthetic chat, but the grader itself approved confident errors in the past.

THE HARD PART
1. What does "rate < 1%" even mean when the distribution is set by a panel writer and each panel is deliberately harder? Propose a target population and a sampling design (e.g. stratified by risk family with fixed weights, adversarial families counted separately) that makes the claim meaningful and not gameable.
2. How do we avoid the winner's curse and multiple testing when many versions are compared and the best is shipped? (Holdout reuse, a final untouched certification panel, alpha spending, or something better.)
3. Can prediction-powered inference, active statistical inference (label mostly the uncertain turns), or stratified importance sampling reduce the number of human-checked labels below ~300 without breaking validity, given the rate is near 0 and the automatic grader can be confidently wrong? Where exactly would large-sample (CLT) intervals mislead near 0%, and what exact or finite-sample alternative works?
4. How do we handle gold-label errors in the panel itself?

WHAT I NEED BACK
- A concrete certification protocol: number of turns, strata and weights, who labels what, the exact interval or test (formula), and the decision rule, with a worked numerical example.
- Pass marks fixed in advance for a first run of the protocol, and the result that would show the protocol is not valid (e.g. a simulation check with known error rates).
- One change at a time: say which part to adopt first.
- Label every claim as shown (proved or published), suggested (published in a different setting), or untested (your reasoning). Cite papers with arXiv IDs where you can.
- A plain-language summary of 6-10 sentences for a high-school senior.

This question is only about the chat pipeline's write safety. Keep it separate from any "small card experiments" or "village model" results.
