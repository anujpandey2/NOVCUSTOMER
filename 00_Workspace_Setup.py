# Fabric Medallion Architecture - Phase 0: Workspace Setup
# Purpose: Initialize workspace configuration and folder structure
# Execution: Run after sample data generation
# Dependencies: None

from pyspark.sql.functions import *
import json
from datetime import datetime

print(f"🔧 Workspace Setup - {datetime.now()}")

# Create folder structure in lakehouse
folders = [
    "Files/config",
    "Files/logs",
    "Files/monitoring",
    "Files/sample_data",
    "Files/landing",
]

print("\n📁 Creating folder structure...")
for folder in folders:
    try:
        dbutils.fs.mkdirs(f"abfss://{folder}@onelake.dfs.fabric.microsoft.com/")
        print(f"✓ Created: {folder}")
    except Exception as e:
        print(f"⚠ Folder may exist: {folder}")

# Initialize configuration
config = {
    "workspace_id": "4850ec28-2ac1-4c80-a70d-977ab969085d",
    "workspace_name": "medallion-analytics",
    "environment": "production",
    "lakehouses": {
        "bronze": "medallion_bronze",
        "silver": "medallion_silver",
        "gold": "medallion_gold"
    },
    "timestamp": datetime.now().isoformat()
}

# Save configuration
config_path = "Files/config/workspace_config.json"
dbutils.fs.put(config_path, json.dumps(config, indent=2), overwrite=True)
print(f"\n✓ Workspace configuration saved to: {config_path}")

# Initialize metadata table
spark.sql("""
    CREATE TABLE IF NOT EXISTS bronze.medallion_metadata (
        metadata_id STRING NOT NULL,
        layer STRING NOT NULL,
        object_name STRING NOT NULL,
        object_type STRING NOT NULL,
        row_count LONG,
        size_bytes LONG,
        created_at TIMESTAMP NOT NULL,
        updated_at TIMESTAMP NOT NULL,
        status STRING,
        PRIMARY KEY (metadata_id)
    )
    USING DELTA
    PARTITIONED BY (layer)
""")

print("✓ Metadata table created")

# Initialize logging table
spark.sql("""
    CREATE TABLE IF NOT EXISTS bronze.medallion_logs (
        log_id STRING NOT NULL,
        log_timestamp TIMESTAMP NOT NULL,
        layer STRING NOT NULL,
        process_name STRING NOT NULL,
        status STRING,
        message STRING,
        row_count_affected LONG,
        execution_time_ms LONG,
        PRIMARY KEY (log_id)
    )
    USING DELTA
    PARTITIONED BY (layer, DATE(log_timestamp))
""")

print("✓ Logging table created")

print("\n✅ Workspace setup complete!")
print(json.dumps(config, indent=2))
