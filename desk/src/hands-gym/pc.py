"""BensPC transport; PowerShell encoded UTF-16LE, Python source through stdin."""
import argparse
import base64
import datetime
from pathlib import Path
import subprocess
import sys

p=argparse.ArgumentParser()
p.add_argument('--python',action='store_true')
p.add_argument('--log',required=True)
p.add_argument('command',nargs='?',default='')
a=p.parse_args()
command="Set-Location C:\\Users\\benja\\hands-gym; $ProgressPreference='SilentlyContinue'; "
command += ('& .\\venv\\Scripts\\python.exe -; exit $LASTEXITCODE' if a.python else a.command)
ssh=['ssh','-o','ConnectTimeout=15','-o','BatchMode=yes','benspc-lan',
     'powershell.exe -NoProfile -NonInteractive -EncodedCommand '+base64.b64encode(command.encode('utf-16le')).decode()]
source=sys.stdin.buffer.read() if a.python else None
result=subprocess.run(ssh,input=source,capture_output=True)
with Path(a.log).open('ab') as f:
    f.write(('\nUTC '+datetime.datetime.now(datetime.timezone.utc).isoformat()+'\nPOWERSHELL '+command+'\n').encode())
    if source:f.write(b'PYTHON STDIN\n'+source+b'\n')
    f.write(b'STDOUT\n'+result.stdout+b'\nSTDERR\n'+result.stderr+('\nEXIT %d\n'%result.returncode).encode())
sys.stdout.buffer.write(result.stdout);sys.stderr.buffer.write(result.stderr)
sys.exit(result.returncode)
