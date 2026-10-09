param([switch]$Push, [switch]$BackupOnly)
$ErrorActionPreference = 'Stop'
Push-Location -LiteralPath $PSScriptRoot
try {
    $configPath = Join-Path $PSScriptRoot 'config.local.json'
    if (-not (Test-Path -LiteralPath $configPath)) { throw 'config.example.jsonをconfig.local.jsonにコピーし、DBのパスを設定してください。' }
    if ($BackupOnly -and $Push) { throw 'BackupOnlyとPushは同時に指定できません。' }
    $localConfig = Get-Content -LiteralPath $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($localConfig.backupDirectory) {
        python -X utf8 (Join-Path $PSScriptRoot 'backup_scores.py') --config $configPath
        if ($LASTEXITCODE -ne 0) { throw 'バックアップに失敗したため、更新を中止します。' }
    } elseif ($BackupOnly) {
        throw 'config.local.jsonにbackupDirectoryを設定してください。'
    } else {
        Write-Host 'バックアップ先が未設定のため、閲覧用データのみ更新します。'
    }
    if ($BackupOnly) { return }
    python -X utf8 (Join-Path $PSScriptRoot 'export_scores.py') --config $configPath
    if ($LASTEXITCODE -ne 0) { throw 'データ出力に失敗したため、同期しません。' }
    if ($Push) {
        git add -- data/viewer.json
        if ($LASTEXITCODE -ne 0) { throw 'git addに失敗しました。' }
        git diff --cached --quiet -- data/viewer.json
        if ($LASTEXITCODE -eq 1) {
            git commit --only -m 'Update LR2 score data' -- data/viewer.json
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
