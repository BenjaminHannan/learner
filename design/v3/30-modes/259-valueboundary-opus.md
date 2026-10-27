# 259 value boundary (Opus build): design note

**Problem.** 252's explicit-denial path took the whole rest of the sentence as the denied value.
"Arlo doesn't work at Brimwell, that's outdated" became the value "Brimwell, that's outdated". That never
matched the stored "Brimwell", so the model replied "I don't have Brimwell, that's outdated as Arlo's employer"
while Brimwell was still stored. That is a false statement.

**Change.** One mixin, scripts/claude_fix259_boundary.py, loaded in scripts/claude_loop259_agent.py on top of 252b.
- The denied value ends at the first clause boundary: ", " " - " " — " "; " " (".
- If the part before the boundary equals a stored value (case-insensitive, with 252's own clause-end words such as
  "anymore" dropped), the model removes it with 252's own remove action and reply.
- Otherwise the "I don't have ..." reply names only that first part. If that part is a stored value with extra
  words after it, the reply is "I have S's R as V, not V W" instead.
- The same rule covers two other places where the tail leaked into a false reply: the relation words
  ("isn't Rune's boss (that was last year)") and 154f's "X's R is not V, tail".

**Result.** Registered FAIL (exp 259 RESULTS.md). Dev sets are clean (0 false replies, every prediction met).
Suites, sleep, restarts and speed are unchanged. The blind panel fails because most of its denials cannot be read
by the base ears at all (two-word names, new shapes). M3 failed on a scorer mismatch: the fix drops "anymore"
but the sealed scorer does not.

**Lesson / next.** The value boundary is necessary but small. The panel's misses sit upstream, in the ears.
The learned ear (235/256/257 line) should be tested on these shapes before any more rule patches here.
