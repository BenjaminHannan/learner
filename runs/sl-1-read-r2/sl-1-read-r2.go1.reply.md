start 2026-09-29 14:02:39 UTC
10:02  up 14:36, 2 users, load averages: 290.35 296.43 286.18
/dev/disk3s1s1       460   12       102    12%  484014 1070239280    0%   /
seal: 20 of 20 files OK
{"selftest": "ok", "torch_part": "ran"}
seed 0 pid 23050 started 2026-09-29 14:02:49 UTC
seed 1 pid 23052 started 2026-09-29 14:02:49 UTC
== seed 0
{"phase": "sl_extract", "seed": 0, "net": "k1024", "consistent": true, "maze_right": 275}
{"phase": "sl_extract", "seed": 0, "net": "k4096", "consistent": true, "maze_right": 256}
{"phase": "sl_extract", "seed": 0, "net": "k16384", "consistent": true, "maze_right": 286}
== seed 1
{"phase": "sl_extract", "seed": 1, "net": "k1024", "consistent": true, "maze_right": 233}
{"phase": "sl_extract", "seed": 1, "net": "k4096", "consistent": true, "maze_right": 292}
{"phase": "sl_extract", "seed": 1, "net": "k16384", "consistent": true, "maze_right": 261}
ok: every recomputed count matched the harness records
== Part A (Lead 3): word per signal, judged on maze rungs (64, 256, 1024, 4096, 16384)
   q_stop: NOT SHOWN | eligible AUROCs by seed {0: [0.6728, 0.2389, 0.3375, 0.3747, 0.8979], 1: [0.6104, 0.7303, 0.6316, 0.8882]}
   q_last: NOT SHOWN | eligible AUROCs by seed {0: [0.6728, 0.2389, 0.3375, 0.3747, 0.9248], 1: [0.6105, 0.7303, 0.5882, 0.8882]}
   margin: USEFUL | eligible AUROCs by seed {0: [0.9026, 0.9815, 0.982, 0.9656, 0.9933], 1: [0.8947, 0.9666, 0.9544, 0.9669]}
   no_flips: NOT SHOWN | eligible AUROCs by seed {0: [0.5496, 0.6669, 0.6621, 0.4963, 0.7847], 1: [0.5796, 0.6391, 0.7121, 0.4996]}
   still: NOT SHOWN | eligible AUROCs by seed {0: [0.7236, 0.6623, 0.6748, 0.3851, 0.6359], 1: [0.7851, 0.7939, 0.7895, 0.479]}
== Part B (Lead 1, ceiling only): word per rule
   ruler: FAILS | rungs passing {0: 1, 1: 1}
   s3: CEILING MET | rungs passing {0: 5, 1: 5}
   s6: CEILING MET | rungs passing {0: 5, 1: 5}
