# Sealing procedure for the uncle's questions

Goal: the questions are a blind test. Nothing is trained on, tuned on, or looked at during development. Ben is the only person who handles the raw text; no Claude-written text enters the set.

Status of every claim below: SUGGESTED (procedure, not yet run). Nothing has been collected.

## Steps (Ben does 1-3, on his own machine)
1. **Receive.** Save the uncle's reply exactly as sent to one file, `uncle_raw.txt`. Do not edit, fix spelling, reorder, or paste it into any AI chat (that would leak it to a model provider and let Claude see it).
2. **Seal.** Run `python3 scripts/claude_dir_uncle_seal.py uncle_raw.txt`. It:
   - splits the file into one item per non-empty line (numbered `Q001`...),
   - saves the text to a blind folder outside the repo (`~/premonition-blind/uncle-YYYYMMDD/`, files set read-only),
   - writes `MANIFEST.json` with only: item count, one SHA-256 hash per item, one hash of the whole file, and the UTC time from the system clock,
   - refuses to write anything into the git repo except that manifest (path is printed).
3. **Commit the manifest only** (`handoff/uncle-questions/manifest-<date>.json`). The hashes prove the question set was fixed before any model saw it. The text itself never goes in git, in data/, in artifacts/, or in any prompt.
4. **Privacy pass (Ben, before sealing).** Skim for real customer names, numbers, or secrets and replace them by hand in `uncle_raw.txt`. Do this once, before sealing; after the seal, no edits (if a fix is needed, seal a new numbered version and keep both manifests).
5. **Verify later.** `python3 scripts/claude_dir_uncle_seal.py --verify <blind-folder> <manifest>` recomputes every hash and compares them to the committed manifest. Run it before scoring and again after.

## Rules that keep it blind
- Never trained on, never used for tuning, never used to pick a checkpoint, prompt, or setting. Same rule as the other blind panels (rules.md: "Blind panels are never trained on, tuned on, read or quoted").
- Not readable by any development thread. Development threads see the manifest and the count, nothing else. Only the scoring run (below) opens the text, once per model, with all models fed in the same session.
- One look-then-freeze: the number of times the questions are run through the joined model is decided in advance (see 03), and every run is logged.
- The set is used up as a test for one build. If the questions are ever used to change the model, that set is retired and a new one is needed for the next claim.
- Do not add more questions to a sealed set. New questions make a new set with a new manifest.
- If a leak happens (text pasted into a chat, committed, or trained on), write it in `LEAK.md` in this folder with the time, and retire the set.
