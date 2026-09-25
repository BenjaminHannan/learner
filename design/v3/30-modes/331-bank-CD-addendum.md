# 331 addendum: banks C and D (month-end line, 2026-09-25 ~02:50 UTC)

Banks A and B are spent after 336 and 336b. Two fresh TEST-ONLY banks for the next joined tests (0.2 and its
follow-up), written blind to design/v3/30-modes/331-e2e-bank-spec.md with these differences only:

- Bank C: 40 lives, ids `e2e-c-01`..`e2e-c-40`. Every person and pet first name is an invented Italian- or
  Spanish-sounding name (e.g. the style of "Lucetta", "Oriano"), no two lives share a name.
- Bank D: 40 lives, ids `e2e-d-01`..`e2e-d-40`. Every person and pet first name is an invented Nordic- or
  Slavic-sounding name (e.g. the style of "Sigrun", "Bozhena"), no two lives share a name.
- No name in C or D may be a name used in bank A, B, DEV or G (the writer cannot see those banks, so it writes
  fresh invented names; the escrow checker lists any overlap afterwards and the writer replaces them).
- Same kinds, minimums, keys, checks and README as the spec. Written to /mnt/project-files/escrow-331/C/ and
  /mnt/project-files/escrow-331/D/, audited blind by a second agent (audit.jsonl + audit_v2.md, fixes in
  turns_v2.jsonl / truth_v2.jsonl), then sealed (SEAL.sha256.txt). Only the SEAL goes on main before a registered run.
