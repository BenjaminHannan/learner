# Post-hoc diagnosis of the FRESH-R7 talker drop (written 2026-10-09 before running; suggested-level only)

FRESH-R7 is not touched again. The diagnosis runs on the spent outside sets R3, R4, R5, R6 (cached, not GOLD-PRIVATE/reserved/blind)
for b0_s0, t1_s0, t2_s0. Nothing here changes a mark or the registered reading in RESULTS.md.

Measured per set: S (short EM), echo_exact (generation starts with the exact question), empty answer part share,
answer part not a substring of the prompt share (invented text), mean answer-part length vs gold.

Decision table (fixed before the run):
- T1 echo_exact on R3-R6 < 50 % while DEV echo is high -> main failure = the talker cannot repeat longer/unfamiliar questions.
- T1 echo_exact >= 80 % but S low -> failure is in producing the answer:
  - mostly not-in-prompt answers -> it writes TEACH-like answers instead of copying from the passage;
  - mostly in-prompt but wrong -> it copies the wrong words.
- 50-80 % echo -> mixed; report both.

## Addendum (after the first diagnosis run, before counting)
Examples showed answers spelled almost right ("Haleel" for Hale, "Danio" for Dani). Count, on the same spent sets and models:
near miss = a wrong short answer whose normalised answer part is within 2 character edits of an accepted answer,
or contains an accepted answer. Reported as a share of wrong short answers. Suggested-level only.
