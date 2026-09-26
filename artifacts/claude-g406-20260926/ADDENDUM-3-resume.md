# g406 ADDENDUM-3: resume plan for the transcripts without a usable answer (written 2026-09-26 20:34:05 UTC by date -u, before any resumed call)

- What happened: the registered run (ADDENDUM-2) stopped itself at 20:08 UTC on its failed-call limit after 80 of 560
  transcripts: 23 usable, 57 without a usable answer (run/RESULTS.md, run/glm.jsonl sha256 147818e3...). Its count is
  INCONCLUSIVE (V: 23 of 560 usable). The thread has seen the partial counts on those 23 transcripts (all mu-402). The
  marks, the prompt, the parser and the packets do not change.
- Gap found: claude_g406_glm.py wrote a helper failure and an unparseable reply as the same empty row, with no error
  text, so the cause cannot be read from the run. Row durations suggest repeated fast failed tries rather than timeouts
  (none of the 57 took 900 s or more), the same class as lis-320 pilot 3's exit-1 failures; the Mac's load average was
  about 185 at the start, and a one-worker retry of one failed transcript worked in 17 s. Suggested, not shown.
- Resume (scripts/claude_g406_glm_resume.py, new file; selftest 6/6): the same build_prompt and parse imported from
  claude_g406_glm.py; calls through the Director's helper v1.1 (scripts/claude_glm_opencode_v11.py, sha256
  7a067cfb...); 3 workers (the Director's share); a transcript counts as done only when a usable row exists; each row
  keeps the first 200 characters of the failure message, or "unparsed reply" and the reply's length. The final count
  reads the merged rows (for each transcript the usable row wins) with the unchanged claude_g406_count.py and the
  unchanged marks.
- Timing: the resume waits in handoff/held/ until the Director's lis320-ocdiag job says whether the failures come from
  load or from the prompt's form. If the prompt's form is the cause, no reworded prompt is run under g406's marks: that
  would be a new gate with its own seal.
