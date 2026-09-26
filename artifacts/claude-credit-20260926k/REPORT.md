# Vast money check — read-only

Check time (date -u): Sat Sep 26 19:32:56 UTC 2026

## User credit
- credit: 33.56528316436976
- balance: 0

## Instances (vastai show instances --raw, 3 instances)

### 52755827
- label: claude-director-depot
- actual_status: exited
- cur_state: stopped
- intended_status: stopped
- status_msg: Done copying
- dph_total: 0.11361111111111112
- dph_base: 0.10666666666666667
- start_date: Sat Sep 26 13:45:29 UTC 2026
- duration_sec: 20846.66199874878
- hours_so_far: 5.790739444096883
- dph_total_x_hours: 0.6578923423987848

### 52799251
- label: claude-fixsleep-dl7b
- actual_status: running
- cur_state: running
- intended_status: running
- dph_total: 0.41666666666666663
- dph_base: 0.39999999999999997
- start_date: Sat Sep 26 18:42:52 UTC 2026
- duration_sec: 3004.120032787323
- hours_so_far: 0.8344777868853675
- dph_total_x_hours: 0.3476990778689031

### 52807320
- label: claude-sleep-358t3
- actual_status: loading
- cur_state: running
- intended_status: running
- dph_total: 0.44814814814814813
- dph_base: 0.39999999999999997
- start_date: Sat Sep 26 19:32:30 UTC 2026
- duration_sec: 25.381617546081543
- hours_so_far: 0.007050449318355984
- dph_total_x_hours: 0.0031596458056336076

Method: hours_so_far = duration_sec / 3600; cost = dph_total * hours_so_far. Read-only; rented nothing, destroyed nothing, changed nothing.
