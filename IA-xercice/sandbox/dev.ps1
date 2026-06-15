param(
    [ValidateSet("api", "front", "all", "stop")]
    [string]$Mode = "all"
)

$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Join-Path $RootDir "backend"
$FrontendDir = Join-Path $RootDir "frontend"

function Start-Api {
    Write-Host "[API] Setup and start FastAPI..."
    Set-Location $BackendDir

    if (-not (Test-Path ".venv")) {
        python -m venv .venv
    }

    & ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
    & ".\.venv\Scripts\python.exe" -m uvicorn app.main:app --reload --port 8000
}

function Start-Front {
    Write-Host "[FRONT] Install and start React..."
    Set-Location $FrontendDir
    npm install
    npm run dev
}

function Stop-Api {
    $job = Get-Job -Name "guestbook-api" -ErrorAction SilentlyContinue
    if ($null -ne $job) {
        Stop-Job -Name "guestbook-api" -ErrorAction SilentlyContinue
        Remove-Job -Name "guestbook-api" -Force -ErrorAction SilentlyContinue
        Write-Host "[STOP] PowerShell job 'guestbook-api' stopped."
    }
    else {
        Write-Host "[STOP] No PowerShell job named 'guestbook-api' found."
    }

    $backendPath = [regex]::Escape((Join-Path $RootDir "backend"))
    $uvicornProcs = Get-CimInstance Win32_Process |
        Where-Object {
            $_.Name -match '^(python|python3|uvicorn)(\.exe)?$' -and
            $_.CommandLine -match 'uvicorn' -and
            $_.CommandLine -match 'app\.main:app' -and
            $_.CommandLine -match $backendPath
        }

    if ($uvicornProcs) {
        $uvicornProcs | ForEach-Object {
            Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
            Write-Host "[STOP] Killed API process PID=$($_.ProcessId)."
        }
    }
    else {
        Write-Host "[STOP] No matching API process found."
    }
}

switch ($Mode) {
    "api" {
        Start-Api
    }
    "front" {
        Start-Front
    }
    "all" {
        Write-Host "[ALL] Starting API as background job and Front here..."
        if (Get-Job -Name "guestbook-api" -ErrorAction SilentlyContinue) {
            Write-Host "[ALL] Existing guestbook-api job detected, replacing it..."
            Stop-Api
        }
        Start-Job -Name "guestbook-api" -ScriptBlock {
            param($ApiDir)
            Set-Location $ApiDir
            if (-not (Test-Path ".venv")) {
                python -m venv .venv
            }
            & ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
            & ".\.venv\Scripts\python.exe" -m uvicorn app.main:app --reload --port 8000
        } -ArgumentList $BackendDir | Out-Null
        Write-Host "[ALL] API job name: guestbook-api (Get-Job / Receive-Job -Name guestbook-api -Keep)"
        Start-Front
    }
    "stop" {
        Stop-Api
    }
}
