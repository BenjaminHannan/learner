# setup.ps1 - one-time, idempotent setup of Glim's Bedwars folder on BensPC.   usage: setup.ps1 [-DryRun]
# Creates C:\Users\benja\glim-bedwars\{server,bridge,shots,logs}; copies the Paper 1.8.8 + BedWars1058 server from
# bedwars-189 (read-only source; world_the_end, logs and player data are left out; sizes are reported); gives our copy
# its own ports; copies these scripts and deskhelper.exe into place; builds GlimTruthKit (our truth-log plugin) and puts it in OUR
# server copy only; (re-)registers the GlimBridge task (hidden, via bridge-launch.vbs); PRINTS the authorized_keys forced-command
# line for Glim's key (never installs it). Never starts anything, never reboots.
param([switch]$DryRun)
$ErrorActionPreference = 'Stop'
$Root = 'C:\Users\benja\glim-bedwars'
$Src  = 'C:\Users\benja\bedwars-189'
$Here = $PSScriptRoot
$FloorGB = 15
function Say($m) { Write-Host $m }
function Do-It([string]$what, [scriptblock]$act) { if ($DryRun) { Say "  [dry-run] would: $what" } else { Say "  $what"; & $act } }
function MB($p) { if (Test-Path -LiteralPath $p) { [math]::Round(((Get-ChildItem -LiteralPath $p -Recurse -File -Force -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum) / 1MB, 1) } else { 0 } }

Say ("== glim-bedwars setup" + $(if ($DryRun) { ' (DRY RUN: nothing is changed)' } else { '' }))
$free = [math]::Round((Get-PSDrive C).Free / 1GB, 1)
Say "disk: $free GB free on C: (floor $FloorGB GB)"
if ($free -lt $FloorGB) { Say 'STOP: below the floor.'; exit 1 }
if (-not (Test-Path -LiteralPath (Join-Path $Src 'server\paper-1.8.8-445.jar'))) { Say "STOP: source server not found in $Src"; exit 1 }

Say '1. folders'
foreach ($d in 'server', 'bridge', 'shots', 'logs') {
  $p = Join-Path $Root $d
  if (Test-Path -LiteralPath $p) { Say "  exists: $p" } else { Do-It "create $p" { New-Item -ItemType Directory -Force -Path $p | Out-Null } }
}

Say '2. server copy (source stays read-only)'
$S = Join-Path $Src 'server'; $D = Join-Path $Root 'server'
foreach ($n in 'world', 'duel', 'squad', 'plugins', 'cache') { Say ("  source {0,-8} {1,7} MB" -f $n, (MB (Join-Path $S $n))) }
Say ("  left out: world_the_end {0} MB, logs, playerdata, console-*.txt, usercache/ops/banned lists" -f (MB (Join-Path $S 'world_the_end')))
if (Test-Path -LiteralPath (Join-Path $D 'paper-1.8.8-445.jar')) { Say '  server copy already there: skipping the copy (idempotent)' }
else {
  Do-It 'robocopy server -> glim-bedwars\server' {
    & robocopy.exe $S $D /E /R:1 /W:1 /NFL /NDL /NJH /NJS /XD world_the_end logs playerdata /XF console-*.txt usercache.json ops.json banned-*.json session.lock | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "robocopy failed with code $LASTEXITCODE" }
  }
}
$props = Join-Path $D 'server.properties'
Do-It 'set our own ports in OUR server.properties: server-port=25567, rcon.port=25577, rcon.password=glim-local, motd' {
  $t = Get-Content -LiteralPath $props
  $t = $t -replace '^server-port=.*', 'server-port=25567' -replace '^rcon.port=.*', 'rcon.port=25577' -replace '^rcon.password=.*', 'rcon.password=glim-local' -replace '^motd=.*', 'motd=Glim Bedwars (local)' -replace '^enable-rcon=.*', 'enable-rcon=true'
  Set-Content -LiteralPath $props -Value $t -Encoding ASCII
}
Do-It 'start with an empty pids.json' { if (-not (Test-Path -LiteralPath (Join-Path $Root 'pids.json'))) { Set-Content -LiteralPath (Join-Path $Root 'pids.json') -Value '{}' -Encoding ASCII } }

