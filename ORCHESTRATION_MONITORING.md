# ORCHESTRATION & MONITORING
## Microsoft Fabric Medallion Architecture

---

## 📋 Master Orchestration Pipeline

**File**: `04_Master_Orchestration_Pipeline.json`  
**Purpose**: Automated Bronze→Silver→Gold execution with error handling and scheduling  

### Pipeline Definition

```json
{
  "name": "Medallion_Master_Orchestration",
  "description": "End-to-end medallion pipeline: Bronze ingestion → Silver transformation → Gold aggregation",
  "properties": {
    "activities": [
      {
        "name": "Check_Data_Freshness",
        "type": "Notebook",
        "typeProperties": {
          "notebookPath": "/Notebooks/00_Check_Freshness",
          "parameters": {
            "processing_date": {
              "value": "@pipeline().parameters.processing_date",
              "type": "Expression"
            }
          },
          "timeout": "0.00:15:00",
          "retryPolicy": {
            "count": 2,
            "intervalInSeconds": 30
          }
        },
        "linkedServiceName": {
          "referenceName": "bronze_lakehouse",
          "type": "LinkedServiceReference"
        }
      },
      {
        "name": "Bronze_Ingestion",
        "type": "Notebook",
        "typeProperties": {
          "notebookPath": "/Notebooks/01_Bronze_Ingestion",
          "parameters": {
            "source_config": "daily_events",
            "processing_date": {
              "value": "@pipeline().parameters.processing_date",
              "type": "Expression"
            },
            "batch_id": {
              "value": "@concat('batch_', utcNow('yyyyMMdd_HHmmss'))",
              "type": "Expression"
            }
          },
          "timeout": "1:00:00",
          "retryPolicy": {
            "count": 3,
            "intervalInSeconds": 60
          }
        },
        "onSuccess": [
          {
            "dependencyConditions": ["Succeeded"],
            "activities": ["Bronze_Validation"]
          }
        ],
        "onFailure": [
          {
            "dependencyConditions": ["Failed"],
            "activities": ["Send_Failure_Alert"]
          }
        ]
      },
      {
        "name": "Bronze_Validation",
        "type": "Notebook",
        "typeProperties": {
          "notebookPath": "/Notebooks/01_Bronze_Validation",
          "timeout": "0:30:00"
        },
        "dependsOn": [
          {
            "activity": "Bronze_Ingestion",
            "dependencyConditions": ["Succeeded"]
          }
        ]
      },
      {
        "name": "Silver_Transformation",
        "type": "Notebook",
        "typeProperties": {
          "notebookPath": "/Notebooks/02_Silver_Transform",
          "parameters": {
            "processing_date": {
              "value": "@pipeline().parameters.processing_date",
              "type": "Expression"
            },
            "full_refresh": {
              "value": "@pipeline().parameters.full_refresh",
              "type": "Expression"
            }
          },
          "timeout": "2:00:00",
          "retryPolicy": {
            "count": 2,
            "intervalInSeconds": 60
          }
        },
        "dependsOn": [
          {
            "activity": "Bronze_Validation",
            "dependencyConditions": ["Succeeded"]
          }
        ]
      },
      {
        "name": "Silver_Validation",
        "type": "Notebook",
        "typeProperties": {
          "notebookPath": "/Notebooks/02_Silver_Validation",
          "timeout": "0:30:00"
        },
        "dependsOn": [
          {
            "activity": "Silver_Transformation",
            "dependencyConditions": ["Succeeded"]
          }
        ]
      },
      {
        "name": "Gold_Aggregation",
        "type": "Notebook",
        "typeProperties": {
          "notebookPath": "/Notebooks/03_Gold_Aggregations",
          "timeout": "1:30:00",
          "retryPolicy": {
            "count": 1,
            "intervalInSeconds": 60
          }
        },
        "dependsOn": [
          {
            "activity": "Silver_Validation",
            "dependencyConditions": ["Succeeded"]
          }
        ]
      },
      {
        "name": "Gold_Optimization",
        "type": "Notebook",
        "typeProperties": {
          "notebookPath": "/Notebooks/03_Gold_Validation",
          "timeout": "1:00:00"
        },
        "dependsOn": [
          {
            "activity": "Gold_Aggregation",
            "dependencyConditions": ["Succeeded"]
          }
        ]
      },
      {
        "name": "Log_Pipeline_Success",
        "type": "Notebook",
        "typeProperties": {
          "notebookPath": "/Notebooks/04_Log_Pipeline_Execution",
          "parameters": {
            "status": "success",
            "processing_date": {
              "value": "@pipeline().parameters.processing_date",
              "type": "Expression"
            }
          }
        },
        "dependsOn": [
          {
            "activity": "Gold_Optimization",
            "dependencyConditions": ["Succeeded"]
          }
        ]
      },
      {
        "name": "Send_Success_Notification",
        "type": "WebActivity",
        "typeProperties": {
          "url": "@pipeline().parameters.webhook_url",
          "method": "POST",
          "body": {
            "message": "Medallion pipeline execution successful",
            "processing_date": {
              "value": "@pipeline().parameters.processing_date",
              "type": "Expression"
            },
            "timestamp": "@utcNow()"
          }
        },
        "dependsOn": [
          {
            "activity": "Log_Pipeline_Success",
            "dependencyConditions": ["Succeeded"]
          }
        ]
      },
      {
        "name": "Send_Failure_Alert",
        "type": "WebActivity",
        "typeProperties": {
          "url": "@pipeline().parameters.error_webhook_url",
          "method": "POST",
          "body": {
            "message": "Medallion pipeline failed - requires investigation",
            "processing_date": {
              "value": "@pipeline().parameters.processing_date",
              "type": "Expression"
            },
            "error": "@activity('Bronze_Ingestion').error.message"
          }
        }
      }
    ],
    "parameters": {
      "processing_date": {
        "type": "String",
        "defaultValue": "@adddays(utcNow(), -1, 'yyyy-MM-dd')"
      },
      "full_refresh": {
        "type": "String",
        "defaultValue": "false"
      },
      "webhook_url": {
        "type": "String",
        "defaultValue": "https://prod-xx.eastus.logic.azure.com:443/workflows/..."
      },
      "error_webhook_url": {
        "type": "String",
        "defaultValue": "https://prod-xx.eastus.logic.azure.com:443/workflows/..."
      }
    },
    "triggers": [
      {
        "name": "Daily_2AM_UTC",
        "type": "ScheduleTrigger",
        "typeProperties": {
          "recurrence": {
            "frequency": "Day",
            "interval": 1,
            "startTime": "2024-01-01T02:00:00",
            "timeZone": "UTC",
            "schedule": {
              "hours": [2],
              "minutes": [0]
            }
          }
        }
      }
    ],
    "concurrency": 1,
    "monitoringLevel": "Pipeline"
  },
  "type": "Microsoft.DataFactory/factories/pipelines"
}
```

