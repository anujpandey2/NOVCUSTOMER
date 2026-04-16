# BRONZE LAYER: Raw Data Ingestion
## Microsoft Fabric Medallion Architecture

This document contains complete, production-ready PySpark code for Bronze layer ingestion.

---

## 📋 Notebook 01: Bronze Ingestion (Generic)

**File**: `01_Bronze_Ingestion.py`  
**Purpose**: Ingest raw data with minimal transformation, add metadata, handle errors  
**Cluster**: Standard (8-16 cores)  
**Runtime**: 5-30 minutes depending on data volume  

### Setup & Imports

```python
# Databricks notebook source
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    current_timestamp, input_file_name, lit, col, 
    concat_ws, row_number, dense_rank
)
from pyspark.sql.window import Window
from datetime import datetime, timedelta
import json
import logging
import uuid
from typing import Dict, List, Optional
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Spark session
spark = SparkSession.builder \
    .appName("BronzeIngestio n") \
    .getOrCreate()

# Bronze layer Spark config (write-optimized)
spark.conf.set("spark.sql.parquet.vorder.default", "false")
spark.conf.set("spark.databricks.delta.autoCompact.enabled", "true")
spark.conf.set("spark.databricks.delta.targetFileSize", "1gb")
spark.conf.set("spark.sql.shuffle.partitions", "200")

print("✓ Bronze layer notebook initialized")
```

### Configuration Loading

```python
# COMMAND: Load configuration from parameters or defaults
dbutils.widgets.text("source_config", "default_events", "Source configuration key")
dbutils.widgets.text("processing_date", datetime.now().strftime("%Y-%m-%d"), "Processing date (YYYY-MM-DD)")
dbutils.widgets.dropdown("mode", "append", ["append", "overwrite"], "Write mode")
dbutils.widgets.text("batch_id", str(uuid.uuid4()), "Unique batch identifier")

# Get widget values
SOURCE_CONFIG = dbutils.widgets.get("source_config")
PROCESSING_DATE = dbutils.widgets.get("processing_date")
WRITE_MODE = dbutils.widgets.get("mode")
BATCH_ID = dbutils.widgets.get("batch_id")

# Load configuration
config_path = f"/Workspace/Files/config/bronze_config.json"
config_json = dbutils.fs.get(config_path).getValues()
bronze_config = json.loads(config_json[config_path])

logger.info(f"Processing date: {PROCESSING_DATE}")
logger.info(f"Batch ID: {BATCH_ID}")
logger.info(f"Source config: {SOURCE_CONFIG}")
logger.info(f"Write mode: {WRITE_MODE}")

# Extract source metadata
if SOURCE_CONFIG not in bronze_config["sources"]:
    raise ValueError(f"Source '{SOURCE_CONFIG}' not found in configuration")

source_meta = bronze_config["sources"][SOURCE_CONFIG]
source_type = source_meta["type"]  # csv, parquet, json, delta
source_path = source_meta["path"]
bronze_table = source_meta["bronze_table"]
partition_col = source_meta.get("partition_col", "ingestion_date")

print(f"✓ Configuration loaded: {SOURCE_CONFIG}")
print(f"  Type: {source_type}, Path: {source_path}")
print(f"  Target table: {bronze_table}")
```

### Ingestion Logging Setup

```python
# COMMAND: Create logging table for ingestion tracking
logger_setup_sql = f"""
CREATE TABLE IF NOT EXISTS bronze.ingestion_log (
    batch_id STRING,
    source_system STRING,
    source_path STRING,
    processing_date DATE,
    ingestion_timestamp TIMESTAMP,
    row_count_attempted LONG,
    row_count_success LONG,
    row_count_error LONG,
    status STRING,  -- 'success', 'partial', 'failed'
    error_message STRING,
    duration_seconds LONG,
    spark_config MAP<STRING, STRING>
)
USING DELTA
PARTITIONED BY (processing_date)
"""
spark.sql(logger_setup_sql)

# Create staging table for error records
error_staging_sql = f"""
CREATE TABLE IF NOT EXISTS bronze.ingestion_errors (
    batch_id STRING,
    source_system STRING,
    error_row NUMBER,
    error_message STRING,
    raw_data STRING,
    error_timestamp TIMESTAMP,
    processing_date DATE
)
USING DELTA
PARTITIONED BY (processing_date)
"""
spark.sql(error_staging_sql)

print("✓ Logging infrastructure ready")
```

### Read Data (Multi-Format Support)

