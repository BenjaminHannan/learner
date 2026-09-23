Writing your blind 280p test panel — pulling the spec and sealing fresh items.
Spec is clear — now I'll build your 90-turn panel.
Counts check out — sealing the panel now.
VERDICT: DONE — blind 90-turn panel written and sealed at artifacts/claude-joinpanel280p-20260923. No code read or run.

Marks table (integer turn counts, total 90):

| category | count |
|---|---|
| ability | 25 |
| teach | 8 |
| called | 12 |
| smalltalk | 25 |
| mixed | 10 |
| control | 10 |
| total | 90 |

Dialogs: 73 (25 ability + 25 smalltalk + 8 teach/called + 10 mixed + 5 control). Keys on every line exactly: dialog_id, turn_index, user_text, category, gold.

Every move:
- Checked uptime (load ~48, but no heavy run needed) and df -g / (9 GB free, over the 3 GB floor).
- git fetch -q origin main; read ONLY the Panel-spec slice of design/v3/30-modes/280m-talking-join.md via origin/main (90-turn spec: 25 ability / 8 teach + 12 called / 25 smalltalk / 10 mixed / 10 controls).
- Created new dir artifacts/claude-joinpanel280p-20260923 (it did not exist).
- Wrote panel.jsonl (90 lines), SPEC-COPY.md (verbatim spec copy + gold-mapping note), README.md (counts + layout).
- Validated counts/keys with one offline Python check (90 lines, keys exact, 73 dialogs).
- Sealed: shasum -a 256 panel.jsonl SPEC-COPY.md > SEAL.sha256.txt. Files untouched after seal.

Every miss: none. No TEST-ONLY panels touched, no scripts/ or other artifacts/ panel opened (only listed dir names), no repo-root notebook writes, no secrets, no commits/pushes, fictional names only.

Deviations / judgment calls (spec was silent, so I picked and documented in README):
- Teach+called layout: 8 dialogs; tc_01–tc_04 hold 1 teach + 2 called, tc_05–tc_08 hold 1 teach + 1 called = 8 teaches + 12 called, every question after its teach in the same dialog.
- Four called shapes each used 3 times (called/named wordings asking for the taught value; gold = exact value).
- Mixed: all 10 are small-talk + ability question, standalone dialogs, gold ability_list (spec allows ability OR called; I chose ability so no extra teaches were needed).
- Control: 5 dialogs x (teach + plain question) = 5 control-teaches (gold triple) + 5 control-questions (gold exact value).
- No abstain items used (brief lists abstain as allowed, not required).

Seal file contents:
5f56887c19eaefdf29b81ca490b907dd45fc7e64ff390c9e60bf35e78ace8731  artifacts/claude-joinpanel280p-20260923/panel.jsonl
978cdce3af69b80f95739dc79c53ca99cc641de6bec13f0b9e28858513f7c2af  artifacts/claude-joinpanel280p-20260923/SPEC-COPY.md

What it means (plain high-school English): there is a fresh 90-question quiz ready for the re-test, with the right mix of question types and answer keys, locked so nobody can quietly change it later.

What it doesn't mean: it says nothing about whether the talking-line join works — I never ran any model or scored anything, I only wrote the test.
