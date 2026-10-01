import stat
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from scripts.cap256_launch.storage_snapshot import allocated_bytes,raw_allocated_bytes


class SnapshotTests(unittest.TestCase):
    def test_real_files_include_atomic_checkpoint_temporary(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder)/'checkpoint.pt.tmp').write_bytes(b'x'*4097)
            (Path(folder)/'record.json').write_bytes(b'x')
            self.assertEqual(allocated_bytes(folder,4096),12288)
            self.assertEqual(raw_allocated_bytes(folder,4096),4096)

    def test_vanished_bounded_receipt_reserves_full_size(self):
        vanished=Path('/root/launch-cap256/mixtures/batch/PROGRESS.json.tmp-17-25-1')
        with tempfile.TemporaryDirectory() as folder,patch.object(Path,'rglob',return_value=iter([vanished])),patch.object(Path,'stat',side_effect=[SimpleNamespace(st_mode=stat.S_IFDIR),FileNotFoundError()]):
            self.assertEqual(allocated_bytes(folder,4096),1048576)

    def test_vanished_checkpoint_reserves_atomic_peak(self):
        vanished=Path('/root/artifacts/run/final-resume.pt.tmp')
        with tempfile.TemporaryDirectory() as folder,patch.object(Path,'rglob',return_value=iter([vanished])),patch.object(Path,'stat',side_effect=[SimpleNamespace(st_mode=stat.S_IFDIR),FileNotFoundError()]):
            self.assertEqual(allocated_bytes(folder,4096),134217728)

    def test_unknown_vanished_entry_fails_closed(self):
        vanished=Path('/root/source.json')
        with tempfile.TemporaryDirectory() as folder,patch.object(Path,'rglob',return_value=iter([vanished])),patch.object(Path,'stat',side_effect=[SimpleNamespace(st_mode=stat.S_IFDIR),FileNotFoundError()]):
            with self.assertRaises(FileNotFoundError):allocated_bytes(folder,4096)

    def test_permission_error_still_fails_closed(self):
        denied=SimpleNamespace(stat=lambda:(_ for _ in ()).throw(PermissionError()))
        with tempfile.TemporaryDirectory() as folder,patch.object(Path,'rglob',return_value=iter([denied])):
            with self.assertRaises(PermissionError):allocated_bytes(folder,4096)

    def test_raw_counts_unique_failed_receipt_temps(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder)/'PROGRESS.json.tmp-1-2-3').write_bytes(b'x')
            self.assertEqual(raw_allocated_bytes(folder,4096),4096)


if __name__=='__main__':unittest.main()
