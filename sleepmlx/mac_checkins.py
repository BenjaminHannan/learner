"""Prepare or explicitly install the external Mac Sleepmode check-in patch.

Prepare reads the external sources but never changes them. Install verifies all
original and prepared hashes, backs up all files, and rolls back failed writes.
"""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

FILES = ('checkin.py', 'config.py', 'scheduler.py')
SELECTOR = '''def verified_triage_lora(cfg):
    """Only the centralized completed-export selector may authorize an adapter."""
    import pathlib
    import tempfile
    try:
        worker = list(cfg.worker_cmd or [])
        # The executable and module/profile must be the configured LFM3 worker;
        # reject ambiguous or duplicate profile options instead of guessing.
        if len(worker) < 4 or worker[1:3] != ["-m", "sleepmlx.worker"]:
            return ""
        profiles = []
        for i, value in enumerate(worker[3:], 3):
            if value == "--profile": profiles.append(worker[i + 1] if i + 1 < len(worker) else "")
            elif value.startswith("--profile="): profiles.append(value.split("=", 1)[1])
        if profiles != ["lfm3_mps"]:
            return ""
        raw_lora = pathlib.Path(os.path.expanduser(cfg.triage_lora))
        if raw_lora.name != "adapter.gguf":
            return ""
        home = raw_lora.parent.resolve()
        models = []
        server = list(cfg.triage_server_cmd or [])
        for i, value in enumerate(server):
            if value in ("-m", "--model"): models.append(server[i + 1] if i + 1 < len(server) else "")
            elif value.startswith("--model="): models.append(value.split("=", 1)[1])
        if len(models) != 1 or not models[0]:
            return ""
        command = [os.path.expanduser(worker[0]), "-m", "sleepmlx.day_adapter", "--json", "--home", str(home), "--profile", profiles[0], "--base-gguf", os.path.expanduser(models[0])]
        env = os.environ.copy()
        extra = dict(cfg.worker_env or {})
        pythonpath = extra.pop("PYTHONPATH", "")
        env.update(extra)
        if pythonpath: env["PYTHONPATH"] = pythonpath + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
        if extra.get("SLEEPMLX_MODEL_DIR"): command += ["--base-dir", os.path.expanduser(extra["SLEEPMLX_MODEL_DIR"])]
        with tempfile.TemporaryFile() as output:
            result = subprocess.run(command, env=env, stdout=output, stderr=subprocess.DEVNULL, timeout=10, check=False)
            if result.returncode != 0: return ""
            output.seek(0); data = output.read(65537)
        if len(data) > 65536: return ""
        selection = json.loads(data.decode("utf-8"))
        adapter = selection.get("adapter") if isinstance(selection, dict) else None
        if not isinstance(adapter, str): return ""
        candidate = pathlib.Path(adapter)
        allowed = (home / "adapter.gguf", home / "adapter.prev.gguf")
        if candidate not in allowed or candidate.is_symlink() or not candidate.is_file() or candidate.resolve().parent != home:
            return ""
        return str(candidate)
    except (OSError, ValueError, TypeError, AttributeError, subprocess.SubprocessError):
        return ""


'''
OLD_START = '''    lora = os.path.expanduser(cfg.triage_lora) if cfg.triage_lora else ""
    if lora and os.path.exists(lora) and lora_matches(lora, cfg.lora_base):
        cmd += ["--lora", lora]
'''
NEW_START = '''    lora = verified_triage_lora(cfg)
    if lora:
        cmd += ["--lora", lora]
'''
OLD_DAY = '    daytime_model: str = "qwen36 (the assistant gateway)"   # named in the morning summary: what Ben\'s daytime chats run on'
NEW_DAY = '    daytime_model: str = "LFM3 (the assistant gateway)"   # named in the morning summary: what Ben\'s daytime chats run on'
OLD_SUMMARY = '''            lines += ["", "Where it is used: the LFM3 helper that reads your mail at check-ins (triage_lora, loaded only when adapter.gguf.json "
                      "names %s) and `sleepmlx recall`. " % getattr(sc.cfg, "lora_base", "LFM3") +
                      "Your daytime model, %s, is not changed: an adapter only fits the base it was trained on (%s)." % (
                          getattr(sc.cfg, "daytime_model", "the assistant"), getattr(sc.cfg, "lora_base", "LFM3"))]
'''
NEW_SUMMARY = '''            lines += ["", "Daytime LFM3 and check-ins can use matching verified exports; pending or failed exports are excluded."]
'''


