"""One exact cached wheel, conditional on explicit Ben approval. No other deletion."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys

BODY = Path('C:/Users/benja/AppData/Local/pip/Cache/http-v2/6/b/a/1/4/6ba143c6fba3bb4981bc76d8467c3ac4660ba96dc240cdf080bd75a5.body')
SAFETY_SOURCE_SHA256 = '6940b080a62d7816809fc84585536ec37c394b28ddb35f188c4dafac83ada132'
SAFETY_RAW_SHA256 = '66894f07bd9fafecfd2b0d2128158cfad81318f79605656eec8c4f9731833190'

def validate_approval(approval):
    if not isinstance(approval, dict) or approval.get('approved') is not True:
        raise PermissionError('Explicit Ben approval is required before any action')
    if approval.get('authorized_by') != 'Ben' or approval.get('action') != 'unlink-one-exact-pip-cache-body':
        raise PermissionError('Exact single-file approval differs')
    if approval.get('path') != BODY.as_posix() or approval.get('safety_raw_sha256') != SAFETY_RAW_SHA256:
        raise PermissionError('Approved exact cache path/evidence differs')
    ref = approval.get('parent_authorization_reference')
    if not isinstance(ref, str) or not ref.strip() or len(ref) > 1024:
        raise PermissionError('Actual parent-recorded Ben authorization reference required')

def perform(approval, safety_source, expected):
    validate_approval(approval)
    if platform.system() != 'Windows' or sys.version_info[:3] != (3, 10, 9):
        raise RuntimeError('Verified native PC runtime required')
    if hashlib.sha256(safety_source.encode('utf8')).hexdigest() != SAFETY_SOURCE_SHA256:
        raise ValueError('Pinned metadata-only safety source differs')
    if set(expected) != {'bytes', 'mtime_ns', 'ctime_ns', 'file_id', 'nlink'}:
        raise ValueError('Exact integer identity fields required')
    # All JSON identity integers are decoded in Python; no JavaScript number conversion.
    namespace = {'__name__': 'cache_safety_before_approved_action'}
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        exec(compile(safety_source, '<pinned-cache-safety>', 'exec'), namespace)
    checked = namespace['record']
    if checked.get('bounded_safety_checks_pass') is not True or checked.get('cached_version_installed_in_project_venv') is not True:
        raise RuntimeError('Fresh bounded stable/package/process safety check refused')
    if checked.get('before') != expected or checked.get('after') != expected or BODY.is_symlink():
        raise RuntimeError('Exact original cache identity changed; preserved')
    # Check active roles again after the two-second stability interval, immediately before unlink.
    probe = subprocess.run(['powershell.exe', '-NoLogo', '-NoProfile', '-NonInteractive', '-Command', namespace['probe']], capture_output=True, timeout=12)
    if probe.returncode != 0 or len(probe.stdout) > 65536:
        raise RuntimeError('Immediate process safety query failed; preserved')
    active = json.loads(probe.stdout.decode('utf-8-sig'))
    if not isinstance(active, list) or active:
        raise RuntimeError('Immediate pip/install/download process candidate; preserved')
    if namespace['stamp'](BODY) != expected:
        raise RuntimeError('Identity changed before action; preserved')
    before_free = shutil.disk_usage('C:/').free
    before = {'schema': 'sol.cloud.single-cache-removal.v1', 'phase': 'admitted-before-one-unlink', 'path': str(BODY),
              'approval': approval, 'before': expected, 'C_free_before_bytes': before_free,
              'fresh_safety': checked, 'immediate_active_candidates': active,
              'open_handle_coverage': 'not inspected; point-in-time role checks only', 'other_files_touched': 0}
    print(json.dumps(before, sort_keys=True), flush=True)
    BODY.unlink()
    after = {'schema': 'sol.cloud.single-cache-removal.v1', 'phase': 'after-one-unlink', 'path': str(BODY),
             'deleted': True, 'target_exists_after': BODY.exists(), 'C_free_before_bytes': before_free,
             'C_free_after_bytes': shutil.disk_usage('C:/').free, 'approved_by': 'Ben', 'deletion_count': 1,
             'companion_metadata_deleted': False, 'installed_packages_deleted': False, 'models_or_evidence_deleted': False,
             'model_calls': 0, 'optimizer_updates': 0}
    print(json.dumps(after, sort_keys=True), flush=True)
    return 0
