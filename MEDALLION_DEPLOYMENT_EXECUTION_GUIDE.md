# Medallion Architecture Deployment Execution Guide

**Status**: ✅ **READY FOR EXECUTION**  
**Generated**: 2026-03-31  
**Workspace ID**: 4850ec28-2ac1-4c80-a70d-977ab969085d  
**Target**: Microsoft Fabric  

---

## Executive Summary

A complete **Medallion Architecture** deployment package has been prepared and validated for Microsoft Fabric. All 12 notebooks have been verified, authentication has been configured, and deployment artifacts are ready.

| Component | Status | Details |
|-----------|--------|---------|
| **Notebooks** | ✅ Verified | All 12 notebooks exist (48,662 bytes total) |
| **Authentication** | ✅ Ready | Fabric API token configured |
| **Lakehouses** | ✅ Defined | 3 lakehouses (bronze, silver, gold) |
| **Deployment Plan** | ✅ Generated | JSON config with all parameters |
| **Orchestration** | ✅ Prepared | Python & PowerShell scripts ready |

---

## Deployment Architecture

### 📊 Medallion Layer Structure

```
┌─────────────────────────────────────────────────────────┐
│           MEDALLION ARCHITECTURE                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  GOLD (Analytics Layer)                                │
│  ├── 03_Gold_Aggregations                             │
│  ├── 03_Gold_Validation                               │
│  ├── 04_Master_Orchestration_Pipeline                 │
│  ├── 04_Pipeline_Monitoring                           │
│  └── 04_Log_Pipeline_Execution                        │
│                                                         │
│  SILVER (Transformation Layer)                         │
│  ├── 02_Quality_Rules_Engine                          │
│  ├── 02_Silver_Transform                              │
│  └── 02_Silver_Validation                             │
│                                                         │
│  BRONZE (Raw Data Layer)                               │
│  ├── 01_Bronze_Ingestion                              │
│  ├── 01_Bronze_Validation                             │
│  ├── 00_Generate_Sample_Data                          │
│  └── 00_Workspace_Setup                               │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 📁 Lakehouse Assignments

#### medallion_bronze (4 notebooks)
- **Purpose**: Raw data ingestion and validation
- **Retention Policy**: Write-optimized
- **Notebooks**:
  1. `00_Generate_Sample_Data` - Creates test data
  2. `00_Workspace_Setup` - Initializes workspace
  3. `01_Bronze_Ingestion` - Ingests raw data
  4. `01_Bronze_Validation` - Validates ingestion

#### medallion_silver (3 notebooks)
- **Purpose**: Data transformation and quality
- **Retention Policy**: Balanced read/write
- **Notebooks**:
  5. `02_Quality_Rules_Engine` - Applies quality rules
  6. `02_Silver_Transform` - Transforms data
  7. `02_Silver_Validation` - Validates transformations

#### medallion_gold (5 notebooks)
- **Purpose**: Business-ready analytics
- **Retention Policy**: Read-optimized
- **Notebooks**:
  8. `03_Gold_Aggregations` - Creates aggregations
  9. `03_Gold_Validation` - Validates aggregations
  10. `04_Master_Orchestration_Pipeline` - Orchestrates all
  11. `04_Pipeline_Monitoring` - Monitors execution
  12. `04_Log_Pipeline_Execution` - Logs metrics

---

## Deployment Execution Flow

### Phase 0: Setup (Lakehouses & Authentication)
```
[ ] 1. Verify Azure CLI authentication
[ ] 2. Create 3 lakehouses (POST requests)
[ ] 3. Verify lakehouses created
```
**Expected Duration**: 30 seconds  
**Rate Limit**: 3 seconds between API calls

### Phase 1: Notebook Deployment
```
[ ] 4. Deploy 12 notebooks to workspace
[ ] 5. Read .py files and encode to base64
[ ] 6. POST each notebook to Fabric
[ ] 7. Collect notebook IDs
```
**Expected Duration**: ~45 seconds (12 × 3s delay + overhead)  
**Rate Limit**: 3 seconds between API calls

### Phase 2: Notebook Binding
```
[ ] 8. Bind each notebook to correct lakehouse
[ ] 9. PATCH notebook properties
[ ] 10. Verify bindings established
```
**Expected Duration**: ~40 seconds  
**Rate Limit**: 3 seconds between API calls

### Phase 3: Sequential Execution
```
[ ] 11. Execute notebooks 1-12 in order
[ ] 12. Submit job for notebook 1
[ ] 13. Poll every 5s until completion
[ ] 14. Move to notebook 2
[ ] 15. Repeat for all 12 notebooks
```
**Expected Duration**: 45-120 minutes (variable based on notebook complexity)  
**Polling Interval**: 5 seconds  
**Timeout per Notebook**: 10 minutes

---

## Execution Instructions

### Option 1: Python Orchestrator (Recommended)

```bash
cd C:\Users\anujpandey
python medallion_deployment.py
```

**Advantages**:
- Full control and monitoring
- Comprehensive error handling
- Real-time status updates
- Automatic retries with exponential backoff
- Detailed execution report

**Output**:
- Console: Real-time execution status
- File: `MEDALLION_EXECUTION_REPORT.json` with full metrics
- Log: `medallion_deployment.log` with debugging info

### Option 2: PowerShell Deployment

```powershell
cd C:\Users\anujpandey
powershell -ExecutionPolicy Bypass -File deploy.ps1
```

**Advantages**:
- Native Windows integration
- Easy to customize
- Direct API control
- Built-in retry logic

### Option 3: Manual REST API Calls

Reference the deployment plan JSON for manual API construction:

```bash
curl -X POST https://api.powerbi.com/v1.0/myorg/workspaces/4850ec28-2ac1-4c80-a70d-977ab969085d/lakehouses \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"displayName":"medallion_bronze"}'
```

---

## Deployment Artifacts

### 📄 Configuration Files

| File | Purpose |
|------|---------|
| `MEDALLION_DEPLOYMENT_PLAN.json` | Machine-readable deployment specification |
| `medallion_deployment.py` | Python orchestrator script |
| `deploy.ps1` | PowerShell deployment script |
| `MEDALLION_DEPLOYMENT_SUMMARY.md` | Comprehensive documentation |
| `check_deployment_ready.ps1` | Pre-flight verification script |

### 📊 Notebook Files (12 total)

**Phase 0 - Setup (2)**
- `00_Generate_Sample_Data.py` (4.6 KB)
- `00_Workspace_Setup.py` (2.5 KB)

**Phase 1 - Bronze (2)**
- `01_Bronze_Ingestion.py` (2.8 KB)
- `01_Bronze_Validation.py` (3.8 KB)

**Phase 2 - Silver (3)**
- `02_Quality_Rules_Engine.py` (2.1 KB)
- `02_Silver_Transform.py` (3.5 KB)
- `02_Silver_Validation.py` (3.0 KB)

**Phase 3 - Gold (2)**
- `03_Gold_Aggregations.py` (4.1 KB)
- `03_Gold_Validation.py` (3.8 KB)

**Phase 4 - Orchestration (3)**
- `04_Master_Orchestration_Pipeline.py` (6.5 KB)
- `04_Pipeline_Monitoring.py` (3.6 KB)
- `04_Log_Pipeline_Execution.py` (3.4 KB)

---

## API Endpoints Used

### Lakehouses
```
POST /workspaces/{workspaceId}/lakehouses
```
- Creates medallion_bronze, medallion_silver, medallion_gold

### Notebooks
```
POST /workspaces/{workspaceId}/items
```
- Uploads each of the 12 notebooks
- Accepts base64-encoded content
- Returns notebook IDs for binding and execution

### Notebook Binding
```
PATCH /workspaces/{workspaceId}/items/{notebookId}
```
- Associates each notebook with its target lakehouse
- Sets `oneLakeLakehouseId` property

### Notebook Execution
```
POST /workspaces/{workspaceId}/notebooks/{notebookId}/jobs/instances
```
- Submits execution job
- Returns job ID for status polling

### Job Status
```
GET /workspaces/{workspaceId}/notebooks/{notebookId}/jobs/instances/{jobId}
```
- Polls job status (Submitted → Running → Completed)
- Retrieves execution output and metrics

---

## Authentication Configuration

### Configured Method: Azure CLI + Power BI Resource

```powershell
# Get token for Power BI (Fabric)
$token = az account get-access-token `
  --resource "https://analysis.windows.net/powerbi/api" `
  --query accessToken -o tsv
