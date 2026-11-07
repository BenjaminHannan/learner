"""Owned, loopback-only Minecraft 1.8.9 lifecycle. Never controls desktop input."""
import argparse
import base64
import json
from pathlib import Path
import shutil
import socket
import struct
import subprocess
import time


ROOT = Path(r'C:\Users\benja\bedwars-play\bedwars1')
SOURCE = Path(r'C:\Users\benja\bedwars-play')
PORT = 25571
RCON_PORT = 25581
BRAIN_PORT = 7796
NAMES = ('BotHands1', 'BotIdle1')


def rcon(command, port=RCON_PORT):
    def receive(connection):
        def exact(length):
            data = bytearray()
            while len(data) < length:
                part = connection.recv(length - len(data))
                if not part:
                    raise ConnectionError('RCON closed')
                data.extend(part)
            return bytes(data)
        length = struct.unpack('<i', exact(4))[0]
        if not 10 <= length <= 1048576:
            raise ValueError('invalid RCON packet')
        payload = exact(length)
        return struct.unpack_from('<ii', payload), payload[8:-2].decode('utf8', 'replace')
    def send(connection, request, kind, text):
        payload = struct.pack('<ii', request, kind) + text.encode() + b'\0\0'
        connection.sendall(struct.pack('<i', len(payload)) + payload)
    with socket.create_connection(('127.0.0.1', port), timeout=8) as connection:
        send(connection, 10, 3, 'bwlocal')
        header, _ = receive(connection)
        if header[0] == -1:
            raise PermissionError('RCON refused authentication')
        send(connection, 11, 2, command)
        for _ in range(4):
            header, text = receive(connection)
            if header[0] == 11:
                return text
    raise ConnectionError('RCON response missing')


def available(port):
    with socket.socket() as connection:
        return connection.connect_ex(('127.0.0.1', port)) != 0


def owned_processes():
    command = ('Get-CimInstance Win32_Process | Where-Object {$_.CommandLine -like '
               "'*bedwars-play*bedwars1*' -and $_.Name -match '^(javaw?|portablemc)\\.exe$'} | "
               'Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress')
    result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', command],
                            capture_output=True, text=True, check=True)
    found = json.loads(result.stdout or '[]')
    return found if isinstance(found, list) else [found]


def detached(arguments, cwd, tag):
    if tag not in {'server', 'controller'}:
        raise ValueError('unknown owned task')
    ROOT.mkdir(parents=True, exist_ok=True)
    wrapper = ROOT / (tag + '-job.py')
    name = 'BEDWARS1-' + tag
    guard = ("$ErrorActionPreference='Stop'; " +
        "$existing=Get-ScheduledTask -TaskName '" + name + "' -ErrorAction SilentlyContinue; " +
        "if($existing -and ($existing.State -eq 'Running' -or $existing.Actions.Arguments -ne '\"" + str(wrapper) + "\"')){throw 'Task already running or ownership mismatch'}; ")
    subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-EncodedCommand',
                    base64.b64encode(guard.encode('utf-16le')).decode()], check=True)
    wrapper.write_text('import subprocess\nfrom pathlib import Path\n' +
        'with open(' + repr(str(ROOT / (tag + '.out'))) + ", 'ab') as stdout, open(" +
        repr(str(ROOT / (tag + '.err'))) + ", 'ab') as stderr:\n" +
        '    process = subprocess.Popen(' + repr(arguments) + ', cwd=' + repr(str(cwd)) +
        ', stdout=stdout, stderr=stderr, stdin=subprocess.DEVNULL, creationflags=' +
        'subprocess.CREATE_NO_WINDOW | subprocess.BELOW_NORMAL_PRIORITY_CLASS)\n' +
        '    Path(' + repr(str(ROOT / (tag + '.pid'))) + ').write_text(str(process.pid))\n' +
        '    code = process.wait()\n' +
        '    Path(' + repr(str(ROOT / (tag + '-exit.json'))) + ').write_text(str(code))\n')
    python = r'C:\Users\benja\hands-gym\venv\Scripts\pythonw.exe'
    command = (guard +
        "$principal=New-ScheduledTaskPrincipal -UserId 'benja' -LogonType Interactive -RunLevel Limited; " +
        "$action=New-ScheduledTaskAction -Execute '" + python + "' -Argument '\"" + str(wrapper) + "\"'; " +
        "$settings=New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours " + ('6' if tag == 'server' else '2') + "); " +
        "Register-ScheduledTask -TaskName '" + name + "' -Action $action -Principal $principal " +
        "-Settings $settings -Force | Out-Null; Start-ScheduledTask -TaskName '" + name + "'")
    subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-EncodedCommand',
                    base64.b64encode(command.encode('utf-16le')).decode()], check=True)
    return {'scheduled_task': name, 'pid_file': str(ROOT / (tag + '.pid'))}


