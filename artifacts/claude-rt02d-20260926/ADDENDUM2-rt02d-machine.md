# ADDENDUM 2 rt-02d: machine and owner only (2026-09-26, before any registered run)

PASSMARKS-rt02d.md, ADDENDUM-rt02d.md, the route code and the blind panel are sealed and unchanged (SEAL-code-rt02d.sha256.txt).

1. Owner: the Plain-English puzzles thread took rt-02d over from Month-end (coordinator, 13:33 UTC; Month-end's agreement in
   the job file's header). Month-end joins the verdict into the build as its own single change.
2. Machine: Ben, 13:30 UTC 09-26: queued GPU tests run on vast.ai rentals and never wait for BensPC. The registered run moves
   from handoff/queue/007s-rt02d-benspc.md (now in handoff/held, never launched) to handoff/queue/rent-rt02d.md, with the
   same steps, arms, seeds, reader (sha256 e688e1b2...6a76) and 0.2c adapter (sha256 a33211dc...36f5).
3. What this can change: the 1B's numbers on a different GPU can differ slightly from BensPC's, so B0's replies need not
   match 0.2c's. B0, B1 and B1off all run on the same rental, so R1, R2 and R4 still compare like with like. The dev gate
   (B0 twice on the 55 dev cases, byte-identical, ADDENDUM item 3) still runs first on the rental.
No mark, bar, panel, seed or line of code changes.
