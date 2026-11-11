# Run by the post-G1 chain waiter (v3e) as the inserted job WORK\insert\10-g2fgate.txt (cmd: g2f_gate.cmd), at its first insert check point:
# right after g2c3s and G2f (B3 group 2, 3M, seed 400), before B3 group 1. Spec addendum AD. It reads G2f against the sealed AT-1 gate
# (g2f_gate.py: the proved-wrong lines of B3G2-1 to B3G2-3 that do not need group 1) and, only when that does not say "not proved wrong",
# turns WORK\insert\11-at.txt (AT-1, queue 8aAT from src-at) into a no-op (cmd: at_skipped.cmd), keeping the original beside it as
# 11-at.txt.gated-<stamp>. It starts and stops nothing and deletes nothing; it ends in seconds. Log: the waiter's log; full output WORK\g2f-gate.txt.
$CIO   = 'C:\Users\benja\custom-io'
$WORK  = "$CIO\work"
$LOG   = "$WORK\q8aPost-waiter.log"
$PY    = 'C:\Users\benja\AppData\Local\Programs\Python\Python310\python.exe'
$AT    = "$WORK\insert\11-at.txt"
$STAMP = (Get-Date).ToString('yyyyMMdd-HHmm')
function Say($m) { "$((Get-Date).ToString('yyyy-MM-dd HH:mm:ss')) ET g2f_gate: $m" | Add-Content -Encoding ascii $LOG }
function NewestOk($glob) {
  $best = $null
  foreach ($r in @(Get-ChildItem $glob -ErrorAction SilentlyContinue)) {
    try { if ((Get-Content $r.FullName -Raw | ConvertFrom-Json).status -eq 'ok' -and (-not $best -or $r.LastWriteTime -gt $best.LastWriteTime)) { $best = $r } } catch { }
  }
  if ($best) { return $best.FullName } else { return 'missing' }
}
if (-not (Test-Path $AT)) { Say 'WORK\insert\11-at.txt is not there: nothing to gate'; exit 0 }
$g2f  = NewestOk "$WORK\results\8aB3G2s400*-pc\8aB3G2s400*-3M-s400\B3G2\RESULT.json"
$pair = NewestOk "$WORK\results\8aG2C3S*-pc\8aG2C3S*-3M-s400\PTS\RESULT.json"
$out = @(& $PY -I "$CIO\g2f_gate.py" --g2f $g2f --pair $pair --out "$WORK\g2f-gate.json" 2>&1 | ForEach-Object { "$_" })
$rc = $LASTEXITCODE
$out | Set-Content -Encoding ascii "$WORK\g2f-gate.txt"
foreach ($l in $out) { Say "  $l" }
if ($rc -eq 0) { Say 'AT-1 (11-at.txt) runs next'; exit 0 }
$why = if ($rc -eq 3) { 'G2f seed 400 is proved wrong' } else { "cannot tell (rc $rc), NEEDS ATTENTION" }
Copy-Item $AT "$AT.gated-$STAMP"
Set-Content -Encoding ascii $AT -Value @('cmd: at_skipped.cmd', "gated: $why ($STAMP; WORK\g2f-gate.txt)")
Say "AT-1 NOT started: $why. 11-at.txt now runs at_skipped.cmd (a no-op); the original is kept as 11-at.txt.gated-$STAMP"
exit 0
