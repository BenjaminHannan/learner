from pathlib import Path
import argparse
import os
import shutil
import subprocess


def build(output, node_include=None):
    repo = Path(__file__).resolve().parents[2]
    node = Path(shutil.which('node') or '/opt/homebrew/bin/node').resolve()
    headers = Path(node_include or os.environ.get('NODE_INCLUDE_DIR') or node.parent.parent / 'include/node')
    if not (headers / 'node_api.h').is_file():
        raise RuntimeError(f'Node API headers missing at {headers}; set NODE_INCLUDE_DIR')
    output.mkdir(parents=True, exist_ok=True)
    for name, source in [('capture', 'recorder.swift'), ('canary', 'secure-canary.swift')]:
        target = output / f'{name}.dylib'
        subprocess.run(['swiftc', '-O', '-target', 'arm64-apple-macos13.0', '-emit-library', '-module-name', 'Glim_' + name, str(repo / 'helper/hands-toy' / source), '-o', str(target)], check=True)
        subprocess.run(['codesign', '--force', '--sign', '-', str(target)], check=True)
    target = output / 'native-bridge.node'
    subprocess.run(['clang++', '-arch', 'arm64', '-std=c++17', '-bundle', '-undefined', 'dynamic_lookup', '-I' + str(headers), str(repo / 'helper/hands-toy/native-bridge.cc'), '-o', str(target)], check=True)
    subprocess.run(['codesign', '--force', '--sign', '-', str(target)], check=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--node-include')
    args = parser.parse_args()
    build(args.output, args.node_include)
