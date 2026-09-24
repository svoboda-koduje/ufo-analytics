import json
from pathlib import Path
import sys
import shutil
import uuid
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import local_archive as archive
import archive_report
import pymupdf


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.test_root = Path(__file__).resolve().parents[1] / 'local_state/tests'
        self.root = self.test_root / uuid.uuid4().hex
        self.source = self.root / 'input'
        self.source.mkdir(parents=True)
        self.db = archive.connect(self.root / 'state.sqlite3')

    def tearDown(self):
        self.db.close()
        assert self.root.resolve().is_relative_to(self.test_root.resolve())
        shutil.rmtree(self.root)

    def pdf(self, name='example.pdf'):
        path = self.source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with pymupdf.open() as doc:
            doc.new_page().insert_text((50, 50), 'This is a complete source document with enough text for the test.')
            doc.new_page()
            doc.save(path)
        return path

    def test_recursive_deduplication_and_missing_paths(self):
        path = self.pdf()
        duplicate = self.source / 'nested' / 'copy.pdf'
        duplicate.parent.mkdir()
        duplicate.write_bytes(path.read_bytes())
        archive.scan(self.db, self.source)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM assets').fetchone()[0], 1)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM paths WHERE present=1').fetchone()[0], 2)
        duplicate.unlink()
        archive.scan(self.db, self.source)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM paths WHERE present=1').fetchone()[0], 1)

    def test_full_text_and_resume_after_interruption(self):
        path = self.pdf()
        archive.scan(self.db, self.source)
        sha = archive.digest(path)
        real = pymupdf.Page.get_text
        def fail_second(page, *args, **kwargs):
            if page.number == 1:
                raise RuntimeError('simulated interruption')
            return real(page, *args, **kwargs)
        with patch.object(pymupdf.Page, 'get_text', fail_second):
            with self.assertRaises(RuntimeError):
                archive.process(self.db, sha, self.root / 'previews')
        first = self.db.execute('SELECT completed_at FROM units').fetchone()[0]
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM units').fetchone()[0], 1)
        archive.process(self.db, sha, self.root / 'previews')
        rows = self.db.execute('SELECT * FROM units ORDER BY unit_key').fetchall()
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['completed_at'], first)
        self.assertIn('complete source document', json.loads(rows[0]['result'])['text'])
        self.assertEqual(json.loads(rows[1]['result'])['ocr_state'], 'needs_review')

    def test_preview_repair_and_changed_source_rejection(self):
        path = self.pdf()
        archive.scan(self.db, self.source)
        sha = archive.digest(path)
        archive.process(self.db, sha, self.root / 'previews', previews=True)
        preview = Path(json.loads(self.db.execute('SELECT result FROM units').fetchone()[0])['preview'])
        preview.unlink()
        archive.process(self.db, sha, self.root / 'previews', previews=True)
        self.assertTrue(preview.exists())
        path.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'Source changed'):
            archive.process(self.db, sha, self.root / 'previews')

    def test_corrupt_file_is_recorded_without_stopping_scan(self):
        (self.source / 'broken.pdf').write_bytes(b'not a pdf')
        self.pdf()
        result = archive.scan(self.db, self.source)
        self.assertEqual(len(result['errors']), 1)
        self.assertEqual(len(archive.export(self.db)['assets']), 2)

    def test_macos_sidecars_are_not_documents(self):
        self.pdf()
        (self.source / '._example.pdf').write_bytes(b'AppleDouble metadata')
        result = archive.scan(self.db, self.source)
        self.assertEqual(result['ignored_paths'], 1)
        self.assertEqual(result['errors'], [])
        self.assertEqual(len(archive.export(self.db)['assets']), 1)

    def test_long_document_is_not_truncated(self):
        path = self.source / 'long.pdf'
        with pymupdf.open() as doc:
            for i in range(5):
                page = doc.new_page()
                page.insert_textbox(page.rect + (30, 30, -30, -30), ('Full text must be preserved. ' * 150) + f' END PAGE {i}', fontsize=8)
            doc.save(path)
        archive.scan(self.db, self.source)
        archive.process(self.db, archive.digest(path), self.root / 'previews')
        units = archive.export(self.db)['assets'][0]['units']
        self.assertEqual(len(units), 5)
        self.assertGreater(sum(len(u['text']) for u in units), 15000)
        self.assertIn('END PAGE 4', units[-1]['text'])

    def test_video_sampling_timestamps_and_resume(self):
        import cv2
        import numpy as np
        path = self.source / 'test.avi'
        writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*'MJPG'), 10, (64, 48))
        self.assertTrue(writer.isOpened())
        for i in range(30):
            writer.write(np.full((48, 64, 3), i * 5, dtype=np.uint8))
        writer.release()
        archive.scan(self.db, self.source)
        sha = archive.digest(path)
        archive.process(self.db, sha, self.root / 'frames', interval=0.1, max_frames=3)
        before = [dict(r) for r in self.db.execute('SELECT * FROM units ORDER BY unit_key')]
        self.assertEqual(len(before), 3)
        times = sorted(json.loads(r['result'])['timestamp_seconds'] for r in before)
        self.assertEqual(times, [0, 1.4, 2.9])
        exported = archive.export(self.db)['assets'][0]['units']
        self.assertEqual([u['timestamp_seconds'] for u in exported], times)
        archive.process(self.db, sha, self.root / 'frames', interval=0.1, max_frames=3)
        self.assertEqual(before, [dict(r) for r in self.db.execute('SELECT * FROM units ORDER BY unit_key')])
        with self.assertRaises(ValueError):
            archive.process(self.db, sha, self.root / 'frames', interval=0)

    def test_html_report_escapes_untrusted_document_text(self):
        path = self.pdf()
        archive.scan(self.db, self.source)
        archive.process(self.db, archive.digest(path), self.root / 'previews')
        data = archive.export(self.db)
        data['assets'][0]['units'][0]['text'] = '<script>alert(1)</script>'
        report = archive_report.render(data)
        self.assertNotIn('<script>alert(1)</script>', report)
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;', report)


if __name__ == '__main__':
    unittest.main()
