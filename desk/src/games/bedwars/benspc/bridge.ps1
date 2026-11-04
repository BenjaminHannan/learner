# bridge.ps1 - runs INSIDE benja's signed-in desktop session (scheduled task "GlimBridge", InteractiveToken, only when logged on;
# started through bridge-launch.vbs so no console window ever shows). glimtool.ps1 drops a request file in bridge\req\<id>.json
# and runs the task; this script answers in bridge\res\<id>.json. It loops until no request has arrived for 25 s, then exits.
# Actions: idle (hands rule: seconds since the last keyboard/mouse input in this session + the session's lock flag), desk
# (deskhelper.exe verbs), client-launch (launch-client.ps1). Nothing else. It never unlocks the screen and never sends input itself.
$ErrorActionPreference = 'Stop'
$Root   = 'C:\Users\benja\glim-bedwars'
$Bridge = Join-Path $Root 'bridge'
$Req    = Join-Path $Bridge 'req'
$Res    = Join-Path $Bridge 'res'
$Desk   = Join-Path $Bridge 'deskhelper.exe'
$Launch = Join-Path $Root 'launch-client.ps1'
$DeskVerbs = @('look', 'press', 'click', 'type', 'key', 'scroll', 'open-app', 'screenshot')
New-Item -ItemType Directory -Force -Path $Req, $Res | Out-Null
$handsErr = $null
try {
  Add-Type -TypeDefinition @"
using System; using System.Runtime.InteropServices;
public static class GlimHands {
  [StructLayout(LayoutKind.Sequential)] struct LII { public uint cbSize; public uint dwTime; }
  [DllImport("user32.dll")] static extern bool GetLastInputInfo(ref LII p);
  [DllImport("kernel32.dll")] static extern uint GetTickCount();
  [DllImport("wtsapi32.dll", SetLastError = true)] static extern bool WTSQuerySessionInformationW(IntPtr h, int sid, int cls, out IntPtr buf, out int bytes);
  [DllImport("wtsapi32.dll")] static extern void WTSFreeMemory(IntPtr p);
  // seconds since the last input in THIS session (-1 if unknown); tick arithmetic wraps correctly after 49.7 days
  public static double IdleSeconds() { LII l = new LII(); l.cbSize = (uint)Marshal.SizeOf(typeof(LII)); if (!GetLastInputInfo(ref l)) return -1; return unchecked(GetTickCount() - l.dwTime) / 1000.0; }
  // 1 locked, 0 unlocked, -1 unknown: WTSSessionInfoEx (25) of the current session; SessionFlags at offset 16 (WTS_SESSIONSTATE_LOCK 0, UNLOCK 1)
  public static int Locked() { IntPtr b; int n; if (!WTSQuerySessionInformationW(IntPtr.Zero, -1, 25, out b, out n)) return -1; try { int f = Marshal.ReadInt32(b, 16); return f == 0 ? 1 : (f == 1 ? 0 : -1); } finally { WTSFreeMemory(b); } }
}
"@
} catch { $handsErr = [string]$_.Exception.Message }

function Remove-Ours([string]$p) {
  $full = [IO.Path]::GetFullPath($p)
  if ($full.StartsWith($Root + '\', [StringComparison]::OrdinalIgnoreCase) -and (Test-Path -LiteralPath $full -PathType Leaf)) { Remove-Item -LiteralPath $full -Force }
}
function Write-Res($id, $ok, $data, $err) {
  $o = [ordered]@{ id = $id; ok = $ok; data = $data; error = $err }
  $tmp = Join-Path $Res ($id + '.tmp')
  ($o | ConvertTo-Json -Compress -Depth 8) | Set-Content -LiteralPath $tmp -Encoding UTF8
  Move-Item -LiteralPath $tmp -Destination (Join-Path $Res ($id + '.json')) -Force
}

$idleSince = Get-Date
while ($true) {
  $files = @(Get-ChildItem -LiteralPath $Req -Filter *.json -ErrorAction SilentlyContinue | Sort-Object LastWriteTime)
  if ($files.Count -eq 0) {
    if (((Get-Date) - $idleSince).TotalSeconds -ge 25) { break }   # the check above ran last, so a request written just before is still served
    Start-Sleep -Milliseconds 100; continue
  }
  $idleSince = Get-Date
  foreach ($f in $files) {
    $id = [IO.Path]::GetFileNameWithoutExtension($f.Name)
    try {
      $q = Get-Content -Raw -LiteralPath $f.FullName | ConvertFrom-Json
      Remove-Ours $f.FullName
      $a = @($q.args | ForEach-Object { [string]$_ })
      switch ([string]$q.action) {
        'idle' {
          if ($handsErr) { Write-Res $id $false $null ('hands check unavailable: ' + $handsErr); break }
          $now = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds(); $idle = [GlimHands]::IdleSeconds()
          $last = $null; if ($idle -ge 0) { $last = [long]($now - [math]::Round($idle * 1000)) }
          Write-Res $id $true ([ordered]@{ idle_s = $idle; last_input_ms = $last; locked = [GlimHands]::Locked(); now_ms = $now }) $null
        }
        'desk' {
          if ($a.Count -lt 1 -or $DeskVerbs -notcontains $a[0]) { Write-Res $id $false $null 'desk verb not allowed'; break }
          if ($a[0] -eq 'screenshot' -and $a.Count -ge 2 -and -not ([IO.Path]::GetFullPath($a[1])).StartsWith((Join-Path $Root 'shots') + '\', [StringComparison]::OrdinalIgnoreCase)) { Write-Res $id $false $null 'screenshots may only go under shots\'; break }
          if (-not (Test-Path -LiteralPath $Desk)) { Write-Res $id $false $null 'deskhelper.exe is missing in bridge\'; break }
          $out = & $Desk @a 2>&1 | Out-String
          $data = $null; try { $data = $out | ConvertFrom-Json } catch { $data = $out.Trim() }
          Write-Res $id $true $data $null
        }
        'client-launch' {
          if ($a.Count -lt 3) { Write-Res $id $false $null 'client-launch needs name, host, port'; break }
          $out = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Launch -Name $a[0] -ServerHost $a[1] -ServerPort ([int]$a[2]) 2>&1 | Out-String
          $j = $null; try { $j = $out.Trim().Split("`n")[-1] | ConvertFrom-Json } catch { }
          if ($j -and $j.ok) { Write-Res $id $true $j $null } else { Write-Res $id $false $null ('launch failed: ' + $out.Trim()) }
        }
        default { Write-Res $id $false $null 'action not allowed' }
      }
    } catch { Write-Res $id $false $null ([string]$_.Exception.Message) }
  }
}
