# lis-319f addendum R: machine change only (reading thread, 2026-09-26 13:25 UTC, before any run)

Why: BensPC is busy until 007b ends (cap 15:56 UTC) and more jobs queue behind it. Ben gave each thread $2 of
vast.ai compute (12:59 UTC); this thread spends it to run lis-319f on a rented RTX 5090 (4090 if none) now.
handoff/queue/007f-lis-319f-former.md is withdrawn from the BensPC queue in the same commit that adds
handoff/queue/rent-lis-319f.md, so the sealed panel is still read exactly once per reader.

Nothing else changes: same data commands, same training arguments, same seeds, same scorers, same marks M1-M3,
same proved-wrong and INCONCLUSIVE rules (PASSMARKS.md).
- OLD reader = the lis-319 merged reader copied to the rental byte for byte (model.safetensors sha256
  e688e1b221cff938d7032a8864c87df60111ad92bc09a650d091931704776a76). No re-merge. Any other sha: no OLD reads.
- Both readers read the panel on the same rental GPU, so machine numerics touch both arms alike.
- BASE = openbmb/MiniCPM5-1B downloaded on the rental (the kit's model; commit 87179e5c1f455ef22e6223592d2d61351b525bfc).
  The lis-319 dev predictions used for dev_former_old were made on BensPC; dev numbers are report only.
- If the rental job ends without both panel reads, the reading thread requeues the missing reads on BensPC
  (never a second read of the same reader).
