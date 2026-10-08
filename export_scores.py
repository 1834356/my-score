"""Read LR2 scores and existing BMS play logs; publish only allowlisted fields."""
import argparse
import hashlib
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sqlite3
from urllib.parse import urljoin
from urllib.request import Request, urlopen

JST = timezone(timedelta(hours=9))
DEFAULT_TABLE = 'https://stellabms.xyz/sl/table.html'
MD5 = re.compile(r'^[a-f0-9]{32}$', re.I)

class TablePage(HTMLParser):
    header_url = None
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'meta' and attrs.get('name', '').lower() == 'bmstable':
            self.header_url = attrs.get('content')

def get_json(url):
    with urlopen(Request(url, headers={'User-Agent':'LR2-Personal-Score-Viewer/1.0'}), timeout=30) as r:
        return json.loads(r.read().decode('utf-8-sig'))

def get_table(url):
    if url.lower().split('?')[0].endswith('.json'):
        header_url = url
    else:
        with urlopen(Request(url, headers={'User-Agent':'LR2-Personal-Score-Viewer/1.0'}), timeout=30) as r:
            page = r.read().decode('utf-8-sig')
        parser = TablePage(); parser.feed(page)
        if not parser.header_url:
            raise ValueError('難易度表のbmstableメタタグが見つかりません。header.jsonのURLを指定してください。')
        header_url = urljoin(url, parser.header_url)
    header = get_json(header_url)
    return header, get_json(urljoin(header_url, header['data_url']))

def table_id(url):
    known = {
        DEFAULT_TABLE: 'satellite',
        'https://stellabms.xyz/st/table.html': 'stella',
        'https://bms-ir.org/new/table/16': 'favorite',
        'https://miraiscarlet.github.io/bms/table/genocide_insane/insane_bms.html': 'insane',
    }
    return known.get(url.rstrip('/'), 'table-' + hashlib.sha256(url.encode('utf-8')).hexdigest()[:12])

def compile_table(header, entries, table_url, scores):
    charts = []; seen = set(); skipped = 0
    for entry in entries:
        key = str(entry.get('md5', '')).lower()
        if not MD5.fullmatch(key):
            skipped += 1; continue
        if key in seen: raise ValueError('難易度表に重複したMD5があります。')
        seen.add(key); score = scores.get(key)
        # LR2 normal clear: 0=no play, 1=failed, 2=easy, 3=clear, 4=hard, 5=FC.
        # Separate clear_db / clear_sd / clear_ex values are not merged into normal lamps.
        lamp = int(score['clear'] or 0) if score else 0
        if not 0 <= lamp <= 5: raise ValueError('未対応のLR2ランプ値があります。')
        bp = score['minbp'] if score and (lamp > 0 or (score['playcount'] or 0) > 0) else None
        bp = int(bp) if bp is not None and bp >= 0 else None
        charts.append({'md5':key, 'title':str(entry.get('title') or key), 'level':str(entry['level']), 'lamp':lamp, 'minBp':bp})
    order = header.get('level_order')
    if order is not None and not isinstance(order, list): raise ValueError('level_orderの形式が正しくありません。')
    return {'id':table_id(table_url), 'name':str(header['name']), 'symbol':str(header['symbol']),
        'sourceUrl':table_url, 'levelOrder':[str(level) for level in order] if order is not None else [],
        'skippedMissingMd5':skipped, 'charts':charts}

