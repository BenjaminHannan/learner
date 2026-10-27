# Exp 247 PASSMARKS (cause C1: missing-apostrophe questions) -- written before any registered run

Base: scripts/claude_loop228_agent.py + artifacts/claude-determinism228-20260922/loop228-config.json.
Agent: scripts/claude_loop247_agent.py (Loop247Daemon; SrcGuardMixin228 first, install_srcguard228() at import)
+ config artifacts/claude-apos247-20260922/loop247-config.json (byte copy of the 228 config).
The one change: scripts/claude_fix247_apos.py Apos247Mixin, outermost on the 138i ears, "?" turns only:
"<Name>s <stored relation>" -> "<Name>'s <stored relation>" when the name (1-3 words) is a notebook entity
by display name, "<Name>s" does not resolve, W is not a known alias, the 165 plural gate holds, and the
relation is already stored for that entity; the rewrite is kept only if the base then emits an ask about that
entity, else the original turn goes to the base unchanged.

Runner: scripts/claude_apos247_run.py (both arms interleaved in one process, fresh dir per arm per item).
Scorer: scripts/claude_apos247_score.py (askpanel243 schema check -> SCHEMA-MISMATCH exit 3 = VOID; scoring rules
exactly as in the schema brief). Dev cases: artifacts/claude-apos247-20260922/dev247.jsonl (writer
scripts/claude_apos247_devcases.py): 33 fix, 15 keep, 10 trap, 5 outside.

## Marks (registered, each run once)
| mark | bar |
|---|---|
| M1a | family no_apos on the panel: right >= 15/16 (90 %, rounded up) |
| M1b | wrong-value items on all 124: 0 |
| M1c | question writes on all 124: 0 |
| M1d | control 12/12 byte-identical to base228.jsonl base_reply |
| M1e | no item in another family (not no_apos, not combo) goes base_right true -> wrong or decline; untaught 10/10 no stated value; 0 NEW direction leaks vs base228 (base228 leaks listed, not counted) |
| M1f | combo items reported per item, no bar (a wrong value still counts in M1b) |
| M2 | dev: fix 33/33 right with no wrong value; keep 15/15 byte-identical to base228 rerun; trap 10/10 no stored value; outside 5/5 no wrong value; 0 question writes; setup replies identical across arms |
| M3 | suitediff218 vs 138i (rt136, rt143, sessions152, bench): 0 new WRONG / WRONG-WRITE / junk / lost OK; moves = predicted list = EMPTY (0 moves in every suite) |
| M4 | sleep smoke: sleeps 1, installed 1, probes 5/5, wrong 0, taught 50/50, overwrote 0, under 300 s |
| M5 | median over panel items of (mine q-seconds - base228 q-seconds), same process: <= +5 ms |

Verdict PASS only if every mark passes. Schema mismatch -> VOID (no verdict).

## Predicted moves
- Panel: the only replies that change vs base228 are in no_apos and combo items (combo items with a
  no-apostrophe name). No control/untaught/direction/other-family reply changes.
- Suites: none (pilot: 0 moves, GATE clean).
- Dev: 33 fix items move decline/opinion -> right; keep/trap/outside replies unchanged in class.

## Known limits (declared before the run)
- Greeting/please prefixes ("Hi! Who is Pells spouse?"), yes/no ("Is Orrin Pells spouse?") and verb forms
  ("Where does Pells spouse live?") stay as the base: their apostrophe twins fail on base228 too (dev class
  "outside"); fixing them would be a second change.
- A relation must already be stored for the entity; synonyms ("wife" for stored "spouse") are not mapped.
- Names must equal a notebook DISPLAY name (a surname alone, "Hales", never fires).
