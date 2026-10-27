#!/usr/bin/env python3
"""Sealed, model-free launch-helper import smoke through the existing Mac relay.

Only three explicitly selected r5 Python modules are admitted. Their sealed
bytes are imported from memory with ordinary non-main module names and a
package-shaped virtual __file__ layout. No source or data is written on PC.
This does not check deployment files, model loading, optimization or semantics.
"""
from __future__ import annotations

import __future__
import argparse
import ast
import base64
from collections import Counter
import datetime
import hashlib
import importlib
import importlib.abc
import importlib.util
import inspect
import io
import json
import os
from pathlib import Path, PurePosixPath
import platform
import random
import shutil
import signal
import subprocess
import sys
import tarfile
import time

ROOT = Path(__file__).resolve().parents[1]
OWN = ROOT / 'artifacts/sol-cloud-launch-smoke-20260930'
WATCHER_ROOT = Path('/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27')
PC_LAYOUT = 'C:/Users/benja/sol-cloud-exposure16-r5'
SELECTED = {
    'scripts/sol_cloud_trainonly_v1.py': 'sol_cloud_trainonly_v1',
    'scripts/sol_cloud_exposure16_v5.py': 'sol_cloud_exposure16_v5',
    'scripts/sol_cloud_exposure16_prepare_v5.py': 'sol_cloud_exposure16_prepare_v5',
}
STD_IMPORTS = {'__future__', 'argparse', 'ast', 'collections', 'datetime', 'hashlib',
               'json', 'os', 'pathlib', 'random', 'shutil', 'signal', 'subprocess',
               'sys', 'time'}
STRICT_SSH = ['ssh', '-T', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
              '-o', 'UpdateHostKeys=no', '-o', 'ConnectTimeout=15',
              '-o', 'ServerAliveInterval=5', '-o', 'ServerAliveCountMax=2', 'benspc',
              r'C:\\Users\\benja\\lis300\\venv\\Scripts\\python.exe -X utf8 -B -']
PACKAGE_CAP = 256 * 1024
SOURCE_CAP = 192 * 1024


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def safe_relative(name):
    require(isinstance(name, str) and name and '\\' not in name and ':' not in name,
            'strict relative POSIX source path required')
    path = PurePosixPath(name)
    require(not path.is_absolute() and '..' not in path.parts and '.' not in path.parts
            and path.as_posix() == name, 'relative source containment differs')
    return path


def contained_target(base, name):
    """No extraction occurs; retain the same strict path check for source layout."""
    safe_relative(name)
    base = Path(base).resolve()
    target = (base / name).resolve()
    require(target != base and target.is_relative_to(base), 'source layout escaped root')
    return target


def regular_members_only(members, expected):
    """Pure manual-extraction contract check; never extract or write members."""
    require(len(members) == len(expected) and len(set(m.name for m in members)) == len(members),
            'exact unique member count required')
    require(set(m.name for m in members) == set(expected), 'exact source membership required')
    require(sum(m.size for m in members) <= SOURCE_CAP, 'bounded source members required')
    for member in members:
        safe_relative(member.name)
        require(member.isfile() and not member.issym() and not member.islnk(),
                'source links or special members forbidden')


def tar_capabilities():
    """Exercise actual filter keyword and data filter behavior without writes."""
    record = {'extractall_filter_parameter': 'filter' in inspect.signature(tarfile.TarFile.extractall).parameters,
              'data_filter_callable': callable(getattr(tarfile, 'data_filter', None)),
              'filesystem_extractions': 0}
    memory = io.BytesIO()
    with tarfile.open(fileobj=memory, mode='w'):
        pass
    memory.seek(0)
    try:
        with tarfile.open(fileobj=memory, mode='r:') as archive:
            # Empty members invokes the real API without touching filesystem.
            archive.extractall(path=str(Path.cwd()), members=[], filter='data')
        record['empty_archive_filter_data_call'] = 'supported'
    except (TypeError, ValueError, AttributeError) as error:
        record['empty_archive_filter_data_call'] = 'unavailable'
        record['empty_archive_error_type'] = type(error).__name__
    if record['data_filter_callable']:
        destination = str(Path.cwd() / '__sol_smoke_filter_no_write__')
        regular = tarfile.TarInfo('scripts/smoke.py')
        regular.size = 0
        try:
            filtered = tarfile.data_filter(regular, destination)
            record['regular_member_filter_ok'] = bool(filtered is not None and filtered.isfile())
        except Exception as error:
            record['regular_member_filter_error_type'] = type(error).__name__
        for label, name, linkname in (
                ('parent_escape', '../outside.py', None),
                ('symlink_escape', 'scripts/link.py', '../../outside.py')):
            member = tarfile.TarInfo(name)
            if linkname is not None:
                member.type, member.linkname = tarfile.SYMTYPE, linkname
            try:
                tarfile.data_filter(member, destination)
                record[label + '_rejected'] = False
            except Exception as error:
                record[label + '_rejected'] = True
                record[label + '_error_type'] = type(error).__name__
    return record


