param(
  [Parameter(Mandatory = $true)]
  [string]$ProjectId,

  [Parameter(Mandatory = $false)]
  [string]$Region = "us-central1",

  [Parameter(Mandatory = $false)]
  [string]$ServiceName = "sentilyze-web",

  [Parameter(Mandatory = $false)]
  [string]$EnvFile = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# PowerShell 7+ treats native stderr as errors when $ErrorActionPreference='Stop'.
# gcloud frequently writes non-fatal status lines to stderr, which can abort scripts.
# Disable this behavior and rely on $LASTEXITCODE instead.
if ($PSVersionTable.PSVersion.Major -ge 7) {
  $PSNativeCommandUseErrorActionPreference = $false
}

function Write-Step([string]$Message) {
  Write-Host ""
  Write-Host "==> $Message"
}

function Ensure-WritableTempDir() {
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
    # Use cmd.exe to avoid PowerShell treating gcloud stderr as terminating errors.
    $cmd = @(
      'gcloud iam service-accounts add-iam-policy-binding'
      ('"{0}"' -f $ServiceAccountEmail)
      ('--project "{0}"' -f $ProjectId)
      ('--member "{0}"' -f $Member)
      ('--role "{0}"' -f $Role)
      '2>&1'
    ) -join ' '

    $output = & cmd.exe /c $cmd

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
    # gcloud --set-env-vars uses comma-separated key=value pairs.
    # Escape commas in values so they are treated literally (\,).
    $value = $value.Replace(",", "\,")
    $pairs += ("{0}={1}" -f $key, $value)
  }

  return ($pairs -join ",")
}

Write-Step "Setting gcloud project/region"
& gcloud config set project $ProjectId | Out-Host
& gcloud config set run/region $Region | Out-Host

Write-Step "Setting TEMP/TMP to a writable workspace folder"
Ensure-WritableTempDir

Ensure-CloudRunDeployActAsPermissions $ProjectId

Write-Step "Ensuring Artifact Registry repo exists: sentilyze"
& gcloud artifacts repositories describe sentilyze --location $Region --project $ProjectId | Out-Null
if ($LASTEXITCODE -ne 0) {
  & gcloud artifacts repositories create sentilyze --repository-format docker --location $Region --description "Sentilyze container images" --project $ProjectId | Out-Host
  & gcloud artifacts repositories describe sentilyze --location $Region --project $ProjectId | Out-Null
  if ($LASTEXITCODE -ne 0) {
    throw "Failed to create/find Artifact Registry repo 'sentilyze' in $Region (project: $ProjectId)."
  }
}

Write-Step "Building + pushing web image with Cloud Build"
$webImage = ("{0}-docker.pkg.dev/{1}/sentilyze/web:latest" -f $Region, $ProjectId)
& gcloud builds submit apps/web --tag $webImage --project $ProjectId | Out-Host
if ($LASTEXITCODE -ne 0) {
  throw "Cloud Build failed. Aborting deploy."
}

$envArg = "NODE_ENV=production"
if ($EnvFile -and $EnvFile.Trim().Length -gt 0) {
  Write-Step ("Loading env vars from: {0}" -f $EnvFile)
  $fileVars = Get-EnvVarsFromDotEnvFile $EnvFile
  if ($fileVars) {
    $envArg = $envArg + "," + $fileVars
  }
}

Write-Step ("Deploying to Cloud Run service: {0}" -f $ServiceName)
& gcloud run deploy $ServiceName `
  --image $webImage `
  --region $Region `
  --platform managed `
  --allow-unauthenticated `
  --port 3000 `
  --set-env-vars $envArg `
  --quiet `
  --project $ProjectId | Out-Host

$url = & gcloud run services describe $ServiceName --region $Region --project $ProjectId --format "value(status.url)"
Write-Step ("URL: {0}" -f $url)
