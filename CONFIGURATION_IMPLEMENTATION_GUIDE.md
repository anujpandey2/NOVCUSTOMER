# CONFIGURATION TEMPLATES & IMPLEMENTATION GUIDE
## Microsoft Fabric Medallion Architecture

---

## 📝 Configuration Templates

### Bronze Config: `bronze_config.json`

```json
{
  "metadata": {
    "version": "1.0",
    "description": "Bronze layer ingestion configuration",
    "last_updated": "2024-01-15",
    "owner": "data-engineering@company.com"
  },
  "sources": {
    "default_events": {
      "type": "csv",
      "path": "/Workspace/Files/landing/daily/orders_sample.csv",
      "system_name": "ecommerce_system",
      "system_type": "OLTP",
      "bronze_table": "events_raw",
      "partition_col": "ingestion_date",
      "description": "Daily order events from e-commerce platform",
      "sla_freshness_hours": 24,
      "required_columns": ["order_id", "customer_id", "order_date", "order_amount"],
      "expected_columns": 5,
      "column_types": {
        "order_id": "string",
        "customer_id": "string",
        "order_date": "date",
        "order_amount": "decimal(10,2)",
        "currency": "string",
        "status": "string"
      },
      "sampling": {
        "enabled": false,
        "fraction": 0.1
      },
      "error_handling": "capture_and_flag",
      "contact": "orders-data-owner@company.com"
    },
    "sensors_iot": {
      "type": "csv",
      "path": "/Workspace/Files/landing/daily/iot_sensors_sample.csv",
      "system_name": "iot_platform",
      "system_type": "IoT",
      "bronze_table": "sensor_readings_raw",
      "partition_col": "ingestion_date",
      "description": "Hourly sensor readings from manufacturing plant",
      "sla_freshness_hours": 1,
      "required_columns": ["sensor_id", "timestamp", "temperature", "humidity"],
      "expected_columns": 7,
      "sampling": {
        "enabled": true,
        "fraction": 0.5
      },
      "contact": "iot-platform@company.com"
    },
    "customer_master": {
      "type": "csv",
      "path": "/Workspace/Files/landing/daily/customers_sample.csv",
      "system_name": "crm_system",
      "system_type": "CRM",
      "bronze_table": "customers_raw",
      "partition_col": "ingestion_date",
      "description": "Customer master data from CRM",
      "sla_freshness_hours": 6,
      "required_columns": ["customer_id", "customer_name"],
      "contact": "crm-data-team@company.com"
    }
  },
  "settings": {
    "default_mode": "append",
    "enable_error_logging": true,
    "enable_schema_inference": true,
    "retention_days": 90,
    "compression": "snappy",
    "optimize_write": false,
    "compaction_schedule": "manual",
    "max_parallel_ingestions": 3,
    "timeout_minutes": 60
  }
}
```

### Silver Config: `silver_config.json`

```json
{
  "metadata": {
    "version": "1.0",
    "description": "Silver layer transformation and quality configuration",
    "last_updated": "2024-01-15"
  },
  "quality_rules": {
    "no_nulls": {
      "enabled": true,
      "events_raw": ["order_id", "customer_id", "order_date"],
      "severity": "error",
      "action": "drop_row"
    },
    "unique_keys": {
      "enabled": true,
      "events_raw": {
        "key_columns": ["order_id", "order_date"],
        "keep": "latest"
      },
      "severity": "error"
    },
    "range_checks": {
      "enabled": true,
      "rules": [
        {
          "column": "order_amount",
          "min": 0,
          "max": 999999,
          "severity": "warning",
          "action": "flag_for_review"
        },
        {
          "column": "age",
          "min": 18,
          "max": 120,
          "severity": "error",
          "action": "drop_row"
        }
      ]
    },
    "pattern_checks": {
      "enabled": true,
      "rules": [
        {
          "column": "email",
          "pattern": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$",
          "severity": "warning"
        }
      ]
    }
  },
  "transformations": {
    "events_raw": {
      "source_bronze": "bronze.events_raw",
      "target_silver": "silver.events_cleaned",
      "partition_column": "order_date",
      "scd_type": 1,
      "derived_columns": {
        "order_year": "YEAR(order_date)",
        "order_month": "MONTH(order_date)",
        "order_week": "WEEKOFYEAR(order_date)",
        "is_high_value": "order_amount > 1000",
        "is_refunded": "LOWER(status) = 'refunded'"
      },
      "column_mappings": {
        "order_id": "order_id",
        "customer_id": "customer_id",
        "order_date": "order_date",
        "order_amount": "amount",
        "currency": "currency",
        "status": "status"
      },
      "description": "Clean and validate order events from Bronze"
    }
  },
  "settings": {
    "enable_deduplication": true,
    "enable_null_handling": true,
    "enable_data_profiling": true,
    "retention_years": 3,
    "optimize_write": false,
    "run_statistics": true,
    "schedule_frequency": "daily",
    "schedule_time": "01:00 UTC"
  }
}
```

