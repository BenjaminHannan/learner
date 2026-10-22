#!/usr/bin/env bash
# hostmon.sh OUT.csv [PERIOD_S] [PID_PATTERN]: the GPU-RUN-4 host monitor (condition 3). One CSV row every PERIOD_S seconds (default 10) until killed:
#   utc, epoch, gpu_sm_mhz, gpu_mem_mhz, gpu_power_w, gpu_temp_c, gpu_util_pct, gpu_mem_used_mib, throttle_active (hex bitmask, 0x0 or 0x1 = none/idle),
#   cpu_steal_pct (over the period, whole box, from /proc/stat), load1, trainer_pid, trainer_cpu (the core the trainer last ran on, /proc/PID/stat field 39),
#   trainer_cpu_mhz (that core's current MHz: cpufreq scaling_cur_freq, else /proc/cpuinfo), trainer_cpu_pct (trainer CPU time over the period, 100 = one core)
# The trainer is the newest process whose command line matches PID_PATTERN (default 'python[0-9.]* .*prof_launch[.]py': the python process itself, never a wrapper shell or this script). A column that cannot be read is "NA" (e.g. no nvidia-smi on a CPU dry run).
# Plain bash + coreutils + awk; no python, so it cannot disturb the trainer's interpreter. Written 2026-10-16/17 for PREREG-launch-defer.md mark 3.
set -u
OUT=${1:?usage: hostmon.sh OUT.csv [PERIOD_S] [PID_PATTERN]}
P=${2:-10}
PAT=${3:-python[0-9.]* .*prof_launch[.]py}
HZ=$(getconf CLK_TCK 2>/dev/null || echo 100)
echo "utc,epoch,gpu_sm_mhz,gpu_mem_mhz,gpu_power_w,gpu_temp_c,gpu_util_pct,gpu_mem_used_mib,throttle_active,cpu_steal_pct,load1,trainer_pid,trainer_cpu,trainer_cpu_mhz,trainer_cpu_pct" > "$OUT"

cpustat() { awk '/^cpu /{t=0; for(i=2;i<=NF;i++) t+=$i; print t, $9}' /proc/stat; }   # total jiffies, steal jiffies
read -r T0 S0 < <(cpustat)
PJ0=""; PID0=""
while true; do
  sleep "$P"
  NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ); EP=$(date +%s)
  if command -v nvidia-smi >/dev/null 2>&1; then
    G=$(nvidia-smi --query-gpu=clocks.sm,clocks.mem,power.draw,temperature.gpu,utilization.gpu,memory.used,clocks_throttle_reasons.active --format=csv,noheader,nounits 2>/dev/null | head -1 | tr -d ' ')
    [ -n "$G" ] || G="NA,NA,NA,NA,NA,NA,NA"
  else
    G="NA,NA,NA,NA,NA,NA,NA"
  fi
  read -r T1 S1 < <(cpustat)
  DT=$((T1 - T0)); STEAL=NA
  [ "$DT" -gt 0 ] && STEAL=$(awk -v s=$((S1 - S0)) -v d=$DT 'BEGIN{printf "%.2f", 100*s/d}')
  T0=$T1; S0=$S1
  L1=$(cut -d' ' -f1 /proc/loadavg)
  PID=$(pgrep -n -f "$PAT" 2>/dev/null || true)
  TC=NA; MHZ=NA; PCT=NA
  if [ -n "$PID" ] && [ -r "/proc/$PID/stat" ]; then
    ST=$(sed 's/^.*) //' "/proc/$PID/stat")                     # fields after "(comm) ": field 3 of the man page is $1 here
    TC=$(echo "$ST" | awk '{print $37}')                         # man proc field 39 (processor) = $37 after dropping pid and comm
    PJ=$(echo "$ST" | awk '{print $12 + $13}')                   # utime + stime (fields 14, 15)
    if [ -r "/sys/devices/system/cpu/cpu$TC/cpufreq/scaling_cur_freq" ]; then
      MHZ=$(awk '{printf "%.0f", $1/1000}' "/sys/devices/system/cpu/cpu$TC/cpufreq/scaling_cur_freq")
    else
      MHZ=$(awk -v c="$TC" '/^processor/{p=$3} /^cpu MHz/{if(p==c){printf "%.0f", $4; exit}}' /proc/cpuinfo)
      [ -n "$MHZ" ] || MHZ=NA
    fi
    if [ "$PID" = "$PID0" ] && [ -n "$PJ0" ]; then
      PCT=$(awk -v a=$((PJ - PJ0)) -v hz="$HZ" -v p="$P" 'BEGIN{printf "%.1f", 100*a/hz/p}')
    fi
    PJ0=$PJ; PID0=$PID
  else
    PID=NA; PJ0=""; PID0=""
  fi
  echo "$NOW,$EP,$G,$STEAL,$L1,$PID,$TC,$MHZ,$PCT" >> "$OUT"
done
