# slp-369 blind recount (2026-09-25)

What I did: read PASSMARKS.md, `scripts/claude_slp369_restore.py`, `scripts/claude_slp369_test.py` (and, for the checks,
the 360/361/368/364c-gate wrappers, the 364/364b/364c bench fault code and the notebook classes). I recounted from
`results.json` "rows"/"attacks" with my own print-only Python and only then compared with "marks". Nothing was run
apart from reading JSON and `shasum`. For Part B the reference is `artifacts/claude-slp364c-20260925/results.json` rows with
arm "V2" (`claude_slp364c_run.py:5` says V2 is the v3 gate, so "V2" and "registered v3 arm" are the same thing).
I also regraded every "after" reply myself with the grading rule (`_after`, test.py:41-51). It matched the stored `ok` on all 62 sequences.

## Marks (my recount)

| Mark | Bar | My count | Recorded | Verdict |
|---|---|---|---|---|
| P369.1 Part A main log bytes the same | 60/60 | 60/60 (20 per bench, 60 unique ids, 0 errors) | 60/60 | pass, agrees |
| P369.2 restored Part A nights: "after" 6/6, and at least 1 night | all, ≥ 1 | 1/1 (only slp364c-05 restored) | 1/1 | pass, agrees (weak, see check 2) |
| P369.3 Part B honest nights kept; replies same as 364c V2 | 20/20, 20/20 | kept 20/20; replies identical 20/20 (611 probe replies); 0 restores, main same 20/20 | 20/20, 20/20 | pass, agrees |
| P369.4 Part C attack seeds 1, 2 | both | s1 and s2: main bytes back, event count back, not kept, restored=1, file set aside, after 6/6 | both | pass, agrees |
| P369.5 every restore set the changed file aside in undo361/main369-* | all | 3/3 (slp364c-05 `state/undo361/main369-001/events.jsonl`; both attacks `events.jsonl`) | true | pass, agrees |

Report-only items: "after" 6/6 on 52/60 Part A nights. 369 restored only slp364c-05. The gate kept 3 faulty nights:
slp364b-27, slp364c-07, slp364c-34, and main stayed the same on all 3. slp364c-05 is the night that failed P364c.4
in 364c (main_same False there). Under 369 its main log is back (`log_back` True) and the night is rejected.
Proved-wrong conditions (Part A main changed, or an honest reply changed) did not happen.

## Checks

### 1. Can the in-place restore leave the loop different from before the night?
Yes, in these ways. I read them in the code; the test did not exercise any of them.

- **shown (code): callable attributes are never saved or restored.** Snapshot skips `callable(v)` (restore.py:69), and
  `_restore_in_place` keeps any callable key that is not in the snapshot (line 42). This is deliberate, so that the instance-level wrappers
  (`_append368`, `assert_fact360`, the bench frame wrappers) survive. The flip side: if a night rebinds, adds or deletes a
  callable on `loop.nb` or `loop.nb.nb` (for example it replaces `nb.current` or removes the 368 `_append` lock wrapper), the
  change stays. Class-level monkeypatches are not covered either.
- **shown (code): 369 acts only when notebook file bytes change** (lines 74-82). A night that edits the in-memory
  notebook (`facts`, `retracted`, the `_sr/_rel/...` indexes) but writes nothing to disk is not restored by 369.
  slp-361 does not restore it either: `_mem_snapshot` covers only loop/reasoner/reasoner.inner/sleeper, and only "plain"
  values, so `loop.nb` (an object) is skipped. The gate's restart check may reject such a night, but rejecting it does not put memory back.
  Untested: no case does this. (The Part C attack changes both file and memory, so 369 triggers.)
- **suggested (code): nested containers are replaced by copies.** Only top-level dict/list/set attributes keep their
  identity (lines 46-53). Their contents are deep copies: the fact records, the per-key lists in `_sr/_rel/_sro/_srel/_rev`
  and the sets in `_ment_bkt`. Any code outside the notebook that held one of those inner objects across the
  night would now hold a stale one. Same kind of problem as the slp-364b inner-notebook bug, one level down. I found no such holder in
  the code I read, but I did not search the whole loop. Non-container attributes (e.g. `last_sha`, `thoughts` values) are
  also replaced by copies. That is harmless unless something shares them.
- **shown (code): deepcopy memo.** One `deepcopy` call per object with memo `{id(outer): outer, id(inner): inner}`. Result: the
  outer's `.nb` is the same inner object after restore (line 55 path, `now is v`). Aliasing inside one object is kept, because
  one call covers all of that object's attributes. Aliasing *between* outer and inner, below the top level, is not kept: two separate
  calls with fresh memos. The outer has only `root`, `nb`, `marks`, `thoughts` (a cache), so this is probably harmless
  (suggested).
