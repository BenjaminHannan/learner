# glimtool.ps1 - the single entrypoint for Glim's BensPC tools (contract: ../TOOLS.md, v2).
# Run as the SSH forced command: the verb line comes from $env:SSH_ORIGINAL_COMMAND (else from $args, for local tests).
# Every verb prints ONE JSON line. Errors: {"ok":false,"error":"...","next":[...]}; "next" comes from runbook.json.
# Guardrails: writes only under $Root; stops only pids in pids.json after a command-line check; 15 GB disk floor;
# GPU_LOAN.txt rules; local server only; never types a password; never buys anything. Minecraft is driven from the inside
# (GlimTruthKit commands over RCON, run as the player), never with desktop clicks or typing; the locked screen is never unlocked.
$ErrorActionPreference = 'Stop'
$Root     = 'C:\Users\benja\glim-bedwars'
$Src189   = 'C:\Users\benja\bedwars-189'          # READ-ONLY source of the older track
$GpuLoan  = 'C:\Users\benja\qonly-staging\runs\autopilot\GPU_LOAN.txt'
$Port     = 25567                                  # not 25566, so we never collide with bedwars-189
$RconPort = 25577
$RconPass = 'glim-local'
$FloorGB  = 15
$Who      = 'glim-bedwars'
$TagArg   = '-Dglim.tag=glim-bedwars'
$TagLike  = '*glim.tag=glim-bedwars*'
$PidsFile = Join-Path $Root 'pids.json'
$ShotDir  = Join-Path $Root 'shots'
$BridgeDir = Join-Path $Root 'bridge'
$Runbook  = Join-Path $PSScriptRoot 'runbook.json'

$Verbs = @(
  'ping', 'disk', 'gpu-status', 'gpu-acquire', 'gpu-release',
  'server-start', 'server-stop', 'server-status', 'map-list',
  'match-start', 'match-status', 'match-stop', 'log-read',
  'client-launch', 'client-stop', 'desk', 'fetch'
)
$DeskVerbs = @('look', 'press', 'click', 'type', 'key', 'scroll', 'open-app', 'screenshot')

# ---------- output ----------
function Out-Json($obj, [int]$code = 0) {
  [Console]::Out.WriteLine(($obj | ConvertTo-Json -Compress -Depth 8))
  exit $code
}
function Get-Next([string]$id) {
  $n = @()
  try {
    $rb = Get-Content -Raw -LiteralPath $Runbook | ConvertFrom-Json
    foreach ($s in $rb.steps) { foreach ($e in $s.errors) { if ($e.id -eq $id) {
      foreach ($f in $e.fixes) { if ($f.verb) { $n += [string]$f.verb } else { $n += ('hint: ' + $f.do) } }
      if ($e.askBen) { $n += ('ask-ben: ' + $e.askBenWhy) }
    } } }
  } catch { }
  return , $n
}
function Fail([string]$id, [string]$msg) {
  $o = [ordered]@{ ok = $false; error = $msg; id = $id; next = (Get-Next $id) }
  Out-Json $o 1
}
function Ok($h) { $o = [ordered]@{ ok = $true }; foreach ($k in $h.Keys) { $o[$k] = $h[$k] }; Out-Json $o 0 }

