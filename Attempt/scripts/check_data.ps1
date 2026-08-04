param(
    [string]$DatasetPath
)

if ([string]::IsNullOrWhiteSpace($DatasetPath)) {
    throw 'Provide -DatasetPath with a file or directory under the Data folder.'
}

$resolved = Resolve-Path -LiteralPath $DatasetPath -ErrorAction Stop
Write-Output "Checking: $resolved"
Get-ChildItem -LiteralPath $resolved -Recurse -File | Select-Object FullName, Length, LastWriteTime
