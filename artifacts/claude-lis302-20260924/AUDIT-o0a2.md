# lis-302: blind dev-label audit (report only, 2026-09-24)

Input: 40 lis-301 dev rows, fixed by seed 302. There are 11 rows the reader got wrong at T = 0, plus 29 control rows. Two independent blind Opus labellers (L1 and L3) labelled them from the frame spec alone. Neither saw the key or the reader's output. A third run (L2) was not independent and is ignored.

The 2 rows that stay wrong at T = 0.995:
- "Guess my favorite color is blue" (o0a2-q050). Both labellers save it as a plain statement, but the key calls it SUPPOSE. This is a key dispute, not a clear reader error.
- "Ada was born in May" (o0a2-s125). Both labellers read it as a birthday, and the reader read place_of_birth. This is a real misread of an ambiguous word.

Of the other 9 wrong-at-T=0 rows, the "hazels" owner row has both labellers agreeing with the reader, not the key.

Controls: the labellers agree with the key on 47 of 58 labels. Most disagreements are city vs home-type relation noise.

What this means: at most 1 of the 2 remaining dev wrong turns is a clear reader error. The o0a2 key still carries some label noise.
