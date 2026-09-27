BASH-ONLY: yes
GPU: no. LOAD-LIGHT: yes
Director read-only M3 Pro probe (Thread manager 17:17 UTC 09-27, after Ben's "Use the m3 pro"). Changes nothing; only tests that the vast key file exists, never reads it.
```bash
tailscale status 2>&1 | grep -i 100.93.41.100 | cut -c1-200
R='hostname; sysctl -n machdep.cpu.brand_string hw.memsize vm.loadavg; df -h ~ | tail -1; for c in uv git vastai python3.12; do printf "%s: " $c; command -v $c || echo missing; done; test -e ~/.config/vastai/vast_api_key && echo "vast key file: exists" || echo "vast key file: missing"; P=$(uv python find 3.12 2>/dev/null); [ -n "$P" ] && "$P" -c "import torch; print(\"torch\", torch.__version__, \"mps\", torch.backends.mps.is_available())" 2>&1 | tail -1; for d in ~/learner ~/beautiful-model ~/premonition-watch/work; do [ -d "$d/.git" ] && echo "$d $(git -C "$d" log -1 --format=%h)"; done; date -u'
perl -e 'alarm shift; exec @ARGV' 120 ssh -o ConnectTimeout=10 -o BatchMode=yes ben-hannan@100.93.41.100 "$R" </dev/null 2>&1 | cut -c1-200; echo "rc=$?"
date -u
```
