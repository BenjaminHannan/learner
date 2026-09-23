Blind panel build for 263 — pulling the spec and locking in additive-only rules.
Spec is clear on families and schema. Now learning the base-260 drive method without touching blind files.
Base behavior mapped. Probing more opener candidates for the junk-subject effect.
Base run finished. Checking counts and determinism.
Determinism confirmed. Restoring single-marked panel, then sealing.
DONE — blind panel commapanel263 built, base-run, and sealed. No item text quoted below, only category counts and ids.

## Verdict: PASS (panel sealed, base260 measured)

Folder `artifacts/claude-commapanel263-20260923/` holds panel.jsonl (60), base260.jsonl (60 rows), make_panel.py, run_base.py, README.md (category level only), SEAL.sha256.txt. Seal check: 4/4 OK.

## Marks table (base260, integer counts)

| family | n | base right | base junk (comma subject) |
|---|---|---|---|
| unlisted_opener_teach | 20 | 1/20 | 16/20 |
| appositive_subject | 10 | 0/10 | 0/10 |
| comma_value_ok | 8 | 8/8 | 0/8 |
| question | 8 | 4/8 | 0/8 |
| control | 14 | 14/14 | 0/14 |
| TOTAL | 60 | 27/60 | 16/60 |

Junk count: 16 rows store a comma subject (all in unlisted_opener_teach). Question/followup writes: 0 rows. Control 14/14 right. Schema: 10 panel fields and 10 base-row fields on every row, ids c263-001…c263-060, no duplicate turns, all names fictional.

## Every move/miss (by id only)

- unlisted_opener_teach wrong (19): c263-001 … c263-019 except c263-020 is the single RIGHT one. Of the 19: 16 WRONG+JUNK (opener glued into the stored subject, followup then fails), 3 WRONG without junk (nothing stored at all).
- appositive_subject wrong (10): c263-021 … c263-030, all WRONG, 0 junk (base stores nothing, so the followup fails).
- comma_value_ok: all 8 RIGHT, 0 junk (comma stays in the value, subject clean).
- question wrong (4): c263-043 … c263-046 (base asks for clarification, 0 writes); c263-039 … c263-042 RIGHT.
- control: all 14 RIGHT. Misses: 0.

## Deviations

1. The OPUS-RULES probe path `.../scratchpad/dialog_nb.py` does not exist. I drove the base the same way it describes: fresh agent per item, setup→turn→followup in order, triples read after each turn, plain_turn in a second fresh agent — via `loop.turn()` in-process with isolated /tmp state dirs. Never touched repo-root notebook/.
2. Determinism check: ran run_base twice; base260.jsonl byte-identical both times. The rerun double-appended note markers, so I restored panel.jsonl to the single-marked run-one copy and re-verified counts; sealed files are run one.
3. Additive only: 5 new files in the new folder; nothing edited, deleted, committed, or pushed (OPUS-RULES forbids pushes; the PUSH line is taken as the deliverable path). Never opened fix263/comma263/fix260 word lists, builder dev files, TEST-ONLY panels, or openpanel260 item files. CPU only, one process, disk was 18 GB free (over the 3 GB floor).

## What it means (plain high-school English)

The base agent handles listed openers fine, but everyday openers outside its list break it: 16 out of 20 unlisted-opener teaches save a junk name with the opener glued on, and 3 more save nothing at all. Appositive subjects save nothing. Comma values and plain controls are all safe. The panel gives the fix a clear target: strip any opener before the comma and never store a subject with a comma.

## What it doesn't mean

It doesn't mean the fix will be easy or complete — this is 60 items, not every sentence a user could type, and the appositive cases store nothing on the base, so they only guard against new junk rather than proving understanding.
