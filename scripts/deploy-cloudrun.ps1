param(
  [Parameter(Mandatory = $true)]
  [string]$ProjectId,

  [Parameter(Mandatory = $false)]
  [string]$Region = "us-central1",

  [Parameter(Mandatory = $false)]
  [bool]$DeployBackend = $true,

  [Parameter(Mandatory = $false)]
  [bool]$DeployWeb = $true,

  [Parameter(Mandatory = $false)]
  [string]$WebServiceName = "sentilyze-web",

  [Parameter(Mandatory = $false)]
  [string]$WebEnvFile = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step([string]$Message) {
  Write-Host ""
  Write-Host "==> $Message"
}

function Ensure-WritableTempDir() {
  # Work around Windows temp permission issues that can break `gcloud builds submit`
  $tmp = Join-Path -Path (Get-Location) -ChildPath ".tmp"
  if (-not (Test-Path -LiteralPath $tmp)) {
    New-Item -ItemType Directory -Path $tmp | Out-Null
  }

  $env:TEMP = $tmp
  $env:TMP = $tmp
}

function Add-ServiceAccountPolicyBindingWithRetry(
  [string]$ProjectId,
  [string]$ServiceAccountEmail,
  [string]$Member,
  [string]$Role
) {
  $delaySeconds = 1
  for ($attempt = 1; $attempt -le 6; $attempt++) {
    $output = & gcloud iam service-accounts add-iam-policy-binding $ServiceAccountEmail `
      --project $ProjectId `
      --member $Member `
      --role $Role 2>&1

    $output | Out-Host

    if ($LASTEXITCODE -eq 0) {
      return
    }

    if ($output -match "concurrent policy changes") {
      Start-Sleep -Seconds $delaySeconds
      $delaySeconds = [Math]::Min($delaySeconds * 2, 16)
      continue
    }

    throw ("Failed to add IAM policy binding: {0} {1} {2}" -f $ServiceAccountEmail, $Member, $Role)
  }

  throw ("Failed to add IAM policy binding after retries: {0} {1} {2}" -f $ServiceAccountEmail, $Member, $Role)
}

function Ensure-CloudRunDeployActAsPermissions([string]$ProjectId) {
  # Cloud Build often runs as the project's Compute Engine default SA.
  # Deploying to Cloud Run requires `iam.serviceaccounts.actAs` on the runtime SA (default is also compute SA),
  # which is satisfied by granting roles/iam.serviceAccountUser on that service account.
  Write-Step "Ensuring Cloud Run deploy IAM actAs permissions"

  $projectNumber = (& gcloud projects describe $ProjectId --format "value(projectNumber)" 2>&1).Trim()
  if (-not $projectNumber) {
    throw "Failed to resolve projectNumber for project: $ProjectId"
  }

  $computeSa = ("{0}-compute@developer.gserviceaccount.com" -f $projectNumber)
  $cloudBuildSa = ("{0}@cloudbuild.gserviceaccount.com" -f $projectNumber)

  Add-ServiceAccountPolicyBindingWithRetry -ProjectId $ProjectId -ServiceAccountEmail $computeSa -Member ("serviceAccount:{0}" -f $computeSa) -Role "roles/iam.serviceAccountUser"
  Add-ServiceAccountPolicyBindingWithRetry -ProjectId $ProjectId -ServiceAccountEmail $computeSa -Member ("serviceAccount:{0}" -f $cloudBuildSa) -Role "roles/iam.serviceAccountUser"
}

function Get-EnvVarsFromDotEnvFile([string]$Path) {
  if (-not (Test-Path -LiteralPath $Path)) {
    throw "Env file not found: $Path"
  }

  $pairs = @()
  foreach ($line in Get-Content -LiteralPath $Path) {
    $trimmed = $line.Trim()
    if ($trimmed.Length -eq 0) { continue }
    if ($trimmed.StartsWith("#")) { continue }

    $idx = $trimmed.IndexOf("=")
    if ($idx -lt 1) { continue }

    $key = $trimmed.Substring(0, $idx).Trim()
    $value = $trimmed.Substring($idx + 1)

    # gcloud expects comma-separated KEY=VALUE pairs.
    # If your value contains commas, escape them manually (\,) or set env vars via Secret Manager.
    $pairs += ("{0}={1}" -f $key, $value)
  }

  return ($pairs -join ",")
}

Write-Step "Setting gcloud project/region"
& gcloud config set project $ProjectId | Out-Host
& gcloud config set run/region $Region | Out-Host

Write-Step "Ensuring required APIs are enabled"
& gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com --project $ProjectId | Out-Host

Write-Step "Setting TEMP/TMP to a writable workspace folder"
Ensure-WritableTempDir

Ensure-CloudRunDeployActAsPermissions $ProjectId

Write-Step "Ensuring Artifact Registry repo exists: sentilyze"
& gcloud artifacts repositories describe sentilyze --location $Region --project $ProjectId | Out-Null
if ($LASTEXITCODE -ne 0) {
  & gcloud artifacts repositories create sentilyze --repository-format docker --location $Region --description "Sentilyze container images" --project $ProjectId | Out-Host

  # Re-check for clearer error output if creation fails
  & gcloud artifacts repositories describe sentilyze --location $Region --project $ProjectId | Out-Null
  if ($LASTEXITCODE -ne 0) {
    throw "Failed to create/find Artifact Registry repo 'sentilyze' in $Region (project: $ProjectId)."
  }
}

Write-Step "Configuring Docker auth for Artifact Registry"
& gcloud auth configure-docker ("{0}-docker.pkg.dev" -f $Region) --quiet | Out-Host

if ($DeployBackend) {
  Write-Step "Deploying backend services to Cloud Run via Cloud Build"
  & gcloud builds submit `
    --config infrastructure/cloudbuild/cloudbuild.yaml `
    --substitutions ("_REGION={0}" -f $Region) `
    --project $ProjectId | Out-Host
}

if ($DeployWeb) {
  $webImage = ("{0}-docker.pkg.dev/{1}/sentilyze/web:latest" -f $Region, $ProjectId)

  Write-Step ("Building + pushing web image: {0}" -f $webImage)
  & gcloud builds submit apps/web --tag $webImage --project $ProjectId | Out-Host

  $envArg = "NODE_ENV=production"
  if ($WebEnvFile -and $WebEnvFile.Trim().Length -gt 0) {
    Write-Step ("Loading env vars from: {0}" -f $WebEnvFile)
    $fileVars = Get-EnvVarsFromDotEnvFile $WebEnvFile
    if ($fileVars) {
      $envArg = $envArg + "," + $fileVars
    }
  }

  Write-Step ("Deploying web to Cloud Run service: {0}" -f $WebServiceName)
  & gcloud run deploy $WebServiceName `
    --image $webImage `
    --region $Region `
    --platform managed `
    --allow-unauthenticated `
    --port 3000 `
    --set-env-vars $envArg `
    --quiet `
    --project $ProjectId | Out-Host

  $webUrl = & gcloud run services describe $WebServiceName --region $Region --project $ProjectId --format "value(status.url)"
  Write-Step ("Web URL: {0}" -f $webUrl)
}

Write-Step "Done"
