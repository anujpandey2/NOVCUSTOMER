# Fabric Medallion Architecture - Phase 2: Silver Validation
# Purpose: Validate Silver layer transformations and data quality
# Execution: Run after silver transformation
# Dependencies: 02_Silver_Transform.py

from pyspark.sql.functions import *
import json
from datetime import datetime
import uuid

print(f"🔍 Silver Layer Validation - {datetime.now()}")

# Validation results
validation_results = {
    "timestamp": datetime.now().isoformat(),
    "layer": "silver",
    "validations": {}
}

# Check events_cleaned table
print("\n📊 Validating events_cleaned table...")
events_count = spark.table("silver.events_cleaned").count()
events_duplicates = spark.sql("""
    SELECT COUNT(*) as dup_count FROM (
        SELECT event_id, COUNT(*) as cnt FROM silver.events_cleaned 
        GROUP BY event_id HAVING cnt > 1
    )
""").collect()[0][0]

validation_results["validations"]["events_cleaned"] = {
    "row_count": events_count,
    "duplicate_keys": events_duplicates,
    "status": "valid" if events_duplicates == 0 and events_count > 0 else "invalid"
}
print(f"✓ Events row count: {events_count:,}")
print(f"✓ Duplicate keys: {events_duplicates}")

# Check transactions_cleaned table
print("\n📊 Validating transactions_cleaned table...")
transactions_count = spark.table("silver.transactions_cleaned").count()
transactions_duplicates = spark.sql("""
    SELECT COUNT(*) as dup_count FROM (
        SELECT transaction_id, transaction_date, COUNT(*) as cnt 
        FROM silver.transactions_cleaned 
        GROUP BY transaction_id, transaction_date HAVING cnt > 1
    )
""").collect()[0][0]

validation_results["validations"]["transactions_cleaned"] = {
    "row_count": transactions_count,
    "duplicate_keys": transactions_duplicates,
    "status": "valid" if transactions_duplicates == 0 and transactions_count > 0 else "invalid"
}
print(f"✓ Transactions row count: {transactions_count:,}")
print(f"✓ Duplicate keys: {transactions_duplicates}")

# Data quality score
print("\n📈 Calculating quality score...")
quality_score = (events_count + transactions_count) / (events_count + transactions_count + 1) * 100
validation_results["quality_score"] = round(quality_score, 2)
print(f"✓ Quality score: {quality_score:.2f}%")

# Overall validation
all_valid = all(v.get("status") == "valid" for v in validation_results["validations"].values())
validation_results["overall_status"] = "PASSED" if all_valid and quality_score >= 95 else "WARNING"

print(f"\n✅ Silver validation complete!")
print(f"Overall Status: {validation_results['overall_status']}")

# Log results
log_id = str(uuid.uuid4())
spark.sql(f"""
    INSERT INTO silver.quality_metrics
    VALUES (
        '{log_id}',
        current_timestamp(),
        'silver',
        'validation',
        'quality_score',
        {int(quality_score)},
        0,
        {quality_score / 100.0}
    )
""")
