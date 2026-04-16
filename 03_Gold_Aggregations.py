# Fabric Medallion Architecture - Phase 3: Gold Aggregations
# Purpose: Create aggregated analytics tables in Gold layer
# Execution: Run after silver validation
# Dependencies: 02_Silver_Validation.py

from pyspark.sql.functions import *
from datetime import datetime
import uuid
import json

print(f"🟡 Gold Layer Aggregations - {datetime.now()}")

# Configure Spark for read-optimized Gold layer
spark.conf.set("spark.sql.parquet.vorder.default", "true")
spark.conf.set("spark.databricks.delta.optimizeWrite.enabled", "true")
spark.conf.set("spark.databricks.delta.optimizeWrite.binSize", "1g")

print("✓ Spark optimization config set for Gold layer")

# Create daily transaction summary
print("\n📊 Creating daily transaction summary...")
transactions_daily = (spark.table("silver.transactions_cleaned")
    .groupBy(
        col("transaction_date").alias("period_date"),
        lit("general").alias("category"),
        lit("global").alias("region"),
        lit("standard").alias("customer_segment")
    )
    .agg(
        sum("amount").alias("total_amount"),
        count("*").alias("transaction_count"),
        avg("amount").alias("average_amount"),
        countDistinct("customer_id").alias("unique_customers"),
        current_timestamp().alias("created_timestamp")
    )
)

transactions_daily.write.mode("overwrite").partitionBy("period_date").format("delta").saveAsTable("gold.gold_transactions_daily")
daily_count = transactions_daily.count()
print(f"✓ Daily summaries created: {daily_count}")

# Create customer metrics
print("\n📊 Creating customer analytics...")
customer_metrics = (spark.table("silver.transactions_cleaned")
    .groupBy(
        col("transaction_date").alias("period_date"),
        col("customer_id"),
        lit("standard").alias("customer_segment")
    )
    .agg(
        sum("amount").alias("lifetime_value"),
        count("*").alias("transaction_frequency"),
        datediff(lit(datetime.now().date()), max("transaction_date")).alias("days_since_last_transaction"),
        avg("amount").alias("average_transaction_value"),
        current_timestamp().alias("created_timestamp")
    )
)

customer_metrics.write.mode("overwrite").partitionBy("period_date").format("delta").saveAsTable("gold.gold_customer_metrics")
customer_count = customer_metrics.count()
print(f"✓ Customer metrics created: {customer_count}")

# Create monthly summary
print("\n📊 Creating monthly aggregations...")
monthly_summary = (spark.table("silver.transactions_cleaned")
    .groupBy(
        year("transaction_date").alias("year"),
        month("transaction_date").alias("month"),
        lit("general").alias("category")
    )
    .agg(
        count("*").alias("total_transactions"),
        sum("amount").alias("total_amount"),
        countDistinct("customer_id").alias("unique_customers"),
        current_timestamp().alias("created_timestamp")
    )
)

monthly_summary.write.mode("overwrite").partitionBy("year", "month").format("delta").saveAsTable("gold.gold_summary_monthly")
monthly_count = monthly_summary.count()
print(f"✓ Monthly summaries created: {monthly_count}")

# Optimize Gold tables
print("\n⚡ Optimizing Gold tables with ZORDER...")
spark.sql("OPTIMIZE TABLE gold.gold_transactions_daily ZORDER BY (category, region)")
spark.sql("OPTIMIZE TABLE gold.gold_customer_metrics ZORDER BY (customer_segment, customer_id)")
spark.sql("OPTIMIZE TABLE gold.gold_summary_monthly ZORDER BY (category)")
print("✓ Gold tables optimized with ZORDER")

# Log aggregations
log_id = str(uuid.uuid4())
spark.sql(f"""
    INSERT INTO bronze.medallion_logs
    VALUES (
        '{log_id}',
        current_timestamp(),
        'gold',
        'aggregation',
        'success',
        'Gold layer aggregations completed',
        {daily_count + customer_count + monthly_count},
        0
    )
""")

print(f"\n✅ Gold aggregations complete!")
print(f"Daily summaries: {daily_count}")
print(f"Customer metrics: {customer_count}")
print(f"Monthly summaries: {monthly_count}")
