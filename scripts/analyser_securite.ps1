# Analyse locale des failles (dépendances, secrets, mauvaises configs).
# Préférer le binaire Trivy s'il est installé, sinon Docker.

$ErrorActionPreference = "Stop"
$racine = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$image = "aquasec/trivy:0.70.0"

Set-Location $racine

if (Get-Command trivy -ErrorAction SilentlyContinue) {
    trivy fs . --config trivy.yaml --severity HIGH,CRITICAL --exit-code 1
    exit $LASTEXITCODE
}

if (Get-Command docker -ErrorAction SilentlyContinue) {
    docker run --rm -v "${racine}:/projet:ro" -w /projet $image fs . --config trivy.yaml --severity HIGH,CRITICAL --exit-code 1
    exit $LASTEXITCODE
}

Write-Error "Installe Trivy (winget install AquaSecurity.Trivy) ou Docker, puis relance ce script."
