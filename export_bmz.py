"""Export one BMZ rule and LN setting for the existing My Score viewer."""
import argparse
from contextlib import closing, contextmanager
from datetime import datetime
import json
from pathlib import Path
import sqlite3

from export_scores import JST, MD5, write_atomic

LAMPS = {name: rank for rank, name in enumerate((
    'NoPlay', 'Failed', 'AssistEasy', 'LightAssistEasy', 'Easy', 'Normal',
    'Hard', 'ExHard', 'FullCombo', 'Perfect', 'Max',
))}
RULES = ('Beatoraja', 'Lr2Oraja', 'Dx')
LN_SETTINGS = ('AutoLn', 'AutoCn', 'AutoHcn', 'ForceLn', 'ForceCn', 'ForceHcn')
JUDGES = ('pgreat', 'great', 'good', 'bad', 'poor', 'empty_poor')


@contextmanager
def read_database(path):
    uri = Path(path).resolve(strict=True).as_uri() + '?mode=ro'
    with closing(sqlite3.connect(uri, uri=True, timeout=10)) as db:
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA query_only=ON')
        db.execute('PRAGMA trusted_schema=OFF')
        db.execute('BEGIN')
        yield db


def ln_policy(setting, chart):
    # BMZ shares the same score key across settings that resolve to the same LN mode.
    undefined = bool(chart['has_undefined_ln'])
    defined = [mode for mode, column in (
        ('Ln', 'has_defined_ln'), ('Cn', 'has_defined_cn'), ('Hcn', 'has_defined_hcn')
    ) if chart[column]]
    if not undefined and not defined:
        return 'ForceLn'
    if setting.startswith('Force'):
        return setting
    if not defined:
        return 'Force' + setting[4:]
    if not undefined:
        return 'Force' + defined[0] if len(defined) == 1 else 'AutoLn'
    return setting


def load_charts(db, hashes):
    charts = {}
    hashes = sorted(hashes)
    for offset in range(0, len(hashes), 500):
        batch = hashes[offset:offset+500]
        marks = ','.join('?' for _ in batch)
        for row in db.execute(f'''
            SELECT sha256, md5, title, subtitle,
                   has_undefined_ln, has_defined_ln, has_defined_cn, has_defined_hcn
            FROM charts WHERE sha256 IN ({marks}) ORDER BY id
        ''', batch):
            charts.setdefault(row['sha256'], row)
    return charts


def positive(value):
    return value if value is not None and value > 0 else None


def nonnegative(value):
    return value if value is not None and value >= 0 else None


def make_history(rows, charts, memberships, setting):
    days = {}
    for row in rows:
        sha = row['chart_sha256']
        chart = charts.get(sha)
        if row['ln_policy'] != (ln_policy(setting, chart) if chart else setting):
            continue
        stamp = datetime.fromtimestamp(row['played_at'], JST)
        date = stamp.date().isoformat()
        day = days.setdefault(date, {
            'date': date, 'plays': 0, 'judgements': 0, 'notes': 0,
            'notesMissingPlays': 0, 'seconds': None,
            'lampUpdates': 0, 'bpUpdates': 0, 'scoreUpdates': 0, 'entries': [],
        })
        old_lamp = LAMPS[row['old_clear_type'] or 'NoPlay']
        new_lamp = max(old_lamp, LAMPS[row['clear_type']])
        old_bp, old_ex = nonnegative(row['old_bp']), nonnegative(row['old_ex_score'])
        # A clear-only row has no numerical best; its zeroes are placeholders.
        if old_lamp in (0, 2, 3) and old_bp == old_ex == 0:
            old_bp = old_ex = None
        bp, ex = row['bp'], row['ex_score']
        new_bp = min(bp, old_bp) if old_bp is not None else bp
        new_ex = max(ex, old_ex) if old_ex is not None else ex
        notes = positive(row['total_notes'])
        judgements = sum(row[f'{side}_{judge}'] for judge in JUDGES for side in ('fast', 'slow'))
        md5 = (chart['md5'] or '').lower() if chart else ''
        md5 = md5 if MD5.fullmatch(md5) else None
        title = ' '.join((chart[k] or '').strip() for k in ('title', 'subtitle')).strip() if chart else ''
        level, labels = memberships.get(md5, (None, []))
        lamp_updated = new_lamp > old_lamp
        bp_updated = old_bp is not None and new_bp < old_bp
        score_updated = old_ex is not None and new_ex > old_ex
        day['plays'] += 1
        day['notes'] += notes or 0
        day['notesMissingPlays'] += notes is None
        day['judgements'] += judgements
        day['lampUpdates'] += lamp_updated
        day['bpUpdates'] += bp_updated
        day['scoreUpdates'] += score_updated
        day['entries'].append({
            'chartId': sha[:32], 'md5': md5, 'title': title or '曲名未取得の譜面',
            'level': level, 'tableLabels': labels, 'time': stamp.strftime('%H:%M:%S'),
            'plays': 1, 'totalNotes': notes, 'notes': notes, 'judgements': judgements,
            'oldLamp': old_lamp, 'newLamp': new_lamp, 'oldMinBp': old_bp, 'newMinBp': new_bp,
            'oldExScore': old_ex, 'newExScore': new_ex, 'oldTotalNotes': notes if old_ex is not None else None,
            'lampUpdated': lamp_updated, 'bpUpdated': bp_updated, 'scoreUpdated': score_updated,
        })
    return {
        'scope': '選択した判定・LN設定のBMZプレイ（取り込み・コースを除外）',
        'timezone': 'Asia/Tokyo', 'detailsVersion': 2, 'excludedUnfinalized': 0,
        'durationAvailable': False, 'days': sorted(days.values(), key=lambda d: d['date'], reverse=True),
    }


