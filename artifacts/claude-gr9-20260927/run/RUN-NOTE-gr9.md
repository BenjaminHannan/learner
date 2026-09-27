# RUN-NOTE gr-9 (dev only)

- **Seal.** Sealed in 98b53d445 (PASSMARKS-gr9.md, SEAL-gr9.sha256.txt, dev/SEAL-dev.sha256.txt).
- **Launch.** cpu/chain.sh started once, on this container's CPU with 4 threads, at $0. Its first STEP line is
  2026-09-27T12:03:28Z. All seals, gr-7's adapter sha256 and gr-6's rows sha256 checked OK, and L9 training started
  (STEP train_L9 2026-09-27T12:03:29Z).
- **Smoke test before sealing (disclosed).** The run path ran once, for arms L9 and L7 with gr-7's adapter, on 1
  gr-8 practice item (d8-un-000, already spent practice). It is in no mark here. Both arms read the same grid.
- **Scratch build (disclosed).** Before sealing, the training rows and the dev set were built once in a scratch folder.
  The sealed files are byte-identical to it: the same sha256 for rows.jsonl and every dev file. The owner read 5 dev
  rows and 4 training rows from that build.
- **Weights stay off git.** Adapters go to /mnt/project-files/plain-english-puzzles/ (gr9_adapter.pt,
  gr9_l7c_adapter.pt), and their sha256 go to run/adapter-*.sha256.txt.

Written 2026-09-27T12:03:47Z (date -u).
