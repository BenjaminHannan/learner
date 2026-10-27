#!/bin/bash
# Install the assistant on the Mac. Safe to re-run.
PY="${ASSISTANT_PY:-$HOME/learner-ops/speedbench/venv312/bin/python}"
SRC="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/learner-ops/assistant"
CFG="$HOME/.config/opencode/opencode.json"
DET="$HOME/Library/Application Support/OpenBot/openbot-provider-detection-v1.json"

mkdir -p "$DEST/run" "$HOME/learner-ops/diary/raw/blobs" "$HOME/.config/opencode" \
         "$(dirname "$DET")" "$DEST/launchers"
cp "$SRC/gateway.py" "$SRC/diary_mcp.py" "$SRC/serve.sh" "$SRC/stop.sh" "$SRC/status.sh" "$SRC/watchdog.sh" \
   "$SRC/k2_nothink.jinja" "$DEST/"
rm -f "$DEST/opencode.json"   # an unfilled template here is read as a project config
chmod +x "$DEST"/*.sh

VLM_VENV="${ASSISTANT_VLM_VENV:-$HOME/learner-ops/vlm-venv}"
VLM_MODEL="${ASSISTANT_VLM_MODEL:-$HOME/learner-ops/models/qwen35-2b-vlm}"
VLM_REPO="${ASSISTANT_VLM_REPO:-mlx-community/Qwen3.5-2B-4bit}"
WANT_VISION=0; [ "${1:-}" = "--vision" ] && WANT_VISION=1

# Saved model settings (edit this file to change models or turn the helper off).
if [ ! -f "$DEST/config.sh" ]; then
  cat > "$DEST/config.sh" <<'CFGEOF'
# Read by serve.sh. Blank ASSISTANT_SMALL_MODEL = no K2 helper (saves ~4-5 GB of memory).
ASSISTANT_BIG_MODEL="$HOME/learner-ops/swap1/models/qwen36-35b-4bit"
# Off by default: big + K2 together peak ~27 GB, too much beside normal apps on 32 GB.
ASSISTANT_SMALL_MODEL=""
#ASSISTANT_SMALL_MODEL="$HOME/learner-ops/sleep-m2/models/k2-3.7b-4bit"
ASSISTANT_SMALL_ARGS="--trust-remote-code"
ASSISTANT_SMALL_TEMPLATE="$HOME/learner-ops/assistant/k2_nothink.jinja"
# Image reading: a small vision model (own venv, ~2.5 GB) captions images for the big text-only model.
# serve.sh turns it on by itself when both paths below exist; set ASSISTANT_VISION=0 to force it off.
#ASSISTANT_VISION=1
#ASSISTANT_VLM_VENV="$HOME/learner-ops/vlm-venv"
#ASSISTANT_VLM_MODEL="$HOME/learner-ops/models/qwen35-2b-vlm"
#ASSISTANT_VLM_PORT=18082
CFGEOF
fi
# Save which Python to use, so the Start button works on every Mac.
grep -q '^ASSISTANT_PY=' "$DEST/config.sh" || echo "ASSISTANT_PY=\"$PY\"" >> "$DEST/config.sh"

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

# OpenBot provider list: one "Premonition" entry with readable model names (OpenBot reads it at launch).
python3 - "$(dirname "$DET")/openbot-custom-providers-v1.json" <<'PYEOF'
import json, os, shutil, sys, time
p, url = sys.argv[1], "http://127.0.0.1:8090/v1"
ours = {"id": "server-127-0-0-1-8090", "name": "Premonition", "baseUrl": url, "secret": None, "models": [
    {"id": "qwen36-auto", "name": "Premonition Auto"},
    {"id": "qwen36", "name": "Premonition Thinking"},
    {"id": "qwen36-fast", "name": "Premonition Fast"}]}
d = {"version": 1, "providers": []}
if os.path.exists(p):
    shutil.copy(p, p + time.strftime(".bak-%Y%m%d-%H%M%S"))
    try:
        d = json.load(open(p))
    except ValueError:
        pass
d["providers"] = [x for x in d.get("providers", []) if x.get("baseUrl", "").rstrip("/") != url] + [ours]
json.dump(d, open(p, "w"), separators=(",", ":"))
print("wrote", p)
PYEOF

# Optional image reader (run `install.sh --vision`): mlx-vlm in its own venv (it needs a newer mlx than
# the main venv) plus a 1.75 GB model; about 2.5 GB of disk in all. Skipped when already present.
if [ $WANT_VISION = 1 ]; then
  echo "Image reader: needs about 2.5 GB of disk ($VLM_VENV and $VLM_MODEL)."
  if [ ! -x "$VLM_VENV/bin/python" ]; then
    python3 -m venv "$VLM_VENV" && "$VLM_VENV/bin/python" -m pip install -q --upgrade pip &&
      "$VLM_VENV/bin/python" -m pip install -q "mlx-vlm==0.7.10" ||
      echo "Could not set up the vision venv; images will show as unreadable."
  else
    echo "  vision venv already there; skipped."
  fi
  if [ ! -f "$VLM_MODEL/config.json" ] && [ -x "$VLM_VENV/bin/python" ]; then
    mkdir -p "$VLM_MODEL" && "$VLM_VENV/bin/python" -c \
      'import sys; from huggingface_hub import snapshot_download; snapshot_download(sys.argv[1], local_dir=sys.argv[2])' \
      "$VLM_REPO" "$VLM_MODEL" || echo "Could not download $VLM_REPO."
  else
    echo "  vision model already there; skipped."
  fi
elif [ ! -x "$VLM_VENV/bin/python" ]; then
  echo "Images are not readable yet. To add the small image reader (about 2.5 GB), run: $SRC/install.sh --vision"
fi

# Double-clickable launchers.
cat > "$DEST/launchers/Start Assistant.command" <<'CMD'
#!/bin/bash
"$HOME/learner-ops/assistant/serve.sh" || { echo; echo "Could not start. Press Return to close."; read -r _; exit 1; }
open -a OpenBot 2>/dev/null || echo "(OpenBot app not found; open it yourself.)"
echo
"$HOME/learner-ops/assistant/status.sh" | head -n 4
echo
echo "Ready. You can close this window; the assistant keeps running."
CMD
cat > "$DEST/launchers/Stop Assistant.command" <<'CMD'
#!/bin/bash
"$HOME/learner-ops/assistant/stop.sh"
echo "You can close this window."
CMD
chmod +x "$DEST/launchers/"*.command
# Over SSH macOS privacy blocks ~/Desktop; keep the copies in $DEST/launchers then.
cp "$DEST/launchers/"*.command "$HOME/Desktop/" 2>/dev/null ||
  echo "Could not put the launchers on the Desktop (macOS privacy); drag them from $DEST/launchers"

# Start at login (LaunchAgent). ASSISTANT_AUTOSTART=0 removes it.
AGENT="$HOME/Library/LaunchAgents/com.premonition.assistant.plist"
if [ "${ASSISTANT_AUTOSTART:-1}" = 1 ]; then
  mkdir -p "$(dirname "$AGENT")"
  # AbandonProcessGroup: serve.sh exits after starting the servers; launchd must not kill them.
  cat > "$AGENT" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.premonition.assistant</string>
  <key>ProgramArguments</key>
  <array><string>/bin/bash</string><string>$DEST/serve.sh</string><string>--yes</string></array>
  <key>RunAtLoad</key><true/>
  <key>AbandonProcessGroup</key><true/>
  <key>StandardOutPath</key><string>$DEST/run/autostart.log</string>
  <key>StandardErrorPath</key><string>$DEST/run/autostart.log</string>
</dict>
</plist>
PLIST
  plutil -lint "$AGENT" >/dev/null || exit 1
  # bootstrap also runs it now (RunAtLoad); serve.sh is a no-op when already running
  launchctl bootout "gui/$(id -u)/com.premonition.assistant" 2>/dev/null
  launchctl bootstrap "gui/$(id -u)" "$AGENT" && echo "autostart on: $AGENT"
elif [ -f "$AGENT" ]; then
  launchctl bootout "gui/$(id -u)/com.premonition.assistant" 2>/dev/null
  rm -f "$AGENT" && echo "autostart off: removed $AGENT"
fi

cat <<MSG

Installed. Next steps:
  1. Double-click "Start Assistant" on the Desktop (first start loads the model; up to ~5 min).
  2. In OpenBot pick the "Premonition (local Mac)" models (qwen36-auto is the default and picks how hard to think; qwen36 always thinks, qwen36-fast never).
  3. Model choices live in $DEST/config.sh (blank ASSISTANT_SMALL_MODEL turns the K2 helper off).
  4. Double-click "Stop Assistant" when done. Check anything with $DEST/status.sh
  5. It starts by itself at login (re-run with ASSISTANT_AUTOSTART=0 to turn that off).
MSG
