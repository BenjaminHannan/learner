# PASSMARKS sf-401, addendum 1 (2026-09-26 ~13:45 UTC, before the panel exists and before any run)

Agreed with Reading facts, Month-end and "Making things up about you" (Ben's 12:48 integration rule). PASSMARKS.md
is unchanged; this addendum adds one mark and narrows the guard before sealing. The seal (SEAL-sf401.sha256.txt)
covers the code as it stands after this addendum.

1. Narrower doubts (Reading facts, 13:11 UTC). A doubt needs the frame's person to resolve to the saved person
   (same_person), and the frame fact in mode ASSERT or CORRECT (rules a, b) or NEGATED/FORMER naming the saved
   value (rule c). QUESTION, SUPPOSE, REPORTED and other modes never raise a doubt. The earlier rule-(b) exception
   (the user names the saved person in the same turn, for a misspelled reader owner) is removed. FORMER (lis-319f's
   "used to" mode) counts like NEGATED on the saved value; a FORMER value that is not the saved one never doubts.
   CPU tests 13/13 with the new cases.
2. New mark M6 (Reading facts' no-harm ask on "I don't know" rows): never-told asks answered "don't know" (scorer
   RIGHT on ask_type never_told), B ≥ A − 1. sf-401 PASSES only if M1-M6 all pass (INCONCLUSIVE rule unchanged).
   Report only, paired per ask: asks A got right that B did not, split into B's hedge line vs anything else.
3. Month-end's asks: both arms launch through scripts/claude_readersha_wrap.py with READER_SHA = the lis-319 sha
   (already in the job); a right-after-correction mark (ME1-style) is M3, already a mark.
4. The 0.2c bank D counts that motivated this change ran with the wrong reader weights (VERIFY-02c D1). This test does
   not use bank D: A is the right-weights agent on a fresh panel. When 0.2d-r's counts land they are quoted in the
   report as context only (H1 X' vs G), never as this test's baseline.

DEV replay after this addendum (scripts/claude_sf401_devreplay.py; dev/mechanical_dev_v2.json, dev/sf401_counts_v2.jsonl):
2 doubts (rules a and c), both on real correction turns, 0 on the other 192 DEV turns; the guard did not fire; every
count equal in A and B. The single DEV fix seen before came from the removed exception.
