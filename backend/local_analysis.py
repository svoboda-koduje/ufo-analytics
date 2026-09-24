"""Local OCR and technical image measurements, without cloud calls.

All results refer to a specific extracted page or sampled video frame. OCR
confidence is an engine score, not the probability that a statement is true.
"""
import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
from contextlib import contextmanager

import local_archive as archive

VERSION = 'ocr-metrics-2'


def prepare(db):
    db.executescript('''
    CREATE TABLE IF NOT EXISTS analyses (
        sha256 TEXT NOT NULL, extraction_version TEXT NOT NULL, unit_key TEXT NOT NULL,
        analyzer_version TEXT NOT NULL, result TEXT NOT NULL, completed_at TEXT NOT NULL,
        PRIMARY KEY(sha256,extraction_version,unit_key,analyzer_version));
    CREATE VIRTUAL TABLE IF NOT EXISTS page_search USING fts5(
        sha256 UNINDEXED, unit_key UNINDEXED, extraction_version UNINDEXED,
        text, tokenize='unicode61 remove_diacritics 2');
    ''')


def tesseract():
    candidates = [os.getenv('TESSERACT_CMD'), shutil.which('tesseract'),
                  r'C:\Program Files\Tesseract-OCR\tesseract.exe']
    for value in candidates:
        if value and Path(value).is_file():
            return str(Path(value).resolve())
    raise RuntimeError('Tesseract nebyl nalezen. Nastavte TESSERACT_CMD na jeho spustitelný soubor.')


