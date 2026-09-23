# smallpanel282b (exp 282b blind panel, 2026-09-23)

Blind test panel for experiment 282b (casual greetings and closings).
Written blind: the writer never read or ran any agent or scorer code,
and never opened any other panel.

## Counts per category

| category | turns | gold |
|---|---|---|
| greeting | 20 | `smalltalk` |
| closing | 15 | `smalltalk` (thanks and closings) |
| mixed | 15 | stored triple `Subject\|relation\|Object` for teaches, exact expected answer for questions |
| control | 10 | stored triple `Subject\|relation\|Object` for teaches, exact expected answer for questions |
| total | 60 | |

## Layout

- `panel.jsonl`: one line per turn, keys exactly
  `dialog_id, turn_index, user_text, category, gold`.
- 48 dialogs: 20 single-turn greeting dialogs (`d_greet_01`–`d_greet_20`),
  15 single-turn closing dialogs (`d_close_01`–`d_close_15`),
  8 mixed dialogs (`d_mix_01`–`d_mix_07` two turns: teach then question;
  `d_mix_08` single teach), 5 control dialogs (`d_ctl_01`–`d_ctl_05`,
  two turns each: plain teach then plain question).
- `turn_index` is 0-based within each dialog.
- All names are freshly invented and fictional. No real person is named.
- Greeting/closing turns are pure small talk (slang, typos in filler
  words, extra words, emoji) and name no entity.
- Mixed turns pair small talk with a real teach (`my <animal> is called
  <Name>`, gold `<animal>|called|<Name>`) or a question about a fact
  taught earlier in the same dialog (gold: the taught name).
- Control turns are plain teaches and matching questions with no small
  talk, in plain wording and punctuation.
