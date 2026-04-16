# Example: Hierarchical Data Medallion Architecture
# Purpose: Domain-specific implementation for hierarchical/dimensional data
# This example shows how to adapt medallion architecture for star schema patterns

from pyspark.sql.functions import *
from pyspark.sql.types import *
from datetime import datetime
import json

print(f"🏛️ Hierarchical Data Medallion Architecture Example - {datetime.now()}")

# Hierarchical Fact and Dimension Tables
print("\n📋 Hierarchical Star Schema:")

# Bronze Layer - Raw Dimensions and Facts
print("\n🔵 Bronze Layer - Raw Data:")
bronze_dimensions = {
    "customer_dim_raw": {
        "key": "customer_id",
        "attributes": ["name", "country", "region", "segment", "created_date"]
    },
    "product_dim_raw": {
        "key": "product_id",
        "attributes": ["name", "category", "subcategory", "brand", "price"]
    },
    "date_dim_raw": {
        "key": "date_id",
        "attributes": ["date", "year", "quarter", "month", "day", "week", "day_of_week"]
    }
}

bronze_facts = {
    "sales_fact_raw": {
        "keys": ["customer_id", "product_id", "date_id"],
        "measures": ["quantity", "unit_price", "total_amount", "discount", "tax"]
    }
}

for dim, spec in bronze_dimensions.items():
    print(f"  {dim}: {spec['key']}")

for fact, spec in bronze_facts.items():
    print(f"  {fact}: {spec['measures']}")

# Silver Layer - Conformed Dimensions
print("\n⚪ Silver Layer - Conformed Dimensions:")
silver_dimensions = {
    "customer_dim": {
        "key": "customer_id",
        "attributes": ["name", "country", "region", "segment", "lifecycle_stage"],
        "scd_type": "Type 2
    },
    "product_dim": {
        "key": "product_id",
        "attributes": ["name", "category", "subcategory", "brand", "current_price"],
        "scd_type": "Type 2"
    },
    "date_dim": {
        "key": "date_id",
        "attributes": ["date", "year", "quarter", "month", "day", "week", "is_holiday"]
    }
}

for dim, spec in silver_dimensions.items():
    print(f"  {dim}: SCD {spec['scd_type']}")

# Silver Layer - Fact Tables
print("\n  Sales Fact (Silver):")
print("    - Deduplicated transactions")
print("    - Validated amounts and quantities")
print("    - Foreign key validation")
print("    - Slowly Changing Dimension handling")

# Gold Layer - Business Views
print("\n🟡 Gold Layer - Business Aggregations:")
gold_aggregations = {
    "sales_by_customer_product": {
        "dimensions": ["customer_segment", "product_category", "year", "month"],
        "measures": ["total_sales", "quantity", "transaction_count", "avg_transaction_value"]
    },
    "sales_by_region_time": {
        "dimensions": ["region", "date", "day_of_week"],
        "measures": ["daily_sales", "daily_quantity", "daily_avg_price"]
    },
    "customer_analytics": {
        "dimensions": ["customer_segment", "lifecycle_stage"],
        "measures": ["customer_count", "total_lifetime_value", "avg_purchase_frequency"]
    },
    "product_performance": {
        "dimensions": ["category", "brand", "product_id"],
        "measures": ["total_revenue", "units_sold", "return_rate", "profitability"]
    }
}

for agg, spec in gold_aggregations.items():
    print(f"\n  {agg}:")
    print(f"    Dimensions: {', '.join(spec['dimensions'])}")
    print(f"    Measures: {', '.join(spec['measures'])}")

# Hierarchical Quality Rules
hierarchy_quality_rules = {
    "dimension_quality": {
        "customer_dim": {
            "required_fields": ["customer_id", "name"],
            "unique_constraints": ["customer_id"],
            "validations": [
                {"field": "segment", "rule": "segment IN ('premium', 'standard', 'basic')"}
            ]
        },
        "product_dim": {
            "required_fields": ["product_id", "name", "category"],
            "unique_constraints": ["product_id"],
            "hierarchical_validations": [
                "Each product belongs to exactly one category",
                "Each category belongs to exactly one subcategory"
            ]
        }
    },
    "fact_quality": {
        "sales_fact": {
            "required_fields": ["customer_id", "product_id", "date_id"],
            "referential_integrity": [
                "customer_id must exist in customer_dim",
                "product_id must exist in product_dim",
                "date_id must exist in date_dim"
            ],
            "measure_validations": [
                {"field": "total_amount", "rule": "total_amount > 0"},
                {"field": "quantity", "rule": "quantity > 0"}
            ]
        }
    }
}

print("\n📋 Hierarchical Quality Rules:")
print(json.dumps(hierarchy_quality_rules, indent=2))

print("\n✅ Hierarchical Data Medallion Architecture Example complete!")
