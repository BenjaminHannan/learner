# Reading-list statistics

- tokens: **45,613,271**
- sentences: **4,333,967** (mean 10.52 pieces)
- documents: **209,282**
- `<ENT>` placeholders: 916,982 (2.01 % of tokens)

## Tokens per source

| split/source | tokens |
|---|---:|
| train/simplestories | 11,392,915 |
| train/soda | 5,976,266 |
| train/tinydialogues | 10,878,420 |
| train/tinystories_v2 | 12,312,606 |
| valid/simplestories | 1,424,245 |
| valid/soda | 729,440 |
| valid/tinydialogues | 1,361,021 |
| valid/tinystories_v2 | 1,538,358 |

## Sentence-length histogram (pieces)

| len | sentences |
|---:|---:|
| 1 | 359 |
| 2 | 22,579 |
| 3 | 130,502 |
| 4 | 211,898 |
| 5 | 296,616 |
| 6 | 333,789 |
| 7 | 341,078 |
| 8 | 348,538 |
| 9 | 351,250 |
| 10 | 338,216 |
| 11 | 325,419 |
| 12 | 293,654 |
| 13 | 266,850 |
| 14 | 236,743 |
| 15 | 185,084 |
| 16 | 150,452 |
| 17 | 119,488 |
| 18 | 92,892 |
| 19 | 72,413 |
| 20 | 54,003 |
| 21 | 40,481 |
| 22 | 30,409 |
| 23 | 22,773 |
| 24 | 17,192 |
| 25 | 12,889 |
| 26 | 9,718 |
| 27 | 7,123 |
| 28 | 5,299 |
| 29 | 3,977 |
| 30 | 3,007 |
| 31 | 2,253 |
| 32 | 1,643 |
| 33 | 1,246 |
| 34 | 947 |
| 35 | 655 |
| 36 | 634 |
| 37 | 454 |
| 38 | 345 |
| 39 | 235 |
| 40 | 211 |
| 41 | 154 |
| 42 | 125 |
| 43 | 116 |
| 44 | 82 |
| 45 | 46 |
| 46 | 60 |
| 47 | 40 |
| 48 | 30 |

## Vocabulary coverage

- BPE ids actually used: 7972 / 8192 (97.3 %)
- word types that are a single piece: 4,887 / 24,701 (19.8 %)
- word *occurrences* that are a single piece: 95.1 %
- mean pieces per word: 1.0543

## Measured throughput

- 4.79 MB of raw text per second with 4 worker(s)
- 1,021,807 tokens per second
