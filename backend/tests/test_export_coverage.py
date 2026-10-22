import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from export_source_catalog import coverage

class ExportCoverage(unittest.TestCase):
    def test_pdf_requires_exact_page_coverage_and_dossier(self):
        meta={'kind':'pdf','pages':2}
        units=[{'unit_key':'page:1'},{'unit_key':'page:2','status':'partial'}]
        self.assertTrue(coverage(meta,units,True)['complete'])
        self.assertEqual(coverage(meta,units,True)['partial_units'],1)
        self.assertFalse(coverage(meta,units,False)['complete'])
        self.assertFalse(coverage(meta,[units[0],{'unit_key':'page:3'}],True)['complete'])
    def test_video_is_always_a_sample(self):
        value=coverage({'kind':'video'},[{'unit_key':'frame:1'}],True)
        self.assertFalse(value['complete']);self.assertEqual(value['scope'],'sample')
    def test_image_can_be_complete(self):
        self.assertTrue(coverage({'kind':'image'},[{'unit_key':'image:1'}],True)['complete'])

if __name__=='__main__':unittest.main()
