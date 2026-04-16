$WorkspaceId = "4850ec28-2ac1-4c80-a70d-977ab969085d"
$BASE_URL = "https://api.powerbi.com/v1.0/myorg"
$RATE_LIMIT_DELAY = 3
$POLL_INTERVAL = 5
$MAX_WAIT_TIME = 600

$notebooks = @(
    @{ Path = "C:\Users\anujpandey\00_Generate_Sample_Data.py"; DisplayName = "00_Generate_Sample_Data"; Lakehouse = "medallion_bronze"; Order = 1 },
    @{ Path = "C:\Users\anujpandey\00_Workspace_Setup.py"; DisplayName = "00_Workspace_Setup"; Lakehouse = "medallion_bronze"; Order = 2 },
    @{ Path = "C:\Users\anujpandey\01_Bronze_Ingestion.py"; DisplayName = "01_Bronze_Ingestion"; Lakehouse = "medallion_bronze"; Order = 3 },
    @{ Path = "C:\Users\anujpandey\01_Bronze_Validation.py"; DisplayName = "01_Bronze_Validation"; Lakehouse = "medallion_bronze"; Order = 4 },
    @{ Path = "C:\Users\anujpandey\02_Quality_Rules_Engine.py"; DisplayName = "02_Quality_Rules_Engine"; Lakehouse = "medallion_silver"; Order = 5 },
    @{ Path = "C:\Users\anujpandey\02_Silver_Transform.py"; DisplayName = "02_Silver_Transform"; Lakehouse = "medallion_silver"; Order = 6 },
    @{ Path = "C:\Users\anujpandey\02_Silver_Validation.py"; DisplayName = "02_Silver_Validation"; Lakehouse = "medallion_silver"; Order = 7 },
    @{ Path = "C:\Users\anujpandey\03_Gold_Aggregations.py"; DisplayName = "03_Gold_Aggregations"; Lakehouse = "medallion_gold"; Order = 8 },
    @{ Path = "C:\Users\anujpandey\03_Gold_Validation.py"; DisplayName = "03_Gold_Validation"; Lakehouse = "medallion_gold"; Order = 9 },
    @{ Path = "C:\Users\anujpandey\04_Master_Orchestration_Pipeline.py"; DisplayName = "04_Master_Orchestration_Pipeline"; Lakehouse = "medallion_gold"; Order = 10 },
    @{ Path = "C:\Users\anujpandey\04_Pipeline_Monitoring.py"; DisplayName = "04_Pipeline_Monitoring"; Lakehouse = "medallion_gold"; Order = 11 },
    @{ Path = "C:\Users\anujpandey\04_Log_Pipeline_Execution.py"; DisplayName = "04_Log_Pipeline_Execution"; Lakehouse = "medallion_gold"; Order = 12 }
)

function Get-AccessToken {
    $token = az account get-access-token --query accessToken -o tsv
    if ($LASTEXITCODE -ne 0) { throw "Auth failed" }
    return $token
}

function Invoke-FabricAPI {
    param([string]$Method, [string]$Endpoint, [object]$Body, [string]$Token)
    $headers = @{ "Authorization" = "Bearer $Token"; "Content-Type" = "application/json" }
    $url = "$BASE_URL$Endpoint"
    
    try {
        $response = Invoke-WebRequest -Uri $url -Method $Method -Headers $headers -Body (if ($Body) { $Body | ConvertTo-Json -Depth 10 }) -ErrorAction Stop
        return @{ Success = $true; Status = $response.StatusCode; Content = $response.Content | ConvertFrom-Json }
    }
    catch {
        $statusCode = if ($_.Exception.Response) { $_.Exception.Response.StatusCode.Value } else { 0 }
        return @{ Success = $false; Status = $statusCode; Error = $_.Exception.Message }
    }
}

