# Exp 248 PASSMARKS (sealed before any registered run; panel not opened)

**Change.** One outermost ears mixin, scripts/claude_fix248_whats.py (Whats248Mixin), on base 228
(scripts/claude_loop228_agent.py + artifacts/claude-determinism228-20260922/loop228-config.json).
Agent scripts/claude_loop248_agent.py, config artifacts/claude-whats248-20260922/loop248-config.json
(content identical to loop228-config.json except two descriptive strings). 228 guard installed
at import and first in the daemon bases.

**Exactly what is accepted.** A turn that, after collapsing whitespace, ends in "?" and has no
"?" or "!" before its final run of marks; optionally ONE leading filler word from
{so, hey, hi, hello, yo, ok, okay, well, oh, um, uh, please}, optionally followed by "," or "!"
(the filler is dropped); then, as the first real word, whats / whos / wheres / whens / hows in any
casing, followed by whitespace and more text. The word must not resolve to a notebook entity.
Rewrite: "<word minus final s> is <rest, unchanged>". The rewrite is used only when the unchanged
stack hears it as an ask; otherwise the original turn is handled exactly as on base 228.
Names that only start with these letters ("Whatsley", "Whosby") never match.

**Marks (bars from the common brief; M1a family = whats).**
| mark | bar | predicted |
|---|---|---|
| M1a whats family on panel | >= 90 % right (>= 11/12) | 12/12 |
| M1b wrong values, all 124 | 0 | 0 |
| M1c question writes, all 124 | 0 | 0 |
| M1d control byte-identical to base228 base_reply | 12/12 | 12/12 |
| M1e other families: base_right true -> wrong/decline | 0 | 0 |
| M1e untaught with no stored value | 10/10 | 10/10 |
| M1e direction: new value leaks vs base228 | 0 | 0 (base228 leaks listed, not counted) |
| M1f combo | per item, no bar | only combos whose other cause is already read after the rewrite answer (e.g. "whats my city?" via Me166); combos that also need C1/A/B/D stay declined |
| M2 dev (dev248.jsonl, 57 items) | right 34/34, traps 8/8 clean, must-not-change 15/15 byte-identical to base228, 0 question writes | as bar |
| M3 suitediff vs 138i (rt136, rt143, sessions152, bench) | 0 new WRONG / WRONG-WRITE / junk / lost OK; moves = predicted list | predicted move list: EMPTY (0 moves in every suite), GATE clean |
| M4 sleep smoke | sleeps 1, installed, probes 5/5, wrong 0, taught 50/50, overwrote 0, < 300 s | as bar |
| M5 median added ms per panel question (248 - base228, same session, paired) | <= +5 ms | <= 0 ms |

**Scoring.** scripts/claude_whats248_score.py implements the askpanel243 schema check (missing
file, wrong fields, unknown family, wrong counts, wrong expect label, id mismatch -> print
SCHEMA-MISMATCH, exit 3, VOID) and the shared scoring rules. M1e regressions exclude control
(M1d), whats (M1a) and combo (M1f). `--panel-dir` exists only for the scorer self-test; the
registered run uses the default folder.

**Verdict.** PASS iff every barred mark passes. Any change to a sealed file after the seal = FAIL.
Pilot deviation already fixed before the seal: trap d248-042 first asked about a name that was
itself a stated value (the whole-word rule flags an echoed question name), replaced by
"whats Sella Voss's city?"; two must-not-change items added (whens, "whats Pell?").

**Order.** M2 dev, M3 suites, M4 sleep smoke, then M1+M5 panel after the panel's seal checks OK.
