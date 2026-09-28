STATUS: HELD. DO NOT RUN (helper D, 2026-09-28 21:18 UTC from date -u). The Director releases it by deleting this line.
BASH-ONLY: yes
GPU: no. LOAD-LIGHT: yes
Owner job (helper D, Claude, thread "D: Finish the size test"). Read-only look at what became of the FIRST rsn-358s vast rental. Finding behind it: rent358s-1-start was released 2026-09-27 14:43 UTC (ledger line 2699, commit b437a4ec2) and printed STARTED at 14:59 UTC (builder-outbox runs/rent358s-1-start/rent358s-1-start.go1.reply.md): instance 52973474, RTX 5090, $0.469/h, guard started. The instance was still "running" at 17:16 UTC (runs/000-bash-vastcredit-1715) and gone from the list by 18:14 UTC (1813). No collect job (rent358s-2-collect) exists on main and no runs-vast/ or run-vast/ is on main. So the 8 nets may already have been trained, evaluated and copied back to the Mac, and never collected. This job rents nothing, creates nothing, destroys nothing, starts nothing, and prints no key, email or config. It prints no score: for the 8 runs it only lists whether each file exists (never the contents of tests.json).
```bash
G=$HOME/premonition-watch/rsn358s-vast; MP=$HOME/premonition-models/rsn358s-vast
date -u
[ -d "$G" ] || { echo "NO-STATE: $G does not exist (the first start never wrote state on this Mac)"; exit 0; }
echo "== END: $(cat "$G/END" 2>/dev/null || echo 'none (guard not ended or never ran)')"
echo "== rentals.txt (id $/h created gone):"; cat "$G/rentals.txt" 2>/dev/null
echo "== guard processes: $(pgrep -f "vguard.sh $G" | tr '\n' ' ')"
echo "== last 25 lines of $G/log.txt:"; tail -25 "$G/log.txt" 2>/dev/null | cut -c1-260
O=$G/out/W
echo "== rental progress file (drive-state.txt):"; cat "$O/drive-state.txt" 2>/dev/null | cut -c1-200
echo "== SEAL-run on the rental (sha and name only):"; cat "$O/SEAL-run.sha256.txt" 2>/dev/null
echo "== manifest lines: $(cat "$O/MANIFEST.sha256" 2>/dev/null | wc -l | tr -d " ")"
echo "== per run: final.pt on Mac / train_log / train_summary / tests.json present (yes or no only)"
for R in loop-s9 plain-s9 loop-s10 plain-s10 loop-s11 plain-s11 loop-s12 plain-s12; do
  sha=$(awk -v f="$R/final.pt" '$2==f {print $1}' "$O/SEAL-run.sha256.txt" 2>/dev/null); m=$(shasum -a 256 "$MP/$R/final.pt" 2>/dev/null | awk '{print $1}')
  echo "$R: sealed=$([ -n "$sha" ] && echo yes || echo no) mac-copy-matches-seal=$([ -n "$sha" ] && [ "$m" = "$sha" ] && echo yes || echo no) train_log=$([ -s "$O/$R/train_log.jsonl" ] && echo yes || echo no) summary=$([ -s "$O/$R/train_summary.json" ] && echo yes || echo no) tests=$([ -s "$O/$R/tests.json" ] && echo yes || echo no)"; done
echo "== live vast instances (id label status $/h):"
command -v vastai >/dev/null && vastai show instances --raw 2>/dev/null | perl -MJSON::PP -e 'local $/; my $d=decode_json(<STDIN>); printf "%s %s %s %.3f\n", $_->{id}, $_->{label}//"-", $_->{actual_status}//"-", $_->{dph_total}//0 for @$d' || echo "vastai CLI missing"
echo "== collected on main (run-vast/COLLECT.txt in origin/main): $(git cat-file -e origin/main:artifacts/claude-rsn358s-20260926/run-vast/COLLECT.txt 2>/dev/null && echo yes || echo no)"
date -u
```
