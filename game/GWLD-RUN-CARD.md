# GW-LD run card (prep only; nothing runs; coordinator ruling Q101)

Marks: `game/GWLD-MARKS-PROPOSAL.md`, accepted and **frozen as written** (Q101). This card answers Q101's conditions; it changes no mark.

## Q101 conditions and their status
1. **The GW-LS sealed read is taken first, under the Q96 confirmation.** Pending: the read-side gate fixes (round 2) are in progress, and
   the read goes only if the re-review is clean.
2. **The GW-LD driver is committed as DRAFT and passes the coordinator code review (the built-in review plus an independent read) before
   anything runs.** Not written yet. When it is, it will carry two hard guards:
   - it refuses to run unless GW-LS's `final.json` (the sealed read) is on record;
   - it refuses any arm-D training step unless an audit-clearance record is passed in (condition 3).
3. **Labeller-bar question, answered in writing.**
   - The B3 re-audit FAIL bars the labeller from on-policy use until a teacher passes a fresh audit. The source is the coordinator's
     statement in Q101. The audit record itself is not in this repo.
   - **GW-LD as frozen is on-policy use.** Arm D trains on labeller labels for views the student itself visited.
   - A measurement-only version (no such training) cannot meet the frozen marks: M1 and M2 both read a student trained on those labels.
     It would be a different design and would need new marks.
   - **Answer: GW-LD waits until the audit bar is cleared on the Track 10 path.** It is not converted to measurement-only, because the
     marks are frozen.
   - Until then, only the guarded draft driver may be written and reviewed. No collection, no training, no sealed read for GW-LD.

## Booking (when all three conditions hold)
- Venue: free cloud container CPU, $0. No spend bid.
- About 10-11 h of wall clock (marks file, "Venue and cost").
- Seeds 200 / 201.
- World days 40-43 (collection) and 50-51 (M1) of run seeds 398 / 399. These are unused by GW-LS (days 4-35) and Z8 (days 0-3).
- Not authorized by Q101: GW-LS2.
