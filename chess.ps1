# Load it from your PowerShell profile:  . "<path to repo>\chess.ps1"

$script:ChessDigestDir = $PSScriptRoot

function Invoke-ChessDigest {
    docker compose -f (Join-Path $script:ChessDigestDir 'docker-compose.yml') run --rm digest @args | Out-Host
    return $LASTEXITCODE -eq 0
}

function Get-LatestDigest([datetime]$After = [datetime]::MinValue) {
    Get-ChildItem (Join-Path $script:ChessDigestDir 'out') -Filter 'digest-*.html' -ErrorAction SilentlyContinue |
        Where-Object LastWriteTime -ge $After | Sort-Object LastWriteTime | Select-Object -Last 1
}

# The published site lives on the gh-pages branch, checked out as a worktree in .site/.
# Reports never touch main, so clones and forks of the code don't carry them.
function Initialize-ChessSite {
    $repo = $script:ChessDigestDir
    $site = Join-Path $repo '.site'
    if (Test-Path (Join-Path $site '.git')) {
        git -C $site pull -q --rebase 2>&1 | Out-Null
        return $true
    }
    # docker compose creates an empty .site on runs without a worktree; git refuses a non-empty one.
    if ((Test-Path $site) -and -not (Get-ChildItem $site -Force)) { Remove-Item $site }
    if (Test-Path $site) {
        Write-Host '.site exists but is not a gh-pages checkout. Move it away and try again.'
        return $false
    }
    git -C $repo fetch -q origin gh-pages 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        git -C $repo worktree add -q --track -B gh-pages $site origin/gh-pages | Out-Host
    } else {
        Write-Host 'No gh-pages branch yet, creating one.'
        git -C $repo worktree add -q --orphan -b gh-pages $site | Out-Host
    }
    return $LASTEXITCODE -eq 0
}

function Push-ChessDigests {
    $site = Join-Path $script:ChessDigestDir '.site'
    Copy-Item (Join-Path $script:ChessDigestDir 'site\index.html') (Join-Path $site 'index.html')
    $noJekyll = Join-Path $site '.nojekyll'
    if (-not (Test-Path $noJekyll)) { New-Item -ItemType File $noJekyll | Out-Null }
    git -C $site add -A
    git -C $site diff --cached --quiet
    if ($LASTEXITCODE -eq 0) {
        Write-Host 'Nothing new to publish.'
        return
    }
    git -C $site commit -q -m "docs(digests): publish digest $(Get-Date -Format yyyy-MM-dd)"
    if ($LASTEXITCODE -eq 0) { git -C $site push -u origin gh-pages }
}

function chess {
    $cmd, $rest = $args

    switch -Regex ($cmd) {
        '^(analyse|analyze|a)$' {
            $pass = [System.Collections.Generic.List[string]]::new()
            $open = $true
            $publish = $false
            for ($i = 0; $i -lt $rest.Count; $i++) {
                $t = [string]$rest[$i]
                switch -Regex ($t) {
                    '^(-g|--games)$'       { $pass.Add('--games'); $pass.Add([string]$rest[++$i]) }
                    '^(-w|--week)$'        { $pass.Add('--since-days'); $pass.Add('7') }
                    '^(-m|--month)$'       { $pass.Add('--since-days'); $pass.Add('30') }
                    '^(-d|--days)$'        { $pass.Add('--since-days'); $pass.Add([string]$rest[++$i]) }
                    '^(-u|--user)$'        { $pass.Add('--user'); $pass.Add([string]$rest[++$i]) }
                    '^(-t|--time-class)$'  { $pass.Add('--time-class'); $pass.Add([string]$rest[++$i]) }
                    '^(-a|--all)$'         { $pass.Add('--all') }
                    '^(-p|--publish)$'     { $pass.Add('--publish'); $publish = $true }
                    '^--no-open$'          { $open = $false }
                    default                { $pass.Add($t) }
                }
            }
            if ($publish -and -not (Initialize-ChessSite)) { return }
            $started = Get-Date
            if (-not (Invoke-ChessDigest @pass)) { return }
            $latest = Get-LatestDigest $started
            if ($open -and $latest) { Start-Process $latest.FullName }
            if ($publish -and $latest) { Push-ChessDigests }
        }
        '^publish$' {
            if ((Initialize-ChessSite) -and (Invoke-ChessDigest '--publish-last')) { Push-ChessDigests }
        }
        '^open$' {
            $latest = Get-LatestDigest
            if ($latest) { Start-Process $latest.FullName } else { Write-Host 'No digest yet. Run: chess analyse' }
        }
        '^build$' { docker compose -f (Join-Path $script:ChessDigestDir 'docker-compose.yml') build }
        default {
            Write-Host @'
Usage:
  chess analyse [-g N] [--week | --month | -d DAYS] [-t blitz] [-u USER] [--all] [--publish]
                [--no-ai] [--no-open] [--depth N]
  chess publish   publish the last analysis to the gh-pages branch (no new analysis, no AI cost)
  chess open      open the latest local digest
  chess build     rebuild the Docker image after code changes

Games covered by an earlier digest are skipped; --all includes them again.

Examples:
  chess analyse -g 10
  chess analyse --week --publish
  chess analyse --month -t rapid
'@
        }
    }
}
