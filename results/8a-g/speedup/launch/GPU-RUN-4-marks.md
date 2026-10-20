# GPU-RUN-4 readout against PREREG-launch-defer.md

outcome (section 5): **mark 2 fails for defer: defer is not used however fast**

## Mark 2 (same maths, box 1)

- defer: bar True (bf16: rel loss 3.531162509143189e-06, grad cos 0.9999995764426567); E4 {'passed': False, 'registered_window': True, 'mean_abs_diff': 0.04811040282249451, 'diff_of_means': 0.03501561045646673, 'updates': 300}; holds False; numerics-changing
- kvcat: holds True (fell to the bf16 bar: relabelled near); exact-candidate (treated as numbers-changing in this run)

## Mark 7 (mechanism, box 1 profiler)

- holds True; defer syncs 62.5 (base 1305.0), DtoH 20.0 (base 745.0), kernels 44830.0 / 75966.0 = 0.5901324276650081, kernel ms ratio 0.9603774566241554

## Box 1: c9f54a0290a6 | Intel(R) Xeon(R) Platinum 8352V CPU @ 2.10GHz | torch 2.11.0+cu128 cuda 12.8 | machine 151645 | image pytorch/pytorch:2.11.0-cuda12.8-cudnn9-runtime

references {"base4": 2.3509, "defer4": 1.5512, "kvdefer4": 1.4428, "base8": 3.4127, "defer8": 1.9819}; host monitor {'samples': 395, 'trainer_mhz_median': 2500.0, 'rule_e_struck': False, 'gpu_util_median': 45.0}; mark 5 (AA) True (0.000895918539137952); box counts: True

| arm | status | read rounds | A median | B median | speed | all B<A | peak B GB | mark 1 |
|---|---|---|---|---|---|---|---|---|
| d4 | regime-confounded | 2 | - | - | - | - | 8.15 | - |
| aa | decided | 3 | 2.4019 | 2.4041 | 0.999 | False | 8.33 | False |
| k4 (secondary) | decided | 3 | 1.5550 | 1.4475 | 1.074 | True | 4.99 | True |
| d8 (secondary) | regime-confounded | 2 | - | - | - | - | 4.36 | - |

- d4 round 3 not read: A ok; B ['(b) chunk 5 1.6715 / median 1.5809 = 1.057']; mark 4 True
- d8 round 1 not read: A ok; B ['(b) chunk 5 2.1052 / median 1.9999 = 1.053']; mark 4 True

## Box 2: c4e54a088b90 | AMD EPYC 9684X 96-Core Processor | torch 2.11.0+cu128 cuda 12.8 | machine 150319 | image pytorch/pytorch:2.11.0-cuda12.8-cudnn9-runtime

references {"base4": 1.7984, "defer4": 1.3315, "kvdefer4": null, "base8": null, "defer8": null}; host monitor {'samples': 102, 'trainer_mhz_median': 2546.0, 'rule_e_struck': False, 'gpu_util_median': 79.5}; mark 5 (AA) True (-0.0018514583820222752); box counts: True

| arm | status | read rounds | A median | B median | speed | all B<A | peak B GB | mark 1 |
|---|---|---|---|---|---|---|---|---|
| d4 | decided | 3 | 1.8093 | 1.3321 | 1.358 | True | 8.15 | False |
| aa | decided | 3 | 1.8038 | 1.8005 | 1.002 | False | 8.33 | False |
| k4 | missing | - | - | - | - | - | - | - |
| d8 | missing | - | - | - | - | - | - | - |


## Predictions

```
{
 "P1": [
  {
   "box": 1,
   "speed": null,
   "right": null
  },
  {
   "box": 2,
   "speed": 1.3582118176748423,
   "right": true
  }
 ],
 "P2": {
  "d8": null,
  "d4": null,
  "right": null,
  "secondary": true
 },
 "P3": {
  "k4": 1.074275696081376,
  "right": true
 },
 "P4": "not tested in this run (PC)",
 "P5": {
  "base_gb": 8.327202796936035,
  "defer_gb": 8.152946949005127,
  "right": true
 },
 "K4_peak_gb": 4.990385055541992
}
```

P6: {"R": 0.5916102373768055, "dead": false, "kernel_ms": 1391.1047424999774, "a_median_s": 2.3513872049748894}

## Outcome detail

```
{
 "d4_wins": [
  false,
  false
 ],
 "d4_speeds": [
  null,
  1.3582118176748423
 ],
 "boxes_count": [
  true,
  true
 ],
 "replication_hosts_distinct": true,
 "replication_same_env": true,
 "mark7": true,
 "mark2_defer": false,
 "p1_kill_by_box": [
  false,
  false
 ],
 "defer_inefficient_by_box": [
  false,
  false
 ],
 "p6_R": 0.5916102373768055,
 "p6_dead": false,
 "voided_boxes": [],
 "allows": "mark 2 fails for defer: defer is not used however fast"
}
```
