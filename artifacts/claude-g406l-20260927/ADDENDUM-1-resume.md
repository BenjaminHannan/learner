# g406b-L ADDENDUM 1: finish the time-stopped run before any verdict

"Making things up about you" thread. Written 2026-09-27 06:42 UTC (date -u), after reading run/RESULTS.md, which
builder-outbox pushed at 06:32 UTC and which I copied to main. The marks, prompt, model, attempts and count are
unchanged.

## What happened
- The pilot passed: 10 of 10 usable, 0 limit errors (pilot-check exit 0).
- The full run stopped on its own 45-minute cap at 48.9 minutes.
  - 220 of 240 packets had a usable row, and there were 0 failed rows.
  - The other 20 packets were never sent, so their attempt count is 0 of 3.
  - My job file set this cap. It was too short for 240 packets at 1 call at a time. Luna did not fail.
- I recounted the job's count on those 220 packets here (claude_g406_count.py on run/best_b.jsonl with mu-405b's judge
  folder), and it matches exactly. I have seen it:
  - V false (220, needed 228). G1 true: 121 of 122 both-flagged replies caught. G2 true: either-rate 0.0122 among 737
    clean replies. G3 true: 0.67 clean. Not proved wrong. The count script's word is INCONCLUSIVE.
  - Arm report: Luna catches 72 of U's 72 both-flagged replies.
  - All 220 rows carry labeller "luna:gpt-6-luna".
- One job deviation. g406-2's own selftest reads artifacts/claude-mu402-20260926/JUDGE-claims.md, and my job's file
  list left it out. The job agent took that one file from the same main commit so the selftest could run (7/7).
  - The mode-two prompt never reads that file: prompt_for uses G.build_prompt only for mode "one"
    (claude_g406_2_glm.py:65-66).
  - The resume job includes the file.

## Rule (fixed now, before the resume runs)
- The run is not finished, because V counts packets "within 3 attempts" and 20 packets have had none. The registered
  g406b-L verdict comes from the count after the sealed command resumes, unchanged, on a copy of run/luna_b.jsonl.
  - The copy's sha256 is 19889ed299570f1adc3fecb5576246156dc98bdd4759f706e87f46f8e414f910, and the resume works in
    run2/.
  - Only packets without a usable row are sent, each with up to 3 attempts. Nothing about the prompt, the model or the
    helper changes.
  - run/ stays as it is, as the record of the partial count.
- If the resume cannot run, or stops again before every packet has had its attempts, the verdict stays INCONCLUSIVE.
- The partial count above is reported next to the final one, marked as seen before the resume.
- Then the blind recount, then VERIFY.md with "labeller: Luna (gpt-6-luna)".
- Job: handoff/queue/madeup-g406l-resume-mac.md. It has LOAD-LIGHT: yes and 1 worker; the long step runs in the
  background with a 30-minute cap and the stop at 70 minutes.
