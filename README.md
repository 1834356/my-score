# My Score

LR2のスコアDBを読み取り、複数の難易度表のランプ・最小BPと日々のプレイ記録をGitHub Pagesで閲覧する個人用ページです。

- Satellite: https://stellabms.xyz/sl/table.html
- Stella: https://stellabms.xyz/st/table.html
- Favorite: https://bms-ir.org/new/table/16
- 発狂BMS難易度表: https://miraiscarlet.github.io/bms/table/genocide_insane/insane_bms.html
- 閲覧ページ: https://1834356.github.io/my-score/
- ソース: https://github.com/1834356/my-score

他の方が利用する場合は、スコアデータを含まない[配布用リポジトリ](https://github.com/1834356/lr2-score-viewer)をフォークしてください。

## 表示機能

- 難易度表を切り替えて、それぞれの全譜面を表示。MD5でLR2のスコアと照合。
- レベル別のランプ集計、EASY以上・HARD以上・未プレイの譜面数。グラフを押すと、全7種のランプの譜面数・割合を開閉できます。
- 譜面一覧に最小BPとスコアレート（小数点以下2桁）を表示。曲名検索、レベル・ランプ絞り込み、BP・曲名・ランプ順のソート。
- 日付別の打鍵数（総ノーツ数）、プレイ数、演奏時間、ランプ・BP・EXスコア更新。
- 新規FC・HC・NC・EC・AAA、BP更新、スコア更新を種類別に表示。変更前後の値と差分を確認できます。ランプ更新は変更前後それぞれのランプ色で表示します。
- スマートフォンの画面幅にも対応。
- 出力日時を表示。自宅PCが停止していても、最後に同期したデータを閲覧可能。

## スコアを更新する

初回設定済みのローカルフォルダでは `config.local.json` にDBの保存場所を記載しています。このファイルはGitHubには送信しません。

1. LR2でプレイする。
2. このフォルダ内の `update-and-backup.cmd` をダブルクリックする。日時付きDBバックアップ、閲覧用JSONの更新、GitHubへの同期を順に実行します。完了後はキーを押してウィンドウを閉じられます。

PowerShellから実行する場合は、以下のコマンドです。

```powershell
.\update.ps1 -Push
```

`config.local.json` の `backupDirectory` が設定されている場合は、最初に元DBをSQLiteのバックアップ機能で保存します。書き込み中のDBにも対応し、整合性確認を通過したものだけを日時付きの `.db` として残します。既存バックアップは上書き・削除しません。バックアップに失敗すると、閲覧用JSONの更新とGitHubへの同期も中止します。

続いて公開難易度表を取得し、スコアDBを読み取り専用で開き、`data/viewer.json` を出力してGitHubへ送ります。GitHub Pagesの反映後、スマホ側のページを再読み込みしてください。自動実行は設定していません。

GitHubへ同期せず、DBバックアップとJSONの書き出しだけ実行する場合は次のコマンドです。

```powershell
.\update.ps1
```

DBバックアップだけ実行する場合は `.\update.ps1 -BackupOnly` を使えます。バックアップ先は `config.local.json` の `backupDirectory` で変更できます。保存名は `player_YYYYMMDD_HHMMSS_ffffff.db`（日本時間）です。元DBは全内容をローカルに保存し、GitHubへは閲覧用JSONだけを同期します。バックアップ先がOneDrive内なら、OneDriveの通常の同期対象になります。

## 別のPCで設定する

Python 3.10以上とGitが必要です。Gitには対象GitHubアカウントの認証を設定してください。

```powershell
git clone https://github.com/1834356/my-score.git
cd my-score
Copy-Item config.example.json config.local.json
```

`config.local.json` の `database` を使用中のLR2スコアDBのパスへ変更します。`backupDirectory` をバックアップの保存先へ変更し、`tableUrls` 配列に閲覧したい難易度表のURLを指定します。曲名用の `song.db` は、スコアDBの `Score` フォルダの1つ上から自動検出します。別の場所にある場合は `songDatabase` をローカル設定へ追加するか、`--song-db` で指定できます。曲名以外のフォルダパスなどは公開JSONに出力しません。旧設定の `tableUrl`（単一URL）も引き続き使用できます。その後 `update.ps1 -Push` を実行してください。

## データと公開範囲

ページと閲覧用JSONは公開です。元DB・プレイヤーの認証情報・ゴースト・ローカルパスは出力しません。`score` テーブルからMD5、通常ランプ、最小BP、EXスコア、総ノーツ数を取り出し、難易度表の譜面情報と結合します。別モードの `clear_db`、`clear_sd`、`clear_ex` は通常ランプに混ぜません。

UIのランプ値はLR2の通常 `clear` に合わせ、0=NO PLAY、1=FAILED、2=EASY、3=CLEAR、4=HARD、5=FC。BPの未取得は `null`、0 BPは数値の0です。スコアレートは `EXスコア ÷ (総ノーツ数 × 2) × 100` で計算し、EXスコアは `perfect × 2 + great` から取得します。未プレイ・総ノーツ数未取得は「—」、有効な0点は `0.00%` と表示します。旧JSONにスコア情報がない場合も「—」を表示します。難易度表全体の未プレイ譜面も表示します。

HTTP/HTTPSでは `data/viewer.json` を読み込みます。未配置なら明示したデモを表示し、取得・形式エラーは画面に表示します。`index.html` を直接開く場合は「閲覧用JSONを開く」で `data/viewer.json` を選択できます。

## 日別ログの範囲

既存の `bms_lr2_play_history` テーブルがある場合のみ読み込みます。DBに新しいテーブルやトリガーを追加せず、確定済み（`finalized=1`）の行を日本時間の日付で集計します。

日別集計は登録した難易度表以外も含む全譜面です。同じ譜面が複数の表にある場合でも、プレイ数やノーツ数を重複集計しません。所属レベルは `sl6 / Fav0` のように表示します。どの表にも登録されていない譜面名は、LR2の `song.db` から曲名・サブタイトルを取得します。段位・コースも名称を表示します。DBに名称が見つからない場合だけ「難易度表外の譜面」と表示します。未確定の行は除外し、その件数をページに表示します。

打鍵数は各ログの `new_totalnotes × player_playcount_delta` の合計です。途中終了やFAILEDでも譜面全体のノーツ数を加算します。実際の判定数や物理的なキー押下回数とは異なります。総ノーツ数が未取得のプレイは加算せず、除外したプレイ数を表示します。既存JSONの `judgements` は互換性のため残しますが、画面の打鍵数には使用しません。

演奏時間はログの `playtime_delta`、プレイ数は `player_playcount_delta` の合計です。ランプ更新はベストの通常ランプ上昇、BP改善は以前の最小BP減少、スコア更新は以前のEXスコア上昇です。初回BP・EXスコア記録は改善件数に含めません。集計カードは更新イベント数、種類別の一覧は同じ譜面のその日の開始前と終了時のベストをまとめて比較します。新規AAAはEXスコアが最大値（総ノーツ数 × 2）の8/9以上に達した譜面です。

公開ログには総ノーツ数、変更前後の通常ランプ・BP・EXスコア、一覧をまとめるための譜面IDを追加しています。元DBのプレイヤー情報やファイルパスは含みません。曲名は省略表示され、押すと全文を開閉できます。「全プレイ履歴」を開くと時系列でも確認できます。

ログ機能の導入前の過去プレイは復元できません。確定済みログがない日は「ログなし」と表示します。

BeMusicSeeker側の記録機能の説明:
https://neeted.github.io/bemusicseeker-unofficial-fork/manual.ja.html#lr2プレイログ

## 技術構成

フロントエンドは依存ライブラリなしのHTML/CSS/JavaScript、エクスポータはPython標準ライブラリのみです。GitHub Pagesの配信元は `main` ブランチのルートで、`.nojekyll` を配置しています。

すべての難易度表を取得してから1回のDB読み取りで出力します。レベル順は難易度表の `level_order` があれば、その定義に従います。

難易度表の取得・DB読み取りに失敗した場合は公開JSONを置き換えず、GitHubへの同期も中止します。更新スクリプトは `data/viewer.json` だけをコミットします。

## DB構造の確認

```powershell
python -X utf8 inspect_db.py 'D:\LR2\LR2files\Database\Score\your-player.db'
```

テーブル名と列名だけを表示し、スコア行や設定値は出力しません。