```

### Required Permissions
- **Workspace Access**: Admin or Editor role in the target workspace
- **Power BI Service**: Enabled in tenant
- **Fabric Admin**: Optional (for capacity management)

### No Hardcoded Credentials
✅ All authentication uses Azure CLI session token  
✅ No passwords or keys stored in scripts  
✅ Credentials expire after session  

---

## Execution Timeline

### Estimated Duration: 45-120 minutes

| Phase | Duration | Cumulative |
|-------|----------|-----------|
| Setup (Lakehouses) | 30s | 0:00:30 |
| Deployment (Notebooks) | 45s | 0:01:15 |
| Binding | 40s | 0:01:55 |
| **Execution (Sequential)** | 45-115min | 0:46:55 - 1:56:55 |

### Per-Notebook Typical Duration
- Setup notebooks: 1-2 minutes
- Bronze notebooks: 2-5 minutes each
- Silver notebooks: 3-8 minutes each (depends on data volume)
- Gold notebooks: 2-5 minutes each
- Orchestration: 1-3 minutes each

---

## Monitoring During Execution

### Real-Time Console Output
```
[*] Executing: 01_Bronze_Ingestion
    Status: Submitted
    Status: Running (5s elapsed)
    Status: Running (10s elapsed)
    Status: Completed (45s elapsed)
