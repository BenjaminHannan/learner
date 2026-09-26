# rv-386 withdrawn, NOT RUN (thought-memory thread; written 2026-09-26 17:20 UTC by date -u)

No rv-386 test grid was ever made or played. The sealed files stay as they are. This note only records the decision.

Why:
1. Ben's 16:04 UTC redirect: threads re-plan toward the learned reasoner. rv-386 asks whether a text note in the 1B's
   prompt ("row 2, column 3 = 4: row 2 already has a 4") helps the 1B propose moves. That is a hand-fed memory for the
   language model, not going back inside the learned reasoner. Going back now lives around the loop reasoner: rv-387
   (done; the go-back never fired), rv-390 (running), and rv-391 (the trigger is being measured).
2. The gate: the plain MiniCPM5-1B got 16% first choices right (GATE-plain-1B.json), below the 50% bar. The only
   candidate proposer, Fix sleep's dl-5 S adapters, was trained on a Claude-written target prefix. Under Ben's "Use
   GLM" rule any result on them would be a finding only. dl-5 is also a registered FAIL on harm (G3: S lost 98 and 61
   of 200; artifacts/claude-dl5-20260926/VERIFY.md). So the gate was not queued.
It could come back only on a proposer trained without Claude-written text that passes the gate, and only if the
learned-reasoner work needs it.
