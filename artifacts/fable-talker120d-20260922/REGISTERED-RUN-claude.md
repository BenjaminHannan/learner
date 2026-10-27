# Exp 120d — registered runs (run by Claude, director), 2026-09-22 07:37–07:44

Why Claude ran them: the Muse agent checked for the checkpoint shortly before Claude re-copied it from BensPC (07:21, 346,258,593 bytes, same size as `C:\Users\benja\talker101\fable-talker120b-ft\fable_talker120b_ckpt_last.pt`), so it recorded the runs as BLOCKED. Seal re-verified first (`shasum -a 256 -c SEAL.sha256.txt` → PASSMARKS.md: OK). The agent's err log shows no code edits after its seal line; after the seal it only edited the ledger, RESULTS.md and the doc. Each registered run was executed once, exactly as in RESULTS.md "Reproduce", with Qwen ears at 127.0.0.1:18081 (health ok).

| mark | bar | result | status |
|---|---|---|---|
| R1 wrong_writes | [0,0,0] | [0,0,0] | PASS |
| R1 correct / abstentions / missed / two-hop | [12,12,12] / [3,3,3] / [0,0,0] / [6,6,6] | identical | PASS |
| R1 empty said | ≤ 5 per run, 0 on answer turns | 5 / 5 / 5 (all 5 are small-talk turns: "Hi, how are you?", "Thanks", weather, joke, "Good morning!"); 0 on answer turns | PASS |
| R1 ears english | ≥ 39/40 per run | 40 / 40 / 40 | PASS |
| R2 after-brake unfaithful | 0 | 0 (raw before-brake 172, not gated) | PASS |
| R2 status recoverable | ≥ 486/500 | 489/500 | PASS |
| R2 OK answer present | 250/250 | 250/250 | PASS |
| R3 wall-clock | < 25 min each | replay 328 s, score 426 s | PASS |

**Verdict: PASS (all marks).** Files: replay.json, replay-registered.log, score.json, score-registered.log.

The two don't-know answers now: "Where is Zed's city?" → "I don't know anyone called Zed." (was silent, then vague). The Porto question → "Ana's city is Porto, which is not someone I can look up." (was "I don't know Porto's city").

What it means: answer statuses the talker never trained on now always get the notebook's own faithful sentence, so no silent or wrong-shaped don't-knows remain in this replay.
What it doesn't mean: the talker itself is unchanged. It is still unfaithful before the brake on 172/500 records, and small talk is still silent. Also seen, not gated: a doubled word ("Rome Rome, no doubt."), and an internal parser message reaching the user ("…relation path/surface lengths differ").
