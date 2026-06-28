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
$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) "mpal-wheel-smoke-$([System.Guid]::NewGuid())"
$tempVenvDir = Join-Path $tempRoot "venv"
$tempDataDir = Join-Path $tempRoot "data"
$venvPython = Join-Path $tempVenvDir "Scripts\python.exe"
$venvMpal = Join-Path $tempVenvDir "Scripts\mpal.exe"
$wheelPath = $null

function Invoke-CommandChecked {
    param(
        [Parameter(Mandatory = $true)]
        [string]$DisplayCommand,
        [Parameter(Mandatory = $true)]
        [string]$Executable,
        [string[]]$Arguments = @()
    )

    Write-Host ""
    Write-Host ">>> $DisplayCommand"
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $DisplayCommand"
    }
}

function Invoke-VenvMpal {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    Invoke-CommandChecked `
        -DisplayCommand ("mpal " + ($Arguments -join " ")) `
        -Executable $venvMpal `
        -Arguments $Arguments
}

try {
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    $OutputEncoding = $utf8NoBom
    [Console]::OutputEncoding = $utf8NoBom
    $env:PYTHONIOENCODING = "utf-8"
    $env:PYTHONUTF8 = "1"

    New-Item -ItemType Directory -Path $tempRoot | Out-Null
    New-Item -ItemType Directory -Path $tempDataDir | Out-Null
    $env:MPAL_DATA_DIR = $tempDataDir

    Write-Host "mpal wheel smoke test"
    Write-Host "Temp root: $tempRoot"
    Write-Host "Temp venv directory: $tempVenvDir"
    Write-Host "Temp data directory: $tempDataDir"
    Write-Host "MPAL_DATA_DIR=$env:MPAL_DATA_DIR"
    Write-Host "Python output encoding forced to UTF-8 for this process."

    Invoke-CommandChecked `
        -DisplayCommand "python -m build" `
        -Executable "python" `
        -Arguments @("-m", "build")

    $wheels = @(Get-ChildItem -Path "dist" -Filter "mpal_cli-*.whl" | Sort-Object LastWriteTime -Descending)
    if ($wheels.Count -eq 0) {
        throw "No mpal_cli wheel found under dist."
    }
    $wheelPath = $wheels[0].FullName
    Write-Host "Wheel under test: $wheelPath"

    Invoke-CommandChecked `
        -DisplayCommand "python -m venv $tempVenvDir" `
        -Executable "python" `
        -Arguments @("-m", "venv", $tempVenvDir)

    Invoke-CommandChecked `
        -DisplayCommand "$venvPython -m pip install $wheelPath" `
        -Executable $venvPython `
        -Arguments @("-m", "pip", "install", $wheelPath)

    Invoke-VenvMpal -Arguments @("--version")
    Invoke-VenvMpal -Arguments @("--help")
    Invoke-VenvMpal -Arguments @("init")
    Invoke-VenvMpal -Arguments @("portfolio", "create", "etfs", "--initial", "10000")
    Invoke-VenvMpal -Arguments @("portfolio", "allocation")
    Invoke-VenvMpal -Arguments @("capital", "-p", "etfs")
    Invoke-VenvMpal -Arguments @("asset", "add", "ETHA", "-p", "etfs")
    Invoke-VenvMpal -Arguments @("asset", "buy", "ETHA", "-p", "etfs", "--price", "22.04", "--quantity", "10")
    Invoke-VenvMpal -Arguments @("asset", "list")
    Invoke-VenvMpal -Arguments @("summary", "-p", "etfs", "-a", "ETHA")
    Invoke-VenvMpal -Arguments @("summary", "-p", "etfs")
    Invoke-VenvMpal -Arguments @("summary")
    Invoke-VenvMpal -Arguments @("summary", "--explain")
    Invoke-VenvMpal -Arguments @("portfolio", "allocation")

    Write-Host ""
    Write-Host "Wheel smoke test completed successfully."
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
        Write-Host "Keeping temp root: $tempRoot"
    } elseif (Test-Path -LiteralPath $tempRoot) {
        Remove-Item -Recurse -Force -LiteralPath $tempRoot
        Write-Host "Removed temp root: $tempRoot"
    }
}
