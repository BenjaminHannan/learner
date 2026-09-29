# Briefs for the four sweep tests (Director, 02:04 UTC 09-29)
Read handoff/director-briefs/thread-helper-common.md and rules.md first (MARKS SELF-CHECK applies). The test definitions, marks and costs are in design/research/lead-sweep-2026-09-29/SYNTHESIS.md section 3 (numbered 1-5); marks are fixed there. Add your own PASSMARKS.md before any code, seal, then queue jobs. New files only. Dev panel only, blind panels untouched. No vast. Ask me by send_message (session_01AfubiZBgctbvNzz8pdHwMb), not Ben.

## S1 "Turn and flip mazes" (test 1)
Rulings: hand-picked D4 prior, mazes/grids only; apply to loop AND plain, both seeds; label results "with a hand-picked prior"; not a kind-blind claim. Compare each arm to its own un-augmented row on main (loop-s{0,1}-pre, plain-s{0,1}-pre in artifacts/claude-fewex-20260927/eq-runs). Use a new plug-in, do not edit claude_fewex_eq_bench.py. Mac CPU (strict fp32), ~3 h per arm-seed; GPU only after the fp32 equivalence smoke passes. Noise bars 7.0 / 8.5 stand (2 x sd 3.33/4.17); the synthesis' +8.0/+10.5 is fine.

## S2 "Watch it think" (test 2)
Zero training. New script + new queue job (do NOT edit sl-1-read-r2). Run on every saved practised-loop and sleep checkpoint that exists; list which are missing and wait on ks-1 for those. Report which of HEAD / FLICKER / CONVERGES / DRIFTS each net is, with the synthesis' marks. Also explain the 8-of-300 cap hits after sleep16384.

## S3 "Numbers: nearest valid answer" (test 3)
Ruling: choosing among code-enumerated valid answers is kind-blind. Same pool/seeds (13, 14) as H2 (artifacts/claude-dir-h2-recount-20260928 has the recounted floors and P_other), two loop + two plain nets, plus the random-valid arm beside it. BensPC GPU, but dir-g-a holds C:\Users\benja\GPU-BUSY.txt: queue behind it; the runner honors the marker. Plain net must be able to fail the plain-net row.

## S5 "Can the talker read the notes" (test 5)
Guard: hash the 100-question dev slice first, prove it is disjoint from earlier dev slices (grep handoff/ and artifacts/ for LongMemEval slices) and from the sealed final set; say in PASSMARKS what the final set is. LFM2.5-1.2B on BensPC after dir-g-a. Under $0.50, no rental.