def allocation_capabilities():
    """Read-only native allocation-unit metadata relevant to r5 byte budgets."""
    record = {'metadata_only': True, 'filesystem_writes': 0}
    try:
        if platform.system() == 'Windows':
            import ctypes
            function = ctypes.windll.kernel32.GetDiskFreeSpaceW
            record['GetDiskFreeSpaceW_callable'] = callable(function)
            sectors, bytes_per_sector, free, total = [ctypes.c_ulong() for _ in range(4)]
            result = function('C:\\', ctypes.byref(sectors), ctypes.byref(bytes_per_sector),
                              ctypes.byref(free), ctypes.byref(total))
            require(bool(result), 'native allocation query unavailable')
            unit = sectors.value * bytes_per_sector.value
            record.update(volume='C:/', allocation_unit_bytes=unit,
                          r5_allocation_unit_bound_ok=0 < unit <= 64 * 1024)
        else:
            unit = os.statvfs(Path.cwd()).f_frsize
            record.update(api='os.statvfs', allocation_unit_bytes=unit,
                          r5_allocation_unit_bound_ok=0 < unit <= 64 * 1024)
    except Exception as error:
        record['error_type'] = type(error).__name__
    return record


def verify_package(package):
    require(package.get('schema') == 'sol.cloud.offline-smoke-package.v1'
            and package.get('source_files_only') is True
            and package.get('actual_user_day') is False, 'source-only smoke package required')
    entries = package['modules']
    require(isinstance(entries, list) and len(entries) == len(SELECTED), 'three selected modules required')
    require({entry['path'] for entry in entries} == set(SELECTED), 'source whitelist differs')
    decoded = {}
    for entry in entries:
        safe_relative(entry['path'])
        require(entry['module'] == SELECTED[entry['path']], 'module identity differs')
        data = base64.b64decode(entry['source_b64'], validate=True)
        require(sha_bytes(data) == entry['sha256'], 'source byte pin differs')
        decoded[entry['module']] = {'path': entry['path'], 'data': data, 'sha256': entry['sha256']}
    require(sum(len(item['data']) for item in decoded.values()) <= SOURCE_CAP, 'source byte cap exceeded')
    return decoded


