# Notebook: Work Items Silver Transform - Data Cleaning
# Purpose: Clean Bronze table and create Silver Delta table
# Author: Fabric Analytics Pipeline
# Date: 2025-03-30

# CELL 1: IMPORTS & CONFIGURATION ==========================================

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, when, isnan, isnull, trim, coalesce, 
    count, countDistinct, sum as spark_sum, avg, min as spark_min, max as spark_max
)
from datetime import datetime

# Configuration
LAKEHOUSE_NAME = "Fabric_Product_LKH"
BRONZE_TABLE = "WorkItems_Bronze"
SILVER_TABLE = "Cleaned_Items_Silver"

# Initialize Spark
spark = SparkSession.builder.appName("SilverTransform").getOrCreate()

print("✓ Spark session initialized")
print(f"  Lakehouse: {LAKEHOUSE_NAME}")
print(f"  Bronze table: {BRONZE_TABLE}")
print(f"  Silver table: {SILVER_TABLE}")

# CELL 2: READ BRONZE TABLE ==========================================

print(f"\n📖 Reading Bronze table: {BRONZE_TABLE}...")

try:
    bronze_path = f"abfss://{LAKEHOUSE_NAME}@onelake.dfs.fabric.microsoft.com/Tables/{BRONZE_TABLE}"
    df_bronze = spark.read.format("delta").load(bronze_path)
    
    print(f"✓ Bronze table loaded")
    print(f"  Records: {df_bronze.count()}")
    print(f"  Columns: {len(df_bronze.columns)}")
    print(f"\n  Schema:")
    df_bronze.printSchema()
    
except Exception as e:
    print(f"✗ Error reading Bronze table: {str(e)}")
    raise

# CELL 3: DATA QUALITY ANALYSIS ==========================================

print(f"\n📊 Data Quality Analysis (Pre-Cleaning)...")

quality_stats = {
    'total_rows': df_bronze.count(),
    'total_cols': len(df_bronze.columns)
}

# Count nulls per column
print(f"\nNull/Empty value counts:")
for col_name in df_bronze.columns:
    null_count = df_bronze.filter(
        (col(col_name).isNull()) | 
        (trim(col(col_name)).eqNullSafe(''))
    ).count()
    
    pct = (null_count / quality_stats['total_rows'] * 100) if quality_stats['total_rows'] > 0 else 0
    
    print(f"  {col_name}: {null_count} nulls ({pct:.1f}%)")

# Detailed stats for key columns
print(f"\nKey column statistics:")
for key_col in ['WorkItemType', 'State', 'Status']:
    if key_col in df_bronze.columns:
        counts = df_bronze.groupBy(key_col).count().collect()
        print(f"\n  {key_col}:")
        for row in sorted(counts, key=lambda x: x[1], reverse=True):
            print(f"    {row[0]}: {row[1]}")

# CELL 4: DEFINE CLEANING RULES ==========================================

print(f"\n🧹 Cleaning Rules:")
print(f"  1. Remove rows where Title (Name) IS NULL or empty")
print(f"  2. Remove rows where Description IS NULL or empty")
print(f"  3. Keep all other rows as-is")

# CELL 5: APPLY CLEANING TRANSFORMATION ==========================================

print(f"\n🔄 Applying cleaning transformations...")

# Apply cleaning rules
df_cleaned = df_bronze.filter(
    # Title must not be null and not be empty string
    (col("Title").isNotNull()) & 
    (trim(col("Title")) != "") &
    # Description must not be null and not be empty string
    (col("Description").isNotNull()) & 
    (trim(col("Description")) != "")
)

print(f"✓ Cleaning complete")
print(f"  Original records: {quality_stats['total_rows']}")
print(f"  Cleaned records: {df_cleaned.count()}")
print(f"  Rows removed: {quality_stats['total_rows'] - df_cleaned.count()}")
print(f"  Retention rate: {(df_cleaned.count() / quality_stats['total_rows'] * 100):.1f}%")

# CELL 6: VALIDATE CLEANED DATA ==========================================

print(f"\n✅ Validating cleaned data...")

# Verify no nulls in critical columns
critical_cols = ['WorkItemId', 'Title', 'Description']
validation_errors = []

for col_name in critical_cols:
    null_count = df_cleaned.filter(col(col_name).isNull()).count()
    if null_count > 0:
        validation_errors.append(f"  ✗ {col_name} has {null_count} nulls")
    else:
        print(f"  ✓ {col_name}: No nulls")

if validation_errors:
    print("\nValidation errors:")
    for error in validation_errors:
        print(error)
else:
    print("✓ All validation checks passed")

# CELL 7: SAMPLE DATA DISPLAY ==========================================

print(f"\n📋 Sample of cleaned data:")
print(f"\nFirst 5 rows:")
df_cleaned.select(
    col("WorkItemId"),
    col("Title"),
    col("WorkItemType"),
    col("State"),
    col("CustomerPromise")
).show(5, truncate=False)

print(f"\nData types:")
df_cleaned.printSchema()

# CELL 8: CREATE SILVER DELTA TABLE ==========================================

print(f"\n💾 Writing Silver Delta table: {SILVER_TABLE}...")

try:
    silver_path = f"abfss://{LAKEHOUSE_NAME}@onelake.dfs.fabric.microsoft.com/Tables/{SILVER_TABLE}"
    
    df_cleaned.write \
        .format("delta") \
        .mode("overwrite") \
        .option("mergeSchema", "true") \
        .save(silver_path)
    
    print(f"✓ Silver table created: {SILVER_TABLE}")
    print(f"  Path: {silver_path}")
    print(f"  Records: {df_cleaned.count()}")
    print(f"  Columns: {len(df_cleaned.columns)}")
    
except Exception as e:
    print(f"✗ Error creating Silver table: {str(e)}")
    raise

# CELL 9: VERIFY SILVER TABLE ==========================================

print(f"\n✓ Verifying Silver table...")

try:
    df_silver = spark.read.format("delta").load(silver_path)
    
    print(f"  Records: {df_silver.count()}")
    print(f"  Columns: {', '.join(df_silver.columns)}")
    
    # Calculate summary statistics
    print(f"\n📈 Silver table summary:")
    summary = df_silver.select(
        countDistinct("WorkItemId").alias("UniqueItems"),
        countDistinct("WorkItemType").alias("ItemTypes"),
        countDistinct("State").alias("States"),
        countDistinct("AssignedTo").alias("AssignedUsers")
    ).collect()
    
    for row in summary:
        print(f"  Unique work items: {row['UniqueItems']}")
        print(f"  Work item types: {row['ItemTypes']}")
        print(f"  States: {row['States']}")
        print(f"  Assigned users: {row['AssignedUsers']}")
    
except Exception as e:
    print(f"✗ Error verifying Silver table: {str(e)}")
    raise

# ═══════════════════════════════════════════════════════════════════════════

print("\n" + "="*70)
print("✅ SILVER TABLE TRANSFORMATION COMPLETE")
print("="*70)
print(f"\n✓ Ready for semantic model creation")
print(f"  Silver table: {SILVER_TABLE}")
print(f"  Total records: {df_silver.count()}")
print(f"  Quality: All Title and Description fields populated")
