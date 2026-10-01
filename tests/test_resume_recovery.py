import hashlib,json,random,tempfile,unittest
from pathlib import Path
from scripts.cap256_launch.resume_io import restore_prefix
from scripts.cap256_launch.checkpoint_io import save_reserved
from scripts.sol_cloud_capability256_v1 import save_new_atomic_file


class RecoveryTests(unittest.TestCase):
    def prefix(self,folder):
        source=Path(folder)/'source.jsonl';lines=[]
        frame={'cohort':'original','labels':[[1,2]],'label_mask':[[True,True]],'frame_sha256':'fixture'}
        for n in range(1,5121):lines.append((json.dumps({'additional_update':n,'update':10240+n,'id':'a','visit_for_row':40+n,'config_sha256':'old','labels':frame['labels'],'label_mask':frame['label_mask'],'input_frame_sha256':'fixture'})+'\n').encode())
        data=b''.join(lines);source.write_bytes(data)
        return source,data,frame

    def test_exact_prefix_preserved_no_rng_or_source_mutation(self):
        with tempfile.TemporaryDirectory() as folder:
            source,data,frame=self.prefix(folder);target=Path(folder)/'new.jsonl';calls=[];before=random.getstate()
            visits=restore_prefix(source,target,5120,['a']*5120,{'a':frame},hashlib.sha256(data).hexdigest(),'old',calls.append)
            self.assertEqual(target.read_bytes(),data);self.assertEqual(source.read_bytes(),data)
            self.assertEqual(visits['a'],5160);self.assertEqual(len(calls),1);self.assertEqual(random.getstate(),before)

    def test_stale_hash_or_provenance_rejected_before_copy(self):
        with tempfile.TemporaryDirectory() as folder:
            source,data,frame=self.prefix(folder)
            for digest,config in [('0'*64,'old'),(hashlib.sha256(data).hexdigest(),'wrong')]:
                target=Path(folder)/'new.jsonl'
                with self.assertRaises(ValueError):restore_prefix(source,target,5120,['a']*5120,{'a':frame},digest,config,lambda n:None)
                self.assertFalse(target.exists())

    def test_atomic_peak_reserved_once_not_per_chunk(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'cp.pt';calls=[];before=random.getstate()
            def serialize(sink):
                for _ in range(100):sink.write(b'x'*100)
            save_reserved(path,20000,serialize,save_new_atomic_file,lambda n=0:calls.append(n),lambda:10**9,100000,4096)
            self.assertEqual(len(calls),2);self.assertEqual(path.stat().st_size,10000)
            self.assertGreaterEqual(calls[0],20000);self.assertEqual(calls[1],0)
            self.assertEqual(random.getstate(),before)

    def test_failed_capacity_has_no_new_checkpoint(self):
        with tempfile.TemporaryDirectory() as folder:
            def guard(n):raise RuntimeError('cap')
            with self.assertRaises(RuntimeError):save_reserved(Path(folder)/'cp.pt',20,lambda s:s.write(b'x'),save_new_atomic_file,guard,lambda:10**9,100,4096)
            self.assertEqual(list(Path(folder).iterdir()),[])

    def test_extent_failure_preserves_temporary(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'cp.pt'
            with self.assertRaises(RuntimeError):save_reserved(path,3,lambda s:s.write(b'1234'),save_new_atomic_file,lambda n:None,lambda:10**9,100,4096)
            self.assertFalse(path.exists());self.assertTrue(path.with_suffix('.pt.tmp').exists())


if __name__=='__main__':unittest.main()
