from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest

from export_bmz import JUDGES, build_bmz, ln_policy


class BmzExportTests(unittest.TestCase):
    def test_ln_settings_match_the_chart_score_key(self):
        chart = dict(has_undefined_ln=0, has_defined_ln=0, has_defined_cn=0, has_defined_hcn=0)
        self.assertEqual(ln_policy('ForceHcn', chart), 'ForceLn')
        self.assertEqual(ln_policy('AutoHcn', chart | {'has_defined_cn': 1}), 'ForceCn')
        self.assertEqual(ln_policy('AutoHcn', chart | {'has_undefined_ln': 1}), 'ForceHcn')
        self.assertEqual(ln_policy('AutoHcn', chart | {'has_defined_cn': 1, 'has_undefined_ln': 1}), 'AutoHcn')
        self.assertEqual(ln_policy('AutoHcn', chart | {'has_defined_cn': 1, 'has_defined_ln': 1}), 'AutoLn')

    def test_bests_and_only_local_plays_are_exported(self):
        with tempfile.TemporaryDirectory() as folder:
            library, scores = Path(folder)/'library.db', Path(folder)/'score.db'
            sha, md5, unmatched = 'a'*64, 'b'*32, 'c'*32
            with closing(sqlite3.connect(library)) as db, db:
                db.execute('''CREATE TABLE charts (id INTEGER, sha256 TEXT, md5 TEXT, title TEXT,
                    subtitle TEXT, has_undefined_ln INTEGER, has_defined_ln INTEGER,
                    has_defined_cn INTEGER, has_defined_hcn INTEGER, folder_path TEXT)''')
                db.execute('INSERT INTO charts VALUES(1,?,?,?,?,1,0,0,0,?)',
                           (sha, md5, 'Library title', '[7K]', 'do-not-publish'))
            with closing(sqlite3.connect(scores)) as db, db:
                db.execute('''CREATE TABLE score_best (chart_sha256 TEXT, ln_policy TEXT,
                    double_option TEXT, rule_mode TEXT, clear_type TEXT, ex_score INTEGER,
                    bp INTEGER, best_score_history_id INTEGER)''')
                judges = ','.join(f'{side}_{judge} INTEGER DEFAULT 0' for judge in JUDGES for side in ('fast', 'slow'))
                db.execute(f'''CREATE TABLE score_history (id INTEGER PRIMARY KEY, chart_sha256 TEXT,
                    ln_policy TEXT, double_option TEXT, rule_mode TEXT, clear_type TEXT, bp INTEGER,
                    ex_score INTEGER, total_notes INTEGER, played_at INTEGER, old_clear_type TEXT,
                    old_bp INTEGER, old_ex_score INTEGER, autoplay INTEGER, source_kind TEXT,
                    course_score_id INTEGER, {judges})''')
                db.execute('CREATE TABLE score_history_sources(score_history_id INTEGER, account_id TEXT)')
                db.executemany('INSERT INTO score_best VALUES(?,?,?,?,?,?,?,?)', [
                    (sha, 'ForceLn', 'Off', 'Lr2Oraja', 'ExHard', 180, 0, 1),
                    (sha, 'ForceCn', 'Off', 'Lr2Oraja', 'Max', 230, 0, 2),
                    (sha, 'ForceLn', 'Off', 'Beatoraja', 'Max', 200, 0, 3),
                ])
                rows = [
                    (1, 'ForceLn', 'Off', 'Lr2Oraja', 'ExHard', 12, 180, 100, 'Hard', 16, 170, 0, 'Local', None),
                    (2, 'ForceCn', 'Off', 'Lr2Oraja', 'Max', 0, 230, 115, None, None, None, 0, 'Local', None),
                    (3, 'ForceLn', 'Off', 'Beatoraja', 'Max', 0, 200, 100, None, None, None, 0, 'Local', None),
                    (4, 'ForceLn', 'Off', 'Lr2Oraja', 'Hard', 16, 170, 100, None, None, None, 0, 'Lr2', None),
                    (5, 'ForceLn', 'Off', 'Lr2Oraja', 'Hard', 16, 170, 100, None, None, None, 0, 'Local', None),
                    (6, 'ForceLn', 'Off', 'Lr2Oraja', 'Max', 0, 200, 100, None, None, None, 1, 'Local', None),
                    (7, 'ForceLn', 'Off', 'Lr2Oraja', 'Hard', 16, 170, 100, None, None, None, 0, 'Local', 1),
                    (8, 'ForceLn', 'Battle', 'Lr2Oraja', 'Max', 0, 200, 100, None, None, None, 0, 'Local', None),
                    (9, 'ForceLn', 'Off', 'Lr2Oraja', 'Failed', 40, 140, 100, 'ExHard', 0, 180, 0, 'Local', None),
                ]
                for ident, policy, double, rule, lamp, bp, ex, notes, old_lamp, old_bp, old_ex, auto, source, course in rows:
                    db.execute('''INSERT INTO score_history(id,chart_sha256,ln_policy,double_option,rule_mode,
                        clear_type,bp,ex_score,total_notes,played_at,old_clear_type,old_bp,old_ex_score,autoplay,
                        source_kind,course_score_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                        (ident,sha,policy,double,rule,lamp,bp,ex,notes,1735686000+ident,old_lamp,old_bp,old_ex,auto,source,course))
                db.execute("INSERT INTO score_history_sources VALUES(5,'private-account')")
            before = {p: p.read_bytes() for p in (library, scores)}
            tables = {'tables': [
                {'id': 'a', 'name': 'A', 'symbol': '★', 'charts': [
                    {'md5': md5, 'title': 'Table title', 'level': '1', 'lamp': 1, 'minBp': 999},
                    {'md5': unmatched, 'title': 'LR2 only', 'level': '2', 'lamp': 6, 'minBp': 0},
                ]},
                {'id': 'b', 'name': 'B', 'symbol': 'sl', 'charts': [{'md5': md5, 'title': 'Table title', 'level': '0'}]},
            ]}
            payload = build_bmz({'scoreDatabase': scores, 'libraryDatabase': library,
                                 'ruleMode': 'Lr2Oraja', 'lnSetting': 'ForceLn'}, tables)
            chart, blank = payload['tables'][0]['charts']
            self.assertEqual((chart['lamp'], chart['exScore'], chart['minBp'], chart['totalNotes']), (7, 180, 0, 100))
            self.assertEqual((blank['lamp'], blank['minBp']), (0, None))
            day, = payload['history']['days']
            self.assertEqual((day['plays'], day['notes'], day['seconds']), (2, 200, None))
            self.assertEqual((day['lampUpdates'], day['bpUpdates'], day['scoreUpdates']), (1, 1, 1))
            improved, failed = day['entries']
            self.assertEqual((improved['oldLamp'], improved['newLamp']), (6, 7))
            self.assertEqual((failed['oldLamp'], failed['newLamp'], failed['newMinBp']), (7, 7, 0))
            self.assertEqual(improved['tableLabels'], ['★1', 'sl0'])
            self.assertEqual(improved['title'], 'Library title [7K]')
            self.assertNotIn('private-account', str(payload))
            self.assertNotIn('do-not-publish', str(payload))
            for path, content in before.items():
                self.assertEqual(path.read_bytes(), content)


if __name__ == '__main__':
    unittest.main()
