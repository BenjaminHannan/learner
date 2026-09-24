# own-M1v: sample-first decoding on the own-M1n mouth. Pass marks fixed 2026-09-24 03:40 UTC, before the run

ONE change vs own-M1n (registered FAIL on variety only: 59 distinct replies per 1,000, top reply 129): the mouth tries up to
4 sampled replies first (temperature 0.8, top-p 0.95), keeps the first that passes the sealed slot_check, and uses the
greedy reply last (scripts/claude_own_m1v_speak.py). Same weights (merged sha256 de12daf488e462814caa6c9de23603aae22326b26060525b2b534f08c4b1564a),
same sealed gate and prompt, same dev set (artifacts/claude-own-m0b-20260923/dev.jsonl = own-M0 dev, 1,000 rows), seed 1. Runs on BensPC.

Grammar is graded on the text a user would see: the winning raw reply filled by the mouth layer's printer
(scripts/claude_own_mouth_layer.py fill_natural). The printer uses plain relation nouns from the 241b say-forms table
("favorite food", not "favorite_food"). This is a printer fix, not a model change. 175/1000 dev rows have such relations,
and own-M1/M1n's fill printed the raw names.

| Mark | Bar |
|---|---|
| Pm1v.1 spoke (a reply passed the gate within 5 tries) | >= 990/1000 |
| Pm1v.2 fresh slot_check recount failures on winning raws | 0 |
| Pm1v.3 variety | distinct slotted replies >= 300/1000; the single most common reply <= 50/1000 (5%) |
| Pm1v.4 grammar | kit = 300 random spoken replies + 40 planted-error canaries (scripts/claude_own_m1v_grade_kit.py, seed 331). Two blind Opus graders, each must catch >= 36/40 canaries (else that grader is replaced once; if the replacement also misses, the mark is FAIL). A real reply counts as an error if both graders flag it; if exactly one flags it, a third blind grader decides. Errors <= 3/300 (>= 99%). |
| Pm1v.5 crashes | 0 |
Reported, no bar: try histogram (how often greedy was needed), replies with a literal record string outside a slot (the layer's
leak gate would send these to fallback), median / p90 ms on the 5070 Ti.
Proved wrong if: distinct < 150 (sampling does not fix the collapse), or grammar errors > 9/300 (sampling breaks grammar).
One change only; a FAIL gets exactly one diagnosis-driven follow-up.
