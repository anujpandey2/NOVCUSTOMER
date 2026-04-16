# SILVER LAYER: Data Cleaning & Validation
## Microsoft Fabric Medallion Architecture

---

## 📋 Notebook 02: Quality Rules Engine

**File**: `02_Quality_Rules_Engine.py`  
**Purpose**: Configurable data quality framework with validation and scoring  

```python
# Databricks notebook source
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import (
    col, when, count, coalesce, lit, 
    concat_ws, md5, array, explode
)
from typing import Dict, List, Tuple
import json

spark = SparkSession.builder.appName("QualityRulesEngine").getOrCreate()

# COMMAND: Load Quality Rules Configuration
config_path = "/Workspace/Files/config/quality_rules.json"
config_json = dbutils.fs.get(config_path).getValues()
quality_config = json.loads(config_json[config_path])

# COMMAND: Quality Rules Engine
class QualityRulesEngine:
    """
    Configurable data quality validation framework
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.violations = []
        self.quality_scores = {}
    
    def validate_no_nulls(self, df: DataFrame, columns: List[str]) -> Tuple[DataFrame, int]:
        """
        Check for null values in critical columns
        """
        null_checks = [col(c).isNull() for c in columns if c in df.columns]
        
        if not null_checks:
            return df, 0
        
        from pyspark.sql.functions import when, coalesce
        
        # Flag rows with nulls
        df_flagged = df.withColumn(
            "_quality_flag_null",
            when(coalesce(*null_checks), lit(True)).otherwise(lit(False))
        )
        
        violation_count = df_flagged.filter(col("_quality_flag_null")).count()
        
        if violation_count > 0:
            self.violations.append({
                "rule": "no_nulls",
                "columns": columns,
                "violation_count": violation_count
            })
        
        return df_flagged, violation_count
    
    def validate_unique_keys(self, df: DataFrame, key_columns: List[str]) -> Tuple[DataFrame, int]:
        """
        Check for duplicate keys
        """
        from pyspark.sql.window import Window
        from pyspark.sql.functions import row_number
        
        window = Window.partitionBy(key_columns)
        df_with_rn = df.withColumn("_rn", row_number().over(window))
        
        duplicate_count = df_with_rn.filter(col("_rn") > 1).count()
        
        if duplicate_count > 0:
            self.violations.append({
                "rule": "unique_keys",
                "columns": key_columns,
                "violation_count": duplicate_count
            })
        
        return df_with_rn, duplicate_count
    
    def validate_range(self, df: DataFrame, column: str, min_val, max_val) -> Tuple[DataFrame, int]:
        """
        Check values are within specified range
        """
        df_flagged = df.withColumn(
            f"_quality_flag_range_{column}",
            when((col(column) < min_val) | (col(column) > max_val), lit(True)).otherwise(lit(False))
        )
        
        violation_count = df_flagged.filter(col(f"_quality_flag_range_{column}")).count()
        
        if violation_count > 0:
            self.violations.append({
                "rule": "range_check",
                "column": column,
                "min": min_val,
                "max": max_val,
                "violation_count": violation_count
            })
        
        return df_flagged, violation_count
    
    def validate_pattern(self, df: DataFrame, column: str, pattern: str) -> Tuple[DataFrame, int]:
        """
        Check values match regex pattern
        """
        from pyspark.sql.functions import regexp_like
        
        df_flagged = df.withColumn(
            f"_quality_flag_pattern_{column}",
            when(~regexp_like(col(column), pattern), lit(True)).otherwise(lit(False))
        )
        
        violation_count = df_flagged.filter(col(f"_quality_flag_pattern_{column}")).count()
        
        if violation_count > 0:
            self.violations.append({
                "rule": "pattern_check",
                "column": column,
                "pattern": pattern,
                "violation_count": violation_count
            })
        
        return df_flagged, violation_count
    
    def calculate_quality_score(self, df: DataFrame, total_rows: int) -> float:
        """
        Calculate overall data quality score (0-100)
        """
        violation_rows = sum(v.get("violation_count", 0) for v in self.violations)
        quality_score = max(0, 100 - (violation_rows / total_rows * 100))
        return round(quality_score, 2)
    
    def generate_report(self, total_rows: int) -> Dict:
        """
        Generate quality report
        """
        quality_score = self.calculate_quality_score(None, total_rows)
        
        return {
            "total_rows": total_rows,
            "violations": self.violations,
            "violation_count": sum(v.get("violation_count", 0) for v in self.violations),
            "quality_score": quality_score,
            "status": "PASS" if quality_score >= 95 else "WARN" if quality_score >= 80 else "FAIL"
        }

# COMMAND: Apply Quality Rules
engine = QualityRulesEngine(quality_config)

# Read Bronze data
df_bronze = spark.sql("SELECT * FROM bronze.events_raw LIMIT 100000")
total_rows = df_bronze.count()

print(f"Processing {total_rows} rows...")

# Apply rules from config
rules = quality_config.get("rules", {})

for rule_name, rule_config in rules.items():
    if rule_name == "no_nulls" and "columns" in rule_config:
        df_bronze, violation_count = engine.validate_no_nulls(df_bronze, rule_config["columns"])
        print(f"✓ No-null check: {violation_count} violations")
    
    elif rule_name == "unique_keys" and "columns" in rule_config:
        df_bronze, violation_count = engine.validate_unique_keys(df_bronze, rule_config["columns"])
        print(f"✓ Unique key check: {violation_count} violations")
    
    elif rule_name == "range_checks":
        for col_config in rule_config:
            col_name = col_config["column"]
            df_bronze, violation_count = engine.validate_range(
                df_bronze,
                col_name,
                col_config["min"],
                col_config["max"]
            )
            print(f"✓ Range check on {col_name}: {violation_count} violations")

# Generate report
quality_report = engine.generate_report(total_rows)

print("\n" + "="*80)
print("DATA QUALITY REPORT")
print("="*80)
print(f"Total Rows: {quality_report['total_rows']:,}")
print(f"Violations: {quality_report['violation_count']:,}")
print(f"Quality Score: {quality_report['quality_score']:.1f}%")
print(f"Status: {quality_report['status']}")
print("\nDetailed Violations:")
for violation in quality_report['violations']:
    print(f"  - {violation['rule']}: {violation.get('violation_count', 0)} violations")

# Log to quality metrics table
spark.sql("""
    CREATE TABLE IF NOT EXISTS silver.quality_metrics (
        run_id STRING,
        source_table STRING,
        total_rows LONG,
        violation_count LONG,
        quality_score FLOAT,
        check_timestamp TIMESTAMP,
        rule_details STRING
    )
    USING DELTA
""")
```

