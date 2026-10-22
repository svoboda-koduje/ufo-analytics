import json,sqlite3,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from audit_pdf_results import audit

class AuditEmptyReading(unittest.TestCase):
    def check(self, text, source=True):
        with sqlite3.connect(':memory:') as db:
            db.executescript('CREATE TABLE research_units(sha256,unit_key,result); CREATE TABLE research_documents(sha256,result); CREATE TABLE units(sha256,unit_key,result,completed_at);')
            value={'status':'partial','source_unit':'page:1','parts':[{'translation_status':'partial','translation_cs':'','summary_cs':'Fotografie bez čitelného popisku.','limitations_cs':['Text není čitelný.']}]}
            db.execute('INSERT INTO research_units VALUES(?,?,?)',('x','page:1',json.dumps(value)))
            if source:db.execute('INSERT INTO units VALUES(?,?,?,?)',('x','page:1',json.dumps({'text':text}),'now'))
            return audit(db,{'files':[{'sha':'x','name':'test.pdf','pages':1}],'pages':1})
    def test_punctuation_only_image_is_warning(self):
        result=self.check('• \n')
        self.assertEqual(result['errors'],[])
        self.assertEqual(len(result['warnings']),1)
    def test_missing_translation_with_real_text_remains_error(self):
        self.assertEqual(len(self.check('1952 Utah')['errors']),1)
    def test_unknown_source_is_not_exempt(self):
        self.assertEqual(len(self.check('',source=False)['errors']),1)

if __name__=='__main__':unittest.main()
