# y1t data gate: do the GLM practice questions do what their labels say? (Answering-from-memory thread, marks fixed 18:21 UTC 2026-09-26, before the practice chats exist)

Why: the Thread manager's test-hygiene rule 2 (design/v3/30-modes/test-hygiene-2026-09-26.md, 3242b2019): a label
taken from what a writer was asked to write is not a label of what the text does (rt-02h: 77 of 144 "asks" did not
ask). y1t's items (and y1v's, which reuse them) take two labels from the seed, not from the text: that an "ask" turn
asks for one stored fact, and that a never-told twin no longer says the answer once the turns carrying that fact are
removed. The value is already checked from the text (build_items counts a fact only if its value is typed in that
kept user turn). This gate runs on the Mac job's items before any training; y1t's sealed files do not change.

## Checks (scripts/claude_y1t_gate.py)
- G1, code, every never-told twin: the gold value appears (336's vmatch) in no turn the twin keeps. PASS if at most
  5% of twins still carry it.
- G2 and G3, blind sample: 60 answerable items drawn from items_train.jsonl (seed 4034). Two blind judges (fresh
  agents, each reads only its own folder, never trained on, tuned on or quoted), a fresh third on any item where they
  differ. G2: the last message asks for the named fact. G3: the earlier messages state that value as the current
  answer. PASS if G2 >= 54 of 60 and G3 >= 54 of 60.

## Decision (fixed now)
- All three PASS: the thread asks the Director to release handoff/held/rent-0y1t.md.
- Any FAIL: y1t is not run on these items. The fix labels from the text itself (code or GLM, never the judges'
  labels) and gets a new seal; bank E stays unused.

The judges' labels decide only whether the data is used; nothing trained on is written or judged by Claude (Ben 16:39).

## Plain summary for Ben
GLM was asked to write questions like "what's my sister's dog called?". Before training on them, we check that a
sample of 60 really asks that, and that the chat really gave the answer. Code also checks that the "never told"
copies of each chat don't still contain the answer somewhere. If more than a few are off, we don't train on them.
