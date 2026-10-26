import unittest
from report_summary import summarize, known_label


class ReportCoverageTests(unittest.TestCase):
    def test_missing_is_per_statistic_and_zero_is_recorded(self):
        rows = [
            {'group': 'Lab', 'minutes': 0, 'software': ['A', 'A']},
            {'group': 'Lab', 'minutes': None, 'software': ['B']},
            {'group': '[Non Renseigné]', 'minutes': 60, 'software': []},
            {'group': '[Imaging Lab]', 'minutes': 120, 'software': ['Non renseigné', 'A']},
        ]
        groups = summarize(rows, 'group')
        self.assertEqual(groups['excluded'], 2)
        self.assertEqual([(i['label'], i['value']) for i in groups['items']], [('[Imaging Lab]', 120), ('Lab', 0)])
        science = summarize(rows, 'software')
        self.assertEqual(science['excluded'], 1)
        self.assertEqual([(i['label'], i['count']) for i in science['items']], [('A', 2), ('B', 1)])
        self.assertEqual(rows[2]['group'], '[Non Renseigné]')

    def test_empty_and_entirely_missing(self):
        self.assertEqual(summarize([], 'group')['excluded'], 0)
        result = summarize([{'group': ' ', 'minutes': None}], 'group')
        self.assertEqual(result['items'], [])
        self.assertEqual(result['excluded'], 1)
        for value in [None, '', ' [Non Renseigné] ', 'Unknown', 'Not specified']:
            self.assertFalse(known_label(value))
        self.assertTrue(known_label('[Cellular Imaging Facility]'))

    def test_export_keeps_raw_projects_and_explains_filtered_categories(self):
        import io, zipfile, csv
        from data_store import export_activity
        row = dict(title='Historical', group='[Non Renseigné]', contact='Contact',
                   status='Unknown', minutes=60, session_count=1, activity_type='',
                   software=[], modalities=[], topics=[])
        report = dict(projects=[row], start='2026-01-01', end='2026-12-31',
                      total_minutes=60, group_count=0, contact_count=1,
                      entries_without_time=0, warnings=[])
        with zipfile.ZipFile(io.BytesIO(export_activity(report))) as archive:
            read = lambda name: list(csv.reader(io.StringIO(archive.read(name).decode('utf-8-sig'))))
            self.assertEqual(len(read('group.csv')), 1)
            self.assertEqual(len(read('projects.csv')), 2)
            self.assertEqual(read('coverage.csv')[1][1:3], ['0', '1'])
            self.assertIn('1 projet(s) exclus', archive.read('README.html').decode())
            self.assertTrue(archive.read('activity-report.pdf').startswith(b'%PDF'))


if __name__ == '__main__':
    unittest.main()
