# 0.2d gates, ADDENDUM-32: "obvious fix first" applied to 0.2d. Written 2026-09-26 19:24 UTC, before any seal or run

Rule from the Thread manager, 19:33 UTC, after Ben's 19:20 message: when an approach keeps failing, list the plain,
well-known fixes and test the simplest one next.
1. **Failing joined builds (0.1, 0.2c, 0.2d-r).** The textbook fix for a large joined system that keeps failing is to
   start from the smallest end-to-end build and add one part at a time. 0.2d is that build (ADDENDUM-24, 29, 31: no rule
   layers). It is untested so far. Its first test is D0 on BensPC once the gates pass.
2. **H1, wrong answers stated as fact (0.2d-r 12 vs 6).** Field fix: answer only when the answer is grounded in a
   source and the model is confident, else abstain (selective prediction, trained verifier). Brain fix, which is a
   guess: source monitoring, where a recalled detail is asserted only when its source comes back with it. The status of
   each:
   - self-consistency as the confidence signal: y1g, NO-GO (efa4d8923);
   - trained doubt: y1t, sealed (cd525ecf3), queued on BensPC, untested. It is next, and it fills 0.2d's doubt slot if
     it passes (ADDENDUM-29);
   - grounding: 0.2d's talker reads the user's own lines (the W input) and no rule answer path. mu-405 is testing this
     now (W vs K).
   In 0.2d-r, 28 of 42 missed corrections were lost at the reader and 14 at the answer step (sf-401 blame, da3294a87).
3. **Sleep slot.** SLEEP02D is no longer assumed to be an always-on adapter on the talker. It takes the form of
   whichever recipe passes H-B. That may be dl-8's error-gated nights (1771eba18, BensPC), or a separate-store-plus-switch
   design (complementary learning systems; the brain's hippocampus and cortex, a guess) if Fix sleep or Sleep research
   passes one. If the passing recipe is always-on, the no-harm rows (K1, C1, GSM8K/MMLU) are the check, as before.
No mark, bar, panel or arm changes. Free routes only.