def stage():
    server = ROOT / 'server'
    if server.exists():
        if not (server / 'plugins/PlayKit/config.yml').exists():
            raise RuntimeError('partial staging; inspect before proceeding')
        return {'staged': str(server), 'reused': True}
    if not available(PORT) or not available(RCON_PORT):
        raise RuntimeError('owned server ports are occupied; refusing changes')
    source_server = SOURCE / 'server'
    server.mkdir(parents=True)
    plugins = server / 'plugins'
    plugins.mkdir()
    for name in ['paper-1.8.8-445.jar', 'eula.txt', 'bukkit.yml', 'spigot.yml', 'paper.yml']:
        shutil.copy2(source_server / name, server / name)
    shutil.copytree(source_server / 'cache', server / 'cache')
    for name in ['bedwars-plugin-25.2.jar', 'PlayKit.jar']:
        shutil.copy2(source_server / 'plugins' / name, plugins / name)
    config = plugins / 'BedWars1058'
    config.mkdir()
    for item in (source_server / 'plugins/BedWars1058').iterdir():
        if item.name in {'Arenas', 'Cache', 'cache', 'Maps', 'maps', 'database.db'}:
            continue
        if item.is_file():
            shutil.copy2(item, config / item.name)
        elif item.is_dir() and item.name.lower() in {'languages', 'shop', 'upgrades'}:
            shutil.copytree(item, config / item.name)
    original = Path(r'C:\Users\benja\bedwars-189\server')
    shutil.copytree(original / 'duel', server / 'duel')
    (config / 'Arenas').mkdir()
    shutil.copy2(original / 'plugins/BedWars1058/Arenas/duel.yml', config / 'Arenas/duel.yml')
    text = (config / 'config.yml').read_text(encoding='utf8')
    replacements = {'game-start-regular: 10': 'game-start-regular: 5',
        'game-restart: 45': 'game-restart: 5',
        'next-event-beds-destroy: 360': 'next-event-beds-destroy: 15',
        'next-event-dragon-spawn: 600': 'next-event-dragon-spawn: 15',
        'next-event-game-end: 600': 'next-event-game-end: 15'}
    for before, after in replacements.items():
        if before not in text:
            raise ValueError('source configuration changed: ' + before)
        text = text.replace(before, after)
    (config / 'config.yml').write_text(text, encoding='utf8')
    generators = config / 'generators.yml'
    text = generators.read_text(encoding='utf8')
    text = text.replace('start: 360', 'start: 5').replace('start: 720', 'start: 10')
    generators.write_text(text, encoding='utf8')
    properties = (source_server / 'server.properties').read_text()
    properties = properties.replace('server-port=25570', 'server-port=' + str(PORT))
    properties = properties.replace('rcon.port=25580', 'rcon.port=' + str(RCON_PORT))
    properties = properties.replace('view-distance=6', 'view-distance=3')
    (server / 'server.properties').write_text(properties)
    truth = ROOT / 'truth'
    truth.mkdir(exist_ok=True)
    (plugins / 'PlayKit').mkdir()
    (plugins / 'PlayKit/config.yml').write_text(
        "autojoin: 'duel'\nrejoin: true\nstop-file: ''\n"
        "bot-regex: '^(BotHands1|BotIdle1)$'\ntruth: true\ntruth-dir: '" + str(truth) + "'\n")
    return {'staged': str(server), 'map': 'existing private generated duel', 'round_timers_seconds': [15, 15, 15]}


def launch_server():
    stage()
    if not available(PORT) or not available(RCON_PORT):
        raise RuntimeError('server ports already occupied')
    java = r'C:\Program Files\Eclipse Adoptium\jdk-21.0.5.11-hotspot\bin\java.exe'
    server = ROOT / 'server'
    task = detached([java, '-Xms256M', '-Xmx1536M', '-XX:ActiveProcessorCount=2',
                    '-jar', str(server / 'paper-1.8.8-445.jar'), 'nogui'], server, 'server')
    (ROOT / 'server-owner.json').write_text(json.dumps({'task': task, 'started': time.time()}))
    return {'server_task': task, 'port': PORT, 'root': str(ROOT)}


def join(name):
    raise RuntimeError('BensPC client rendering disabled: iGPU preference was ignored. Use bedwars-brikto.ps1.')


def quit_client(name):
    if name not in NAMES:
        raise ValueError('only owned bot names allowed')
    killed = []
    for row in owned_processes():
        if ('-Dbw.name=' + name) not in row['CommandLine'] and ('-u ' + name) not in row['CommandLine']:
            continue
        pid = int(row['ProcessId'])
        command = (f'$process=Get-CimInstance Win32_Process -Filter "ProcessId={pid}"; '
                   f'if($process.CommandLine -like "*bedwars-play*bedwars1*" -and '
                   f'$process.CommandLine -like "*{name}*"){{Stop-Process -Id {pid} -Force}}else{{exit 2}}')
        subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', command], check=True)
        killed.append(pid)
    return {'name': name, 'killed_own_pids': killed}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['stage', 'launch', 'join', 'quit', 'status', 'stop', 'rcon'])
    parser.add_argument('--name', choices=NAMES, default=NAMES[0])
    parser.add_argument('--text', default='list')
    args = parser.parse_args()
    if args.command == 'stage':
        result = stage()
    elif args.command == 'launch':
        result = launch_server()
    elif args.command == 'join':
        result = join(args.name)
    elif args.command == 'quit':
        result = quit_client(args.name)
    elif args.command == 'rcon':
        result = {'response': rcon(args.text)}
    elif args.command == 'stop':
        result = {'clients': [quit_client(name) for name in NAMES]}
        if not available(RCON_PORT):
            if not any(str(ROOT / 'server') in row['CommandLine'] for row in owned_processes()):
                raise RuntimeError('RCON listener ownership not verified; refusing stop')
            result['server'] = rcon('stop')
    else:
        result = {'processes': owned_processes(), 'server_listening': not available(PORT),
                  'truth': str(ROOT / 'truth')}
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    main()
