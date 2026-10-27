
## Addendum E (2026-10-27 05:30Z, before any P1, P2a or P2b result): adaptive halting
Raised by Ben: the assistant must decide by itself how many laps each problem gets, not use a fixed count.
- Always reported, no pass mark: for every lap arm, accuracy by depth (1-6) at each scored lap count. Halting is only
  worth building if harder (deeper) questions gain more from extra laps than easy ones.
- Arm `halt` runs only if a notes test passes (P2a, P2b, P3 or P4 meets every bar) AND that arm's lap gain is larger on
  depth 4-6 than on depth 1-2. It is the passing arm's recipe plus a halting head on the notes (PonderNet-style: a stop
  probability per lap, loss = expected answer loss over the halting distribution + 0.01 x KL to a geometric prior with
  p = 0.25), L_max 8, from the same start checkpoint with the same steps. At test time it stops at the first lap whose
  stop probability is >= 0.5.
- Marks: H1: S_halt >= S_fixed - 0.5, where S_fixed is the passing arm at its own lap count, while the mean number of
  laps is <= 0.6 x L_max. H2: mean laps on depth 4-6 rows minus depth 1-2 rows >= 1.0 (bootstrap interval excluding 0).
- Wrong if the laps used don't rise with depth (Spearman rho <= 0.1 between depth and laps), or S_halt < S_fixed - 1.5.
- It never changes another test's verdict; its run counts toward the 18 R cap.
