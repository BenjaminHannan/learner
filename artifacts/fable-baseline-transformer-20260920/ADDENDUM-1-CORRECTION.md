# Correction to Addendum 1 (2026-09-20, appended; Addendum 1 is left byte-for-byte as hashed)

Addendum 1 says "no arm of S was ever trained that way on full stories successfully either". That is wrong: operator variant `e0` (answer loss only, full stories
from the first update) succeeded in seed 0 (and failed to start in seeds 1 and 2). Also, per Astra's audit 18 §1: the 11k baseline failure is a failure to fit whose
cause is unresolved — "under-trained" is only the registered reporting label; the baseline's Linear layers are initialised at std 0.02 while the successful operator rescales
to 1/sqrt(3·fan_in) ≈ 0.083, an unmatched ~4× difference (untested as a cause); and the dev run's 0.684 token accuracy came from END tokens and intermediate people, not
attribute lookup (1/10 one-hop on Astra's diagnostic draw). A-ev stays the registered hint-only intervention; initialisation-matched arms follow as baseline v2.
