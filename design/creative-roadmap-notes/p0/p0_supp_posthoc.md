
## B2_s100 (supplementary, post hoc)

| split/variant | T | eff. programs distinct (mean) | eff. program != greedy % | P(answer != greedy given eff. program != greedy) %, greedy NUM rows | same, other rows | hits by candidate path (NUM=prompt number / NUM other / WORD / GEN) | uniform prompt-token floor pass@32 | sampled pass@32 |
|---|---|---|---|---|---|---|---|---|
| heldout/prog | 0.7 | 2.3 | 14.5 | 97.2 (n=708) | 97.1 (n=35) | 0 / 4 / 0 / 0 | 1.1 | 1.2 |
| heldout/prog | 1.0 | 3.1 | 20.0 | 96.1 (n=979) | 100.0 (n=44) | 0 / 6 / 0 / 0 | 1.1 | 1.2 |
| heldout/prog | 1.5 | 4.2 | 27.3 | 96.7 (n=1322) | 98.7 (n=75) | 0 / 9 / 0 / 0 | 1.1 | 1.9 |
| heldout/all | 0.7 | 2.3 | 14.8 | 96.5 (n=721) | 100.0 (n=39) | 0 / 6 / 0 / 0 | 1.1 | 1.2 |
| heldout/all | 1.0 | 3.0 | 19.5 | 96.1 (n=946) | 100.0 (n=53) | 0 / 14 / 0 / 0 | 1.1 | 1.9 |
| heldout/all | 1.5 | 4.3 | 28.0 | 96.5 (n=1356) | 97.4 (n=78) | 0 / 12 / 0 / 1 | 1.1 | 3.1 |
| frame_wrong/prog | 0.7 | 1.1 | 1.4 | 100.0 (n=85) | 100.0 (n=1) | 1 / 41 / 67 / 0 | 25.0 | 10.7 |
| frame_wrong/prog | 1.0 | 1.1 | 1.8 | 100.0 (n=108) | 33.3 (n=3) | 3 / 44 / 92 / 0 | 25.0 | 13.3 |
| frame_wrong/prog | 1.5 | 1.2 | 2.2 | 100.0 (n=127) | 36.4 (n=11) | 7 / 52 / 139 / 0 | 25.0 | 17.3 |
| frame_wrong/all | 0.7 | 1.1 | 1.2 | 100.0 (n=76) | 100.0 (n=1) | 0 / 31 / 76 / 140 | 25.0 | 26.0 |
| frame_wrong/all | 1.0 | 1.1 | 1.7 | 100.0 (n=103) | 50.0 (n=2) | 0 / 40 / 92 / 197 | 25.0 | 34.7 |
| frame_wrong/all | 1.5 | 1.2 | 2.2 | 100.0 (n=121) | 40.0 (n=20) | 4 / 47 / 164 / 241 | 25.0 | 46.4 |
| vocab_wrong/prog | 0.7 | 1.3 | 4.1 | 89.0 (n=127) | n/a | 3 / 40 / 26 / 0 | 23.0 | 15.6 |
| vocab_wrong/prog | 1.0 | 1.6 | 6.6 | 85.6 (n=202) | n/a | 7 / 65 / 46 / 0 | 23.0 | 19.8 |
| vocab_wrong/prog | 1.5 | 1.8 | 8.9 | 87.9 (n=273) | n/a | 9 / 64 / 74 / 0 | 23.0 | 25.0 |
| vocab_wrong/all | 0.7 | 1.4 | 5.2 | 88.8 (n=160) | n/a | 4 / 58 / 35 / 69 | 23.0 | 28.1 |
| vocab_wrong/all | 1.0 | 1.7 | 6.7 | 86.5 (n=207) | n/a | 8 / 55 / 52 / 74 | 23.0 | 35.4 |
| vocab_wrong/all | 1.5 | 1.8 | 8.8 | 89.7 (n=271) | n/a | 7 / 57 / 58 / 82 | 23.0 | 43.8 |

