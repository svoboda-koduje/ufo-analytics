import json
from pathlib import Path
import shutil
import sys
import threading
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request
import uuid
from types import SimpleNamespace
from http.server import ThreadingHTTPServer

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pymupdf
import local_archive as archive
import local_analysis as analysis
from local_workbench import Workbench, handler_for


class AnalysisTests(unittest.TestCase):
    def test_processing_lock_rejects_overlap_and_releases(self):
        output = self.root / 'previews'
        with analysis.processing_lock(output):
            with self.assertRaisesRegex(RuntimeError, 'Jiná místní analýza'):
                with analysis.processing_lock(output):
                    self.fail('Overlapping processing must be rejected')
        with analysis.processing_lock(output):
            pass

    def setUp(self):
        self.parent = Path(__file__).resolve().parents[1] / 'local_state/tests'
        self.root = self.parent / uuid.uuid4().hex
        self.root.mkdir(parents=True)
        self.source = self.root / 'input'
        self.source.mkdir()
        self.path = self.source / 'document.pdf'
        with pymupdf.open() as doc:
            doc.new_page().insert_text((50, 50), 'Original evidence: aircraft appeared above the ocean at night.')
            doc.new_page()
            doc.save(self.path)
        self.database = self.root / 'archive.sqlite3'
        self.db = archive.connect(self.database)
        archive.scan(self.db, self.source)
        self.sha = archive.digest(self.path)

    def tearDown(self):
        self.db.close()
        assert self.root.resolve().is_relative_to(self.parent.resolve())
        shutil.rmtree(self.root)

    def test_real_ocr_and_measurements(self):
        try:
            analysis.tesseract()
        except RuntimeError:
            self.skipTest('Tesseract is not installed')
        image = self.root / 'ocr.png'
        with pymupdf.open() as doc:
            page = doc.new_page(width=600, height=180)
            page.insert_text((30, 65), 'AIRCRAFT REPORT 1952', fontsize=26)
            page.get_pixmap(dpi=200).save(image)
        result = analysis.ocr_image(image)
        self.assertIn('AIRCRAFT REPORT 1952', result['text'])
        self.assertGreater(result['mean_confidence'], 60)
        metrics = analysis.image_metrics(image)
        self.assertGreater(metrics['width_pixels'], 1000)
        self.assertGreater(metrics['contrast_stddev'], 0)

    def test_ocr_literal_quotes_do_not_swallow_tsv_rows(self):
        tsv = 'level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n'
        tsv += '5\t1\t1\t1\t1\t1\t0\t0\t20\t20\t95\t"Oh,\n'
        tsv += '5\t1\t1\t1\t1\t2\t25\t0\t20\t20\t96\taircraft\n'
        with patch.object(analysis, 'tesseract', return_value='tesseract'), patch.object(analysis.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout=tsv.encode(), stderr=b'')):
            result = analysis.ocr_image(self.root / 'unused.png')
        self.assertEqual(result['text'], '"Oh, aircraft')
        self.assertEqual(len(result['words']), 2)

    def test_native_text_preserved_and_ocr_resumes(self):
        try:
            analysis.tesseract()
        except RuntimeError:
            self.skipTest('Tesseract is not installed')
        fake = {'state': 'done', 'text': 'Recovered text from scan', 'mean_confidence': 90}
        with patch.object(analysis, 'ocr_image', return_value=fake) as ocr:
            result = analysis.analyze(self.db, self.sha, self.root / 'previews')
            self.assertEqual(result['ocr_errors'], 0)
            self.assertEqual(ocr.call_count, 1)
            before = [tuple(x) for x in self.db.execute('SELECT * FROM analyses ORDER BY unit_key')]
            analysis.analyze(self.db, self.sha, self.root / 'previews')
            self.assertEqual(ocr.call_count, 1)
            self.assertEqual(before, [tuple(x) for x in self.db.execute('SELECT * FROM analyses ORDER BY unit_key')])
        bench = Workbench(self.database)
        try:
            self.assertEqual(len(bench.catalog('Recovered')['hits']), 1)
            self.assertEqual(len(bench.catalog('aircraft')['hits']), 1)
            detail = bench.detail(self.sha)
            self.assertIn('Original evidence', detail['units'][0]['text'])
            self.assertEqual(detail['units'][1]['analysis']['ocr']['text'], fake['text'])
        finally:
            bench.pool.shutdown()

    def test_failed_ocr_retries_without_repeating_success(self):
        try:
            analysis.tesseract()
        except RuntimeError:
            self.skipTest('Tesseract is not installed')
        with patch.object(analysis, 'ocr_image', side_effect=RuntimeError('OCR failed')):
            self.assertEqual(analysis.analyze(self.db, self.sha, self.root / 'previews')['ocr_errors'], 1)
        with patch.object(analysis, 'ocr_image', return_value={'state': 'done', 'text': 'repaired'}) as ocr:
            self.assertEqual(analysis.analyze(self.db, self.sha, self.root / 'previews')['ocr_errors'], 0)
            self.assertEqual(ocr.call_count, 1)

    def test_loopback_api_rejects_unauthorized_mutation_and_host(self):
        bench = Workbench(self.database)
        server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(bench))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f'http://127.0.0.1:{server.server_port}'
        try:
            with urllib.request.urlopen(base + '/api/assets') as response:
                self.assertEqual(len(json.load(response)['assets']), 1)
            with self.assertRaises(urllib.error.HTTPError) as caught:
                urllib.request.urlopen(urllib.request.Request(base + '/api/analyze/' + self.sha, data=b'{}', method='POST'))
            self.assertEqual(caught.exception.code, 403)
            caught.exception.close()
            with self.assertRaises(urllib.error.HTTPError) as caught:
                urllib.request.urlopen(urllib.request.Request(base + '/api/assets', headers={'Host': 'attacker.example'}))
            self.assertEqual(caught.exception.code, 403)
            caught.exception.close()
            with self.assertRaises(urllib.error.HTTPError) as caught:
                urllib.request.urlopen(urllib.request.Request(base + '/api/analyze/' + self.sha, data=b'{}', method='POST',
                    headers={'X-Local-Token': bench.token, 'Origin': 'https://attacker.example'}))
            self.assertEqual(caught.exception.code, 403)
            caught.exception.close()
            with patch.object(bench, 'start', return_value=True) as start:
                with urllib.request.urlopen(urllib.request.Request(base + '/api/analyze/' + self.sha, data=b'{}', method='POST',
                        headers={'X-Local-Token': bench.token, 'Origin': base})) as response:
                    self.assertEqual(response.status, 202)
                start.assert_called_once_with(self.sha, False)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
            bench.pool.shutdown()


if __name__ == '__main__':
    unittest.main()
