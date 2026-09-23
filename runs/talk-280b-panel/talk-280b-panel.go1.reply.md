Writing your blind 280b panel — starting with the rules and spec.
Spec read. The 280b section calls for 50 turns: 25 general, 10 specific, 10 near-miss, 5 controls. Setting up the panel directory now.
Directory created. Writing the 50-turn panel now.
Files written. Verifying the verbatim copy and the JSONL before sealing.
Verbatim copy matches. Now validating the JSONL structure and line count.
Structure verified: 50 turns, 45 dialogs. Sealing now.
VERDICT: DONE — blind panel for exp 280b written, verified, and sealed. No misses on counts.

## Marks table (integer counts)

| Check | Spec | Written |
|---|---|---|
| Total turns | 50 | 50 |
| general ability questions | 25 | 25 |
| "Can you <specific>?" turns | 10 | 10 |
| near-miss non-ability turns | 10 | 10 |
| controls | 5 | 5 |
| Dialogs (scored last turns) | — | 45 (40 single-turn + 5 two-turn) |
| gold ability_list (scored) | — | 25 |
| gold unchanged (scored) | — | 10 |
| gold fact string (scored) | — | 7 |
| gold no_write (scored) | — | 3 |
| JSON lines valid, exact 5-field schema | — | 50 / 50 |
| Sealed files unchanged after seal | — | 2 / 2 |

## Every move made

1. Read the rules file in full before starting.
2. From the worktree root: checked `uptime` (load ~57, under the 60 limit; panel writing is light work anyway) and `df -g /` (12 GB free, over the 3 GB floor). Ran `git fetch -q origin main`.
3. Read ONLY the 280b section of `design/v3/30-modes/280-282-chat-fixes.md` via `git show origin/main:<path>` (saved to /tmp, read lines 64–80). Never used `git log`, never checked out main, never opened `scripts/`, any other panel, or any file inside another artifacts folder.
4. Created new directory `artifacts/claude-capabilpanel280b-20260923/` (confirmed absent first; purely additive, no existing file touched).
5. Wrote `panel.jsonl` (50 lines: dialog_id, turn_index, user, category, gold; categories general/specific/nearmiss/control).
6. Wrote `SPEC-COPY.md` (280b section transcribed verbatim + turn counts) and `README.md` (schema, counts per category, counts per scored gold). All names fictional and freshly invented; no spec-example names reused.
7. Validated with two read-only JSON structure checks on my own new file only (50 lines parse; categories 25/10/10/5; 45 dialogs with contiguous turn indexes).
8. Sealed from the worktree root with the exact required command. Never modified the files after sealing.

## Deviations and transparency notes

- I ran `ls artifacts/` (top-level names only) to confirm my target directory did not already exist. I never opened any file in any other artifacts folder.
- I ran Python twice via the mandated `uv run --offline` prefix, but only to JSON-parse my own newly written panel file. I never read, ran, or inspected any repo/agent code, scorer, or other panel.
- The brief's "PUSH" line is satisfied as files in place at `artifacts/claude-capabilpanel280b-20260923/`; per the standing rules I did not commit, push, or open a PR.
- Design care (not a deviation): every general item meets all four rule conditions (question-shaped or tell-me/list start, addresses the assistant, ability cue, no entity or relation word), with typos kept in filler words only so the 100% bar is fairly testable. Every specific item names one concrete ability target. Every near-miss names a person or is statement-form.
- Misses: 0. Every spec count is met exactly.

## Seal contents (report)

```
c37bac6824958115543359e30423ad2e8bf74c5b6e7213f3e40d51cdd23ee6b1  artifacts/claude-capabilpanel280b-20260923/panel.jsonl
36c3e88d2206635bd4ced2bb6b760e807bf24c732486ca9b16c3a26201bcdcb4  artifacts/claude-capabilpanel280b-20260923/SPEC-COPY.md
```

No items are quoted in this report or in the README, per the blind-panel rule.

## What it means / doesn't mean (plain high-school English)

- What it means: 280b now has a fresh 50-turn test with the exact mix the spec asked for (25 broad ability questions, 10 specific-ability questions, 10 tricky look-alikes, 5 plain controls), and the sealed copy proves nobody can quietly edit the test after seeing results.
- What it doesn't mean: this says nothing about whether the 280b fix actually works. The grades come later, when the builder's agent runs against this sealed panel.
