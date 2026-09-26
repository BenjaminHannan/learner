# ADDENDUM 0.2d-r: machine only (2026-09-26 ~14:30 UTC, before any run)

PASSMARKS-02dr.md and SEAL-02dr.sha256.txt are sealed and unchanged. No row, bar, arm, seed, judge rule or line of code changes.

1. Machine. Ben, 13:30 UTC 09-26: queued GPU tests run on vast.ai rentals and never wait for BensPC. The run moves from
   handoff/queue/007r-02dr-benspc.md (moved to handoff/held, never launched) to handoff/queue/rent-02dr.md. The reader comes
   from the Director's depot (claude-director-depot, /root/reader319, sha256 e688e1b2...6a76, DEPOT READY 14:12 UTC). The
   0.2c adapter (sha256 a33211dc...36f5) is streamed from BensPC with its json sidecar. Spend: $0.80 cap from Month-end's $2.
2. R0 on the Mac. The rental has no lis-301 weights and shipping 2 GB from the Mac takes about 90 min, so R0's refusal half
   runs on the Mac against ~/premonition-models/lis301-merged (the wrapper hashes the file and stops before loading anything;
   CPU only, no disk written). R0's acceptance half is X's first output line on the rental, as before.
3. What the machine change can alter. X' now runs on a rental GPU while G's reused 0.2c file came from BensPC, so X' - G
   carries a small GPU-numerics difference on top of the one registered change. To size it, one REPORT-ONLY arm runs after X'
   on the same rental: the plain twin, `--arm twin --name Tr --model BASE`, the exact 0.2c T command. It is scored on its own
   (score-machine/), never mixed into the registered score, and changes no mark.
   Fixed now: if Tr's scorer counts for answerable-right (M4), never-told "don't know" (M5) and edit asks right each lie within
   2 of 0.2c T's, the machine effect is treated as small. If any differs by more than 2, VERIFY-02dr reads every row exactly
   as registered but states that X' - G is confounded by the machine and cannot be credited to the weights alone.
