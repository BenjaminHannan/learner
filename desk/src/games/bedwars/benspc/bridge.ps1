# bridge.ps1 - runs INSIDE benja's signed-in desktop session (scheduled task "GlimBridge", InteractiveToken, only when logged on).
# glimtool.ps1 drops a request file in bridge\req\<id>.json and runs the task; this script answers in bridge\res\<id>.json.
# It loops until no request has arrived for 25 s, then exits (the task is started again by the next request).
# Actions: desk (deskhelper.exe verbs), client-launch (launch-client.ps1). Nothing else.
$ErrorActionPreference = 'Stop'
$Root   = 'C:\Users\benja\glim-bedwars'
$Bridge = Join-Path $Root 'bridge'
$Req    = Join-Path $Bridge 'req'
$Res    = Join-Path $Bridge 'res'
$Desk   = Join-Path $Bridge 'deskhelper.exe'
$Launch = Join-Path $Root 'launch-client.ps1'
$DeskVerbs = @('look', 'press', 'click', 'type', 'key', 'scroll', 'open-app', 'screenshot')
New-Item -ItemType Directory -Force -Path $Req, $Res | Out-Null

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
while (((Get-Date) - $idleSince).TotalSeconds -lt 25) {
  $files = @(Get-ChildItem -LiteralPath $Req -Filter *.json -ErrorAction SilentlyContinue | Sort-Object LastWriteTime)
  if ($files.Count -eq 0) { Start-Sleep -Milliseconds 250; continue }
  $idleSince = Get-Date
  foreach ($f in $files) {
    $id = [IO.Path]::GetFileNameWithoutExtension($f.Name)
    try {
      $q = Get-Content -Raw -LiteralPath $f.FullName | ConvertFrom-Json
      Remove-Ours $f.FullName
      $a = @($q.args | ForEach-Object { [string]$_ })
      switch ([string]$q.action) {
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
