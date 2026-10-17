# GPU-RUN-4 readout against PREREG-launch-defer.md

outcome (section 5): **a box failed mark 5 (or its AA is undecided): nothing on that box counts; undecided**

## Mark 2 (same maths, box 1)

- defer: bar True (fp32: rel loss 0.0, grad cos 0.9999999999999909); E4 {'passed': False, 'registered_window': False, 'mean_abs_diff': 0.0, 'diff_of_means': 0.0, 'updates': 6}; holds None; numerics-changing
- kvcat: holds True (baseline rerun bitwise in fp32: kvcat must be bitwise); exact-candidate (treated as numbers-changing in this run)

## Mark 7 (mechanism, box 1 profiler)

- holds None; defer syncs None (base None), DtoH None (base None), kernels None / None = None, kernel ms ratio None

## Box 1: vm | Intel(R) Xeon(R) Processor @ 2.10GHz | torch 2.11.0+cpu cuda None | machine dry1 | image local

references {"base4": 0.7849, "defer4": 0.448, "kvdefer4": 0.439, "base8": 1.5933, "defer8": 0.6984}; host monitor {'samples': 21, 'trainer_mhz_median': 2100.0, 'rule_e_struck': False, 'gpu_util_median': None}; mark 5 (AA) None (None); box counts: False

| arm | status | read rounds | A median | B median | speed | all B<A | peak B GB | mark 1 |
|---|---|---|---|---|---|---|---|---|
| d4 | regime-confounded | 0 | - | - | - | - | - | - |
| aa | regime-confounded | 0 | - | - | - | - | - | - |
| k4 (secondary) | regime-confounded | 0 | - | - | - | - | - | - |
| d8 (secondary) | regime-confounded | 0 | - | - | - | - | - | - |

- d4 round 1 not read: A ['(b) chunk 1 0.6455 / median 0.6096 = 1.059', '(b) chunk 2 0.9431 / median 1.0099 = 0.934']; B ['(a) 0.5215 > 1.1 x ref 0.4480', '(b) chunk 1 0.4865 / median 0.4036 = 1.205', '(b) chunk 2 0.5566 / median 0.5885 = 0.946']; mark 4 True
- d4 round 2 not read: A ok; B ['(b) chunk 1 0.3594 / median 0.4036 = 0.890', '(b) chunk 2 0.5366 / median 0.5885 = 0.912']; mark 4 True
- d4 round 3 not read: A ['(b) chunk 1 0.5715 / median 0.6096 = 0.938']; B ['(b) chunk 1 0.3341 / median 0.4036 = 0.828']; mark 4 True
- aa round 1 not read: A ['(a) 0.9380 > 1.1 x ref 0.7849', '(b) chunk 1 0.6884 / median 0.6096 = 1.129', '(b) chunk 2 1.1876 / median 1.0099 = 1.176']; B ok; mark 4 True
- aa round 2 not read: A ['(a) 0.8712 > 1.1 x ref 0.7849', '(b) chunk 1 0.6623 / median 0.6096 = 1.086', '(b) chunk 2 1.0802 / median 1.0099 = 1.070']; B ok; mark 4 True
- aa round 3 not read: A ok; B ['(a) 0.8658 > 1.1 x ref 0.7849', '(b) chunk 1 0.7420 / median 0.6096 = 1.217']; mark 4 True
- k4 round 1 not read: A ['(b) chunk 1 0.3706 / median 0.4036 = 0.918']; B ['(a) 0.5180 > 1.1 x ref 0.4390']; mark 4 True
- k4 round 2 not read: A ['(a) 0.5705 > 1.1 x ref 0.4480', '(b) chunk 1 0.4367 / median 0.4036 = 1.082', '(b) chunk 2 0.7043 / median 0.5885 = 1.197']; B ['(a) 0.5368 > 1.1 x ref 0.4390', '(b) chunk 1 0.4373 / median 0.3726 = 1.174']; mark 4 True
- k4 round 3 not read: A ['(a) 0.5417 > 1.1 x ref 0.4480', '(b) chunk 1 0.4564 / median 0.4036 = 1.131', '(b) chunk 2 0.6270 / median 0.5885 = 1.065']; B ['(b) chunk 2 0.5151 / median 0.6364 = 0.809']; mark 4 True
- d8 round 1 not read: A ['(a) 1.8568 > 1.1 x ref 1.5933', '(b) chunk 1 2.0671 / median 1.6019 = 1.290']; B ['(b) chunk 1 0.6684 / median 0.7827 = 0.854', '(b) chunk 2 0.7284 / median 0.7775 = 0.937']; mark 4 True
- d8 round 2 not read: A ok; B ['(a) 0.9022 > 1.1 x ref 0.6984', '(b) chunk 1 0.9080 / median 0.7827 = 1.160', '(b) chunk 2 0.8964 / median 0.7775 = 1.153']; mark 4 True
- d8 round 3 not read: A ok; B ['(a) 0.7801 > 1.1 x ref 0.6984', 'no host-monitor sample in the timed window']; mark 4 True

