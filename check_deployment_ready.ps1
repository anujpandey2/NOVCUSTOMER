#requires -Version 5.1

param(
    [string]$WorkspaceId = "4850ec28-2ac1-4c80-a70d-977ab969085d"
)

$ErrorActionPreference = "Continue"
$ProgressPreference = "SilentlyContinue"

$BASE_URL = "https://api.powerbi.com/v1.0/myorg"
$RATE_LIMIT_DELAY = 3
$POLL_INTERVAL = 5
$MAX_WAIT_TIME = 600

$Notebooks = @(
    @{ Path = "C:\Users\anujpandey\00_Generate_Sample_Data.py"; Name = "00_Generate_Sample_Data"; Lakehouse = "medallion_bronze"; Order = 1 },
    @{ Path = "C:\Users\anujpandey\00_Workspace_Setup.py"; Name = "00_Workspace_Setup"; Lakehouse = "medallion_bronze"; Order = 2 },
    @{ Path = "C:\Users\anujpandey\01_Bronze_Ingestion.py"; Name = "01_Bronze_Ingestion"; Lakehouse = "medallion_bronze"; Order = 3 },
    @{ Path = "C:\Users\anujpandey\01_Bronze_Validation.py"; Name = "01_Bronze_Validation"; Lakehouse = "medallion_bronze"; Order = 4 },
    @{ Path = "C:\Users\anujpandey\02_Quality_Rules_Engine.py"; Name = "02_Quality_Rules_Engine"; Lakehouse = "medallion_silver"; Order = 5 },
    @{ Path = "C:\Users\anujpandey\02_Silver_Transform.py"; Name = "02_Silver_Transform"; Lakehouse = "medallion_silver"; Order = 6 },
    @{ Path = "C:\Users\anujpandey\02_Silver_Validation.py"; Name = "02_Silver_Validation"; Lakehouse = "medallion_silver"; Order = 7 },
    @{ Path = "C:\Users\anujpandey\03_Gold_Aggregations.py"; Name = "03_Gold_Aggregations"; Lakehouse = "medallion_gold"; Order = 8 },
    @{ Path = "C:\Users\anujpandey\03_Gold_Validation.py"; Name = "03_Gold_Validation"; Lakehouse = "medallion_gold"; Order = 9 },
    @{ Path = "C:\Users\anujpandey\04_Master_Orchestration_Pipeline.py"; Name = "04_Master_Orchestration_Pipeline"; Lakehouse = "medallion_gold"; Order = 10 },
    @{ Path = "C:\Users\anujpandey\04_Pipeline_Monitoring.py"; Name = "04_Pipeline_Monitoring"; Lakehouse = "medallion_gold"; Order = 11 },
    @{ Path = "C:\Users\anujpandey\04_Log_Pipeline_Execution.py"; Name = "04_Log_Pipeline_Execution"; Lakehouse = "medallion_gold"; Order = 12 }
)

$Lakehouses = @("medallion_bronze", "medallion_silver", "medallion_gold")

function Write-Banner {
    param([string]$Text)
    Write-Host ""
    Write-Host "=" * 70 -ForegroundColor Cyan
    Write-Host $Text -ForegroundColor Cyan
    Write-Host "=" * 70 -ForegroundColor Cyan
}

function Get-FabricToken {
    Write-Host "[*] Retrieving Fabric API token..." -ForegroundColor White
    $token = az account get-access-token --resource "https://analysis.windows.net/powerbi/api" --query accessToken -o tsv 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Token retrieved successfully" -ForegroundColor Green
        return $token
    } else {
        Write-Host "[ERROR] Failed to retrieve token" -ForegroundColor Red
        return $null
    }
}

function Invoke-FabricAPI {
    param(
        [string]$Method,
        [string]$Endpoint,
        [object]$Body,
        [string]$Token,
        [int]$Retries = 3
    )
    
    $url = "$BASE_URL$Endpoint"
    $headers = @{
        "Authorization" = "Bearer $Token"
        "Content-Type" = "application/json"
    }
    
    for ($attempt = 1; $attempt -le $Retries; $attempt++) {
        try {
            $params = @{
                Uri = $url
                Method = $Method
                Headers = $headers
                TimeoutSec = 30
                ErrorAction = "Stop"
            }
            
            if ($Body) {
                $params["Body"] = $Body | ConvertTo-Json -Depth 10
            }
            
            $response = Invoke-WebRequest @params
            return @{ Success = $true; Status = $response.StatusCode; Content = $response.Content | ConvertFrom-Json }
        }
        catch {
            if ($attempt -lt $Retries) {
                Start-Sleep -Seconds ([Math]::Pow(2, $attempt - 1))
                continue
            }
            return @{ Success = $false; Status = 0; Error = $_.Exception.Message }
        }
    }
}

Write-Banner "MEDALLION ARCHITECTURE DEPLOYMENT TO FABRIC"
Write-Host "Workspace ID: $WorkspaceId" -ForegroundColor Cyan

# Verify notebooks
Write-Host "[*] Verifying notebooks..." -ForegroundColor White
$allExist = $true
foreach ($nb in $Notebooks) {
    if (Test-Path $nb.Path) {
        $size = (Get-Item $nb.Path).Length
        Write-Host "  [OK] $($nb.Name) ($size bytes)" -ForegroundColor Green
    } else {
        Write-Host "  [ERROR] $($nb.Name) NOT FOUND" -ForegroundColor Red
        $allExist = $false
    }
}

if (-not $allExist) {
    Write-Host "[ERROR] Missing notebooks, aborting" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Get token
$token = Get-FabricToken
if (-not $token) {
    Write-Host "[ERROR] Failed to get token, aborting" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Banner "DEPLOYMENT SUMMARY"

Write-Host "Total Notebooks: 12" -ForegroundColor Cyan
Write-Host "  Phase 0 (Setup): 2 notebooks" -ForegroundColor White
Write-Host "  Phase 1 (Bronze): 2 notebooks" -ForegroundColor White
Write-Host "  Phase 2 (Silver): 3 notebooks" -ForegroundColor White
Write-Host "  Phase 3 (Gold): 2 notebooks" -ForegroundColor White
Write-Host "  Phase 4 (Orchestration): 3 notebooks" -ForegroundColor White
Write-Host ""
Write-Host "Lakehouses: 3" -ForegroundColor Cyan
Write-Host "  medallion_bronze - 4 notebooks" -ForegroundColor White
Write-Host "  medallion_silver - 3 notebooks" -ForegroundColor White
Write-Host "  medallion_gold - 5 notebooks" -ForegroundColor White
Write-Host ""

Write-Host "[OK] All notebooks verified and ready for deployment" -ForegroundColor Green
Write-Host "[OK] Authentication successful" -ForegroundColor Green
Write-Host "[OK] Deployment plan prepared" -ForegroundColor Green

Write-Host ""
Write-Banner "DEPLOYMENT READY"

Write-Host "To execute deployment, run the following command:" -ForegroundColor Yellow
Write-Host "python C:\Users\anujpandey\medallion_deployment.py" -ForegroundColor Cyan
Write-Host ""
Write-Host "Deployment Artifacts:" -ForegroundColor Cyan
Write-Host "  MEDALLION_DEPLOYMENT_PLAN.json - Machine-readable plan" -ForegroundColor White
Write-Host "  medallion_deployment.py - Python orchestrator" -ForegroundColor White
Write-Host "  deploy.ps1 - PowerShell deployment script" -ForegroundColor White
Write-Host "  MEDALLION_DEPLOYMENT_SUMMARY.md - Full documentation" -ForegroundColor White
Write-Host ""

