#!/bin/sh
# Rebuild preview/ from the delivered chapters in chapters-out/ (kit copy in a temp dir; needs Node 22 on PATH, e.g. animations/.tools/node-v22.23.3-darwin-arm64/bin).
set -e
HERE=$(cd "$(dirname "$0")" && pwd); T=$(mktemp -d)
cp -R "$HERE/kit/." "$T/"; mkdir -p "$T/chapters" "$T/content"
for d in "$HERE"/chapters-out/ch*/; do c=$(basename "$d"); [ -f "$d$c.json" ] && [ -f "$d$c.js" ] && cp "$d$c.json" "$T/content/" && cp "$d$c.js" "$T/chapters/"; done
(cd "$T" && node tools/merge.mjs && node tools/mkindex.mjs && node tools/audit.mjs | tail -3)
P="$HERE/preview"; mkdir -p "$P"; cp "$P/player.js" "$T/player.js" 2>/dev/null || true
python3 - "$T" <<'PY'
import sys; t=sys.argv[1]; s=open(t+'/index.html').read().replace('</body>','<script src="player.js"></script>\n  </body>'); open(t+'/watch.html','w').write(s)
PY
cp -R "$T/vendor" "$T/content" "$T/chapters" "$T/style.css" "$T/content.js" "$T/kit.js" "$T/main.js" "$T/only.js" "$T/index.html" "$T/watch.html" "$P/"
echo "preview rebuilt in $P"