---

## 📋 Notebook 03: Silver Transformation

**File**: `02_Silver_Transform.py`  
**Purpose**: Deduplicate, validate, cleanse, and transform Bronze data to Silver  

```python
# Databricks notebook source
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import (
    col, when, expr, lit, row_number, 
    current_timestamp, md5, concat_ws,
    lead, lag, coalesce
)
from pyspark.sql.window import Window
from datetime import datetime
import json

spark = SparkSession.builder.appName("SilverTransformation").getOrCreate()

# Silver layer Spark config (balanced)
spark.conf.set("spark.sql.parquet.vorder.default", "true")
spark.conf.set("spark.databricks.delta.optimizeWrite.enabled", "false")
spark.conf.set("spark.sql.adaptive.enabled", "true")
spark.conf.set("spark.sql.shuffle.partitions", "100")

# COMMAND: Load Bronze Data
print("Loading Bronze data...")

df_bronze = spark.sql("""
    SELECT *
    FROM bronze.events_raw
    WHERE _ingestion_date >= DATE(DATE_SUB(CURRENT_DATE(), 7))  -- Last 7 days
""")

bronze_count = df_bronze.count()
print(f"✓ Loaded {bronze_count:,} rows from Bronze")

# COMMAND: Step 1: Deduplication
print("\nStep 1: Deduplication...")

window_spec = Window.partitionBy("order_id", "order_date").orderBy(col("_insertion_timestamp").desc())

df_dedup = df_bronze \
    .withColumn("_row_number", row_number().over(window_spec)) \
    .filter(col("_row_number") == 1) \
    .drop("_row_number")

dedup_count = df_dedup.count()
duplicates_removed = bronze_count - dedup_count

print(f"  Original rows: {bronze_count:,}")
print(f"  Deduplicated rows: {dedup_count:,}")
print(f"  Duplicates removed: {duplicates_removed:,} ({duplicates_removed/bronze_count*100:.1f}%)")

# COMMAND: Step 2: Data Cleansing
print("\nStep 2: Data Cleansing...")

df_clean = df_dedup \
    # Remove rows with null in critical columns
    .filter(col("order_id").isNotNull()) \
    .filter(col("customer_id").isNotNull()) \
    .filter(col("order_date").isNotNull()) \
    \
    # Fill null amounts with 0
    .withColumn("order_amount", coalesce(col("order_amount"), lit(0.0))) \
    \
    # Fix data type issues
    .withColumn("order_date", col("order_date").cast("date")) \
    .withColumn("order_amount", col("order_amount").cast("decimal(10,2)")) \
    \
    # Standardize string columns
    .withColumn("status", lower(trim(col("status")))) \
    .withColumn("currency", upper(trim(col("currency"))))

clean_count = df_clean.count()
rows_filtered = dedup_count - clean_count

print(f"  Clean rows: {clean_count:,}")
print(f"  Rows filtered: {rows_filtered:,}")

# COMMAND: Step 3: Data Enrichment
print("\nStep 3: Data Enrichment...")

df_enriched = df_clean \
    # Add derived columns
    .withColumn("order_year", year(col("order_date"))) \
    .withColumn("order_month", month(col("order_date"))) \
    .withColumn("order_week", weekofyear(col("order_date"))) \
    \
    # Add flags for business logic
    .withColumn("is_high_value", when(col("order_amount") > 1000, True).otherwise(False)) \
    .withColumn("is_refunded", when(col("status") == "refunded", True).otherwise(False)) \
    \
    # Add processing metadata
    .withColumn("_silver_transform_timestamp", current_timestamp()) \
    .withColumn("_row_hash_silver", md5(concat_ws("|", *df_clean.columns)))

print(f"  ✓ Enrichment complete: {df_enriched.columns.count()} columns")

# COMMAND: Step 4: Schema Conformance
print("\nStep 4: Schema Conformance...")

# Define target Silver schema
df_silver = df_enriched.select(
    # Business keys
    col("order_id"),
    col("customer_id"),
    col("order_date"),
    
    # Fact columns
    col("order_amount").alias("amount"),
    col("currency"),
    col("status"),
    
    # Time dimensions
    col("order_year").alias("year"),
    col("order_month").alias("month"),
    col("order_week").alias("week"),
    
    # Flags
    col("is_high_value"),
    col("is_refunded"),
    
    # Lineage
    col("_ingestion_id").alias("_bronze_batch_id"),
    col("_source_system"),
    col("_ingestion_timestamp").alias("_bronze_ingestion_time"),
    col("_silver_transform_timestamp"),
    col("_row_hash_silver")
)

silver_count = df_silver.count()
print(f"  ✓ Schema conformance: {silver_count:,} rows, {len(df_silver.columns)} columns")

# COMMAND: Step 5: Write to Silver
print("\nStep 5: Writing to Silver...")

df_silver.write \
    .format("delta") \
    .mode("append") \
    .partitionBy("order_date") \
    .option("mergeSchema", "true") \
    .saveAsTable("silver.events_cleaned")

print(f"  ✓ Written {silver_count:,} rows to silver.events_cleaned")

# COMMAND: Validation & Reconciliation
print("\nValidation & Reconciliation:")

# Check unique keys
unique_order_ids = df_silver.select("order_id").distinct().count()
print(f"  ✓ Unique order IDs: {unique_order_ids:,}")

# Check data types
print(f"  ✓ Data types:")
for field in df_silver.schema.fields:
    print(f"    - {field.name}: {field.dataType}")

# Reconciliation
reconciliation = spark.sql("""
    SELECT 
        COUNT(*) as silver_rows,
        COUNT(DISTINCT order_id) as unique_orders,
        COUNT(DISTINCT customer_id) as unique_customers,
        MIN(order_date) as min_date,
        MAX(order_date) as max_date,
        SUM(amount) as total_amount
    FROM silver.events_cleaned
""")

reconciliation.show()

print(f"\n✓ Silver transformation complete!")
```