Say '3. our scripts and deskhelper.exe'
$files = 'glimtool.ps1', 'bridge.ps1', 'bridge-launch.vbs', 'launch-client.ps1', 'bridge-task.xml', 'runbook.json', 'RUNBOOK.md', 'setup.ps1'
$same = ([IO.Path]::GetFullPath($Here)).TrimEnd('\') -ieq $Root
if ($same) { Say '  scripts already run from the glim-bedwars folder' }
else {
  foreach ($f in $files) { if (Test-Path -LiteralPath (Join-Path $Here $f)) { Do-It "copy $f -> $Root" { Copy-Item -LiteralPath (Join-Path $Here $f) -Destination (Join-Path $Root $f) -Force } } }
  $dh = Join-Path $Here 'bridge\deskhelper.exe'; if (-not (Test-Path -LiteralPath $dh)) { $dh = Join-Path $Here 'deskhelper.exe' }
  if (Test-Path -LiteralPath $dh) { Do-It 'copy deskhelper.exe -> bridge\' { Copy-Item -LiteralPath $dh -Destination (Join-Path $Root 'bridge\deskhelper.exe') -Force } }
  else { Say '  note: deskhelper.exe not found next to this script (deploy.sh puts it in bridge\)' }
}
if (-not (Test-Path -LiteralPath (Join-Path $Root 'bridge\deskhelper.exe')) -and $same) { Say '  note: bridge\deskhelper.exe is missing (run deploy.sh)' }

Say '4. GlimTruthKit (truth log, auto-join, match start/stop) -> OUR server copy only'
$tkb = Join-Path $Root 'truthkit\build.ps1'
if (-not (Test-Path -LiteralPath $tkb)) { Say '  note: truthkit\build.ps1 is missing (run deploy.sh); the truth log will not exist' }
else {
  Do-It 'build GlimTruthKit.jar and install it into server\plugins' {
    $o = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $tkb -Install 2>&1
    $o | ForEach-Object { Say ('    ' + $_) }
    if (-not ($o -match '^BUILD OK')) { throw 'GlimTruthKit build failed' }
  }
}

Say '5. bridge task (GlimBridge, InteractiveToken, only when logged on, no window)'
if (-not (Test-Path -LiteralPath (Join-Path $env:WINDIR 'System32\wscript.exe'))) { Say '  WARNING: wscript.exe not found; the bridge task cannot start hidden' }
$xml = Join-Path $Root 'bridge-task.xml'; if (-not (Test-Path -LiteralPath $xml)) { $xml = Join-Path $Here 'bridge-task.xml' }
cmd.exe /c "schtasks /query /tn GlimBridge >nul 2>&1"
$had = ($LASTEXITCODE -eq 0)
# registered from the XML text (not schtasks /xml: the file is ASCII but says UTF-16); -Force replaces our own older definition
Do-It ($(if ($had) { 're-register' } else { 'register' }) + " task GlimBridge from $xml") { Register-ScheduledTask -TaskName 'GlimBridge' -Xml (Get-Content -Raw -LiteralPath $xml) -Force | Out-Null }

Say '6. SSH key line for Glim (NOT installed by this script)'
$isAdmin = $false; try { $isAdmin = [bool]((& net.exe localgroup Administrators 2>$null) -match '\\benja$|^benja$') } catch { }
$cmd = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\Users\benja\glim-bedwars\glimtool.ps1'
Say '  add this ONE line (replace <GLIM_PUBKEY> with Glim''s public key, e.g. "ssh-ed25519 AAAA... glim"):'
Say ('  command="' + $cmd + '",no-port-forwarding,no-X11-forwarding,no-agent-forwarding,no-pty <GLIM_PUBKEY>')
if ($isAdmin) { Say '  benja is an Administrator, so Windows OpenSSH reads C:\ProgramData\ssh\administrators_authorized_keys (not benja''s own file).' }
else { Say '  benja is not an Administrator, so the line goes in C:\Users\benja\.ssh\authorized_keys.' }
Say 'done.'
