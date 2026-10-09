---
name: audio-design-opus
description: Audio design (Opus thread, 10-03): game sound first, small causal stereo ear, PR #25 on PR #24's branch, S0-S3/G1-G3 ladder
metadata:
  type: project
  modified: 2026-10-03T13:53:51.497Z
---

Thread cmsg_01GSLCHTCnZxn7DhV19qcDvMMW6HVu4atHEySZyS1Lk5at took over from "Design: audio input" (PR #24). Follow-up PR #25 (branch claude/project-thread-q2xoid, base claude/project-thread-qsg2yc). Explainer https://claude.ai/artifact/1LEjqqsYpV95YUNUvztYBg (v2).

- Decision (Ben 13:39 UTC: "hear sounds", creeper behind you): game sound is the primary audio track; speech (Whisper-base, A0/E1-E7) is later.
- Default game ear: own causal stereo ear (premonition/audio/stream.py): uncentred STFT, fixed log floor, L/R/ILD mel, dilated causal conv (RF 0.63 s, 289k params) + adapter (230k), 50 ms slots, last 40 slots, coords time = slot centre minus now. Counts toward size budget. Fair opponent: frozen frame_mn06 (PretrainedSED) per channel.
- Facts checked: creeper 1.5 s fuse, needs line of sight; OpenAL panpot = amplitude panning, front/back blind; Directional Audio (HRTF) since 1.19; subtitles L/R only, keep OFF; MineRL/MineDojo have no audio.
- Workspace issues sent to coordinator for the reasoner thread: audio row/col=0 collides with image (0,0); +/-4 bias = +/-200 ms, use log time buckets; registers need t=0.
- PAUSED (Ben 15:07 UTC 10-03, cmsg_01GSLCHTCnZxn7DhV19qcDvMAHzsVZ9uKbcBNTDxVh56Ke: "Don't worry abt vision and audio yet"). All work pushed to PR #25 (head 5ddf403c8, matches Workspace v1 id tables). No new audio work until Ben or the coordinator restarts it.
- Audio does not take an early GPU slot. S1 is CPU once game sounds are rendered.

**Why:** Minecraft north star; skills first. **How to apply:** follow section (j) of design/next-parts/audio-input.md. See [[critical-thinking-reasoner-design]].
