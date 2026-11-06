# BMZ-playerの設定

My Scoreの上部で「LR2」と「BMZ」を切り替えます。BMZは `?player=bmz` でも直接開けます。

`config.local.json` に次の `bmz` 項目を追加してください。パスはBMZの実際のプロファイルに合わせます。

```json
"bmz": {
  "scoreDatabase": "D:/your-bmz/data/profiles/default/score.db",
  "libraryDatabase": "D:/your-bmz/data/library.db",
  "ruleMode": "Lr2Oraja",
  "lnSetting": "ForceLn"
}
```

`ruleMode` は `Beatoraja`、`Lr2Oraja`、`Dx`、`lnSetting` は `AutoLn`、`AutoCn`、`AutoHcn`、`ForceLn`、`ForceCn`、`ForceHcn` が使えます。BATTLE用の記録は集計しません。

通常は `update-and-backup.cmd` で従来どおりLR2をバックアップし、両方の公開データを更新します。BMZだけ更新する場合は、難易度表の取得を省いて保存済みの表を使う `powershell -NoProfile -File .\update.ps1 -BmzOnly -Push` を実行してください。

難易度表のベストにはBMZに取り込んだスコアも反映します。日別・月別は選択した設定で履歴が保存されたBMZの単曲プレイだけを集計します。他のプレイヤーから取り込んだ履歴、IR取り込み元と紐づく履歴、オートプレイ、コースは除きます。日別・月別の演奏時間はBMZの履歴から取得できません。

元DBは読み取り専用で開きます。GitHubに公開するのは閲覧用JSONで、DB、設定、リプレイ、認証情報は含めません。