[OK] Execution completed in 45.23s
```

### Job Status Values
- `Submitted` - Job received, waiting to start
- `Running` - Actively executing
- `Completed` - Success
- `Failed` - Execution error
- `Aborted` - User or system canceled

### Polling Configuration
- **Interval**: 5 seconds between status checks
- **Timeout**: 10 minutes per notebook
- **Auto-Retry**: 3 attempts on transient errors

---

## Success Criteria

✅ **Deployment Success** = All 12 notebooks execute sequentially  
✅ **Execution Success** = Status = "Completed" for each notebook  
✅ **Data Flow Success** = Gold layer aggregations match Silver layer counts  

### Validation Queries (Run in Gold Lakehouse)

```sql
-- Check aggregation totals
SELECT COUNT(*) as record_count FROM medallion_gold_aggregations;

-- Verify data pipeline ran
SELECT MAX(execution_timestamp) as last_run FROM medallion_gold_pipeline_log;

-- Compare layer record counts
SELECT 'Bronze' as layer, COUNT(*) as count FROM medallion_bronze_raw
UNION ALL
SELECT 'Silver' as layer, COUNT(*) FROM medallion_silver_transformed
UNION ALL
SELECT 'Gold' as layer, COUNT(*) FROM medallion_gold_aggregations;
```

---

## Error Handling & Troubleshooting

### Common Issues

| Issue | Cause | Resolution |
|-------|-------|-----------|
| **Auth Failed** | Token expired | Re-run `az login` |
| **Lakehouse exists** | Already deployed | Script reuses existing |
| **Notebook timeout** | Slow execution | Check Fabric capacity |
| **Binding fails** | Lakehouse not found | Verify lakehouse created |
| **Job fails** | Code error in notebook | Check notebook error message |

### Debug Mode

```powershell
# Run with verbose logging
$DebugPreference = "Continue"
python medallion_deployment.py --verbose
```

### Collect Logs

```powershell
# All execution logs and reports
ls C:\Users\anujpandey\*medallion*.* | Format-Table Name, Length
cat C:\Users\anujpandey\medallion_deployment.log
```

---

## Post-Execution Steps

### 1. Verify Deployment
```powershell
# Check lakehouses in workspace
az fabric workspace show --workspace-id 4850ec28-2ac1-4c80-a70d-977ab969085d
```

### 2. Review Execution Report
```
Open: C:\Users\anujpandey\MEDALLION_EXECUTION_REPORT.json
```

### 3. Validate Data
- Open Fabric Workspace
- Navigate to each lakehouse
- Verify tables are populated with data

### 4. Test Business Logic
- Run validation queries in Gold layer
- Confirm aggregations match source data
- Verify data quality metrics

### 5. Document Results
- Archive execution logs
- Record execution timestamps
- Note any warnings or errors
- Update runbooks with lessons learned

---

## Performance Tuning

### Optimize Notebook Execution

1. **Increase Capacity SKU** if notebooks timeout
   - Bronze: F2 (2 CUs) sufficient for setup
   - Silver: F4-F8 (4-8 CUs) for transformations
   - Gold: F4+ (4+ CUs) for aggregations

2. **Parallel Bronze Notebooks**
   - Setup notebooks can run in parallel (if needed)
   - Adjust orchestration logic

3. **Partition Silver Transformations**
   - If data volume is large, consider partitioning
   - Allows parallel execution within phase

4. **Incremental Processing**
   - Add watermarks to notebooks
   - Process only new/changed data after first run

---

## Rollback Procedure

### If Deployment Fails

```powershell
# Option 1: Delete entire workspace and recreate
az fabric workspace delete --workspace-id 4850ec28-2ac1-4c80-a70d-977ab969085d

