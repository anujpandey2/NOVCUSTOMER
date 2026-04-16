#requires -Version 5.1
<#
.SYNOPSIS
    Medallion Architecture Deployment to Microsoft Fabric
    
.DESCRIPTION
    Deploys and executes 12 notebooks across 3 lakehouses in Microsoft Fabric
    using REST APIs with proper authentication, rate limiting, and error handling.
    
.PARAMETER WorkspaceId
    The Fabric workspace ID
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$WorkspaceId = "4850ec28-2ac1-4c80-a70d-977ab969085d"
)

$ErrorActionPreference = "Continue"
$ProgressPreference = "SilentlyContinue"

# Configuration
$BASE_URL = "https://api.powerbi.com/v1.0/myorg"
$RATE_LIMIT_DELAY = 3  # seconds
$POLL_INTERVAL = 5      # seconds
$MAX_WAIT_TIME = 600    # seconds (10 minutes per notebook)
$DeploymentLog = @()

# Notebook definitions (in execution order)
$Notebooks = @(
    @{ Path = "C:\Users\anujpandey\00_Generate_Sample_Data.py"; Name = "00_Generate_Sample_Data"; Lakehouse = "medallion_bronze"; Order = 1; Phase = "Setup" },
    @{ Path = "C:\Users\anujpandey\00_Workspace_Setup.py"; Name = "00_Workspace_Setup"; Lakehouse = "medallion_bronze"; Order = 2; Phase = "Setup" },
    @{ Path = "C:\Users\anujpandey\01_Bronze_Ingestion.py"; Name = "01_Bronze_Ingestion"; Lakehouse = "medallion_bronze"; Order = 3; Phase = "Bronze" },
    @{ Path = "C:\Users\anujpandey\01_Bronze_Validation.py"; Name = "01_Bronze_Validation"; Lakehouse = "medallion_bronze"; Order = 4; Phase = "Bronze" },
    @{ Path = "C:\Users\anujpandey\02_Quality_Rules_Engine.py"; Name = "02_Quality_Rules_Engine"; Lakehouse = "medallion_silver"; Order = 5; Phase = "Silver" },
    @{ Path = "C:\Users\anujpandey\02_Silver_Transform.py"; Name = "02_Silver_Transform"; Lakehouse = "medallion_silver"; Order = 6; Phase = "Silver" },
    @{ Path = "C:\Users\anujpandey\02_Silver_Validation.py"; Name = "02_Silver_Validation"; Lakehouse = "medallion_silver"; Order = 7; Phase = "Silver" },
    @{ Path = "C:\Users\anujpandey\03_Gold_Aggregations.py"; Name = "03_Gold_Aggregations"; Lakehouse = "medallion_gold"; Order = 8; Phase = "Gold" },
    @{ Path = "C:\Users\anujpandey\03_Gold_Validation.py"; Name = "03_Gold_Validation"; Lakehouse = "medallion_gold"; Order = 9; Phase = "Gold" },
    @{ Path = "C:\Users\anujpandey\04_Master_Orchestration_Pipeline.py"; Name = "04_Master_Orchestration_Pipeline"; Lakehouse = "medallion_gold"; Order = 10; Phase = "Orchestration" },
    @{ Path = "C:\Users\anujpandey\04_Pipeline_Monitoring.py"; Name = "04_Pipeline_Monitoring"; Lakehouse = "medallion_gold"; Order = 11; Phase = "Orchestration" },
    @{ Path = "C:\Users\anujpandey\04_Log_Pipeline_Execution.py"; Name = "04_Log_Pipeline_Execution"; Lakehouse = "medallion_gold"; Order = 12; Phase = "Orchestration" }
)

$Lakehouses = @("medallion_bronze", "medallion_silver", "medallion_gold")

# ============================================================================
# FUNCTIONS
# ============================================================================

function Write-Banner {
    param([string]$Text, [string]$Color = "Cyan")
    Write-Host ""
    Write-Host "=" * 70 -ForegroundColor $Color
    Write-Host $Text -ForegroundColor $Color
    Write-Host "=" * 70 -ForegroundColor $Color
}

