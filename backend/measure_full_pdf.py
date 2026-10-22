"""Read-only PDF coverage and shared budget. No API calls."""
from pathlib import Path
import json,sqlite3,collections
BASE=Path(__file__).resolve().parent
if __name__=='__main__':
    with sqlite3.connect('file:'+str(BASE/'local_state/archive.sqlite3')+'?mode=ro',uri=True) as db:
        manifest=json.loads((BASE/'full_pdf_batch_500.json').read_text(encoding='utf-8'))
        pages=complete=partial=0
        for f in manifest['files']:
            units=list(db.execute('select unit_key,result from research_units where sha256=?',(f['sha'],)))
            expected={f'page:{n}' for n in range(1,f['pages']+1)}
            present={r[0] for r in units}
            pages+=len(expected&present)
            partial+=sum(json.loads(r[1]).get('status')=='partial' for r in units)
            complete+=present==expected and db.execute('select 1 from research_documents where sha256=?',(f['sha'],)).fetchone() is not None
        cost,accounted=db.execute('select coalesce(sum(cost_usd),0),coalesce(sum(coalesce(cost_usd,reserved_usd)),0) from research_calls').fetchone()
        limit=db.execute('select limit_usd from research_budget where id=1').fetchone()[0]
        report={'pdf_files':len(manifest['files']),'pdf_pages':manifest['pages'],'stored_pages':pages,'complete_dossiers':complete,'partial_readability_pages':partial,'recorded_cost_usd':round(cost,6),'accounted_including_reservations_usd':round(accounted,6),'total_cap_usd':limit,'remaining_after_reservations_usd':round(limit-accounted,6),'call_states':dict(db.execute('select state,count(*) from research_calls group by state'))}
        print(json.dumps(report,ensure_ascii=False))
