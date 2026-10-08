import hashlib
import importlib.util
from pathlib import Path
import sqlite3
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('backup', Path(__file__).resolve().parents[1]/'backup_scores.py')
backup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backup)

class BackupTests(unittest.TestCase):
    def test_wal_snapshot_and_existing_backups_preserved(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            root = Path(directory)
            source = root/'player.db'
            connection = sqlite3.connect(source)
            try:
                connection.execute('PRAGMA journal_mode=WAL')
                connection.execute('CREATE TABLE score(hash TEXT, minbp INTEGER)')
                connection.execute('INSERT INTO score VALUES (?,?)', ('a'*32, 7))
                connection.commit()
                wal = Path(str(source)+'-wal')
                before = [(p, hashlib.sha256(p.read_bytes()).digest()) for p in (source, wal)]
                folder = root/'日本語 バックアップ'
                first = backup.backup_database(source, folder)
                second = backup.backup_database(source, folder)
                self.assertNotEqual(first, second)
                self.assertEqual(len(list(folder.glob('*.db'))), 2)
                self.assertEqual(list(folder.glob('*.tmp')), [])
                for output in (first, second):
                    with sqlite3.connect(output) as reader:
                        self.assertEqual(reader.execute('SELECT minbp FROM score').fetchall(), [(7,)])
                        self.assertEqual(reader.execute('PRAGMA quick_check').fetchone(), ('ok',))
                    reader.close()
                for p, digest in before:
                    self.assertEqual(hashlib.sha256(p.read_bytes()).digest(), digest)
            finally:
                connection.close()

    def test_invalid_source_leaves_no_backup(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            root = Path(directory)
            source = root/'invalid.db'
            source.write_bytes(b'not a sqlite database')
            folder = root/'backups'
            with self.assertRaises(sqlite3.DatabaseError):
                backup.backup_database(source, folder)
            self.assertEqual(list(folder.iterdir()), [])

if __name__ == '__main__': unittest.main()
