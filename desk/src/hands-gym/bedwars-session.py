"""Whitelisted Mac lifecycle commands for Glim; never sends desktop input."""
import argparse
import base64
import json
from pathlib import Path
import subprocess
import time


def powershell(host, source):
    command = ['ssh', '-C', '-o', 'IPQoS=none', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15']
    command += [host, 'powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -EncodedCommand '
                + base64.b64encode(source.encode('utf-16le')).decode()]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        return {'command': command, 'source': source, 'stdout': '',
                'stderr': 'Owned lifecycle transport timed out after 120 seconds; inspect status before retrying.', 'exit': 124}
    return {'command': command, 'source': source, 'stdout': result.stdout,
            'stderr': result.stderr, 'exit': result.returncode}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['launch', 'join', 'quit', 'status'])
    parser.add_argument('--name', choices=['BotHands1', 'BotIdle1', 'both'], default='both')
    parser.add_argument('--log', type=Path, required=True)
    args = parser.parse_args()
    records = []
    if args.command in {'launch', 'status'}:
        verb = 'launch' if args.command == 'launch' else 'status'
        records.append(powershell('benspc', "$ErrorActionPreference='Stop'; "
            "Set-Location C:\\Users\\benja\\hands-gym; "
            "& .\\venv\\Scripts\\python.exe -m hands_gym.bedwars_tools " + verb + '; exit $LASTEXITCODE'))
    if args.command in {'join', 'quit', 'status'}:
        verb = {'join': 'launch', 'quit': 'quit', 'status': 'status'}[args.command]
        names = ['BotHands1', 'BotIdle1'] if args.name == 'both' else [args.name]
        for name in names:
            records.append(powershell('brikto', "$ErrorActionPreference='Stop'; "
                "& C:\\Users\\Public\\bedwars1\\bedwars-brikto.ps1 -Command " + verb
                + ' -Name ' + name + '; exit $LASTEXITCODE'))
            if records[-1]['exit']:
                break
    with args.log.open('a') as trace:
        for record in records:
            trace.write(json.dumps({'wall_ms': int(time.time() * 1000), **record}) + '\n')
    print(json.dumps(records, indent=2))
    raise SystemExit(max(record['exit'] for record in records))


if __name__ == '__main__':
    main()
