"""Logged Tailscale transport for own Bedwars Python commands on BensPC."""
import argparse
import base64
import datetime
from pathlib import Path
import subprocess
import sys

parser = argparse.ArgumentParser()
parser.add_argument('--log', type=Path, required=True)
parser.add_argument('--timeout', type=int, default=180)
args = parser.parse_args()
source = sys.stdin.buffer.read()
script = "Set-Location C:\\Users\\benja\\hands-gym; $ProgressPreference='SilentlyContinue'; & .\\venv\\Scripts\\python.exe -; exit $LASTEXITCODE"
command = ['ssh', '-C', '-o', 'IPQoS=none', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15', 'benspc',
           'powershell.exe -NoProfile -NonInteractive -EncodedCommand '
           + base64.b64encode(script.encode('utf-16le')).decode()]
try:
    result = subprocess.run(command, input=source, capture_output=True, timeout=args.timeout)
except subprocess.TimeoutExpired as error:
    result = subprocess.CompletedProcess(command, 124, error.stdout or b'',
        (error.stderr or b'') + b'\nOwned transport timed out; inspect remote status before retrying.\n')
with args.log.open('ab') as output:
    output.write(('\nUTC ' + datetime.datetime.now(datetime.timezone.utc).isoformat()
                  + '\nCOMMAND ' + repr(command) + '\n').encode())
    output.write(b'PYTHON STDIN\n' + source + b'\nSTDOUT\n' + result.stdout
                 + b'\nSTDERR\n' + result.stderr + ('\nEXIT %d\n' % result.returncode).encode())
sys.stdout.buffer.write(result.stdout)
sys.stderr.buffer.write(result.stderr)
sys.exit(result.returncode)