== seed 0: rule rows of n (right | cap hits | mean rounds), then AUROC per signal
   k0 grids5: ruler 200 of 200 |0|8.97 ; fixed 200 of 200 ; s3 200 of 200 |0|8.97 ; s6 200 of 200 |1|14.245
      AUROC not eligible (0 wrong of 200)
   k0 maze: ruler 0 of 300 |300|48.0 ; fixed 0 of 300 ; s3 0 of 300 |300|48.0 ; s6 0 of 300 |300|48.0
      AUROC not eligible (300 wrong of 300)
   k0 sums4: ruler 200 of 200 |0|5.645 ; fixed 200 of 200 ; s3 200 of 200 |0|5.645 ; s6 200 of 200 |0|9.335
      AUROC not eligible (0 wrong of 200)
   k1024 grids5: ruler 0 of 200 |174|44.79 ; fixed 0 of 200 ; s3 0 of 200 |87|30.67 ; s6 0 of 200 |98|35.385
      AUROC not eligible (200 wrong of 200)
   k1024 maze: ruler 275 of 300 |300|48.0 ; fixed 272 of 300 ; s3 276 of 300 |83|23.35 ; s6 276 of 300 |91|27.147
      AUROC q_stop=0.3375 q_last=0.3375 margin=0.982 no_flips=0.6621 still=0.6748
   k1024 sums4: ruler 0 of 200 |50|21.645 ; fixed 0 of 200 ; s3 0 of 200 |42|20.375 ; s6 0 of 200 |56|26.88
      AUROC not eligible (200 wrong of 200)
   k16384 grids5: ruler 0 of 200 |59|24.14 ; fixed 0 of 200 ; s3 0 of 200 |7|15.705 ; s6 0 of 200 |14|23.02
      AUROC not eligible (200 wrong of 200)
   k16384 maze: ruler 286 of 300 |143|29.43 ; fixed 285 of 300 ; s3 283 of 300 |11|11.137 ; s6 285 of 300 |19|16.51
      AUROC q_stop=0.8979 q_last=0.9248 margin=0.9933 no_flips=0.7847 still=0.6359
   k16384 sums4: ruler 0 of 200 |8|11.955 ; fixed 0 of 200 ; s3 0 of 200 |6|11.55 ; s6 0 of 200 |27|20.98
      AUROC not eligible (200 wrong of 200)
   k256 grids5: ruler 0 of 200 |154|42.365 ; fixed 0 of 200 ; s3 0 of 200 |91|33.515 ; s6 0 of 200 |130|40.645
      AUROC not eligible (200 wrong of 200)
   k256 maze: ruler 263 of 300 |300|48.0 ; fixed 254 of 300 ; s3 261 of 300 |47|22.24 ; s6 262 of 300 |65|27.877
      AUROC q_stop=0.2389 q_last=0.2389 margin=0.9815 no_flips=0.6669 still=0.6623
   k256 sums4: ruler 0 of 200 |29|17.705 ; fixed 0 of 200 ; s3 0 of 200 |29|17.685 ; s6 0 of 200 |64|27.795
      AUROC not eligible (200 wrong of 200)
   k4096 grids5: ruler 0 of 200 |200|48.0 ; fixed 0 of 200 ; s3 0 of 200 |45|23.46 ; s6 0 of 200 |78|32.8
      AUROC not eligible (200 wrong of 200)
   k4096 maze: ruler 256 of 300 |300|48.0 ; fixed 243 of 300 ; s3 251 of 300 |80|22.12 ; s6 255 of 300 |134|31.633
      AUROC q_stop=0.3747 q_last=0.3747 margin=0.9656 no_flips=0.4963 still=0.3851
   k4096 sums4: ruler 0 of 200 |189|46.265 ; fixed 0 of 200 ; s3 0 of 200 |63|26.415 ; s6 0 of 200 |116|37.31
      AUROC not eligible (200 wrong of 200)
   k64 grids5: ruler 0 of 200 |193|46.915 ; fixed 0 of 200 ; s3 0 of 200 |23|19.655 ; s6 0 of 200 |45|29.165
      AUROC not eligible (200 wrong of 200)
   k64 maze: ruler 126 of 300 |300|48.0 ; fixed 122 of 300 ; s3 123 of 300 |19|15.5 ; s6 125 of 300 |27|20.743
      AUROC q_stop=0.6728 q_last=0.6728 margin=0.9026 no_flips=0.5496 still=0.7236
   k64 sums4: ruler 0 of 200 |161|40.425 ; fixed 0 of 200 ; s3 0 of 200 |8|12.595 ; s6 0 of 200 |46|25.915
      AUROC not eligible (200 wrong of 200)