```python
# COMMAND: Read source data based on type
from pyspark.sql.types import StructType

def read_source_data(source_type: str, source_path: str, schema: Optional[StructType] = None):
    """
    Read source data in multiple formats with error handling
    """
    try:
        if source_type.lower() == "csv":
            df = spark.read \
                .format("csv") \
                .option("header", "true") \
                .option("inferSchema", "true") \
                .option("multiLine", "true") \
                .option("escape", "\"") \
                .load(source_path)
        
        elif source_type.lower() == "parquet":
            df = spark.read.format("parquet").load(source_path)
        
        elif source_type.lower() == "json":
            df = spark.read.format("json").load(source_path)
        
        elif source_type.lower() == "delta":
            df = spark.read.format("delta").load(source_path)
        
        else:
            raise ValueError(f"Unsupported source type: {source_type}")
        
        logger.info(f"✓ Successfully read {source_type} from {source_path}")
        logger.info(f"  Schema: {df.schema}")
        logger.info(f"  Row count: {df.count()}")
        
        return df
    
    except Exception as e:
        logger.error(f"✗ Failed to read {source_type}: {str(e)}")
        raise

# Read the source data
df_raw = read_source_data(source_type, source_path)
row_count_raw = df_raw.count()
print(f"✓ Read {row_count_raw} rows from {source_type} source")
```

### Add Metadata Columns

```python
# COMMAND: Enhance with metadata columns
from pyspark.sql.functions import (
    current_timestamp, input_file_name, 
    sha2, concat_ws, md5, coalesce
)

def add_bronze_metadata(df, batch_id: str, source_system: str):
    """
    Add technical metadata columns to track lineage and enable replay
    """
    df_with_metadata = df \
        .withColumn("_ingestion_timestamp", current_timestamp()) \
        .withColumn("_ingestion_id", lit(batch_id)) \
        .withColumn("_source_system", lit(source_system)) \
        .withColumn("_source_file", input_file_name()) \
        .withColumn("_ingestion_date", current_timestamp().cast("date")) \
        .withColumn("_row_hash", md5(concat_ws("|", df.columns))) \
        .withColumn("_insertion_timestamp", current_timestamp())
    
    return df_with_metadata

# Apply metadata
df_with_metadata = add_bronze_metadata(
    df_raw, 
    batch_id=BATCH_ID, 
    source_system=source_meta["system_name"]
)

print("✓ Metadata columns added:")
print(f"  _ingestion_timestamp: When data was ingested")
print(f"  _ingestion_id: Batch identifier for this load")
print(f"  _source_system: Source system name")
print(f"  _source_file: Original file path")
print(f"  _ingestion_date: Date partition column")
print(f"  _row_hash: Hash for duplicate detection")
```

### Data Validation

```python
# COMMAND: Validate data before writing
def validate_ingestion_data(df, source_config: Dict) -> Dict:
    """
    Pre-ingestion validation checks
    Returns dictionary of validation results
    """
    validation_results = {
        "row_count": df.count(),
        "column_count": len(df.columns),
        "expected_columns": source_config.get("expected_columns", []),
        "checks": {}
    }
    
    # Check 1: Row count > 0
    if validation_results["row_count"] == 0:
        validation_results["checks"]["empty_data"] = "FAIL"
        logger.warning("⚠ No rows found in source data")
    else:
        validation_results["checks"]["empty_data"] = "PASS"
    
    # Check 2: Required columns present
    df_columns = set(df.columns)
    required_cols = set(source_config.get("required_columns", []))
    missing_cols = required_cols - df_columns
    
    if missing_cols:
        validation_results["checks"]["required_columns"] = f"FAIL - Missing: {missing_cols}"
        logger.error(f"✗ Required columns missing: {missing_cols}")
    else:
        validation_results["checks"]["required_columns"] = "PASS"
    
    # Check 3: Column count matches expected
    expected_col_count = len(source_config.get("expected_columns", []))
    if expected_col_count > 0 and validation_results["column_count"] != expected_col_count:
        validation_results["checks"]["column_count"] = \
            f"WARN - Expected {expected_col_count}, got {validation_results['column_count']}"
    else:
        validation_results["checks"]["column_count"] = "PASS"
    
    # Check 4: Data type validation (sample)
    for col_name, expected_type in source_config.get("column_types", {}).items():
        if col_name in df.columns:
            actual_type = dict(df.dtypes)[col_name]
            if actual_type.lower() != expected_type.lower():
                validation_results["checks"][f"type_{col_name}"] = \
                    f"WARN - Expected {expected_type}, got {actual_type}"
            else:
                validation_results["checks"][f"type_{col_name}"] = "PASS"
    
    return validation_results

# Run validation
validation = validate_ingestion_data(df_with_metadata, source_meta)

print("✓ Validation Results:")
for check, result in validation["checks"].items():
    status_icon = "✓" if result == "PASS" else "⚠"
    print(f"  {status_icon} {check}: {result}")

if not all(v == "PASS" for v in validation["checks"].values()):
    logger.warning("⚠ Validation completed with warnings (non-fatal)")
```

