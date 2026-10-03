import errno
import json
import random
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts.cap256_launch import receipt_io


def windows_error(code):
    error=PermissionError('injected replacement error');error.winerror=code;return error


class ReceiptTests(unittest.TestCase):
    def test_transient_share_error_retries_without_rng_change(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'BATCH.json';receipt_io.write_json(path,{'n':0})
            replace=receipt_io.os.replace;calls=[]
            def retry(source,target):
                calls.append(source)
                if len(calls)<3:raise windows_error(5)
                replace(source,target)
            before=random.getstate()
            with patch.object(receipt_io.os,'replace',side_effect=retry):result=receipt_io.write_json(path,{'n':1})
            self.assertEqual(receipt_io.read_json(path),{'n':1})
            self.assertEqual(result['replace_retries'],2)
            self.assertEqual(random.getstate(),before)

    def test_persistent_access_denial_preserves_old_receipt_and_unique_failures(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'BATCH.json';receipt_io.write_json(path,{'n':0})
            with patch.object(receipt_io.os,'replace',side_effect=windows_error(5)):
                for n in (1,2):
                    with self.assertRaises(PermissionError):receipt_io.write_json(path,{'n':n},timeout=0)
            self.assertEqual(receipt_io.read_json(path),{'n':0})
            files=list(Path(folder).glob('BATCH.json.tmp-*'))
            self.assertEqual(len(files),2)
            self.assertEqual({json.loads(p.read_bytes())['n'] for p in files},{1,2})

    def test_genuine_disk_error_not_retried(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(receipt_io.os,'replace',side_effect=OSError(errno.ENOSPC,'full')) as replace:
                with self.assertRaises(OSError):receipt_io.write_json(Path(folder)/'BATCH.json',{'n':1})
            self.assertEqual(replace.call_count,1)

    def test_nonwindows_permission_error_not_retried(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(receipt_io.os,'replace',side_effect=PermissionError('denied')) as replace:
                with self.assertRaises(PermissionError):receipt_io.write_json(Path(folder)/'BATCH.json',{'n':1})
            self.assertEqual(replace.call_count,1)

    def test_terminal_fallback_is_immutable_and_preserves_blocked_target(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'BATCH.json';receipt_io.write_json(path,{'status':'running'})
            with patch.object(receipt_io.os,'replace',side_effect=windows_error(5)):
                # Default timeout is bound at definition; set replacement deadline
                # via clock injection to make this permanent-denial test immediate.
                with patch.object(receipt_io.time,'monotonic',side_effect=[0,2]):
                    receipt_io.write_terminal_failure(path,{'status':'failed'})
            self.assertEqual(receipt_io.read_json(path),{'status':'running'})
            fallback=list(Path(folder).glob('FATAL-*.json'))
            self.assertEqual(len(fallback),1)
            self.assertEqual(receipt_io.read_json(fallback[0])['status'],'failed')

    def test_receipt_size_is_bounded_before_any_write(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):receipt_io.write_json(Path(folder)/'BATCH.json',{'x':'x'*receipt_io.MAX_RECEIPT_BYTES})
            self.assertEqual(list(Path(folder).iterdir()),[])

    def test_exclusive_receipt_cannot_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'FIRST.json';receipt_io.write_json(path,{'n':1},exclusive=True)
            with self.assertRaises(FileExistsError):receipt_io.write_json(path,{'n':2},exclusive=True)


if __name__=='__main__':unittest.main()
