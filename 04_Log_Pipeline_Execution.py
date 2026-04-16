# Fabric Medallion Architecture - Phase 4: Log Pipeline Execution
# Purpose: Centralized logging for all pipeline executions
# Execution: Run to record pipeline execution logs
# Dependencies: All medallion layers

from pyspark.sql.functions import *
from datetime import datetime
import json

print(f"📝 Pipeline Execution Logging - {datetime.now()}")

# Create comprehensive logging table
spark.sql("""
    CREATE TABLE IF NOT EXISTS bronze.pipeline_execution_logs (
        log_id STRING NOT NULL,
        execution_timestamp TIMESTAMP NOT NULL,
        layer STRING NOT NULL,
        process_name STRING NOT NULL,
        status STRING NOT NULL,
        message STRING,
        input_row_count LONG,
        output_row_count LONG,
        execution_time_ms LONG,
        error_message STRING,
        PRIMARY KEY (log_id)
    )
    USING DELTA
    PARTITIONED BY (layer, DATE(execution_timestamp))
""")

print("✓ Execution logs table created")

# Retrieve execution logs from medallion_logs
print("\n📖 Retrieving medallion logs...")
try:
    logs = spark.sql("""
        SELECT 
            log_id,
            log_timestamp,
            layer,
            process_name,
            status,
            message,
            row_count_affected as output_row_count,
            execution_time_ms
        FROM bronze.medallion_logs
        ORDER BY log_timestamp DESC
        LIMIT 100
    """)
    
    log_count = logs.count()
    print(f"✓ Retrieved {log_count} log entries")
    
    # Display recent logs
    print("\nRecent Pipeline Logs:")
    logs.show(20, truncate=False)
    
    # Write to execution logs table
    logs.write.mode("append").format("delta").saveAsTable("bronze.pipeline_execution_logs")
    print(f"✓ Logs written to pipeline_execution_logs table")
    
except Exception as e:
    print(f"⚠ Error retrieving logs: {str(e)}")

# Generate logging report
print("\n📊 Logging Report:")
logging_report = {
    "report_timestamp": datetime.now().isoformat(),
    "total_logs": log_count if 'log_count' in locals() else 0,
    "log_tables": {
        "medallion_logs": "Real-time execution logs",
        "pipeline_execution_logs": "Centralized execution history",
        "quality_metrics": "Data quality scores",
        "pipeline_monitoring": "Performance metrics"
    },
    "log_retention": {
        "recent_logs": "Last 30 days",
        "archive": "30-90 days",
        "deletion": "After 90 days"
    }
}

print(json.dumps(logging_report, indent=2))

# Save logging report
report_path = f"Files/logs/logging_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
dbutils.fs.put(report_path, json.dumps(logging_report, indent=2), overwrite=True)
print(f"\n✅ Logging report saved to: {report_path}")

# Create audit trail table
spark.sql("""
    CREATE TABLE IF NOT EXISTS bronze.medallion_audit_trail (
        audit_id STRING NOT NULL,
        audit_timestamp TIMESTAMP NOT NULL,
        action_type STRING NOT NULL,
        entity_type STRING NOT NULL,
        entity_id STRING,
        changed_by STRING,
        change_details STRING,
        PRIMARY KEY (audit_id)
    )
    USING DELTA
    PARTITIONED BY (DATE(audit_timestamp))
""")

print("✓ Audit trail table created")

print(f"\n✅ Pipeline Execution Logging complete!")
