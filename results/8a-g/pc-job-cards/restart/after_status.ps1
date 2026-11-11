# Read-only status after g1recover.ps1 (spec addendum AC): the install's output, the recovery log, the waiter log, G1's runners and GPU.
$W = 'C:\Users\benja\custom-io\work'
'== install (WORK\in-rr2-install.txt)'
Get-Content "$W\in-rr2-install.txt" -ErrorAction SilentlyContinue
'== AT-1 + G2Q install (WORK\in-agent-install.txt)'
Get-Content "$W\in-agent-install.txt" -ErrorAction SilentlyContinue
"== WORK\G1-DONE.txt: $(if (Test-Path "$W\G1-DONE.txt") { (@(Get-Content "$W\G1-DONE.txt") -join ' | ') } else { 'none' })"
'== recovery log, last 15'
Get-Content "$W\q8aG1recover.log" -Tail 15 -ErrorAction SilentlyContinue
'== post-G1 waiter log, last 6'
Get-Content "$W\q8aPost-waiter.log" -Tail 6 -ErrorAction SilentlyContinue
'== G1 queue logs, last 3 each'
foreach ($q in @('8aG1fR', '8aG1s401r')) { "-- q$q.log"; Get-Content "$W\q$q.log" -Tail 3 -ErrorAction SilentlyContinue }
'== python processes'
Get-CimInstance Win32_Process -Filter "Name like 'python%'" | ForEach-Object { "  $($_.ProcessId) $($_.CommandLine)" }
'== memory and GPU'
$os = Get-CimInstance Win32_OperatingSystem
"free to commit $([math]::Floor($os.FreeVirtualMemory / 1024)) MB of $([math]::Floor($os.TotalVirtualMemorySize / 1024)) MB"
nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader
