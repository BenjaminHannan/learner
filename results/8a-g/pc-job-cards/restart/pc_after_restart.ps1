# Started detached by g1recover.ps1 after Ben's PC restart (11 Oct 2026; spec addendum AC), or by nog1_go.ps1 after it stops the G1 reruns
# (12 Oct; addendum AE: it renames g1recover-plan.json aside first, so step 2 below finds no plan). Log WORK\q8aG1recover.log.
#   1. The install (install_rr.ps1 in this folder, with its own checks; output WORK\in-rr2-install.txt) while the PC's memory is still free,
#      then agent\install_agent.ps1 if present (AT-1 + G2Q; output WORK\in-agent-install.txt). Its result does not hold G1 back.
#      With NO-G1-RERUN.txt here (Ben, 1:17 AM ET 12 Oct; addendum AE) no G1 arm reruns: WORK\G1-DONE.txt is written after a clean install_rr.
#   2. G1's reruns from WORK\g1recover-plan.json: s400 (8aG1fR) first. s401 (8aG1s401r) starts beside it only once s400 trains and the
#      PC has room (free commit >= s400's python memory + 4 GB, GPU memory used <= 9,000 MiB; two runs on the card is how G1 ran before),
#      else when s400's runner ends. Each start writes q<Q>_run.cmd and its card in pc-jobs, as the G1 waiters did.
# It stops nothing and deletes nothing.
$IN   = Split-Path -Parent $MyInvocation.MyCommand.Path
$CIO  = 'C:\Users\benja\custom-io'
$WORK = "$CIO\work"
$SRC  = "$CIO\src-8ag"
$JOBS = 'C:\Users\benja\pc-jobs'
$PY   = 'C:\Users\benja\AppData\Local\Programs\Python\Python310\python.exe'
$RLOG = "$WORK\q8aG1recover.log"
$CAPS = '3DA2DFBB0DDDE64F0B4A263CCC025A01E70CA35C7C69FD9E9FDBB9C2D2325F78'
function Say($m) { "$((Get-Date).ToString('yyyy-MM-dd HH:mm:ss')) ET $m" | Add-Content -Encoding ascii $RLOG }
function Py($pat) { @(Get-CimInstance Win32_Process -Filter "Name like 'python%'" | Where-Object { $_.CommandLine -like $pat }) }
function Runner($q) { @(Py "*local_runner*queue_local\$q-pc.txt*").Count -gt 0 }
function FreeMB { [math]::Floor((Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory / 1024) }
function GpuUsedMiB { $v = "$(& nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>$null)".Trim(); if ($v -match '^\d+') { [int]$Matches[0] } else { 99999 } }
function Start-G1($q, $card) {
  if (Test-Path "$WORK\STOP") { Say "WORK\STOP exists: $q NOT started, NEEDS ATTENTION"; return $false }
  if ((Get-FileHash "$SRC\custom_io\g8a\caps.py").Hash -ne $CAPS) { Say "caps.py hash wrong in src-8ag: $q NOT started, NEEDS ATTENTION"; return $false }
  if (Runner $q) { Say "$q already has a runner: not started again"; return $true }
  Set-Content -Encoding ascii "$CIO\q${q}_run.cmd" -Value @(
    '@echo off',
    'set PYTHONUTF8=1',
    'set PYTHONUNBUFFERED=1',
    "cd /d $SRC",
    "$PY -m custom_io.local_runner run --work $WORK --queue custom_io\queue_local\$q-pc.txt --device cuda --par 1 --busy C:\Users\benja\GPU-BUSY.txt >> $WORK\q$q.log 2>&1")
  $r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine="cmd.exe /c $CIO\q${q}_run.cmd"}
  Say "started $q (ReturnValue $($r.ReturnValue), cmd pid $($r.ProcessId)); log WORK\q$q.log"
  if (Test-Path "$CIO\$card.template.md") {
    (Get-Content "$CIO\$card.template.md") -replace '@STARTED@', "$((Get-Date).ToString('yyyy-MM-dd HH:mm:ss')) ET" | Set-Content -Encoding ascii "$JOBS\$card.md"
    Say "installed pc-jobs\$card.md"
  }
  return $true
}