---

## 📋 Notebook 04: Silver Validation & Lineage

**File**: `02_Silver_Validation.py`  

```python
# Databricks notebook source
print("="*80)
print("SILVER LAYER VALIDATION & LINEAGE REPORT")
print("="*80)

# COMMAND: Table Lineage
lineage_sql = """
SELECT 
    'bronze.events_raw' as source_table,
    'silver.events_cleaned' as target_table,
    (SELECT COUNT(*) FROM bronze.events_raw) as source_row_count,
    (SELECT COUNT(*) FROM silver.events_cleaned) as target_row_count,
    CURRENT_TIMESTAMP() as lineage_timestamp
"""

spark.sql(f"""
    CREATE TABLE IF NOT EXISTS silver.table_lineage (
        source_table STRING,
        target_table STRING,
        source_row_count LONG,
        target_row_count LONG,
        lineage_timestamp TIMESTAMP
    )
    USING DELTA
""")

spark.sql(f"INSERT INTO silver.table_lineage {lineage_sql}")

print("Lineage tracked:")
spark.sql("SELECT * FROM silver.table_lineage ORDER BY lineage_timestamp DESC LIMIT 10").show()

# COMMAND: Quality Metrics
print("\nData Quality Metrics:")

spark.sql("""
    SELECT 
        COUNT(*) as total_rows,
        COUNT(DISTINCT order_id) as unique_orders,
        COUNT(CASE WHEN amount IS NULL THEN 1 END) as null_amounts,
        COUNT(CASE WHEN amount < 0 THEN 1 END) as negative_amounts,
        CAST(SUM(amount) as DECIMAL(15,2)) as total_sales
    FROM silver.events_cleaned
""").show()

print("\n✓ Silver validation complete")
```

