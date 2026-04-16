# Example: E-Commerce Medallion Architecture
# Purpose: Domain-specific implementation for e-commerce transactions
# This example shows how to adapt medallion architecture for e-commerce use cases

from pyspark.sql.functions import *
from pyspark.sql.types import *
from datetime import datetime
import json

print(f"🛍️ E-Commerce Medallion Architecture Example - {datetime.now()}")

# E-Commerce specific entities
print("\n📋 E-Commerce Specific Tables:")

# Bronze Layer - Raw Orders
bronze_orders_schema = StructType([
    StructField("order_id", StringType()),
    StructField("order_date", DateType()),
    StructField("customer_id", StringType()),
    StructField("product_id", StringType()),
    StructField("quantity", IntegerType()),
    StructField("unit_price", DecimalType(18, 2)),
    StructField("order_status", StringType()),
    StructField("payment_method", StringType()),
    StructField("shipping_address", StringType()),
    StructField("ingestion_timestamp", TimestampType()),
    StructField("source_file", StringType()),
    StructField("batch_id", StringType())
])

# Bronze Layer - Raw Returns
bronze_returns_schema = StructType([
    StructField("return_id", StringType()),
    StructField("order_id", StringType()),
    StructField("return_date", DateType()),
    StructField("return_reason", StringType()),
    StructField("refund_amount", DecimalType(18, 2)),
    StructField("return_status", StringType()),
    StructField("ingestion_timestamp", TimestampType()),
    StructField("source_file", StringType()),
    StructField("batch_id", StringType())
])

print("✓ Bronze: orders_raw, returns_raw")

# Silver Layer - Orders Processed
silver_orders_schema = StructType([
    StructField("order_id", StringType()),
    StructField("order_date", DateType()),
    StructField("customer_id", StringType()),
    StructField("product_id", StringType()),
    StructField("quantity", IntegerType()),
    StructField("unit_price", DecimalType(18, 2)),
    StructField("total_amount", DecimalType(18, 2)),
    StructField("order_status", StringType()),
    StructField("payment_method", StringType()),
    StructField("day_of_week", IntegerType()),
    StructField("week_of_year", IntegerType()),
    StructField("month", IntegerType()),
    StructField("year", IntegerType())
])

print("✓ Silver: orders_processed, returns_processed")

# Gold Layer - Order Aggregations
print("✓ Gold: daily_orders_summary, customer_lifetime_value, product_performance")

# Gold Layer - Key Metrics
gold_aggregations = {
    "daily_orders_summary": {
        "dimensions": ["order_date", "product_category", "region"],
        "measures": [
            "total_orders",
            "total_revenue",
            "average_order_value",
            "unique_customers",
            "return_rate"
        ]
    },
    "customer_lifetime_value": {
        "dimensions": ["customer_id", "customer_segment"],
        "measures": [
            "total_purchases",
            "lifetime_value",
            "average_order_value",
            "purchase_frequency",
            "days_since_last_order"
        ]
    },
    "product_performance": {
        "dimensions": ["product_id", "product_category"],
        "measures": [
            "units_sold",
            "total_revenue",
            "return_rate",
            "average_rating",
            "inventory_level"
        ]
    }
}

print("\n📊 E-Commerce Gold Layer Aggregations:")
for table, spec in gold_aggregations.items():
    print(f"\n{table}:")
    print(f"  Dimensions: {', '.join(spec['dimensions'])}")
    print(f"  Measures: {', '.join(spec['measures'])}")

# Quality Rules for E-Commerce
ecommerce_quality_rules = {
    "orders": {
        "required_fields": ["order_id", "customer_id", "order_date", "total_amount"],
        "validations": [
            {"field": "total_amount", "rule": "amount > 0"},
            {"field": "quantity", "rule": "quantity > 0"},
            {"field": "order_status", "rule": "status IN ('completed', 'pending', 'cancelled', 'refunded')"},
            {"field": "order_date", "rule": "order_date <= current_date"}
        ]
    },
    "returns": {
        "required_fields": ["return_id", "order_id", "return_reason"],
        "validations": [
            {"field": "refund_amount", "rule": "refund_amount >= 0"},
            {"field": "return_status", "rule": "status IN ('requested', 'approved', 'rejected', 'processed')"}
        ]
    }
}

print("\n✅ E-Commerce Medallion Architecture Example complete!")
print(f"\nQuality Rules Defined: {json.dumps(ecommerce_quality_rules, indent=2)}")
