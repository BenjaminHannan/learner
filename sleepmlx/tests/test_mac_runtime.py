import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from sleepmlx.mac_runtime import patch_service, prepare, install

SERVE = '''#!/bin/bash
BIG_MODEL="${ASSISTANT_BIG_MODEL:-mlx-community/Qwen3.6-35B-A3B-4bit}"
ours_re() { case "$1" in big) echo "mlx_lm|mlx_server_persist" ;; small) echo "mlx_lm" ;; gateway) echo "gateway.py" ;; watchdog) echo "watchdog" ;; esac; }
  need=20; [ $need_small = 1 ] && need=25; [ $need_vlm = 1 ] && need=$((need + 2))
if [ $need_big = 1 ]; then
  echo "Starting big model ($BIG_MODEL) ..."
  if [ "$PERSIST_CACHE" = 1 ]; then
    BIG_CMD=("$PY" "$DIR/mlx_server_persist.py" --cache-dir "$RUN/kvcache")
  else
    BIG_CMD=("$PY" -m mlx_lm.server)
  fi
  launch big "${BIG_CMD[@]}" --model "$BIG_MODEL"
fi
if [ $need_small = 1 ]; then
  :
fi
if [ $need_gw = 1 ]; then
  launch gateway "$PY" -u "$DIR/gateway.py" --big-url "http://127.0.0.1:$BIG_PORT"
fi
'''
STOP = '''#!/bin/bash
ours_re() { case "$1" in big) echo "mlx_lm|mlx_server_persist" ;; small) echo "mlx_lm" ;; gateway) echo "gateway.py" ;; watchdog) echo "watchdog" ;; esac; }
'''
CONFIG = '''# keep this configuration
ASSISTANT_BIG_MODEL="old-model"
ASSISTANT_SMALL_MODEL="untouched"
'''


class MacRuntimeTest(unittest.TestCase):
    def files(self, path):
        path.mkdir()
        for name, text in [('serve.sh', SERVE), ('stop.sh', STOP), ('config.sh', CONFIG)]:
            (path / name).write_text(text)

    def test_prepare_install_and_idempotent_config(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); service = root / 'service'; self.files(service)
            prepared = root / 'prepared'; backup = root / 'backup'
            prepare(service, prepared)
            self.assertEqual((service / 'config.sh').read_text(), CONFIG)
            install(service, prepared, backup)
            self.assertEqual((backup / 'config.sh').read_text(), CONFIG)
            updated = (service / 'config.sh').read_text()
            self.assertIn('ASSISTANT_SMALL_MODEL="untouched"', updated)
            self.assertIn('ASSISTANT_ENGINE="llama"', updated)
            files = patch_service(*(service.joinpath(name).read_text() for name in ('serve.sh', 'stop.sh', 'config.sh')))
            self.assertEqual(files['config.sh'], updated)
            self.assertEqual(files['serve.sh'], (service / 'serve.sh').read_text())
            self.assertIn('sleepmlx[.]mac_gateway', files['stop.sh'])
            self.assertNotIn('--reasoning-budget', files['serve.sh'])

    def test_unknown_anchors_and_changed_original_refuse(self):
        with self.assertRaises(ValueError): patch_service(SERVE.replace('need=20', 'need=19'), STOP, CONFIG)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); service = root / 'service'; self.files(service)
            prepare(service, root / 'prepared')
            (service / 'config.sh').write_text(CONFIG + '# changed\n')
            with self.assertRaises(ValueError): install(service, root / 'prepared', root / 'backup')
            self.assertFalse((root / 'backup').exists())
            self.assertEqual((service / 'serve.sh').read_text(), SERVE)

    def test_llama_command_only_loads_verified_adapter(self):
        patched = patch_service(SERVE, STOP, CONFIG)['serve.sh']
        block = patched[patched.index('if [ $need_big = 1 ]; then'):patched.index('if [ $need_small = 1 ]; then')]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); helper = root / 'python'; server = root / 'llama-server'; model = root / 'base.gguf'; out = root / 'args'
            helper.write_text('#!/bin/bash\n[ "$HELPER_FAIL" = 1 ] && exit 1\nprintf "%s" "$ADAPTER"\n')
            helper.chmod(0o755); server.write_text('#!/bin/bash\n:'); server.chmod(0o755); model.touch()
            script = 'launch() { printf "%s\\n" "$@" > "$OUT"; }\n' + block
            base = dict(os.environ, need_big='1', ENGINE='llama', PY=str(helper), LLAMA_SERVER=str(server), BIG_MODEL=str(model), BIG_PORT='18080', OUT=str(out), HOME=str(root))
            for adapter in ('', '/tmp/accepted adapter.gguf'):
                proc = subprocess.run(['bash', '-c', script], env=dict(base, ADAPTER=adapter, HELPER_FAIL='0'))
                self.assertEqual(proc.returncode, 0)
                args = out.read_text().splitlines()
                self.assertEqual('--lora' in args, bool(adapter))
                if adapter: self.assertEqual(args[args.index('--lora') + 1], adapter)
                self.assertNotIn('--reasoning-budget', args)
            out.unlink()
            proc = subprocess.run(['bash', '-c', script], env=dict(base, ADAPTER='', HELPER_FAIL='1'))
            self.assertNotEqual(proc.returncode, 0)
            self.assertFalse(out.exists())


if __name__ == '__main__': unittest.main()