---

## GOLD LAYER: Analytics Ready Aggregations

---

## 📋 Notebook 05: Gold Aggregations

**File**: `03_Gold_Aggregations.py`  
**Purpose**: Create business-ready analytics tables with optimal performance  

```python
# Databricks notebook source
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, sum as spark_sum, avg, min, max, count, 
    date_trunc, current_timestamp, to_date
)

spark = SparkSession.builder.appName("GoldAggregations").getOrCreate()

# Gold layer Spark config (read-optimized)
spark.conf.set("spark.sql.parquet.vorder.default", "true")
spark.conf.set("spark.databricks.delta.optimizeWrite.enabled", "true")
spark.conf.set("spark.databricks.delta.optimizeWrite.binSize", "1g")
spark.conf.set("spark.sql.adaptive.enabled", "true")
spark.conf.set("spark.sql.shuffle.partitions", "50")

print("✓ Gold layer Spark config applied")

# COMMAND: Daily Summary Table
print("\nCreating gold.events_daily_summary...")

df_daily = spark.sql("""
    SELECT 
        order_date as summary_date,
        status as order_status,
        COUNT(*) as metric_order_count,
        COUNT(DISTINCT customer_id) as metric_unique_customers,
        SUM(amount) as metric_total_amount,
        AVG(amount) as metric_avg_amount,
        MIN(amount) as metric_min_amount,
        MAX(amount) as metric_max_amount,
        SUM(CASE WHEN is_high_value THEN 1 ELSE 0 END) as metric_high_value_orders,
        CURRENT_TIMESTAMP() as created_timestamp
    FROM silver.events_cleaned
    GROUP BY order_date, status
    ORDER BY order_date DESC
""")

df_daily.write \
    .format("delta") \
    .mode("overwrite") \
    .partitionBy("summary_date") \
    .option("mergeSchema", "true") \
    .saveAsTable("gold.events_daily_summary")

print(f"  ✓ Created gold.events_daily_summary: {df_daily.count()} rows")

# COMMAND: Customer Segment Analysis
print("\nCreating gold.customer_segment_analysis...")

df_segment = spark.sql("""
    SELECT 
        customer_id,
        COUNT(*) as lifetime_order_count,
        SUM(amount) as lifetime_value,
        AVG(amount) as avg_order_value,
        MIN(order_date) as first_order_date,
        MAX(order_date) as last_order_date,
        DATEDIFF(MAX(order_date), MIN(order_date)) as customer_lifetime_days,
        CASE 
            WHEN SUM(amount) > 5000 THEN 'VIP'
            WHEN SUM(amount) > 1000 THEN 'High-Value'
            WHEN SUM(amount) > 100 THEN 'Regular'
            ELSE 'New'
        END as customer_segment,
        CURRENT_TIMESTAMP() as created_timestamp
    FROM silver.events_cleaned
    GROUP BY customer_id
""")

df_segment.write \
    .format("delta") \
    .mode("overwrite") \
    .option("mergeSchema", "true") \
    .saveAsTable("gold.customer_segment_analysis")

print(f"  ✓ Created gold.customer_segment_analysis: {df_segment.count()} rows")

# COMMAND: Monthly Trend Analysis
print("\nCreating gold.monthly_trend...")

df_monthly = spark.sql("""
    SELECT 
        CONCAT(YEAR(order_date), '-', LPAD(MONTH(order_date), 2, '0')) as month_key,
        status,
        COUNT(*) as order_count,
        SUM(amount) as total_revenue,
        AVG(amount) as avg_order_value,
        COUNT(DISTINCT customer_id) as unique_customers
    FROM silver.events_cleaned
    GROUP BY YEAR(order_date), MONTH(order_date), status
    ORDER BY month_key DESC
""")

df_monthly.write \
    .format("delta") \
    .mode("overwrite") \
    .option("mergeSchema", "true") \
    .saveAsTable("gold.monthly_trend_analysis")

print(f"  ✓ Created gold.monthly_trend_analysis: {df_monthly.count()} rows")

print("\n✓ Gold aggregations complete!")
```

