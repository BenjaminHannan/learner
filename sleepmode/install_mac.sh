#!/bin/bash
# Installs Sleep Mode on the Mac. Safe to re-run. Works with bash 3.2.
set -e
SRC="$(cd "$(dirname "$0")" && pwd)"
OPS="$HOME/learner-ops"
APP="$OPS/sleepmode/app"
PY="${SLEEPMODE_PY:-$OPS/speedbench/venv312/bin/python}"

mkdir -p "$APP"
rm -rf "$APP/sleepmode"
cp -R "$SRC" "$APP/sleepmode"
find "$APP/sleepmode" -name __pycache__ -type d -prune -exec rm -rf {} +
rm -rf "$APP/sleepmode/tests"

cat > "$HOME/Desktop/Sleep Mode.command" <<EOS
#!/bin/bash
# Frees the assistant's memory, then starts sleep mode in the background.
if [ -x "$OPS/assistant/stop.sh" ]; then "$OPS/assistant/stop.sh"; fi
export PYTHONPATH="$APP"
"$PY" -m sleepmode start
echo
echo "Sleep mode is running. Use 'Wake Up' when you want your Mac back."
sleep 5
EOS

cat > "$HOME/Desktop/Wake Up.command" <<EOS
#!/bin/bash
export PYTHONPATH="$APP"
"$PY" -m sleepmode wake
echo
read -p "Press Return to close. " _
EOS

chmod +x "$HOME/Desktop/Sleep Mode.command" "$HOME/Desktop/Wake Up.command"
echo "Installed to $APP"
echo "Desktop launchers: 'Sleep Mode.command' and 'Wake Up.command'"
echo "Python used: $PY"
[ -x "$PY" ] || echo "WARNING: $PY not found. Set SLEEPMODE_PY to a Python 3.9+ and re-run."
