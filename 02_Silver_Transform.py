# Fabric Medallion Architecture - Phase 2: Silver Transformation
# Purpose: Bronze-to-Silver transformation with deduplication and validation
# Execution: Run after quality rules setup
# Dependencies: 02_Quality_Rules_Engine.py, 01_Bronze_Validation.py

from pyspark.sql.functions import *
from pyspark.sql.window import Window
import json
from datetime import datetime
import uuid

print(f"⚪ Silver Layer Transformation - {datetime.now()}")

# Configuration
config = {
    "incremental_mode": True,
    "write_mode": "overwrite"
}

# Transform events
print("\n🔄 Transforming events to silver...")
events_raw = spark.table("bronze.events_raw")

events_cleaned = (events_raw
    .filter(col("event_id").isNotNull())
    .filter(col("event_type").isNotNull())
    .withColumn("event_date", col("event_timestamp").cast(DateType()))
    .withColumn("event_hour", hour(col("event_timestamp")))
    .withColumn("properties_json", col("properties"))
    .select([
        "event_id", "event_type", "event_timestamp", "source_system",
        "user_id", "event_date", "event_hour", "properties_json"
    ])
    .dropDuplicates(["event_id"])  # Deduplication
)

# Write to silver
events_cleaned.write.mode(config["write_mode"]).partitionBy("event_date").format("delta").saveAsTable("silver.events_cleaned")
events_silver_count = events_cleaned.count()
print(f"✓ Events transformed: {events_silver_count:,}")

# Transform transactions
print("\n🔄 Transforming transactions to silver...")
transactions_raw = spark.table("bronze.transactions_raw")

# Filter valid records and deduplicate
transactions_cleaned = (transactions_raw
    .filter(col("transaction_id").isNotNull())
    .filter(col("customer_id").isNotNull())
    .filter(col("amount").isNotNull())
    .filter((col("amount") > 0) & (col("amount") < 1000000))  # Range validation
    .filter(col("currency").isin("USD", "EUR", "GBP"))
    .dropDuplicates(["transaction_id", "transaction_date"])  # Deduplication
    .withColumn("day_of_week", dayofweek(col("transaction_date")))
    .withColumn("hour_of_day", hour(col("transaction_timestamp")))
    .withColumn("month", month(col("transaction_date")))
    .withColumn("year", year(col("transaction_date")))
    .select([
        "transaction_id", "transaction_date", "transaction_timestamp",
        "amount", "currency", "customer_id", "merchant_id", "status",
        "day_of_week", "hour_of_day", "month", "year"
    ])
)

# Apply ZORDER optimization hint
transactions_cleaned.write.mode(config["write_mode"]).partitionBy("transaction_date").format("delta").saveAsTable("silver.transactions_cleaned")
transactions_silver_count = transactions_cleaned.count()
print(f"✓ Transactions transformed: {transactions_silver_count:,}")

# Log transformation metrics
log_id = str(uuid.uuid4())
spark.sql(f"""
    INSERT INTO silver.quality_metrics
    VALUES (
        '{log_id}',
        current_timestamp(),
        'silver',
        'transformation',
        'row_count',
        {events_silver_count + transactions_silver_count},
        0,
        1.0
    )
""")

# Run OPTIMIZE on Silver tables
print("\n⚡ Optimizing Silver tables...")
spark.sql("OPTIMIZE TABLE silver.events_cleaned")
spark.sql("OPTIMIZE TABLE silver.transactions_cleaned")
print("✓ Silver tables optimized")

print(f"\n✅ Silver transformation complete!")
print(f"Events: {events_silver_count:,}")
print(f"Transactions: {transactions_silver_count:,}")