function Write-Step {
    param([string]$Text, [string]$Status = "INFO")
    $colors = @{
        "INFO" = "White"; "OK" = "Green"; "WARN" = "Yellow"; "ERROR" = "Red"
    }
    $prefix = @{
        "INFO" = "[*]"; "OK" = "[✓]"; "WARN" = "[!]"; "ERROR" = "[✗]"
    }
    Write-Host "$($prefix[$Status]) $Text" -ForegroundColor $colors[$Status]
}

function Get-FabricToken {
    try {
        Write-Step "Retrieving Fabric API token..." "INFO"
        $token = az account get-access-token --resource "https://analysis.windows.net/powerbi/api" --query accessToken -o tsv 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Step "Token retrieved successfully" "OK"
            return $token
        } else {
            Write-Step "Failed to retrieve token: $token" "ERROR"
            return $null
        }
    }
    catch {
        Write-Step "Exception during token retrieval: $_" "ERROR"
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
            $statusCode = $_.Exception.Response.StatusCode.Value
            
            if ($statusCode -eq 404) {
                return @{ Success = $false; Status = 404; Error = "Not Found" }
            }
            elseif ($statusCode -eq 409) {
                return @{ Success = $false; Status = 409; Error = "Conflict - Resource may exist" }
            }
            elseif ($statusCode -ge 500 -and $attempt -lt $Retries) {
                Start-Sleep -Seconds ([Math]::Pow(2, $attempt - 1))
                continue
            }
            
            return @{ Success = $false; Status = $statusCode; Error = $_.Exception.Message }
        }
    }
}

function Verify-NotebookFiles {
    Write-Step "Verifying all notebook files exist..." "INFO"
    
    $allExist = $true
    foreach ($nb in $Notebooks) {
        if (Test-Path $nb.Path) {
            $size = (Get-Item $nb.Path).Length
            Write-Host "  [✓] $($nb.Name) ($size bytes)" -ForegroundColor Green
        }
        else {
            Write-Host "  [✗] $($nb.Name) NOT FOUND" -ForegroundColor Red
            $allExist = $false
        }
    }
    
    return $allExist
}

function Deploy-Lakehouses {
    param([string]$Token)
    
    Write-Banner "Step 1: Creating Lakehouses" "Yellow"
    
    foreach ($lakehouse in $Lakehouses) {
        Write-Step "Creating lakehouse: $lakehouse" "INFO"
        
        $body = @{
            displayName = $lakehouse
            description = "Medallion architecture $lakehouse layer"
        }
        
        $result = Invoke-FabricAPI -Method "POST" `
            -Endpoint "/workspaces/$WorkspaceId/lakehouses" `
            -Body $body -Token $Token
        
        if ($result.Success) {
            Write-Step "Lakehouse '$lakehouse' created successfully" "OK"
            $global:DeploymentLog += @{
                Timestamp = Get-Date
                Operation = "CreateLakehouse"
                Resource = $lakehouse
                Status = "Success"
            }
        }
        else {
            if ($result.Status -eq 409) {
                Write-Step "Lakehouse '$lakehouse' already exists (reusing)" "WARN"
            }
            else {
                Write-Step "Failed to create lakehouse: $($result.Error)" "ERROR"
            }
        }
        
        Start-Sleep -Seconds $RATE_LIMIT_DELAY
    }
}

function Deploy-Notebooks {
    param([string]$Token)
    
    Write-Banner "Step 2: Deploying Notebooks" "Yellow"
    
    $deployedNotebooks = @{}
    
    foreach ($nb in $Notebooks) {
        Write-Step "Deploying notebook: $($nb.Name)" "INFO"
        
        # Read notebook content
        $content = Get-Content -Path $nb.Path -Raw
        $contentBase64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($content))
        
        $body = @{
            displayName = $nb.Name
            type = "Notebook"
            definition = @{
                format = "ipynb"
                parts = @(
                    @{
                        path = "notebook-content.ipynb"
                        payloadType = "InlineBase64"
                        payload = $contentBase64
                    }
                )
            }
        }
        
        $result = Invoke-FabricAPI -Method "POST" `
            -Endpoint "/workspaces/$WorkspaceId/items" `
            -Body $body -Token $Token
        
        if ($result.Success) {
            $notebookId = $result.Content.id
            $deployedNotebooks[$nb.Name] = @{
                Id = $notebookId
                Lakehouse = $nb.Lakehouse
                Order = $nb.Order
                Path = $nb.Path
            }
            Write-Step "Notebook deployed: $notebookId" "OK"
        }
        else {
            Write-Step "Failed to deploy notebook: $($result.Error)" "ERROR"
        }
        
        Start-Sleep -Seconds $RATE_LIMIT_DELAY
    }
    
    return $deployedNotebooks
}

