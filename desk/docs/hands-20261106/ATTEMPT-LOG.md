# Attempt log: hands-attempt/v1

The local writer uses `~/learner-ops/hands-attempts/attempts.jsonl`. Each
complete line is one `hands-attempt/v1` object with a unique `attemptId`,
`requestedAt`, `finishedAt`, Ben's `request`, ordered `steps`, `preparations`,
`corrections`, and `outcome`. The writer keeps a private pending file while an
attempt runs; interrupted attempts recover as `unknown`. Readers ignore a final
incomplete JSON line and refuse duplicate IDs.

Each step records `at`, Glim's `intent`, an `observation` reference, `action`,
`actor` and `status`; it may have an `after` reference and a verification.
These records say what was attempted, not what was definitely achieved.
`outcome.result` is `pass`, `fail`, or `unknown`, with `evidence`. Missing
evidence or unfinished work is `unknown`. A Glim guess alone is not proof.

A correction has an `action`, an `observation` reference, `source` (`ben` or
`independently_verified`) and `evidence`. Night learning treats these as
candidates, not labels: it must independently resolve and check the observation
and evidence before applying weight 3. Model suggestions are never correction
labels merely because Glim wrote them. For a failed attempt Glim can describe
`shouldHaveDone`, `actuallyDid`, `whatWentWrong`, `facts`, `guesses`, and
`confidence`; the explanation does not itself prove a corrected action.

This is the shared reader contract; a deployed end-to-end attempt, evidence
resolver and correction writer still need their own real-task verification.

For an eligible correction, `observation` and `evidence` are file names inside
`~/learner-ops/hands-attempts/`. The evidence JSON uses
`schema: "hands-correction-evidence/v1"`, the same `attemptId` and `source`,
`verified: true`, SHA-256 fields `observationSha256` and `actionSha256`, an
`intent`, `timeMs`, and the display `bounds`, `scaleX`, and `scaleY`. The
image and canonical action hashes must match. Only a trusted Ben or independent
verifier may issue such a receipt. The existing attempt writer does not yet
produce these receipts, so none should be invented by the night reader.