Say "pc_after_restart started (pid $PID)"
# 1. The install.
$rrok = $false
if (Test-Path "$IN\install_rr.ps1") {
  Say "install_rr.ps1 running (free to commit $(FreeMB) MB); output WORK\in-rr2-install.txt"
  & powershell -NoProfile -ExecutionPolicy Bypass -File "$IN\install_rr.ps1" 2>&1 | ForEach-Object { "$_" } | Out-File -Encoding ascii "$WORK\in-rr2-install.txt"
  $out = @(Get-Content "$WORK\in-rr2-install.txt")
  $fails = @($out | Where-Object { $_ -like 'FAILED*' })
  $rrok = (-not $fails.Count) -and @($out | Where-Object { $_ -like 'INSTALL RR DONE*' }).Count -gt 0
  Say "install_rr.ps1 ended: $(if ($fails.Count) { $fails -join ' | ' } else { 'no FAILED line' }); last line: $($out | Select-Object -Last 1)"
} else { Say 'no install_rr.ps1 here: install skipped' }
# 1b. The talker thread's AT-1 and G2Q (spec addendum AD), after install_rr (they need waiter v3e). Their result does not hold the chain back:
#     they can be installed again later, until G2f ends.
if (Test-Path "$IN\agent\install_agent.ps1") {
  Say "install_agent.ps1 running (free to commit $(FreeMB) MB); output WORK\in-agent-install.txt"
  & powershell -NoProfile -ExecutionPolicy Bypass -File "$IN\agent\install_agent.ps1" 2>&1 | ForEach-Object { "$_" } | Out-File -Encoding ascii "$WORK\in-agent-install.txt"
  $out = @(Get-Content "$WORK\in-agent-install.txt")
  $fails = @($out | Where-Object { $_ -like 'FAILED*' })
  Say "install_agent.ps1 ended: $(if ($fails.Count) { ($fails -join ' | ') + ', NEEDS ATTENTION' } else { 'no FAILED line' }); last line: $($out | Select-Object -Last 1)"
}

# 2. G1.
$plan = $null
try { $plan = Get-Content "$WORK\g1recover-plan.json" -Raw -ErrorAction Stop | ConvertFrom-Json } catch { }
$qs = @(); if ($plan) { $qs = @($plan.PSObject.Properties | ForEach-Object { $_.Name }) }
if (-not $qs.Count -and (Test-Path "$IN\NO-G1-RERUN.txt")) {
  # No G1 rerun (Ben, 1:17 AM ET 12 Oct): the chain starts once the new code is in. Only after a clean install_rr, so the chain never starts
  # on the old code; otherwise it waits (NEEDS ATTENTION) and the install is run again.
  if ($rrok) {
    Set-Content -Encoding ascii "$WORK\G1-DONE.txt" -Value @("G1 ended without reruns: Ben, 1:17 AM ET 12 Oct, ""I don't think you should rerun g1, it's not worth it"" (spec addendum AE)",
      "written by pc_after_restart.ps1 $((Get-Date).ToString('yyyy-MM-dd HH:mm:ss')) ET after install_rr.ps1 ended with INSTALL RR DONE")
    Say 'G1 not rerun (NO-G1-RERUN.txt): wrote WORK\G1-DONE.txt; the post-G1 chain starts after 5 quiet minutes'
  } else { Say 'G1 not rerun, but install_rr.ps1 did not end with INSTALL RR DONE: WORK\G1-DONE.txt NOT written, the chain waits, NEEDS ATTENTION' }
  exit
}
if (-not $qs.Count) { Say 'no G1 rerun planned: done'; exit }
$s400 = $qs -contains '8aG1fR'; $s401 = $qs -contains '8aG1s401r'
if ($s400) { $null = Start-G1 '8aG1fR' 'g1fr' }
if (-not $s401) { Say 'only s400 to rerun: done'; exit }
if (-not $s400) { $null = Start-G1 '8aG1s401r' 'g1s401r'; Say 'done'; exit }

# s401 beside s400 only when s400 trains and there is room; else after s400.
$t0 = Get-Date; $beside = $false
while (((Get-Date) - $t0).TotalMinutes -lt 90) {
  Start-Sleep -Seconds 60
  if (-not (Runner '8aG1fR')) { Say 's400 runner is not running (ended or failed): s401 starts now, alone'; break }
  $tr = @(Py '*custom_io.train*8aG1fR*')
  $st = @(Get-ChildItem "$WORK\results\8aG1fR-pc\8aG1fR-10M-s400\*\stdout.txt" -ErrorAction SilentlyContinue | Where-Object { Select-String -Path $_.FullName -Pattern '"event": "train"' -SimpleMatch -Quiet })
  if (-not ($tr.Count -and $st.Count)) { continue }
  Start-Sleep -Seconds 120      # let its memory settle
  $mine = 0
  foreach ($p in @(Py '*8aG1fR*')) { $g = Get-Process -Id $p.ProcessId -ErrorAction SilentlyContinue; if ($g) { $mine += $g.PrivateMemorySize64 } }
  $mine = [math]::Ceiling($mine / 1MB); $free = FreeMB; $gpu = GpuUsedMiB
  if ($free -ge $mine + 4096 -and $gpu -le 9000) { $beside = $true; Say "s400 trains (its python memory $mine MB; free to commit $free MB; GPU used $gpu MiB): s401 starts beside it" }
  else { Say "s400 trains (its python memory $mine MB; free to commit $free MB; GPU used $gpu MiB): not enough room, s401 starts after s400" }
  break
}
if (-not $beside) {
  while (Runner '8aG1fR') { Start-Sleep -Seconds 60 }
  Start-Sleep -Seconds 30
}
$null = Start-G1 '8aG1s401r' 'g1s401r'
Say 'done'
