"""Create a self-contained, offline HTML review of a local archive export."""
import argparse
import base64
import html
import json
from pathlib import Path


def render(data, preview_root=None):
    esc = lambda value: html.escape(str(value))
    assets = data['assets']
    rows, samples = [], []
    for asset in assets:
        names = [Path(p['path']).name for p in asset['paths'] if p['present']]
        meta = asset.get('metadata') or {}
        amount = (str(meta.get('pages', '')) + ' stran') if meta.get('kind') != 'video' else f"{meta.get('duration_seconds', 0):.1f} s"
        rows.append('<tr><td>' + '<br>'.join(map(esc, names)) + '</td><td>' + esc(meta.get('kind', 'chyba'))
                    + '</td><td>' + esc(amount) + '</td><td>' + esc(meta.get('classification', ''))
                    + '</td><td>' + esc(meta.get('ocr_review_pages', '')) + '</td><td>'
                    + esc(asset.get('inspection_error') or 'Otevřeno') + '</td></tr>')
        if asset['units']:
            parts = []
            for unit in asset['units']:
                title = f"Strana {unit['page']}" if 'page' in unit else f"Snímek {unit['frame']} · {unit['timestamp_seconds']:.2f} s"
                picture = ''
                if preview_root and unit.get('preview'):
                    p = Path(unit['preview']).resolve()
                    if p.is_relative_to(Path(preview_root).resolve()) and p.is_file() and p.suffix in {'.png', '.jpg'}:
                        mime = 'image/png' if p.suffix == '.png' else 'image/jpeg'
                        picture = f'<img loading="lazy" alt="{esc(title)}" src="data:{mime};base64,{base64.b64encode(p.read_bytes()).decode()}">'
                parts.append(f'<details><summary>{esc(title)} · OCR: {esc(unit.get("ocr_state", "neprovedeno"))}</summary>'
                             f'<div class="pair">{picture}<pre>{esc(unit.get("text") or "Textová vrstva není k dispozici. OCR ani AI popis zatím nebyly provedeny.")}</pre></div></details>')
            samples.append('<section><h3>' + esc(names[0] if names else asset['sha256']) + '</h3><p class="hash">SHA-256: '
                           + esc(asset['sha256']) + '</p>' + ''.join(parts) + '</section>')
    return ('''<!doctype html><html lang="cs"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>UAP — místní inventura archivu</title><style>
body{font:16px/1.6 system-ui;background:#f4f7fb;color:#17283c;margin:0;padding:36px;max-width:1500px;margin:auto}
h1{font-size:36px;margin-bottom:8px}h2{margin-top:36px}p{max-width:1000px}section, .intro{background:white;padding:24px;border-radius:12px;margin:20px 0}
table{border-collapse:collapse;width:100%;font-size:13px;background:white}td,th{padding:12px;text-align:left;border-bottom:1px solid #dde3eb;overflow-wrap:anywhere}td:first-child{max-width:560px}
input{padding:12px;width:min(600px,90%);font:inherit;border:1px solid #aab9cb;border-radius:6px;margin-bottom:16px}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin:16px 0}.pair img{max-width:100%;height:auto}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:14px/1.6 system-ui;margin:0}.hash{font-size:12px;overflow-wrap:anywhere;color:#52647a}summary{cursor:pointer;padding:12px;background:#eaf1f8;margin:6px 0}
@media(max-width:750px){body{padding:16px}.pair{grid-template-columns:1fr}.table{overflow:auto}}
</style><h1>UAP / UFO · Místní archiv</h1><div class="intro"><b>Inventura a ověření extrakce</b>
<p>Tento přehled neobsahuje nové překlady ani závěry AI. PDF jsou posuzována podle textové vrstvy; méně než 40 znaků na stránce označujeme k prověření OCR. Mohou to být i prázdné stránky. U videí jde o metadata a vybrané snímky, nikoli analýzu celého pohybu.</p>'''
    + f'<p>{len(assets)} unikátních zdrojů · {len(data.get("ignored_paths", []))} pomocných souborů vyřazeno · {esc(data["generated_at"])}</p></div>' \
    + '<h2>Katalog</h2><label for="filter">Filtrovat podle názvu nebo typu</label><br><input id="filter" placeholder="Například PDF, mixed nebo název spisu"><div class="table"><table><thead><tr><th>Soubor</th><th>Typ</th><th>Rozsah</th><th>Textová vrstva</th><th>Stran k OCR</th><th>Kontrola</th></tr></thead><tbody>' \
    + ''.join(rows) + '</tbody></table></div><h2>Ověřené vzorky</h2>' + ''.join(samples) \
    + '''<script>document.getElementById('filter').addEventListener('input',function(){const q=this.value.toLocaleLowerCase();document.querySelectorAll('tbody tr').forEach(r=>r.hidden=!r.textContent.toLocaleLowerCase().includes(q));});</script></html>''')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--preview-root', type=Path)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(json.loads(args.input.read_text(encoding='utf-8')), args.preview_root), encoding='utf-8')
