### Table A: healthy redo (4 resumes R1..R4, each a fresh process with its own noise) over updates 31..60

| accum | NOISE_EPS | loss level (mean C, 31..60) | first_diff (u31) mean R-C | early_max (u31..33) mean | mean_abs R-C | mean_abs/level | max_abs R-C (max of 4) | signed mean R-C | mean_abs R-R pairs | mean_abs R-C (each of R1..R4) | D/N | C rank of 5 (1 = most central) | healthy exact-field mismatch |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 4 | 0 | 7.9394 | 0.00000 | 0.00000 | 0.00000 | 0.0000% | 0.00000 | 0.00000 | 0.00000 | 0.00000, 0.00000, 0.00000, 0.00000 | n/a | 1 | {None} |
| 4 | 0.01 | 7.9428 | 0.00000 | 5.33e-04 | 4.06e-04 | 0.0051% | 0.00112 | -3.77e-04 | 3.41e-04 | 2.70e-04, 4.60e-04, 2.18e-04, 6.77e-04 | 1.190 | 4 | {None} |
| 4 | 0.3 | 13.7311 | 0.00000 | 0.00285 | 0.00509 | 0.0371% | 0.01726 | 0.00222 | 0.00684 | 0.00506, 0.00408, 0.00694, 0.00428 | 0.744 | 1 | {None} |
| 4 | 1 | 19.2167 | 0.00000 | 0.00575 | 0.00715 | 0.0372% | 0.02808 | 0.00214 | 0.01082 | 0.00669, 0.00665, 0.00936, 0.00590 | 0.661 | 1 | {None} |
| 4 | 8 | 61.1044 | 0.00000 | 0.06207 | 0.23492 | 0.3845% | 1.85528 | 0.22685 | 0.34387 | 0.05889, 0.66779, 0.04507, 0.16794 | 0.683 | 4 | {None} |
| 8 | 0 | 7.6402 | 0.00000 | 0.00000 | 0.00000 | 0.0000% | 0.00000 | 0.00000 | 0.00000 | 0.00000, 0.00000, 0.00000, 0.00000 | n/a | 1 | {None} |
| 8 | 0.01 | 7.6882 | 0.00000 | 7.25e-05 | 3.28e-04 | 0.0043% | 0.00247 | 9.72e-05 | 4.66e-04 | 4.39e-04, 2.19e-04, 4.09e-04, 2.45e-04 | 0.704 | 1 | {None} |
| 8 | 0.3 | 13.9286 | 0.00000 | 0.00178 | 0.00614 | 0.0441% | 0.02214 | -0.00392 | 0.00798 | 0.00906, 0.00753, 0.00347, 0.00452 | 0.770 | 1 | {None} |
| 8 | 1 | 22.4107 | 0.00000 | 0.00608 | 0.03814 | 0.1702% | 0.11291 | -0.03812 | 0.01217 | 0.03018, 0.03983, 0.04274, 0.03980 | 3.134 | 5 | {None} |
| 8 | 8 | 57.4285 | 0.00000 | 0.11023 | 0.25914 | 0.4512% | 1.46097 | -0.14217 | 0.43310 | 0.16486, 0.15702, 0.62651, 0.08818 | 0.598 | 1 | {None} |

### Table B: faulty resumes (same NOISE_EPS as the healthy ones, one fresh process each) vs C over updates 31..60

"u31 diff" = |loss(R) - loss(C)| at the first redone update (0 = exact match of the logged 5-decimal loss). "first nonzero" = first redone update at which the loss differs at all. "exact-field mismatch" = first update at which a field that must be exactly equal in a healthy redo (lr, rounds, plan_*, drill_share, copy_share, stop_w, cap_hits) differs. "x healthy" = mean_abs / healthy mean_abs(R,C). ">10x" = first redone update where |dL| > 10 * max(healthy max at that update over all R-C and R-R comparisons, 1e-5).

