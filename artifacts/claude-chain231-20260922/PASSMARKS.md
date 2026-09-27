# Exp 231 -- PASSMARKS (registered before any registered run and before the panel is opened)

Build: loop231 = loop221 + Chain231Mixin outermost on the ears (scripts/claude_loop231_agent.py).
Chains in table-question subjects are resolved hop by hop through taught, active notebook facts.
The stage is read-only.
Design: design/v3/30-modes/231-chain-opus.md.
Scorer: scripts/claude_chain231_run.py. It is the one scorer for all three arms, and its rules are
in the module docstring. Only load_items() may be adapted to the panel's field names after opening,
and any such change is listed as a deviation.
Verdict = PASS only if every mark M1-M5 passes. Any single failure = FAIL (named mark).

## Answerable subset (added before sealing, after the coordinator's note about two-word names)
On 138i/221, a verb-form teach with a two-word subject ("Anselm Rook lives in Tillmarsh.") does
not save. Experiment 232 is fixing that separately.
- An item is ANSWERABLE iff, on the 221 arm, every setup turn landed, as defined in the scorer
  docstring. Otherwise it is BLOCKED.
- Right-answer bars use the answerable subset.
- Wrong values and question writes are counted on ALL items.
- Blocked items are listed separately with their replies.

## M1 -- blind chain panel (artifacts/claude-chainpanel231-20260922/, run ONCE per arm)
Its SEAL.sha256.txt must verify (`shasum -a 256 -c`) before the panel file is read, else M1 is VOID.
Arms: 138i, 221, 231, run one after another, each with a fresh notebook per item.
- M1a: **0** WRONG for 231 over ALL items (wrong value, a wrong yes/no, or a value asserted on an
  abstain item).
- M1b: **0** question turns that change the notebook fact hash in the 231 arm, over ALL items.
- M1c: answerable subset: 231 RIGHT **>= 221 RIGHT + 20**.
- M1d: answerable subset, answer + yes/no items: 231 RIGHT **>= 85 %**.
- M1e: **0** items (ALL items) RIGHT on 221 but not RIGHT on 231.

## M2 -- dev cases (artifacts/claude-chain231-20260922/dev231.jsonl, 55 items, written by me)
Run once more on the sealed code, arms 221 and 231.
- M2a: answerable items: 231 RIGHT **>= 90 %**.
- M2b: answerable abstain-kind items (broken, ambiguous, forgotten, unknown-root and self chains):
  231 RIGHT (honest abstain) **100 %**.
- M2c: 0 WRONG and 0 question writes for 231.

## M3 -- frozen suites vs 221's behaviour
Tool: scripts/fable_suitediff218.py --base-dir artifacts/claude-chain231-20260922/base221.
- base221/ holds byte-identical copies of 221's sealed suitediff rows. The rt136/rt143 files are
  renamed so that the tool's filename search finds them; the hashes are in SEAL.
- Suites: rt136, rt143, sessions152, bench.
- M3a: GATE clean: **0** new WRONG, **0** new WRONG-WRITE, **0** new junk write, **0** lost OK.
- M3b: **0** moved cases absent from predicted_moves231.json (sealed).
- Predicted direction: the 221 not-understood or empty-key reply becomes a chain answer or a
  targeted abstain.
- Pilot (pre-seal) saw exactly 4 moves, all rt143 reply-only OK->OK targeted abstains: A1, F6, K8
  and U1. Predicted: the same 4.
- Known flake rule (OPUS-RULES): an unpredicted abstain-direction flip is reported as it is, counts
  against the mark, and is re-run alone 5 times.

## M4 -- sleep smoke (scripts/fable_sleepsmoke206.py on loop231)
Same marks as 221: sleeps 1, installed (episodes 20), probes 5/5, wrong 0, broken = abstain,
taught 50/50, overwrote 0, wall < 300 s.

## M5 -- latency
Median over panel question turns of (231 ms - 221 ms) **<= +10 ms**. The p90 is reported.

## Declared deviations (known now)
1. The chain-only input tidy strips a leading filler and a trailing again/now/then.
2. The table's yes/no rows are read, but only for chain subjects.
3. Table v1 gaps are inherited: the "language(s)" template needs the "s", and wife/husband are not
   aliases of spouse.
4. Scorer "no other value" rule: the intermediate chain entities the reply names ("Kim's boss is
   Lee, ...") are allowed when they lie on a stored path from a question entity to the gold value.
   Any other stored value in the reply is WRONG.
5. The base221/ copies are needed because the 218 tool cannot find 221's rt136/rt143 rows under
   their saved names.
