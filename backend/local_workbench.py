"""Loopback-only research workbench. Run with python backend/local_workbench.py."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import secrets
import threading
from urllib.parse import parse_qs, urlparse
import webbrowser

import local_archive as archive
import local_analysis as analysis
import research
import source_catalog


class Workbench:
    def __init__(self, database):
        self.database = Path(database).resolve()
        self.previews = self.database.parent / 'previews'
        self.token = secrets.token_urlsafe(32)
        self.lock = threading.Lock()
        self.pool = ThreadPoolExecutor(max_workers=1)
        self.job = {'state': 'idle'}
        with closing(archive.connect(self.database)) as db:
            research.prepare(db)

    def start(self, sha, force=False, czech=False):
        with self.lock:
            if self.job['state'] == 'running':
                return False
            self.job = {'state': 'running', 'sha256': sha, 'message': 'Ověřuji zdroj a připravuji stránky a náhledy…'}
            self.pool.submit(self.run, sha, force, czech)
        return True

    def run(self, sha, force, czech=False):
        def progress(i, total, key):
            with self.lock:
                self.job.update({'completed': i, 'total': total, 'message': f'{i}/{total} · {key}'})
        try:
            with closing(archive.connect(self.database)) as db:
                result = research.run(db, sha, self.previews, progress=progress) if czech else analysis.analyze(db, sha, self.previews, force_ocr=force, progress=progress)
            with self.lock:
                self.job.update({'state': 'done' if not result.get('ocr_errors') else 'partial', 'result': result,
                                 'message': 'Český obsah uložen' if czech else ('Dokončeno' if not result['ocr_errors'] else 'Dokončeno s chybami OCR; lze zopakovat.')})
        except Exception as exc:
            with self.lock:
                self.job.update({'state': 'error', 'message': str(exc)})

    def catalog(self, query='', filters=None):
        query = query.strip()
        filters = filters or {}
        for key in ('year_from','year_to'):
            if filters.get(key) and not 1 <= int(filters[key]) <= 9999:
                raise ValueError('Neplatný rok')
        if filters.get('year_from') and filters.get('year_to') and int(filters['year_from']) > int(filters['year_to']):
            raise ValueError('Obrácený rozsah roků')
        for key in ('time_from','time_to'):
            if filters.get(key) and not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',filters[key]):
                raise ValueError('Neplatný čas')
        with closing(archive.connect(self.database)) as db:
            readings = research.summaries(db)
            hits = []
            if query.strip():
                # Quote tokens so a research query cannot become FTS syntax.
                expression = ' AND '.join('"' + w.replace('"', '""') + '"' for w in query.split()[:12])
                found = set()
                for x in db.execute("SELECT sha256,unit_key,snippet(research_search,2,'','', ' … ',24) AS excerpt FROM research_search WHERE research_search MATCH ?",(expression,)):
                    hits.append(dict(x))
                    found.add((x['sha256'],x['unit_key']))
                for x in db.execute('''SELECT sha256, unit_key, snippet(page_search,3,'','', ' … ',24) AS excerpt
                    FROM page_search WHERE page_search MATCH ?
                    AND EXISTS (SELECT 1 FROM paths WHERE paths.sha256=page_search.sha256 AND present=1)
                    ''', (expression,)):
                    key = (x['sha256'], x['unit_key'])
                    if key not in found:
                        hits.append(dict(x))
                        found.add(key)
            matched = {h['sha256'] for h in hits}
            assets = []
            source_records = source_catalog.load()
            for row in db.execute('''SELECT a.*,p.path FROM assets a JOIN paths p USING(sha256)
                                     WHERE p.present=1 GROUP BY a.sha256 ORDER BY p.path'''):
                name = Path(row['path']).name
                source = source_catalog.lookup(name, source_records)
                source_text = json.dumps(source, ensure_ascii=False) if source else ''
                if query and query.casefold() not in (name+' '+source_text).casefold() and row['sha256'] not in matched:
                    continue
                meta = json.loads(row['metadata']) if row['metadata'] else {}
                reading = readings.get(row['sha256'],{'ready':0,'partial':0,'events':[]})
                if filters.get('kind') and filters['kind'] != meta.get('kind'): continue
                if filters.get('ready') == 'yes' and not reading['ready']: continue
                if filters.get('ready') == 'no' and reading['ready']: continue
                event_filter = any(filters.get(k) for k in ('year_from','year_to','country','time_from','time_to'))
                matching = [e for e in reading['events'] if research.matches_event(e,filters)]
                if event_filter and not matching: continue
                count = db.execute('SELECT COUNT(DISTINCT unit_key) FROM analyses WHERE sha256=?', (row['sha256'],)).fetchone()[0]
                assets.append({'sha256': row['sha256'], 'name': name, 'kind': meta.get('kind', 'unknown'),
                               'pages': meta.get('pages'), 'seconds': meta.get('duration_seconds'),
                               'ocr_pages': meta.get('ocr_review_pages'), 'analyzed_units': count,
                               'error': row['inspection_error'], 'czech_units':reading['ready'],
                               'czech_partial_units':reading['partial'],'matching_events':matching if event_filter else []})
            visible = {a['sha256'] for a in assets}
            countries = sorted({e['country_cs'] for r in readings.values() for e in r['events'] if e.get('country_cs')})
            return {'assets': assets, 'hits': [h for h in hits if h['sha256'] in visible][:200], 'hit_limit': 200,
                    'countries':countries,'budget':research.budget(db),
                    'coverage':{'files_with_czech':len(readings),'files_with_events':sum(bool(r['events']) for r in readings.values())}}

    def detail(self, sha, page=1):
        with closing(archive.connect(self.database)) as db:
            row = db.execute('SELECT * FROM assets WHERE sha256=?', (sha,)).fetchone()
            if not row:
                raise KeyError('Soubor není v katalogu')
            path = db.execute('SELECT path FROM paths WHERE sha256=? AND present=1 LIMIT 1', (sha,)).fetchone()
            if not path:
                raise KeyError('Zdroj už není přítomen')
            # Prefer a version used by analysis, otherwise latest extraction.
            version = db.execute('SELECT extraction_version FROM analyses WHERE sha256=? ORDER BY completed_at DESC LIMIT 1', (sha,)).fetchone()
            if not version:
                version = db.execute('SELECT version FROM units WHERE sha256=? ORDER BY completed_at DESC LIMIT 1', (sha,)).fetchone()
            units, count = [], 0
            if version:
                count = db.execute('SELECT COUNT(*) FROM units WHERE sha256=? AND version=?', (sha, version[0])).fetchone()[0]
                rows = db.execute("SELECT * FROM units WHERE sha256=? AND version=? ORDER BY CAST(substr(unit_key,instr(unit_key,':')+1) AS INTEGER) LIMIT 20 OFFSET ?", (sha, version[0], (page - 1) * 20))
                for unit in rows:
                    result = json.loads(unit['result'])
                    enriched = db.execute('SELECT result FROM analyses WHERE sha256=? AND extraction_version=? AND unit_key=? ORDER BY completed_at DESC LIMIT 1', (sha, version[0], unit['unit_key'])).fetchone()
                    result.update({'key': unit['unit_key'], 'version': unit['version'],
                                   'analysis': json.loads(enriched[0]) if enriched else None,
                                   'has_preview': bool(result.get('preview') and Path(result['preview']).is_file())})
                    translated = db.execute('SELECT result FROM research_units WHERE sha256=? AND unit_key=?',(sha,unit['unit_key'])).fetchone()
                    result['research'] = json.loads(translated[0]) if translated else None
                    result.pop('preview', None)
                    units.append(result)
            dossier = db.execute('SELECT result FROM research_documents WHERE sha256=?',(sha,)).fetchone()
            return {'sha256': sha, 'name': Path(path[0]).name, 'metadata': json.loads(row['metadata'] or '{}'),
                    'source':source_catalog.lookup(Path(path[0]).name),
                    'dossier':json.loads(dossier[0]) if dossier else None,
                    'units': units, 'count': count, 'page': page, 'page_size': 20,
                    'research':research.summaries(db).get(sha,{'ready':0,'partial':0,'events':[]}), 'budget':research.budget(db)}

    def preview(self, sha, key, version):
        with closing(archive.connect(self.database)) as db:
            row = db.execute('SELECT result FROM units WHERE sha256=? AND version=? AND unit_key=?', (sha, version, key)).fetchone()
            if not row:
                raise KeyError('Náhled nenalezen')
            value = json.loads(row[0]).get('preview')
            if not value:
                raise KeyError('Nejprve spusťte analýzu pro vytvoření náhledu')
            path = Path(value).resolve()
            if not path.is_relative_to(self.previews.resolve()) or path.suffix not in {'.png', '.jpg'}:
                raise KeyError('Nepovolený náhled')
            return path.read_bytes(), 'image/png' if path.suffix == '.png' else 'image/jpeg'


def handler_for(workbench):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def allowed(self):
            return self.headers.get('Host') == f'127.0.0.1:{self.server.server_port}'

        def send(self, data, status=200, mime='application/json; charset=utf-8'):
            if not isinstance(data, bytes):
                data = json.dumps(data, ensure_ascii=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('X-Frame-Options', 'DENY')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if not self.allowed():
                return self.send({'error': 'Host odmítnut'}, 403)
            url = urlparse(self.path)
            args = parse_qs(url.query)
            try:
                if url.path == '/':
                    html = Path(__file__).with_name('local_workbench.html').read_text(encoding='utf-8')
                    return self.send(html.replace('__SESSION_TOKEN__', workbench.token).encode('utf-8'), mime='text/html; charset=utf-8')
                if url.path == '/api/assets':
                    filters = {k:args.get(k,[''])[0][:100] for k in ('year_from','year_to','country','time_from','time_to','kind','ready')}
                    return self.send(workbench.catalog(args.get('q', [''])[0][:200],filters))
                if url.path == '/api/job':
                    with workbench.lock:
                        return self.send(dict(workbench.job))
                if re.fullmatch(r'/api/asset/[0-9a-f]{64}', url.path):
                    return self.send(workbench.detail(url.path.rsplit('/', 1)[1], max(1, int(args.get('page', ['1'])[0]))))
                if url.path == '/api/preview':
                    data, mime = workbench.preview(args['sha'][0], args['key'][0], args['version'][0])
                    return self.send(data, mime=mime)
                return self.send({'error': 'Nenalezeno'}, 404)
            except (KeyError, FileNotFoundError):
                return self.send({'error': 'Nenalezeno'}, 404)
            except ValueError:
                return self.send({'error': 'Neplatný požadavek'}, 400)
            except Exception:
                return self.send({'error': 'Chyba místního katalogu'}, 500)

        def do_POST(self):
            origin = self.headers.get('Origin')
            expected = f'http://127.0.0.1:{self.server.server_port}'
            if not self.allowed() or (origin and origin != expected) or not secrets.compare_digest(self.headers.get('X-Local-Token', ''), workbench.token):
                return self.send({'error': 'Požadavek odmítnut'}, 403)
            if not re.fullmatch(r'/api/(?:analyze|research)/[0-9a-f]{64}', self.path):
                return self.send({'error': 'Nenalezeno'}, 404)
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 <= length <= 1024:
                    return self.send({'error': 'Příliš velký požadavek'}, 413)
                body = json.loads(self.rfile.read(length) or b'{}')
                if not isinstance(body, dict) or not isinstance(body.get('force', False), bool):
                    raise ValueError()
                sha = self.path.rsplit('/', 1)[1]
                workbench.detail(sha)
                started = workbench.start(sha, False, True) if self.path.startswith('/api/research/') else workbench.start(sha, body.get('force', False))
                if not started:
                    return self.send({'error': 'Jiná úloha už běží. Vyčkejte na dokončení.'}, 409)
                return self.send({'state': 'running'}, 202)
            except KeyError:
                return self.send({'error': 'Neznámý soubor'}, 404)
            except (ValueError, TypeError):
                return self.send({'error': 'Neplatný požadavek'}, 400)
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', type=Path, default=Path(__file__).parent / 'local_state/archive.sqlite3')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--open', action='store_true')
    args = parser.parse_args()
    bench = Workbench(args.db)
    server = ThreadingHTTPServer(('127.0.0.1', args.port), handler_for(bench))
    print(f'Místní badatelna: http://127.0.0.1:{server.server_port}', flush=True)
    if args.open:
        webbrowser.open(f'http://127.0.0.1:{server.server_port}')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        bench.pool.shutdown(wait=True)


if __name__ == '__main__':
    main()
