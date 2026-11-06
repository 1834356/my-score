"""Create a consistent, read-only SQLite backup of the local LR2 or BMZ score DB."""
import argparse
import hashlib
from contextlib import closing
from datetime import datetime, timedelta, timezone
import json
import re
from pathlib import Path
import sqlite3
import tempfile
import time

JST = timezone(timedelta(hours=9))

def file_digest(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.digest()

def backup_database(database, directory, force=False, player='lr2'):
    source = Path(database).resolve(strict=True)
    if not source.is_file(): raise ValueError('スコアDBがファイルではありません。')
    folder = Path(directory).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(JST).strftime('%Y%m%d_%H%M%S_%f')
    stem = f'bmz_{source.parent.name}_{source.stem}' if player == 'bmz' else source.stem
    destination = folder / f'{stem}_{stamp}.db'
    required = {'score_best', 'score_history'} if player == 'bmz' else {'score'}
    deadline = time.monotonic() + 60
    def progress(status, remaining, total):
        if time.monotonic() > deadline:
            raise TimeoutError('DBの読み取りが60秒以内に完了しませんでした。プレイヤーを閉じて再実行してください。')
    with tempfile.NamedTemporaryFile(prefix='bms-backup-', suffix='.tmp', dir=folder, delete=False) as file:
        temporary = Path(file.name)
    try:
        with closing(sqlite3.connect(source.as_uri()+'?mode=ro', uri=True, timeout=10)) as origin:
            origin.execute('PRAGMA query_only=ON')
            origin.execute('PRAGMA trusted_schema=OFF')
            tables = {row[0] for row in origin.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if not required <= tables:
                raise ValueError(f'指定したDBは{player.upper()}のスコアDBではありません。')
            with closing(sqlite3.connect(temporary, timeout=10)) as target:
                origin.backup(target, pages=256, progress=progress, sleep=0.1)
                if target.execute('PRAGMA quick_check').fetchall() != [('ok',)]:
                    raise ValueError('バックアップDBの整合性確認に失敗しました。')
        # Compare the consistent snapshot, including committed WAL contents.
        pattern = re.compile(re.escape(stem) + r'_\d{8}_\d{6}_\d{6}\.db$')
        previous = max((p for p in folder.iterdir() if p.is_file() and pattern.fullmatch(p.name)),
                       key=lambda p: p.name, default=None)
        if not force and previous is not None and file_digest(previous) == file_digest(temporary):
            return None
        # rename fails on Windows if this unique destination already exists.
        if destination.exists(): raise FileExistsError('同名のバックアップが既に存在します。')
        temporary.rename(destination)
        return destination
    finally:
        temporary.unlink(missing_ok=True)

def main():
    parser = argparse.ArgumentParser(description='LR2またはBMZのスコアDBを日時付きでバックアップします。')
    parser.add_argument('--player', choices=('lr2','bmz'), default='lr2')
    parser.add_argument('--config', help='databaseとbackupDirectoryを指定したローカル設定')
    parser.add_argument('--db', help='LR2スコアDB。ローカル設定より優先します。')
    parser.add_argument('--directory', help='バックアップ先。ローカル設定より優先します。')
    parser.add_argument('--force', action='store_true', help='同じ内容でも日時付きバックアップを保存します。')
    args = parser.parse_args()
    try:
        config = json.loads(Path(args.config).read_text(encoding='utf-8-sig')) if args.config else {}
        section = config.get('bmz') or {} if args.player == 'bmz' else config
        database = args.db or section.get('scoreDatabase' if args.player == 'bmz' else 'database')
        directory = args.directory or section.get('backupDirectory')
        if not isinstance(database, str) or not database.strip(): raise ValueError('スコアDBを指定してください。')
        if not isinstance(directory, str) or not directory.strip(): raise ValueError('バックアップ先を指定してください。')
        destination = backup_database(database, directory, force=args.force, player=args.player)
        print(f'{args.player.upper()} バックアップ完了: {destination}' if destination else f'{args.player.upper()}: DBに変更がないため、バックアップ保存を省略しました。')
    except Exception as error:
        parser.exit(1, f'バックアップに失敗しました: {error}\n')

if __name__ == '__main__': main()
