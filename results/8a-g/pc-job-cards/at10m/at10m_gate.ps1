# Run by the post-G1 chain waiter (v3e) as the inserted job WORK\insert\15-at10mgate.txt (cmd: at10m_gate.cmd), at the check point where the waiter reaches it (first batch: after
# 14-ptc10s, just before 16-at10m). Big-run PLAN.md eighteenth Addendum 10-12 (2). It reads AT-1 (8aAT, 3M, seed 400) against G2f and g2c3s (at10m_gate.py: AT-1a, AT-1c, AT-1d, AT-1f
# if its counters are in RESULT.json; AT-1b and AT-1e are not gated) and, unless that says "not proved wrong", turns WORK\insert\16-at10m.txt (the agent model at 10M, queue 8aAT10M
# from src-at) into a no-op (cmd: at10m_skipped.cmd), keeping the original beside it as 16-at10m.txt.gated-<stamp>. Proved wrong, "cannot tell" (a file or key missing, AT-1 skipped)
# and any error all skip. It starts and stops nothing and deletes nothing; it ends in seconds. Log: the waiter's log; full output WORK\at10m-gate.txt and WORK\at10m-gate.json.
# (The waiter lists WORK\insert once per check point but reads each file's content when it reaches it, so this rewrite is seen when it gets to 16-at10m.txt.)
$CIO   = 'C:\Users\benja\custom-io'
$WORK  = "$CIO\work"
$LOG   = "$WORK\q8aPost-waiter.log"
$PY    = 'C:\Users\benja\AppData\Local\Programs\Python\Python310\python.exe'
$AT10  = "$WORK\insert\16-at10m.txt"
$STAMP = (Get-Date).ToString('yyyyMMdd-HHmm')
function Say($m) { "$((Get-Date).ToString('yyyy-MM-dd HH:mm:ss')) ET at10m_gate: $m" | Add-Content -Encoding ascii $LOG }
function NewestOk($glob) {
  $best = $null
  foreach ($r in @(Get-ChildItem $glob -ErrorAction SilentlyContinue)) {
    try { if ((Get-Content $r.FullName -Raw | ConvertFrom-Json).status -eq 'ok' -and (-not $best -or $r.LastWriteTime -gt $best.LastWriteTime)) { $best = $r } } catch { }
  }
  if ($best) { return $best.FullName } else { return 'missing' }
}
if (-not (Test-Path $AT10)) { Say 'WORK\insert\16-at10m.txt is not there: nothing to gate'; exit 0 }
if (@(Get-Content $AT10) -match '^\s*cmd\s*:') { Say '16-at10m.txt is already a no-op (cmd:): nothing to gate'; exit 0 }
# AT-1 is job 8aAT-3M-s400 of queue 8aAT (a relaunch after a spill is queue 8aATb, job 8aATb-3M-s400), arm folder AT; G2f is 8aB3G2s400, arm B3G2; g2c3s is 8aG2C3S, arm PTS.
$at   = NewestOk "$WORK\results\8aAT*-pc\8aAT*-3M-s400\AT\RESULT.json"
$g2f  = NewestOk "$WORK\results\8aB3G2s400*-pc\8aB3G2s400*-3M-s400\B3G2\RESULT.json"
$pair = NewestOk "$WORK\results\8aG2C3S*-pc\8aG2C3S*-3M-s400\PTS\RESULT.json"
$rc = 2
try {
  $out = @(& $PY -I "$CIO\at10m_gate.py" --at $at --g2f $g2f --pair $pair --out "$WORK\at10m-gate.json" 2>&1 | ForEach-Object { "$_" })
  $rc = $LASTEXITCODE
} catch { $out = @("gate script error: $($_.Exception.Message)"); $rc = 2 }
$out | Set-Content -Encoding ascii "$WORK\at10m-gate.txt"
foreach ($l in $out) { Say "  $l" }
if ($rc -eq 0) { Say 'the agent model at 10M (16-at10m.txt, queue 8aAT10M) runs next'; exit 0 }
$why = if ($rc -eq 3) { 'AT-1 (3M, seed 400) is proved wrong on a gate line' } else { "cannot tell (rc $rc), NEEDS ATTENTION" }
Copy-Item $AT10 "$AT10.gated-$STAMP"
Set-Content -Encoding ascii $AT10 -Value @('cmd: at10m_skipped.cmd', "gated: $why ($STAMP; WORK\at10m-gate.txt)")
Say "8aAT10M NOT started: $why. 16-at10m.txt now runs at10m_skipped.cmd (a no-op); the original is kept as 16-at10m.txt.gated-$STAMP"
exit 0
