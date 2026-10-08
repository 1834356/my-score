# LR2 Score Viewer

LR2のスコアDBを読み取り、Satelliteのランプ・最小BPと日々のプレイ記録をGitHub Pagesで閲覧する個人用ページです。

- 難易度表: https://stellabms.xyz/sl/table.html
- 閲覧ページ: https://1834356.github.io/lr2-score-viewer/
- ソース: https://github.com/1834356/lr2-score-viewer

## 表示機能

- Satelliteの全譜面を表示。MD5でLR2のスコアと照合。
- レベル別のランプ集計、EASY以上・HARD以上・未プレイの譜面数。
- 曲名検索、レベル・ランプ絞り込み、BP・曲名・ランプ順のソート。
- 日付別のプレイ数、判定数、演奏時間、ランプ更新・BP改善。
- スマートフォンの画面幅にも対応。
- 出力日時を表示。自宅PCが停止していても、最後に同期したデータを閲覧可能。

## スコアを更新する

初回設定済みのローカルフォルダでは `config.local.json` にDBの保存場所を記載しています。このファイルはGitHubには送信しません。

1. LR2でプレイする。
2. このフォルダでPowerShellを開き、以下を実行する。

```powershell
.\update.ps1 -Push
```

この処理は公開難易度表を取得し、スコアDBを読み取り専用で開き、`data/viewer.json` を出力してGitHubへ送ります。GitHub Pagesの反映後、スマホ側のページを再読み込みしてください。自動実行は設定していません。

JSONを書き出すだけなら次のコマンドです。

```powershell
.\update.ps1
```

## 別のPCで設定する

Python 3.10以上とGitが必要です。Gitには対象GitHubアカウントの認証を設定してください。

```powershell
git clone https://github.com/1834356/lr2-score-viewer.git
cd lr2-score-viewer
Copy-Item config.example.json config.local.json
```

`config.local.json` の `database` を使用中のLR2スコアDBのパスへ変更します。その後 `update.ps1 -Push` を実行してください。

## データと公開範囲

ページと閲覧用JSONは公開です。元DB・プレイヤーの認証情報・ゴースト・ローカルパスは出力しません。`score` テーブルからMD5、通常ランプ、最小BPだけを取り出し、難易度表の譜面情報と結合します。別モードの `clear_db`、`clear_sd`、`clear_ex` は通常ランプに混ぜません。

UIのランプ値はLR2の通常 `clear` に合わせ、0=NO PLAY、1=FAILED、2=EASY、3=CLEAR、4=HARD、5=FC。BPの未取得は `null`、0 BPは数値の0です。難易度表全体の未プレイ譜面も表示します。

HTTP/HTTPSでは `data/viewer.json` を読み込みます。未配置なら明示したデモを表示し、取得・形式エラーは画面に表示します。`index.html` を直接開く場合は「閲覧用JSONを開く」で `data/viewer.json` を選択できます。

## 日別ログの範囲

既存の `bms_lr2_play_history` テーブルがある場合のみ読み込みます。DBに新しいテーブルやトリガーを追加せず、確定済み（`finalized=1`）の行を日本時間の日付で集計します。

日別集計はSatellite以外も含む全譜面です。Satelliteに登録されていない譜面名は「難易度表外の譜面」と表示します。未確定の行は除外し、その件数をページに表示します。

判定数はPG・GR・GD・BD・PRの増分合計です。皿やLNなどのゲーム側の集計を含み、鍵盤だけの物理的なキー押下回数とは異なります。演奏時間はログの `playtime_delta`、プレイ数は `player_playcount_delta` の合計です。ランプ更新はベストの通常ランプ上昇、BP改善は以前の記録からの最小BP減少です。初回BP記録は改善件数に含めません。

ログ機能の導入前の過去プレイは復元できません。確定済みログがない日は「ログなし」と表示します。

BeMusicSeeker側の記録機能の説明:
https://neeted.github.io/bemusicseeker-unofficial-fork/manual.ja.html#lr2プレイログ

## 技術構成

フロントエンドは依存ライブラリなしのHTML/CSS/JavaScript、エクスポータはPython標準ライブラリのみです。GitHub Pagesの配信元は `main` ブランチのルートで、`.nojekyll` を配置しています。

難易度表の取得・DB読み取りに失敗した場合は公開JSONを置き換えず、GitHubへの同期も中止します。更新スクリプトは `data/viewer.json` だけをコミットします。

## DB構造の確認

```powershell
python -X utf8 inspect_db.py 'D:\LR2\LR2files\Database\Score\your-player.db'
```

テーブル名と列名だけを表示し、スコア行や設定値は出力しません。
