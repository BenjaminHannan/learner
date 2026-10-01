import stat
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from scripts.cap256_launch.storage_snapshot import allocated_bytes


class SnapshotTests(unittest.TestCase):
    def test_real_files_include_atomic_checkpoint_temporary(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder)/'checkpoint.pt.tmp').write_bytes(b'x'*4097)
            (Path(folder)/'record.json').write_bytes(b'x')
            self.assertEqual(allocated_bytes(folder,4096),12288)

    def test_vanished_entry_does_not_abort_snapshot(self):
        vanished=SimpleNamespace(stat=lambda:(_ for _ in ()).throw(FileNotFoundError()))
        live=SimpleNamespace(stat=lambda:SimpleNamespace(st_mode=stat.S_IFREG,st_size=17))
        with tempfile.TemporaryDirectory() as folder,patch.object(Path,'rglob',return_value=iter([vanished,live])):
            self.assertEqual(allocated_bytes(folder,4096),4096)

    def test_permission_error_still_fails_closed(self):
        denied=SimpleNamespace(stat=lambda:(_ for _ in ()).throw(PermissionError()))
        with tempfile.TemporaryDirectory() as folder,patch.object(Path,'rglob',return_value=iter([denied])):
            with self.assertRaises(PermissionError):allocated_bytes(folder,4096)


if __name__=='__main__':unittest.main()