function Bind-NotebooksToLakehouses {
    param(
        [hashtable]$DeployedNotebooks,
        [string]$Token
    )
    
    Write-Banner "Step 3: Binding Notebooks to Lakehouses" "Yellow"
    
    foreach ($nbName in $DeployedNotebooks.Keys) {
        $nb = $DeployedNotebooks[$nbName]
        $lakehouse = $nb.Lakehouse
        
        Write-Step "Binding $nbName to $lakehouse..." "INFO"
        
        # First, get the lakehouse ID
        $result = Invoke-FabricAPI -Method "GET" `
            -Endpoint "/workspaces/$WorkspaceId/lakehouses" `
            -Token $Token
        
        $lhId = $null
        if ($result.Success) {
            $lh = $result.Content.value | Where-Object { $_.displayName -eq $lakehouse } | Select-Object -First 1
            $lhId = $lh.id
        }
        
        if ($lhId) {
            $body = @{
                properties = @{
                    oneLakeWorkspaceId = $WorkspaceId
                    oneLakeLakehouseId = $lhId
                }
            }
            
            $updateResult = Invoke-FabricAPI -Method "PATCH" `
                -Endpoint "/workspaces/$WorkspaceId/items/$($nb.Id)" `
                -Body $body -Token $Token
            
            if ($updateResult.Success) {
                Write-Step "Notebook bound to $lakehouse successfully" "OK"
            }
            else {
                Write-Step "Failed to bind notebook: $($updateResult.Error)" "WARN"
            }
        }
        
        Start-Sleep -Seconds $RATE_LIMIT_DELAY
    }
}

function Execute-NotebooksSequentially {
    param(
        [hashtable]$DeployedNotebooks,
        [string]$Token
    )
    
    Write-Banner "Step 4: Executing Notebooks Sequentially" "Yellow"
    
    $executionResults = @()
    $sortedNotebooks = $DeployedNotebooks.GetEnumerator() | 
        Sort-Object { $_.Value.Order }
    
    foreach ($entry in $sortedNotebooks) {
        $nbName = $entry.Name
        $nbInfo = $entry.Value
        $notebookId = $nbInfo.Id
        $order = $nbInfo.Order
        
        Write-Host ""
        Write-Host "[$order/12] Executing: $nbName" -ForegroundColor Cyan
        Write-Host "-" * 70 -ForegroundColor Cyan
        
        $startTime = Get-Date
        
        # Submit job
        $submitResult = Invoke-FabricAPI -Method "POST" `
            -Endpoint "/workspaces/$WorkspaceId/notebooks/$notebookId/jobs/instances" `
            -Token $Token
        
        if ($submitResult.Success) {
            $jobId = $submitResult.Content.id
            Write-Step "Job submitted: $jobId" "OK"
            
            # Poll for completion
            $elapsedSeconds = 0
            $completed = $false
            $jobStatus = "Submitted"
            $jobOutput = ""
            
            while ($elapsedSeconds -lt $MAX_WAIT_TIME) {
                Start-Sleep -Seconds $POLL_INTERVAL
                $elapsedSeconds += $POLL_INTERVAL
                
                $statusResult = Invoke-FabricAPI -Method "GET" `
                    -Endpoint "/workspaces/$WorkspaceId/notebooks/$notebookId/jobs/instances/$jobId" `
                    -Token $Token
                
                if ($statusResult.Success) {
                    $jobStatus = $statusResult.Content.status
                    $jobOutput = if ($statusResult.Content.output) { $statusResult.Content.output } else { "" }
                    
                    Write-Host "  Status: $jobStatus (${elapsedSeconds}s elapsed)" -ForegroundColor Cyan
                    
                    if ($jobStatus -eq "Completed" -or $jobStatus -eq "Failed" -or $jobStatus -eq "Aborted") {
                        $completed = $true
                        break
                    }
                }
                else {
                    Write-Step "Failed to get job status: $($statusResult.Error)" "WARN"
                }
            }
            
            $endTime = Get-Date
            $duration = ($endTime - $startTime).TotalSeconds
            
            if ($completed) {
                if ($jobStatus -eq "Completed") {
                    Write-Step "Notebook execution completed in $([Math]::Round($duration, 2))s" "OK"
                }
                else {
                    Write-Step "Notebook execution $jobStatus after $([Math]::Round($duration, 2))s" "ERROR"
                }
            }
            else {
                Write-Step "Notebook execution timed out after ${MAX_WAIT_TIME}s" "ERROR"
            }
            
            $executionResults += @{
                Order = $order
                Name = $nbName
                Status = $jobStatus
                Duration = $duration
                Output = $jobOutput.Substring(0, [Math]::Min(200, $jobOutput.Length))
                Timestamp = $startTime
            }
        }
        else {
            Write-Step "Failed to submit job: $($submitResult.Error)" "ERROR"
            $executionResults += @{
                Order = $order
                Name = $nbName
                Status = "SubmissionFailed"
                Duration = 0
                Output = $submitResult.Error
                Timestamp = Get-Date
            }
        }
        
        Start-Sleep -Seconds $RATE_LIMIT_DELAY
    }
    
    return $executionResults
}

