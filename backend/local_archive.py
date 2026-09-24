"""Offline, resumable archive inventory and extraction. No network or AI calls.

python backend/local_archive.py scan
python backend/local_archive.py process --sha256 HASH --previews
python backend/local_archive.py export --output report.json
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
from datetime import datetime, timezone

VERSION = '1'
SUPPORTED = {'.pdf', '.jpg', '.jpeg', '.png', '.mp4', '.mov', '.avi'}
VIDEO = {'.mp4', '.mov', '.avi'}


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def connect(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.executescript('''
        PRAGMA journal_mode=WAL;
        PRAGMA foreign_keys=ON;
        CREATE TABLE IF NOT EXISTS assets (
            sha256 TEXT PRIMARY KEY, extension TEXT NOT NULL, size INTEGER NOT NULL,
            metadata TEXT, inspection_error TEXT, inspected_at TEXT,
            extraction_state TEXT NOT NULL DEFAULT 'pending', extraction_error TEXT);
        CREATE TABLE IF NOT EXISTS paths (
            path TEXT PRIMARY KEY, root TEXT NOT NULL, sha256 TEXT NOT NULL REFERENCES assets(sha256),
            present INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS units (
            sha256 TEXT NOT NULL REFERENCES assets(sha256), version TEXT NOT NULL,
            unit_key TEXT NOT NULL, result TEXT NOT NULL, completed_at TEXT NOT NULL,
            PRIMARY KEY (sha256, version, unit_key));
        CREATE TABLE IF NOT EXISTS ignored_paths (
            path TEXT PRIMARY KEY, root TEXT NOT NULL, reason TEXT NOT NULL, size INTEGER NOT NULL);
    ''')
    return db


def video_info(path):
    import cv2
    cap = cv2.VideoCapture(str(path))
    try:
        if not cap.isOpened():
            raise ValueError('Video cannot be opened')
        fps = cap.get(cv2.CAP_PROP_FPS)
        count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        if not math.isfinite(fps) or fps <= 0 or not math.isfinite(count) or count <= 0:
            raise ValueError('Invalid video frame count or FPS')
        return {'kind': 'video', 'fps': fps, 'frames': int(count),
                'duration_seconds': count / fps,
                'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                'duration_method': 'OpenCV frame count / FPS; approximate for variable frame rate',
                'validation': 'metadata only; not a full video decode'}
    finally:
        cap.release()


def inspect_file(path):
    if path.suffix.lower() in VIDEO:
        return video_info(path)
    import pymupdf
    with pymupdf.open(path) as doc:
        if doc.needs_pass:
            raise ValueError('Encrypted document requires a password')
        if path.suffix.lower() != '.pdf':
            if not len(doc):
                raise ValueError('Empty image document')
            return {'kind': 'image', 'pages': len(doc),
                    'width': doc[0].rect.width, 'height': doc[0].rect.height,
                    'dimensions_unit': 'document points', 'format': path.suffix.lower()}
        pages = []
        for page in doc:
            text = page.get_text()
            chars = len(''.join(text.split()))
            pages.append({'page': page.number + 1, 'text_characters': chars,
                          'needs_ocr_review': chars < 40,
                          'embedded_images': len(page.get_images())})
        sparse = sum(p['needs_ocr_review'] for p in pages)
        return {'kind': 'pdf', 'pages': len(doc), 'page_details': pages,
                'classification': 'scan_or_sparse' if sparse == len(doc) else 'mixed' if sparse else 'text',
                'ocr_review_pages': sparse,
                'classification_note': 'Heuristic: fewer than 40 non-whitespace characters; blank pages also qualify.'}


def scan(db, root):
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError('Input directory does not exist: ' + str(root))
    # Only mark absent after a successful complete traversal. A interrupted scan
    # must not make untouched files disappear from the catalogue.
    seen, errors, ignored = set(), [], []
    files = sorted(p for p in root.rglob('*') if p.is_file() and not p.is_symlink())
    for i, path in enumerate(files, 1):
        reason = None
        if '__MACOSX' in path.relative_to(root).parts or path.name.startswith('._') or path.name == '.DS_Store':
            reason = 'macOS metadata; not a source document'
        elif path.suffix.lower() not in SUPPORTED:
            reason = 'unsupported extension'
        if reason:
            ignored.append((str(path.resolve()), str(root), reason, path.stat().st_size))
            continue
        resolved = str(path.resolve())
        seen.add(resolved)
        try:
            before = path.stat()
            sha = digest(path)
            after = path.stat()
            if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                raise ValueError('File changed while hashing; run scan again')
            with db:
                db.execute('INSERT OR IGNORE INTO assets(sha256,extension,size) VALUES(?,?,?)',
                           (sha, path.suffix.lower(), after.st_size))
                db.execute('INSERT OR REPLACE INTO paths VALUES(?,?,?,1)', (resolved, str(root), sha))
            previous = db.execute('SELECT metadata FROM assets WHERE sha256=?', (sha,)).fetchone()
            if previous['metadata'] is None:
                try:
                    metadata = inspect_file(path)
                    after_inspection = path.stat()
                    if (after.st_size, after.st_mtime_ns) != (after_inspection.st_size, after_inspection.st_mtime_ns):
                        raise ValueError('File changed during inspection; run scan again')
                    with db:
                        db.execute('UPDATE assets SET metadata=?,inspection_error=NULL,inspected_at=? WHERE sha256=?',
                                   (json.dumps(metadata, ensure_ascii=False), now(), sha))
                except Exception as exc:
                    with db:
                        db.execute('UPDATE assets SET inspection_error=?,inspected_at=? WHERE sha256=?', (str(exc), now(), sha))
                    errors.append({'path': resolved, 'error': str(exc)})
        except Exception as exc:
            errors.append({'path': resolved, 'error': str(exc)})
        if i % 25 == 0:
            print(f'Inspected {i}/{len(files)} files', flush=True)
    with db:
        db.execute('DELETE FROM ignored_paths WHERE root=?', (str(root),))
        db.executemany('INSERT OR REPLACE INTO ignored_paths VALUES(?,?,?,?)', ignored)
        for row in db.execute('SELECT path FROM paths WHERE root=?', (str(root),)).fetchall():
            db.execute('UPDATE paths SET present=? WHERE path=?', (int(row['path'] in seen), row['path']))
    return {'files_seen': len(files), 'supported_paths': len(seen), 'ignored_paths': len(ignored), 'errors': errors}


def process(db, sha, output, previews=False, interval=30.0, max_frames=12):
    if not math.isfinite(interval) or interval <= 0 or max_frames < 1:
        raise ValueError('Video interval and max_frames must be positive')
    row = db.execute('SELECT * FROM assets WHERE sha256=?', (sha,)).fetchone()
    source = db.execute('SELECT path FROM paths WHERE sha256=? AND present=1 ORDER BY path LIMIT 1', (sha,)).fetchone()
    if row is None or source is None:
        raise ValueError('Unknown asset or missing source; run scan first')
    path = Path(source['path'])
    if digest(path) != sha:
        raise ValueError('Source changed; run scan again')
    version = f'{VERSION}:preview={previews}:interval={interval}:max={max_frames}'
    folder = Path(output).resolve() / sha / hashlib.sha256(version.encode()).hexdigest()[:12]
    folder.mkdir(parents=True, exist_ok=True)
    with db:
        db.execute("UPDATE assets SET extraction_state='running',extraction_error=NULL WHERE sha256=?", (sha,))

    def done(key):
        old = db.execute('SELECT result FROM units WHERE sha256=? AND version=? AND unit_key=?', (sha, version, key)).fetchone()
        if not old:
            return False
        preview = json.loads(old['result']).get('preview')
        return not preview or Path(preview).is_file()

    def save(key, result):
        result.update({'translation_state': 'not_started', 'visual_analysis_state': 'not_started'})
        with db:
            db.execute('INSERT OR REPLACE INTO units VALUES(?,?,?,?,?)',
                       (sha, version, key, json.dumps(result, ensure_ascii=False), now()))

    def atomic_preview(target, write):
        temp = target.with_name(target.stem + '.tmp' + target.suffix)
        write(temp)
        temp.replace(target)

    try:
        if path.suffix.lower() in VIDEO:
            import cv2
            info = video_info(path)
            # Bounded sampling spans the entire duration when the requested
            # cadence exceeds the budget. This is not full-video analysis.
            count = min(max_frames, max(1, math.ceil(info['duration_seconds'] / interval)))
            indexes = sorted({round(i * (info['frames'] - 1) / max(1, count - 1)) for i in range(count)})
            cap = cv2.VideoCapture(str(path))
            try:
                for frame in indexes:
                    key = f'frame:{frame}'
                    if done(key):
                        continue
                    cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
                    ok, image = cap.read()
                    if not ok:
                        raise ValueError(f'Cannot decode frame {frame}')
                    target = folder / f'frame-{frame:09d}.jpg'
                    def write_image(temp):
                        ok, encoded = cv2.imencode('.jpg', image)
                        if not ok:
                            raise OSError('Cannot write video preview')
                        temp.write_bytes(encoded.tobytes())
                    atomic_preview(target, write_image)
                    save(key, {'frame': frame, 'timestamp_seconds': frame / info['fps'],
                               'timestamp_method': 'frame / FPS (approximate)', 'preview': str(target),
                               'coverage': 'sampled frames only', 'text': None})
            finally:
                cap.release()
        else:
            import pymupdf
            with pymupdf.open(path) as doc:
                if doc.needs_pass:
                    raise ValueError('Encrypted document requires a password')
                for page in doc:
                    key = f'page:{page.number + 1}'
                    if done(key):
                        continue
                    text = page.get_text() if path.suffix.lower() == '.pdf' else ''
                    result = {'page': page.number + 1, 'text': text,
                              'text_source': 'pdf_text_layer' if text.strip() else 'none',
                              'ocr_state': 'needs_review' if len(''.join(text.split())) < 40 else 'not_run',
                              'embedded_images': len(page.get_images()) if path.suffix.lower() == '.pdf' else None}
                    if previews:
                        target = folder / f'page-{page.number + 1:05d}.png'
                        atomic_preview(target, lambda temp: page.get_pixmap(dpi=100).save(str(temp)))
                        result['preview'] = str(target)
                    save(key, result)
        with db:
            db.execute("UPDATE assets SET extraction_state='extracted',extraction_error=NULL WHERE sha256=?", (sha,))
    except BaseException as exc:
        with db:
            db.execute("UPDATE assets SET extraction_state='error',extraction_error=? WHERE sha256=?", (str(exc) or type(exc).__name__, sha))
        raise


def export(db):
    assets = []
    for row in db.execute('SELECT * FROM assets a WHERE EXISTS (SELECT 1 FROM paths p WHERE p.sha256=a.sha256 AND p.present=1) ORDER BY sha256'):
        item = dict(row)
        item['metadata'] = json.loads(item['metadata']) if item['metadata'] else None
        item['paths'] = [dict(p) for p in db.execute('SELECT path,present FROM paths WHERE sha256=?', (row['sha256'],))]
        item['units'] = [{'version': u['version'], 'key': u['unit_key'], 'completed_at': u['completed_at'],
                          **json.loads(u['result'])} for u in db.execute('SELECT * FROM units WHERE sha256=? ORDER BY unit_key', (row['sha256'],))]
        item['units'].sort(key=lambda u: (u['version'], u.get('page', u.get('frame', 0))))
        assets.append(item)
    return {'schema_version': VERSION, 'generated_at': now(), 'assets': assets,
            'ignored_paths': [dict(r) for r in db.execute('SELECT * FROM ignored_paths ORDER BY path')],
            'notice': 'Local extraction only. No translation, OCR, or AI analysis has been performed.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    base = Path(__file__).resolve().parent
    parser.add_argument('--db', type=Path, default=base / 'local_state/archive.sqlite3')
    sub = parser.add_subparsers(dest='command', required=True)
    scan_parser = sub.add_parser('scan')
    scan_parser.add_argument('--input', type=Path, default=Path(os.getenv('INCOMING_DATA_DIR', str(base / 'incoming_data'))))
    proc = sub.add_parser('process')
    proc.add_argument('--sha256', required=True)
    proc.add_argument('--output', type=Path, default=base / 'local_state/previews')
    proc.add_argument('--previews', action='store_true')
    proc.add_argument('--interval', type=float, default=30.0)
    proc.add_argument('--max-frames', type=int, default=12)
    out = sub.add_parser('export')
    out.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    db = connect(args.db)
    try:
        if args.command == 'scan':
            result = scan(db, args.input)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            if result['errors']:
                raise SystemExit(1)
        elif args.command == 'process':
            process(db, args.sha256, args.output, args.previews, args.interval, args.max_frames)
            print('Extraction complete; translation and AI analysis have not been run.')
        else:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            temp = args.output.with_suffix(args.output.suffix + '.tmp')
            temp.write_text(json.dumps(export(db), ensure_ascii=False, indent=2), encoding='utf-8')
            temp.replace(args.output)
    finally:
        db.close()


if __name__ == '__main__':
    main()
