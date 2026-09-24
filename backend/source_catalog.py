"""Provenance catalogue. No media downloads, guessed row IDs, or paid calls on reads."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlparse

BASE = Path(__file__).resolve().parent
CATALOG = BASE / 'source_catalog.json'
RELEASES = {'5/8/26':'01','5/22/26':'02','6/12/26':'03','7/10/26':'04','8/7/26':'05','9/18/26':'06'}

def slug(title):
    return re.sub('-+', '-', re.sub(r'[^A-Za-z0-9\-_]', '', re.sub(r'\s+', '-', title.strip())))

def identity(text):
    m = re.search(r'\b(?:DOW|DOD|FBI|NASA|CIA|DOS|LLE)-UAP-(?:PR|D)?0*([0-9]+)\b', text, re.I)
    if not m: return None
    raw = m.group().upper()
    return re.sub(r'(?<=-)0+(?=\d)|(?<=[A-Z])0+(?=\d)', '', raw)

def safe_url(value):
    p = urlparse(value)
    return value if p.scheme == 'https' and (p.hostname in {'www.war.gov','war.gov','media.defense.gov','www.dvidshub.net','dvidshub.net'} or (p.hostname or '').endswith('.dvidshub.net')) else ''

def load():
    return json.loads(CATALOG.read_text(encoding='utf-8')) if CATALOG.exists() else []

def lookup(filename, records=None):
    records = load() if records is None else records
    name = Path(filename).name.casefold()
    ext=Path(filename).suffix.lower()
    kinds={'.pdf':{'PDF'},'.mp4':{'VID','AUD'},'.jpg':{'JPG','JPEG','IMAGE','IMG'},'.jpeg':{'JPG','JPEG','IMAGE','IMG'},'.png':{'PNG','IMAGE','IMG'}}
    if ext in kinds: records=[r for r in records if r['document_type'].strip().lstrip('.').upper() in kinds[ext]]
    found = [r for r in records if name in [x.casefold() for x in r.get('local_filenames',[])] or name == r.get('download_filename','').casefold() or name == r['asset_file_name'].casefold()]
    if len(found) == 1: return found[0]
    if found: return None
    key = identity(filename)
    found = [r for r in records if key and identity(r['asset_file_name']) == key]
    return found[0] if len(found) == 1 else None

def build(csv_path, archive_path):
    raw = Path(csv_path).read_bytes()
    try: text = raw.decode('utf-8-sig')
    except UnicodeDecodeError: text = raw.decode('cp1252')
    rows = list(csv.DictReader(io.StringIO(text)))
    previous = {r['source_id']:r for r in load()}
    records=[]
    for row in rows:
        title=row['Title'].strip()
        if not title: continue
        release=RELEASES[row['Release Date']]
        url=safe_url(row['PDF | Image Link'].strip().split('|')[0].strip())
        description=row['Description Blurb'].strip()
        record={'source_id':slug(title), 'asset_file_name':title, 'row_title':title,
          'source_url':f'https://www.war.gov/UFO/release/{release}/?release={release}#{slug(title)}',
          'download_url':url,'download_filename':unquote(urlparse(url).path.rsplit('/',1)[-1]) if url else '',
          'release':release,'release_date':row['Release Date'], 'agency':row['Agency'],
          'incident_date':row['Incident Date'],'incident_location':row['Incident Location'],
          'document_type':row['Type'].strip().upper(),'virin':row['Image VIRIN'],
          'video_id':row['DVIDS Video ID'], 'description_en':description,
          'related_ids':[x.strip() for x in (row['Video Pairing']+'|'+row['PDF Pairing']).split('|') if x.strip()],
          'local_filenames':[], 'provenance':{'url':'https://www.war.gov/Portals/1/Interactive/2026/UFO/uap-data.csv?release=6v3','retrieved_at':'2026-09-24','sha256':hashlib.sha256(raw).hexdigest()},
          'content_hash':hashlib.sha256((title+description+row['Incident Date']+row['Incident Location']).encode()).hexdigest()}
        old=previous.get(record['source_id'],{})
        if old.get('content_hash')==record['content_hash']:
            for key in ('translation','translation_model','translation_status'):
                if key in old: record[key]=old[key]
        records.append(record)
    unmatched=[]
    for path in Path(archive_path).rglob('*'):
        if not path.is_file() or path.name.startswith('.') or '__MACOSX' in path.parts: continue
        record=lookup(path.name, records)
        if record: record['local_filenames'].append(path.name)
        else: unmatched.append(path.name)
    if len({r['source_id'] for r in records})!=len(records): raise ValueError('Duplicate source IDs')
    save(records)
    return {'records':len(records),'release06':sum(r['release']=='06' for r in records),'matched':sum(bool(r['local_filenames']) for r in records),'unmatched_files':unmatched,'unmatched_records':[r['asset_file_name'] for r in records if not r['local_filenames']]}

def save(records):
    temp=CATALOG.with_suffix('.tmp')
    temp.write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
    temp.replace(CATALOG)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('csv');p.add_argument('--archive',default=BASE/'incoming_data');args=p.parse_args()
    print(json.dumps(build(args.csv,args.archive),ensure_ascii=False,indent=2))
