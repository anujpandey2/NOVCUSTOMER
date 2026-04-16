# Fabric Medallion Architecture - Phase 2: Quality Rules Engine
# Purpose: Define and apply quality rules for Silver layer transformations
# Execution: Run before silver transformations
# Dependencies: None (setup phase)

from pyspark.sql.functions import *
from pyspark.sql.types import *
import json
from datetime import datetime

print(f"⚙️ Quality Rules Engine Setup - {datetime.now()}")

# Define quality rules
quality_rules = {
    "deduplication": {
        "enabled": True,
        "transactions": {
            "key_columns": ["transaction_id", "transaction_date"],
            "strategy": "keep_latest"
        }
    },
    "null_handling": {
        "transactions": {
            "required_columns": ["transaction_id", "customer_id", "amount"],
            "drop_if_null": True
        }
    },
    "range_validation": {
        "transactions": {
            "amount": {"min": 0, "max": 1000000},
            "currency": {"allowed_values": ["USD", "EUR", "GBP"]}
        }
    },
    "referential_integrity": {
        "transactions": {
            "customer_id": {
                "check": "not_empty",
                "pattern": "^[A-Z]{0,10}[0-9]*$"
            }
        }
    }
}

print("✓ Quality rules engine initialized")
print(json.dumps(quality_rules, indent=2))

# Create quality metrics table
spark.sql("""
    CREATE TABLE IF NOT EXISTS silver.quality_metrics (
        metric_id STRING NOT NULL,
        metric_timestamp TIMESTAMP NOT NULL,
        layer STRING NOT NULL,
        rule_name STRING NOT NULL,
        rule_type STRING NOT NULL,
        passed_count LONG,
        failed_count LONG,
        pass_rate DOUBLE,
        PRIMARY KEY (metric_id)
    )
    USING DELTA
    PARTITIONED BY (layer, DATE(metric_timestamp))
""")

print("✓ Quality metrics table created")

# Save rules to file
rules_path = "Files/config/quality_rules.json"
dbutils.fs.put(rules_path, json.dumps(quality_rules, indent=2), overwrite=True)
print(f"✓ Quality rules saved to: {rules_path}")

print("\n✅ Quality Rules Engine setup complete!")
