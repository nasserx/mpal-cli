[CmdletBinding()]
param(
    [switch]$KeepData
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$originalDataDir = $env:MPAL_DATA_DIR
$originalPythonIoEncoding = $env:PYTHONIOENCODING
$originalPythonUtf8 = $env:PYTHONUTF8
$originalOutputEncoding = $OutputEncoding
$originalConsoleOutputEncoding = [Console]::OutputEncoding
$tempDataDir = Join-Path ([System.IO.Path]::GetTempPath()) "mpal-manual-qa-$([System.Guid]::NewGuid())"

function Invoke-Mpal {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    $displayCommand = "mpal " + ($Arguments -join " ")
    Write-Host ""
    Write-Host ">>> $displayCommand"
    & mpal @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $displayCommand"
    }
}

try {
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    $OutputEncoding = $utf8NoBom
    [Console]::OutputEncoding = $utf8NoBom
    $env:PYTHONIOENCODING = "utf-8"
    $env:PYTHONUTF8 = "1"

    New-Item -ItemType Directory -Path $tempDataDir | Out-Null
    $env:MPAL_DATA_DIR = $tempDataDir

    Write-Host "mpal manual QA"
    Write-Host "Temp data directory: $tempDataDir"
    Write-Host "MPAL_DATA_DIR=$env:MPAL_DATA_DIR"
    Write-Host "Python output encoding forced to UTF-8 for this process."

    Invoke-Mpal -Arguments @("--version")
    Invoke-Mpal -Arguments @("--help")
    Invoke-Mpal -Arguments @("init")
    Invoke-Mpal -Arguments @("portfolio", "create", "etfs", "--initial", "10000")
    Invoke-Mpal -Arguments @("portfolio", "create", "stocks")
    Invoke-Mpal -Arguments @("portfolio", "list")
    Invoke-Mpal -Arguments @("summary", "-p", "etfs")
    Invoke-Mpal -Arguments @("capital", "show", "-p", "etfs")
    Invoke-Mpal -Arguments @("capital", "deposit", "2500", "-p", "etfs", "--note", "Manual QA deposit")
    Invoke-Mpal -Arguments @("capital", "withdraw", "500", "-p", "etfs", "--note", "Manual QA withdrawal")
    Invoke-Mpal -Arguments @("capital", "log", "-p", "etfs")
    Invoke-Mpal -Arguments @("capital", "entry", "edit", "1", "-p", "etfs", "--note", "Corrected initial deposit")
    Invoke-Mpal -Arguments @("capital", "entry", "delete", "2", "-p", "etfs")
    Invoke-Mpal -Arguments @("capital", "show", "-p", "etfs")
    Invoke-Mpal -Arguments @("asset", "add", "ETHA", "AAPL", "-p", "etfs")
    Invoke-Mpal -Arguments @("asset", "buy", "ETHA", "-p", "etfs", "--price", "22.04", "--quantity", "10")
    Invoke-Mpal -Arguments @("asset", "buy", "ETHA", "-p", "etfs", "--price", "22.15", "--quantity", "2", "--fee", "1.00")
    Invoke-Mpal -Arguments @("asset", "income", "ETHA", "12.34", "-p", "etfs", "--note", "Manual QA income")
    Invoke-Mpal -Arguments @("asset", "sell", "ETHA", "-p", "etfs", "--price", "23.00", "--quantity", "3", "--fee", "1.00")
    Invoke-Mpal -Arguments @("asset", "list")
    Invoke-Mpal -Arguments @("asset", "list", "-p", "etfs")
    Invoke-Mpal -Arguments @("summary", "-p", "etfs", "-a", "ETHA")
    Invoke-Mpal -Arguments @("asset", "log", "ETHA", "-p", "etfs")
    Invoke-Mpal -Arguments @("asset", "entry", "edit", "ETHA", "1", "-p", "etfs", "--note", "Corrected buy note")
    Invoke-Mpal -Arguments @("asset", "entry", "delete", "ETHA", "3", "-p", "etfs", "--yes")
    Invoke-Mpal -Arguments @("summary", "-p", "etfs", "-a", "ETHA")
    Invoke-Mpal -Arguments @("summary", "-p", "etfs")

    Write-Host ""
    Write-Host "Manual QA completed successfully."
}
finally {
    if ($null -eq $originalDataDir) {
        Remove-Item Env:\MPAL_DATA_DIR -ErrorAction SilentlyContinue
    } else {
        $env:MPAL_DATA_DIR = $originalDataDir
    }
    if ($null -eq $originalPythonIoEncoding) {
        Remove-Item Env:\PYTHONIOENCODING -ErrorAction SilentlyContinue
    } else {
        $env:PYTHONIOENCODING = $originalPythonIoEncoding
    }
    if ($null -eq $originalPythonUtf8) {
        Remove-Item Env:\PYTHONUTF8 -ErrorAction SilentlyContinue
    } else {
        $env:PYTHONUTF8 = $originalPythonUtf8
    }
    $OutputEncoding = $originalOutputEncoding
    [Console]::OutputEncoding = $originalConsoleOutputEncoding

    if ($KeepData) {
        Write-Host "Keeping temp data directory: $tempDataDir"
    } elseif (Test-Path -LiteralPath $tempDataDir) {
        Remove-Item -Recurse -Force -LiteralPath $tempDataDir
        Write-Host "Removed temp data directory: $tempDataDir"
    }
}