Write-Host "Medallion Deployment - Fabric REST API" -ForegroundColor Cyan
Write-Host "Workspace: $WorkspaceId" -ForegroundColor Cyan
Write-Host ""

Write-Host "Step 1: Authenticating..." -ForegroundColor Yellow
try {
    $token = Get-AccessToken
    Write-Host "OK - Token obtained" -ForegroundColor Green
} catch {
    Write-Host "FAILED: $_" -ForegroundColor Red
    exit 1
}
Write-Host ""

Write-Host "Step 2: Testing workspace access..." -ForegroundColor Yellow
$wsResult = Invoke-FabricAPI -Method "GET" -Endpoint "/workspaces/$WorkspaceId" -Token $token
if ($wsResult.Success) {
    Write-Host "OK - Workspace accessible" -ForegroundColor Green
    Write-Host "  Name: $($wsResult.Content.displayName)" -ForegroundColor Gray
} else {
    Write-Host "FAILED: Cannot access workspace $($wsResult.Status)" -ForegroundColor Red
    exit 1
}
Write-Host ""

Write-Host "Step 3: Creating lakehouses..." -ForegroundColor Yellow

$lakehouses = @{}
foreach ($lhName in @("medallion_bronze", "medallion_silver", "medallion_gold")) {
    Write-Host "  Creating $lhName..." -ForegroundColor Gray
    $body = @{ displayName = $lhName; description = "Medallion $lhName" }
    $result = Invoke-FabricAPI -Method "POST" -Endpoint "/workspaces/$WorkspaceId/lakehouses" -Body $body -Token $token
    
    if ($result.Success) {
        $lakehouses[$lhName] = $result.Content.id
        Write-Host "    Created: $($result.Content.id)" -ForegroundColor Green
    } elseif ($result.Status -eq 409) {
        $itemsResult = Invoke-FabricAPI -Method "GET" -Endpoint "/workspaces/$WorkspaceId/items" -Token $token
        $existing = $itemsResult.Content.value | Where-Object { $_.displayName -eq $lhName -and $_.type -eq "Lakehouse" }
        if ($existing) {
            $lakehouses[$lhName] = $existing.id
            Write-Host "    Exists: $($existing.id)" -ForegroundColor Yellow
        }
    } else {
        Write-Host "    Failed: $($result.Status)" -ForegroundColor Red
    }
    Start-Sleep -Seconds $RATE_LIMIT_DELAY
}
Write-Host ""

Write-Host "Step 4: Deploying notebooks..." -ForegroundColor Yellow
$deployed = @{}

foreach ($nb in $notebooks | Sort-Object Order) {
    Write-Host "  $($nb.Order)/12: $($nb.DisplayName)..." -ForegroundColor Gray
    
    $notebookContent = [System.IO.File]::ReadAllText($nb.Path)
    $notebookBytes = [System.Text.Encoding]::UTF8.GetBytes($notebookContent)
    $base64Content = [System.Convert]::ToBase64String($notebookBytes)
    
    $body = @{
        displayName = $nb.DisplayName
        type = "Notebook"
        definition = @{
            format = "ipynb"
            parts = @(@{ path = "notebook-content.ipynb"; payload = $base64Content })
        }
    }
    
    $result = Invoke-FabricAPI -Method "POST" -Endpoint "/workspaces/$WorkspaceId/items" -Body $body -Token $token
    
    if ($result.Success) {
        $nbId = $result.Content.id
        $deployed[$nb.DisplayName] = $nbId
        
        $lhId = $lakehouses[$nb.Lakehouse]
        $bindBody = @{ defaultLakehouse = $lhId }
        Invoke-FabricAPI -Method "PATCH" -Endpoint "/workspaces/$WorkspaceId/items/$nbId" -Body $bindBody -Token $token | Out-Null
        
        Write-Host "    OK" -ForegroundColor Green
    } else {
        Write-Host "    Failed: $($result.Status)" -ForegroundColor Red
    }
    Start-Sleep -Seconds $RATE_LIMIT_DELAY
}
Write-Host ""

