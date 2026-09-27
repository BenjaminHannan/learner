BASH-ONLY: yes
GPU: no. LOAD-LIGHT: yes
HELD until the Thread manager relays Ben's own typed words ("yes, delete those 6") with the message id; the Director then adds that id on the BEN-YES line and moves this file to queue/. Deletes EXACTLY these 6 folders on BensPC (owners confirmed finished and not needed, 09-27 12:1x UTC; paths and sizes from disklist2, outbox 8b1ec5b81). Each path is re-checked: it must exist, be a directory, not be a link, and have a size within 0.9x to 1.1x of the listed size, or it is SKIPPED. Nothing else is touched.
BEN-YES: Thread manager question cmsg_01FuvegZXjMmeUzStiEFVnEW1kKSynA9PRrFRCGui4v9jd (12:18:49Z) naming these 6 paths; Ben typed "yes" in cmsg_01FuvegZXjMmeUzStiEFVnEWXvFKahCeyp6nNSxcfMHpub (12:19:32Z). Held further for the coordinator's read-only reader check (12:19Z).
```bash
PS=$(cat <<'PSEOF'
$ErrorActionPreference='Stop'
function Sz($p){ (Get-ChildItem -LiteralPath $p -Recurse -Force -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum/1GB }
function Free(){ "{0:N2}" -f ((Get-PSDrive C).Free/1GB) }
"free before: $(Free) GB"
$list=[ordered]@{ 'C:\Users\benja\rd371b'=5.80; 'C:\Users\benja\rsn299panel'=0.81; 'C:\Users\benja\rsn299bpanel'=0.81; 'C:\Users\benja\cre333'=1.27; 'C:\Users\benja\e2e330dev'=1.08; 'C:\Users\benja\e339style'=1.27 }
foreach($p in $list.Keys){
 $want=$list[$p]
 if(-not (Test-Path -LiteralPath $p -PathType Container)){ "SKIP $p : missing"; continue }
 $it=Get-Item -LiteralPath $p -Force
 if($it.Attributes -band [IO.FileAttributes]::ReparsePoint){ "SKIP $p : is a link"; continue }
 $g=Sz $p
 if($g -lt 0.9*$want -or $g -gt 1.1*$want){ "SKIP $p : size {0:N2} GB, expected {1} GB" -f $g,$want; continue }
 try { Remove-Item -LiteralPath $p -Recurse -Force; "DELETED $p ({0:N2} GB)" -f $g } catch { "FAILED $p : $($_.Exception.Message)" }
}
"free after: $(Free) GB"
PSEOF
)
ENC=$(printf '%s' "$PS" | iconv -f UTF-8 -t UTF-16LE | base64 | tr -d '\n')
perl -e 'alarm shift; exec @ARGV' 3000 ssh -o ConnectTimeout=10 -o BatchMode=yes benspc "powershell -NoProfile -EncodedCommand $ENC" </dev/null 2>&1 | cut -c1-300
echo "rc=$?"
```