function Generate-ExecutionReport {
    param([array]$Results)
    
    Write-Banner "Execution Report" "Green"
    
    Write-Host ""
    Write-Host "Summary:" -ForegroundColor Cyan
    Write-Host "-" * 70 -ForegroundColor Cyan
    
    $completed = ($Results | Where-Object { $_.Status -eq "Completed" }).Count
    $failed = ($Results | Where-Object { $_.Status -ne "Completed" }).Count
    $totalDuration = ($Results | Measure-Object -Property Duration -Sum).Sum
    
    Write-Host "Total Notebooks:      $($Results.Count)"
    Write-Host "Successful:           $completed" -ForegroundColor Green
    Write-Host "Failed/Other:         $failed" -ForegroundColor Red
    Write-Host "Total Duration:       $([Math]::Round($totalDuration, 2))s"
    Write-Host ""
    
    Write-Host "Detailed Results:" -ForegroundColor Cyan
    Write-Host "-" * 70 -ForegroundColor Cyan
    
    foreach ($result in $Results) {
        $statusColor = if ($result.Status -eq "Completed") { "Green" } else { "Red" }
        Write-Host "[$($result.Order):12] $($result.Name)" -ForegroundColor Cyan
        Write-Host "  Status:   $($result.Status)" -ForegroundColor $statusColor
        Write-Host "  Duration: $([Math]::Round($result.Duration, 2))s"
        Write-Host "  Output:   $($result.Output)"
        Write-Host ""
    }
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

Clear-Host
Write-Banner "MEDALLION ARCHITECTURE DEPLOYMENT TO FABRIC" "Cyan"
Write-Host "Workspace ID: $WorkspaceId" -ForegroundColor Cyan
Write-Host "Timestamp: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Cyan
Write-Host ""

# Step 0: Verify files
if (-not (Verify-NotebookFiles)) {
    Write-Step "Some notebook files are missing. Aborting deployment." "ERROR"
    exit 1
}

Write-Host ""

# Step 1: Get token
$token = Get-FabricToken
if (-not $token) {
    Write-Step "Failed to obtain Fabric API token. Aborting deployment." "ERROR"
    exit 1
}

Write-Host ""

# Step 2: Deploy lakehouses
Deploy-Lakehouses -Token $token

Write-Host ""

# Step 3: Deploy notebooks
$deployedNotebooks = Deploy-Notebooks -Token $token

Write-Host ""

# Step 4: Bind notebooks
Bind-NotebooksToLakehouses -DeployedNotebooks $deployedNotebooks -Token $token

Write-Host ""

# Step 5: Execute notebooks
$executionResults = Execute-NotebooksSequentially -DeployedNotebooks $deployedNotebooks -Token $token

Write-Host ""

# Step 6: Generate report
Generate-ExecutionReport -Results $executionResults

Write-Host ""
Write-Banner "DEPLOYMENT COMPLETE" "Green"
Write-Host "Check the execution results above for any errors or warnings." -ForegroundColor Green
