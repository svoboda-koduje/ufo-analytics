"""Export only public metadata and prepared readings, never originals or credentials."""
import argparse
from collections import Counter
from contextlib import closing
import json
from pathlib import Path
import re
import local_archive as archive
import research
import source_catalog as sources

def years(raw):
    values=sorted(set(int(x) for x in re.findall(r'\b(?:18|19|20)\d{2}\b',raw)))
    if values:return values
    m=re.fullmatch(r'\s*\d{1,2}/\d{1,2}/(\d{2})\s*',raw)
    if m:
        n=int(m[1]);return [2000+n if n<=26 else 1900+n]
    return []

def export(video_path=None):
    records=sources.load()
    videos=json.loads(Path(video_path).read_text(encoding='utf-8')) if video_path else {}
    if not videos and (sources.BASE/'source_video_metadata.json').exists():videos=json.loads((sources.BASE/'source_video_metadata.json').read_text(encoding='utf-8'))
    if video_path:(sources.BASE/'source_video_metadata.json').write_text(json.dumps(videos,ensure_ascii=False,indent=2),encoding='utf-8')
    files=[p for p in (sources.BASE/'incoming_data').rglob('*') if p.is_file() and not p.name.startswith('.') and '__MACOSX' not in p.parts]
    for r in records:
        r['document_type']=r['document_type'].strip()
        if r.get('translation'):
            country=r['translation'].get('country_cs')
            r['translation']['country_cs']={'USA':'Spojené státy americké','Spojené státy':'Spojené státy americké','Papua Nová Guinea':'Papua-Nová Guinea'}.get(country,country)
        r['local_filenames']=[]
        v=videos.get(r['video_id'],{})
        r['video_page_url']=sources.safe_url(v.get('page_url','')) if v.get('title') else ''
        r['catalog_years']=years(r['incident_date'])
    unmatched=[]
    for p in files:
        record=sources.lookup(p.name,records)
        if not record and p.suffix.lower()=='.mp4':
            code=re.search(r'DOD_\d+',p.name)
            candidates=[r for r in records if code and code[0] in videos.get(r['video_id'],{}).get('codes',[]) and r['document_type'] in {'VID','AUD'}]
            # Multiple official entries may intentionally point to the same video.
            if candidates:
                for r in candidates:r['local_filenames'].append(p.name)
                continue
        if record: record['local_filenames'].append(p.name)
        else: unmatched.append(p.name)
    public=sources.BASE.parent/'frontend/public/research';public.mkdir(parents=True,exist_ok=True)
    with closing(archive.connect(sources.BASE/'local_state/archive.sqlite3')) as db:
        summaries=research.summaries(db)
        byname={Path(x['path']).name.casefold():x['sha256'] for x in db.execute('SELECT path,sha256 FROM paths WHERE present=1')}
        for r in records:
            hashes=sorted({byname[n.casefold()] for n in r['local_filenames'] if n.casefold() in byname})
            r['local_sha256']=hashes
            r['analyses']=[];r['events']=[]
            for sha in hashes:
                units=[{'unit_key':x['unit_key'],**json.loads(x['result'])} for x in db.execute('SELECT unit_key,result FROM research_units WHERE sha256=? ORDER BY CAST(substr(unit_key,instr(unit_key,\':\')+1) AS INTEGER)',(sha,))]
                if not units:continue
                dossier=db.execute('SELECT result FROM research_documents WHERE sha256=?',(sha,)).fetchone()
                payload={'sha256':sha,'units':units,'dossier':json.loads(dossier[0]) if dossier else None,'source_url':r['source_url']}
                (public/(sha+'.json')).write_text(json.dumps(payload,ensure_ascii=False),encoding='utf-8')
                r['analyses'].append({'sha256':sha,'units':len(units),'url':'/research/'+sha+'.json'})
                r['events'].extend(summaries.get(sha,{}).get('events',[]))
        budget=research.budget(db)
    sources.save(records)
    target=sources.BASE.parent/'frontend/app/source_catalog.json'
    target.write_text(json.dumps(records,ensure_ascii=False),encoding='utf-8')
    # Backward-compatible fields; source_id is stable, index is display-only.
    mapping=[{'index':i+1,**r,'war_gov_search_url':r['source_url']} for i,r in enumerate(records)]
    for p in [sources.BASE/'file_to_asset_mapping.json',sources.BASE.parent/'frontend/app/file_to_asset_mapping.json']:
        p.write_text(json.dumps(mapping,ensure_ascii=False,indent=2),encoding='utf-8')
    report={'records':len(records),'release_counts':dict(Counter(r['release'] for r in records)),
      'translated_descriptions':sum(bool(r.get('translation')) for r in records),'local_files':len(files),
      'matched_records':sum(bool(r['local_filenames']) for r in records),'unmatched_files':unmatched,
      'release06_unmatched':[r['asset_file_name'] for r in records if r['release']=='06' and not r['local_filenames']],
      'budget':budget}
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--video-metadata');args=p.parse_args()
    print(json.dumps(export(args.video_metadata),ensure_ascii=False,indent=2))
