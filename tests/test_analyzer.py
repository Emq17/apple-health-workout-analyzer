import sys
import unittest
from unittest.mock import patch
from datetime import datetime, timedelta, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from extract_cadence import list_workouts, overlapping_steps, summarize, choose_source, mmss, select_interval, format_duration

SAMPLE = Path(__file__).resolve().parents[1] / 'examples' / 'synthetic_sample.xml'

class AnalyzerTests(unittest.TestCase):
    def test_fixture_and_source_name_independence(self):
        workouts = list_workouts(SAMPLE)
        self.assertEqual(len(workouts), 1)
        w = workouts[0]
        records = overlapping_steps(SAMPLE, w['start'], w['end'])
        source, chosen = choose_source(records, w['source'], None, True)
        self.assertEqual(source, 'Example Runner Watch')
        result = summarize(chosen, w['start'], w['end'])
        self.assertEqual(result['count'], 2)
        self.assertEqual(result['cadence'], 180)
        self.assertEqual(result['missing'], 0)
        self.assertEqual(result['overlap'], 0)
    def test_gap(self):
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        rows = [{'start':start,'end':start+timedelta(seconds=20),'steps':60},
                {'start':start+timedelta(seconds=30),'end':start+timedelta(seconds=60),'steps':90}]
        result = summarize(rows, start, start+timedelta(seconds=60))
        self.assertEqual(result['missing'], 10)
    def test_overlap(self):
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        rows = [{'start':start,'end':start+timedelta(seconds=40),'steps':120},
                {'start':start+timedelta(seconds=30),'end':start+timedelta(seconds=60),'steps':90}]
        self.assertEqual(summarize(rows, start, start+timedelta(seconds=60))['overlap'], 10)
    def test_entire_workout_selection(self):
        with patch('builtins.input', return_value='1'):
            self.assertEqual(select_interval(518), (0, 518))

    def test_custom_section_mmss(self):
        with patch('builtins.input', side_effect=['2', '00:17', '08:27']):
            self.assertEqual(select_interval(518), (17, 507))

    def test_invalid_custom_section(self):
        with patch('builtins.input', side_effect=['2', '00:17', '09:00']):
            with self.assertRaises(ValueError):
                select_interval(518)

    def test_format_duration(self):
        self.assertEqual(format_duration(518), '08:38')

    def test_offsets(self):
        self.assertEqual(mmss('8:10'), 490)
        self.assertEqual(mmss('01:02:03'), 3723)

if __name__ == '__main__':
    unittest.main()
