# k1f ADDENDUM 1: run on BensPC instead of a rental (Creative answers in chat thread, written 2026-09-26 19:16 UTC)

Written before any k1f command has run anywhere. Registered FAILs stay FAILs; nothing in the marks changes.

## Why
- rent-k1f ended HOST-FAIL (runs/rent-k1f on builder-outbox): three RTX 5090 rentals either never finished loading or
  never accepted SSH, so no k1f command ran. About $0.10 spent, nothing copied back, all rentals destroyed.
- Ben, 18:42 and 18:54 UTC: the rest runs on BensPC, and any new rental needs his yes on a written plan. BensPC is free
  and already holds every model this test needs at the pinned revisions.

## What changes (the machine only)
- Machine: BensPC (Windows, RTX 5070 Ti 16 GB, its torch 2.11 and Python 3.10 venv), not a rented Linux 5090.
- Arms run one after another, not at once (bm-390 on BensPC ran out of GPU memory running arms side by side).
- Models come from BensPC's Hugging Face cache at the same pinned commits: MiniCPM5-1B 87179e5c1f455ef22e6223592d2d61351b525bfc,
  Qwen3.5-2B 15852e8c16360a2fea060d615a32b45270f8a8fc, LFM2.5-1.2B-Instruct 0f604ada3f766f9f257460c4c9f0b5d6f69d431b
  (the snapshot folder names are those commits; bm-390 loaded both rivals there on 2026-09-25). This replaces the
  PASSMARKS line that the rivals are downloaded on the rental and that nothing comes from BensPC's copies; that line
  was about where the files come from, and the pinned files are the same.
- Windows line endings: every Python command goes through scripts/claude_winnl2_wrap.py, as in gram-364 and bm-390,
  so written files keep Linux line endings (checked by a CRLF count, expected 0).

## What does not change
The code, the seals (SEAL.sha256.txt), the panel and its seal, the arms and their env settings (K1F_WRITER_MODEL for
F only, K1F_DRAFTS for K and F, SLEEP02C_ADAPTER = 0.2c's adapter02c.pt sha256 a33211dc...36f5 for K and F), the DEV
gate, the V1 lines, the marks K1f.1-3, the K1 line, the rival readings, the draft report, the judging and the recount.