## B2_s101 (supplementary, post hoc)

| split/variant | T | eff. programs distinct (mean) | eff. program != greedy % | P(answer != greedy given eff. program != greedy) %, greedy NUM rows | same, other rows | hits by candidate path (NUM=prompt number / NUM other / WORD / GEN) | uniform prompt-token floor pass@32 | sampled pass@32 |
|---|---|---|---|---|---|---|---|---|
| heldout/prog | 0.7 | 2.1 | 13.9 | 92.1 (n=546) | 84.8 (n=164) | 0 / 28 / 0 / 0 | 1.1 | 4.4 |
| heldout/prog | 1.0 | 2.9 | 19.5 | 92.3 (n=736) | 78.5 (n=260) | 0 / 17 / 0 / 0 | 1.1 | 4.4 |
| heldout/prog | 1.5 | 4.4 | 27.9 | 92.9 (n=1061) | 80.2 (n=368) | 0 / 27 / 0 / 0 | 1.1 | 5.6 |
| heldout/all | 0.7 | 2.1 | 13.8 | 94.3 (n=545) | 87.0 (n=162) | 0 / 20 / 0 / 0 | 1.1 | 3.8 |
| heldout/all | 1.0 | 2.9 | 18.6 | 93.9 (n=716) | 90.2 (n=235) | 0 / 29 / 0 / 0 | 1.1 | 5.0 |
| heldout/all | 1.5 | 4.5 | 27.8 | 93.1 (n=1057) | 91.0 (n=368) | 0 / 37 / 0 / 0 | 1.1 | 6.2 |
| frame_wrong/prog | 0.7 | 1.0 | 0.6 | 100.0 (n=30) | n/a | 0 / 7 / 51 / 0 | 15.5 | 4.8 |
| frame_wrong/prog | 1.0 | 1.1 | 0.9 | 100.0 (n=45) | 0.0 (n=1) | 2 / 9 / 62 / 1 | 15.5 | 10.2 |
| frame_wrong/prog | 1.5 | 1.1 | 1.3 | 96.8 (n=62) | 33.3 (n=9) | 8 / 15 / 95 / 1 | 15.5 | 13.8 |
| frame_wrong/all | 0.7 | 1.0 | 0.4 | 100.0 (n=24) | n/a | 6 / 6 / 49 / 159 | 15.5 | 22.8 |
| frame_wrong/all | 1.0 | 1.1 | 0.8 | 100.0 (n=40) | 100.0 (n=1) | 13 / 7 / 58 / 175 | 15.5 | 31.1 |
| frame_wrong/all | 1.5 | 1.1 | 1.2 | 98.3 (n=58) | 37.5 (n=8) | 19 / 13 / 111 / 220 | 15.5 | 40.1 |
| vocab_wrong/prog | 0.7 | 1.1 | 1.9 | 93.3 (n=60) | 100.0 (n=1) | 0 / 21 / 32 / 0 | 22.4 | 10.7 |
| vocab_wrong/prog | 1.0 | 1.2 | 2.8 | 87.8 (n=90) | 100.0 (n=1) | 0 / 21 / 51 / 0 | 22.4 | 14.6 |
| vocab_wrong/prog | 1.5 | 1.2 | 3.6 | 95.8 (n=118) | 50.0 (n=2) | 0 / 31 / 64 / 0 | 22.4 | 16.5 |
| vocab_wrong/all | 0.7 | 1.1 | 2.2 | 94.4 (n=71) | n/a | 3 / 17 / 30 / 68 | 22.4 | 23.3 |
| vocab_wrong/all | 1.0 | 1.1 | 2.2 | 94.4 (n=72) | n/a | 3 / 23 / 49 / 72 | 22.4 | 29.1 |
| vocab_wrong/all | 1.5 | 1.2 | 3.8 | 94.3 (n=122) | 100.0 (n=2) | 12 / 30 / 70 / 98 | 22.4 | 41.7 |
