# Fabric Medallion Architecture - Phase 3: Gold Validation
# Purpose: Validate Gold layer aggregations and performance
# Execution: Run after gold aggregations
# Dependencies: 03_Gold_Aggregations.py

from pyspark.sql.functions import *
import json
from datetime import datetime
import uuid

print(f"🔍 Gold Layer Validation - {datetime.now()}")

# Validation results
validation_results = {
    "timestamp": datetime.now().isoformat(),
    "layer": "gold",
    "tables": {}
}

# Validate daily transactions
print("\n📊 Validating gold_transactions_daily...")
daily_count = spark.table("gold.gold_transactions_daily").count()
daily_nulls = spark.sql("""
    SELECT COUNT(*) FROM gold.gold_transactions_daily 
    WHERE total_amount IS NULL OR transaction_count IS NULL
""").collect()[0][0]

validation_results["tables"]["daily_transactions"] = {
    "row_count": daily_count,
    "null_count": daily_nulls,
    "status": "valid" if daily_nulls == 0 and daily_count > 0 else "warning"
}
print(f"✓ Row count: {daily_count}, Nulls: {daily_nulls}")

# Validate customer metrics
print("\n📊 Validating gold_customer_metrics...")
customer_count = spark.table("gold.gold_customer_metrics").count()
customer_nulls = spark.sql("""
    SELECT COUNT(*) FROM gold.gold_customer_metrics 
    WHERE lifetime_value IS NULL OR transaction_frequency IS NULL
""").collect()[0][0]

validation_results["tables"]["customer_metrics"] = {
    "row_count": customer_count,
    "null_count": customer_nulls,
    "status": "valid" if customer_nulls == 0 and customer_count > 0 else "warning"
}
print(f"✓ Row count: {customer_count}, Nulls: {customer_nulls}")

# Validate monthly summary
print("\n📊 Validating gold_summary_monthly...")
monthly_count = spark.table("gold.gold_summary_monthly").count()
monthly_nulls = spark.sql("""
    SELECT COUNT(*) FROM gold.gold_summary_monthly 
    WHERE total_amount IS NULL OR total_transactions IS NULL
""").collect()[0][0]

validation_results["tables"]["monthly_summary"] = {
    "row_count": monthly_count,
    "null_count": monthly_nulls,
    "status": "valid" if monthly_nulls == 0 and monthly_count > 0 else "warning"
}
print(f"✓ Row count: {monthly_count}, Nulls: {monthly_nulls}")

# Check table sizes
print("\n💾 Checking table sizes...")
tables_info = spark.sql("""
    SELECT 
        name,
        size_in_bytes / 1024.0 / 1024.0 as size_mb,
        num_files,
        num_rows
    FROM INFORMATION_SCHEMA.TABLES
    WHERE table_schema = 'gold'
""").collect()

table_sizes = {}
for row in tables_info:
    table_name = row[0]
    size_mb = round(float(row[1]), 2)
    num_files = row[2]
    num_rows = row[3]
    
    table_sizes[table_name] = {
        "size_mb": size_mb,
        "num_files": num_files,
        "num_rows": num_rows
    }
    print(f"✓ {table_name}: {size_mb} MB, {num_files} files, {num_rows:,} rows")

validation_results["table_sizes"] = table_sizes

# Overall status
all_valid = all(t.get("status") == "valid" for t in validation_results["tables"].values())
validation_results["overall_status"] = "PASSED" if all_valid else "WARNING"

print(f"\n✅ Gold validation complete!")
print(f"Overall Status: {validation_results['overall_status']}")
print(f"Results: {json.dumps(validation_results, indent=2, default=str)}")

# Log validation
log_id = str(uuid.uuid4())
spark.sql(f"""
    INSERT INTO bronze.medallion_logs
    VALUES (
        '{log_id}',
        current_timestamp(),
        'gold',
        'validation',
        '{validation_results['overall_status']}',
        'Gold layer validation completed',
        {daily_count + customer_count + monthly_count},
        0
    )
""")
