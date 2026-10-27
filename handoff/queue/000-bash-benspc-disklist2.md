BASH-ONLY: yes
GPU: no. LOAD-LIGHT: yes
Director read-only disk list on BensPC for Ben's pick (Thread manager 11:5x UTC 09-27). NO deletes, NO moves, NO writes on BensPC. PowerShell goes over as -EncodedCommand (no stdin, no quoting issues).
```bash
PS=$(cat <<'PSEOF'
$ErrorActionPreference='SilentlyContinue'
"=== drives"; Get-PSDrive -PSProvider FileSystem | ForEach-Object { "{0}: free {1:N1} GB, used {2:N1} GB" -f $_.Name, ($_.Free/1GB), ($_.Used/1GB) }
$ours='^(y1t|lis3|rsn358|bm398|rv39|dl|k1|rd378|premonition-models|tree|tmp-|358|claude)'
function Sz($p){ (Get-ChildItem -LiteralPath $p -Recurse -Force -File | Measure-Object Length -Sum).Sum/1GB }
foreach($root in 'C:\','C:\Users\benja'){ "=== top of $root (>= 0.5 GB)"
 Get-ChildItem -LiteralPath $root -Force -Directory | Where-Object { $_.Name -notin 'Windows','Program Files','Program Files (x86)','ProgramData','AppData','$Recycle.Bin','System Volume Information' } | ForEach-Object {
  $g=Sz $_.FullName; if($g -ge 0.5){ $tag= if($_.Name -match $ours){'OURS?'} else {'ben/other'}; "{0,8:N2} GB  {1,-9}  {2}  (modified {3:yyyy-MM-dd})" -f $g,$tag,$_.FullName,$_.LastWriteTime } } | Sort-Object -Descending }
"=== C:\Users\benja\premonition-models subfolders"
Get-ChildItem -LiteralPath 'C:\Users\benja\premonition-models' -Force -Directory | ForEach-Object { "{0,8:N2} GB  {1}  (modified {2:yyyy-MM-dd})" -f (Sz $_.FullName),$_.Name,$_.LastWriteTime }
"=== skipped system folders, totals only"
foreach($p in 'C:\Windows','C:\Program Files','C:\Program Files (x86)','C:\ProgramData','C:\Users\benja\AppData'){ "{0,8:N2} GB  {1}" -f (Sz $p),$p }
"=== recycle bin"; "{0,8:N2} GB" -f (Sz 'C:\$Recycle.Bin')
PSEOF
)
ENC=$(printf '%s' "$PS" | iconv -f UTF-8 -t UTF-16LE | base64 | tr -d '\n')
perl -e 'alarm shift; exec @ARGV' 3000 ssh -o ConnectTimeout=10 -o BatchMode=yes benspc "powershell -NoProfile -EncodedCommand $ENC" </dev/null 2>&1 | cut -c1-300
echo "rc=$?"
```
"OURS?" is a name guess only; owners confirm before anything is proposed to Ben.
