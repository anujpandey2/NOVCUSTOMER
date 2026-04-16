# Fabric Medallion Architecture - Phase 1: Bronze Ingestion
# Purpose: Multi-format ingestion into Bronze layer with metadata tracking
# Execution: Run after workspace setup
# Dependencies: 00_Workspace_Setup.py

from pyspark.sql.functions import *
from pyspark.sql.types import *
import json
import uuid
from datetime import datetime

print(f"🔵 Bronze Layer Ingestion - {datetime.now()}")

# Configuration
config = {
    "environment": "production",
    "ingestion_date": current_date().cast(DateType()),
    "batch_id": str(uuid.uuid4()),
    "source_paths": {
        "events": "Files/sample_data/events.csv",
        "transactions": "Files/sample_data/transactions.csv"
    }
}

print(f"Configuration: {json.dumps(config, default=str, indent=2)}")

# Ingest events data
print("\n📥 Ingesting events data...")
events_df = spark.read.format("csv").option("header", "true").option("inferSchema", "true").load(config["source_paths"]["events"])

# Add metadata columns
events_raw = (events_df
    .withColumn("ingestion_timestamp", current_timestamp())
    .withColumn("source_file", lit(config["source_paths"]["events"]))
    .withColumn("batch_id", lit(config["batch_id"]))
    .withColumn("ingestion_date", current_date())
)

# Write to bronze
events_raw.write.mode("append").partitionBy("ingestion_date").format("delta").saveAsTable("bronze.events_raw")
events_count = events_raw.count()
print(f"✓ Events ingested: {events_count:,}")

# Ingest transactions data
print("\n📥 Ingesting transactions data...")
transactions_df = spark.read.format("csv").option("header", "true").option("inferSchema", "true").load(config["source_paths"]["transactions"])

# Add metadata columns
transactions_raw = (transactions_df
    .withColumn("ingestion_timestamp", current_timestamp())
    .withColumn("source_file", lit(config["source_paths"]["transactions"]))
    .withColumn("batch_id", lit(config["batch_id"]))
    .withColumn("ingestion_date", current_date())
)

# Write to bronze
transactions_raw.write.mode("append").partitionBy("ingestion_date").format("delta").saveAsTable("bronze.transactions_raw")
transactions_count = transactions_raw.count()
print(f"✓ Transactions ingested: {transactions_count:,}")

# Log ingestion
spark.sql(f"""
    INSERT INTO bronze.medallion_logs 
    VALUES (
        '{str(uuid.uuid4())}',
        current_timestamp(),
        'bronze',
        'ingestion',
        'success',
        'Ingestion of events and transactions completed',
        {events_count + transactions_count},
        0
    )
""")

print("\n✅ Bronze ingestion complete!")
print(f"Total records ingested: {events_count + transactions_count:,}")
print(f"Batch ID: {config['batch_id']}")
