"""Create a consistent, read-only SQLite backup of the local LR2 score DB."""
import argparse
from contextlib import closing
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
import tempfile
import time

JST = timezone(timedelta(hours=9))

def backup_database(database, directory):
    source = Path(database).resolve(strict=True)
    if not source.is_file(): raise ValueError('スコアDBがファイルではありません。')
    folder = Path(directory).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(JST).strftime('%Y%m%d_%H%M%S_%f')
    destination = folder / f'{source.stem}_{stamp}.db'
    deadline = time.monotonic() + 60
    def progress(status, remaining, total):
        if time.monotonic() > deadline:
            raise TimeoutError('DBの読み取りが60秒以内に完了しませんでした。LR2を閉じて再実行してください。')
    with tempfile.NamedTemporaryFile(prefix='lr2-backup-', suffix='.tmp', dir=folder, delete=False) as file:
        temporary = Path(file.name)
    try:
        with closing(sqlite3.connect(source.as_uri()+'?mode=ro', uri=True, timeout=10)) as origin:
            origin.execute('PRAGMA query_only=ON')
            origin.execute('PRAGMA trusted_schema=OFF')
            if origin.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='score'").fetchone()[0] != 1:
                raise ValueError('指定したDBにLR2のscoreテーブルがありません。')
            with closing(sqlite3.connect(temporary, timeout=10)) as target:
                origin.backup(target, pages=256, progress=progress, sleep=0.1)
                if target.execute('PRAGMA quick_check').fetchall() != [('ok',)]:
                    raise ValueError('バックアップDBの整合性確認に失敗しました。')
        # rename fails on Windows if this unique destination already exists.
        if destination.exists(): raise FileExistsError('同名のバックアップが既に存在します。')
        temporary.rename(destination)
        return destination
    finally:
        temporary.unlink(missing_ok=True)

def main():
    parser = argparse.ArgumentParser(description='LR2スコアDBの日時付きバックアップを作成します。')
    parser.add_argument('--config', help='databaseとbackupDirectoryを指定したローカル設定')
    parser.add_argument('--db', help='LR2スコアDB。ローカル設定より優先します。')
    parser.add_argument('--directory', help='バックアップ先。ローカル設定より優先します。')
    args = parser.parse_args()
    try:
        config = json.loads(Path(args.config).read_text(encoding='utf-8-sig')) if args.config else {}
        database = args.db or config.get('database')
        directory = args.directory or config.get('backupDirectory')
        if not isinstance(database, str) or not database.strip(): raise ValueError('スコアDBを指定してください。')
        if not isinstance(directory, str) or not directory.strip(): raise ValueError('バックアップ先を指定してください。')
        destination = backup_database(database, directory)
        print(f'バックアップ完了: {destination}')
    except Exception as error:
        parser.exit(1, f'バックアップに失敗しました: {error}\n')

if __name__ == '__main__': main()
