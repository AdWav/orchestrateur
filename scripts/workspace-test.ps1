param(
    [Parameter(Mandatory = $true)]
    [string] $RunId,
    [Parameter(Mandatory = $true)]
    [ValidateSet("team-tdd", "team-classic")]
    [string] $Team,
    [switch] $RunDemo
)

$ErrorActionPreference = "Stop"
$teamPath = "/workspaces/$RunId/$Team"

$pytestCmd = "cd $teamPath && pytest -q"
if ($RunDemo) {
    $pytestCmd = "cd $teamPath && python -m src.fizzbuzz"
}

Write-Host "workspace-runner: $pytestCmd" -ForegroundColor Cyan
docker compose exec workspace-runner bash -lc $pytestCmd
