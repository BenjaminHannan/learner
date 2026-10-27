# ct20-v1.2 launch log

- 2026-09-21T00:04:19Z — Condition 16: Ben replied "go" in chat, in his own words, after being told conditions 1–15 were met (re-audit FREEZE-READY: YES; manifest FREEZE-MANIFEST-v1.2.md sha256 bc48f0668e9bf953df71821a14ef66a64ed559409ab43ed8fb07d8b787707f4f). Recorded by Fable (coordinator).
- Launch deferred until the M1 new-names training wave (started 2026-09-21T00:03Z) and its scoring finish, so the driver's timing preflight runs on a quiet Mac.
- 2026-09-21T00:22:26Z LAUNCH (single registered launch). Mac state: no Python jobs; one system process (fileproviderd) at ~100% of one core, disclosed. Command as in manifest.
- 2026-09-21T00:23:38Z RUN COMPLETE exit 0, 62.3 s wall (preflight 16.7 s). Tier L: accounting valid, 72 run / 0 reused, verdict calibration-invalid/startup-or-implementation. Tier H (required by tier L): accounting valid, 72 run / 0 reused, verdict too-hard. FINAL: too-hard. Verdict sealed; binding.
- 2026-09-21T00:24:45Z VERDICT SEALED: wave1/VERDICT-SEAL-v1.2.sha256.txt (hash list over every v1.2 output file). v1.1 quarantine may now be opened for the single reproducibility comparison only.
- 2026-09-21T00:28:03Z v1.1/v1.2 tier-L comparison done: 72/72 bit-identical (wave1/V11-V12-COMPARISON.md sha 86f045af…). Quarantine closed again; no further reads.
