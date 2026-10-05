# Fixed TRAIN-only continuation to visit40

Both looping seeds met the fixed TRAIN target244/256. This is a TRAIN fit result; unfamiliar-question improvement remains untested by this run. The original consumed-panel failed capability verdict is unchanged. The conditional LR fork is skipped.

| Seed | Arm | Visit20 TRAIN | Visit40 TRAIN | Mean endpoint numeric CE | Optimizer seconds | Additional updates/s |
|---|---|---:|---:|---:|---:|---:|
| 0 | loop | 194 | 250 | 0.04903622 | 585.147 | 8.750 |
| 0 | plain | 214 | 254 | 0.01733363 | 688.667 | 7.435 |
| 1 | loop | 98 | 244 | 0.07741436 | 551.869 | 9.278 |
| 1 | plain | 185 | 245 | 0.05526856 | 686.141 | 7.462 |

All4 checkpoint fullSHA256s match CLOSED; every arm has exactly5120 additional optimizer updates,10240 global updates and40 visits for every256 TRAIN row. Each arm exited0 andclosedtrue. The independent saved-record verifier made0 model/optimizer calls and verified96 original training/evaluation artifact hashes unchanged. No nonfinite records. All3072 saved TRAIN diagnostic generations emitted EOS. Fixedvisit40 endpoints were used, including loop0=250 rather than its visit30=252.

The serial runner interval was4659.053 seconds (77m39.053s), including diagnostics/loading/closure; matrix20480 optimizer updates / this wall time =4.396updates/s. Optimizer-only time is separately shown above. Training stopped at01:06:51.714274UTC.

Literal continuation preserved Adam state/parameter mapping/RNG, repeated the original finite TRAIN order exactly once, and kept constantLR0.001,zero weight_decay,masks/targets/4loops/architecture unchanged. The original matrix is retained; the separate continuation matrix had the same1,140,850,688-byte new-output allowance, project100GiB cap and1GiB free reserve.

Original sparse TRAIN audit found no teacherforced/nativegeneration item disagreement atvisits3/10/20 and no dominant observed retention problem; this does not exclude intrapass forgetting. CE/accuracy improvement supports additional fitting; it does not establish model advantage or a mechanism.

Success successor: presealed fresh64 new-story/seen-footprint, sameeightfixed20/40 endpoints, paired counts; partialcomponent only. Failure successor (.0003 TRAIN LR tail) remains a preserved draft and is not released because bothloop controls passed. Remaining structural/range source policy is frozen before fresh predictions; new Luna sources are disclosed.