# ---------- small helpers ----------
function Get-ET { $tz = [TimeZoneInfo]::FindSystemTimeZoneById('Eastern Standard Time'); [TimeZoneInfo]::ConvertTime([DateTime]::UtcNow, [TimeZoneInfo]::Utc, $tz).ToString('yyyy-MM-dd HH:mm:ss') + ' ET' }
function Get-FreeGB { [math]::Round((Get-PSDrive C).Free / 1GB, 1) }
function Assert-Disk { $f = Get-FreeGB; if ($f -lt $FloorGB) { Fail 'low-disk' "only $f GB free on C: (floor is $FloorGB GB)" } }
function Test-Under([string]$p) {
  $full = [IO.Path]::GetFullPath($p)
  return ($full.StartsWith($Root + '\', [StringComparison]::OrdinalIgnoreCase))
}
function Remove-Ours([string]$p) {   # the only delete in this tool: files inside our own folder
  $full = [IO.Path]::GetFullPath($p)
  if ($full.StartsWith($Root + '\', [StringComparison]::OrdinalIgnoreCase) -and (Test-Path -LiteralPath $full -PathType Leaf)) { Remove-Item -LiteralPath $full -Force }
}
function Get-Session {
  $u = $null; try { $u = (Get-CimInstance Win32_ComputerSystem).UserName } catch { }
  $locked = [bool](Get-Process -Name LogonUI -ErrorAction SilentlyContinue)
  [ordered]@{ user = $u; signed_in = [bool]$u; locked = $locked }
}
function Get-Pids {
  $h = @{}
  if (Test-Path -LiteralPath $PidsFile) {
    try { $j = Get-Content -Raw -LiteralPath $PidsFile | ConvertFrom-Json; foreach ($p in $j.PSObject.Properties) { $h[$p.Name] = $p.Value } } catch { }
  }
  return $h
}
function Save-Pids($h) {
  if (-not (Test-Path -LiteralPath $Root)) { Fail 'not-set-up' "$Root does not exist yet (setup.ps1 has not run)" }
  ($h | ConvertTo-Json -Compress) | Set-Content -LiteralPath $PidsFile -Encoding ASCII
}
function Get-OursProc([string]$key) {   # returns the process object only if the pid is ours AND its command line carries our tag
  $h = Get-Pids
  if (-not $h.ContainsKey($key) -or -not $h[$key]) { return $null }
  $pidv = [int]$h[$key]
  $p = Get-CimInstance Win32_Process -Filter "ProcessId=$pidv" -ErrorAction SilentlyContinue
  if ($p -and $p.CommandLine -like $TagLike) { return $p }
  return $null
}
function Stop-Ours([string]$key) {
  $p = Get-OursProc $key
  if ($p) { Stop-Process -Id ([int]$p.ProcessId) -Force -ErrorAction SilentlyContinue; return $true }
  return $false
}
function Test-PortListen([int]$port) { [bool](Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue) }
function Get-Maps {
  $d = Join-Path $Root 'server\plugins\BedWars1058\Arenas'
  $src = 'ours'
  if (-not (Test-Path -LiteralPath $d)) { $d = Join-Path $Src189 'server\plugins\BedWars1058\Arenas'; $src = 'bedwars-189 (read-only)' }
  $m = @()
  if (Test-Path -LiteralPath $d) { $m = @(Get-ChildItem -LiteralPath $d -Filter *.yml | ForEach-Object { $_.BaseName }) }
  return @{ maps = $m; source = $src }
}
function Test-Name([string]$s, [string]$what) { if ($s -notmatch '^[A-Za-z0-9_\-]{1,32}$') { Fail 'bad-arg' "bad $what" } }

# ---------- RCON (to OUR server only, 127.0.0.1) ----------
function Invoke-Rcon([string[]]$cmds) {
  $c = New-Object Net.Sockets.TcpClient
  $c.ReceiveTimeout = 6000; $c.SendTimeout = 6000
  $c.Connect('127.0.0.1', $RconPort)
  $s = $c.GetStream()
  $send = {
    param($id, $type, $body)
    $b = [Text.Encoding]::UTF8.GetBytes($body)
    $ms = New-Object IO.MemoryStream; $w = New-Object IO.BinaryWriter($ms)
    $w.Write([int](10 + $b.Length)); $w.Write([int]$id); $w.Write([int]$type); $w.Write($b); $w.Write([byte]0); $w.Write([byte]0); $w.Flush()
    $a = $ms.ToArray(); $s.Write($a, 0, $a.Length)
  }
  $recv = {
    $hdr = New-Object byte[] 4; $n = 0
    while ($n -lt 4) { $r = $s.Read($hdr, $n, 4 - $n); if ($r -le 0) { throw 'rcon closed' }; $n += $r }
    $len = [BitConverter]::ToInt32($hdr, 0); $buf = New-Object byte[] $len; $n = 0
    while ($n -lt $len) { $r = $s.Read($buf, $n, $len - $n); if ($r -le 0) { throw 'rcon closed' }; $n += $r }
    [pscustomobject]@{ id = [BitConverter]::ToInt32($buf, 0); body = [Text.Encoding]::UTF8.GetString($buf, 8, [math]::Max(0, $len - 10)) }
  }
  try {
    & $send 1 3 $RconPass
    $a = & $recv
    if ($a.id -eq -1) { throw 'rcon auth failed' }
    $out = @(); $i = 10
    foreach ($cmd in $cmds) { & $send $i 2 $cmd; $out += (& $recv).body; $i++ }
    return $out
  } finally { $c.Close() }
}
function Get-Players {   # returns @{ok; players=[names]} using the RCON "list" command
  try {
    $r = (Invoke-Rcon @('list'))[0]
    $names = @()
    if ($r -match ':\s*(.*)$') { $names = @($Matches[1] -split ',\s*' | Where-Object { $_ }) }
    return @{ ok = $true; players = $names }
  } catch { return @{ ok = $false; players = @() } }
}
function Invoke-Tk([string]$cmd) {   # GlimTruthKit console command over RCON -> its one-line JSON reply, or $null
  try {
    $b = [string](Invoke-Rcon @("tk $cmd"))[0]; $i = $b.IndexOf('{')
    if ($i -lt 0) { return $null }
    return ($b.Substring($i).Trim() | ConvertFrom-Json)
  } catch { return $null }
}
function Get-Arena($tk, [string]$map) { if (-not $tk) { return $null }; return (@($tk.arenas) | Where-Object { $_.name -eq $map } | Select-Object -First 1) }
function Get-State([string]$s) { switch ($s) { 'waiting' { 'waiting' } 'starting' { 'starting' } 'playing' { 'running' } 'restarting' { 'ended' } default { 'unknown' } } }

# ---------- bridge (desktop steps in benja's signed-in session) ----------
# -Soft: return @{ok=$false; error} instead of failing the verb (ping uses it: a missing bridge must not break ping)
function Invoke-Bridge([string]$action, $args2, [int]$timeoutSec = 30, [switch]$Soft) {
  $s = Get-Session
  if (-not $s.signed_in) { if ($Soft) { return @{ ok = $false; error = 'no signed-in session' } }; Fail 'no-session' 'no signed-in session' }
  if (-not (Test-Path -LiteralPath $BridgeDir)) { if ($Soft) { return @{ ok = $false; error = 'bridge not set up' } }; Fail 'not-set-up' "$BridgeDir does not exist yet (setup.ps1 has not run)" }
  if (-not $Soft) { Assert-Disk }
  $id = [guid]::NewGuid().ToString('N')
  $reqDir = Join-Path $BridgeDir 'req'; $resDir = Join-Path $BridgeDir 'res'
  New-Item -ItemType Directory -Force -Path $reqDir, $resDir | Out-Null
  $req = [ordered]@{ id = $id; action = $action; args = @($args2) }
  $tmp = Join-Path $reqDir ($id + '.tmp'); $final = Join-Path $reqDir ($id + '.json')
  ($req | ConvertTo-Json -Compress -Depth 5) | Set-Content -LiteralPath $tmp -Encoding UTF8
  Move-Item -LiteralPath $tmp -Destination $final
  cmd.exe /c "schtasks /run /tn GlimBridge >nul 2>&1"
  if ($LASTEXITCODE -ne 0) { Remove-Ours $final; if ($Soft) { return @{ ok = $false; error = 'the GlimBridge task is not registered' } }; Fail 'bridge-missing' 'the GlimBridge scheduled task is not registered' }
  $resFile = Join-Path $resDir ($id + '.json')
  $t0 = Get-Date; $end = $t0.AddSeconds($timeoutSec); $kicks = @(3, 8)   # re-run the task once or twice: it may have been exiting (25 s idle) as we wrote
  while ((Get-Date) -lt $end) {
    if (Test-Path -LiteralPath $resFile) {
      Start-Sleep -Milliseconds 100
      $r = Get-Content -Raw -LiteralPath $resFile | ConvertFrom-Json
      Remove-Ours $resFile
      return $r
    }
    if ($kicks.Count -gt 0 -and ((Get-Date) - $t0).TotalSeconds -ge $kicks[0]) { cmd.exe /c "schtasks /run /tn GlimBridge >nul 2>&1"; $kicks = @($kicks | Select-Object -Skip 1) }
    Start-Sleep -Milliseconds 100
  }
  Remove-Ours $final
  if ($Soft) { return @{ ok = $false; error = "the bridge did not answer within $timeoutSec s" } }
  Fail 'bridge-timeout' "the bridge did not answer within $timeoutSec s"
}

# ---------- parse the request ----------
$raw = $env:SSH_ORIGINAL_COMMAND
if (-not $raw) { $raw = ($args -join ' ') }
if (-not $raw -or $raw.Trim() -eq '') { Out-Json ([ordered]@{ ok = $false; error = 'not allowed' }) 1 }
if ($raw -match '[;&|`$<>\r\n]') { Out-Json ([ordered]@{ ok = $false; error = 'not allowed' }) 1 }
$tokens = @()
foreach ($m in [regex]::Matches($raw.Trim(), '"([^"]*)"|''([^'']*)''|(\S+)')) {
  if ($m.Groups[1].Success) { $tokens += $m.Groups[1].Value } elseif ($m.Groups[2].Success) { $tokens += $m.Groups[2].Value } else { $tokens += $m.Groups[3].Value }
}
$verb = $tokens[0]
if ($Verbs -notcontains $verb) { Out-Json ([ordered]@{ ok = $false; error = 'not allowed' }) 1 }
$rest = @(); if ($tokens.Count -gt 1) { $rest = @($tokens[1..($tokens.Count - 1)]) }
$opt = @{}
if ($verb -ne 'desk') {
  for ($i = 0; $i -lt $rest.Count; $i++) {
    if ($rest[$i] -like '--*') {
      $k = $rest[$i].Substring(2)
      if (($i + 1) -lt $rest.Count -and $rest[$i + 1] -notlike '--*') { $opt[$k] = $rest[$i + 1]; $i++ } else { $opt[$k] = $true }
    }
  }
}
$MatchFile = Join-Path $Root 'match.json'

# ---------- verbs ----------
switch ($verb) {
  'ping' {
    # hands rule input: locked (WTS session flag, read inside the session by the bridge; LogonUI as fallback) and idle_s
    # (GetLastInputInfo in benja's signed-in session, through the bridge). last_input_ms is on BensPC's clock (epoch ms).
    $s = Get-Session
    $o = [ordered]@{ host = $env:COMPUTERNAME; time = (Get-Date).ToString('o'); session_user = $s.user; signed_in = $s.signed_in; locked = $s.locked; lock_src = 'logonui'; idle_s = $null; last_input_ms = $null; free_gb = (Get-FreeGB) }
    if ($s.signed_in) {
      $r = Invoke-Bridge 'idle' @() 12 -Soft
      if ($r.ok -and $r.data -and $null -ne $r.data.idle_s -and [double]$r.data.idle_s -ge 0) {
        $o['idle_s'] = [math]::Round([double]$r.data.idle_s, 1); $o['last_input_ms'] = [long]$r.data.last_input_ms
        if ($null -ne $r.data.locked -and [int]$r.data.locked -ge 0) { $o['locked'] = ([int]$r.data.locked -eq 1); $o['lock_src'] = 'wts' }
      } else { $o['idle_error'] = [string]$r.error }
    }
    Ok $o
  }
  'disk' { Ok ([ordered]@{ free_gb = (Get-FreeGB); floor_gb = $FloorGB }) }
  'gpu-status' {
    if (-not (Test-Path -LiteralPath $GpuLoan)) { Fail 'gpu-sheet-missing' 'GPU_LOAN.txt not found' }
    $last = (Get-Content -LiteralPath $GpuLoan | Where-Object { $_.Trim() } | Select-Object -Last 1)
    $free = [bool]($last -match '^GPU free'); $holder = $null
    if ($last -match '^GPU in use by (\S+)') { $holder = $Matches[1] }
    $util = $null; $mem = $null
    try { $q = (& nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader,nounits 2>$null | Select-Object -First 1) -split ',\s*'; $util = [int]$q[0]; $mem = [int]$q[1] } catch { }
    Ok ([ordered]@{ holder = $holder; free = $free; last_line = [string]$last; util = $util; mem_mb = $mem })
  }
  'gpu-acquire' {
    $who = $opt['who']; if (-not $who) { $who = $Who }
    if ($who -ne $Who) { Fail 'bad-arg' "this tool only signs up as $Who" }
    $why = [string]$opt['why']; if ($why.Length -gt 120) { $why = $why.Substring(0, 120) }
    Assert-Disk
    if (-not (Test-Path -LiteralPath $GpuLoan)) { Fail 'gpu-sheet-missing' 'GPU_LOAN.txt not found' }
    $last = (Get-Content -LiteralPath $GpuLoan | Where-Object { $_.Trim() } | Select-Object -Last 1)
    if ($last -notmatch '^GPU free') {
      $h = 'someone'; if ($last -match '^GPU in use by (\S+)') { $h = $Matches[1] }
      Fail 'gpu-held' "GPU is held by $h"
    }
    $line = "GPU in use by $Who since $(Get-ET)"; if ($why) { $line += ". $why" }
    Add-Content -LiteralPath $GpuLoan -Value $line -Encoding ASCII
    Start-Sleep -Milliseconds 300
    $after = (Get-Content -LiteralPath $GpuLoan | Where-Object { $_.Trim() } | Select-Object -Last 1)
    if ($after -notlike "GPU in use by $Who*") { Fail 'gpu-held' 'someone else signed up at the same moment' }
    Ok ([ordered]@{ holder = $Who })
  }
  'gpu-release' {
    if (-not (Test-Path -LiteralPath $GpuLoan)) { Fail 'gpu-sheet-missing' 'GPU_LOAN.txt not found' }
    $last = (Get-Content -LiteralPath $GpuLoan | Where-Object { $_.Trim() } | Select-Object -Last 1)
    if ($last -like "GPU in use by $Who*") { Add-Content -LiteralPath $GpuLoan -Value "GPU free $(Get-ET)" -Encoding ASCII; Ok ([ordered]@{ released = $true }) }
    Ok ([ordered]@{ released = $false; note = "$Who did not hold the GPU; nothing written" })
  }
  'map-list' { $m = Get-Maps; Ok ([ordered]@{ maps = @($m.maps); source = $m.source }) }
  'server-status' {
    $p = Get-OursProc 'server'
    $listen = Test-PortListen $Port
    $players = @(); $n = 0
    if ($p -and $listen) { $pl = Get-Players; $players = @($pl.players); $n = $players.Count }
    $procId = $null; if ($p) { $procId = [int]$p.ProcessId }
    Ok ([ordered]@{ running = [bool]($p -and $listen); pid = $procId; port = $Port; players = $n; names = @($players) })
  }
  'server-start' {
    Assert-Disk
    $srv = Join-Path $Root 'server'
    $jar = Join-Path $srv 'paper-1.8.8-445.jar'
    if (-not (Test-Path -LiteralPath $jar)) { Fail 'not-set-up' 'our server copy is missing (setup.ps1 has not run)' }
    $map = $opt['map']
    if ($map) {
      Test-Name ([string]$map) 'map'
      if ((Get-Maps).maps -notcontains $map) { Fail 'map-missing' "map '$map' is not in map-list" }
    }
    $p = Get-OursProc 'server'
    if ($p -and (Test-PortListen $Port)) { Ok ([ordered]@{ pid = [int]$p.ProcessId; port = $Port; note = 'already running' }) }
    if (Test-PortListen $Port) { Fail 'port-in-use' "port $Port is already used by a process that is not ours" }
    $java = 'C:\Program Files\Eclipse Adoptium\jdk-21.0.5.11-hotspot\bin\java.exe'
    if (-not (Test-Path -LiteralPath $java)) {
      $alt = Get-ChildItem 'C:\Program Files\Eclipse Adoptium' -Filter java.exe -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
      if ($alt) { $java = $alt.FullName } else { Fail 'server-wont-start' 'no Java 21 found' }
    }
    $logs = Join-Path $Root 'logs'; New-Item -ItemType Directory -Force -Path $logs | Out-Null
    if ($map) {   # GlimTruthKit sends GlimBot into this arena on login (performCommand as the player: no chat typing)
      $tkd = Join-Path $srv 'plugins\GlimTruthKit'; New-Item -ItemType Directory -Force -Path $tkd | Out-Null
      Set-Content -LiteralPath (Join-Path $tkd 'autojoin.txt') -Value $map -Encoding ASCII -NoNewline
    }
    $out = Join-Path $logs 'server.out'
    $cl = 'cmd.exe /c ""' + $java + '" -Xms1G -Xmx3G -XX:+UseG1GC -XX:MaxGCPauseMillis=50 ' + $TagArg + ' -jar paper-1.8.8-445.jar nogui > "' + $out + '" 2>&1"'
    $r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cl; CurrentDirectory = $srv }
    if ($r.ReturnValue -ne 0) { Fail 'server-wont-start' "could not start the server process (code $($r.ReturnValue))" }
    $jp = $null; $end = (Get-Date).AddSeconds(20)
    while ((Get-Date) -lt $end -and -not $jp) {
      $jp = Get-CimInstance Win32_Process -Filter "Name='java.exe'" | Where-Object { $_.CommandLine -like $TagLike } | Select-Object -First 1
      if (-not $jp) { Start-Sleep -Milliseconds 500 }
    }
    if (-not $jp) { Fail 'server-wont-start' 'the java process did not appear' }
    $h = Get-Pids; $h['server'] = [int]$jp.ProcessId; Save-Pids $h
    $end = (Get-Date).AddSeconds(120)
    while ((Get-Date) -lt $end) {
      if (-not (Get-Process -Id ([int]$jp.ProcessId) -ErrorAction SilentlyContinue)) {
        $tail = ''; if (Test-Path -LiteralPath $out) { $tail = (Get-Content -LiteralPath $out -Tail 4) -join ' / ' }
        Fail 'server-wont-start' ("the server exited while starting: " + $tail)
      }
      if (Test-PortListen $Port) {
        # RCON opens last (after every plugin is enabled): wait for it so match-start can talk to GlimTruthKit right away
        $rcon = $false; $end2 = (Get-Date).AddSeconds(60)
        while ((Get-Date) -lt $end2 -and -not $rcon) { try { Invoke-Rcon @('list') | Out-Null; $rcon = $true } catch { Start-Sleep 1 } }
        $tk = $null; if ($rcon) { $tk = Invoke-Tk 'status' }
        if ($map) { @{ map = $map } | ConvertTo-Json -Compress | Set-Content -LiteralPath (Join-Path $Root 'wanted-map.json') -Encoding ASCII }
        $aj = $null; if ($tk) { $aj = [string]$tk.autojoin }
        Ok ([ordered]@{ pid = [int]$jp.ProcessId; port = $Port; rcon = $rcon; truthkit = [bool]$tk; autojoin = $aj })
      }
      Start-Sleep 1
    }
    Fail 'server-wont-start' 'the server did not open its port within 120 s'
  }
  'server-stop' {
    $p = Get-OursProc 'server'
    if ($p) {
      try { Invoke-Rcon @('stop') | Out-Null } catch { }
      $end = (Get-Date).AddSeconds(25)
      while ((Get-Date) -lt $end -and (Get-Process -Id ([int]$p.ProcessId) -ErrorAction SilentlyContinue)) { Start-Sleep 1 }
      Stop-Ours 'server' | Out-Null
    }
    Remove-Ours $MatchFile
    Ok ([ordered]@{ stopped = [bool]$p })
  }
  'match-start' {
    # No desktop input: GlimTruthKit sends GlimBot into the arena (auto-join on login, or "tk join" = "/bw join MAP" run as the player)
    # and starts it with BedWars1058's own "/bw forceStart debug" run as GlimBot (CmdStart needs a player in the arena; "debug" with
    # op starts it with one player; GlimTruthKit gives op for that one command only).
    Assert-Disk
    $map = [string]$opt['map']; if (-not $map) { Fail 'bad-arg' '--map is required' }
    Test-Name $map 'map'
    $mode = [string]$opt['mode']; if (-not $mode) { $mode = '1v1' }
    if ($mode -ne '1v1') { Fail 'bad-arg' "mode '$mode' is not supported yet (only 1v1)" }
    $opp = [string]$opt['opponent']; if (-not $opp) { $opp = 'none' }
    if ($opp -ne 'none') { Fail 'opponent-unavailable' "opponent '$opp' is not built yet (only 'none')" }
    $name = [string]$opt['name']; if (-not $name) { $name = 'GlimBot' }
    if ($name -notmatch '^[A-Za-z0-9_]{3,16}$') { Fail 'bad-arg' 'bad player name' }
    if ((Get-Maps).maps -notcontains $map) { Fail 'map-missing' "map '$map' is not in map-list" }
    if (-not (Get-OursProc 'server') -or -not (Test-PortListen $Port)) { Fail 'server-down' 'our server is not running' }
    $tk = Invoke-Tk 'status'
    if (-not $tk) { Fail 'truthkit-missing' 'the GlimTruthKit plugin did not answer on RCON (tk status)' }
    Invoke-Tk "autojoin $map" | Out-Null
    $joinedBy = 'autojoin'; $triedJoin = $false; $arena = $null; $in = $false
    $end = (Get-Date).AddSeconds(45)   # the client may still be connecting
    while ((Get-Date) -lt $end) {
      $tk = Invoke-Tk 'status'
      if ($tk) {
        $arena = Get-Arena $tk $map; $in = [bool]($arena -and (@($arena.players) -contains $name))
        if ($in) { break }
        $elsewhere = @($tk.arenas | Where-Object { @($_.players) -contains $name -or @($_.spectators) -contains $name }).Count -gt 0
        if ((@($tk.online) -contains $name) -and -not $elsewhere -and -not $triedJoin -and ((Get-Date) -gt $end.AddSeconds(-41))) {
          Invoke-Tk "join $name $map" | Out-Null; $triedJoin = $true; $joinedBy = 'tk join (bw join as the player)'
        }
      }
      Start-Sleep -Milliseconds 700
    }
    if (-not $in) {
      if (-not $tk -or -not (@($tk.online) -contains $name)) { Fail 'client-not-joined' "$name is not on the server" }
      Fail 'arena-join-failed' "$name is on the server but not in arena $map"
    }
    $cmdUsed = 'none (already playing)'
    if ($arena.state -ne 'playing') {
      $r = Invoke-Tk "start $map"; $cmdUsed = 'bw forceStart debug (run as ' + $name + ' by GlimTruthKit)'
      if (-not $r -or -not $r.ok) { $why = 'no reply'; if ($r) { $why = [string]$r.error; if (-not $why) { $why = 'state ' + [string]$r.state } }; Fail 'match-wont-start' ('tk start did not start the arena: ' + $why) }
      $end = (Get-Date).AddSeconds(30)
      while ((Get-Date) -lt $end) { $tk = Invoke-Tk 'status'; $arena = Get-Arena $tk $map; if ($arena -and $arena.state -eq 'playing') { break }; Start-Sleep -Milliseconds 700 }
      if (-not $arena -or $arena.state -ne 'playing') { $st = 'unknown'; if ($arena) { $st = [string]$arena.state }; Fail 'match-wont-start' "the arena did not reach playing within 30 s (state $st)" }
    }
    $id = [string]$arena.match_id; if (-not $id) { $id = 'm' + (Get-Date).ToString('yyyyMMddHHmmss') }
    [ordered]@{ id = $id; map = $map; mode = $mode; opponent = $opp; name = $name; started = (Get-Date).ToString('o'); seen_playing = $true; command = $cmdUsed } | ConvertTo-Json -Compress | Set-Content -LiteralPath $MatchFile -Encoding ASCII
    Ok ([ordered]@{ match_id = $id; arena = $map; state = (Get-State ([string]$arena.state)); joined_by = $joinedBy; command = $cmdUsed })
  }
  'match-status' {
    $m = $null; if (Test-Path -LiteralPath $MatchFile) { try { $m = Get-Content -Raw -LiteralPath $MatchFile | ConvertFrom-Json } catch { } }
    $up = [bool]((Get-OursProc 'server') -and (Test-PortListen $Port))
    $mid = $null; $mp = $null; $t = 0
    if ($m) { $mid = $m.id; $mp = $m.map; $t = [int]((Get-Date) - [datetime]$m.started).TotalSeconds }
    if (-not $up) { Ok ([ordered]@{ state = 'no-server'; t = $t; match_id = $mid; map = $mp; teams = @(); beds = @{}; players = @() }) }
    $tk = Invoke-Tk 'status'
    if (-not $tk) { $st = 'idle'; if ($m) { $st = 'unknown' }; Ok ([ordered]@{ state = $st; t = $t; match_id = $mid; map = $mp; teams = @(); beds = @{}; players = @(); note = 'GlimTruthKit did not answer' }) }
    if (-not $mp) { $mp = @($tk.arenas | Where-Object { @($_.players).Count -gt 0 } | Select-Object -First 1 | ForEach-Object { $_.name })[0] }
    $arena = $null; if ($mp) { $arena = Get-Arena $tk $mp }
    $state = 'idle'; $teams = @(); $beds = [ordered]@{}; $players = @()
    if ($arena) {
      $state = Get-State ([string]$arena.state)
      if ($m) {   # our match is over once its arena resets or a different match id runs there
        if ($state -eq 'waiting' -or $state -eq 'starting' -or ($arena.match_id -and $m.id -and [string]$arena.match_id -ne [string]$m.id -and -not ([string]$m.id).StartsWith('m'))) { $state = 'ended' }
      } elseif ($state -eq 'waiting') { $state = 'idle' }
      $teams = @($arena.teams | ForEach-Object { [ordered]@{ team = $_.team; bed = [bool]$_.bed; members = @($_.members) } })
      foreach ($x in @($arena.teams)) { $beds[[string]$x.team] = [bool]$x.bed }
      $players = @($arena.players)
    } elseif ($m) { $state = 'unknown' }
    Ok ([ordered]@{ state = $state; t = $t; match_id = $mid; map = $mp; teams = @($teams); beds = $beds; players = @($players) })
  }
  'match-stop' {
    $had = Test-Path -LiteralPath $MatchFile
    $m = $null; if ($had) { try { $m = Get-Content -Raw -LiteralPath $MatchFile | ConvertFrom-Json } catch { } }
    $n = $null
    if ((Get-OursProc 'server') -and (Test-PortListen $Port)) {
      $target = 'all'; if ($m -and $m.map) { $target = [string]$m.map }
      $r = Invoke-Tk "stop $target"; if ($r) { $n = $r.stopped }
      Invoke-Tk 'autojoin off' | Out-Null
    }
    Remove-Ours $MatchFile
    Ok ([ordered]@{ stopped = $had; arena_stopped = $n })
  }
  'log-read' {
    # events after --since (ISO) in time order, at most --max (default 200, cap 2000); --types a,b,c keeps only those types.
    # Source 1 (preferred): our truth log logs\truth.jsonl, written by GlimTruthKit, ms times; lines are passed through as written.
    # Source 2 (only when truth.jsonl is missing or empty): the plain server log, whole-second times, fewer event types.
    $sinceMs = [long]0
    if ($opt['since'] -and $opt['since'] -ne $true) { try { $sinceMs = [DateTimeOffset]::Parse([string]$opt['since'], [Globalization.CultureInfo]::InvariantCulture).ToUnixTimeMilliseconds() } catch { Fail 'bad-arg' '--since must be an ISO time' } }
    $max = 200; if ($opt['max'] -and $opt['max'] -ne $true) { $max = [math]::Min(2000, [math]::Max(1, [int]$opt['max'])) }
    $types = $null; if ($opt['types'] -and $opt['types'] -ne $true) { $types = @(([string]$opt['types']).Split(',') | ForEach-Object { $_.Trim() } | Where-Object { $_ }) }
    $items = New-Object System.Collections.ArrayList
    $tf = Join-Path $Root 'logs\truth.jsonl'
    $src = 'server-log'
    if ((Test-Path -LiteralPath $tf) -and (Get-Item -LiteralPath $tf).Length -gt 0) {
      $src = 'truth'
      $lines = @(Get-Content -LiteralPath $tf -Tail 6000 -Encoding UTF8)
      for ($k = 0; $k -lt $lines.Count; $k++) {
        $l = $lines[$k]
        if ($l -notmatch '^\{"ms":(\d+),"t":"[^"]*","type":"([a-z_]+)"') { continue }
        $ms = [long]$Matches[1]; $ty = $Matches[2]
        if ($ms -le $sinceMs) { continue }
        if ($types -and $types -notcontains $ty) { continue }
        if ($k -eq $lines.Count - 1) { try { $null = $l | ConvertFrom-Json } catch { continue } }   # the newest line may be half written
        [void]$items.Add([pscustomobject]@{ ms = $ms; i = $k; json = $l })
      }
    } else {
      $lf = Join-Path $Root 'server\logs\latest.log'
      if (Test-Path -LiteralPath $lf) {
        $day = (Get-Item -LiteralPath $lf).LastWriteTime.Date; $k = 0
        foreach ($l in (Get-Content -LiteralPath $lf -Tail 3000)) {
          $k++
          if ($l -notmatch '^\[(\d\d):(\d\d):(\d\d)\] \[[^\]]*\]: (.*)$') { continue }
          $t = $day.AddHours([int]$Matches[1]).AddMinutes([int]$Matches[2]).AddSeconds([int]$Matches[3]); $msg = $Matches[4]
          if ($t -gt (Get-Date).AddMinutes(5)) { $t = $t.AddDays(-1) }
          $ms = ([DateTimeOffset]$t).ToUnixTimeMilliseconds()
          if ($ms -le $sinceMs) { continue }
          $ev = $null
          if ($msg -match '^(\w+)\[/[\d\.:]+\] logged in') { $ev = [ordered]@{ type = 'join'; player = $Matches[1] } }
          elseif ($msg -match '^(\w+) (lost connection|left the game)') { $ev = [ordered]@{ type = 'leave'; player = $Matches[1] } }
          elseif ($msg -match '(\w+) (was knocked into the void by|was thrown into the void by|was killed by .*into the void) (\w+)') { $ev = [ordered]@{ type = 'void_death'; victim = $Matches[1]; killer = $Matches[3] } }
          elseif ($msg -match '(\w+) fell into the void') { $ev = [ordered]@{ type = 'void_death'; victim = $Matches[1] } }
          elseif ($msg -match '(\w+) was (slain|shot|killed|blown up|burnt|fireballed).* by (\w+)') { $ev = [ordered]@{ type = 'kill'; victim = $Matches[1]; killer = $Matches[3] } }
          elseif ($msg -match '(\w+) (died|fell from a high place|drowned|burned to death)') { $ev = [ordered]@{ type = 'death'; victim = $Matches[1] } }
          elseif ($msg -match '[Bb]ed (was )?[Dd]estroy') { $ev = [ordered]@{ type = 'bed_broken'; text = $msg } }
          elseif ($msg -match 'game (has )?started|Game starts|The game has begun') { $ev = [ordered]@{ type = 'match_start' } }
          elseif ($msg -match 'won the game|Game over|has won|WINNER') { $ev = [ordered]@{ type = 'match_end'; text = $msg } }
          if (-not $ev) { continue }
          if ($types -and $types -notcontains $ev['type']) { continue }
          $o = [ordered]@{ ms = $ms; t = $t.ToString('yyyy-MM-ddTHH:mm:ss.fffzzz') }; foreach ($kk in $ev.Keys) { $o[$kk] = $ev[$kk] }; $o['src'] = 'server-log'
          [void]$items.Add([pscustomobject]@{ ms = $ms; i = $k; json = ($o | ConvertTo-Json -Compress) })
        }
      }
    }
    $sorted = @($items | Sort-Object -Property @{ Expression = 'ms' }, @{ Expression = 'i' })
    $n = [math]::Min($max, $sorted.Count); $more = $sorted.Count -gt $n
    if ($more -and $n -gt 0) {   # never split one millisecond across two pages (the next page starts after next_since)
      $cut = $sorted[$n].ms; $m2 = $n; while ($m2 -gt 0 -and $sorted[$m2 - 1].ms -eq $cut) { $m2-- }
      if ($m2 -gt 0) { $n = $m2 }
    }
    $nxMs = $sinceMs; if ($n -gt 0) { $nxMs = $sorted[$n - 1].ms }
    $nx = [DateTimeOffset]::FromUnixTimeMilliseconds($nxMs).ToLocalTime().ToString('yyyy-MM-ddTHH:mm:ss.fffzzz')
    $sb = New-Object System.Text.StringBuilder
    [void]$sb.Append('{"ok":true,"source":"' + $src + '","count":' + $n + ',"more":' + ([string]$more).ToLower() + ',"next_since":"' + $nx + '","events":[')
    for ($k = 0; $k -lt $n; $k++) { if ($k -gt 0) { [void]$sb.Append(',') }; [void]$sb.Append($sorted[$k].json) }
    [void]$sb.Append(']}')
    [Console]::Out.WriteLine($sb.ToString()); exit 0
  }
  'client-launch' {
    Assert-Disk
    $name = [string]$opt['name']; if (-not $name) { $name = 'GlimBot' }
    if ($name -notmatch '^[A-Za-z0-9_]{3,16}$') { Fail 'bad-arg' 'bad player name' }
    $srvAddr = [string]$opt['server']; if (-not $srvAddr) { $srvAddr = "127.0.0.1:$Port" }
    if ($srvAddr -notmatch '^(127\.0\.0\.1|localhost):\d{2,5}$') { Fail 'bad-arg' 'only our local server is allowed' }
    $sh = $srvAddr.Split(':')[0]; $sp = [int]$srvAddr.Split(':')[1]
    if (Get-OursProc 'client') { Ok ([ordered]@{ pid = [int](Get-Pids)['client']; window = $name; note = 'already running' }) }
    # the GPU must be signed up for first (plan section 3b step 1)
    $last = (Get-Content -LiteralPath $GpuLoan | Where-Object { $_.Trim() } | Select-Object -Last 1)
    if ($last -notlike "GPU in use by $Who*") { Fail 'gpu-not-held' "sign up for the GPU first (last line: $last)" }
    if (-not (Test-PortListen $sp)) { Fail 'server-down' "nothing is listening on $srvAddr" }
    $r = Invoke-Bridge 'client-launch' @($name, $sh, [string]$sp) 120
    if (-not $r.ok) { Fail 'client-crash' ('the client did not start: ' + $r.error) }
    $h = Get-Pids; $h['client'] = [int]$r.data.pid; if ($r.data.launcher_pid) { $h['client_launcher'] = [int]$r.data.launcher_pid }; Save-Pids $h
    # is the game on the NVIDIA GPU? nvidia-smi lists the processes with a context on it (graphics ones too, on Windows)
    $gpuSeen = $null; $end = (Get-Date).AddSeconds(15)
    while ((Get-Date) -lt $end -and -not $gpuSeen) {
      try { $ids = @(& nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>$null | ForEach-Object { [string]$_.Trim() }); $gpuSeen = $ids -contains ([string][int]$r.data.pid) } catch { $gpuSeen = $null; break }
      if (-not $gpuSeen) { Start-Sleep 1 }
    }
    Ok ([ordered]@{ pid = [int]$r.data.pid; window = [string]$r.data.window; nvidia = $gpuSeen })
  }
  'client-stop' {
    $a = Stop-Ours 'client'; $b = Stop-Ours 'client_launcher'
    Ok ([ordered]@{ stopped = [bool]($a -or $b) })
  }
  'desk' {
    if ($rest.Count -lt 1 -or $DeskVerbs -notcontains $rest[0]) { Out-Json ([ordered]@{ ok = $false; error = 'not allowed' }) 1 }
    $sub = $rest[0]; $dargs = @($rest[0]); if ($rest.Count -gt 1) { $dargs += @($rest[1..($rest.Count - 1)]) }
    if (@('press', 'click', 'type', 'key', 'scroll', 'open-app') -contains $sub -and (Get-OursProc 'client')) { Fail 'desk-refused' 'Minecraft is driven from the inside (server commands, client control path), never with desktop clicks or typing' }
    $s = Get-Session
    if (-not $s.signed_in) { Fail 'no-session' 'no signed-in session' }
    if ($s.locked) { Fail 'screen-locked' 'the screen is locked, so clicks and screenshots cannot work' }
    if ($sub -eq 'open-app' -and ($rest.Count -lt 2 -or $rest[1] -notmatch '^(?i)minecraft')) { Fail 'bad-arg' 'open-app only opens Minecraft windows' }
    if ($sub -eq 'screenshot') {
      Assert-Disk
      New-Item -ItemType Directory -Force -Path $ShotDir | Out-Null
      $nm = 'shot-' + (Get-Date).ToString('yyyyMMdd-HHmmss-fff') + '.png'
      if ($rest.Count -gt 1 -and $rest[1] -notlike '--*') { $nm = [IO.Path]::GetFileName($rest[1]); if ($nm -notmatch '^[A-Za-z0-9_\-\.]{1,60}\.png$') { Fail 'bad-arg' 'screenshot name must be like name.png' } }
      $rel = 'shots\' + $nm
      $dargs = @('screenshot', (Join-Path $Root $rel)); if ($rest.Count -gt 2) { $dargs += @($rest[2..($rest.Count - 1)]) }
    }
    $r = Invoke-Bridge 'desk' $dargs 40
    if ($sub -eq 'screenshot') {
      # short window + size cap: keep the newest 60 files and at most 300 MB
      $files = @(Get-ChildItem -LiteralPath $ShotDir -File -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending)
      $tot = 0; $k = 0
      foreach ($f in $files) { $k++; $tot += $f.Length; if ($k -gt 60 -or $tot -gt 300MB) { Remove-Ours $f.FullName } }
    }
    if ($r.data -is [pscustomobject]) {
      $o = [ordered]@{}; foreach ($p in $r.data.PSObject.Properties) { $o[$p.Name] = $p.Value }
      if (-not $o.Contains('ok')) { $o['ok'] = [bool]$r.ok }
      Out-Json $o 0
    }
    if ($r.ok) { Ok ([ordered]@{ out = $r.data }) }
    Fail 'desk-failed' ([string]$r.error)
  }
  'fetch' {
    $rel = [string]$opt['path']; if (-not $rel -or $rel -eq 'True') { Fail 'bad-arg' '--path is required' }
    if ($rel -match '\.\.' -or $rel -match '^[A-Za-z]:' -or $rel.StartsWith('\') -or $rel.StartsWith('/')) { Fail 'bad-arg' 'path must be relative, inside glim-bedwars' }
    $full = [IO.Path]::GetFullPath((Join-Path $Root $rel))
    if (-not (Test-Under $full)) { Fail 'bad-arg' 'path must stay inside glim-bedwars' }
    if (-not (Test-Path -LiteralPath $full -PathType Leaf)) { Fail 'no-such-file' "no file at $rel" }
    $len = (Get-Item -LiteralPath $full).Length
    if ($len -gt 8MB) { Fail 'too-big' "file is $len bytes (cap is 8 MB)" }
    Ok ([ordered]@{ path = $rel; bytes = $len; b64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes($full)) })
  }
}