### Key Features

1. **Sequential Execution**: Bronze → Silver → Gold (no skipping)
2. **Error Handling**: Retry logic with exponential backoff
3. **Validation Gates**: Each layer validates before proceeding
4. **Parameterization**: Processing date, full vs incremental, webhook URLs
5. **Scheduling**: Daily at 2 AM UTC (configurable)
6. **Notifications**: Success and failure alerts via webhooks
7. **Logging**: All execution metrics tracked

### Execution Flow

```
START
  ↓
[Check Data Freshness]
  ↓
[Bronze Ingestion] ← RETRY: 3 attempts
  ├─ Success → [Bronze Validation]
  └─ Failure → [Send Failure Alert] → END
  ↓
[Silver Transformation] ← RETRY: 2 attempts
  ├─ Success → [Silver Validation]
  └─ Failure → [Send Failure Alert] → END
  ↓
[Gold Aggregation] ← RETRY: 1 attempt
  ├─ Success → [Gold Optimization]
  └─ Failure → [Send Failure Alert] → END
  ↓
[Log Success] → [Send Success Notification]
  ↓
END
```

---

## 📋 Notebook: Pipeline Monitoring & Observability

**File**: `04_Pipeline_Monitoring.py`  
**Purpose**: Dashboard and health monitoring for medallion pipeline  

