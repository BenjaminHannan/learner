# Night learning: local status

A launchd job, `com.premonition.night-learn`, checks every five minutes. It
starts the pass only from 01:00 to 07:00 after 20 minutes of Mac idle. The
pass checks the idle rule again while training. It uses the previous local
calendar day, and puts the last fifth of elapsed recording time aside.

The reader supports the recorder's indexed clock only with an actual measured
offset and uncertainty, a matching frame count, stable display layout and a
passing scratch display calibration. It also supports the stronger v2 encoder
receipt. It matches frames before input, maps points through the full-display
letterbox, and rejects unverifiable clips. The teacher uses Glim's video eyes
and the real-model lock; output with invalid action references is refused.
The candidate trainer fits click, drag, key and scroll actions, compares a
zero-intent control, and weights evidence-backed corrections three times.
Candidates are quarantined. A rollback is logged; this action head is not yet
wired into the live HANDS worker.

**Not yet a completed real night.** The installed app has not yet supplied the
requested two-minute scratch cursor check, so `calibration.json` does not exist.
The live recorder is being installed separately. The earlier toy policy has no
verified, compatible live native-action checkpoint, so P2 cannot yet be claimed
against the real pre-sleep hands. The pass records that as not measured. The
real-recording path and full Glim-to-training path have not been smoke-tested.
The scheduled pass fails closed on missing calibration or recording evidence;
it cannot be claimed to have completed simply because launchd is installed.

The scorer hashes the held labels; a completed pass must also retain its full
evaluation-set hash, all three model hashes, five real explanations, and P1–P3
results. Existing retention runs only after a valid comparison has been judged.
No awake live weights are changed. Do not use synthetic development results as
real recordings or as P2 proof.