### Handle Errors (Optional)

```python
# COMMAND: Error handling for problematic records
def capture_invalid_records(df, batch_id: str, processing_date: str):
    """
    Identify and capture records with data quality issues
    """
    # Example: capture rows with null values in critical columns
    critical_columns = ["customer_id", "order_date", "amount"]
    null_checks = [col(c).isNull() for c in critical_columns if c in df.columns]
    
    if null_checks:
        from pyspark.sql.functions import when, coalesce
        
        # Flag rows with nulls
        df_with_flags = df.withColumn(
            "_has_nulls",
            when(coalesce(*null_checks), lit(True)).otherwise(lit(False))
        )
        
        # Separate clean and error records
        df_clean = df_with_flags.filter(col("_has_nulls") == False).drop("_has_nulls")
        df_errors = df_with_flags.filter(col("_has_nulls") == True)
        
        # Log errors
        error_count = df_errors.count()
        if error_count > 0:
            logger.warning(f"⚠ Found {error_count} records with null values in critical columns")
            df_errors.write.format("delta").mode("append") \
                .option("mergeSchema", "true") \
                .saveAsTable("bronze.ingestion_errors")
        
        return df_clean, error_count
    else:
        return df, 0

# Apply error handling (optional)
df_cleaned, error_count = capture_invalid_records(
    df_with_metadata, 
    BATCH_ID, 
    PROCESSING_DATE
)

print(f"✓ Error handling: {error_count} records flagged")
```

### Write to Bronze Table

```python
# COMMAND: Write to Bronze Delta table with partitioning
import time

start_time = time.time()

try:
    # Partition data by ingestion date for efficient queries
    df_to_write = df_cleaned if 'df_cleaned' in locals() else df_with_metadata
    
    df_to_write.write \
        .format("delta") \
        .mode(WRITE_MODE) \
        .partitionBy("_ingestion_date") \
        .option("mergeSchema", "true") \
        .option("overwriteSchema", "true") \
        .saveAsTable(f"bronze.{bronze_table}")
    
    write_duration = time.time() - start_time
    row_count_written = df_to_write.count()
    
    logger.info(f"✓ Successfully wrote {row_count_written} rows to bronze.{bronze_table}")
    logger.info(f"  Duration: {write_duration:.2f} seconds")
    logger.info(f"  Throughput: {row_count_written / write_duration:.0f} rows/sec")
    
    # Log ingestion success
    spark.sql(f"""
        INSERT INTO bronze.ingestion_log VALUES (
            '{BATCH_ID}',
            '{source_meta['system_name']}',
            '{source_path}',
            DATE('{PROCESSING_DATE}'),
            current_timestamp(),
            {row_count_raw},
            {row_count_written},
            {error_count if 'error_count' in locals() else 0},
            'success',
            NULL,
            {int(write_duration)},
            map()
        )
    """)
    
    print(f"✓ Ingestion logged successfully")
    
except Exception as e:
    logger.error(f"✗ Failed to write to Bronze layer: {str(e)}")
    
    # Log failure
    error_msg = str(e).replace("'", "")
    spark.sql(f"""
        INSERT INTO bronze.ingestion_log VALUES (
            '{BATCH_ID}',
            '{source_meta['system_name']}',
            '{source_path}',
            DATE('{PROCESSING_DATE}'),
            current_timestamp(),
            {row_count_raw},
            0,
            {row_count_raw},
            'failed',
            '{error_msg}',
            0,
            map()
        )
    """)
    
    raise
```

### Display Results

