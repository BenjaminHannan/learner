Building your blind test panel for exp 280 — inventing fresh items without looking at code.
Spec confirmed — now drafting the 40 fresh test items.
Panel validates — now sealing the files.
VERDICT: DONE, SEALED — blind panel for exp 280 written (40 test turns), sealed, ready in `artifacts/claude-capabilpanel280-20260923/`.

Marks table (integer counts):

| Category | Count |
|---|---|
| general | 12 |
| can_you | 20 |
| control_teach | 4 |
| control_ask | 4 |
| controls combined | 8 |
| total lines in panel.jsonl | 40 |
| dialogs | 36 |
| gold no_write | 32 |
| gold stored-triple (teach) | 4 |
| gold exact-fact (stored ask) | 3 |
| gold abstain (never-taught ask) | 1 |
| TEST-ONLY panels opened | 0 |
| code files read or run | 0 |
| existing files edited or deleted | 0 |

Every move:
- Created `artifacts/claude-capabilpanel280-20260923/panel.jsonl` (40 lines; fields exactly `dialog_id`, `turn_index`, `user_text`, `category`, `gold`).
- Created `SPEC-COPY.md` (280 section copied verbatim, source noted).
- Created `README.md` (schema + counts per category + dialog structure).
- Validated with the uv python prefix: 40 lines, categories 12/20/4/4, 36 dialogs, turn indices 0 / 0-1, all 3 stored asks match their teach triple values, abstain dialog correct, triple keys all subject/relation/value.
- Sealed: `shasum -a 256 panel.jsonl SPEC-COPY.md > SEAL.sha256.txt`. No changes after sealing.

Every miss: none. All 40 turns present, all categories at full count.

Seal file contents (`SEAL.sha256.txt`):
```
f5db799101c1432f09ad861bb2d284a43b6c039d49edab3244ebac9caa23f920  artifacts/claude-capabilpanel280-20260923/panel.jsonl
f3c286398e56e5985e66cbd25b97468316b68fbd7b7ad0b5fff98b5d5d7af877  artifacts/claude-capabilpanel280-20260923/SPEC-COPY.md
```

Deviations (honest list):
1. PUSH withheld: the brief says PUSH the directory, but OPUS-RULES hard rule forbids commits/pushes, so I staged, committed, and pushed nothing. Files exist sealed on disk in the worktree.
2. Note: `artifacts/` is gitignored in this worktree, so the new directory does not appear in `git status` unless force-added (which I did not do, per the no-commit rule).
3. To locate the 280 section I transferred the whole spec file to /tmp and read it, but I used only the 280 section (lines for exp 280) and copied only that section.
4. I ran `ls artifacts/` (names only) to confirm the target name was free and did not collide with the existing similarly-named `claude-capab280-20260923`. I never opened any panel file, script, or chatweak content.

What it means (plain high-school English): the test is ready and locked. Nobody can now quietly change the questions. The 32 ability questions check whether the bot only claims powers it really has, and the 8 control checks make sure normal teaching and asking still work.

What it doesn't mean: this says nothing about whether the exp 280 fix itself works. I never ran the bot or looked at its code. A scorer and the director still have to run the panel and judge the claims.
