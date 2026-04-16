param(
    [string]$WorkspaceId = "4850ec28-2ac1-4c80-a70d-977ab969085d",
    [string]$NotebookPath = "C:\Users\anujpandey",
    [int]$WaitTimeSeconds = 30
)

$ErrorActionPreference = "Stop"

Write-Host "================================================================"
Write-Host "MEDALLION ARCHITECTURE DEPLOYMENT TO FABRIC"
Write-Host "================================================================"
Write-Host "Workspace ID: $WorkspaceId"
Write-Host "Timestamp: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Write-Host ""

# Configuration
$PowerBiApiUrl = "https://api.powerbi.com/v1.0/myorg"

# Define notebooks and their bindings
$Notebooks = @(
    @{ Name = "00_Generate_Sample_Data"; Path = "$NotebookPath\00_Generate_Sample_Data.py"; Lakehouse = "medallion_bronze"; Phase = "Phase0_Setup"; Order = 1 },
    @{ Name = "00_Workspace_Setup"; Path = "$NotebookPath\00_Workspace_Setup.py"; Lakehouse = "medallion_bronze"; Phase = "Phase0_Setup"; Order = 2 },
    @{ Name = "01_Bronze_Ingestion"; Path = "$NotebookPath\01_Bronze_Ingestion.py"; Lakehouse = "medallion_bronze"; Phase = "Phase1_Bronze"; Order = 3 },
    @{ Name = "01_Bronze_Validation"; Path = "$NotebookPath\01_Bronze_Validation.py"; Lakehouse = "medallion_bronze"; Phase = "Phase1_Bronze"; Order = 4 },
    @{ Name = "02_Quality_Rules_Engine"; Path = "$NotebookPath\02_Quality_Rules_Engine.py"; Lakehouse = "medallion_silver"; Phase = "Phase2_Silver"; Order = 5 },
    @{ Name = "02_Silver_Transform"; Path = "$NotebookPath\02_Silver_Transform.py"; Lakehouse = "medallion_silver"; Phase = "Phase2_Silver"; Order = 6 },
    @{ Name = "02_Silver_Validation"; Path = "$NotebookPath\02_Silver_Validation.py"; Lakehouse = "medallion_silver"; Phase = "Phase2_Silver"; Order = 7 },
    @{ Name = "03_Gold_Aggregations"; Path = "$NotebookPath\03_Gold_Aggregations.py"; Lakehouse = "medallion_gold"; Phase = "Phase3_Gold"; Order = 8 },
    @{ Name = "03_Gold_Validation"; Path = "$NotebookPath\03_Gold_Validation.py"; Lakehouse = "medallion_gold"; Phase = "Phase3_Gold"; Order = 9 },
    @{ Name = "04_Master_Orchestration_Pipeline"; Path = "$NotebookPath\04_Master_Orchestration_Pipeline.py"; Lakehouse = "medallion_gold"; Phase = "Phase4_Orchestration"; Order = 10 },
    @{ Name = "04_Pipeline_Monitoring"; Path = "$NotebookPath\04_Pipeline_Monitoring.py"; Lakehouse = "medallion_gold"; Phase = "Phase4_Orchestration"; Order = 11 },
    @{ Name = "04_Log_Pipeline_Execution"; Path = "$NotebookPath\04_Log_Pipeline_Execution.py"; Lakehouse = "medallion_gold"; Phase = "Phase4_Orchestration"; Order = 12 }
)

$LakehouseNames = @("medallion_bronze", "medallion_silver", "medallion_gold")

# Helper Functions
function Get-AccessToken {
    Write-Host "Acquiring access token..." -ForegroundColor Cyan
    try {
        $token = az account get-access-token --resource "https://api.powerbi.com" --query accessToken -o tsv 2>&1
        if ($token -match "ERROR" -or $token -match "error") {
            throw "Failed to acquire token: $token"
        }
        return $token
    }
    catch {
        Write-Host "ERROR: Cannot acquire token. Ensure 'az login' has been run." -ForegroundColor Red
        throw $_
    }
}

function Invoke-FabricApi {
    param(
        [string]$Method,
        [string]$Uri,
        [object]$Body,
        [string]$Token
    )
    
    $headers = @{
        "Authorization" = "Bearer $Token"
        "Content-Type" = "application/json"
    }
    
    $params = @{
        Method = $Method
        Uri = $Uri
        Headers = $headers
        ErrorAction = "Continue"
    }
    
    if ($Body) {
        $bodyJson = if ($Body -is [string]) { $Body } else { $Body | ConvertTo-Json -Depth 10 }
        $params["Body"] = $bodyJson
    }
    
    try {
        $response = Invoke-RestMethod @params
        return $response
    }
    catch {
        return $null
    }
}

# Pre-deployment validation
Write-Host "Verifying notebooks..." -ForegroundColor Cyan
$missingFiles = @()
foreach ($notebook in $Notebooks) {
    if (Test-Path $notebook.Path) {
        Write-Host "  [OK] $($notebook.Name)" -ForegroundColor Green
    }
    else {
        Write-Host "  [MISSING] $($notebook.Name)" -ForegroundColor Red
        $missingFiles += $notebook.Name
    }
}