def local_ir_history(config, scores, linked_rows):
    """Return locally submitted history IDs, without publishing any IR metadata."""
    if not linked_rows:
        return set()
    path = config.get('networkDatabase') or Path(config['scoreDatabase']).with_name('network.db')
    if not Path(path).is_file():
        return set()
    linked = {row['id']: row['chart_sha256'] for row in linked_rows}
    confirmed = set()
    with read_database(path) as network:
        tables = {r['name'] for r in network.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not tables.intersection(('ir_score_success_ledger', 'ir_score_jobs')):
            return confirmed
        for link in scores.execute("""SELECT score_history_id, provider, account_id, remote_score_id, imported_at
                                      FROM score_history_sources WHERE source='bmz_ir'"""):
            ident = link['score_history_id']
            if ident not in linked or ident in confirmed:
                continue
            # A matching successful submission identifies the same remote score.
            if 'ir_score_success_ledger' in tables and link['remote_score_id'] and network.execute("""
                SELECT 1 FROM ir_score_success_ledger
                WHERE kind='score' AND local_score_id=? AND provider=? AND account_id=?
                      AND remote_score_id=? AND submitted_at<=? LIMIT 1
            """, (ident, link['provider'], link['account_id'], link['remote_score_id'], link['imported_at'])).fetchone():
                confirmed.add(ident)
                continue
            # A job for this history already existed before the IR download.
            # This also covers a local submission with a lost response.
            if 'ir_score_jobs' in tables and network.execute("""
                SELECT 1 FROM ir_score_jobs
                WHERE kind='score' AND local_score_id=? AND provider=? AND account_id=?
                      AND chart_sha256=? AND created_at<? LIMIT 1
            """, (ident, link['provider'], link['account_id'], linked[ident], link['imported_at'])).fetchone():
                confirmed.add(ident)
    return confirmed


def build_bmz(config, table_data):
    rule = config.get('ruleMode', 'Beatoraja')
    setting = config.get('lnSetting', 'AutoLn')
    if rule not in RULES or setting not in LN_SETTINGS:
        raise ValueError('bmz.ruleModeまたはbmz.lnSettingの設定を確認してください。')
    table_sources = table_data['tables']
    if not table_sources:
        raise ValueError('先に難易度表データを出力してください。')
    with read_database(config['scoreDatabase']) as db:
        bests = db.execute('''
            SELECT b.chart_sha256, b.ln_policy, b.clear_type, b.ex_score, b.bp, h.total_notes
            FROM score_best b LEFT JOIN score_history h ON h.id = b.best_score_history_id
            WHERE b.rule_mode = ? AND b.double_option = 'Off'
        ''', (rule,)).fetchall()
        judges = ','.join(f'h.{side}_{judge}' for judge in JUDGES for side in ('fast', 'slow'))
        history_rows = db.execute(f'''
            SELECT h.id, h.chart_sha256, h.ln_policy, h.played_at, h.clear_type, h.bp, h.ex_score,
                   h.total_notes, h.old_clear_type, h.old_bp, h.old_ex_score, {judges},
                   EXISTS (SELECT 1 FROM score_history_sources s WHERE s.score_history_id=h.id) AS ir_linked
            FROM score_history h
            WHERE h.rule_mode = ? AND h.double_option = 'Off' AND h.autoplay = 0
                AND h.source_kind = 'Local' AND h.course_score_id IS NULL
            ORDER BY h.played_at, h.id
        ''', (rule,)).fetchall()
        confirmed = local_ir_history(config, db, [r for r in history_rows if r['ir_linked']])
        history_rows = [r for r in history_rows if not r['ir_linked'] or r['id'] in confirmed]
    with read_database(config['libraryDatabase']) as db:
        charts = load_charts(db, {r['chart_sha256'] for rows in (bests, history_rows) for r in rows})

    scores = {}
    for row in bests:
        chart = charts.get(row['chart_sha256'])
        if chart is None or row['ln_policy'] != ln_policy(setting, chart):
            continue
        md5 = (chart['md5'] or '').lower()
        if not MD5.fullmatch(md5):
            continue
        notes = positive(row['total_notes'])
        scores[md5] = {
            'lamp': LAMPS[row['clear_type']], 'minBp': nonnegative(row['bp']) if notes else None,
            'exScore': nonnegative(row['ex_score']) if notes else None, 'totalNotes': notes,
        }

    blank = {'lamp': 0, 'minBp': None, 'exScore': None, 'totalNotes': None}
    memberships = {}
    tables = []
    for source in table_sources:
        entries = []
        for chart in source['charts']:
            md5, level = chart['md5'].lower(), chart['level']
            entries.append({'md5': md5, 'level': level, 'title': chart['title'], **scores.get(md5, blank)})
            memberships.setdefault(md5, (level, []))[1].append(source['symbol'] + level)
        tables.append({k: source[k] for k in ('id', 'name', 'symbol', 'sourceUrl', 'levelOrder', 'skippedMissingMd5') if k in source} | {'charts': entries})
    return {
        'schemaVersion': 1, 'player': 'bmz', 'demo': False,
        'ruleMode': rule, 'lnSetting': setting,
        'generatedAt': datetime.now(JST).isoformat(timespec='seconds'),
        'tables': tables, 'history': make_history(history_rows, charts, memberships, setting),
    }


def configured_modes(config):
    additional = config.get('additionalModes', [])
    if not isinstance(additional, list):
        raise ValueError('bmz.additionalModesは配列にしてください。')
    default = {
        'ruleMode': config.get('ruleMode', 'Beatoraja'),
        'lnSetting': config.get('lnSetting', 'AutoLn'),
    }
    modes = []
    seen = set()
    for mode in [default, *additional]:
        if (not isinstance(mode, dict) or mode.get('ruleMode') not in RULES
                or mode.get('lnSetting') not in LN_SETTINGS):
            raise ValueError('bmz.ruleModeとbmz.lnSettingを有効な組み合わせで指定してください。')
        rule, setting = mode['ruleMode'], mode['lnSetting']
        mode_id = f'{rule}-{setting}'
        if mode_id in seen:
            raise ValueError(f'BMZの表示設定が重複しています: {mode_id}')
        seen.add(mode_id)
        modes.append({'id': mode_id, 'ruleMode': rule, 'lnSetting': setting})
    return modes


def export_modes(config, table_data, output):
    modes = configured_modes(config)
    mode_dir = output.with_name(output.stem + '-modes')
    index = output.with_name(output.stem + '-index.json')
    if mode_dir.is_symlink():
        raise ValueError('BMZの追加モードの出力先にシンボリックリンクは使えません。')

    datasets = [build_bmz(config | mode, table_data) for mode in modes]
    extra_files = {mode['id'] + '.json' for mode in modes[1:]}
    for position, (mode, payload) in enumerate(zip(modes, datasets)):
        target = mode_dir / (mode['id'] + '.json') if position else output
        changed = write_atomic(target, payload)
        recorded = sum(c['lamp'] > 0 for t in payload['tables'] for c in t['charts'])
        plays = sum(d['plays'] for d in payload['history']['days'])
        status = f'ランプ記録あり {recorded}譜面（表の重複含む） / 保存済みプレイ {plays}件' if changed else '変更なし'
        print(f'BMZ {mode["id"]}: {len(payload["tables"])}表 / {status}')

    write_atomic(index, {'schemaVersion': 1, 'defaultMode': modes[0]['id'], 'modes': modes})
    known_files = {f'{rule}-{ln}.json' for rule in RULES for ln in LN_SETTINGS}
    for filename in known_files - extra_files:
        stale = mode_dir / filename
        if stale.is_file() or stale.is_symlink():
            stale.unlink()


def main():
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description='BMZのDBを読み取り専用で閲覧用JSONに出力します。')
    parser.add_argument('--config', required=True)
    parser.add_argument('--tables', type=Path, default=root/'data/viewer.json')
    parser.add_argument('--output', type=Path, default=root/'data/bmz.json')
    args = parser.parse_args()
    try:
        config = json.loads(Path(args.config).read_text(encoding='utf-8-sig'))['bmz']
        tables = json.loads(args.tables.read_text(encoding='utf-8-sig'))
        export_modes(config, tables, args.output)
    except (OSError, sqlite3.Error, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f'BMZの出力に失敗しました: {error}\n')


if __name__ == '__main__':
    main()
