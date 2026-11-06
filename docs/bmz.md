# BMZ-playerの設定

My Scoreの上部で「LR2」と「BMZ」を切り替えます。BMZは `?player=bmz` でも直接開けます。

`config.local.json` に次の `bmz` 項目を追加してください。パスはBMZの実際のプロファイルに合わせます。

```json
"bmz": {
  "scoreDatabase": "D:/your-bmz/data/profiles/default/score.db",
  "libraryDatabase": "D:/your-bmz/data/library.db",
  "backupDirectory": "D:/BMSbackup/bmz",
  "ruleMode": "Lr2Oraja",
  "lnSetting": "ForceLn"
}
```

`ruleMode` は `Beatoraja`、`Lr2Oraja`、`Dx`、`lnSetting` は `AutoLn`、`AutoCn`、`AutoHcn`、`ForceLn`、`ForceCn`、`ForceHcn` が使えます。BATTLE用の記録は集計しません。

通常は `update-and-backup.cmd` で設定したバックアップを保存し、両方の公開データを更新します。`.\update.ps1 -CheckOnly -Push` はDB・ブランチ・送信先の確認だけを行います。BMZだけ更新する場合は `.\update.ps1 -BmzOnly -Push`、BMZのバックアップだけ取る場合は `.\update.ps1 -BmzOnly -BackupOnly` を実行してください。

難易度表のベストにはBMZに取り込んだスコアも反映します。日別・月別は選択した設定で履歴が保存されたBMZの単曲プレイを集計します。IRと紐づく履歴は、このPCから取り込み前に送信した証拠がある場合だけ含めます。既定ではスコアDBと同じフォルダの `network.db` を読み、別の場所なら `bmz.networkDatabase` を設定します。日ごとの演奏時間はBMZの履歴から取得できません。

日別記録の「日付リンクをコピー」で、選択したプレイヤーと日付を開くURLを取得できます。1画面表示の「リンクをコピー」では、全更新／ランプ更新のみも指定できます。

元DBは読み取り専用で開きます。GitHubに公開するのは閲覧用JSONで、DB、設定、リプレイ、認証情報は含めません。
