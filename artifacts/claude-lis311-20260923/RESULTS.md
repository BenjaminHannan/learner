# lis-311 RESULTS: PASS (registered run 2026-09-23, builder; re-run lis-311b)

Registered verdict: PASS on all three bars. 10/10 sealed stub scenarios
passed, exit 0; 0 base-chain writes across the 5 blocked-write turns; the
server on 8767 answers GET / with 200 and POST /turn with 200 plus a reply,
and was left running. Seal 5/5 OK after the run; no post-seal change. No
TEST-ONLY panel was opened, tuned on, or quoted (none is used by this task).
All names fictional.

Resume note: a first lis-311 run on 2026-09-23 sealed the 5 files
(SEAL.sha256.txt verified 5/5 OK before and after this run), wrote the
ledger predictions, created real-rows/rows.jsonl empty, and served one
server turn (transcript index 0, 10:02 local) before the Mac slept. This
run re-ran every step from the sealed files without editing them: stub
scenarios, the full 30-turn real-model try-out, and the server check
(transcript index 1). Ledger predictions were not duplicated.

## Marks table (integer counts)

| Mark | Bar | Got |
|---|---|---|
| P311.1 every stub scenario passes | 10/10 PASS, exit 0 | 10/10 PASS, exit 0 |
| P311.2 base-chain writes in the blocked-write test (T7) | 0 writes over 5 turns | 0 writes over 5 turns |
| P311.3 the server on 8767 answers a turn | GET / 200 + POST /turn 200 with a reply | GET / 200 + POST /turn 200 with a reply |

## Every move (registered stub run, StubReader, threshold 0.995)

- T1 two-facts-save-2: PASS. "My sisters are Mira and Tal." saved 2 triples
  (USER,sister,Mira) + (USER,sister,Tal); reply the 292 base mouth's save
  confirmation ("Saved: your sister is Mira. Saved: your sister is Tal.
  (I also have Mira.)"). Matches prediction exactly.
- T2 whose-ask: PASS. "Our dog is Pip." replied exactly "Whose dog is Pip,
  yours or someone else's?"; 0 triples. Matches prediction exactly.
- T3a askback-yes: PASS. Low-conf STATE (0.5 < 0.995) asked back exactly
  "Just to check: is Mira's dog Pip?" (0 triples); "yes" saved exactly 1
  triple with a Saved reply ("Saved: Mira's dog is Pip."). Matches
  prediction exactly.
- T3b askback-no: PASS. Same ask-back, then "no": 0 triples,
  "Okay, I won't save that." Matches prediction exactly.
- T3c askback-dropped: PASS. Same ask-back, then another fact turn: pending
  dropped, new turn saved normally (1 triple, the dog fact never saved).
  Matches prediction exactly.
- T4 negation: PASS. NEGATE turn saved 0; reply is the base's clarify (no
  write). Matches prediction exactly.
- T5 CHECK: PASS. "So Mira's dog is Pip." after a STATE teach: base answered
  "I already have that."; triples unchanged (1); 0 new events. Matches
  prediction exactly.
- T6 question: PASS. "Whose dog is Pip?" (ASK frame) answered from the
  notebook ("Mira's dog is Pip. (worked out backwards)"); 0 new events.
  Matches prediction exactly.
- T7 blocked five: PASS. Each of the 5 turns (SUPPOSE/NEGATE/PLAN/REPORTED/
  CHECK city turns) was first verified to grow notebook events on the raw
  292 base, then grew 0 events / 0 triples under 311. Base-chain writes: 0.
  Matches prediction exactly.
- T8 unparsed: PASS. Unparsed frame saved 0 with the exact sorry-reply.
  Matches prediction exactly.
- P311.3 server: PASS. GET http://127.0.0.1:8767/ answered 200; POST
  /turn {"text":"My sister is Mira."} answered 200 with reply "Saved: your
  sister is Mira." and added [["USER","sister","Mira"]]. Server left
  running; 8765 answered /ready true (untouched); 8766 gave no answer
  (pre-existing state, never touched by this task). Own state dir
  ~/premonition-chat/lis311-state; Ben's existing notebook never touched.

Misses: 0. Deviations on the bars: 0 (every sealed prediction matched
exactly).

## Step 3 real-model try-out (report-only, no bar)

- Weights: ~/premonition-models/lis300-merged/model.safetensors sha256
  112880d610173aef9b39715e0f6db51a16af8dece42dbd7132b83c0be8285324,
  matches the lis-300 recorded value. Device: mps (Mac).
- 30 scripted casual turns (3 conversations x 10) + 4 adaptive "yes" turns
  after ask-backs = 34 rows total in
  artifacts/claude-lis311-20260923/real-rows/rows.jsonl (34 lines).
- ms per turn: median 2826.6, p90 15567.1, max 59429.6 (B-family#2,
  two-facts-in-one-message ask-back).
- Final notebooks per conversation: A-pets [["USER","sister","mira"]];
  B-family [["USER","mother","lena"],["tal","boss","mara"]];
  C-mixed [["USER","friend","zoe"],["USER","uncle","dev"],
  ["zoe","cat","mochi"]].
- Every turn row (turn, reply, saved, frame, confs, ms, adaptive flag) is in
  rows.jsonl; full log in /tmp/lis311_real.log on the Mac (not pushed).
- Report-only observations (no bar; expected since lis-300 is a registered
  FAIL on recall and asks back about half the true facts):
  - 4 ask-backs occurred (A#4 sisters, B#2 brother+cousin, B#7 tal's boss,
    C#9 uncle works in porto); all 4 follow-up "yes" turns resolved
    (3 saved, 1 "I already have that").
  - A-pets#7 ("mira's dog is pip."): mouth replied "That sounds like a
    description, not a name, so I didn't save it..." yet the row records
    saved [["mira","dog","pip"]]. Reply text and write disagree on this
    turn; reported as-is.
  - A-pets#8 ("whose dog is pip?"): answered "I don't know anyone whose dog
    is pip." although (mira,dog,pip) had just been written (lowercase names
    stored as typed). A recall miss; reported as-is.
  - C-mixed#4 correction ("no wait, zoe's cat is fig."): wrote
    (zoe,cat,fig) while (zoe,cat,mochi) from #3 stayed, so zoe briefly held
    2 cats; C-mixed#6 ("is zoe's cat fig?") was not understood. Reported
    as-is; no correction/removal bar exists for this build.
  - Small talk / unclear turns (hey!, hi there, good morning, ok got it,
    thanks/bye, cool talk later, see you soon, imagine/suppose/want turns)
    saved 0 facts, as designed.

## What this means / doesn't mean (plain English)

- The listener plug-in now works on the new 292 base: ordinary facts still
  save, unsure facts get a check-back question first, and the five kinds of
  turns that must never write (suppose, negate, plan, reported, check)
  wrote nothing. High-school version: the notebook guard moved to the new
  notebook without breaking.
- The chat page on port 8767 works with the real model and was left running
  for Ben. His old chat pages were not touched.
- The 30-turn casual try-out is only a report, not a grade: with the real
  model, some lowercase answers confuse it (it once said "I didn't save
  it" while saving, and once forgot a fact it just wrote). That matches the
  known lis-300 recall weakness and sets no bar here.
- What it doesn't mean: this does not prove the model recalls well (it
  doesn't, about half the true facts get asked back), does not test speed
  limits (slowest turn took ~59 s on the loaded Mac), and does not touch
  any graded test panel.