Write-Host "Step 5: Executing notebooks..." -ForegroundColor Yellow
$results = @()

foreach ($nb in $notebooks | Sort-Object Order) {
    $nbId = $deployed[$nb.DisplayName]
    if (-not $nbId) {
        Write-Host "  $($nb.Order)/12: $($nb.DisplayName) - SKIPPED (not deployed)" -ForegroundColor Yellow
        continue
    }
    
    Write-Host "  $($nb.Order)/12: $($nb.DisplayName)..." -ForegroundColor Gray
    $startTime = Get-Date
    
    $execResult = Invoke-FabricAPI -Method "POST" -Endpoint "/workspaces/$WorkspaceId/notebooks/$nbId/jobs/instances" -Token $token
    
    if (-not $execResult.Success) {
        Write-Host "    Failed to submit" -ForegroundColor Red
        $results += @{ Name = $nb.DisplayName; Status = "Failed"; Duration = 0 }
        continue
    }
    
    $jobId = $execResult.Content.id
    $elapsed = 0
    $status = "Unknown"
    
    while ($elapsed -lt $MAX_WAIT_TIME) {
        Start-Sleep -Seconds $POLL_INTERVAL
        $elapsed += $POLL_INTERVAL
        
        $statusResult = Invoke-FabricAPI -Method "GET" -Endpoint "/workspaces/$WorkspaceId/notebooks/$nbId/jobs/instances/$jobId" -Token $token
        
        if ($statusResult.Success) {
            $status = $statusResult.Content.status
            
            if ($status -eq "Completed") {
                $endTime = Get-Date
                $duration = ($endTime - $startTime).TotalSeconds
                Write-Host "    Completed in $([Math]::Round($duration, 2))s" -ForegroundColor Green
                $results += @{ Name = $nb.DisplayName; Status = "Success"; Duration = [Math]::Round($duration, 2) }
                break
            } elseif ($status -eq "Failed") {
                $endTime = Get-Date
                $duration = ($endTime - $startTime).TotalSeconds
                Write-Host "    Failed after $([Math]::Round($duration, 2))s" -ForegroundColor Red
                $results += @{ Name = $nb.DisplayName; Status = "Failed"; Duration = [Math]::Round($duration, 2); Error = $statusResult.Content.failureReason }
                break
            }
        }
    }
    
    if ($status -ne "Completed" -and $status -ne "Failed") {
        $endTime = Get-Date
        $duration = ($endTime - $startTime).TotalSeconds
        Write-Host "    Timeout after $([Math]::Round($duration, 2))s" -ForegroundColor Yellow
        $results += @{ Name = $nb.DisplayName; Status = "Timeout"; Duration = [Math]::Round($duration, 2) }
    }
    
    Start-Sleep -Seconds $RATE_LIMIT_DELAY
}
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "EXECUTION REPORT" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$success = ($results | Where-Object { $_.Status -eq "Success" }).Count
$failed = ($results | Where-Object { $_.Status -eq "Failed" }).Count
$timeout = ($results | Where-Object { $_.Status -eq "Timeout" }).Count
$totalTime = ($results | Measure-Object -Property Duration -Sum).Sum

Write-Host "Summary:"
Write-Host "  Total: $($results.Count)"
Write-Host "  Success: $success"
Write-Host "  Failed: $failed"
Write-Host "  Timeout: $timeout"
Write-Host "  Total Time: $([Math]::Round($totalTime, 2))s"
Write-Host ""

foreach ($r in $results) {
    $color = if ($r.Status -eq "Success") { "Green" } elseif ($r.Status -eq "Failed") { "Red" } else { "Yellow" }
    $durationStr = $r.Duration
    Write-Host "$($r.Name): $($r.Status) ($durationStr s)" -ForegroundColor $color
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Deployment Complete" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
