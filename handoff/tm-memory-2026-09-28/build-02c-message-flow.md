---
name: build-02c-message-flow
description: How one message actually flows through the 0.2c build (traced in code 2026-09-26 ~13:58 UTC), versus Ben's mental model of reader -> reasoner -> talker
metadata:
  type: project
  modified: 2026-09-26T13:56:13.744Z
---
**Ben's picture (13:53-13:55 UTC 09-26):**
- A 1B reader formats messages for the reasoner.
- The reasoner uses tools (clock, calculator) and is "persistently on".
- The talker turns the reasoner's thoughts into a message.

The build does NOT work this way yet. Told him so, with the flow below.

**Actual 0.2c** (scripts/claude_e2e02c.py:41-112; the last-installed layer runs first):
- think299b and cre333d catch math and creative turns first and send them to the 1B. On math, the 1B writes steps and a calculator does the arithmetic: 5 runs, 3 must agree.
- Every other turn goes to the reader (lis-319, 6 history pairs), which makes a frame and saves confident facts.
- On ASK turns, the reader frame is NOT given to the reasoner. Old rule "ears" parse the question, the hand-written reasoner returns a status record, and a fixed template mouth writes the sentence.
- lis-313 answers from the reader's ASK frame only if the rule path abstains.
- The MiniCPM talker answers only when every layer gives up (claude_chat338_agent.py:143-161). Its prompt holds notebook facts plus the last 12 messages, never reasoner output.
- No clock tool. Nothing runs between messages except sleep in downtime.

**Why:** Ben thought the design was already built. The learned loop reasoner (358 line) is meant to become the middle piece.
**How to apply:** when talking about "putting the loop in the assistant", say it means the talker's own layers, and that the reader->reasoner handoff does not exist yet. See [[reasoner-roadmap-state]], [[brain-emulation-goal]].
