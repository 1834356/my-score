"""Inspect column names only; never print score rows, settings or credentials."""
import argparse
import json
import sqlite3
from pathlib import Path


def inspect(path):
    source = Path(path).resolve(strict=True)
    # Read-only connection: a wrong path must not create a new database.
    with sqlite3.connect(source.as_uri() + '?mode=ro', uri=True, timeout=5) as connection:
        connection.execute('PRAGMA query_only=ON')
        connection.execute('PRAGMA trusted_schema=OFF')
        tables = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
        result = []
        for (name,) in tables:
            quoted = '"' + name.replace('"', '""') + '"'
            # Defaults may contain secrets; report only names and SQLite types.
            columns = connection.execute(f'PRAGMA table_info({quoted})').fetchall()
            result.append({'table': name, 'columns': [
                {'name': column[1], 'type': column[2]} for column in columns
            ]})
    return {'tables': result}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='LR2 DBのテーブル名と列名だけを読み取ります。')
    parser.add_argument('database', help='LR2で使用しているスコアDBのパス')
    args = parser.parse_args()
    try:
        print(json.dumps(inspect(args.database), ensure_ascii=False, indent=2))
    except (OSError, sqlite3.Error) as error:
        parser.exit(1, f'読み込みに失敗しました: {error}\n')