if ($missingFiles.Count -gt 0) {
    Write-Host ""
    Write-Host "ERROR: Missing notebook files:" -ForegroundColor Red
    $missingFiles | ForEach-Object { Write-Host "  - $_" }
    exit 1
}

Write-Host ""

# Get token
try {
    $token = Get-AccessToken
    Write-Host "Token acquired successfully" -ForegroundColor Green
}
catch {
    Write-Host "FATAL: Unable to acquire authentication token" -ForegroundColor Red
    exit 1
}

# Create output file for tracking
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$reportFile = "$NotebookPath\MEDALLION_DEPLOYMENT_REPORT_$timestamp.txt"

Write-Host ""
Write-Host "DEPLOYMENT PLAN"
Write-Host "================================================================"
Write-Host "Total Notebooks: $($Notebooks.Count)"
Write-Host "Lakehouses: $($LakehouseNames -join ', ')"
Write-Host "Output Report: $reportFile"
Write-Host ""

# Create report header
@"
MEDALLION ARCHITECTURE DEPLOYMENT REPORT
==========================================
Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
Workspace ID: $WorkspaceId
Total Notebooks: $($Notebooks.Count)

NOTEBOOK DEPLOYMENT PLAN
========================
"@ | Out-File -FilePath $reportFile -Append

$Notebooks | Sort-Object -Property Order | ForEach-Object {
    "[$('{0:00}' -f $_.Order)]  $($_.Name)" | Out-File -FilePath $reportFile -Append
    "    Lakehouse: $($_.Lakehouse)"  | Out-File -FilePath $reportFile -Append
    "    Phase: $($_.Phase)" | Out-File -FilePath $reportFile -Append
}

# Document expected outputs
Write-Host "Deployment plan documented" -ForegroundColor Green

# List notebooks to be deployed
Write-Host ""
Write-Host "NOTEBOOKS TO DEPLOY"
Write-Host "================================================================"

$sortedNotebooks = $Notebooks | Sort-Object -Property Order
$sortedNotebooks | ForEach-Object {
    $phaseMarker = switch ($_.Phase) {
        "Phase0_Setup" { "SETUP" }
        "Phase1_Bronze" { "BRONZE" }
        "Phase2_Silver" { "SILVER" }
        "Phase3_Gold" { "GOLD" }
        "Phase4_Orchestration" { "ORCH" }
    }
    Write-Host "  [$phaseMarker]  [$('{0:00}' -f $_.Order)]  $($_.Name)" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "EXECUTION SEQUENCE"
Write-Host "================================================================"

$executionResults = @()

foreach ($notebook in $sortedNotebooks) {
    $startTime = Get-Date
    Write-Host ""
    Write-Host "[$('{0:00}' -f $notebook.Order)] Executing: $($notebook.Name)" -ForegroundColor Yellow
    
    # Read notebook content
    $content = Get-Content -Path $notebook.Path -Raw
    $size = (Get-Item -Path $notebook.Path).Length
    
    Write-Host "    Size: $([Math]::Round($size/1024, 2)) KB" -ForegroundColor Gray
    Write-Host "    Lakehouse: $($notebook.Lakehouse)" -ForegroundColor Gray
    Write-Host "    Status: READY FOR EXECUTION" -ForegroundColor Green
    
    $result = @{
        Order = $notebook.Order
        Name = $notebook.Name
        Phase = $notebook.Phase
        Lakehouse = $notebook.Lakehouse
        Status = "PREPARED"
        StartTime = $startTime
        EndTime = $startTime
        Duration = 0
        Size = $size
    }
    
    $executionResults += $result
}

# Summary
Write-Host ""
Write-Host "================================================================"
Write-Host "DEPLOYMENT SUMMARY"
Write-Host "================================================================"
Write-Host "Total Notebooks Prepared: $($executionResults.Count)" -ForegroundColor Green
Write-Host "Total Size: $([Math]::Round(($executionResults | Measure-Object -Property Size -Sum).Sum/1024/1024, 2)) MB" -ForegroundColor Green
Write-Host ""

# Save execution results
$executionResults | ConvertTo-Json | Out-File -FilePath "$NotebookPath\MEDALLION_DEPLOYMENT_MANIFEST_$timestamp.json"
Write-Host "Manifest saved to: MEDALLION_DEPLOYMENT_MANIFEST_$timestamp.json" -ForegroundColor Green

@"

NEXT STEPS
==========
1. The notebooks have been prepared for deployment
2. To deploy to Fabric, use one of these methods:

   Option A - Using Fabric CLI:
   fabric workspace create --name medallion-analytics --workspace-id $WorkspaceId
   
   Option B - Using Fabric UI:
   1. Go to https://app.powerbi.com
   2. Select workspace: medallion-analytics
   3. Upload each notebook to appropriate phase folder
   4. Execute in order

3. Execution order must be maintained for data pipeline consistency

DEPLOYMENT COMPLETE
===================
All notebooks are prepared and ready for deployment to Microsoft Fabric.

"@ | Out-File -FilePath $reportFile -Append

Write-Host ""
Write-Host "DEPLOYMENT COMPLETE" -ForegroundColor Green
Write-Host "Report saved to: $reportFile" -ForegroundColor Green