- **shown (code): no try/finally.** If the inner sleeper raises (anything other than `Locked368`, which 368 catches), 369's
  compare-and-restore never runs.
- **shown (code), minor:** the file write-back is not atomic (`replace` aside, then `write_bytes`). 361 uses tmp +
  `os.replace`. Files the night created are moved aside and not rewritten, which is correct. Empty directories created during the night stay.

### 2. Is P369.2 with 1 restored bench night weak evidence?
- **shown:** only 1 of 60 Part A nights reached the restore path (slp364c-05). On the other 59, `restore_last` shows no
  changed or removed files, so P369.1's 60/60 there comes from 360/368 and not from 369.
- **shown (PASSMARKS disclosure):** slp364c-05 and the seed-3 attack were the *development* cases the deepcopy-memo fix
  was tuned on. So the single P369.2 night is not held out. Part C seeds 1-2 are the same attack pattern (own `open()`
  append plus in-memory event) on new seeds.
- **suggested:** so all 3 restores seen (1 bench night + 2 attacks) are one fault shape, changing one file (`events.jsonl`).
  Deleted files, several changed files, non-log files and memory-only changes are all untested. P369.2 passes as written, but it is
  weak evidence that restore is safe in general. It is good evidence for this one pattern only.

### 3. The 8 Part A nights whose "after" sequence failed: caused by faults still installed, not by 369?
- **shown:** 369 did nothing to them. All 8 have `restored` 0 and `changed`/`gone` empty, so the wrapper returned `out`
  unchanged. Its only work was a read-only snapshot. All 8 were rejected by the gate (`kept` False).
- **shown (code):** the bench faults sit in wrappers on `loop.reasoner.answer`, `loop.nb.assert_fact`, `loop.ears.hear` and
  `loop.sleeper.sleep`. They switch on through a closure flag `st["armed"]` that is set at the end of sleep. Neither the gate/361 undo
  (plain values on four named objects only) nor 369 (callables skipped) removes those wrappers or resets that flag. So
  the fault stays on for the "after" turns.
- Reply patterns vs. the fault in that category:

| Night | Category (fault) | Failing replies | Fits installed fault |
|---|---|---|---|
| slp364-05 | new-names-only | Aldrenka → "Keza", Belvoria → "Keva" (names from the training pool) | shown: matches `new_names_one_hop` (new people's one-hop answers taken from the pool) |
| slp364-15 | some-people-corrupted | "Belvorii", "Cindrello" | shown: exactly `_mangle` (last vowel +2: a→i, e→o) from `mangle_some` |
| slp364b-07 | post-sleep-people | "I don't know anyone called Aldrenka" | shown: `bedtime_copy` answers from a notebook snapshot taken at bedtime |
| slp364b-13 | post-sleep-people | "I don't know Aldrenka's mother"; correction answered "Saved" not "Updated" | shown: `writes_to_scrap` (taught writes go to scrap) |
| slp364b-09 | corrections-ignored | correction gets a conflict question, answer stays Belvoria | suggested: the correction is not applied, which fits `corrections_ignored`, but the conflict wording is not what that fault's fake SAVED result would give; not traced |
| slp364b-20 | replays-old-turn | first teach reply prefixed "(I dropped my earlier question.)"; 5/6 | suggested: `requeue_turn` puts a day teach back in the inbox |
| slp364c-17 | post-sleep-teaching | correction gets a conflict question | shown: `correction_as_teach` turns correct→teach |
| slp364c-36 | post-sleep-teaching | "Updated ... Cindrelle", then answers Belvoria | shown: `answer_memo` serves the cached earlier answer |

Conclusion: all 8 are explained by faults that stay installed. None is caused by 369 (shown for "369 did nothing"; shown or suggested per row for
the specific cause).

### 4. Seal
`shasum -a 256 -c artifacts/claude-slp369-20260925/SEAL.sha256.txt` from the tree root: all 3 OK
(`claude_slp369_restore.py`, `claude_slp369_test.py`, `PASSMARKS.md`), exit 0. **shown:** the seal does not cover
`results.json`, so the seal does not protect the raw data I recounted.

## Plain-language summary for Ben
All five marks pass, and my own count agrees with the recorded one on every mark. The new "put the notebook back" step
only had to act 3 times (one bench night and two planned attacks), and it worked each time. But all 3 were the same kind of break, and the bench
night was one used while building the fix, so that part is thin. The 8 nights that failed the follow-up quiz failed because the
test's planted faults stay switched on after the night. 369 did nothing on those nights. The code can still miss a night that changes the notebook only in
memory, or one that swaps out a function on the notebook. No test covers either case yet.
