# Bump the date-based version in ../VERSION (YYYY.M.D.N, N = build number that day) and print it.
$file = Join-Path $PSScriptRoot "..\VERSION"
$current = if (Test-Path $file) { (Get-Content $file -Raw).Trim() } else { $null }

function Get-NextVersion([string]$current) {
    $today = Get-Date
    $todayKey = [int]$today.ToString('yyyyMMdd')
    if ($current -match '^(\d+)\.(\d+)\.(\d+)\.(\d+)$') {
        $y, $m, $d, $n = [int]$Matches[1], [int]$Matches[2], [int]$Matches[3], [int]$Matches[4]
        if ($y * 10000 + $m * 100 + $d -ge $todayKey) {      # same day (or a later date): bump N
            return "$y.$m.$d.$($n + 1)"
        }
    }
    return "$($today.Year).$($today.Month).$($today.Day).0"   # first build today (or no version yet)
}

$next = Get-NextVersion $current
[IO.File]::WriteAllText($file, "$next`n")
$next
