# slp-368 blind recount (2026-09-25)

Recounted from `results.json` keys `bench` (80 rows = 40 cases x LOCK/NOLOCK, 0 errors) and `attacks` (seeds 1, 2),
with print-only Python, before reading the `marks` block. Nothing was run except that Python and `shasum`.

## Seal

`shasum -a 256 -c artifacts/claude-slp368-20260925/SEAL.sha256.txt` from the tree root:
`scripts/claude_slp368_lock.py: OK`, `scripts/claude_slp368_test.py: OK`, `artifacts/claude-slp368-20260925/PASSMARKS.md: OK` (exit 0).
The seal does not cover `results.json`, which is expected because it was written after the seal (02:49 seal, 03:48 results).

## Marks

| Mark | My value | Bar | Result |
|---|---|---|---|
| P368.1 LOCK main log bytes unchanged across the sleep | 40/40 (NOLOCK: 38/40) | 40/40 | PASS |
| P368.2 LOCK clean nights kept / user-probe replies identical to NOLOCK | 20/20 kept; 20/20 identical (310 probe replies, none empty) | 20/20 and 20/20 | PASS |
| P368.3 faults caught LOCK vs NOLOCK; NOLOCK main-changing cases rejected with main unchanged under LOCK | caught 13/20 vs 13/20 (same 13 cases); NOLOCK leaks = slp364-10, slp364-19; both LOCK kept=False, main_same=True | LOCK >= NOLOCK, >= 1 leak case, all fixed | PASS |
| P368.4 attack: 15/16 refused, only the outer sleep-derived write passes, main unchanged | s1: 16 tries, 15 LOCKED, only (outer, assert_sleep_derived) = SAVED, main_same True, lock blocked=15. s2: identical | both seeds | PASS |
| P368.5 attack: teach saved, question right | s1 and s2: teach reply "Saved: Quenna's mother is Brisa.", events 126 -> 129; ask reply exactly "Quenna's mother is Brisa." | both seeds | PASS |

Proved-wrong conditions: no LOCK case changed the main log (40/40), and no clean night's replies differ (20/20). Not triggered.
The recorded `marks` block agrees with every number above (all five True, proved_wrong False, detail counts identical).

Report-only numbers: lock counters summed over the 40 LOCK cases: blocked 2, aborted 2, log_changed 0; the lock fired
only on slp364-10 and slp364-19. Uncaught faults (same in both arms): 01, 29, 32 silent-noop; 05, 14, 37 new-names-only;
30 made-up-answer. Attack: slp-361 undid the night on both seeds (undone = 1).

## Checks

1. **Does the lock sit around every write path the attack used? Shown (by code reading plus the data).**
   `Notebook._append` (fable_notebook_contract.py:164) is the only place the contract appends to `events.jsonl`.
   `declare_relation`, `new_entity`, `add_alias`, `approve_rule`, `assert_fact`, `retract`, `propose_merge` all call
   `self._append`, and `promote` goes through `assert_fact`. `loop.nb` is an `IndexedLoopNotebook` (a `ThoughtNotebook` subclass),
   which has no `_append` of its own. Its `__getattr__` hands `_append`, `retract`, `propose_merge` and the rest to
   the inner `IndexedContractNotebook` (a `C.Notebook` subclass that does not override `_append`). `ThoughtNotebook._mark`
   calls `self.nb._append`. The lock replaces `_append` as an instance attribute on both objects. Instance lookup happens
   at call time, so the bench fault hooks and the attack reach the wrapped method even though they captured `nb`
   before the lock was installed. The data agrees: all 15 refusals are `LOCKED` and not NOT_ALLOWED or BAD_REQUEST,
   which means each attack passed the contract's own checks and was stopped at `_append`. The one write that passed,
   outer `assert_fact(source="sleep-derived")`, goes through slp-360's `assert_fact360`: `sleep-derived` is in
   `DERIVED360`, so it goes to `scrap.fact` and never reaches `_append`. The test stores only the status `SAVED`, and main
   bytes and event count did not change (126 -> 126). That it landed in the scrap file is therefore *suggested*, not shown;
   the scrap file was in a temp dir and is gone.
   Not covered by the lock (suggested, from code): `repair_torn_tail` (writes by `os.replace`, not `_append`), any direct
   file write, and a second `Notebook` object on the same folder. PASSMARKS already states the last one as a limit.
   All three would only be caught by the before/after digest. None of these was attacked.

2. **Was any LOCK case rejected only because of the lock while NOLOCK kept it? Shown: no.** `kept` is identical in the two
   arms for all 40 cases. The lock fired (blocked > 0) only on slp364-10 and slp364-19, which NOLOCK also rejected. It
   fired on none of the 20 clean nights (blocked 0, aborted 0, log_changed 0 on each). Rejection reasons are identical
   across arms for 38/40 cases. The 2 that differ are the leak cases: under LOCK their reason is "sleep did not run
   (slp-368 ... refused ... (FACT))", and under NOLOCK it is the 364 gate's content checks.

3. **Are the two NOLOCK main-notebook leaks the cases the lock fixed? Shown: yes.** NOLOCK main_same=False on exactly
   slp364-10 and slp364-19. Recomputing the slp-364 id shuffle from the case table maps them to `sleep_rewrites_taught`
   (seed 8) and `sleep_writes_guess` (seed 12). These are the only two faults whose after-sleep hook calls `loop.nb.assert_fact(..., "listening", "taught", ...)`.
   Under LOCK each shows blocked=1, aborted=True, main_same=True, kept=False. User probes differ between arms only on
   these two cases. For example, in slp364-10 "Who is Krimo's mother?" gets LOCK "Nako" and NOLOCK "Nemo" (the rewritten value).

4. **Marks easier than their wording.** None found that changes a verdict. Notes:
   - P368.1: 38/40 cases leave main unchanged even without the lock, so only 2 cases discriminate. The measurement
     spans the whole `force_sleep` (gate, undo, `_save`), which is stricter than "the sleep" alone. slp-361 never copies the main
     notebook back (it skips the notebook folder), so the unchanged bytes come from the lock and not from the undo. *Shown* from code and from the
     NOLOCK leaks persisting.
   - P368.2: "identical to NOLOCK" compares against the other arm, not against correct answers. Because the lock never fired
     on a clean night, the two arms ran the same code there, so this is close to automatic. The scorer checks `error`
     only on the LOCK row, but the NOLOCK arm had 0 errors too.
   - P368.3: "at least as many" is met by equality (the same 13 cases).
   - P368.4: "which slp-360 sends to the scrap layer" is not checked directly; see check 1 (*suggested*).
   - P368.5: the scorer tests `"Brisa" in ask_reply` (a substring), which is weaker than "answered right". The actual reply is exactly
     "Quenna's mother is Brisa." on both seeds, so the verdict stands. The teach sentence is fixed and is not about the attacked fact.
   - *Suggested, untested:* in slp364-19 (a fault case, outside P368.2) the LOCK arm answers "Who is Voba's boss of spouse?"
     with "Voba's spouse is Goli.", which answers a different question. NOLOCK says "I don't know Voba's boss of spouse."
     This looks like awake-side handling of a half-known chain, not the lock. It is worth a look, but it is not a mark.
   - *Suggested, report-only:* slp-361's memory undo `setattr`s clones of plain loop attributes. After an undone night,
     `loop.lock368` becomes a stale copy, while the wrappers keep using the original dict in their closure. The lock still
     works and the test reads the returned dict, so the results are unaffected. Counters read through `loop.lock368`
     after an undo would be wrong.