def build_many(database, definitions):
    if not definitions: raise ValueError('難易度表を1つ以上指定してください。')
    urls = [definition[2] for definition in definitions]
    if len(urls) != len(set(urls)): raise ValueError('難易度表URLが重複しています。')
    source = Path(database).resolve(strict=True)
    with sqlite3.connect(source.as_uri()+'?mode=ro', uri=True, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA query_only=ON')
        conn.execute('PRAGMA trusted_schema=OFF')
        conn.execute('BEGIN')
        scores = {}
        for row in conn.execute('SELECT hash, clear, minbp, playcount FROM score'):
            key = str(row['hash']).lower()
            if MD5.fullmatch(key):
                if key in scores: raise ValueError('スコアDBに重複したMD5があります。')
                scores[key] = row
        output_tables = [compile_table(header, entries, url, scores) for header, entries, url in definitions]
        titles = {}; memberships = {}
        for table in output_tables:
            for chart in table['charts']:
                key = chart['md5']
                titles.setdefault(key, chart['title'])
                memberships.setdefault(key, []).append({'level':chart['level'], 'label':table['symbol']+chart['level']})
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        names = {r['name'] for r in tables}
        history = None
        if 'bms_lr2_play_history' in names:
            rows = conn.execute('''SELECT hash, played_at, player_playcount_delta, judge_delta, playtime_delta,
                old_clear, new_clear, old_minbp, new_minbp
                FROM bms_lr2_play_history WHERE finalized=1 ORDER BY played_at, history_id''').fetchall()
            days = {}
            for row in rows:
                stamp = datetime.fromtimestamp(int(row['played_at']), JST)
                date = stamp.date().isoformat()
                day = days.setdefault(date, {'date':date,'plays':0,'judgements':0,'seconds':0,'lampUpdates':0,'bpUpdates':0,'entries':[]})
                for field,column in [('plays','player_playcount_delta'),('judgements','judge_delta'),('seconds','playtime_delta')]:
                    value = row[column]
                    if value is None or value < 0: raise ValueError('履歴の確定済み行に欠損・負の増分があります。')
                    day[field] += int(value)
                old_lamp, new_lamp = int(row['old_clear'] or 0), int(row['new_clear'] or 0)
                lamp_updated = new_lamp > old_lamp
                old_bp, new_bp = row['old_minbp'], row['new_minbp']
                # A first play establishes a BP; it is not a reduction from an existing best.
                bp_updated = old_lamp > 0 and old_bp is not None and new_bp is not None and 0 <= new_bp < old_bp
                day['lampUpdates'] += int(lamp_updated); day['bpUpdates'] += int(bp_updated)
                key = str(row['hash']).lower()
                belonging = memberships.get(key, [])
                day['entries'].append({'time':stamp.strftime('%H:%M:%S'),'title':titles.get(key,'難易度表外の譜面'),
                    'level':belonging[0]['level'] if belonging else None,
                    'tableLabels':[member['label'] for member in belonging],
                    'judgements':int(row['judge_delta']), 'lampUpdated':lamp_updated,'bpUpdated':bp_updated})
            pending = conn.execute('SELECT COUNT(*) FROM bms_lr2_play_history WHERE finalized!=1 OR finalized IS NULL').fetchone()[0]
            history = {'scope':'全譜面の確定済みログ（登録した難易度表以外も含む）','timezone':'Asia/Tokyo',
                'source':'BeMusicSeeker LR2 play history','excludedUnfinalized':pending,'days':sorted(days.values(),key=lambda d:d['date'],reverse=True)}
    return {'schemaVersion':1,'demo':False,'generatedAt':datetime.now(JST).isoformat(timespec='seconds'),
        'tables':output_tables,'history':history}

def build(database, header, entries, table_url=DEFAULT_TABLE):
    return build_many(database, [(header, entries, table_url)])

def write_atomic(destination, payload):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix+'.tmp')
    temporary.write_text(json.dumps(payload,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    temporary.replace(destination)

def main():
    parser = argparse.ArgumentParser(description='LR2のスコアと既存のプレイログを読み取り専用でJSONに出力します。')
    parser.add_argument('--db',help='LR2スコアDB。--configの設定より優先します。')
    parser.add_argument('--config',help='databaseとtableUrlsを指定したローカル設定ファイル')
    parser.add_argument('--table-url',action='append',help='難易度表のURL。複数回指定できます。')
    parser.add_argument('--output',default=str(Path(__file__).parent/'data'/'viewer.json'))
    parser.add_argument('--header-file',help='保存済み難易度表ヘッダ（オフライン確認用）')
    parser.add_argument('--data-file',help='保存済み難易度表データ（オフライン確認用）')
    args = parser.parse_args()
    try:
        config = json.loads(Path(args.config).read_text(encoding='utf-8-sig')) if args.config else {}
        database = args.db or config.get('database')
        if not database: raise ValueError('--dbまたは設定ファイルのdatabaseを指定してください。')
        configured_urls = config.get('tableUrls')
        if configured_urls is None:
            configured_urls = [config.get('tableUrl') or DEFAULT_TABLE]
        urls = args.table_url or configured_urls
        if not isinstance(urls, list) or not urls or any(not isinstance(url, str) or not url for url in urls):
            raise ValueError('tableUrlsは空でないURLの配列にしてください。')
        if len(urls) != len(set(urls)): raise ValueError('難易度表URLが重複しています。')
        if bool(args.header_file) != bool(args.data_file): raise ValueError('header-fileとdata-fileは両方指定してください。')
        if args.header_file:
            if len(urls) != 1: raise ValueError('オフラインのheader-file/data-fileは1表だけに対応します。')
            header=json.loads(Path(args.header_file).read_text(encoding='utf-8-sig'))
            entries=json.loads(Path(args.data_file).read_text(encoding='utf-8-sig'))
            definitions = [(header, entries, urls[0])]
        else:
            definitions = [(*get_table(url), url) for url in urls]
        payload=build_many(database,definitions)
        write_atomic(args.output,payload)
        for table in payload['tables']:
            charts=table['charts']
            print(f"{table['name']}: {len(charts)}譜面 / ランプ記録あり {sum(c['lamp']>0 for c in charts)}譜面")
        print(f"出力完了: {len(payload['tables'])}表 / 履歴 {sum(len(d['entries']) for d in (payload['history'] or {}).get('days',[]))}件")
    except Exception as error:
        parser.exit(1,f'出力に失敗しました: {error}\n')

if __name__=='__main__':main()