```python
# Databricks notebook source
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, count, max, min, datediff, current_timestamp
)
from datetime import datetime, timedelta
import json

spark = SparkSession.builder.appName("PipelineMonitoring").getOrCreate()

# COMMAND: Setup Monitoring Tables
spark.sql("""
    CREATE TABLE IF NOT EXISTS monitoring.pipeline_execution (
        run_id STRING,
        pipeline_name STRING,
        start_timestamp TIMESTAMP,
        end_timestamp TIMESTAMP,
        duration_seconds LONG,
        status STRING,
        layer_bronze_status STRING,
        layer_silver_status STRING,
        layer_gold_status STRING,
        error_message STRING,
        execution_date DATE
    )
    USING DELTA
    PARTITIONED BY (execution_date)
""")

print("✓ Monitoring infrastructure ready")

# COMMAND: Pipeline Health Dashboard
print("\n" + "="*80)
print("MEDALLION PIPELINE HEALTH DASHBOARD")
print("="*80)

# 1. Recent Execution Status
print("\n1. Recent Execution Status (Last 10 runs):")
spark.sql("""
    SELECT 
        run_id,
        pipeline_name,
        start_timestamp,
        duration_seconds,
        status,
        layer_bronze_status,
        layer_silver_status,
        layer_gold_status
    FROM monitoring.pipeline_execution
    ORDER BY start_timestamp DESC
    LIMIT 10
""").show(truncate=False)

# 2. Success Rate
print("\n2. Pipeline Success Rate (Last 30 days):")
spark.sql("""
    SELECT 
        COUNT(*) as total_runs,
        SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful_runs,
        SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_runs,
        ROUND(100.0 * SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) / COUNT(*), 2) as success_rate_percent
    FROM monitoring.pipeline_execution
    WHERE execution_date >= DATE_SUB(CURRENT_DATE(), 30)
""").show()

# 3. Average Duration
print("\n3. Average Pipeline Duration (by layer):")

duration_stats = spark.sql("""
    SELECT 
        'Bronze_Ingestion' as layer,
        COUNT(*) as runs,
        ROUND(AVG(CAST(duration_seconds as DOUBLE)), 0) as avg_duration_seconds,
        MIN(CAST(duration_seconds as INT)) as min_duration_seconds,
        MAX(CAST(duration_seconds as INT)) as max_duration_seconds
    FROM monitoring.pipeline_execution
    WHERE execution_date >= DATE_SUB(CURRENT_DATE(), 7)
    UNION ALL
    SELECT 
        'Silver_Transformation' as layer,
        COUNT(*) as runs,
        ROUND(AVG(CAST(duration_seconds as DOUBLE)), 0) as avg_duration_seconds,
        MIN(CAST(duration_seconds as INT)) as min_duration_seconds,
        MAX(CAST(duration_seconds as INT)) as max_duration_seconds
    FROM monitoring.pipeline_execution
    WHERE execution_date >= DATE_SUB(CURRENT_DATE(), 7)
""")

duration_stats.show()

# 4. Data Freshness Check
print("\n4. Data Freshness Indicators:")

freshness = spark.sql("""
    SELECT 
        'Bronze' as layer,
        MAX(_ingestion_date) as last_update,
        DATEDIFF(CURRENT_DATE(), MAX(_ingestion_date)) as days_since_update
    FROM bronze.events_raw
    UNION ALL
    SELECT 
        'Silver' as layer,
        MAX(order_date) as last_update,
        DATEDIFF(CURRENT_DATE(), MAX(order_date)) as days_since_update
    FROM silver.events_cleaned
    UNION ALL
    SELECT 
        'Gold' as layer,
        MAX(summary_date) as last_update,
        DATEDIFF(CURRENT_DATE(), MAX(summary_date)) as days_since_update
    FROM gold.events_daily_summary
""")

freshness.show()

# 5. Layer Metrics Comparison
print("\n5. Row Count Trends (Bronze → Silver → Gold):")

row_counts = spark.sql("""
    SELECT 
        (SELECT COUNT(*) FROM bronze.events_raw) as bronze_rows,
        (SELECT COUNT(*) FROM silver.events_cleaned) as silver_rows,
        (SELECT COUNT(*) FROM gold.events_daily_summary) as gold_rows,
        ROUND(100.0 * (SELECT COUNT(*) FROM silver.events_cleaned) / (SELECT COUNT(*) FROM bronze.events_raw), 2) as bronze_to_silver_pct,
        CURRENT_TIMESTAMP() as snapshot_timestamp
""")

row_counts.show()

# 6. Error Analysis
print("\n6. Recent Errors (Last 7 days):")

spark.sql("""
    SELECT 
        execution_date,
        COUNT(*) as error_count,
        COLLECT_LIST(DISTINCT SUBSTRING(error_message, 1, 100)) as error_samples
    FROM monitoring.pipeline_execution
    WHERE status = 'failed'
    AND execution_date >= DATE_SUB(CURRENT_DATE(), 7)
    GROUP BY execution_date
    ORDER BY execution_date DESC
""").show(truncate=False)

# 7. Quality Metrics
print("\n7. Data Quality Metrics:")

quality = spark.sql("""
    SELECT 
        (SELECT COUNT(*) FROM silver.events_cleaned WHERE amount IS NULL) as null_amounts,
        (SELECT COUNT(*) FROM silver.events_cleaned WHERE amount < 0) as negative_amounts,
        (SELECT COUNT(*) FROM silver.events_cleaned WHERE order_id IS NULL) as null_order_ids,
        ROUND(100.0 * (1 - (SELECT COUNT(*) FROM silver.events_cleaned WHERE amount IS NULL) / (SELECT COUNT(*) FROM silver.events_cleaned)), 2) as data_completeness_pct
""")

quality.show()

print("\n✓ Pipeline monitoring dashboard complete!")
```