```python
# COMMAND: Show ingestion results
print("\n" + "="*80)
print("BRONZE INGESTION SUMMARY")
print("="*80)

# Latest ingestion record
latest_log = spark.sql(f"""
    SELECT 
        batch_id,
        source_system,
        processing_date,
        row_count_attempted,
        row_count_success,
        row_count_error,
        status,
        duration_seconds,
        ingestion_timestamp
    FROM bronze.ingestion_log
    WHERE batch_id = '{BATCH_ID}'
    ORDER BY ingestion_timestamp DESC
    LIMIT 1
""")

latest_log.show(truncate=False)

# Table statistics
table_stats = spark.sql(f"""
    SELECT 
        COUNT(*) as total_rows,
        COUNT(DISTINCT _ingestion_id) as unique_batches,
        COUNT(DISTINCT _ingestion_date) as date_range,
        MIN(_ingestion_timestamp) as oldest_record,
        MAX(_ingestion_timestamp) as newest_record
    FROM bronze.{bronze_table}
""")

table_stats.show()

# Sample records
print("\nSample Records:")
spark.sql(f"SELECT * FROM bronze.{bronze_table} LIMIT 10").show(truncate=False)

print("\n✓ Bronze ingestion complete!")
print(f"  Table: bronze.{bronze_table}")
print(f"  Rows written: {row_count_written}")
print(f"  Batch ID: {BATCH_ID}")
```

---

## 📋 Notebook 02: Sample Data Generator

**File**: `00_Generate_Sample_Data.py`  
**Purpose**: Create realistic test data for testing medallion pipeline  
**Cluster**: Standard (4-8 cores)  
**Runtime**: 5-10 minutes  

```python
# Databricks notebook source
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    rand, randn, lit, col, when, expr, 
    to_date, date_add, date_sub, current_timestamp
)
from pyspark.sql.types import *
from datetime import datetime, timedelta
import random

spark = SparkSession.builder.appName("SampleDataGenerator").getOrCreate()

# COMMAND: Generate E-commerce Sample Data
print("Generating E-commerce sample data...")

# Products
products_data = []
for i in range(1, 101):
    products_data.append({
        "product_id": f"PROD_{i:05d}",
        "product_name": f"Product {i}",
        "category": random.choice(["Electronics", "Clothing", "Home", "Sports", "Food"]),
        "price": round(random.uniform(10, 1000), 2),
        "currency": "USD"
    })

df_products = spark.createDataFrame(products_data)
df_products.write.format("csv").mode("overwrite").option("header", "true") \
    .save("/Workspace/Files/landing/daily/products_sample.csv")

# Customers
customers_data = []
for i in range(1, 1001):
    customers_data.append({
        "customer_id": f"CUST_{i:06d}",
        "customer_name": f"Customer {i}",
        "country": random.choice(["US", "CA", "UK", "DE", "FR", "JP", "AU"]),
        "signup_date": (datetime.now() - timedelta(days=random.randint(1, 365))).strftime("%Y-%m-%d")
    })

df_customers = spark.createDataFrame(customers_data)
df_customers.write.format("csv").mode("overwrite").option("header", "true") \
    .save("/Workspace/Files/landing/daily/customers_sample.csv")

# Orders (main transactional data)
orders_data = []
for i in range(1, 10001):
    order_date = (datetime.now() - timedelta(days=random.randint(0, 90))).strftime("%Y-%m-%d")
    orders_data.append({
        "order_id": f"ORD_{i:08d}",
        "customer_id": f"CUST_{random.randint(1, 1000):06d}",
        "order_date": order_date,
        "order_amount": round(random.uniform(10, 5000), 2),
        "currency": "USD",
        "status": random.choice(["pending", "confirmed", "shipped", "delivered", "cancelled"])
    })

df_orders = spark.createDataFrame(orders_data)
df_orders.write.format("csv").mode("overwrite").option("header", "true") \
    .save("/Workspace/Files/landing/daily/orders_sample.csv")

print("✓ E-commerce sample data generated")

# COMMAND: Generate IoT Time-Series Sample Data
print("Generating IoT sensor sample data...")

iot_data = []
base_time = datetime.now() - timedelta(days=30)

for sensor_id in range(1, 11):
    for hour in range(0, 24*30):
        timestamp = (base_time + timedelta(hours=hour)).isoformat()
        iot_data.append({
            "sensor_id": f"SENSOR_{sensor_id:03d}",
            "sensor_location": f"Location_{random.choice(['A', 'B', 'C'])}",
            "timestamp": timestamp,
            "temperature": round(random.uniform(15, 35), 2),
            "humidity": round(random.uniform(30, 90), 2),
            "pressure": round(random.uniform(990, 1010), 2),
            "is_anomaly": random.choice([False, False, False, False, True])  # 20% anomalies
        })

df_iot = spark.createDataFrame(iot_data)
df_iot.write.format("csv").mode("overwrite").option("header", "true") \
    .save("/Workspace/Files/landing/daily/iot_sensors_sample.csv")

print("✓ IoT sensor sample data generated")

# COMMAND: Generate Hierarchical Organizational Data
print("Generating hierarchical organizational data...")

org_data = []
departments = ["Engineering", "Sales", "HR", "Finance", "Operations"]

for i, dept in enumerate(departments):
    for j in range(1, random.randint(5, 15)):
        emp_id = f"EMP_{i*100 + j:05d}"
        org_data.append({
            "employee_id": emp_id,
            "employee_name": f"Employee {emp_id}",
            "department": dept,
            "manager_id": random.choice([None, f"EMP_{random.randint(1, i*100 + j-1):05d}"]),
            "salary": round(random.uniform(50000, 200000), 2),
            "hire_date": (datetime.now() - timedelta(days=random.randint(365, 3650))).strftime("%Y-%m-%d")
        })

df_org = spark.createDataFrame(org_data)
df_org.write.format("csv").mode("overwrite").option("header", "true") \
    .save("/Workspace/Files/landing/daily/employees_sample.csv")

print("✓ Organizational data generated")

print("\n✓ All sample data generated successfully!")
print("\nFiles created:")
print("  /Workspace/Files/landing/daily/products_sample.csv")
print("  /Workspace/Files/landing/daily/customers_sample.csv")
print("  /Workspace/Files/landing/daily/orders_sample.csv")
print("  /Workspace/Files/landing/daily/iot_sensors_sample.csv")
print("  /Workspace/Files/landing/daily/employees_sample.csv")
```

