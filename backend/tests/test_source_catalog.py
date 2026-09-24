import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import source_catalog as source
from export_source_catalog import years

def record(title,filename,kind='PDF'):
    return {'asset_file_name':title,'download_filename':filename,'document_type':kind,'local_filenames':[]}

class SourceTests(unittest.TestCase):
    def test_pdf_link_on_related_video_is_not_a_pdf_identity(self):
        pdf=record('DOW-UAP-D010, Mission Report','report.pdf')
        video=record('DOW-UAP-PR019, Recording','report.pdf','VID')
        self.assertIs(source.lookup('report.pdf',[pdf,video]),pdf)

    def test_prefix_does_not_confuse_d10_with_d102(self):
        one=record('DOW-UAP-D010, Report','x.pdf')
        two=record('DOW-UAP-D102, Report','y.pdf')
        self.assertIs(source.lookup('DOW-UAP-D10-Mission.pdf',[one,two]),one)
        self.assertIsNone(source.lookup('random.pdf',[one,two]))

    def test_ambiguity_is_not_silently_resolved(self):
        self.assertIsNone(source.lookup('a.pdf',[record('one','a.pdf'),record('two','a.pdf')]))

    def test_archive_hash_follows_official_algorithm(self):
        self.assertEqual(source.slug('DOW-UAP-D102, Project Blue Book File on Tremonton Film, Utah, 1952'),'DOW-UAP-D102-Project-Blue-Book-File-on-Tremonton-Film-Utah-1952')

    def test_untrusted_source_urls_are_rejected(self):
        for url in ('javascript:alert(1)','https://war.gov.attacker.test/a','http://www.war.gov/a'):
            self.assertEqual(source.safe_url(url),'')
        self.assertEqual(source.safe_url('https://www.war.gov/UFO/'),'https://www.war.gov/UFO/')

    def test_partial_and_multiple_dates_do_not_get_invented_days(self):
        self.assertEqual(years('1950, 1952'),[1950,1952])
        self.assertEqual(years('7/2/52'),[1952])
        self.assertEqual(years('October, 2023'),[2023])
        self.assertEqual(years('Unknown'),[])

if __name__=='__main__':unittest.main()
