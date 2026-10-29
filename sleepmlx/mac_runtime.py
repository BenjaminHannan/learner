"""Prepare or explicitly install the local Mac assistant's LFM3 service patch.

Preparation is read-only for the installed service. Installation checks the
original hashes, writes a backup and manifest first, and refuses changed inputs.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

FILES = ('serve.sh', 'stop.sh', 'config.sh')
CONFIG = {
    'ASSISTANT_ENGINE': '"llama"',
    'ASSISTANT_BIG_MODEL': '"$HOME/learner-ops/lfm3/gguf/LFM3-1.7B-QAD-Q4_0.gguf"',
    'ASSISTANT_LLAMA_SERVER': '"$HOME/learner-ops/lfm3/llama.cpp/build/bin/llama-server"',
}


def _replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('expected exactly one service anchor: ' + old[:100])
    return text.replace(old, new, 1)


def patch_config(text):
    for key, value in CONFIG.items():
        pattern = re.compile(r'^' + key + r'=.*$', re.MULTILINE)
        hits = list(pattern.finditer(text))
        if len(hits) > 1:
            raise ValueError('duplicate config assignment: ' + key)
        if hits:
            text = pattern.sub(lambda _: key + '=' + value, text, count=1)
        else:
            text = text.rstrip('\n') + '\n' + key + '=' + value + '\n'
    return text


def patch_service(serve, stop, config):
    if 'ENGINE="${ASSISTANT_ENGINE:-mlx}"' in serve:
        required = ('sleepmlx.day_adapter', 'sleepmlx.mac_gateway', 'LLAMA_ARGS=', 'learner-ops/lfm3/llama[.]cpp/build/bin/llama-server')
        if not all(item in serve for item in required) or 'sleepmlx[.]mac_gateway' not in stop or 'learner-ops/lfm3/llama[.]cpp/build/bin/llama-server' not in stop:
            raise ValueError('incomplete existing Mac runtime patch')
        return {'serve.sh': serve, 'stop.sh': stop, 'config.sh': patch_config(config)}
    engine = '''ENGINE="${ASSISTANT_ENGINE:-mlx}"
LLAMA_SERVER="${ASSISTANT_LLAMA_SERVER:-$HOME/learner-ops/lfm3/llama.cpp/build/bin/llama-server}"
case "$ENGINE" in mlx|llama) ;; *) echo "Unknown ASSISTANT_ENGINE: $ENGINE"; exit 1 ;; esac
if [ "$ENGINE" = llama ]; then
  export PYTHONPATH="$HOME/learner-ops/sleepmlx-src${PYTHONPATH:+:$PYTHONPATH}"
fi
'''
    serve = _replace_once(serve, 'BIG_MODEL="${ASSISTANT_BIG_MODEL:-mlx-community/Qwen3.6-35B-A3B-4bit}"\n',
                          'BIG_MODEL="${ASSISTANT_BIG_MODEL:-mlx-community/Qwen3.6-35B-A3B-4bit}"\n' + engine)
    old_re = 'big) echo "mlx_lm|mlx_server_persist" ;; small)'
    new_re = 'big) echo "mlx_lm|mlx_server_persist|learner-ops/lfm3/llama[.]cpp/build/bin/llama-server" ;; small)'
    for_name = 'gateway) echo "gateway.py" ;; watchdog)'
    new_name = 'gateway) echo "gateway[.]py|sleepmlx[.]mac_gateway" ;; watchdog)'
    serve = _replace_once(_replace_once(serve, old_re, new_re), for_name, new_name)
    stop = _replace_once(_replace_once(stop, old_re, new_re), for_name, new_name)
    serve = _replace_once(serve, '  need=20; [ $need_small = 1 ] && need=25; [ $need_vlm = 1 ] && need=$((need + 2))',
        '  need=20; [ "$ENGINE" = llama ] && need=4\n  [ $need_small = 1 ] && need=$((need + 5)); [ $need_vlm = 1 ] && need=$((need + 2))')
    a = 'if [ $need_big = 1 ]; then\n  echo "Starting big model ($BIG_MODEL) ..."\n'
    b = 'if [ $need_small = 1 ]; then\n'
    if serve.count(a) != 1 or serve.count(b) != 1:
        raise ValueError('big server block anchor missing or ambiguous')
    start, end = serve.index(a), serve.index(b)
    original = serve[start:end]
    begin = '  echo "Starting big model ($BIG_MODEL) ..."\n'
    old_body = original[len(a):]
    if not old_body.endswith('fi\n'):
        raise ValueError('unexpected big server block')
    new_body = '''  if [ "$ENGINE" = llama ]; then
    [ -x "$LLAMA_SERVER" ] && [ -f "$BIG_MODEL" ] || { echo "LFM3 server or model is missing"; exit 1; }
    # The helper validates the accepted adapter against its manifest. Errors must
    # stop startup; an empty successful result explicitly means use the base.
    adapter="$("$PY" -m sleepmlx.day_adapter --profile lfm3_mps --home "$HOME/learner-ops/sleepmlx" --base-dir "$HOME/learner-ops/lfm3/hf" --base-gguf "$BIG_MODEL")" || { echo "Could not validate sleep adapter"; exit 1; }
    LLAMA_ARGS=(--model "$BIG_MODEL" --alias lfm3 --host 127.0.0.1 --port "$BIG_PORT" -c 8192 -np 1 --jinja -ngl 99 --no-webui)
    [ -n "$adapter" ] && LLAMA_ARGS+=(--lora "$adapter")
    launch big "$LLAMA_SERVER" "${LLAMA_ARGS[@]}"
  else
''' + ''.join('  ' + line for line in old_body[:-3].splitlines(keepends=True)) + '''  fi
fi
'''
    serve = serve[:start] + 'if [ $need_big = 1 ]; then\n' + begin + new_body + serve[end:]
    serve = _replace_once(serve, '  launch gateway "$PY" -u "$DIR/gateway.py" --big-url',
        '  GATEWAY_CMD=("$PY" -u "$DIR/gateway.py")\n  [ "$ENGINE" = llama ] && GATEWAY_CMD=("$PY" -u -m sleepmlx.mac_gateway --gateway-file "$DIR/gateway.py")\n  launch gateway "${GATEWAY_CMD[@]}" --big-url')
    return {'serve.sh': serve, 'stop.sh': stop, 'config.sh': patch_config(config)}


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _syntax(files):
    for name, data in files.items():
        if name.endswith('.sh'):
            proc = subprocess.run(['bash', '-n'], input=data, capture_output=True)
            if proc.returncode:
                raise ValueError('invalid shell syntax in %s: %s' % (name, proc.stderr.decode(errors='replace')))


def prepare(service_dir, output_dir):
    service_dir, output_dir = Path(service_dir), Path(output_dir)
    original = {name: (service_dir / name).read_bytes() for name in FILES}
    patched = patch_service(*(original[name].decode('utf-8') for name in FILES))
    encoded = {name: patched[name].encode() for name in FILES}
    _syntax(encoded)
    output_dir.mkdir(parents=True, exist_ok=False)
    for name, data in encoded.items():
        (output_dir / name).write_bytes(data)
    manifest = {'version': 1, 'files': {name: {'original_sha256': _sha(original[name]), 'patched_sha256': _sha(encoded[name])} for name in FILES}}
    (output_dir / 'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    return manifest


def install(service_dir, prepared_dir, backup_dir):
    service_dir, prepared_dir, backup_dir = map(Path, (service_dir, prepared_dir, backup_dir))
    manifest = json.loads((prepared_dir / 'manifest.json').read_text())
    if manifest.get('version') != 1 or set(manifest.get('files', {})) != set(FILES):
        raise ValueError('invalid preparation manifest')
    original = {name: (service_dir / name).read_bytes() for name in FILES}
    patched = {name: (prepared_dir / name).read_bytes() for name in FILES}
    for name in FILES:
        item = manifest['files'][name]
        if _sha(original[name]) != item['original_sha256'] or _sha(patched[name]) != item['patched_sha256']:
            raise ValueError('file changed after preparation: ' + name)
    _syntax(patched)
    backup_dir.mkdir(parents=True, exist_ok=False)
    for name in FILES:
        (backup_dir / name).write_bytes(original[name])
        shutil.copymode(service_dir / name, backup_dir / name)
    (backup_dir / 'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    replaced = []
    try:
        for name in FILES:
            fd, temporary = tempfile.mkstemp(prefix='.mac-runtime-', dir=service_dir)
            try:
                with os.fdopen(fd, 'wb') as f:
                    f.write(patched[name]); f.flush(); os.fsync(f.fileno())
                shutil.copymode(service_dir / name, temporary)
                os.replace(temporary, service_dir / name)
                replaced.append(name)
            finally:
                if os.path.exists(temporary): os.unlink(temporary)
    except Exception:
        for name in reversed(replaced):
            shutil.copy2(backup_dir / name, service_dir / name)
        raise
    return manifest


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    prep = sub.add_parser('prepare'); prep.add_argument('--service-dir', required=True); prep.add_argument('--output-dir', required=True)
    inst = sub.add_parser('install'); inst.add_argument('--service-dir', required=True); inst.add_argument('--prepared-dir', required=True); inst.add_argument('--backup-dir', required=True)
    args = p.parse_args()
    if args.command == 'prepare': prepare(args.service_dir, args.output_dir)
    else: install(args.service_dir, args.prepared_dir, args.backup_dir)


if __name__ == '__main__':
    main()
