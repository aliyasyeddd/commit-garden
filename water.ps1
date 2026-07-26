$today = Get-Date -Format "yyyy-MM-dd"
$entry = Read-Host "What did you work on today?"
Add-Content log.md "`n## $today`n$entry`n"
git add log.md
git commit -m "day log $today"