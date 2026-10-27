# Note judge brief v2 (371c contract; replaces the single verdict of rd-378's JUDGE_NOTES.md for new work)

Never use WebFetch. Never call any mcp__hearthbot__ tool. Do not run git. Open only your input file and write only your output file.

Input {INPUT}: one dialog per line {"dialog","kind","speakers","date","turns":[{"t","speaker","text","notes":[{"text","cites","when"}]}]}.
cites are offsets from the note's own turn (0 = that turn, -1 = the turn before, ...). You see exactly what the checker
sees: the note's turn, up to 6 turns before it, the note's text, its cites and its when.

For EVERY note give four true/false judgments, each on its own:
- supported: every fact in the note is stated by the cited turns (reading other turns only to know who "she"/"that" is).
  A plan, wish, guess, joke, hypothetical or what someone else said, written as a plain fact, is NOT supported.
- person: every fact is about the person the turns say it is about (no role swaps, no wrong owner).
- time: "when" matches the time the turns give for this note, or is empty when the turns give none.
- cites: every turn the note needs is cited and no cited turn is unneeded.
Also "form_ok": one plain third-person sentence with names (report only; it does not decide the label).
For EVERY non-assistant turn also give "missed": the number of clearly memorable things no correct note of that turn covers.

Output {OUTPUT}: one JSON line per non-assistant turn:
{"dialog","t","judgments":[{"supported":bool,"person":bool,"time":bool,"cites":bool,"form_ok":bool}, one per note in order],"missed":int}.
Check with Python that every non-assistant turn has one line and the judgment count equals the note count.
Reply with counts only. Never quote dialog text.
