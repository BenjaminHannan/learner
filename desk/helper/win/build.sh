#!/usr/bin/env bash
# Compile deskhelper.exe (a .NET Framework 4.8 console app) on Linux/macOS with mono's mcs, against the official net48
# reference assemblies (NuGet package, cached in build/refs). Output: ../../vendor/helper/deskhelper.exe
# Windows 10/11 ship .NET Framework 4.8, so the exe runs there with nothing installed.
#   apt-get install -y mono-mcs     (or: brew install mono)
set -euo pipefail
cd "$(dirname "$0")"
OUT=../../vendor/helper/deskhelper.exe
REFS_DIR="${REFS_DIR:-../../build/refs}"
command -v mcs >/dev/null || { echo "mcs not found: apt-get install -y mono-mcs" >&2; exit 1; }
FW="$REFS_DIR/build/.NETFramework/v4.8"
if [[ ! -f "$FW/mscorlib.dll" ]]; then
  echo "==> fetching net48 reference assemblies"
  mkdir -p "$REFS_DIR"
  curl -sSL -o "$REFS_DIR/refs.nupkg" https://www.nuget.org/api/v2/package/Microsoft.NETFramework.ReferenceAssemblies.net48
  unzip -q -o "$REFS_DIR/refs.nupkg" -d "$REFS_DIR"
fi
mkdir -p "$(dirname "$OUT")"
mcs -target:exe -platform:x64 -optimize+ -nostdlib -out:"$OUT" -lib:"$FW" \
  -r:mscorlib.dll -r:System.dll -r:System.Core.dll -r:System.Drawing.dll -r:System.Windows.Forms.dll -r:System.Web.Extensions.dll \
  -r:UIAutomationClient.dll -r:UIAutomationTypes.dll -r:WindowsBase.dll -r:Facades/System.Runtime.dll \
  DeskHelper.cs Ui.cs
ls -l "$OUT"