def _once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('expected exactly one check-in patch anchor: ' + old[:80])
    return text.replace(old, new, 1)


def patch_sources(checkin, config, scheduler):
    checkin = _once(checkin, OLD_START, NEW_START)
    checkin = _once(checkin, 'def start_triage_server(cfg: Config):\n', SELECTOR + 'def start_triage_server(cfg: Config):\n')
    return {'checkin.py': checkin, 'config.py': _once(config, OLD_DAY, NEW_DAY), 'scheduler.py': _once(scheduler, OLD_SUMMARY, NEW_SUMMARY)}


def _sha(data): return hashlib.sha256(data).hexdigest()


def _syntax(files):
    for name, data in files.items(): ast.parse(data.decode('utf-8'), filename=name)


def prepare(source_dir, output_dir):
    source_dir, output_dir = Path(source_dir), Path(output_dir)
    originals = {name: (source_dir / name).read_bytes() for name in FILES}
    patched = patch_sources(*(originals[name].decode('utf-8') for name in FILES))
    encoded = {name: patched[name].encode('utf-8') for name in FILES}
    _syntax(encoded)
    output_dir.mkdir(parents=True, exist_ok=False)
    for name in FILES: (output_dir / name).write_bytes(encoded[name])
    manifest = {'version': 1, 'files': {name: {'original_sha256': _sha(originals[name]), 'patched_sha256': _sha(encoded[name])} for name in FILES}}
    (output_dir / 'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    return manifest


def _replace(path, data, mode_source):
    fd, temporary = tempfile.mkstemp(prefix='.mac-checkin-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        shutil.copymode(mode_source, temporary)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)


def install(source_dir, prepared_dir, backup_dir):
    source_dir, prepared_dir, backup_dir = map(Path, (source_dir, prepared_dir, backup_dir))
    manifest = json.loads((prepared_dir / 'manifest.json').read_text())
    if manifest.get('version') != 1 or set(manifest.get('files', {})) != set(FILES): raise ValueError('invalid preparation manifest')
    originals = {name: (source_dir / name).read_bytes() for name in FILES}
    patched = {name: (prepared_dir / name).read_bytes() for name in FILES}
    for name in FILES:
        item = manifest['files'][name]
        if _sha(originals[name]) != item['original_sha256'] or _sha(patched[name]) != item['patched_sha256']:
            raise ValueError('file changed after preparation: ' + name)
    _syntax(patched)
    backup_dir.mkdir(parents=True, exist_ok=False)
    for name in FILES:
        (backup_dir / name).write_bytes(originals[name]); shutil.copymode(source_dir / name, backup_dir / name)
    (backup_dir / 'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    replaced = []
    try:
        for name in FILES:
            _replace(source_dir / name, patched[name], source_dir / name); replaced.append(name)
    except Exception:
        for name in reversed(replaced): _replace(source_dir / name, originals[name], backup_dir / name)
        raise
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('prepare'); p.add_argument('--source-dir', required=True); p.add_argument('--output-dir', required=True)
    p = sub.add_parser('install'); p.add_argument('--source-dir', required=True); p.add_argument('--prepared-dir', required=True); p.add_argument('--backup-dir', required=True)
    args = parser.parse_args()
    if args.command == 'prepare': prepare(args.source_dir, args.output_dir)
    else: install(args.source_dir, args.prepared_dir, args.backup_dir)

if __name__ == '__main__': main()