# Option 2: Remove only failed notebooks
az fabric item delete --workspace-id 4850ec28-2ac1-4c80-a70d-977ab969085d --item-id {notebookId}

# Option 3: Re-run from failed point
# Edit medallion_deployment.py to start at specific notebook
```

---

## Next Steps

### Immediate (Before Execution)
1. ✅ Review this guide
2. ✅ Verify workspace access
3. ✅ Check Azure CLI authentication
4. ✅ Confirm Fabric capacity available

### Execution
1. Run: `python medallion_deployment.py`
2. Monitor console output
3. Review real-time status updates
4. Wait for completion (45-120 minutes)

### Post-Execution
1. ✅ Review `MEDALLION_EXECUTION_REPORT.json`
2. ✅ Verify data in lakehouses
3. ✅ Archive execution logs
4. ✅ Document any customizations

---

## Support & Resources

### Documentation
- `MEDALLION_DEPLOYMENT_PLAN.json` - Deployment specification
- `MEDALLION_DEPLOYMENT_SUMMARY.md` - Architecture overview
- Each notebook includes inline documentation

### Fabric REST API Reference
- [Notebooks API](https://learn.microsoft.com/en-us/rest/api/fabric/notebooks)
- [Lakehouses API](https://learn.microsoft.com/en-us/rest/api/fabric/lakehouses)
- [Jobs API](https://learn.microsoft.com/en-us/rest/api/fabric/jobs)

### Troubleshooting
- Check notebook cell outputs for error details
- Review Fabric workspace activity log
- Enable Fabric admin telemetry for diagnostics

---

## Deployment Status Checklist

### Pre-Deployment
- [x] All 12 notebooks verified
- [x] Notebook files readable
- [x] Authentication configured
- [x] Deployment plan generated
- [x] API endpoints documented
- [x] Rate limiting configured
- [x] Execution sequence defined

### During Deployment
- [ ] Azure CLI token obtained
- [ ] Workspace access confirmed
- [ ] 3 Lakehouses created
- [ ] 12 Notebooks deployed
- [ ] Notebook bindings established
- [ ] Execution started (Notebook 1)
- [ ] Sequential execution monitoring

### Post-Deployment
- [ ] All 12 notebooks executed
- [ ] Execution report generated
- [ ] No critical errors found
- [ ] Data verified in lakehouses
- [ ] Performance metrics collected
- [ ] Logs archived

---

## Conclusion

The Medallion Architecture deployment package is **complete and ready for execution**. All prerequisites have been validated, authentication is configured, and orchestration scripts are prepared.

**To begin deployment:**
```bash
python C:\Users\anujpandey\medallion_deployment.py
```

**Estimated completion**: 45-120 minutes  
**Status**: 🟢 **GO FOR LAUNCH**

---

Generated: 2026-03-31  
Workspace: 4850ec28-2ac1-4c80-a70d-977ab969085d  
Status: ✅ Ready for Execution