### Gold Config: `gold_config.json`

```json
{
  "metadata": {
    "version": "1.0",
    "description": "Gold layer analytics aggregations configuration",
    "last_updated": "2024-01-15"
  },
  "aggregations": {
    "daily_summary": {
      "source_table": "silver.events_cleaned",
      "target_table": "gold.events_daily_summary",
      "grain": "day",
      "partition_columns": ["summary_date"],
      "metrics": {
        "order_count": {
          "expression": "COUNT(*)",
          "data_type": "long"
        },
        "unique_customers": {
          "expression": "COUNT(DISTINCT customer_id)",
          "data_type": "long"
        },
        "total_amount": {
          "expression": "SUM(amount)",
          "data_type": "decimal(15,2)"
        },
        "avg_amount": {
          "expression": "AVG(amount)",
          "data_type": "decimal(15,2)"
        },
        "high_value_orders": {
          "expression": "SUM(CASE WHEN is_high_value THEN 1 ELSE 0 END)",
          "data_type": "long"
        }
      },
      "group_by": ["order_date", "status"],
      "description": "Daily order metrics aggregated by status"
    },
    "customer_segments": {
      "source_table": "silver.events_cleaned",
      "target_table": "gold.customer_segments",
      "grain": "customer",
      "metrics": {
        "lifetime_value": {
          "expression": "SUM(amount)",
          "data_type": "decimal(15,2)"
        },
        "order_count": {
          "expression": "COUNT(*)",
          "data_type": "long"
        },
        "avg_order_value": {
          "expression": "AVG(amount)",
          "data_type": "decimal(15,2)"
        }
      },
      "segments": [
        {
          "name": "VIP",
          "condition": "SUM(amount) > 5000"
        },
        {
          "name": "High-Value",
          "condition": "SUM(amount) > 1000"
        },
        {
          "name": "Regular",
          "condition": "SUM(amount) > 100"
        },
        {
          "name": "New",
          "condition": "SUM(amount) <= 100"
        }
      ],
      "description": "Customer segmentation based on lifetime value"
    },
    "monthly_trend": {
      "source_table": "silver.events_cleaned",
      "target_table": "gold.monthly_trend_analysis",
      "grain": "month",
      "metrics": {
        "order_count": "COUNT(*)",
        "total_revenue": "SUM(amount)",
        "avg_order_value": "AVG(amount)",
        "unique_customers": "COUNT(DISTINCT customer_id)"
      },
      "window_functions": {
        "prev_month_revenue": "LAG(total_revenue) OVER (ORDER BY month_key)",
        "mom_growth_pct": "(total_revenue - prev_month_revenue) / prev_month_revenue * 100"
      },
      "description": "Month-over-month trend analysis"
    }
  },
  "optimization": {
    "v_order": true,
    "optimize_write": true,
    "optimize_write_bin_size": "1gb",
    "zorder_columns": ["summary_date", "order_status"],
    "target_file_size": "1gb",
    "vacuum_retention_hours": 168,
    "schedule_optimize": "daily",
    "optimize_time": "03:00 UTC"
  },
  "settings": {
    "enable_materialized_views": true,
    "cache_results": true,
    "cache_ttl_hours": 24,
    "schedule_frequency": "daily",
    "schedule_time": "02:00 UTC"
  }
}
```

### Orchestration Config: `orchestration_config.json`