class SealedMemoryModules(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    def __init__(self, decoded, layout):
        self.decoded, self.layout = decoded, layout

    def find_spec(self, fullname, path=None, target=None):
        if fullname in self.decoded:
            return importlib.util.spec_from_loader(fullname, self, origin='sealed-memory-source')
        return None

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        item = self.decoded[module.__name__]
        module.__file__ = str(contained_target(self.layout, item['path']))
        module.__cached__ = None
        code = compile(item['data'], module.__file__, 'exec', dont_inherit=True)
        exec(code, module.__dict__)


def run_probe(package, layout, expected_platform=None, expected_version=None):
    os.environ.update(PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1',
                      HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', CUDA_VISIBLE_DEVICES='')
    sys.dont_write_bytecode = True
    decoded = verify_package(package)
    report = {'schema': 'sol.cloud.offline-smoke-host-receipt.v1',
              'observed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'platform': platform.system(), 'version': sys.version,
              'version_info': list(sys.version_info[:3]), 'interpreter': sys.executable,
              'expected_runtime_matches': (expected_platform is None or platform.system() == expected_platform)
                  and (expected_version is None or list(sys.version_info[:3]) == list(expected_version)),
              'tar_capabilities': tar_capabilities(), 'allocation_capabilities': allocation_capabilities(),
              'selected_module_count': len(decoded),
              'source_seal_reference': package['seal_reference'],
              'package_sha256': sha_bytes(canonical(package).encode('utf-8')),
              'virtual_package_root': str(Path(layout).resolve()),
              'module_source_origin': 'sealed-memory-source', 'module_names_are_main': False,
              'actual_host_import_execution': True, 'physical_deployment_files_verified': False,
              'actual_user_day': False, 'model_calls': 0, 'optimizer_updates': 0,
              'GPU_calls': 0, 'data_reads_by_selected_modules': 0, 'PC_writes': 0,
              'offline_environment': True, 'bytecode_writes_disabled': True}
    finder = SealedMemoryModules(decoded, layout)
    previous_path = list(sys.path)
    previous_modules = {name: sys.modules.pop(name, None) for name in decoded}
    active = [False]
    denials = []

    def audit(event, args):
        if not active[0]:
            return
        blocked = False
        if event == 'import':
            blocked = str(args[0]).split('.')[0] not in STD_IMPORTS | set(decoded)
        elif event == 'open':
            # All selected source is already pinned in memory; no data/code reads needed.
            blocked = True
        elif event.startswith(('socket.', 'subprocess.', 'os.exec', 'os.spawn', 'os.posix_spawn')):
            blocked = True
        elif event in ('os.system', 'os.fork', 'os.remove', 'os.rename', 'os.mkdir', 'os.rmdir', 'os.listdir', 'os.scandir'):
            blocked = True
        if blocked:
            denials.append({'event': event})
            raise RuntimeError('selected-module smoke attempted a forbidden side effect')

    sys.addaudithook(audit)
    sys.meta_path.insert(0, finder)
    report['modules'] = []
    try:
        for name, item in decoded.items():
            record = {'module': name, 'path': item['path'], 'sha256': item['sha256']}
            try:
                ast.parse(item['data'], filename=item['path'])
                record['syntax_ok'] = True
                active[0] = True
                module = importlib.import_module(name)
                active[0] = False
                require(module.__name__ == name and name != '__main__', 'module-main execution forbidden')
                record['import_ok'] = True
                record['virtual_file'] = module.__file__
            except Exception as error:
                active[0] = False
                record['import_ok'] = False
                record['error_type'] = type(error).__name__
            report['modules'].append(record)
    finally:
        active[0] = False
        sys.meta_path.remove(finder)
        sys.path[:] = previous_path
        for name, previous in previous_modules.items():
            sys.modules.pop(name, None)
            if previous is not None:
                sys.modules[name] = previous
    report['denied_side_effects'] = denials
    report['pass'] = report['expected_runtime_matches'] and not denials and all(item['import_ok'] for item in report['modules'])
    report['limits'] = ['Only these three source modules were imported; no broad training closure was admitted.',
                        'Host interpreter execution uses sealed memory sources and virtual package layout, not deployment files.',
                        'No main/gates/run/build functions, model loaders, data loaders or optimizers were called.',
                        'Empty archive API and filter calls test tar capabilities; no archive was extracted to disk.']
    return report


def write_new(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True) + '\n')


def build_package(seal_path, expected_sha256, output):
    seal_path = Path(seal_path).resolve()
    require(seal_path == ROOT / 'artifacts/sol-cloud-exposure16-20260930/r5/SEAL.json', 'exact r5 metadata seal required')
    raw = seal_path.read_bytes()
    require(sha_bytes(raw) == expected_sha256, 'external r5 seal pin changed')
    seal = json.loads(raw)
    package = {'schema': 'sol.cloud.offline-smoke-package.v1', 'source_files_only': True,
               'actual_user_day': False, 'seal_reference': {'path': seal_path.relative_to(ROOT).as_posix(),
                                                          'sha256': expected_sha256}, 'modules': []}
    for path, name in SELECTED.items():
        data = contained_target(ROOT, path).read_bytes()
        require(sha_bytes(data) == seal['files'][path], 'selected source differs from exposure seal')
        # Syntax evidence for named runtimes is distinct from future host execution.
        ast.parse(data, filename=path, feature_version=(3, 9))
        ast.parse(data, filename=path, feature_version=(3, 10))
        package['modules'].append({'path': path, 'module': name, 'sha256': sha_bytes(data),
                                   'source_b64': base64.b64encode(data).decode('ascii')})
    verify_package(package)
    data = canonical(package).encode('utf-8')
    require(len(data) <= PACKAGE_CAP, 'source package byte cap exceeded')
    output = Path(output).resolve()
    require(output.is_relative_to(OWN.resolve()) and output != OWN.resolve(), 'new owned smoke output required')
    output.mkdir(parents=True, exist_ok=False)
    with (output / 'SOURCE-PACKAGE.json').open('xb') as stream:
        stream.write(data)
    write_new(output / 'PREPARATION.json', {'package_sha256': sha_bytes(data), 'package_bytes': len(data),
              'selected_source_count': len(SELECTED), 'selected_source_bytes': sum(len(base64.b64decode(item['source_b64'])) for item in package['modules']),
              'syntax_python39_and310': True, 'actual_remote_host_imports': False,
              'model_calls': 0, 'optimizer_updates': 0, 'data_content_read': False,
              'reference': 'https://docs.python.org/3/library/tarfile.html#supporting-older-python-versions'})
    return package


def probe_source(package, layout, expected_platform, expected_version):
    # A standalone stdin probe needs no remote files or code extraction.
    data = Path(__file__).read_text(encoding='utf-8')
    prefix = data.split("\nif __name__ == '__main__':", 1)[0]
    header = '__file__ = ' + repr(str(Path(layout) / 'scripts/sol_cloud_offline_launch_smoke_v1.py')) + '\n'
    call = '\n_receipt = run_probe(' + repr(package) + ', ' + repr(layout) + ', ' + repr(expected_platform) + ', ' + repr(expected_version) + ')\n'
    tail = "print(json.dumps(_receipt, sort_keys=True), flush=True)\nraise SystemExit(0 if _receipt['pass'] else 1)\n"
    source = header + prefix + call + tail
    ast.parse(source, feature_version=(3, 9))
    return source


def read_package(path, expected):
    raw = Path(path).read_bytes()
    require(len(raw) <= PACKAGE_CAP and sha_bytes(raw) == expected, 'external source package pin changed')
    package = json.loads(raw)
    verify_package(package)
    return package


def relay(package, output, pc_layout):
    require(platform.system() == 'Darwin' and sys.version_info[:3] == (3, 9, 6), 'verified native Mac runtime required')
    require(Path.cwd().resolve() == WATCHER_ROOT.resolve(), 'known watcher publisher cwd required')
    output = Path(output).resolve()
    require(output.is_relative_to(OWN.resolve()) and output != OWN.resolve(), 'owned receipt directory required')
    output.mkdir(parents=True, exist_ok=False)
    outcomes = []
    for host, command, layout, system, version in (
            ('Mac', ['/usr/bin/python3', '-B', '-'], str(WATCHER_ROOT), 'Darwin', [3, 9, 6]),
            ('PC', STRICT_SSH, pc_layout, 'Windows', [3, 10, 9])):
        source = probe_source(package, layout, system, version)
        result = subprocess.run(command, input=source, text=True, encoding='utf-8',
                                capture_output=True, timeout=45,
                                env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1', HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1'))
        if len(result.stdout) > 32768:
            raise RuntimeError('bounded host smoke receipt exceeded cap')
        try:
            receipt = json.loads(result.stdout)
            require(receipt.get('schema') == 'sol.cloud.offline-smoke-host-receipt.v1', 'host smoke receipt schema differs')
        except Exception:
            receipt = {'schema': 'sol.cloud.offline-smoke-failure.v1', 'host': host,
                       'returncode': result.returncode, 'raw_diagnostics_suppressed': True}
        write_new(output / (host.upper() + '-RECEIPT.json'), receipt)
        outcomes.append({'host': host, 'returncode': result.returncode,
                         'pass': receipt.get('pass') is True})
    write_new(output / 'RELAY.json', {'outcomes': outcomes, 'actual_user_day': False,
                                      'model_calls': 0, 'optimizer_updates': 0, 'PC_writes': 0})
    return all(item['pass'] and item['returncode'] == 0 for item in outcomes)


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='action', required=True)
    build = sub.add_parser('build')
    build.add_argument('--seal', required=True)
    build.add_argument('--seal-sha256', required=True)
    build.add_argument('--output', required=True)
    for name in ('local-check', 'relay'):
        action = sub.add_parser(name)
        action.add_argument('--package', required=True)
        action.add_argument('--package-sha256', required=True)
        action.add_argument('--output', required=True)
        action.add_argument('--pc-layout', default=PC_LAYOUT)
    args = parser.parse_args()
    if args.action == 'build':
        build_package(args.seal, args.seal_sha256, args.output)
        return 0
    package = read_package(args.package, args.package_sha256)
    if args.action == 'relay':
        return 0 if relay(package, args.output, args.pc_layout) else 1
    receipt = run_probe(package, str(ROOT))
    output = Path(args.output).resolve()
    require(output.is_relative_to(OWN.resolve()) and output != OWN.resolve(), 'owned local receipt required')
    output.parent.mkdir(parents=True, exist_ok=True)
    receipt['claim_scope'] = 'current local interpreter only; actual Mac/PC imports remain unexecuted'
    write_new(output, receipt)
    print(json.dumps(receipt, sort_keys=True), flush=True)
    return 0 if receipt['pass'] else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        print(json.dumps({'smoke_error_type': type(error).__name__, 'raw_diagnostics_suppressed': True}), flush=True)
        raise SystemExit(1)
