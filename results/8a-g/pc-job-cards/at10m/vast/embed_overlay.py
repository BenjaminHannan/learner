#!/usr/bin/env python3
"""Put ../overlay/train.py into at10m_box.sh (gzip -9, mtime 0, base64) and set OVERLAY_TRAIN_SHA. Run after any change of the overlay: python3 embed_overlay.py
selftest.sh decodes the embedded copy and checks it against the pin and against ../overlay/train.py."""
import base64, gzip, hashlib, re, sys
from pathlib import Path

H = Path(__file__).resolve().parent
src = (H.parent / 'overlay' / 'train.py').read_bytes()
sha = hashlib.sha256(src).hexdigest()
b64 = base64.b64encode(gzip.compress(src, 9, mtime=0)).decode()
text = '\n'.join(b64[i:i + 100] for i in range(0, len(b64), 100))
box = H / 'at10m_box.sh'
s = box.read_text()
s, n1 = re.subn(r"(overlay_b64\(\) \{ cat <<'B64'\n).*?(\nB64\n\})", lambda m: m.group(1) + text + m.group(2), s, flags=re.S)
s, n2 = re.subn(r'^OVERLAY_TRAIN_SHA=[0-9a-f@A-Z]+', 'OVERLAY_TRAIN_SHA=' + sha, s, flags=re.M)
assert n1 == 1 and n2 == 1, (n1, n2)
box.write_text(s)
print('embedded overlay/train.py', sha, len(src), 'bytes ->', len(text), 'base64 chars')