---

## 📋 Notebook 06: Gold Optimization & Validation

**File**: `03_Gold_Validation.py`  

```python
# Databricks notebook source
print("="*80)
print("GOLD LAYER OPTIMIZATION & VALIDATION")
print("="*80)

# COMMAND: Optimize all Gold tables
gold_tables = ["events_daily_summary", "customer_segment_analysis", "monthly_trend_analysis"]

for table_name in gold_tables:
    print(f"\nOptimizing gold.{table_name}...")
    
    # Run OPTIMIZE with ZORDER
    if table_name == "events_daily_summary":
        spark.sql(f"""
            OPTIMIZE gold.{table_name}
            ZORDER BY (summary_date, order_status)
        """)
    else:
        spark.sql(f"OPTIMIZE gold.{table_name}")
    
    print(f"  ✓ Optimization complete")

# COMMAND: Collect Statistics
print("\nCollecting table statistics...")

for table_name in gold_tables:
    spark.sql(f"ANALYZE TABLE gold.{table_name} COMPUTE STATISTICS")
    print(f"  ✓ Statistics collected for gold.{table_name}")

# COMMAND: Validation & Performance Profiling
print("\nPerformance Metrics:")

for table_name in gold_tables:
    stats = spark.sql(f"""
        SELECT 
            COUNT(*) as total_rows,
            COUNT(DISTINCT _bronze_batch_id) as unique_batches
        FROM gold.{table_name}
    """).collect()[0]
    
    print(f"  gold.{table_name}:")
    print(f"    - Rows: {stats['total_rows']:,}")
    print(f"    - Batches: {stats['unique_batches']}")

print("\n✓ Gold layer validation complete!")
```

---

## Summary

**Bronze Layer** (Raw Ingestion):
- Generic multi-format ingestion
- Metadata tracking
- Error handling and logging
- Append-only partitioning

**Silver Layer** (Cleaning & Validation):
- Deduplication and quality checks
- Data cleansing and standardization
- Enrichment and schema conformance
- Lineage tracking

**Gold Layer** (Analytics):
- Business-ready aggregations
- Optimized for reporting
- V-Order and ZORDER configuration
- Performance profiling

→ Next: Orchestration Pipeline
