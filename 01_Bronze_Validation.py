# Fabric Medallion Architecture - Phase 1: Bronze Validation
# Purpose: Validate Bronze layer data quality and schema
# Execution: Run after 01_Bronze_Ingestion.py
# Dependencies: 01_Bronze_Ingestion.py

from pyspark.sql.functions import *
import json
from datetime import datetime

print(f"🔍 Bronze Layer Validation - {datetime.now()}")

# Validation results
validation_results = {
    "timestamp": datetime.now().isoformat(),
    "layer": "bronze",
    "validations": {}
}

# Check events table
print("\n📊 Validating events_raw table...")
events_count = spark.table("bronze.events_raw").count()
events_schema = spark.table("bronze.events_raw").schema

validation_results["validations"]["events_raw"] = {
    "row_count": events_count,
    "schema_fields": len(events_schema),
    "status": "valid" if events_count > 0 else "invalid"
}
print(f"✓ Events row count: {events_count:,}")
print(f"✓ Events columns: {len(events_schema)}")

# Check transactions table
print("\n📊 Validating transactions_raw table...")
transactions_count = spark.table("bronze.transactions_raw").count()
transactions_schema = spark.table("bronze.transactions_raw").schema

validation_results["validations"]["transactions_raw"] = {
    "row_count": transactions_count,
    "schema_fields": len(transactions_schema),
    "status": "valid" if transactions_count > 0 else "invalid"
}
print(f"✓ Transactions row count: {transactions_count:,}")
print(f"✓ Transactions columns: {len(transactions_schema)}")

# Null checks
print("\n🔎 Checking for null values...")
events_nulls = spark.sql("""
    SELECT COUNT(*) as null_count FROM bronze.events_raw 
    WHERE event_id IS NULL OR event_type IS NULL
""").collect()[0][0]

transactions_nulls = spark.sql("""
    SELECT COUNT(*) as null_count FROM bronze.transactions_raw 
    WHERE transaction_id IS NULL OR amount IS NULL
""").collect()[0][0]

validation_results["validations"]["null_checks"] = {
    "events_nulls": events_nulls,
    "transactions_nulls": transactions_nulls,
    "status": "valid" if events_nulls == 0 and transactions_nulls == 0 else "warning"
}
print(f"✓ Events null issues: {events_nulls}")
print(f"✓ Transactions null issues: {transactions_nulls}")

# Amount range validation
print("\n💰 Validating amount ranges...")
amount_stats = spark.sql("""
    SELECT 
        MIN(amount) as min_amount,
        MAX(amount) as max_amount,
        AVG(amount) as avg_amount
    FROM bronze.transactions_raw
""").collect()[0]

validation_results["validations"]["amount_validation"] = {
    "min_amount": float(amount_stats[0]) if amount_stats[0] else None,
    "max_amount": float(amount_stats[1]) if amount_stats[1] else None,
    "avg_amount": float(amount_stats[2]) if amount_stats[2] else None,
    "status": "valid" if amount_stats[0] > 0 and amount_stats[1] < 1000000 else "warning"
}
print(f"✓ Amount range: ${amount_stats[0]:.2f} - ${amount_stats[1]:.2f}")
print(f"✓ Average amount: ${amount_stats[2]:.2f}")

# Overall validation
all_valid = all(v.get("status") == "valid" for v in validation_results["validations"].values())
validation_results["overall_status"] = "PASSED" if all_valid else "WARNING"

print("\n✅ Bronze validation complete!")
print(f"Overall Status: {validation_results['overall_status']}")
print(f"Results: {json.dumps(validation_results, indent=2, default=str)}")

# Save results
import uuid
log_id = str(uuid.uuid4())
spark.sql(f"""
    INSERT INTO bronze.medallion_logs 
    VALUES (
        '{log_id}',
        current_timestamp(),
        'bronze',
        'validation',
        '{validation_results['overall_status']}',
        'Bronze layer validation completed',
        0,
        0
    )
""")