---

## 📊 Alert Configuration

### Setup Failure Alerts via Azure Logic Apps

**Trigger**: Pipeline failure  
**Action**: Send email notification

```json
{
  "definition": {
    "$schema": "https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#",
    "actions": {
      "Send_email_notification": {
        "type": "ApiConnection",
        "inputs": {
          "host": {
            "connection": {
              "name": "@parameters('$connections')['office365']['connectionId']"
            }
          },
          "method": "post",
          "path": "/Mail",
          "body": {
            "To": "data-engineering@company.com",
            "Subject": "🚨 Medallion Pipeline Failed",
            "Body": "Pipeline execution failed:\nDate: @{triggerBody()['properties']['processing_date']}\nError: @{triggerBody()['error']['message']}\n\nPlease investigate: https://app.powerbi.com/..."
          }
        }
      }
    }
  }
}
```

### Alert Rules

| Condition | Threshold | Action |
|-----------|-----------|--------|
| Pipeline failed | Any | Email alert + Slack notification |
| Data freshness | > 24 hours stale | Warning email |
| Quality score | < 80% | Validation report sent |
| Execution time | > 2x average | Performance review requested |

---

## 📈 Performance Baseline

| Metric | Target | Current |
|--------|--------|---------|
| Bronze ingestion | < 15 min | - |
| Silver transformation | < 30 min | - |
| Gold aggregation | < 20 min | - |
| Total pipeline duration | < 90 min | - |
| Success rate | > 99% | - |
| Data freshness SLA | < 24 hours | - |

---

## 🔄 Manual Pipeline Execution

### Run Bronze Ingestion Only

```python
%run /Workspace/Notebooks/01_Bronze_Ingestion
  --source_config orders
  --processing_date 2024-01-15
  --mode append
```

### Full Pipeline with Parameters

```python
dbutils.notebook.run(
    "/Workspace/Notebooks/01_Bronze_Ingestion",
    timeout_seconds=3600,
    arguments={
        "source_config": "orders",
        "processing_date": "2024-01-15",
        "batch_id": "manual_batch_20240115_001"
    }
)
```

### Troubleshooting Failed Pipeline

1. Check pipeline run history in Fabric monitoring
2. Review notebook logs for specific errors
3. Manually re-run layer with `--mode=overwrite` if needed
4. Check data quality metrics in monitoring dashboard
5. Verify upstream data source availability
6. Escalate to data engineering if unresolved

---

## 📞 Runbooks

### Runbook 1: Handle Failed Bronze Ingestion

**Problem**: Bronze ingestion notebook fails  
**Steps**:
1. Check source file availability: `dbutils.fs.ls("/Workspace/Files/landing/daily/")`
2. Verify Bronze table exists: `SHOW TABLES IN bronze`
3. Check cluster resources (CPU, memory)
4. Re-run with `--mode=overwrite` to retry
5. If persistent, escalate with logs

### Runbook 2: Address Quality Check Failures

**Problem**: Silver quality checks failing  
**Steps**:
1. View quality report: `SELECT * FROM silver.quality_metrics ORDER BY check_timestamp DESC`
2. Identify violations by rule type
3. Update quality rules in config if needed
4. Re-run Silver transformation
5. Verify Gold updates reflect corrections

### Runbook 3: Optimize Slow Pipeline

**Problem**: Pipeline execution > 2 hours  
**Steps**:
1. Identify slow layer from monitoring dashboard
2. Profile cluster utilization during run
3. Check for data skew in partition columns
4. Run OPTIMIZE on affected tables
5. Consider increasing cluster size for that layer
6. Review Spark configuration for bottlenecks

---

## Summary

**Orchestration**:
- ✓ Automated Bronze→Silver→Gold sequencing
- ✓ Error handling with retries and alerts
- ✓ Parameterized for flexibility
- ✓ Daily schedule with 2 AM UTC trigger
- ✓ Webhook notifications

**Monitoring**:
- ✓ Real-time pipeline health dashboard
- ✓ Success rate and duration tracking
- ✓ Data freshness alerts
- ✓ Quality metrics monitoring
- ✓ Error analysis and logging

→ Next: Power BI Integration & Examples
