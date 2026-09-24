import json
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import uuid

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import local_archive as archive
import research
from local_workbench import Workbench


def reading(events=None):
    return {'translation_cs':'Úplný český text.','translation_status':'translated',
            'summary_cs':'České shrnutí.','context_cs':'Svědecké hlášení.',
            'observations_cs':[],'limitations_cs':[],'document_date':None,'events':events or []}


def event(**values):
    result=dict(kind='observation',description_cs='Pozorování',year=None,year_evidence=None,
                date_iso=None,date_evidence=None,country_cs=None,country_evidence=None,
                time_local=None,time_evidence=None,timezone=None)
    result.update(values)
    return result


class ResearchTests(unittest.TestCase):
    def setUp(self):
        self.root=Path(__file__).resolve().parents[1]/'local_state/tests'/uuid.uuid4().hex
        self.root.mkdir(parents=True)
        self.path=self.root/'archive.sqlite3'
        self.db=archive.connect(self.path)
        research.prepare(self.db)
        with self.db: self.db.execute('UPDATE research_budget SET limit_usd=1')

    def tearDown(self):
        self.db.close()
        shutil.rmtree(self.root)

    def test_long_text_split_preserves_every_character(self):
        text=('Dlouhý text\n s diakritikou. '*900)+'KONEC'
        parts=research.chunks(text)
        self.assertGreater(len(parts),1)
        self.assertEqual(''.join(parts),text)
        self.assertLessEqual(max(map(len,parts)),6000)

    def test_document_dates_and_unquoted_fields_are_excluded(self):
        result=research.validate_reading(reading([
            event(kind='administrative',year=1973,year_evidence='1973'),
            event(year=1947,year_evidence='1947',country_cs='USA',country_evidence='not in source')]),'1947 and 1973')
        self.assertEqual(len(result['events']),1)
        self.assertEqual(result['events'][0]['year'],1947)
        self.assertIsNone(result['events'][0]['country_cs'])
        wrong=research.validate_reading(reading([event(year=1947,year_evidence='1946')]),'1946')
        self.assertIsNone(wrong['events'][0]['year'])

    def test_filters_match_same_event_and_overnight_time(self):
        a=event(year=1947,country_cs='USA',time_local='23:30')
        b=event(year=2001,country_cs='Gruzie',time_local='14:00')
        f={'year_from':'1947','year_to':'1947','country':'Gruzie'}
        self.assertFalse(any(research.matches_event(e,f) for e in [a,b]))
        self.assertTrue(research.matches_event(a,{'time_from':'22:00','time_to':'02:00'}))
        self.assertFalse(research.matches_event(b,{'time_from':'22:00','time_to':'02:00'}))
        self.assertFalse(research.matches_event(event(),{'year_from':'1900'}))

    def test_budget_reserves_before_call_and_blocks_overrun(self):
        research.reserve(self.db,'one',.75)
        with self.assertRaisesRegex(RuntimeError,'limit'):
            research.reserve(self.db,'two',.5)
        self.assertEqual(research.budget(self.db)['accounted_usd'],.75)

    def test_paid_response_is_cached_and_read_without_api(self):
        output=reading()
        response=SimpleNamespace(status='completed',output_text=json.dumps(output),
            usage=SimpleNamespace(input_tokens=100,output_tokens=100),model_dump_json=lambda:'{}')
        api=SimpleNamespace(responses=SimpleNamespace(create=Mock(return_value=response)))
        payload=json.dumps({'text':'Original source'})
        self.assertEqual(research.invoke(self.db,api,payload)['summary_cs'],'České shrnutí.')
        spent=research.budget(self.db)
        research.invoke(self.db,api,payload)
        self.assertEqual(api.responses.create.call_count,1)
        self.assertEqual(research.budget(self.db),spent)

    def test_uncertain_call_not_automatically_repeated(self):
        api=SimpleNamespace(responses=SimpleNamespace(create=Mock(side_effect=TimeoutError())))
        payload=json.dumps({'text':'Source'})
        with self.assertRaises(RuntimeError): research.invoke(self.db,api,payload)
        with self.assertRaisesRegex(RuntimeError,'Předchozí'): research.invoke(self.db,api,payload)
        self.assertEqual(api.responses.create.call_count,1)
        self.assertGreater(research.budget(self.db)['accounted_usd'],0)

    def test_incomplete_response_not_published(self):
        response=SimpleNamespace(status='incomplete',output_text='{}',usage=SimpleNamespace(input_tokens=100,output_tokens=12000),model_dump_json=lambda:'{}')
        api=SimpleNamespace(responses=SimpleNamespace(create=Mock(return_value=response)))
        with self.assertRaises(RuntimeError):research.invoke(self.db,api,json.dumps({'text':'Source'}))
        self.assertEqual(self.db.execute('SELECT state FROM research_calls').fetchone()[0],'received')
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM research_units').fetchone()[0],0)

    def test_catalog_validates_filters_without_charging(self):
        bench=Workbench(self.path)
        try:
            with self.assertRaises(ValueError):bench.catalog(filters={'time_from':'25:00'})
            with self.assertRaises(ValueError):bench.catalog(filters={'year_from':'2000','year_to':'1900'})
            self.assertEqual(bench.catalog('český')['assets'],[])
            self.assertEqual(research.budget(self.db)['accounted_usd'],0)
        finally:bench.pool.shutdown()

    def test_czech_search_and_filters_return_the_same_event(self):
        sha='a'*64
        source=self.root/'report.pdf'
        payload={'status':'ready','parts':[reading([event(year=1947,country_cs='USA'),event(year=2001,country_cs='Gruzie')])]}
        with self.db:
            self.db.execute('INSERT INTO assets(sha256,extension,size,metadata) VALUES(?,?,?,?)',(sha,'.pdf',10,json.dumps({'kind':'pdf','pages':1})))
            self.db.execute('INSERT INTO paths VALUES(?,?,?,1)',(str(source),str(self.root),sha))
            self.db.execute('INSERT INTO research_units VALUES(?,?,?,?,?)',(sha,'page:1','hash',json.dumps(payload),archive.now()))
            self.db.execute('INSERT INTO research_search VALUES(?,?,?)',(sha,'page:1','České svědectví o světle.'))
        bench=Workbench(self.path)
        try:
            self.assertEqual(len(bench.catalog('svedectvi')['assets']),1)
            self.assertEqual(bench.catalog('svedectvi',{'year_from':'1947','year_to':'1947','country':'Gruzie'})['assets'],[])
            result=bench.catalog('svedectvi',{'year_from':'2001','country':'Gruzie'})
            self.assertEqual(len(result['assets']),1)
            self.assertEqual(len(result['hits']),1)
            self.assertEqual(result['assets'][0]['matching_events'][0]['year'],2001)
        finally:bench.pool.shutdown()

    def test_document_summary_rejects_invented_page_reference(self):
        payload={'status':'ready','parts':[reading()]}
        with self.db:self.db.execute('INSERT INTO research_units VALUES(?,?,?,?,?)',('a'*64,'page:1','hash',json.dumps(payload),archive.now()))
        bad={'overview_cs':'Souhrn','context_cs':'Kontext','findings':[{'text_cs':'Tvrzení','source_units':['page:99']}],'limitations_cs':[]}
        with patch.object(research,'invoke',return_value=bad):
            with self.assertRaisesRegex(ValueError,'neexistující'):
                research.document_summary(self.db,object(),'a'*64)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM research_documents').fetchone()[0],0)

    def test_document_summary_consumes_all_source_groups(self):
        payload={'status':'ready','parts':[reading()]}
        with self.db:
            for i in range(33):self.db.execute('INSERT INTO research_units VALUES(?,?,?,?,?)',('a'*64,f'page:{i+1}','hash',json.dumps(payload),archive.now()))
        seen=[]
        def synthesize(db,api,payload,**kwargs):
            sources=json.loads(payload)['sources']
            refs=[]
            for s in sources:
                refs.extend(s.get('source_units',[]))
                refs.extend(r for f in s.get('findings',[]) for r in f['source_units'])
            seen.extend(refs)
            return {'overview_cs':'Souhrn','context_cs':'Kontext','findings':[{'text_cs':'Tvrzení','source_units':refs}],'limitations_cs':[]}
        with patch.object(research,'invoke',side_effect=synthesize):
            research.document_summary(self.db,object(),'a'*64)
        self.assertTrue({f'page:{i+1}' for i in range(33)} <= set(seen))
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM research_documents').fetchone()[0],1)

    def test_new_ocr_invalidates_old_translation_and_overview(self):
        import pymupdf
        import local_analysis as analysis
        try:analysis.tesseract()
        except RuntimeError:self.skipTest('Tesseract is not installed')
        folder=self.root/'input';folder.mkdir()
        pdf=folder/'source.pdf'
        with pymupdf.open() as doc:
            doc.new_page().insert_text((50,50),'Original observation over the ocean in the evening.')
            doc.save(pdf)
        archive.scan(self.db,folder)
        sha=archive.digest(pdf)
        analysis.analyze(self.db,sha,self.root/'previews')
        with self.db:
            self.db.execute('INSERT INTO research_units VALUES(?,?,?,?,?)',(sha,'page:1','old','{}',archive.now()))
            self.db.execute('INSERT INTO research_search VALUES(?,?,?)',(sha,'page:1','Zastaralý překlad'))
            self.db.execute('INSERT INTO research_documents VALUES(?,?,?)',(sha,'{}',archive.now()))
        with patch.object(analysis,'ocr_image',return_value={'state':'done','text':'Corrected observation'}):
            analysis.analyze(self.db,sha,self.root/'previews',force_ocr=True)
        for table in ('research_units','research_search','research_documents'):
            self.assertEqual(self.db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0],0)


if __name__=='__main__':unittest.main()
