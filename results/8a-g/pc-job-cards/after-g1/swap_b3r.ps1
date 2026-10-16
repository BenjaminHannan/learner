# Swaps src-b3r to a newer PR #56 build before any B3 run. It renames the old folder aside (never deletes it), then reruns upgrade_post_g1.ps1,
# which sets up src-b3r from post-g1-in\b3r.zip with its CPU checks (cap 32, test_g8a, test_b3_run) and refreshes the queue files and readout.
# It refuses if a B3 queue runner is running or any B3 result folder exists. It starts no GPU work, and the waiter keeps running.
$CIO = 'C:\Users\benja\custom-io'
$busy = @(Get-CimInstance Win32_Process -Filter "Name like 'python%'" | Where-Object { $_.CommandLine -like '*local_runner*' -and $_.CommandLine -like '*8aB3G1*' })
if ($busy.Count -gt 0) { 'NEEDS ATTENTION: a B3 queue runner is running: not swapping'; exit 1 }
if (@(Get-ChildItem "$CIO\work\results\8aB3G1*" -ErrorAction SilentlyContinue).Count -gt 0) { 'NEEDS ATTENTION: B3 has already started (work\results\8aB3G1* exists): not swapping'; exit 1 }
if (-not (Test-Path "$CIO\post-g1-in\b3r.zip")) { 'NEEDS ATTENTION: post-g1-in\b3r.zip missing'; exit 1 }
if (Test-Path "$CIO\src-b3r") {
  $n = 'src-b3r.before-' + (Get-Date).ToString('yyyyMMdd-HHmm')
  Rename-Item -Path "$CIO\src-b3r" -NewName $n
  "renamed src-b3r to $n (kept)"
}
& powershell -NoProfile -ExecutionPolicy Bypass -File "$CIO\post-g1-in\upgrade_post_g1.ps1"
'--- src-b3r\B3R-SETUP-OK.txt:'
Get-Content "$CIO\src-b3r\B3R-SETUP-OK.txt" -ErrorAction SilentlyContinue
'--- waiter log:'
Get-Content "$CIO\work\q8aPost-waiter.log" -Tail 2 -ErrorAction SilentlyContinue
