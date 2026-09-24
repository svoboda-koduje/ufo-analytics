"""Read-only cost and completeness report for the representative batch; no API calls."""
from pathlib import Path
import sys,json,sqlite3,collections
BASE=Path(__file__).resolve().parent
OUT=BASE/'local_state'
def main():
 m=json.loads((BASE/'representative_batch_2026-09-24.json').read_text(encoding='utf-8'))
 d=sqlite3.connect('file:'+str(BASE/'local_state/archive.sqlite3')+'?mode=ro',uri=True);d.row_factory=sqlite3.Row
 def group(pages,ocr,chars):
  return 'scan_heavy' if ocr/pages>=0.5 else ('dense_text' if chars/pages>=1800 else 'mixed_standard')
 corpus=collections.Counter()
 for r in d.execute("select distinct a.sha256,a.metadata from assets a join paths p on p.sha256=a.sha256 where p.present=1 and a.extension='.pdf' and a.metadata is not null"):
  meta=json.loads(r['metadata']);pages=meta['pages'];chars=sum(p.get('text_characters',0) for p in meta.get('page_details',[]));corpus[group(pages,meta.get('ocr_review_pages',0),chars)]+=pages
 rows=[]
 for f in m['files']:
  units=list(d.execute('select unit_key,result from research_units where sha256=?',(f['sha'],)))
  doc=d.execute('select 1 from research_documents where sha256=?',(f['sha'],)).fetchone() is not None
  c=d.execute('select count(*) n,sum(coalesce(c.cost_usd,c.reserved_usd)) accounted,sum(c.cost_usd) actual,sum(c.input_tokens) input_tokens,sum(c.output_tokens) output_tokens from research_calls c join research_call_context x on x.call_id=c.id where x.sha256=?',(f['sha'],)).fetchone()
  states={r['state']:r['n'] for r in d.execute('select c.state,count(*) n from research_calls c join research_call_context x on x.call_id=c.id where x.sha256=? group by c.state',(f['sha'],))}
  rows.append({**f,'stratum':group(f['pages'],f['ocr'],f['chars']),'translated_pages':len(units),'partial_pages':sum(json.loads(r['result']).get('status')=='partial' for r in units),'has_dossier':doc,'complete_machine_output':len(units)==f['pages'] and doc,'calls':dict(c),'call_states':states})
 groups={}
 for key,n in corpus.items():
  complete=[r for r in rows if r['stratum']==key and r['complete_machine_output'] and set(r['call_states'])<={'done'}]
  pages=sum(r['pages'] for r in complete);cost=sum(r['calls']['actual'] or 0 for r in complete)
  groups[key]={'corpus_pages':n,'sample_complete_pages':pages,'sample_cost_usd':cost,'per_page_usd':cost/pages if pages else None,'projected_pdf_cost_usd':n*cost/pages if pages else None}
 report={'batch_id':m['batch_id'],'sample_design':m['method'],'model':'gpt-5.4-2026-03-05','planned_pages':m['pages'],'stored_pages':sum(r['translated_pages'] for r in rows),'complete_documents':sum(r['complete_machine_output'] for r in rows),'sample_actual_cost_usd':sum(r['calls']['actual'] or 0 for r in rows),'overall_accounted_usd':d.execute('select sum(coalesce(cost_usd,reserved_usd)) from research_calls').fetchone()[0],'states':dict(sum((collections.Counter(r['call_states']) for r in rows),collections.Counter())),'stratified_estimate':groups,'files':rows,'limitations':['Purposive sample; ranges are planning allowances, not statistical confidence intervals.','PDF estimate excludes video/audio, human expert review and hosting.','Machine output completeness does not imply every source passage is legible or translated without error.','Global budget includes prior catalogue work and pilot calls.','Costs use recorded API token usage at standard rates; cached-input discounts are not subtracted. Provider invoice is authoritative.']}
 (OUT/'reprezentativni-davka-237-overeni.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({k:v for k,v in report.items() if k not in {'files','limitations','sample_design','stratified_estimate'}},ensure_ascii=False))
if __name__=='__main__':main()
