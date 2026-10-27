# 248: read "whats / whos / wheres" (diagnosis 243 cause C2) -- Opus builder

**Problem.** "whats Pell's city?" (no apostrophe in "whats") got the glued decline even
when Pell's city was stored. Qform158 (scripts/fable_fix158_qform.py:42) expands only
"what's"; no reader handles "whats". 243 counted 76 grid cells.

**One change.** scripts/claude_fix248_whats.py `Whats248Mixin`, the OUTERMOST ears mixin
(above ChainOf174), so ChainOf174, Typo165, Verb167*, Name173*, Me166, Qform158 and
FakeEars all see the expanded text. Agent: scripts/claude_loop248_agent.py
(`Loop248Ears(Whats248Mixin, Loop138iEars)`; 228 guard first in the daemon bases).
The 138i builder reads the global `Loop138iEars` when it builds; the 248 builder rebinds
it only for the duration of its own build, so base228 in the same process is unchanged.

**Rule (exact).** Turn (whitespace-collapsed) ends in "?", no "?"/"!" before the final mark
run; optionally ONE filler from {so, hey, hi, hello, yo, ok, okay, well, oh, um, uh,
please} with optional "," or "!" (dropped); then the first real word is whats / whos /
wheres / whens / hows (any casing), then whitespace and more text. That word must not
resolve to a notebook entity. Candidate = "<word minus s> is <rest unchanged>". Used only
if the unchanged stack hears the candidate as an ask; else the original turn is heard
exactly as before (same probe contract as Qform158/ChainOf174). hear() writes nothing.

**Known limits.** "whens"/"hows" expand but nothing below reads "when is"/"how is", so they
fall back unchanged. No-apostrophe possessives ("whats Pells city?") are cause C1, not
fixed here. "whos X married to?" still needs cause A's composer fix. A trailing
"please" ("whats X's city please?") is not handled (the base also fails it with "what is").
