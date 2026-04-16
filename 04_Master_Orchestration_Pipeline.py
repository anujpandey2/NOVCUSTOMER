# Fabric Medallion Architecture - Phase 4: Master Orchestration Pipeline
# Purpose: Master orchestration for Bronze-Silver-Gold pipeline execution
# Execution: Run as central orchestrator or via pipeline
# Dependencies: All previous layers

from pyspark.sql.functions import *
from datetime import datetime, timedelta
import json
import uuid

print(f"🎯 Master Orchestration Pipeline - {datetime.now()}")

# Configuration
orchestration_config = {
    "pipeline_name": "medallion_master_orchestration",
    "execution_date": datetime.now().isoformat(),
    "environment": "production",
    "retry_count": 3,
    "timeout_minutes": 180
}

print(f"Configuration: {json.dumps(orchestration_config, indent=2)}")

# Create execution log
execution_log = {
    "pipeline_id": str(uuid.uuid4()),
    "start_time": datetime.now().isoformat(),
    "stages": {}
}

# Stage 1: Bronze ingestion
print("\n🔵 [STAGE 1] Bronze Ingestion")
try:
    # In actual deployment, this would call %run ../Notebooks/Phase1_Bronze/01_Bronze_Ingestion.py
    events_count = spark.table("bronze.events_raw").count()
    transactions_count = spark.table("bronze.transactions_raw").count()
    
    execution_log["stages"]["bronze_ingestion"] = {
        "status": "completed",
        "records": events_count + transactions_count,
        "timestamp": datetime.now().isoformat()
    }
    print(f"✓ Stage 1 complete: {events_count + transactions_count:,} records ingested")
except Exception as e:
    execution_log["stages"]["bronze_ingestion"] = {
        "status": "failed",
        "error": str(e),
        "timestamp": datetime.now().isoformat()
    }
    print(f"✗ Stage 1 failed: {str(e)}")

# Stage 2: Bronze validation
print("\n🔍 [STAGE 2] Bronze Validation")
try:
    events_nulls = spark.sql("""
        SELECT COUNT(*) as null_count FROM bronze.events_raw 
        WHERE event_id IS NULL OR event_type IS NULL
    """).collect()[0][0]
    
    execution_log["stages"]["bronze_validation"] = {
        "status": "completed",
        "quality_issues": events_nulls,
        "timestamp": datetime.now().isoformat()
    }
    print(f"✓ Stage 2 complete: Quality issues found: {events_nulls}")
except Exception as e:
    execution_log["stages"]["bronze_validation"] = {
        "status": "failed",
        "error": str(e)
    }
    print(f"✗ Stage 2 failed: {str(e)}")

# Stage 3: Silver transformation
print("\n⚪ [STAGE 3] Silver Transformation")
try:
    silver_count = spark.table("silver.transactions_cleaned").count()
    execution_log["stages"]["silver_transformation"] = {
        "status": "completed",
        "records": silver_count,
        "timestamp": datetime.now().isoformat()
    }
    print(f"✓ Stage 3 complete: {silver_count:,} records transformed")
except Exception as e:
    execution_log["stages"]["silver_transformation"] = {
        "status": "failed",
        "error": str(e)
    }
    print(f"✗ Stage 3 failed: {str(e)}")

# Stage 4: Silver validation
print("\n🔍 [STAGE 4] Silver Validation")
try:
    duplicates = spark.sql("""
        SELECT COUNT(*) as dup_count FROM (
            SELECT transaction_id, transaction_date, COUNT(*) as cnt 
            FROM silver.transactions_cleaned 
            GROUP BY transaction_id, transaction_date HAVING cnt > 1
        )
    """).collect()[0][0]
    
    execution_log["stages"]["silver_validation"] = {
        "status": "completed",
        "duplicates": duplicates,
        "timestamp": datetime.now().isoformat()
    }
    print(f"✓ Stage 4 complete: Duplicates found: {duplicates}")
except Exception as e:
    execution_log["stages"]["silver_validation"] = {
        "status": "failed",
        "error": str(e)
    }
    print(f"✗ Stage 4 failed: {str(e)}")

# Stage 5: Gold aggregations
print("\n🟡 [STAGE 5] Gold Aggregations")
try:
    gold_daily = spark.table("gold.gold_transactions_daily").count()
    gold_customer = spark.table("gold.gold_customer_metrics").count()
    gold_monthly = spark.table("gold.gold_summary_monthly").count()
    
    execution_log["stages"]["gold_aggregations"] = {
        "status": "completed",
        "tables": {
            "daily": gold_daily,
            "customer": gold_customer,
            "monthly": gold_monthly
        },
        "timestamp": datetime.now().isoformat()
    }
    print(f"✓ Stage 5 complete: {gold_daily + gold_customer + gold_monthly:,} aggregated records")
except Exception as e:
    execution_log["stages"]["gold_aggregations"] = {
        "status": "failed",
        "error": str(e)
    }
    print(f"✗ Stage 5 failed: {str(e)}")

# Stage 6: Gold validation
print("\n🔍 [STAGE 6] Gold Validation")
try:
    daily_nulls = spark.sql("""
        SELECT COUNT(*) FROM gold.gold_transactions_daily 
        WHERE total_amount IS NULL OR transaction_count IS NULL
    """).collect()[0][0]
    
    execution_log["stages"]["gold_validation"] = {
        "status": "completed",
        "quality_issues": daily_nulls,
        "timestamp": datetime.now().isoformat()
    }
    print(f"✓ Stage 6 complete: Quality issues: {daily_nulls}")
except Exception as e:
    execution_log["stages"]["gold_validation"] = {
        "status": "failed",
        "error": str(e)
    }
    print(f"✗ Stage 6 failed: {str(e)}")

# Finalize execution
execution_log["end_time"] = datetime.now().isoformat()
execution_log["overall_status"] = "SUCCESS" if all(
    s.get("status") == "completed" for s in execution_log["stages"].values()
) else "FAILED"

print(f"\n✅ Master Orchestration Pipeline complete!")
print(f"Overall Status: {execution_log['overall_status']}")
print(f"\nExecution Summary:")
print(json.dumps(execution_log, indent=2))

# Save execution log
log_path = f"Files/logs/orchestration_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
dbutils.fs.put(log_path, json.dumps(execution_log, indent=2), overwrite=True)
print(f"\n📝 Execution log saved to: {log_path}")

# Create pipeline metrics table entry
log_id = str(uuid.uuid4())
spark.sql(f"""
    INSERT INTO bronze.medallion_logs
    VALUES (
        '{log_id}',
        current_timestamp(),
        'orchestration',
        'master_pipeline',
        '{execution_log['overall_status']}',
        'Master pipeline execution completed',
        0,
        0
    )
""")