== seed 1: rule rows of n (right | cap hits | mean rounds), then AUROC per signal
   k0 grids5: ruler 200 of 200 |8|11.72 ; fixed 200 of 200 ; s3 200 of 200 |8|11.72 ; s6 200 of 200 |13|16.65
      AUROC not eligible (0 wrong of 200)
   k0 maze: ruler 0 of 300 |300|48.0 ; fixed 0 of 300 ; s3 0 of 300 |295|47.697 ; s6 0 of 300 |299|47.93
      AUROC not eligible (300 wrong of 300)
   k0 sums4: ruler 200 of 200 |0|5.99 ; fixed 200 of 200 ; s3 200 of 200 |0|5.99 ; s6 200 of 200 |1|9.665
      AUROC not eligible (0 wrong of 200)
   k1024 grids5: ruler 0 of 200 |58|26.81 ; fixed 0 of 200 ; s3 0 of 200 |42|23.32 ; s6 0 of 200 |76|32.375
      AUROC not eligible (200 wrong of 200)
   k1024 maze: ruler 233 of 300 |61|19.92 ; fixed 220 of 300 ; s3 230 of 300 |25|14.92 ; s6 233 of 300 |52|21.297
      AUROC q_stop=0.6316 q_last=0.5882 margin=0.9544 no_flips=0.7121 still=0.7895
   k1024 sums4: ruler 0 of 200 |1|7.03 ; fixed 0 of 200 ; s3 0 of 200 |1|6.89 ; s6 0 of 200 |9|12.795
      AUROC not eligible (200 wrong of 200)
   k16384 grids5: ruler 0 of 200 |134|39.74 ; fixed 0 of 200 ; s3 0 of 200 |93|34.565 ; s6 0 of 200 |131|40.59
      AUROC not eligible (200 wrong of 200)
   k16384 maze: ruler 261 of 300 |194|35.333 ; fixed 259 of 300 ; s3 263 of 300 |50|21.713 ; s6 261 of 300 |82|28.237
      AUROC q_stop=0.8882 q_last=0.8882 margin=0.9669 no_flips=0.4996 still=0.479
   k16384 sums4: ruler 0 of 200 |79|28.15 ; fixed 0 of 200 ; s3 0 of 200 |78|27.965 ; s6 0 of 200 |112|35.945
      AUROC not eligible (200 wrong of 200)
   k256 grids5: ruler 0 of 200 |200|48.0 ; fixed 0 of 200 ; s3 0 of 200 |28|18.13 ; s6 0 of 200 |75|29.38
      AUROC not eligible (200 wrong of 200)
   k256 maze: ruler 277 of 300 |300|48.0 ; fixed 268 of 300 ; s3 269 of 300 |2|11.243 ; s6 275 of 300 |7|16.687
      AUROC q_stop=0.7303 q_last=0.7303 margin=0.9666 no_flips=0.6391 still=0.7939
   k256 sums4: ruler 0 of 200 |85|29.395 ; fixed 0 of 200 ; s3 0 of 200 |62|25.875 ; s6 0 of 200 |88|32.085
      AUROC not eligible (200 wrong of 200)
   k4096 grids5: ruler 0 of 200 |190|46.835 ; fixed 0 of 200 ; s3 0 of 200 |120|36.945 ; s6 0 of 200 |155|43.12
      AUROC not eligible (200 wrong of 200)
   k4096 maze: ruler 292 of 300 |196|34.703 ; fixed 288 of 300 ; s3 291 of 300 |21|15.113 ; s6 292 of 300 |27|20.247
      AUROC not eligible (8 wrong of 300)
   k4096 sums4: ruler 0 of 200 |138|37.63 ; fixed 0 of 200 ; s3 0 of 200 |14|13.03 ; s6 0 of 200 |48|24.315
      AUROC not eligible (200 wrong of 200)
   k64 grids5: ruler 0 of 200 |200|48.0 ; fixed 0 of 200 ; s3 0 of 200 |8|15.5 ; s6 0 of 200 |32|25.215
      AUROC not eligible (200 wrong of 200)
   k64 maze: ruler 173 of 300 |265|43.797 ; fixed 171 of 300 ; s3 175 of 300 |13|15.253 ; s6 173 of 300 |17|20.197
      AUROC q_stop=0.6104 q_last=0.6105 margin=0.8947 no_flips=0.5796 still=0.7851
   k64 sums4: ruler 0 of 200 |200|48.0 ; fixed 0 of 200 ; s3 0 of 200 |0|5.355 ; s6 0 of 200 |0|9.35
      AUROC not eligible (200 wrong of 200)
end 2026-09-29 14:09:39 UTC
rc=0
