# build.ps1 - builds GlimTruthKit.jar on BensPC with the existing JDK 21 (--release 8) against Paper 1.8.8 + BedWars1058.
# usage: build.ps1 [-Install]     -Install copies the jar into OUR server copy only (C:\Users\benja\glim-bedwars\server\plugins).
# Classpath: our server copy's jars if present, else bedwars-189's (read-only: only read by javac). Writes only under glim-bedwars.
# Prints "BUILD OK <sha256>" (and "INSTALLED <path>") or "BUILD FAIL ...".
param([switch]$Install)
$ErrorActionPreference = 'Stop'
$Root = 'C:\Users\benja\glim-bedwars'
$Here = $PSScriptRoot
if (-not ([IO.Path]::GetFullPath($Here)).StartsWith($Root + '\', [StringComparison]::OrdinalIgnoreCase)) { 'BUILD FAIL: run me from inside ' + $Root; exit 1 }
$jdk = 'C:\Program Files\Eclipse Adoptium\jdk-21.0.5.11-hotspot\bin'
if (-not (Test-Path -LiteralPath (Join-Path $jdk 'javac.exe'))) {
  $alt = Get-ChildItem 'C:\Program Files\Eclipse Adoptium' -Filter javac.exe -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
  if (-not $alt) { 'BUILD FAIL: no JDK (javac.exe) found'; exit 1 }
  $jdk = $alt.DirectoryName
}
$srv = Join-Path $Root 'server'
if (-not (Test-Path -LiteralPath (Join-Path $srv 'cache\patched_1.8.8.jar'))) { $srv = 'C:\Users\benja\bedwars-189\server' }
$paper = Join-Path $srv 'cache\patched_1.8.8.jar'
$bwjar = Get-ChildItem -LiteralPath (Join-Path $srv 'plugins') -Filter 'bedwars-plugin-*.jar' -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not (Test-Path -LiteralPath $paper) -or -not $bwjar) { "BUILD FAIL: classpath jars not found under $srv"; exit 1 }
$out = Join-Path $Here 'build'; $cls = Join-Path $out 'cls'
New-Item -ItemType Directory -Force -Path $cls | Out-Null
$srcs = @(Get-ChildItem -LiteralPath (Join-Path $Here 'src') -Recurse -Filter *.java | ForEach-Object { $_.FullName })
$ErrorActionPreference = 'Continue'   # javac writes notes to stderr; PowerShell 5.1 would treat them as errors
$log = & (Join-Path $jdk 'javac.exe') --release 8 -Xlint:-options -encoding UTF-8 -cp ($paper + ';' + $bwjar.FullName) -d $cls @srcs 2>&1
$code = $LASTEXITCODE; $ErrorActionPreference = 'Stop'
if ($code -ne 0) { 'BUILD FAIL: javac'; $log | ForEach-Object { "  $_" }; exit 1 }
Copy-Item -LiteralPath (Join-Path $Here 'res\plugin.yml'), (Join-Path $Here 'res\config.yml') -Destination $cls -Force
$jar = Join-Path $out 'GlimTruthKit.jar'
& (Join-Path $jdk 'jar.exe') cf $jar -C $cls .
if ($LASTEXITCODE -ne 0) { 'BUILD FAIL: jar'; exit 1 }
'BUILD OK ' + (Get-FileHash -LiteralPath $jar -Algorithm SHA256).Hash.ToLower() + ' (classpath from ' + $srv + ')'
if ($Install) {
  $pl = Join-Path $Root 'server\plugins'
  if (-not (Test-Path -LiteralPath $pl)) { 'INSTALL SKIPPED: our server copy is not there yet (setup.ps1 has not run)'; exit 0 }
  Copy-Item -LiteralPath $jar -Destination (Join-Path $pl 'GlimTruthKit.jar') -Force
  'INSTALLED ' + (Join-Path $pl 'GlimTruthKit.jar')
}
