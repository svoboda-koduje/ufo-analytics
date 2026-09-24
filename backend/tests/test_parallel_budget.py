"""Concurrent reservations must share one hard budget across worker connections."""
import sys
from pathlib import Path
import uuid
import shutil
from contextlib import contextmanager

@contextmanager
def test_directory(root):
    path=root/uuid.uuid4().hex
    path.mkdir(parents=True)
    try:yield path
    finally:
        assert path.resolve().is_relative_to(root.resolve())
        shutil.rmtree(path)
import threading
import sqlite3
from concurrent.futures import ThreadPoolExecutor
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import local_archive as archive
import research

class ParallelBudgetTests(unittest.TestCase):
    def test_parallel_reservations_cannot_overspend(self):
        temp_root=Path(__file__).resolve().parents[1]/'local_state/tests'
        temp_root.mkdir(parents=True,exist_ok=True)
        with test_directory(temp_root) as temp:
            path=Path(temp)/'budget.sqlite3'
            db=archive.connect(path);research.prepare(db)
            with db:db.execute('UPDATE research_budget SET limit_usd=0.20 WHERE id=1')
            barrier=threading.Barrier(6)
            def reserve_one(i):
                conn=sqlite3.connect(path,timeout=20);conn.row_factory=sqlite3.Row
                try:
                    barrier.wait(timeout=20)
                    try:
                        research.reserve(conn,'different-request-'+str(i),0.06)
                        return True
                    except RuntimeError:
                        return False
                finally:conn.close()
            with ThreadPoolExecutor(max_workers=6) as pool:
                outcomes=list(pool.map(reserve_one,range(6)))
            self.assertEqual(sum(outcomes),3)
            self.assertAlmostEqual(research.budget(db)['accounted_usd'],0.18)
            self.assertEqual(db.execute('SELECT count(*) FROM research_calls').fetchone()[0],3)
            db.close()

if __name__=='__main__':unittest.main()
