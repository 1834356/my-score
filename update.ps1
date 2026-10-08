param([switch]$Push)
$ErrorActionPreference = 'Stop'
Push-Location -LiteralPath $PSScriptRoot
try {
    $configPath = Join-Path $PSScriptRoot 'config.local.json'
    if (-not (Test-Path -LiteralPath $configPath)) { throw 'config.example.jsonをconfig.local.jsonにコピーし、DBのパスを設定してください。' }
    python -X utf8 (Join-Path $PSScriptRoot 'export_scores.py') --config $configPath
    if ($LASTEXITCODE -ne 0) { throw 'データ出力に失敗したため、同期しません。' }
    if ($Push) {
        git add -- data/viewer.json
        if ($LASTEXITCODE -ne 0) { throw 'git addに失敗しました。' }
        git diff --cached --quiet -- data/viewer.json
        if ($LASTEXITCODE -eq 1) {
            git commit --only -m 'Update LR2 score data' -- data/viewer.json
            if ($LASTEXITCODE -ne 0) { throw 'git commitに失敗しました。' }
            git push origin main
            if ($LASTEXITCODE -ne 0) { throw 'git pushに失敗しました。ネットワークとGitHub認証を確認してください。' }
        } elseif ($LASTEXITCODE -ne 0) { throw 'git diffに失敗しました。' }
    }
} finally { Pop-Location }
