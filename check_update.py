"""Validate selected local databases without writing or fetching difficulty tables."""
import argparse
import json
from pathlib import Path
import sqlite3

from export_bmz import LN_SETTINGS, RULES, read_database


def check_config(config, lr2, bmz, backup_only=False):
    if lr2:
        with read_database(config['database']) as db:
            db.execute('SELECT hash, clear, minbp, playcount, perfect, great, totalnotes FROM score LIMIT 0')
        if not backup_only and config.get('songDatabase'):
            with read_database(config['songDatabase']) as db:
                db.execute('SELECT name FROM sqlite_master LIMIT 1').fetchone()
        print('LR2: スコアDBを確認しました。')
    if bmz:
        section = config['bmz']
        if not isinstance(section, dict):
            raise ValueError('bmzは設定項目を持つオブジェクトにしてください。')
        with read_database(section['scoreDatabase']) as db:
            db.execute('SELECT id FROM score_history LIMIT 0')
            if not backup_only:
                rule = section.get('ruleMode', 'Beatoraja')
                ln = section.get('lnSetting', 'AutoLn')
                if rule not in RULES or ln not in LN_SETTINGS:
                    raise ValueError('bmz.ruleModeまたはbmz.lnSettingが無効です。')
                count = db.execute("SELECT COUNT(*) FROM score_best WHERE rule_mode=? AND double_option='Off'",
                                   (rule,)).fetchone()[0]
            else:
                db.execute('SELECT chart_sha256 FROM score_best LIMIT 0')
        if not backup_only:
            with read_database(section['libraryDatabase']) as db:
                db.execute('SELECT sha256, md5, has_undefined_ln, has_defined_ln, has_defined_cn, has_defined_hcn FROM charts LIMIT 0')
            print(f'BMZ: スコアDB・曲情報DBを確認しました。設定: {rule} / {ln}')
            if not count:
                print('注意: この判定ルールに通常プレイのベストがありません。使っているプロファイルと判定ルールを確認してください。')
        else:
            print('BMZ: スコアDBを確認しました。')
    destinations = [config.get('backupDirectory') if lr2 else None,
                    config['bmz'].get('backupDirectory') if bmz else None]
    for directory in filter(None, destinations):
        path = Path(directory)
        if path.exists() and not path.is_dir():
            raise ValueError('バックアップ先はフォルダを指定してください。')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--lr2', action='store_true')
    parser.add_argument('--bmz', action='store_true')
    parser.add_argument('--backup-only', action='store_true')
    args = parser.parse_args()
    try:
        config = json.loads(args.config.read_text(encoding='utf-8-sig'))
        check_config(config, args.lr2, args.bmz, args.backup_only)
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error) as error:
        parser.exit(1, f'設定の確認に失敗しました: {error}\n')


if __name__ == '__main__':
    main()
