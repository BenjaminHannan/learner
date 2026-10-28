# Build Premonition on Windows: build\Premonition-win32-x64.zip containing "Premonition.exe".
# Needs Node.js 20+ (https://nodejs.org). Run from the desk folder:  powershell -ExecutionPolicy Bypass -File .\build-win.ps1
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

if (-not (Get-Command node -ErrorAction SilentlyContinue)) { throw 'Node.js is not installed. Get it from https://nodejs.org (LTS), then run this again.' }

Write-Host '==> npm ci'
npm ci
if ($LASTEXITCODE -ne 0) { throw 'npm ci failed' }

Write-Host '==> icon'
node scripts/make-ico.js assets/icon.png build/icon.ico
if ($LASTEXITCODE -ne 0) { throw 'icon build failed' }

if (-not (Test-Path 'vendor\helper\deskhelper.exe')) { throw 'vendor\helper\deskhelper.exe is missing. Build it on Linux/macOS with helper/win/build.sh (mono mcs) and commit it.' }

$name = 'Premonition'
$out = 'build\win'
if (Test-Path $out) { Remove-Item -Recurse -Force $out }

# The sleep trainer (a Python package; no model, no Python) rides along as resources\sleepmlx
$extra = @()
if (Test-Path '..\sleepmlx') {
  Write-Host '==> staging sleepmlx'
  $stage = 'build\stage\sleepmlx'
  if (Test-Path 'build\stage') { Remove-Item -Recurse -Force 'build\stage' }
  New-Item -ItemType Directory -Force -Path $stage | Out-Null
  robocopy '..\sleepmlx' $stage /E /XD __pycache__ tests /XF *.pyc /NFL /NDL /NJH /NJS | Out-Null
  $extra = @('--extra-resource=build/stage/sleepmlx')
} else { Write-Warning 'sleepmlx folder not found; this build will not be able to sleep.' }
# the bundled CPU llama-server.exe (LFM3-capable) rides along as resources\llama
if (Test-Path 'vendor\llama\llama-server.exe') {
  New-Item -ItemType Directory -Force -Path 'build\stage\llama' | Out-Null
  Copy-Item 'vendor\llama\llama-server.exe' 'build\stage\llama\'
  Get-ChildItem 'vendor\llama' -Filter 'LICENSE*' | Copy-Item -Destination 'build\stage\llama\'
  $extra += '--extra-resource=build/stage/llama'
} else { Write-Warning 'vendor\llama\llama-server.exe not found; the app will need an official llama.cpp release with LFM3.' }

Write-Host '==> packaging (win32 x64)'
npx @electron/packager . $name --platform=win32 --arch=x64 --out=$out --overwrite --icon=build/icon.ico `
  --extra-resource=vendor/helper/deskhelper.exe @extra `
  "--win32metadata.ProductName=$name" "--win32metadata.FileDescription=$name" "--win32metadata.InternalName=$name" "--win32metadata.OriginalFilename=$name.exe" `
  '--ignore=^/(build|test|docs|reviews|scripts|vendor|dist|README\.md|DESIGN\.md|build-mac\.sh|build-win\.sh|build-win\.ps1)($|/)' '--ignore=^/helper($|/)'
if ($LASTEXITCODE -ne 0) { throw 'packaging failed' }

$dir = Join-Path $out "$name-win32-x64"
if (-not (Test-Path (Join-Path $dir "$name.exe"))) { throw "Packaging produced no $name.exe in $dir" }

Write-Host '==> zip'
$zip = "build\$name-win32-x64.zip"
if (Test-Path $zip) { Remove-Item -Force $zip }
Compress-Archive -Path $dir -DestinationPath $zip
Get-Item $zip | Format-Table Name, Length
Write-Host "Done: $zip (unzip anywhere, run $name-win32-x64\$name.exe)"
