# ip-1 blind recount: agrees, FAIL (I2, I3, I4)
A blind agent read only PASSMARKS.md and ip1_results.json and recomputed every mark from the per-kill raw fields:
I0 5/5 PASS, I1 11/11 PASS, I2 10/11 FAIL (k08, v0004), I3 6/11 FAIL (k05 32.79 s, k06 19.83, k08 36.92, k09 20.2,
k10 40.08; all over 15 s; answer text was not stored per kill, so only the time part could be recounted), I4 FAIL
(v0005 accepted and active, rc 0, fingerprint not matching), I5 PASS (0.06 s, rc -15), D1-D4 PASS (booleans only).
No precomputed flag disagreed with the recount. Caveat it added: k07's random kill (88.3 s) came after the night
finished (91.5 s night, rc 0), so 5 of the 6 random kills hit a running night.
