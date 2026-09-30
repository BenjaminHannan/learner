# Numeric16 r3 paired saved-result summary

The sealed two-seed, two-arm fit is physically closed for all four arms. The verifier independently recounted each saved training stream against the strict canonical target IDs and actually emitted terminal EOS; every arm passed 16/16 at update 800, with 50 visits per row, 64 diagnostic rows, and no raw metadata errors.

| Seed | Arm | Job | Updates | Strict result | Saved recount SHA256 |
|---|---|---|---:|---|---|
| 0 | loop | `sol-cloud-numeric-v1-s0-loop-r3-benspc` | 800 | 16/16, numeric + actual EOS | `6d7695fd7c7513d624a766b7aeb6d08d20ad8c5b9c98c826a6be284137e0b2af` |
| 0 | plain | `sol-cloud-numeric-v1-s0-plain-r3-benspc` | 800 | 16/16, numeric + actual EOS | `7bba0ae47d4eeb926b3e729dc7e782ceab99e98ec906c42709f51849f3b07fbf` |
| 1 | loop | `sol-cloud-numeric-v1-s1-loop-r3-benspc` | 800 | 16/16, numeric + actual EOS | `2c0c664c9de5fb7fc5b19e2057e16bee442f9612316204c7b15239753ef04f89` |
| 1 | plain | `sol-cloud-numeric-v1-s1-plain-r3-benspc` | 800 | 16/16, numeric + actual EOS | `88d93be8de9d18a21a4489a5849b6a698bb565bf29d8d193aa9f71a00352ab08` |

The four raw and CLOSED files are retained under `artifacts/sol-cloud-numeric-fit-20260930/run-v1/seed{0,1}/{loop,plain}/`. All four final checkpoints and Adam states remain on the PC. The independent weights-only CPU tensor/Adam audit is pending; this summary does not claim that audit has passed.
