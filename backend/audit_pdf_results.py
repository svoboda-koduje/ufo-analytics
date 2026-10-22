"""Validate saved PDF results without API calls or changes to the research database.

A coherent read transaction excludes pages saved after this audit starts.
An incomplete running document is reported as pending, not as a validation failure.
"""
import argparse
import collections
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3

BASE = Path(__file__).resolve().parent

def audit(db, manifest):
    errors, pending, warnings = [], [], []
    counts = collections.Counter()
    for file in manifest['files']:
        sha = file['sha']
        rows = list(db.execute('SELECT unit_key,result FROM research_units WHERE sha256=?', (sha,)))
        dossier = db.execute('SELECT result FROM research_documents WHERE sha256=?', (sha,)).fetchone()
        expected = {f'page:{n}' for n in range(1, file['pages'] + 1)}
        present = {row[0] for row in rows}
        counts['saved_pages'] += len(expected & present)
        def fail(problem, unit=None):
            errors.append({'file': file['name'], 'unit': unit, 'problem': problem})
        if present - expected:
            fail('Unexpected page identifiers')
        if dossier and present != expected:
            fail('Dossier exists but page coverage is incomplete')
        if not dossier:
            pending.append({'file': file['name'], 'saved_pages': len(expected & present), 'expected_pages': file['pages']})
        for unit, raw in rows:
            value = json.loads(raw)
            if value.get('status') == 'partial':
                counts['partial_readability_pages'] += 1
            parts = value.get('parts', [])
            if not parts:
                fail('No reading parts', unit)
            if value.get('source_unit') != unit:
                fail('Source unit does not match stored page', unit)
            for part in parts:
                status = part.get('translation_status')
                if status not in {'translated', 'partial', 'no_text'}:
                    fail('Unknown translation status', unit)
                if status != 'no_text' and not part.get('translation_cs', '').strip():
                    # OCR punctuation alone is not translatable text. Keep the
                    # original result and its partial flag; never invent prose.
                    source = db.execute('SELECT result FROM units WHERE sha256=? AND unit_key=? ORDER BY completed_at DESC LIMIT 1', (sha, unit)).fetchone()
                    text = json.loads(source[0]).get('text', '') if source else None
                    if (status == 'partial' and text is not None
                            and not any(char.isalnum() for char in text)
                            and part.get('summary_cs', '').strip()
                            and part.get('limitations_cs')):
                        warnings.append({'file':file['name'], 'unit':unit,
                                         'problem':'Image/unreadable page: no alphanumeric source text; partial reading retained'})
                    else:
                        fail('Empty translation for a text-bearing page', unit)
        if dossier:
            value = json.loads(dossier[0])
            if not value.get('overview_cs', '').strip():
                fail('Empty document overview')
            for finding in value.get('findings', []):
                sources = finding.get('source_units', [])
                if not sources or not set(sources) <= present:
                    fail('Finding has missing or invalid page references')
            if present == expected:
                counts['complete_dossiers'] += 1
    return {'checked_at': datetime.now(timezone.utc).isoformat(),
            'scope': 'Structural checks only; not a linguistic or factual expert review.',
            'pdf_files': len(manifest['files']), 'pdf_pages': manifest['pages'],
            **dict(counts), 'errors': errors, 'warnings': warnings, 'pending_documents': pending}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=BASE/'local_state/pdf-results-audit.json')
    args = parser.parse_args()
    manifest = json.loads((BASE/'full_pdf_batch_500.json').read_text(encoding='utf-8'))
    with sqlite3.connect('file:'+str(BASE/'local_state/archive.sqlite3')+'?mode=ro', uri=True) as db:
        db.execute('BEGIN')
        report = audit(db, manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix('.tmp')
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(args.output)
    print(json.dumps({key: value for key, value in report.items() if key != 'pending_documents'}, ensure_ascii=False))
    raise SystemExit(1 if report['errors'] else 0)
