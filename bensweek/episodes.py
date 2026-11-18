"""Finding and loading episode files (dev plaintext, sealed zlib+base64)."""
import base64
import json
import zlib

from .world import PKG_DIR

DEV_DIR = PKG_DIR / "episodes" / "dev"
SEALED_PATH = PKG_DIR / "episodes" / "sealed.bin"


def encode_sealed(eps):
    return base64.b64encode(zlib.compress(json.dumps(eps).encode(), 9)).decode()


def decode_sealed(text):
    return json.loads(zlib.decompress(base64.b64decode(text)).decode())


def read_sealed(path=None):
    path = path or SEALED_PATH
    if not path.exists():
        return []
    return decode_sealed(path.read_text())


def load_episodes(split="dev", sealed_ok=False, only=None, dev_dir=None, sealed_path=None):
    if split == "sealed":
        if not sealed_ok:
            raise SystemExit("refusing to load sealed episodes without --i-am-running-the-final-v2-eval")
        eps = read_sealed(sealed_path)
    else:
        eps = [json.loads(p.read_text()) for p in sorted((dev_dir or DEV_DIR).glob("*.json"))]
    if only:
        eps = [e for e in eps if e["id"] in only]
    return eps