def ocr_image(path, language='eng', psm=3):
    exe = tesseract()
    result = subprocess.run([exe, str(path), 'stdout', '-l', language, '--psm', str(psm), 'tsv'],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120,
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if result.returncode:
        raise RuntimeError('Tesseract: ' + result.stderr.decode('utf-8', errors='replace')[:1200])
    words, lines = [], {}
    # Recognized quotes are literal characters, not CSV quoting delimiters.
    for row in csv.DictReader(io.StringIO(result.stdout.decode('utf-8', errors='replace')), delimiter='\t', quoting=csv.QUOTE_NONE):
        if row.get('level') != '5' or not (row.get('text') or '').strip():
            continue
        confidence = float(row['conf'])
        word = {'text': row['text'], 'confidence': confidence,
                'box': [int(row[k]) for k in ('left', 'top', 'width', 'height')]}
        words.append(word)
        key = tuple(row[k] for k in ('page_num', 'block_num', 'par_num', 'line_num'))
        lines.setdefault(key, []).append(row['text'])
    scores = [w['confidence'] for w in words if w['confidence'] >= 0]
    return {'state': 'done' if words else 'empty', 'text': '\n'.join(' '.join(x) for x in lines.values()),
            'language': language, 'engine': 'Tesseract', 'words': words,
            'mean_confidence': round(sum(scores) / len(scores), 2) if scores else None,
            'low_confidence_words': sum(s < 60 for s in scores),
            'note': 'Strojový přepis vyžaduje kontrolu proti originálu; neobnovuje začerněný obsah.'}


def image_metrics(path):
    import cv2
    import numpy as np
    data = cv2.imdecode(np.frombuffer(Path(path).read_bytes(), dtype=np.uint8), cv2.IMREAD_COLOR)
    if data is None:
        raise ValueError('Obraz nelze dekódovat')
    gray = cv2.cvtColor(data, cv2.COLOR_BGR2GRAY)
    return {'width_pixels': int(data.shape[1]), 'height_pixels': int(data.shape[0]),
            'mean_brightness_0_255': round(float(gray.mean()), 2),
            'contrast_stddev': round(float(gray.std()), 2),
            'laplacian_variance': round(float(cv2.Laplacian(gray, cv2.CV_64F).var()), 2),
            'dark_pixels_percent': round(float((gray < 10).mean() * 100), 2),
            'bright_pixels_percent': round(float((gray > 245).mean() * 100), 2),
            'note': 'Měření pixelů náhledu; závisí na rozlišení. Nedokládá původ objektu ani fyzikální rychlost.'}


def index_unit(db, sha, version, key, text):
    with db:
        db.execute('DELETE FROM page_search WHERE sha256=? AND extraction_version=? AND unit_key=?', (sha, version, key))
        db.execute('INSERT INTO page_search(sha256,unit_key,extraction_version,text) VALUES(?,?,?,?)',
                   (sha, key, version, text))


def rebuild_search(db):
    prepare(db)
    with db:
        db.execute('DELETE FROM page_search')
        # Index every extraction version separately. UI search groups identical
        # source units so alternate preview settings do not create duplicate hits.
        for row in db.execute('SELECT * FROM units').fetchall():
            unit = json.loads(row['result'])
            extra = db.execute('SELECT result FROM analyses WHERE sha256=? AND extraction_version=? AND unit_key=? ORDER BY completed_at DESC LIMIT 1',
                               (row['sha256'], row['version'], row['unit_key'])).fetchone()
            ocr = json.loads(extra['result']).get('ocr', {}).get('text', '') if extra else ''
            text = unit.get('text') or ''
            if ocr:
                text += '\n' + ocr
            db.execute('INSERT INTO page_search VALUES(?,?,?,?)', (row['sha256'], row['unit_key'], row['version'], text))


@contextmanager
def processing_lock(output):
    lock_path = Path(output).resolve().parent / 'analysis.lock'
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open('a+b') as lock:
        lock.seek(0, 2)
        if lock.tell() == 0:
            lock.write(b'0')
            lock.flush()
        lock.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError('Jiná místní analýza už běží. Po jejím dokončení zkuste znovu.') from exc
        try:
            yield
        finally:
            lock.seek(0)
            if os.name == 'nt':
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def analyze(db, sha, output, language='eng', force_ocr=False, progress=None):
    with processing_lock(output):
        return _analyze(db, sha, output, language, force_ocr, progress)


def _analyze(db, sha, output, language='eng', force_ocr=False, progress=None):
    prepare(db)
    exe = tesseract()  # Fail before expensive extraction when unavailable.
    identity = subprocess.run([exe, '--version'], capture_output=True, timeout=10,
                              creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)).stdout.decode(errors='replace').splitlines()[0]
    model = Path(exe).parent / 'tessdata' / f'{language}.traineddata'
    model_hash = archive.digest(model) if model.is_file() else 'external-tessdata'
    analyzer = f'{VERSION}:{language}:force={force_ocr}:{identity}:{model_hash}'
    # Reuse a predictable extraction setting. Full native text is retained.
    archive.process(db, sha, output, previews=True, interval=15.0, max_frames=12)
    version = f'{archive.VERSION}:preview=True:interval=15.0:max=12'
    rows = db.execute('SELECT * FROM units WHERE sha256=? AND version=?', (sha, version)).fetchall()
    rows = sorted(rows, key=lambda r: int(r['unit_key'].split(':')[1]))
    source = db.execute('SELECT path FROM paths WHERE sha256=? AND present=1 LIMIT 1', (sha,)).fetchone()
    source_path = Path(source['path'])
    for i, row in enumerate(rows):
        unit = json.loads(row['result'])
        previous = db.execute('SELECT result FROM analyses WHERE sha256=? AND extraction_version=? AND unit_key=? AND analyzer_version=?',
                              (sha, version, row['unit_key'], analyzer)).fetchone()
        if previous and json.loads(previous['result']).get('ocr', {}).get('state') != 'error':
            if progress:
                progress(i + 1, len(rows), row['unit_key'])
            continue
        preview = Path(unit['preview'])
        result = {'metrics': image_metrics(preview), 'translation_state': 'not_started',
                  'semantic_analysis_state': 'not_started', 'source_unit': row['unit_key']}
        native_text = unit.get('text') or ''
        needs_ocr = force_ocr or len(''.join(native_text.split())) < 40
        if needs_ocr:
            temp = None
            try:
                ocr_path = preview
                if source_path.suffix.lower() == '.pdf':
                    import pymupdf
                    temp = preview.with_name(preview.stem + '.ocr.png')
                    with pymupdf.open(source_path) as doc:
                        page = doc[unit['page'] - 1]
                        # Bound raster allocation for unusually large pages.
                        scale = min(240 / 72, 5000 / max(page.rect.width, page.rect.height))
                        page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False).save(str(temp))
                    ocr_path = temp
                result['ocr'] = ocr_image(ocr_path, language, 11 if 'frame' in unit else 3)
                if temp:
                    result['ocr']['coordinate_space'] = 'OCR raster up to 240 DPI, max side 5000 px; not preview pixels'
            except Exception as exc:
                result['ocr'] = {'state': 'error', 'text': '', 'error': str(exc)}
            finally:
                if temp and temp.is_file():
                    temp.unlink()
        else:
            result['ocr'] = {'state': 'native_text_used', 'text': '', 'note': 'Textová vrstva zachována; OCR lze vynutit.'}
        with db:
            db.execute('INSERT OR REPLACE INTO analyses VALUES(?,?,?,?,?,?)',
                       (sha, version, row['unit_key'], analyzer, json.dumps(result, ensure_ascii=False), archive.now()))
            # New OCR invalidates Czech content derived from the earlier source.
            if db.execute("SELECT 1 FROM sqlite_master WHERE name='research_units'").fetchone():
                db.execute('DELETE FROM research_units WHERE sha256=? AND unit_key=?',(sha,row['unit_key']))
                db.execute('DELETE FROM research_search WHERE sha256=? AND unit_key=?',(sha,row['unit_key']))
                if db.execute("SELECT 1 FROM sqlite_master WHERE name='research_documents'").fetchone():
                    db.execute('DELETE FROM research_documents WHERE sha256=?',(sha,))
        index_unit(db, sha, version, row['unit_key'], native_text + '\n' + result['ocr'].get('text', ''))
        if progress:
            progress(i + 1, len(rows), row['unit_key'])
    return {'units': len(rows), 'analyzer': analyzer,
            'ocr_errors': sum(json.loads(r[0])['ocr']['state'] == 'error' for r in db.execute('SELECT result FROM analyses WHERE sha256=? AND extraction_version=? AND analyzer_version=?', (sha, version, analyzer)))}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', type=Path, default=Path(__file__).parent / 'local_state/archive.sqlite3')
    parser.add_argument('--sha256')
    parser.add_argument('--reindex', action='store_true')
    parser.add_argument('--force-ocr', action='store_true')
    args = parser.parse_args()
    db = archive.connect(args.db)
    try:
        if args.reindex:
            rebuild_search(db)
        elif args.sha256:
            print(json.dumps(analyze(db, args.sha256, args.db.parent / 'previews', force_ocr=args.force_ocr,
                                     progress=lambda i, n, k: print(f'{i}/{n} {k}', flush=True)), ensure_ascii=False))
        else:
            parser.error('Use --sha256 or --reindex')
    finally:
        db.close()
