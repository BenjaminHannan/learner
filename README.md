# 8a own text (data only)

REPLACED 2026-10-07 (about 2:50 PM ET): the new own72 built with both length filters off (data-pool PR #47, own72_MANIFEST.json sha256 e8f32daf44d5...). The first commit held the filtered build and is superseded.

The three own-text files of the 8a growth ladder, xz-compressed (generator output that cannot be re-made on the PC: TEACH is 171,940 rows the 1.2B wrote on the PC GPU).
`python -m custom_io.g8a.get_data --work WORK --data-pool <claude/data-pool-8b checkout> --own-xz <this folder>` decompresses them and checks every file's sha256
against `data_pool/built/own72_MANIFEST.json`; it refuses to continue on any mismatch.
