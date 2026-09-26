# uw-2 test panel: addendum to artifacts/claude-sf401-20260926/PANEL-SPEC.md (part of the blind writer's brief)

Wrong-as-fact thread, 2026-09-26, for uw-2 (artifacts/claude-uw2-20260926/PASSMARKS-uw2.md, sealed 4d535f833).
The writer gets PANEL-SPEC.md and this addendum, and nothing else. Where they differ, this addendum wins.

The bank is TEST-ONLY. It is never trained on, tuned on, quoted or read by builders. It is written into the project's
shared folder (/mnt/project-files/escrow-uw2/), audited there by a second blind agent, and copied unread into
artifacts/claude-uw2-20260926/panel/ with its SEAL hashes before any run.

## What changes
1. Life ids stay `sf-t-01`..`sf-t-24`, so the existing checker runs unchanged. The people, pets and places are all
   new and invented. Do not reuse names you may know from other test banks.
2. Corrections: at least 72 in the bank, exactly 3 per life. They may fall on day 2 or day 3, before that life's
   edit asks. This replaces "2 or 3 per life".
3. Corrections about someone named earlier: at least 40 of the corrections (about 2 in every life) must be about a
   named person or pet who is not the user, where the correction message never uses that person's or pet's name.
   - The message refers to them only by a pronoun ("she", "he", "they", "her", "his") or a role word ("my sister",
     "the dog", "my boss", "his roommate").
   - That person or pet must be named in an earlier user turn of the same life, at least 2 turns before the
     correction.
   - The reference must be unambiguous to a careful reader of the whole life. A pronoun may be used only when one
     person in the recent turns fits it. A role word must pick out exactly one person or pet in that life.
   - Examples: "oh wait, she's actually 13, not 12", "my brother doesn't work at Pellam anymore, he's at Rusk Tools
     now", "the cat is a girl btw, her name's Pim not Pom".
   - Spread these over correction styles 1-6. Each style must be used at least 4 times among these 40.
4. The other corrections may be about the user or may name their owner, as in PANEL-SPEC.
5. Decoys and nosave: the PANEL-SPEC minimums stand (30 decoys, 15 nosave). At least 10 decoys must also refer to a
   person only by a pronoun or role word (for example, "my sister is visiting York this weekend" when she lives in
   Leeds).
6. Everything else in PANEL-SPEC stands: turn kinds, asks, decoys.jsonl and corrections.jsonl formats, truth
   closing rules and the writer's checks.

## Checks the writer runs before finishing (counts only; both must exit 0)
- `python3 scripts/claude_sf401_panelcheck.py /mnt/project-files/escrow-uw2/bank` (the PANEL-SPEC checks)
- `python3 scripts/claude_uw2_panelcheck.py /mnt/project-files/escrow-uw2/bank` (this addendum: at least 72
  corrections, each old fact a note; at least 40 earlier-owner corrections by the code definition; each owner named
  at least 2 turns before; decoy and nosave minimums)
- Both print counts and ids only. Fix the bank until both pass. Report only their printed output and the README
  counts.
