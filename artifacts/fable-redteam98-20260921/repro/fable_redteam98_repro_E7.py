import sys, tempfile
from pathlib import Path
sys.path.insert(0, 'scripts')
from fable_loop90_agent import Loop90Daemon

root = Path(tempfile.mkdtemp())
(root / 'inbox').mkdir()
d = Loop90Daemon(root, cfg={'sleep_threshold': 100000}, idle_seconds=3600.0)
def say(text, name):
    (root / 'inbox' / name).write_text(text)
    for p in sorted((root / 'inbox').glob('*.txt')):
        d.process_file(p)
    print(name, '->', (root / 'outbox' / name).read_text().strip()[:150])

(root/'inbox'/m0.txt).write_bytes(bytes.fromhex('fffe546865206361706974616c'))
say('The capital of Poland is Warsaw', 'm1.txt')
say("Who is Poland's capital?", 'm2.txt')
# EXPECTED (sealed pre-run): final must contain 'Warsaw'
# OBSERVED: BUG -- inbox bytes raised out of process_file (a production daemon would die here)