## Box 2: vm | Intel(R) Xeon(R) Processor @ 2.10GHz | torch 2.11.0+cpu cuda None | machine dry2 | image local

references {"base4": 0.8275, "defer4": 0.5069, "kvdefer4": null, "base8": null, "defer8": null}; host monitor {'samples': 5, 'trainer_mhz_median': 2100.0, 'rule_e_struck': False, 'gpu_util_median': None}; mark 5 (AA) None (None); box counts: False

| arm | status | read rounds | A median | B median | speed | all B<A | peak B GB | mark 1 |
|---|---|---|---|---|---|---|---|---|
| d4 | regime-confounded | 0 | - | - | - | - | - | - |
| aa | regime-confounded | 0 | - | - | - | - | - | - |
| k4 | missing | - | - | - | - | - | - | - |
| d8 | missing | - | - | - | - | - | - | - |

- d4 round 1 not read: A ['(a) 0.9129 > 1.1 x ref 0.8275']; B ['(b) chunk 1 0.4228 / median 0.3974 = 1.064']; mark 4 True
- d4 round 2 not read: A ['(b) chunk 2 1.0096 / median 1.1829 = 0.853']; B ok; mark 4 True
- d4 round 3 not read: A ['(a) 0.9138 > 1.1 x ref 0.8275']; B ['(b) chunk 2 0.6666 / median 0.6168 = 1.081']; mark 4 True
- aa round 1 not read: A ok; B ['(a) 0.9513 > 1.1 x ref 0.8275', '(b) chunk 1 0.6948 / median 0.6501 = 1.069']; mark 4 True
- aa round 2 not read: A ['(a) 0.9886 > 1.1 x ref 0.8275', '(b) chunk 1 0.7251 / median 0.6501 = 1.115', '(b) chunk 2 1.2521 / median 1.1829 = 1.058']; B ['(b) chunk 2 1.0819 / median 1.1829 = 0.915']; mark 4 True
- aa round 3 not read: A ['no host-monitor sample in the timed window']; B ['(a) 0.9232 > 1.1 x ref 0.8275', 'no host-monitor sample in the timed window']; mark 4 True

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
   "speed": null,
   "right": null
  }
 ],
 "P2": {
  "d8": null,
  "d4": null,
  "right": null,
  "secondary": true
 },
 "P3": {
  "k4": null,
  "right": null
 },
 "P4": "not tested in this run (PC)",
 "P5": {
  "base_gb": null,
  "defer_gb": null,
  "right": null
 },
 "K4_peak_gb": null
}
```

P6: {"R": null, "dead": null, "why": "needs the baseline profiled kernel ms and the in-box unprofiled A median"}

## Outcome detail

```
{
 "d4_wins": [
  false,
  false
 ],
 "d4_speeds": [
  null,
  null
 ],
 "boxes_count": [
  false,
  false
 ],
 "replication_hosts_distinct": false,
 "replication_same_env": true,
 "mark7": null,
 "mark2_defer": null,
 "p1_kill_by_box": [
  false,
  false
 ],
 "defer_inefficient_by_box": [
  false,
  false
 ],
 "p6_R": null,
 "p6_dead": null,
 "voided_boxes": [
  1,
  2
 ],
 "allows": "a box failed mark 5 (or its AA is undecided): nothing on that box counts; undecided"
}
```
