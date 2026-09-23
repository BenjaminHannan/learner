Blind panel build for exp 291 — fetching spec and writing your file.
Spec is clear on families and counts — now mapping the base setup.
Base setup matches — now studying the run pattern.
Checks passed — now piloting the base to confirm wording storage.
Pilot shows the base pattern — testing a few more wordings.
Design finalized — now writing the 96-item panel.
Duplicate turn caught — locating it.
Self-checks pass — fixing one setup inconsistency before the base run.
Base runner path bug — fixing it.
Base run shows 11/12 controls and one mis-targeted denial — fixing both pre-seal.
Controls now 12/12 — verifying acceptance checks.
README done — sealing the panel.
VERDICT: PANEL SEALED — READY FOR BUILDERS (artifacts/claude-corrpanel291-20260923/, 96 items, base 138nb run, shasum -c OK).

Marks table — base 138nb, integer counts (right / n, wrong_value, false_claim, junk; followup writes 0 everywhere):

- verb_denial: 0/8, wrong 8, fclaim 0, junk 0
- possessive_denial: 2/8, wrong 6, fclaim 1, junk 0
- contextual_denial: 0/8, wrong 8, fclaim 0, junk 0
- contextual_correction: 0/8, wrong 8, fclaim 0, junk 0
- explicit_correction: 0/8, wrong 5, fclaim 0, junk 2
- tail_denial: 0/8, wrong 6, fclaim 3, junk 0
- opener_teach: 0/8, wrong 0, fclaim 0, junk 7
- opener_correction: 0/8, wrong 7, fclaim 0, junk 0
- unstored_denial: 6/6, wrong 0, fclaim 0, junk 0
- ambiguous: 6/6, wrong 0, fclaim 0, junk 0
- question_trap: 8/8, wrong 0, fclaim 0, junk 0
- control: 12/12, wrong 0, fclaim 0, junk 0
- TOTAL: 34/96 right, 48 wrong_value, 4 false_claim, 9 junk, 0 followup writes.

Every move / every miss: misses are all non-right items above (62 total). No silent passes: cause families were not filtered; reported as observed. Control is 12/12. Stated-vs-stored mismatches 0. Contextual single-value check 16/16. Ambiguous 2+/0 check 6/6. Lowercase turns per cause family: 3, 2, 3, 2, 2 (quota met). Relations used: 10. No duplicate turns. No git push (OPUS-RULES forbids it); files are sealed locally.

Deviations (all pre-seal, own draft only; sealed files untouched after seal):
1. Fixed 2 duplicate turns found by self-check (reworded, same families).
2. Fixed one possessive item whose turn denied the wrong value (now denies the stored value).
3. Replaced one failing control denial with a plain teach (control now 12/12).
4. Fixed runner path bug (repo-root resolution) before the sealed base run.
5. Ran base twice total (draft + final sealed run) because of fixes 2-3; final figures above are from the sealed run only.
6. false_claim has no target field in this schema, so I adapted the 258 rule: still-stored value in turn reply plus a removal/change claim word (don't have / do not have / removed / updated / deleted / changed). Same code in run_base.py and score_panel.py.
7. Disk stayed at 12 GB free (above 3 GB stop line); load 42-56 (below 60); CPU only, one process at a time.

What it means (plain English): the base handles plain questions, untouched-topic denials, two-fact and no-fact ambiguous cases, question-shaped traps, and simple plain teaches/denials well. It fails almost all verb-worded denials, bare context replies, full corrections, tailed denials/corrections, and opener-led teaches/corrections. Opener teaches mostly store junk. A few tailed/possessive replies claim a removal that did not happen.

What it doesn't mean: these numbers do not grade any new builder agent; they only describe the old base the panel was measured on. Low scores on cause/tail/opener families are the test working as designed, not a failure of the panel. The panel does not say why the base fails, only where.
