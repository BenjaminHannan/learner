# q-404 blind panel (2026-09-26)

**TEST-ONLY: never opened, printed or quoted except by the runner and scorer.**

Written blind by a separate agent for q-404 (see `artifacts/claude-q404-20260926/PASSMARKS-q404.md`, "Test data").

## Files

- `math.jsonl`: 100 everyday word problems (shopping, time, distance, recipes, sharing, money, rates), one positive-integer answer each.
  Fields: `id`, `text`, `answer` (int), `calc` (Python arithmetic expression over the problem's numbers; evaluates to `answer`), `you` (bool).
  - 60 items with `you`=true, phrased with "you"/"your".
  - 40 items with `you`=false, containing no "you", "your" or "yourself".
- `self.jsonl`: 60 questions containing 2+ digit numbers that must NOT go to the calculator/think path. Fields: `id`, `text`, `kind`.
  - 30 with `kind`="assistant": about the assistant itself (abilities, memory, preferences), phrased with you/your.
  - 30 with `kind`="user": asking the assistant to recall what the user told it, phrased with you/your.

Every item is in question form, has 2+ numbers written as digits, and names no people. All `calc` values were checked to equal `answer`; no duplicate texts.

## sha256

- math.jsonl: `8776aa553f1163b24ffc16ed7429ebcdc696ac87c5aa3517e6e3abbc76bb001c`
- self.jsonl: `55a82c261e1f9f62a3d827e1da1563781cd83305e1ec307cde87921ef89676db`

`SEAL-panel.sha256.txt` holds the sha256sum of math.jsonl, self.jsonl and this README.
