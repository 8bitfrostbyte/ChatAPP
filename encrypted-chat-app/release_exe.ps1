param(
    [Parameter(Mandatory = $true)]
    [string]$Tag,

    [string]$Title = "",
    [string]$Notes = "Automated release build",
    [string]$Repo = "",
    [string]$PythonPath = "c:/Users/Nico-/Desktop/New folder/.venv/Scripts/python.exe"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Invoke-Step {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][scriptblock]$Action
    )
    Write-Host "[step] $Name"
    & $Action
}

if ([string]::IsNullOrWhiteSpace($Title)) {
    $Title = "Encrypted Chat $Tag"
}

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$clientDir = Join-Path $root "client"
$specPath = Join-Path $clientDir "EncryptedChat.spec"
$mainPy = Join-Path $clientDir "main.py"
$versionFile = Join-Path $clientDir "version.txt"
$distExe = Join-Path $clientDir "dist\EncryptedChat.exe"

if (-not (Test-Path $specPath)) {
    throw "Spec file not found: $specPath"
}
if (-not (Test-Path $mainPy)) {
    throw "Client main.py not found: $mainPy"
}

$releaseVersion = $Tag
if ($releaseVersion.StartsWith("version_")) {
    $releaseVersion = $releaseVersion.Substring(8)
}
elseif ($releaseVersion.StartsWith("v")) {
    $releaseVersion = $releaseVersion.Substring(1)
}

Invoke-Step -Name "Validate tooling" -Action {
    if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
        throw "GitHub CLI (gh) is not installed or not in PATH"
    }
    if (-not (Test-Path $PythonPath)) {
        throw "Python executable not found: $PythonPath"
    }
}

Invoke-Step -Name "Check GitHub auth" -Action {
    gh auth status | Out-Null
}

Invoke-Step -Name "Build EncryptedChat.exe" -Action {
    Set-Content -Path $versionFile -Value $releaseVersion -Encoding UTF8

    $mainContent = Get-Content -Path $mainPy -Raw -Encoding UTF8
    $updatedMain = [regex]::Replace($mainContent, 'CLIENT_VERSION\s*=\s*"[^"]+"', "CLIENT_VERSION = \"$releaseVersion\"")
    if ($updatedMain -eq $mainContent) {
        throw "Failed to update CLIENT_VERSION in $mainPy"
    }
    Set-Content -Path $mainPy -Value $updatedMain -Encoding UTF8

    Push-Location $clientDir
    try {
        if (Test-Path (Join-Path $clientDir "build")) {
            Remove-Item -Recurse -Force (Join-Path $clientDir "build")
        }
        & $PythonPath -m PyInstaller "EncryptedChat.spec" --noconfirm --clean
    }
    finally {
        Pop-Location
    }
}

if (-not (Test-Path $distExe)) {
    throw "Build finished but EXE not found: $distExe"
}

$ghBaseArgs = @()
if (-not [string]::IsNullOrWhiteSpace($Repo)) {
    $ghBaseArgs += @("--repo", $Repo)
}

Invoke-Step -Name "Create or update GitHub release" -Action {
    $releaseExists = $true
    try {
        gh release view $Tag @ghBaseArgs | Out-Null
    }
    catch {
        $releaseExists = $false
    }

    if ($releaseExists) {
        gh release upload $Tag $distExe --clobber @ghBaseArgs
        gh release edit $Tag --title $Title --notes $Notes @ghBaseArgs
        Write-Host "[ok] Updated existing release $Tag with latest EXE"
    }
    else {
        gh release create $Tag $distExe --title $Title --notes $Notes @ghBaseArgs
        Write-Host "[ok] Created release $Tag with EXE asset"
    }
}

Write-Host "[done] Release workflow complete"
Write-Host "       Tag: $Tag"
Write-Host "       EXE: $distExe"