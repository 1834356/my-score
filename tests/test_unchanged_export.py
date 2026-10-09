import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('exporter', Path(__file__).resolve().parents[1]/'export_scores.py')
exporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exporter)

class UnchangedExportTests(unittest.TestCase):
    def test_timestamp_only_does_not_rewrite_but_table_and_history_changes_do(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            destination = Path(directory)/'viewer.json'
            payload = {'schemaVersion':1, 'generatedAt':'before', 'tables':[{'charts':[{'minBp':0}]}], 'history':None}
            self.assertTrue(exporter.write_atomic(destination, payload))
            original = destination.read_bytes()
            modified = destination.stat().st_mtime_ns
            self.assertFalse(exporter.write_atomic(destination, {**payload, 'generatedAt':'after'}))
            self.assertEqual(destination.read_bytes(), original)
            self.assertEqual(destination.stat().st_mtime_ns, modified)
            for changed in ({**payload, 'tables':[]}, {**payload, 'history':{'days':[]}}):
                self.assertTrue(exporter.write_atomic(destination, changed))
                self.assertEqual(json.loads(destination.read_text(encoding='utf-8')), changed)
            destination.write_text('invalid json', encoding='utf-8')
            self.assertTrue(exporter.write_atomic(destination, payload))
            self.assertEqual(list(destination.parent.glob('*.tmp')), [])

if __name__ == '__main__': unittest.main()
