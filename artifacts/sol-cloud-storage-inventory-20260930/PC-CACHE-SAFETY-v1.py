"""One authorized cache file: metadata-only; no deletion or package/model load."""
import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import zipfile

BODY = Path('C:/Users/benja/AppData/Local/pip/Cache/http-v2/6/b/a/1/4/6ba143c6fba3bb4981bc76d8467c3ac4660ba96dc240cdf080bd75a5.body')
EXPECTED_BYTES = 2753152602
START = time.monotonic()

def stamp(path):
    s = path.stat()
    return dict(bytes=s.st_size, mtime_ns=s.st_mtime_ns, ctime_ns=s.st_ctime_ns,
                file_id=[s.st_dev, s.st_ino], nlink=s.st_nlink)

def identity(prefix):
    result = {}
    for line in prefix.decode('utf-8', errors='replace').splitlines():
        for key in ('Name', 'Version'):
            if line.startswith(key + ': '):
                result[key] = line[len(key) + 2:][:160]
    return result

record = dict(schema='sol.cloud.pip-cache-safety.v1', path=str(BODY),
              expected_bytes=EXPECTED_BYTES, cache_kind='pip HTTP-v2 response body',
              deletion_authorized=False, deleted=False, PC_writes=0,
              model_calls=0, optimizer_updates=0, credentials_printed=False,
              open_handle_coverage='not inspected; no handle tools installed')
try:
    before = stamp(BODY)
    record['before'] = before
    record['matches_original_size'] = before['bytes'] == EXPECTED_BYTES
    record['companion_cache_metadata_exists'] = BODY.with_suffix('').is_file()
    with zipfile.ZipFile(BODY) as archive:
        names = archive.namelist()
        metadata = [n for n in names if n.endswith('.dist-info/METADATA')]
        record['archive_metadata'] = dict(member_count=len(names),
            dist_info_metadata_members=metadata[:4], metadata_members_truncated=len(metadata)>4,
            tensor_or_package_payloads_read=False)
        if len(metadata) == 1:
            with archive.open(metadata[0]) as stream:
                record['package_identity'] = identity(stream.read(8192))
    package = record.get('package_identity', {})
    installed = []
    root = Path('C:/Users/benja/lis300/venv/Lib/site-packages')
    name = package.get('Name', '').lower().replace('-', '_')
    if name and name.replace('_', '').isalnum():
        for directory in root.glob(name + '-*.dist-info'):
            candidate = directory / 'METADATA'
            if candidate.is_file():
                with candidate.open('rb') as stream:
                    found = identity(stream.read(8192))
                installed.append(dict(metadata_path=str(candidate), **found))
    record['installed_package_metadata'] = installed
    record['cached_version_installed_in_project_venv'] = any(
        r.get('Name', '').lower() == package.get('Name', '').lower()
        and r.get('Version') == package.get('Version') for r in installed)
    probe = r'''$ErrorActionPreference='Stop'; $cacheSafety=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -match '(?i)(^pip|^uv\.exe$|^msiexec\.exe$|^curl\.exe$|^wget\.exe$|^aria2c|^bitsadmin\.exe$|setup|installer)' -or ($_.Name -match '(?i)^(python|pythonw|py)\.exe$' -and $_.CommandLine -match '(?i)(\bpip\b.*\b(install|download|wheel)\b|\buv\b.*\b(install|download)\b)') } | ForEach-Object { [pscustomobject]@{ pid=$_.ProcessId; name=$_.Name; commandline_omitted=$true } }); ConvertTo-Json -InputObject $cacheSafety -Compress'''
    completed = subprocess.run(['powershell.exe','-NoLogo','-NoProfile','-NonInteractive',
                                '-Command',probe], capture_output=True, timeout=12)
    record['process_probe_returncode'] = completed.returncode
    if completed.returncode == 0:
        candidates = json.loads(completed.stdout.decode('utf-8-sig'))
        if not isinstance(candidates, list):
            raise ValueError('expected process list')
        record['active_pip_install_download_candidates'] = candidates
        record['process_probe_complete'] = True
    else:
        record['process_probe_complete'] = False
        record['process_probe_stderr_bytes'] = len(completed.stderr)
    time.sleep(2)
    after = stamp(BODY)
    record['after'] = after
    record['stable_during_metadata_probe'] = before == after
    identified = set(package) == {'Name','Version'} and len(metadata) == 1
    record['identified_cached_wheel'] = identified
    record['bounded_safety_checks_pass'] = bool(identified and
        record['matches_original_size'] and before['nlink'] == 1 and before == after and
        record.get('process_probe_complete') and not record.get('active_pip_install_download_candidates'))
    record['scope_limit'] = 'Point-in-time process-name/command-role check, not exhaustive handle proof or future network availability; installed package/model files unchanged.'
except Exception as error:
    record['error_type'] = type(error).__name__
    record['bounded_safety_checks_pass'] = False
record['completed_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
record['wall_seconds'] = time.monotonic() - START
record['C_free_bytes'] = shutil.disk_usage('C:/').free
print(json.dumps(record, sort_keys=True), flush=True)
