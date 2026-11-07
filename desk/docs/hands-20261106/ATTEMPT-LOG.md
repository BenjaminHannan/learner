# Attempt log: proposed shared format

Status: proposal for HANDS-ACT and NIGHT-LEARN; not yet agreed or wired up.
Keep this local. Write one complete JSON object per line after each attempted task.
Use `schema: "hands-attempt/v1"` and a unique `attemptId`. Store:

- `requestedAt`, `finishedAt`: ISO-8601 timestamps; `request`: Ben's actual request.
- `steps`: ordered records with `at`, `action` and a reference to the observation used. These describe what was actually done, not the intended plan.
- `outcome`: `result` is `pass`, `fail`, or `unknown`; `evidence` is a local reference to the check and its result. A model's guess is not a verified outcome.
- `corrections`: optional entries with `action`, `observation`, `source` and evidence. Only independently checked or Ben-provided corrections can become weighted training labels. Keep inferred suggestions separate.

The night reader must treat missing evidence or an interrupted attempt as `unknown`, not success or failure. A Glim explanation may state `shouldHaveDone`, `actuallyDid`, `whatWentWrong`, `facts`, `guesses`, and `confidence`, but an explanation alone cannot prove a corrected action. Observation references need a shared, time-aligned image/action contract before they can be training examples. HANDS-ACT must confirm the schema before either side relies on it.
