# launch-client.ps1 - OUR offline Minecraft 1.8.9 client (no Microsoft login). Run by bridge.ps1 inside the signed-in session
# so the game gets the NVIDIA GPU. Based on bedwars-189\tools\launch-bot189.ps1 (read-only source), but: no bridge mod,
# its own game dir, and a tag on the command line so glimtool can find and stop exactly this process.
# usage: launch-client.ps1 [-Name GlimBot] [-ServerHost 127.0.0.1] [-ServerPort 25567]
# Last output line is one JSON object: {"ok":true,"pid":N,"launcher_pid":N,"window":"..."}
param([string]$Name = 'GlimBot', [string]$ServerHost = '127.0.0.1', [int]$ServerPort = 25567)
$ErrorActionPreference = 'Stop'
function Done($o) { [Console]::Out.WriteLine(($o | ConvertTo-Json -Compress)); exit 0 }
function Bad($m) { [Console]::Out.WriteLine((@{ ok = $false; error = $m } | ConvertTo-Json -Compress)); exit 1 }
if ($Name -notmatch '^[A-Za-z0-9_]{3,16}$') { Bad 'bad player name' }
if ($ServerHost -notmatch '^(127\.0\.0\.1|localhost)$') { Bad 'only our local server is allowed' }
$Root = 'C:\Users\benja\glim-bedwars'
$B    = 'C:\Users\benja\bedwars-189'                      # read-only source of java, libraries, assets, versions
$G    = Join-Path $Root 'client'                           # our game dir (options, logs)
$MD   = Join-Path $Root 'client-main'                       # our main dir (own natives), junctions to the shared libs
$java = Join-Path $B 'jdk8\jdk8u504-b01\bin\javaw.exe'
$pm   = 'C:\Users\benja\bedwars-bots\venv\Scripts\portablemc.exe'
foreach ($p in @($java, $pm, (Join-Path $B 'mc\versions\fabric-loader-0.18.3-1.8.9'))) { if (-not (Test-Path -LiteralPath $p)) { Bad "missing: $p" } }
if ((Get-PSDrive C).Free / 1GB -lt 15) { Bad 'low disk (under 15 GB free)' }
New-Item -ItemType Directory -Force -Path (Join-Path $G 'mods'), $MD | Out-Null
@"
fancyGraphics:false
renderDistance:6
maxFramerate:120
enableVsync:false
guiScale:1
particles:2
entityShadows:false
pauseOnLostFocus:false
soundCategory_master:1.0
fullscreen:false
useVbo:true
viewBobbing:false
lang:en_US
snooperEnabled:false
resourcePacks:[]
"@ | Set-Content -LiteralPath (Join-Path $G 'options.txt') -Encoding ASCII
# NVIDIA for this java (same HKCU key the older track uses; setting it again is harmless)
New-Item -Path 'HKCU:\Software\Microsoft\DirectX\UserGpuPreferences' -Force | Out-Null
Set-ItemProperty 'HKCU:\Software\Microsoft\DirectX\UserGpuPreferences' -Name $java -Value 'GpuPreference=2;'
foreach ($d in 'libraries', 'assets', 'versions') {
  if (-not (Test-Path -LiteralPath (Join-Path $MD $d))) { cmd /c mklink /J "$MD\$d" "$B\mc\$d" | Out-Null }
}
$logs = Join-Path $Root 'logs'; New-Item -ItemType Directory -Force -Path $logs | Out-Null
$a = @('--main-dir', $MD, 'start', 'fabric-loader-0.18.3-1.8.9', '--mc-dir', $G, '-u', $Name, '--resolution', '854x480',
       '--join-server', $ServerHost, '--join-server-port', "$ServerPort", '--jvm', "`"$java`"",
       '--jvm-arg=-Xms512M', '--jvm-arg=-Xmx2G', '--jvm-arg=-Dglim.tag=glim-bedwars')
$lp = Start-Process -FilePath $pm -ArgumentList $a -PassThru -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logs 'client.out') -RedirectStandardError (Join-Path $logs 'client.err')
$jp = $null; $end = (Get-Date).AddSeconds(90)
while ((Get-Date) -lt $end -and -not $jp) {
  if ($lp.HasExited -and $lp.ExitCode -ne 0) { Bad ("portablemc exited with code " + $lp.ExitCode + " (see logs\client.err)") }
  $jp = Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^javaw?\.exe$' -and $_.CommandLine -like '*glim.tag=glim-bedwars*' } | Select-Object -First 1
  if (-not $jp) { Start-Sleep -Milliseconds 500 }
}
if (-not $jp) { Bad 'the game process did not appear within 90 s' }
$title = ''
$end = (Get-Date).AddSeconds(25)
while ((Get-Date) -lt $end -and -not $title) {
  $w = Get-Process -Id ([int]$jp.ProcessId) -ErrorAction SilentlyContinue
  if ($w -and $w.MainWindowTitle) { $title = $w.MainWindowTitle } else { Start-Sleep -Milliseconds 500 }
}
Done ([ordered]@{ ok = $true; pid = [int]$jp.ProcessId; launcher_pid = [int]$lp.Id; window = $title })
