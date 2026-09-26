# Vast credit check — 2026-09-26 (13:05 UTC task, run ~09:05–09:10 local)

Worktree: /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
Read-only: nothing deleted, rented, or changed outside this PUSH dir. Numbers 1–3 only, per task.

## 1. vast credit (`vastai show user --raw`; key via $(cat ~/.config/vastai/vast_api_key), never printed)
- credit = 6.832602647269866 (~$6.83)
- balance = 0

## 2. `vastai show instances` (ids, labels, dph, start time)
4 instances, all running, all 1x RTX 5090, pytorch/pytorch:2.8.0-cuda12.8-cudnn9-devel.
- id 52748076, label rent-dl4, dph_total 0.4944 (~$0.49/hr), start 2026-09-26T12:50:15Z
- id 52748679, label rent-brd8-s0, dph_total 0.4852 (~$0.49/hr), start 2026-09-26T12:55:38Z
- id 52748681, label rent-brd8-s1, dph_total 0.4852 (~$0.49/hr), start 2026-09-26T12:55:39Z
- id 52748682, label rent-brd8-s2, dph_total 0.4852 (~$0.49/hr), start 2026-09-26T12:55:40Z
- Combined burn ≈ $1.95/hr → ~$6.83 credit ≈ about 3.5 hours of all four running.

## 3. `df -g /` free GB
- /dev/disk3s1s1: 460 1G-blocks, 12 used, 57 available (19%) → 57 GB free.
