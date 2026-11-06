param([switch]$Push, [switch]$BackupOnly, [switch]$BmzOnly, [switch]$CheckOnly)
$ErrorActionPreference = 'Stop'
Push-Location -LiteralPath $PSScriptRoot
try {
    $configPath = Join-Path $PSScriptRoot 'config.local.json'
    if (-not (Test-Path -LiteralPath $configPath)) { throw 'config.example.jsonをconfig.local.jsonにコピーし、DBのパスを設定してください。' }
    if ($BackupOnly -and $Push) { throw 'BackupOnlyとPushは同時に指定できません。' }
    $localConfig = Get-Content -LiteralPath $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $runLr2 = [bool]$localConfig.database -and -not $BmzOnly
    $runBmz = [bool]$localConfig.bmz
    if ($BmzOnly -and -not $runBmz) { throw 'config.local.jsonにbmzを設定してください。' }
    if (-not $runLr2 -and -not $runBmz) { throw 'config.local.jsonにLR2のdatabaseまたはbmzを設定してください。' }
    $backupLr2 = $runLr2 -and [bool]$localConfig.backupDirectory
    $backupBmz = $runBmz -and [bool]$localConfig.bmz.backupDirectory
    if ($BackupOnly) {
        if (-not $backupLr2 -and -not $backupBmz) { throw '選択したプレイヤーのbackupDirectoryを設定してください。' }
        $runLr2 = $backupLr2
        $runBmz = $backupBmz
    }
    if ($Push) {
        $prefix = git rev-parse --show-prefix
        if ($LASTEXITCODE -ne 0 -or $prefix) { throw 'Gitでクローンしたリポジトリのルートから更新してください。' }
        $branch = git branch --show-current
        if ($LASTEXITCODE -ne 0 -or $branch -cne 'main') { throw '公開更新はリポジトリのmainブランチで実行してください。' }
        $remote = @(git remote get-url --push --all origin)
        if ($LASTEXITCODE -ne 0 -or $remote.Count -ne 1 -or
            $remote[0] -notmatch '^(?:https://github\.com/|ssh://git@github\.com/|git@github\.com:)([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?/?$') {
            throw 'originの送信先を自分のGitHubリポジトリ1件に設定してください。'
        }
        $target = $Matches[1]
        if ($target -in @('1834356/bms-score-viewer','1834356/lr2-score-viewer')) {
            throw '配布元にはスコアを送信できません。originを自分のフォークまたはテンプレートから作ったリポジトリに変更してください。'
        }
        Write-Host "公開先: https://github.com/$target (main)"
    }
    $checkArgs = @('--config', $configPath)
    if ($runLr2) { $checkArgs += '--lr2' }
    if ($runBmz) { $checkArgs += '--bmz' }
    if ($BackupOnly) { $checkArgs += '--backup-only' }
    python -X utf8 (Join-Path $PSScriptRoot 'check_update.py') @checkArgs
    if ($LASTEXITCODE -ne 0) { throw '事前チェックに失敗したため、更新を中止します。' }
    if ($CheckOnly) { Write-Host '事前チェックが完了しました。'; return }
    foreach ($player in @('lr2', 'bmz')) {
        if (($player -eq 'lr2' -and $backupLr2) -or ($player -eq 'bmz' -and $backupBmz)) {
            python -X utf8 (Join-Path $PSScriptRoot 'backup_scores.py') --config $configPath --player $player
            if ($LASTEXITCODE -ne 0) { throw 'バックアップに失敗したため、更新を中止します。' }
        }
    }
    if ($BackupOnly) { return }
    $dataPaths = @()
    if ($runLr2) {
        python -X utf8 (Join-Path $PSScriptRoot 'export_scores.py') --config $configPath
        if ($LASTEXITCODE -ne 0) { throw 'LR2データの出力に失敗したため、同期しません。' }
        $dataPaths += 'data/viewer.json'
    }
    if ($runBmz) {
        $bmzArgs = @('--config', $configPath)
        if ($dataPaths -contains 'data/viewer.json') { $bmzArgs += @('--tables', (Join-Path $PSScriptRoot 'data/viewer.json')) }
        python -X utf8 (Join-Path $PSScriptRoot 'export_bmz.py') @bmzArgs
        if ($LASTEXITCODE -ne 0) { throw 'BMZデータの出力に失敗したため、同期しません。' }
        $dataPaths += 'data/bmz.json'
    }
    if ($Push) {
        git add -- @dataPaths
        if ($LASTEXITCODE -ne 0) { throw 'git addに失敗しました。' }
        git diff --cached --quiet -- @dataPaths
        if ($LASTEXITCODE -eq 1) {
            git commit --only -m 'Update BMS score data' -- @dataPaths
            if ($LASTEXITCODE -ne 0) { throw 'git commitに失敗しました。' }
        } elseif ($LASTEXITCODE -ne 0) { throw 'git diffに失敗しました。' }
        # Only contact GitHub when main contains commits not yet pushed.
        git rev-parse --verify --quiet refs/remotes/origin/main > $null
        if ($LASTEXITCODE -eq 0) {
            $pending = git rev-list --count refs/remotes/origin/main..main
            if ($LASTEXITCODE -ne 0) { throw '未同期コミットの確認に失敗しました。' }
            if ([int]$pending -eq 0) {
                Write-Host '同期する変更がないため、GitHubへの送信を省略しました。'
                return
            }
        }
        # Retry previously committed data too, if an earlier push failed.
        git push origin main
        if ($LASTEXITCODE -ne 0) { throw 'git pushに失敗しました。ネットワークとGitHub認証を確認してください。' }
    }
} finally { Pop-Location }
