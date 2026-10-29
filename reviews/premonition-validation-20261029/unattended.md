# Unattended Premonition improvement session

User authorized continued improvements until returning, about four hours from 2026-10-29 19:56:08 UTC. Stop new work at 2026-10-29 23:56:08 UTC or when the user says they are back. Heartbeat automation `premonition-improvement-session` runs every fifteen minutes until that deadline. Keep Terra on routine implementation/testing/packaging and Sol on harder model/evaluation work.

Use only `/Users/ben-hannan/Desktop/projects/premonition-reliability`, branch `codex/premonition-reliability-20261029`. Original beautiful-model checkout is dirty and preserved. Active model MUST remain LFM3 for chat and sleep; Apex provisioning cancelled. No rented compute, no unrelated jobs killed, no email or third-party messages.

## Current status

- Installed Mac source/app version 1.2.2 uses cached LFM3 GGUF behind loopback gateway8090; sleep remains lfm3_mps against matching HF weights. Production adapter currently absent, so day serves base until a verified accepted export exists. Backups and manifests: `/Users/ben-hannan/learner-ops/premonition-lfm3-backup-20261029-154045`.
- Real LFM3 training/save/reload/export/serving smoke passed. Paired twelve-step replay experiment showed no held-out gain; continuation replay stays off. Four final creative probes valid in665–1032ms; only open ideation/story/poetry uses the private fast pass.
- Full suites passed: sleepmlx221, sleepmode127, desktop437plus1skip, realElectron209. Independent integration review found no blockers. Final upstream updater6tests passed.
- Windows1.2.2 zip is built and verified, SHA c75ee9269a02efe5f71f6b8410933489b1b662f2e111633a9d2db7957f51f34b,122830992bytes. Publish via existing GitSSH+GitLFS distribution and desk/dist/latest.json onmain, after preserving upstream1.2.1f696c99865317789ed2e9aaac61cd397614f9426. Jacob's updater requiresUpdateNow click; no remote installation observed.
- Source commit3549be7a includes tested changes; root merged latestmain and is preparing release assets. Check gitstatus/log for final merge/publication result before repeating anything.

## Parallel next work (source frozen until1.2.2published)

- Sollearning_replay: diagnose actualLFMzeroheldlearning, exacttargettokenization, training-questionvsheldgeneration/NLL; fixed next probe before loading weights. Also audit source-grounding of factcards. No model loading without resource coordination.
- Solcreative_backend: Learn Mode lifecycle audit. Found pending setup'sstop/until inputs can launchthreeindefinitehelpers, and active/held/busy helpers mayignoreuntil. Propose concrete lifecycle fixes/tests after publication.
- Terradesktop_bug_hunt: Windows sleep audit. CPU bf16base~3.4GB but pre-loadguardpermits1GB and maininjectedGuards ignoresprofile; stoptimeoutcan overlapmodels; stalehealthreportready; invalid/inconclusiveservedadaptersmayreuse. Assign focused fixes after publication.

Keep staged/deployed revisions and experiment outputs clearly distinguished. Save reproducible measurements, do not claim quality gains from changed weights or successful plumbing alone. At session end save a handoff and pause the heartbeat.