| accum | NOISE_EPS | fault | u31 diff | first nonzero | exact-field mismatch (update: fields) | early_max | mean_abs | max_abs | signed mean | x healthy (mean_abs) | >10x at update |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 4 | 0 | opt_reset | 0.00000 | 32 | none | 0.97789 | 0.21500 | 0.97789 | -0.10739 | n/a (healthy=0) | 32 |
| 4 | 0 | opt_moments_zero | 0.00000 | 32 | none | 0.66056 | 0.13604 | 0.66056 | 0.06720 | n/a (healthy=0) | 32 |
| 4 | 0 | data_shift | 2.76655 | 31 | 31: rounds,plan_rows,plan_gapped,drill_share | 3.64401 | 1.47579 | 3.64401 | -0.10005 | n/a (healthy=0) | 31 |
| 4 | 0 | rng_noreset | 0.88193 | 31 | 31: rounds,stop_w,plan_rows,plan_gapped,drill_share | 5.52833 | 0.65598 | 5.52833 | -0.39452 | n/a (healthy=0) | 31 |
| 4 | 0 | rng_global_noreset | 0.88001 | 31 | 31: rounds,stop_w | 5.60610 | 0.66942 | 5.60610 | -0.39818 | n/a (healthy=0) | 31 |
| 4 | 0 | rng_model_noreset | 0.00145 | 31 | 31: plan_rows,plan_gapped,drill_share | 0.07348 | 0.05650 | 0.22843 | 0.00799 | n/a (healthy=0) | 31 |
| 4 | 0 | lr_step_off | 0.00000 | 32 | 31: lr | 0.04542 | 0.06680 | 0.13767 | 0.06680 | n/a (healthy=0) | 32 |
| 4 | 0 | weights_eps | 0.00338 | 31 | none | 0.01104 | 0.00213 | 0.01104 | -0.00213 | n/a (healthy=0) | 31 |
| 4 | 0.01 | opt_reset | 0.00000 | 32 | none | 0.62595 | 0.14892 | 0.89954 | 0.07137 | 366.7 | 32 |
| 4 | 0.01 | opt_moments_zero | 0.00000 | 32 | none | 0.28951 | 0.17111 | 0.67551 | 0.15181 | 421.3 | 32 |
| 4 | 0.01 | data_shift | 2.81398 | 31 | 31: rounds,plan_rows,plan_gapped,drill_share | 3.65008 | 1.48421 | 3.65008 | -0.05343 | 3654.2 | 31 |
| 4 | 0.01 | rng_noreset | 0.91389 | 31 | 31: rounds,stop_w,plan_rows,plan_gapped,drill_share | 5.76129 | 0.67228 | 5.76129 | -0.39685 | 1655.2 | 31 |
| 4 | 0.01 | rng_global_noreset | 0.91697 | 31 | 31: rounds,stop_w | 5.84832 | 0.68510 | 5.84832 | -0.39390 | 1686.7 | 31 |
| 4 | 0.01 | rng_model_noreset | 0.00340 | 31 | 31: plan_rows,plan_gapped,drill_share | 0.08239 | 0.07360 | 0.23180 | 0.03834 | 181.2 | 31 |
| 4 | 0.01 | lr_step_off | 0.00000 | 32 | 31: lr | 0.04208 | 0.09350 | 0.19410 | 0.09350 | 230.2 | 32 |
| 4 | 0.01 | weights_eps | 0.00370 | 31 | none | 0.01259 | 0.00399 | 0.01259 | -0.00399 | 9.8 | 31 |
| 4 | 0.3 | opt_reset | 0.00000 | 32 | none | 0.42168 | 0.11568 | 0.42168 | 0.11568 | 22.7 | 32 |
| 4 | 0.3 | opt_moments_zero | 0.00000 | 32 | none | 0.99022 | 1.15092 | 8.04398 | 1.15092 | 226.0 | 32 |
| 4 | 0.3 | data_shift | 6.56460 | 31 | 31: rounds,plan_rows,plan_gapped,drill_share | 9.36654 | 3.21236 | 9.36654 | -0.15067 | 630.8 | 31 |
| 4 | 0.3 | rng_noreset | 3.08238 | 31 | 31: rounds,stop_w,plan_rows,plan_gapped,drill_share | 20.86909 | 2.97960 | 20.86909 | -1.38020 | 585.1 | 31 |
| 4 | 0.3 | rng_global_noreset | 3.14678 | 31 | 31: rounds,stop_w | 21.05845 | 3.04352 | 21.05845 | -1.36847 | 597.6 | 31 |
| 4 | 0.3 | rng_model_noreset | 0.06441 | 31 | 31: plan_rows,plan_gapped,drill_share | 0.41516 | 0.16673 | 0.44951 | 8.55e-04 | 32.7 | 31 |
| 4 | 0.3 | lr_step_off | 0.00000 | 32 | 31: lr | 0.07864 | 0.25091 | 0.57702 | 0.25091 | 49.3 | 32 |
| 4 | 0.3 | weights_eps | 0.00821 | 31 | none | 0.02284 | 0.00468 | 0.02284 | -0.00298 | 0.9 | 31 |
| 4 | 1 | opt_reset | 0.00000 | 32 | none | 0.32300 | 0.08720 | 0.32300 | 0.06450 | 12.2 | 32 |
| 4 | 1 | opt_moments_zero | 0.00000 | 32 | none | 1.01478 | 0.91337 | 2.35660 | 0.91337 | 127.7 | 32 |
| 4 | 1 | data_shift | 8.76487 | 31 | 31: rounds,plan_rows,plan_gapped,drill_share | 12.73379 | 4.76408 | 14.51805 | -0.25868 | 666.3 | 31 |
| 4 | 1 | rng_noreset | 4.32958 | 31 | 31: rounds,stop_w,plan_rows,plan_gapped,drill_share | 29.45236 | 4.92933 | 29.45236 | -2.04493 | 689.4 | 31 |
| 4 | 1 | rng_global_noreset | 4.38440 | 31 | 31: rounds,stop_w | 29.75596 | 5.01175 | 29.75596 | -2.01886 | 700.9 | 31 |
| 4 | 1 | rng_model_noreset | 0.05478 | 31 | 31: plan_rows,plan_gapped,drill_share | 0.60117 | 0.26096 | 0.72902 | 0.00285 | 36.5 | 31 |
| 4 | 1 | lr_step_off | 0.00000 | 32 | 31: lr | 0.08439 | 0.25932 | 0.64786 | 0.25932 | 36.3 | 36 |
| 4 | 1 | weights_eps | 0.00878 | 31 | none | 0.02190 | 0.00685 | 0.02190 | -9.20e-04 | 1.0 | 31 |
| 4 | 8 | opt_reset | 0.00000 | 32 | none | 0.62193 | 0.68094 | 1.55375 | -0.68094 | 2.9 | None |
| 4 | 8 | opt_moments_zero | 0.00000 | 32 | none | 0.37842 | 1.07186 | 2.66565 | 1.07186 | 4.6 | None |
| 4 | 8 | data_shift | 24.88439 | 31 | 31: rounds,plan_rows,plan_gapped,drill_share | 38.52763 | 19.01694 | 62.89604 | -1.19855 | 81.0 | 31 |
| 4 | 8 | rng_noreset | 14.26030 | 31 | 31: rounds,stop_w,plan_rows,plan_gapped,drill_share | 101.12409 | 26.07672 | 101.12409 | -8.90011 | 111.0 | 31 |
| 4 | 8 | rng_global_noreset | 14.23069 | 31 | 31: rounds,stop_w | 101.79994 | 26.49807 | 101.79994 | -8.54948 | 112.8 | 31 |
| 4 | 8 | rng_model_noreset | 0.02593 | 31 | 31: plan_rows,plan_gapped,drill_share | 2.07986 | 1.37153 | 4.23372 | -0.27422 | 5.8 | 31 |
| 4 | 8 | lr_step_off | 0.00000 | 32 | 31: lr | 0.06697 | 0.04111 | 0.13079 | 0.00648 | 0.2 | None |
| 4 | 8 | weights_eps | 7.30e-04 | 31 | none | 0.02413 | 0.11898 | 0.28732 | 0.11893 | 0.5 | 31 |
| 8 | 0 | opt_reset | 0.00000 | 32 | none | 0.53462 | 0.25250 | 0.80267 | -0.25250 | n/a (healthy=0) | 32 |
| 8 | 0 | opt_moments_zero | 0.00000 | 32 | none | 0.18380 | 0.09813 | 0.24124 | 0.05721 | n/a (healthy=0) | 32 |
| 8 | 0 | data_shift | 2.40016 | 31 | 31: rounds,plan_rows,plan_gapped,drill_share | 2.70139 | 1.28300 | 2.72576 | -0.11804 | n/a (healthy=0) | 31 |
| 8 | 0 | rng_noreset | 1.64494 | 31 | 31: rounds,stop_w,plan_rows,plan_gapped,drill_share | 1.64494 | 0.44977 | 1.64494 | 0.01191 | n/a (healthy=0) | 31 |
| 8 | 0 | rng_global_noreset | 1.67948 | 31 | 31: rounds,stop_w | 1.67948 | 0.42873 | 1.67948 | 0.00342 | n/a (healthy=0) | 31 |
| 8 | 0 | rng_model_noreset | 0.03460 | 31 | 31: plan_rows,plan_gapped,drill_share | 0.22191 | 0.06145 | 0.22191 | 0.01345 | n/a (healthy=0) | 31 |
| 8 | 0 | lr_step_off | 0.00000 | 32 | 31: lr | 0.06965 | 0.06222 | 0.13339 | 0.05005 | n/a (healthy=0) | 32 |
| 8 | 0 | weights_eps | 0.00212 | 31 | none | 0.00249 | 9.10e-04 | 0.00249 | -7.68e-04 | n/a (healthy=0) | 31 |
| 8 | 0.01 | opt_reset | 0.00000 | 32 | none | 0.36689 | 0.25515 | 0.60195 | -0.25515 | 777.5 | 32 |
| 8 | 0.01 | opt_moments_zero | 0.00000 | 32 | none | 0.25901 | 0.07576 | 0.25901 | 0.06149 | 230.9 | 32 |
| 8 | 0.01 | data_shift | 2.50121 | 31 | 31: rounds,plan_rows,plan_gapped,drill_share | 2.81121 | 1.28201 | 2.81121 | -0.09310 | 3906.6 | 31 |
| 8 | 0.01 | rng_noreset | 1.85971 | 31 | 31: rounds,stop_w,plan_rows,plan_gapped,drill_share | 1.85971 | 0.47638 | 1.85971 | -0.01628 | 1451.6 | 31 |
| 8 | 0.01 | rng_global_noreset | 1.89737 | 31 | 31: rounds,stop_w | 1.89737 | 0.45349 | 1.89737 | -0.02726 | 1381.9 | 31 |
| 8 | 0.01 | rng_model_noreset | 0.03771 | 31 | 31: plan_rows,plan_gapped,drill_share | 0.21651 | 0.07740 | 0.21682 | 0.02783 | 235.8 | 31 |
| 8 | 0.01 | lr_step_off | 0.00000 | 32 | 31: lr | 0.02757 | 0.09181 | 0.21551 | 0.09181 | 279.8 | 32 |
| 8 | 0.01 | weights_eps | 0.00264 | 31 | none | 0.00281 | 0.00138 | 0.00435 | -0.00138 | 4.2 | 31 |
| 8 | 0.3 | opt_reset | 0.00000 | 32 | none | 0.13649 | 0.09628 | 0.21921 | -0.07193 | 15.7 | 32 |
| 8 | 0.3 | opt_moments_zero | 0.00000 | 32 | none | 0.97648 | 0.58326 | 1.55396 | 0.58090 | 94.9 | 32 |
| 8 | 0.3 | data_shift | 6.56417 | 31 | 31: rounds,plan_rows,plan_gapped,drill_share | 6.56417 | 2.80157 | 8.63351 | -0.35492 | 456.0 | 31 |
| 8 | 0.3 | rng_noreset | 9.90659 | 31 | 31: rounds,stop_w,plan_rows,plan_gapped,drill_share | 9.90659 | 2.66199 | 9.90659 | -0.51851 | 433.3 | 31 |
| 8 | 0.3 | rng_global_noreset | 9.95246 | 31 | 31: rounds,stop_w | 9.95246 | 2.60854 | 9.95246 | -0.49083 | 424.6 | 31 |
| 8 | 0.3 | rng_model_noreset | 0.04587 | 31 | 31: plan_rows,plan_gapped,drill_share | 0.72486 | 0.17689 | 0.72486 | -0.07020 | 28.8 | 31 |
| 8 | 0.3 | lr_step_off | 0.00000 | 32 | 31: lr | 0.08112 | 0.20037 | 0.48312 | 0.20037 | 32.6 | 32 |
| 8 | 0.3 | weights_eps | 0.01298 | 31 | none | 0.01627 | 0.01013 | 0.02087 | -0.00966 | 1.6 | 31 |
| 8 | 1 | opt_reset | 0.00000 | 32 | none | 0.12259 | 0.05399 | 0.14431 | -0.03200 | 1.4 | 32 |
| 8 | 1 | opt_moments_zero | 0.00000 | 32 | none | 0.86203 | 0.89155 | 1.86729 | 0.89155 | 23.4 | 32 |
| 8 | 1 | data_shift | 10.25053 | 31 | 31: rounds,plan_rows,plan_gapped,drill_share | 10.25053 | 5.26922 | 17.23757 | -0.76266 | 138.2 | 31 |
| 8 | 1 | rng_noreset | 16.85285 | 31 | 31: rounds,stop_w,plan_rows,plan_gapped,drill_share | 16.85285 | 5.95475 | 16.85285 | -0.43719 | 156.1 | 31 |
| 8 | 1 | rng_global_noreset | 16.89387 | 31 | 31: rounds,stop_w | 16.89387 | 5.84580 | 16.89387 | -0.39188 | 153.3 | 31 |
| 8 | 1 | rng_model_noreset | 0.04101 | 31 | 31: plan_rows,plan_gapped,drill_share | 1.30134 | 0.39440 | 1.30134 | -0.17992 | 10.3 | 31 |
| 8 | 1 | lr_step_off | 0.00000 | 32 | 31: lr | 0.06520 | 0.21961 | 0.59760 | 0.21961 | 5.8 | None |
| 8 | 1 | weights_eps | 0.01451 | 31 | none | 0.02406 | 0.04438 | 0.09840 | -0.04438 | 1.2 | 31 |
| 8 | 8 | opt_reset | 0.00000 | 32 | none | 0.49792 | 0.84854 | 1.86162 | -0.84854 | 3.3 | None |
| 8 | 8 | opt_moments_zero | 0.00000 | 32 | none | 0.15990 | 0.13506 | 0.45967 | 0.09831 | 0.5 | None |
| 8 | 8 | data_shift | 24.45042 | 31 | 31: rounds,plan_rows,plan_gapped,drill_share | 24.45042 | 17.64762 | 55.82071 | -3.30793 | 68.1 | 31 |
| 8 | 8 | rng_noreset | 45.02859 | 31 | 31: rounds,stop_w,plan_rows,plan_gapped,drill_share | 45.36164 | 21.38322 | 48.69631 | -0.27878 | 82.5 | 31 |
| 8 | 8 | rng_global_noreset | 45.00413 | 31 | 31: rounds,stop_w | 45.00413 | 21.19520 | 47.49887 | 0.08515 | 81.8 | 31 |
| 8 | 8 | rng_model_noreset | 0.01814 | 31 | 31: plan_rows,plan_gapped,drill_share | 3.72302 | 1.36529 | 4.56682 | -0.59783 | 5.3 | 31 |
| 8 | 8 | lr_step_off | 0.00000 | 32 | 31: lr | 0.12487 | 0.11835 | 0.32369 | -0.11589 | 0.5 | None |
| 8 | 8 | weights_eps | 0.00429 | 31 | none | 0.15221 | 0.22356 | 0.54722 | -0.22356 | 0.9 | 31 |
