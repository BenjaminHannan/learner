# 0.2d gates, ADDENDUM-43: the loop net is told the puzzle kind; disclosed as stand-in E1. Written Sun Sep 27 12:11:07 UTC 2026, before any run

Month-end. Additive only. No 0.2d code is sealed and nothing has run.

- The Thread manager (12:1x UTC, from Sol's artifacts/codex-autoroute-20260927/INPUT-AUDIT.md) asked whether the H-A
  slot is given its puzzle kind at chat time. It is. Checked in the code:
  - claude_rsn358b2_bridge.item_of builds every chat grid as E.Item("grids", ...), so env is always "grids".
  - LoopSolver.solve passes it through self.R.tensors, which sets env = ENVS.index(items[0].env)
    (claude_rsn358a_run.py:172), and embed adds self.env(env) to every token (claude_rsn358a_run.py:97).
  - ENVS = ["sums", "grids", "numbers"] (claude_rsn358a_envs.py:40). The 358 nets train on more than one kind (358i3:
    sums and grids), so the label carries information the net did not work out itself.
- 0.2d calls the net only after read_latin (P1) finds a grid, so the label is set by hand-written code. Ben at 11:34
  UTC ruled out caller-given skill labels ("It should for each request be able to automatically decide what").
- Decision: disclosed now as stand-in E1 in scripts/claude_e2e02d.py's header, with its learned part owed (the net
  deciding the kind from the input itself). No code path changes; the wiring selftest still passes 18/18.
- Consequence for the seal: a row A result from this slot is "with the puzzle kind given". Whether the H-A net can
  run without env (a kind-blind arm) is for Sleep research, which the Thread manager has asked the same question.
