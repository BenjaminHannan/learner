**(1) Is "hloopd stops itself" fair as a one-seed lead?**

Yes, if worded exactly that way.

- **Shown:** On seed 0, hloopd passed every pre-registered STOPS ITSELF mark. All marks held on fresh rows: S1 +26.1 and Spearman 0.81.
- **Untested:** Whether this replicates on other seeds. hloop and hloops each have two seeds; hloopd has one.
- **Untested:** Whether it works without depth labels. hloopd uses depth labels in training, so this says nothing about a real assistant or real data.

**Red flags (suggested, not marked failures):**

- **Laps plateau at about 3.7 from depth 6 to 10.** The Spearman mark covers only depths 1-6, so it hides this. Depth tracking is shown for 1-6. Beyond 6 the rule appears to stop at a ceiling.
- **The stop rule throws away accuracy on far chains.** It scores 38.7 on far, versus 87 at a fixed 12 laps (still rising) and 65.7 for max-confidence. "Answer-stable" seems to lock onto a repeated wrong answer early. So "stops itself" holds only for near depths. It does not mean "stops at the right time" for far depths.
- **Laps used sit below training laps at depths 5-6.** Training laps were depth + 0..2, but the model used 3.3-3.6 laps at depths 5-6. The rule may be tracking difficulty roughly rather than counting hops (suggested).
- **The W=0 lesion** (97.9 → 86.1) suggests question feedback matters, from one seed only.

**(2) Cheapest single next test**

Rerun hloopd on seed 1 with the same marks and data, scored once on fresh rows. Do this before the pre-registered depth-label-free addendum.

- **Pass:** S1 ≥ +5 with CI > 0, S2 ≥ −2, and S3 ≥ 0.5 with CI above 0.3, all holding on fresh rows.
- **Proved wrong:** Spearman ≤ 0.1, or S1's CI includes 0.

**For Ben:** One training run showed the small looped model can decide when to stop on puzzles a bit longer than it practiced, but only when it was given the puzzle lengths during training. That needs a second run to confirm, and it stops too early on much longer puzzles, so it says nothing yet about real AI assistants.