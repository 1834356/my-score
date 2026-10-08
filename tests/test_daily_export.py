import hashlib
import importlib.util
from pathlib import Path
import sqlite3
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('exporter',Path(__file__).resolve().parents[1]/'export_scores.py')
exporter=importlib.util.module_from_spec(spec)
spec.loader.exec_module(exporter)

class DailyExportTests(unittest.TestCase):
    def test_note_count_updates_and_shared_membership(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            assert Path(directory).resolve().parent == Path.cwd().resolve()
            database=Path(directory)/'fixture.db'
            with sqlite3.connect(database) as c:
                c.execute('CREATE TABLE score(hash TEXT, clear INTEGER, minbp INTEGER, playcount INTEGER)')
                c.execute('INSERT INTO score VALUES(?,?,?,?)',('a'*32,4,0,3))
                c.execute('''CREATE TABLE bms_lr2_play_history(history_id INTEGER, hash TEXT, played_at INTEGER,
                    finalized INTEGER, player_playcount_delta INTEGER, judge_delta INTEGER, playtime_delta INTEGER,
                    old_clear INTEGER,new_clear INTEGER,old_minbp INTEGER,new_minbp INTEGER,
                    old_totalnotes INTEGER,new_totalnotes INTEGER,old_exscore INTEGER,new_exscore INTEGER)''')
                c.executemany('INSERT INTO bms_lr2_play_history VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',[
                    (1,'a'*32,1728000000,1,2,999,120,0,3,None,50,None,100,None,150),
                    (2,'a'*32,1728000060,1,1,999,60,3,4,50,0,100,100,150,180),
                    (3,'b'*160,1728000120,1,1,500,60,0,1,None,500,None,None,None,0),
                    (4,'a'*32,1728000180,0,None,None,None,4,4,0,0,100,100,180,180)])
            c.close()
            before=hashlib.sha256(database.read_bytes()).digest()
            definitions=[({'name':'A','symbol':'★'},[{'md5':'a'*32,'title':'Test','level':1}],exporter.DEFAULT_TABLE),
                ({'name':'B','symbol':'st'},[{'md5':'a'*32,'title':'Test','level':0}],'https://stellabms.xyz/st/table.html')]
            result=exporter.build_many(database,definitions)
            day=result['history']['days'][0]
            self.assertEqual(day['notes'],300)
            self.assertEqual(day['judgements'],2498)
            self.assertEqual(day['plays'],4)
            self.assertEqual(day['notesMissingPlays'],1)
            self.assertEqual((day['bpUpdates'],day['scoreUpdates']),(1,1))
            self.assertEqual(result['history']['excludedUnfinalized'],1)
            self.assertEqual(day['entries'][0]['tableLabels'],['★1','st0'])
            self.assertFalse(day['entries'][0]['bpUpdated'])
            self.assertFalse(day['entries'][0]['scoreUpdated'])
            self.assertEqual(day['entries'][1]['newMinBp'],0)
            self.assertEqual(len(day['entries'][2]['chartId']),32)
            self.assertNotIn('b'*160,str(result))
            self.assertEqual(hashlib.sha256(database.read_bytes()).digest(),before)

if __name__=='__main__':
    unittest.main()
