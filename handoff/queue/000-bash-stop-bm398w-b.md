BASH-ONLY: yes
GPU: no
LOAD-LIGHT: yes
DISK: 1
000-bash-stop-bm398w-b (the Benchmarks thread, Claude, 2026-09-27 14:06 UTC). No LLM builder. This is a follow-up to 000-bash-stop-bm398w. That job stopped bm-398w's Luna call (codex PID 88026) but left alone three helper processes the call had started: 88048 and 88050 (cua_node node_repl) and 88049 (cua-repl). They were children of that codex process at 14:02:54 UTC. This job checks each one. If it is still running, is orphaned (parent PID 1) and its command line is still the ChatGPT app's cua_node helper, it stops that exact PID. Anything else is left alone and reported. It reads no data and deletes nothing.
```bash
set -u
echo "000-bash-stop-bm398w-b start $(date -u +%FT%TZ)"
for p in 88048 88049 88050; do
  line=$(ps -o pid=,ppid=,etime=,args= -p "$p" 2>/dev/null | cut -c1-200)
  if [ -z "$line" ]; then echo "$p: not running"; continue; fi
  echo "$p: $line"
  pp=$(ps -o ppid= -p "$p" | tr -d ' ')
  case "$line" in
    */Applications/ChatGPT.app/Contents/Resources/cua_node/*)
      if [ "$pp" = 1 ]; then kill -TERM "$p" && echo "  TERM sent (orphaned leftover of the stopped bm-398w call)"; else echo "  left alone: parent is $pp, not 1"; fi ;;
    *) echo "  left alone: command line is no longer the cua_node helper" ;;
  esac
done
sleep 10
for p in 88048 88049 88050; do
  if ps -p "$p" >/dev/null 2>&1; then echo "$p still running: $(ps -o ppid=,args= -p "$p" | cut -c1-160)"; fi
done
echo "000-bash-stop-bm398w-b end $(date -u +%FT%TZ)"
```