---

## 📋 Notebook 03: Bronze Validation

**File**: `01_Bronze_Validation.py`  
**Purpose**: Validate Bronze ingestion results

```python
# Databricks notebook source
print("="*80)
print("BRONZE LAYER VALIDATION REPORT")
print("="*80)

# Check tables exist
bronze_tables = spark.sql("SHOW TABLES IN bronze").collect()
print(f"\nTables in bronze schema: {len(bronze_tables)}")
for row in bronze_tables:
    table_name = row.name
    row_count = spark.sql(f"SELECT COUNT(*) as cnt FROM bronze.{table_name}").collect()[0]["cnt"]
    print(f"  ✓ bronze.{table_name}: {row_count:,} rows")

# Ingestion log analysis
print("\nRecent Ingestion Log:")
spark.sql("""
    SELECT 
        batch_id,
        source_system,
        ingestion_timestamp,
        row_count_success,
        status
    FROM bronze.ingestion_log
    ORDER BY ingestion_timestamp DESC
    LIMIT 10
""").show()

# Quality summary
print("\n✓ Bronze layer validation complete")
```

---

## 🔧 Configuration Template: `bronze_config.json`

```json
{
  "sources": {
    "orders": {
      "type": "csv",
      "path": "/Workspace/Files/landing/daily/orders_sample.csv",
      "system_name": "ecommerce_system",
      "bronze_table": "events_raw",
      "partition_col": "ingestion_date",
      "required_columns": ["order_id", "customer_id", "order_date", "order_amount"],
      "expected_columns": 5,
      "column_types": {
        "order_id": "string",
        "customer_id": "string",
        "order_date": "date",
        "order_amount": "decimal(10,2)",
        "currency": "string"
      }
    },
    "sensors": {
      "type": "csv",
      "path": "/Workspace/Files/landing/daily/iot_sensors_sample.csv",
      "system_name": "iot_platform",
      "bronze_table": "sensor_readings_raw",
      "partition_col": "ingestion_date",
      "required_columns": ["sensor_id", "timestamp", "temperature", "humidity"],
      "expected_columns": 7,
      "column_types": {
        "sensor_id": "string",
        "timestamp": "timestamp",
        "temperature": "double",
        "humidity": "double"
      }
    }
  },
  "settings": {
    "error_handling": "capture_errors",
    "enable_logging": true,
    "retention_days": 90,
    "optimize_write": false,
    "compaction": "manual"
  }
}
```

---

## Summary

The Bronze layer:
- ✓ Ingests raw data from multiple sources
- ✓ Adds technical metadata for lineage
- ✓ Validates data quality
- ✓ Handles errors gracefully
- ✓ Logs all ingestion metrics
- ✓ Supports append/overwrite modes
- ✓ Partitions for query efficiency
- ✓ Enables replay via batch ID and row hash

Next: Silver Layer Transformation →