```json
{
  "pipeline": {
    "name": "Medallion_Master_Orchestration",
    "description": "Bronze → Silver → Gold automated flow",
    "version": "1.0"
  },
  "schedule": {
    "trigger_type": "ScheduleTrigger",
    "frequency": "Daily",
    "hour": 2,
    "minute": 0,
    "timezone": "UTC",
    "description": "Runs every day at 2:00 AM UTC"
  },
  "parameters": {
    "processing_date": {
      "default": "@adddays(utcNow(), -1, 'yyyy-MM-dd')",
      "type": "string",
      "description": "Date to process (defaults to yesterday)"
    },
    "full_refresh": {
      "default": "false",
      "type": "string",
      "allowed_values": ["true", "false"],
      "description": "Full refresh or incremental"
    },
    "cluster_size": {
      "default": "standard",
      "type": "string",
      "allowed_values": ["standard", "large", "xlarge"],
      "description": "Spark cluster size"
    }
  },
  "stages": [
    {
      "stage": 1,
      "name": "Bronze_Ingestion",
      "notebook": "/Workspace/Notebooks/01_Bronze_Ingestion",
      "timeout_minutes": 60,
      "retry_count": 3,
      "retry_wait_seconds": 60,
      "dependencies": []
    },
    {
      "stage": 2,
      "name": "Bronze_Validation",
      "notebook": "/Workspace/Notebooks/01_Bronze_Validation",
      "timeout_minutes": 30,
      "retry_count": 1,
      "dependencies": ["Bronze_Ingestion"]
    },
    {
      "stage": 3,
      "name": "Silver_Transformation",
      "notebook": "/Workspace/Notebooks/02_Silver_Transform",
      "timeout_minutes": 120,
      "retry_count": 2,
      "retry_wait_seconds": 60,
      "dependencies": ["Bronze_Validation"]
    },
    {
      "stage": 4,
      "name": "Silver_Validation",
      "notebook": "/Workspace/Notebooks/02_Silver_Validation",
      "timeout_minutes": 30,
      "retry_count": 1,
      "dependencies": ["Silver_Transformation"]
    },
    {
      "stage": 5,
      "name": "Gold_Aggregation",
      "notebook": "/Workspace/Notebooks/03_Gold_Aggregations",
      "timeout_minutes": 90,
      "retry_count": 1,
      "dependencies": ["Silver_Validation"]
    },
    {
      "stage": 6,
      "name": "Gold_Optimization",
      "notebook": "/Workspace/Notebooks/03_Gold_Validation",
      "timeout_minutes": 60,
      "retry_count": 0,
      "dependencies": ["Gold_Aggregation"]
    },
    {
      "stage": 7,
      "name": "Pipeline_Monitoring",
      "notebook": "/Workspace/Notebooks/04_Pipeline_Monitoring",
      "timeout_minutes": 15,
      "retry_count": 0,
      "dependencies": ["Gold_Optimization"]
    }
  ],
  "notifications": {
    "on_success": {
      "enabled": true,
      "webhook_url": "https://prod-xx.logic.azure.com/workflows/success",
      "teams_channel": "#data-engineering"
    },
    "on_failure": {
      "enabled": true,
      "webhook_url": "https://prod-xx.logic.azure.com/workflows/failure",
      "email": ["data-engineering@company.com"],
      "teams_channel": "#alerts"
    }
  },
  "monitoring": {
    "enable_logging": true,
    "log_level": "INFO",
    "track_lineage": true,
    "track_data_quality": true,
    "alert_on_sla_breach": true,
    "freshness_sla_hours": 24
  }
}
```

---

## 🚀 Step-by-Step Implementation Guide

### Phase 1: Preparation (1-2 hours)

**1.1 Access & Permissions**
```powershell
# Verify workspace access
az login
$workspaceId = "4850ec28-2ac1-4c80-a70d-977ab969085d"
az rest --method get --resource "https://api.fabric.microsoft.com" \
  --url "https://api.fabric.microsoft.com/v1/workspaces/$workspaceId" \
  --query properties.name
```

