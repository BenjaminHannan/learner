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

Write-Host '==> packaging (win32 x64)'
npx @electron/packager . $name --platform=win32 --arch=x64 --out=$out --overwrite --icon=build/icon.ico `
  --extra-resource=helper/deskhelper.ps1 @extra `
  "--win32metadata.ProductName=$name" "--win32metadata.FileDescription=$name" "--win32metadata.InternalName=$name" "--win32metadata.OriginalFilename=$name.exe" `
  '--ignore=^/(build|test|docs|reviews|scripts|README\.md|DESIGN\.md|build-mac\.sh|build-win\.sh|build-win\.ps1)($|/)' '--ignore=^/helper($|/)'
if ($LASTEXITCODE -ne 0) { throw 'packaging failed' }

$dir = Join-Path $out "$name-win32-x64"
if (-not (Test-Path (Join-Path $dir "$name.exe"))) { throw "Packaging produced no $name.exe in $dir" }

Write-Host '==> zip'
$zip = "build\$name-win32-x64.zip"
if (Test-Path $zip) { Remove-Item -Force $zip }
Compress-Archive -Path $dir -DestinationPath $zip
Get-Item $zip | Format-Table Name, Length
Write-Host "Done: $zip (unzip anywhere, run $name-win32-x64\$name.exe)"
