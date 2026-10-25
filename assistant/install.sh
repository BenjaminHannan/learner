#!/bin/bash
# Install the assistant on the Mac. Safe to re-run.
PY="${ASSISTANT_PY:-$HOME/learner-ops/speedbench/venv312/bin/python}"
SRC="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/learner-ops/assistant"
CFG="$HOME/.config/opencode/opencode.json"
DET="$HOME/Library/Application Support/OpenBot/openbot-provider-detection-v1.json"

mkdir -p "$DEST/run" "$HOME/learner-ops/diary/raw/blobs" "$HOME/.config/opencode" \
         "$(dirname "$DET")" "$HOME/Desktop"
cp "$SRC/gateway.py" "$SRC/diary_mcp.py" "$SRC/serve.sh" "$SRC/stop.sh" "$SRC/status.sh" \
   "$SRC/opencode.json" "$DEST/"
chmod +x "$DEST"/*.sh

# OpenCode config: fill the template, merge into any existing file (ours wins).
[ -f "$CFG" ] && cp "$CFG" "$CFG.bak-$(date +%Y%m%d-%H%M%S)"
python3 - "$SRC/opencode.json" "$CFG" "$HOME" "$PY" <<'PYEOF' || exit 1
import json, os, sys
tpl, cfg, home, py = sys.argv[1:5]
ours = json.loads(open(tpl).read().replace("__HOME__", home).replace("__PY__", py))
def merge(a, b):  # b wins
    for k, v in b.items():
        a[k] = merge(a[k], v) if isinstance(v, dict) and isinstance(a.get(k), dict) else v
    return a
cur = {}
if os.path.exists(cfg):
    try:
        cur = json.load(open(cfg))
    except ValueError:
        sys.exit("Existing %s is not plain JSON; left untouched (backup made). Merge by hand." % cfg)
json.dump(merge(cur, ours), open(cfg, "w"), indent=2, ensure_ascii=False)
print("wrote", cfg)
PYEOF

# OpenBot local-server detection: add our address, keep everything else.
python3 - "$DET" <<'PYEOF'
import json, os, sys
p, addr = sys.argv[1], "http://127.0.0.1:8090/v1"
d = {"version": 1, "settings": {"enabled": True, "addresses": [], "folders": [], "hiddenIds": []}}
if os.path.exists(p):
    try:
        d = json.load(open(p))
    except ValueError:
        pass
s = d.setdefault("settings", {})
a = s.setdefault("addresses", [])
if addr not in a:
    a.append(addr)
json.dump(d, open(p, "w"), indent=2)
print("wrote", p)
PYEOF

# Double-clickable launchers.
cat > "$HOME/Desktop/Start Assistant.command" <<'CMD'
#!/bin/bash
"$HOME/learner-ops/assistant/serve.sh" || { echo; echo "Could not start. Press Return to close."; read -r _; exit 1; }
open -a OpenBot 2>/dev/null || echo "(OpenBot app not found; open it yourself.)"
echo
"$HOME/learner-ops/assistant/status.sh" | head -n 4
echo
echo "Ready. You can close this window; the assistant keeps running."
CMD
cat > "$HOME/Desktop/Stop Assistant.command" <<'CMD'
#!/bin/bash
"$HOME/learner-ops/assistant/stop.sh"
echo "You can close this window."
CMD
chmod +x "$HOME/Desktop/Start Assistant.command" "$HOME/Desktop/Stop Assistant.command"

cat <<MSG

Installed. Next steps:
  1. Double-click "Start Assistant" on the Desktop (first start loads the model; up to ~5 min).
  2. In OpenBot pick the "Premonition (local Mac)" models (qwen36 thinks, qwen36-fast is quicker).
  3. For the small helper, set ASSISTANT_SMALL_MODEL (and ASSISTANT_SMALL_ARGS) before starting.
  4. Double-click "Stop Assistant" when done. Check anything with $DEST/status.sh
MSG