**1.2 Create Directory Structure**
```python
# In notebook: 00_Workspace_Setup.py
# Create folder structure in workspace
folders = [
    "/Workspace/Files/config/",
    "/Workspace/Files/landing/daily/",
    "/Workspace/Files/archive/",
    "/Workspace/Files/logs/",
    "/Workspace/Notebooks/",
    "/Workspace/Notebooks/Phase0_Setup/",
    "/Workspace/Notebooks/Phase1_Bronze/",
    "/Workspace/Notebooks/Phase2_Silver/",
    "/Workspace/Notebooks/Phase3_Gold/",
    "/Workspace/Notebooks/Phase4_Orchestration/"
]

for folder in folders:
    try:
        dbutils.fs.ls(folder)
        print(f"✓ {folder} exists")
    except:
        dbutils.fs.mkdirs(folder)
        print(f"✓ Created {folder}")
```

**1.3 Upload Configuration Files**
```bash
# Upload JSON configs to Files/config/
dbutils.fs.put("/Workspace/Files/config/bronze_config.json", bronze_config_json, overwrite=True)
dbutils.fs.put("/Workspace/Files/config/silver_config.json", silver_config_json, overwrite=True)
dbutils.fs.put("/Workspace/Files/config/gold_config.json", gold_config_json, overwrite=True)
dbutils.fs.put("/Workspace/Files/config/orchestration_config.json", orch_config_json, overwrite=True)
```

### Phase 2: Create Lakehouses (30 minutes)

**2.1 Create Bronze Lakehouse**
```powershell
$createBronzeLH = @{
    displayName = "medallion_bronze"
    type = "Lakehouse"
} | ConvertTo-Json

$bronzeLH = curl -X POST \
    -H "Authorization: Bearer $token" \
    "https://api.fabric.microsoft.com/v1/workspaces/$workspaceId/items" \
    -d $createBronzeLH | ConvertFrom-Json

$bronzeLakehouseId = $bronzeLH.id
Write-Host "Bronze Lakehouse ID: $bronzeLakehouseId"
```

**2.2 Create Silver Lakehouse**
```powershell
$createSilverLH = @{
    displayName = "medallion_silver"
    type = "Lakehouse"
} | ConvertTo-Json

$silverLH = curl -X POST \
    -H "Authorization: Bearer $token" \
    "https://api.fabric.microsoft.com/v1/workspaces/$workspaceId/items" \
    -d $createSilverLH | ConvertFrom-Json

$silverLakehouseId = $silverLH.id
```

**2.3 Create Gold Lakehouse**
```powershell
$createGoldLH = @{
    displayName = "medallion_gold"
    type = "Lakehouse"
} | ConvertTo-Json

$goldLH = curl -X POST \
    -H "Authorization: Bearer $token" \
    "https://api.fabric.microsoft.com/v1/workspaces/$workspaceId/items" \
    -d $createGoldLH | ConvertFrom-Json

$goldLakehouseId = $goldLH.id
```

### Phase 3: Deploy Notebooks (2-3 hours)

Create notebooks in workspace:
- `00_Generate_Sample_Data.py` - Sample data generator
- `01_Bronze_Ingestion.py` - Generic ingestion
- `01_Bronze_Validation.py` - Validation checks
- `02_Quality_Rules_Engine.py` - Quality framework
- `02_Silver_Transform.py` - Transformation
- `02_Silver_Validation.py` - Validation & lineage
- `03_Gold_Aggregations.py` - Aggregations
- `03_Gold_Validation.py` - Optimization
- `04_Pipeline_Monitoring.py` - Monitoring dashboard

### Phase 4: Test Bronze Layer (30 minutes)

**4.1 Generate Sample Data**
```python
%run /Workspace/Notebooks/00_Generate_Sample_Data
# Generates CSV files in /Files/landing/daily/
```

**4.2 Run Bronze Ingestion**
```python
%run /Workspace/Notebooks/01_Bronze_Ingestion
# Parameters:
# - source_config: orders
# - processing_date: 2024-01-15
# - mode: append
```

**4.3 Validate Results**
```python
%run /Workspace/Notebooks/01_Bronze_Validation
# Verify tables exist and contain data
```

### Phase 5: Test Silver Layer (30 minutes)

```python
%run /Workspace/Notebooks/02_Quality_Rules_Engine
%run /Workspace/Notebooks/02_Silver_Transform
%run /Workspace/Notebooks/02_Silver_Validation
```

### Phase 6: Test Gold Layer (30 minutes)

```python
%run /Workspace/Notebooks/03_Gold_Aggregations
%run /Workspace/Notebooks/03_Gold_Validation
```

