# g406b-L (DRAFT, not sealed): can GPT-6 Luna spot made-up claims about the user the way the blind judges do?

"Making things up about you" thread. Drafted 2026-09-27 03:51 UTC (date -u), after Ben's 03:47 UTC ruling that Luna
may write training text, inputs and labels (goals page :110-116). DEV data only. Nothing is trained. No Luna call has
been made.

## Why a new gate
- g406b (sealed 21d2ef2fd, artifacts/claude-g406-2-20260926/PASSMARKS.md) decides whether mu-406 picks its training
  replies with GLM's marks.
- It never finished. The Mac job's shell killed its command at 80 minutes (02:06 UTC), and Ben's opencode Go plan has
  been at its usage limit since about 00:57 UTC (run/RUN-NOTE.md). No g406-2 row will be used.
- g406 ADDENDUM-3's rule: a change to how the labeller is called makes a new gate, not a resume. So the labeller change
  (GLM to Luna) is gate g406b-L. g406-2 stays sealed and unrun. If it ever runs, it is report-only.
- Only g406b's two-session mode is repeated, because that is the form mu-406 would use. g406-2's one-session mode
  (mu-402/403 packets) is not repeated.

## Setup (g406b's, with one change)
- Change: the caller. scripts/claude_g406l_luna.py (new file) imports claude_g406_2_glm unchanged and replaces only its
  module-level `call_low` with the Director's Luna text-call helper. It then runs claude_g406_2_glm.main().
  - The helper does not exist yet. Its file, model id and settings go in SEAL.sha256.txt before the first call.
- Unchanged:
  - the prompt: `--mode two`, mu-405's two-session rubric, word for word;
  - the parser: G.parse;
  - the packets: mu-405b's 240, arms N, W, U and H mixed;
  - the attempts: at most 3 per packet;
  - the truth: mu-405b's two blind judges, recount matched;
  - the base either-rate of 0.14 (168 of 1,200 replies; 131 flagged by both);
  - the count: scripts/claude_g406_count.py on the `--best-to` file;
  - the arm report.

## Pilot gate (fixed now, before any Luna answer exists)
- The first 10 packets in file order, with at most 3 attempts each.
- Pass: at least 9 of 10 parse, and the kept raw error fields contain no "usage limit" or "rate limit".
- Agreement with the judges is not computed on the pilot.
- The pilot's rows stay in the output file, and the full run resumes from them. Fail: no full run; I report to the
  Thread manager and do not reword the prompt.

## Marks (g406b's, unchanged; "GLM" reads "Luna")
- V: usable answers on at least 228 of 240 packets. Otherwise INCONCLUSIVE.
- G1: of the replies both judges flagged, Luna flags at least 70%.
- G2: among replies Luna calls clean, the either-rate is at most 0.07.
- G3: Luna calls at least 50% of replies clean.
- PASS = V, G1, G2 and G3.
- Proved wrong: among replies Luna flags, the either-rate is at or below 0.14.

## What each result means for mu-406
- PASS: mu-406 picks its training replies with Luna's two-session marks in this prompt form.
- FAIL or INCONCLUSIVE: no Luna marks for mu-406. It moves to its named fallback (PLAN-draft-2.md). The prompt is not
  reworded to chase a pass.
- This gate alone decides mu-406's labeller. A later g406b result on GLM would be report-only.

## Report only
- Per arm, the same as g406b: Luna flags, the judges' either and both counts, and Luna's catches of replies both judges
  flagged.
- Hard cases, call seconds, error prefixes and the parsed share.

## Predictions (before any call)
- P406L.1: PASS, 35%. That is g406b's 30%, raised a little because Luna's size and effort are not known to be lower
  than GLM Flash at low effort. It is a guess.

## Where and cost
- The job runs where the Director's helper runs, with no claude- prefix. The long step runs in the background with
  polls under 80 minutes.
- Cost: about 240 Luna calls, at most 720, under Ben's Codex plan as ruled at 03:47. No pool money is used.

## Update 03:58 UTC (date -u): helper and wrapper
- Helper: scripts/claude_luna_codex.py (Director, 24ca7a163), model gpt-6-luna. An empty reply, or a short reply that
  looks like an error, becomes a failed call, so it counts against V and never becomes a label.
  - A reply of `{"flags": [...]}` cannot match its error patterns.
  - This gate is sealed only after the helper's selftest job (000-luna-helper-selftest) passes.
- Wrapper: scripts/claude_g406l_luna.py (offline selftest 5/5; claude_g406_2_glm's selftest 7/7 through it). It adds:
  - `--pilot N`, which runs on the first N packets in load order: claims_j*.jsonl sorted, first appearance of each
    pid, 240 packets in all;
  - `pilot-check`, the gate above.
- Order: `--pilot 10`, then `pilot-check --n 10`. On a pass, the same command without `--pilot` resumes into the same
  output file. Then `--best-to`, claude_g406_count.py, and `--arm-report`.
- Truth for the count, as in g406b: mu-405b's judge/out and keys.

