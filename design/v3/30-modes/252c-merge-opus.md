# 252c: merge of 252b + 258 + 259 (the correction line). Opus design note

Date: 2026-09-22. Builder: Opus merge agent. Brief: briefs/252c-merge.txt.

## What 252c is

- Base: 252b (138k + 252 corrections + 252b value screen). The 228 guard is installed at import, and SrcGuardMixin228 comes first in the daemon.
- Inner-ears order, outermost first:
  1. **Comment258EarsMixin** (258, unchanged): it removes a trailing "that's / which is / this is ..." clause on turns that 252b already treats as a denial or correction.
  2. **Merge252cEarsMixin** (new glue, `scripts/claude_fix252c_merge.py`). It only acts on turns that 258 shortened.
  3. **Boundary259EarsMixin** (259, unchanged): the denied value ends at a clause boundary, inside 252's explicit-denial path and on 259's 154f route (3b).
  4. Correct252EarsMixin (252 / 252b), then the base ears.
- 258 and 259 are imported read-only. No existing file is edited.

## Phase 1: the overlap analysis (every turn shape both pieces act on)

258 runs first. Whenever it shortens a turn, the clause and its boundary are gone before 259 sees the turn. So 259 acts on a 258-shortened turn only if a second boundary is left.

| Turn shape | 258 | 259 | Combined (252c) |
|---|---|---|---|
| Explicit denial + that-clause: "X doesn't work at Y, that's old news." / "X's job isn't Y (that was last year)." | strips the clause | would cut V at the boundary | 258 strips, then 252 removes Y exactly. **258's record.** 259 sees no boundary and passes through. (dev252b 001, 010; corrtail t258-002, 010, 011) |
| Garbled 252b parse + that-clause, "X's R isn't Y; that is no longer true." | strips | would still misparse ("I don't have true ...") | **258's record** (removal of Y). (t258-003) |
| 154f shape + that-clause: "X's R is not Y, that's outdated." | strips, then 154f removes Y ("OK, X's R is not Y. I don't have another R for X.") | 3b: removes Y with 252's "OK, I removed" reply | **258's record** (154f's reply). Both remove exactly Y; only the wording differs. (b252-013, 014; v259-015, 016, 063) |
| 154f shape + clause-end word + that-clause: "X's R is not Y anymore, that's outdated." | strips; 154f then says "I don't have Y anymore as X's R." while Y is stored (**false reply**, c252-022 in 258's run) | 3b drops "anymore" before the boundary and removes Y | **Glue**: 258's cut point counts as 259's boundary on the 154f route. "anymore" is dropped and Y is removed with "OK, I removed Y as X's R." (c252-022) |
| Denial of a near-miss value + that-clause: "X doesn't work at Garrow Hall, that's wrong." with Garrow stored | strips; 252 says "I don't have Garrow Hall as X's employer" | rule-3 wording "I have X's employer as Garrow, not Garrow Hall ..." | **Glue** gives 259's wording on both routes (252 and 154f). No write. (v259-024, 027, 065 = 259's record) |
| Denial + tail that is NOT a that/which/this clause: ", it's wrong now", ", not anymore", " - she quit" | does not act | cuts V at the boundary | **259's record.** (b252-003, 015; t258-035; d258-039) |
| Tail landing in the relation words with a non-258 opener: "X isn't Y's boss (that changed in spring)." | does not act ("that changed" is not an opener) | 3a: cuts the relation and re-reads | **259's record.** (d258-003) |
| Contextual correction or pure denial + that-clause: "No, it's Z, that's outdated." / "That's wrong, that's old news." | strips (or falls back to "No.") | not on its path | **258's record.** No value is ever taken from the clause (b252-035, v259-058, 059). |
| Unparseable to the base ears (two-word lowercase names, first person, "no longer lives in", a bare "Nope." after a two-word-name fact) | may strip | cannot act | whatever 252b does on the shortened turn, so **258's record** when 258 strips. (v259-010, 011, 012, 029, 035, 037, 038) |
| Questions, keep/appositive teaches, chat | does not act | does not act | **252b**, byte-identical. |

The rule is kept on every shape above:
- a denial or correction removes or changes exactly the fact it disputes, or leaves the store unchanged with an honest reply;
- no tail is stored as a value on these shapes;
- no "I don't have V" while (S, R, V) is stored;
- no removal of an undisputed fact.

### Known gaps left open (neither piece acts on them; predicted to stay)
- **", sadly" / ", unfortunately" tails.** These go to 252's two-clause path ("X doesn't work at Y, Z." means Z is the new value), which stores "sadly" as the value (d258-037, v259-008). Both own arms do the same. Fixing it would need a new hand-made list of commentary words. That is not part of this merge, and it goes against the "no more hand wording tables" decision. This breaks M3's "0 junk" bar. **Predicted FAIL.**
- **t258-026 "nope, thats stale"** (a pure denial after a two-word-name fact). Here 252b cannot act even on a bare "Nope." (probe with my own names: "couldn't save"). 258 therefore leaves the store unchanged, so the follow-up still says the old value, which counts as a wrong value. 259 wrote the junk value "stale" over it, so it had "no wrong value". M1's bar "no wrong value where 258 or 259 had none" therefore cannot be met together with "0 junk" on this item. **Predicted FAIL** on that one bar.
- "X's R is not Y anymore." with **no** tail still says "I don't have Y anymore as X's R." This is a 154f bug in 252b. The glue only acts where 258 removed a clause, so it is not fixed.