### Phase 7: Create Orchestration Pipeline (1 hour)

Import the pipeline JSON definition and configure parameters.

### Phase 8: Power BI Integration (1-2 hours)

Follow "Power BI Integration Guide" above.

---

## 🔍 Validation Checklist

### Bronze Validation
- [ ] `bronze.events_raw` table exists
- [ ] Row count > 0
- [ ] Metadata columns present (_ingestion_timestamp, etc.)
- [ ] Partition by _ingestion_date working
- [ ] Ingestion log table populated

### Silver Validation
- [ ] `silver.events_cleaned` table exists
- [ ] Row count ≤ Bronze row count (after dedup)
- [ ] Null values removed/handled
- [ ] Duplicates eliminated
- [ ] Schema matches expected columns
- [ ] Quality metrics computed

### Gold Validation
- [ ] `gold.events_daily_summary` exists
- [ ] `gold.customer_segments` exists
- [ ] `gold.monthly_trend_analysis` exists
- [ ] Row counts reasonable (aggregated)
- [ ] ZORDER and OPTIMIZE applied
- [ ] Statistics collected

### Pipeline Validation
- [ ] Orchestration pipeline created
- [ ] Parameters configured
- [ ] Trigger schedule set (2 AM UTC)
- [ ] Notifications working
- [ ] Dry-run executed successfully

### Power BI Validation
- [ ] SQL endpoint available
- [ ] Semantic model created
- [ ] DirectLake connection working
- [ ] Report visuals populated with data
- [ ] Filters and drilldown functional

---

## 📊 Performance Baseline After Implementation

Run this query to establish baseline metrics:

```sql
-- Performance snapshot
SELECT 
    'Bronze_row_count' as metric,
    (SELECT COUNT(*) FROM bronze.events_raw) as value
UNION ALL
SELECT 
    'Silver_row_count',
    (SELECT COUNT(*) FROM silver.events_cleaned)
UNION ALL
SELECT 
    'Gold_row_count',
    (SELECT COUNT(*) FROM gold.events_daily_summary)
UNION ALL
SELECT 
    'Pipeline_duration_minutes',
    AVG(duration_seconds / 60.0)
FROM monitoring.pipeline_execution
WHERE execution_date >= DATE_SUB(CURRENT_DATE(), 7)
```

---

## 🎓 Training & Handoff

### Data Engineers
- Notebook architecture and modification patterns
- Spark configuration tuning
- Adding new data sources
- Troubleshooting common failures

### Analysts & BI Users
- Query Gold tables via SQL endpoint
- Understanding table relationships
- Creating custom Power BI reports
- Interpreting lineage and quality metrics

### Operations & Support
- Pipeline monitoring and alerting
- Troubleshooting runbooks
- Escalation procedures
- Performance tuning playbook

---

## ✅ Production Readiness Checklist

- [ ] All lakehouses created and configured
- [ ] All notebooks deployed and tested
- [ ] Configuration files uploaded
- [ ] Sample data processed successfully
- [ ] Bronze → Silver → Gold flow verified
- [ ] Monitoring dashboard active
- [ ] Alerts configured and tested
- [ ] Orchestration pipeline scheduled
- [ ] Power BI semantic model and reports created
- [ ] SQL endpoint provisioned
- [ ] RBAC configured per layer
- [ ] Documentation reviewed and approved
- [ ] Team trained on operations
- [ ] Capacity planning completed
- [ ] Disaster recovery plan documented
- [ ] Go-live date scheduled

---

## 📞 Support Resources

**Documentation**: See MEDALLION_ARCHITECTURE_PLAN.md  
**Notebooks**: See individual notebook markdown files  
**Troubleshooting**: See ORCHESTRATION_MONITORING.md → Runbooks  
**Examples**: See POWERBI_EXAMPLES_DEPLOYMENT.md  

**Contact**: data-engineering@company.com

---

## Summary

This medallion architecture provides:
- ✓ Scalable, production-ready data platform
- ✓ Clear separation of concerns (Bronze/Silver/Gold)
- ✓ Comprehensive data quality & validation
- ✓ Automated orchestration & monitoring
- ✓ Power BI analytics integration
- ✓ Complete documentation & examples
- ✓ Enterprise-grade governance & lineage

**Ready to deploy to your workspace! 🚀**
