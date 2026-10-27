GPU: no (read-only look at BensPC; ignore GPU-BUSY.txt). LOAD-LIGHT: yes
Director probe, read-only. Change nothing, stop nothing, start nothing.
1. `timeout 30 ssh -o ConnectTimeout=10 -o BatchMode=yes benspc "nvidia-smi; type C:\Users\benja\GPU-BUSY.txt; Get-Process python* -ErrorAction SilentlyContinue | Select Id,StartTime,CPU,Path | Format-Table -Auto; Get-CimInstance Win32_Process -Filter \"Name like 'python%'\" | Select ProcessId,CommandLine | Format-List"` and print the output (command lines are fine; if a line holds a key or token, replace it with [removed]).
2. Report as a table: PID, start time, script name + key args (seed, run name), GPU memory. Say which match 358s (loop-s9, plain-s9, loop-s10) and which match rv390.
