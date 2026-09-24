"""Resume bounded file-by-file research; never label video samples complete.

No API call is made without --run. The shared budget is managed by research.py.
On any API/budget error the whole batch stops for review, with no automatic retry.
"""
import argparse
from contextlib import closing
import json
from pathlib import Path
import sqlite3
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
import threading
import local_archive as archive
import research

BASE=Path(__file__).resolve().parent

def plan(db):
    result=[]
    for row in db.execute('SELECT DISTINCT a.* FROM assets a JOIN paths p ON p.sha256=a.sha256 WHERE p.present=1'):
        paths=[Path(r[0]) for r in db.execute('SELECT path FROM paths WHERE sha256=? AND present=1',(row['sha256'],))]
        paths=[p for p in paths if p.is_file() and not p.name.startswith('.') and '__MACOSX' not in p.parts]
        if not paths:continue
        meta=json.loads(row['metadata'] or '{}');kind=meta.get('kind','unknown')
        ready=db.execute('SELECT 1 FROM research_documents WHERE sha256=?',(row['sha256'],)).fetchone() is not None
        result.append({'sha256':row['sha256'],'filename':paths[0].name,'kind':kind,'units_expected':meta.get('pages',1),'state':'video_requires_temporal_and_audio_pipeline' if kind=='video' else ('cached_dossier' if ready else 'pending')})
    return sorted(result,key=lambda r:(r['kind']!='image',r['units_expected'],r['filename']))

def save(path,value):
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(path)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',action='store_true');p.add_argument('--max-files',type=int);p.add_argument('--manifest',type=Path);p.add_argument('--workers',type=int,default=3,choices=range(1,7));args=p.parse_args()
    dbpath=BASE/'local_state/archive.sqlite3'
    with closing(archive.connect(dbpath)) as db:
        research.prepare(db)
        items=plan(db)
        if args.manifest:
            manifest=json.loads(args.manifest.read_text(encoding='utf-8'))
            wanted={r['sha'] for r in manifest['files']}
            selected=[r for r in items if r['sha256'] in wanted]
            if len(selected)!=len(wanted):raise ValueError('Manifest obsahuje nedostupný soubor.')
            if sum(r['units_expected'] for r in selected)!=manifest['pages']:raise ValueError('Počet stran neodpovídá manifestu.')
            items=selected
        report={'started_at':archive.now(),'items':items,'budget':research.budget(db),'status':'planned'}
        output=dbpath.parent/('representative-batch.json' if args.manifest else 'full-research-batch.json');report['budget_before']=research.budget(db);report['model']=research.MODEL;save(output,report)
        if not args.run:
            print(json.dumps({'files':len(items),'pending':sum(r['state']=='pending' for r in items),'budget':report['budget']}));return
        completed=0
        stop=threading.Event()
        def worker(item):
            with closing(archive.connect(dbpath)) as workdb:
                def progress(i,n,k):
                    print(json.dumps({'file':item['filename'],'progress':i,'total':n,'unit':k},ensure_ascii=False),flush=True)
                    if stop.is_set():raise RuntimeError('Dávka zastavena; hotové jednotky zachovány.')
                return research.run_prepared(workdb,item['sha256'],progress=progress,api=research.client())
        def collect(futures):
            nonlocal completed
            for future in futures:
                item=inflight.pop(future)
                try:
                    future.result();item['state']='machine_results_saved';completed+=1
                except Exception as exc:
                    item['state']='stopped_for_review'
                    item['reason']=str(exc) if isinstance(exc,RuntimeError) else type(exc).__name__
                    stop.set()
                report['budget']=research.budget(db);save(output,report)
                print(json.dumps({'file':item['filename'],'state':item['state'],'budget':report['budget']},ensure_ascii=False),flush=True)
        inflight={}
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            submitted=0
            for item in items:
                if item['state']!='pending' or item['kind'] not in {'pdf','image'}:continue
                if len(inflight)>=args.workers:
                    done,_=wait(inflight,return_when=FIRST_COMPLETED);collect(done)
                if stop.is_set() or (args.max_files and submitted>=args.max_files):break
                item['state']='preparing';report['status']='running';save(output,report)
                try:
                    # Serial local preparation; API work only reads prepared sources.
                    research.analysis.analyze(db,item['sha256'],dbpath.parent/'previews')
                except Exception as exc:
                    item['state']='stopped_for_review';item['reason']=type(exc).__name__;stop.set();break
                if stop.is_set():item['state']='pending';break
                item['state']='running';inflight[pool.submit(worker,item)]=item;submitted+=1
                print(json.dumps({'file':item['filename'],'status':'started'},ensure_ascii=False),flush=True)
            if inflight:
                wait(inflight);collect(list(inflight))
        if stop.is_set():
            report['status']='stopped_for_review';report['finished_at']=archive.now();save(output,report)
            print(json.dumps({'status':report['status'],'budget':report['budget']},ensure_ascii=False),flush=True);return
        report['status']='batch_finished_with_remaining_scope';report['finished_at']=archive.now();save(output,report)
        print(json.dumps({'status':report['status'],'completed_this_run':completed,'budget':report['budget']}),flush=True)

if __name__=='__main__':
    with research.analysis.processing_lock(BASE/'local_state/batch/previews'):
        main()
