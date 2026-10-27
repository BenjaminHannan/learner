# Scorer check on smoke 2's whole replies (2026-09-26 17:11 UTC, sleep research thread)

**Replies.** Benchmarks' smoke 2, on builder-outbox at artifacts/claude-bmriv-smoke-20260926/run2/rival_{plain1b,qwen2b,lfm12b}_4k.jsonl. These are 8 of this smoke panel's 30 items (7 for qwen2b), with thinking off and a 4,096-token cap. This panel is a smoke panel, not a test panel, so reading replies is allowed.

## Four scorer bugs found and fixed in scripts/claude_rsn358b3_panel.py (before any sealed panel)
1. **think_closed=false was read as "cut off".** The rival runner writes false on every thinking-off reply, so no broken item could ever be right. Now only hit_max counts as cut off. An unclosed thinking reply is already "" and so not right.
2. **A capped reply could still count right on a solve item.** Now a capped reply is never right on any item, as the docstring always said.
3. **Missed answer formats.** Two were missed:
   - Markdown tables with a header row "| | 1 | 2 | ... |" and row labels "| **Row 1** |" or "| **1** |";
   - LaTeX arrays ("1 & 5 & 2 \\\\" with \hline).

   Both are now read, with selftests added.
4. **A broken item counted right when the reply attempted a square with numbers outside 1..s.** One lfm12b reply had rows containing 7, 8, 9 and 0 on a 6x6 square. Now any attempted square (s rows of s numbers) on a broken item is wrong.

## Effect on smoke 2 (right / n)

| arm | before the fixes | after | cut off |
|---|---|---|---|
| plain1b | 0 / 8 | 0 / 8 | 2 |
| qwen2b | 1 / 7 | **5 / 7** | 2 |
| lfm12b | 1 / 8 | 0 / 8 | 0 |

Qwen, the bar, had 4 valid final squares that went unread: 3 were in tables and 1 in a LaTeX array.

**Hand check.** I read the end of every reply scored "no grid" that was not capped.
- None holds a valid final square.
- They are incomplete squares, rows with blanks, rows of the wrong length, or numbers outside 1..s (such as 7, 8 and 9 on 5x5 or 6x6 squares).
- Every "VALID" is the code's is_solution check against the puzzle.

**Cap.** Qwen hit 4,096 on 2 of 7, plus 2 near misses. So 358b3 seals 8,192 for thinking-off arms, as Benchmarks recommended, with hit_max reported.
