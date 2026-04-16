# Fabric Medallion Architecture - Phase 0: Generate Sample Data
# Purpose: Create realistic sample datasets for testing medallion flow
# Execution: Run first to seed test data
# Dependencies: None

from pyspark.sql.types import *
from pyspark.sql.functions import *
from datetime import datetime, timedelta
import json
import random

# Configuration
config = {
    "num_events": 100000,
    "num_transactions": 50000,
    "num_days": 30,
    "sample_data_path": "Files/sample_data"
}

print(f"🚀 Starting sample data generation at {datetime.now()}")
print(f"Configuration: {json.dumps(config, indent=2)}")

# Create event data
event_types = ["page_view", "purchase", "cart_add", "checkout", "login", "logout"]
sources = ["web", "mobile_app", "api", "third_party"]
users = [f"USER_{i:06d}" for i in range(1000)]

events_data = []
for i in range(config["num_events"]):
    days_back = random.randint(0, config["num_days"] - 1)
    hours_offset = random.randint(0, 23)
    minutes_offset = random.randint(0, 59)
    
    event_timestamp = datetime.now() - timedelta(days=days_back, hours=hours_offset, minutes=minutes_offset)
    
    events_data.append({
        "event_id": f"EVT_{i:010d}",
        "event_type": random.choice(event_types),
        "event_timestamp": event_timestamp,
        "source_system": random.choice(sources),
        "user_id": random.choice(users),
        "properties": json.dumps({
            "session_id": f"SESSION_{random.randint(100000, 999999)}",
            "page_url": f"https://example.com/page/{random.randint(1, 1000)}",
            "referrer": random.choice(["direct", "google", "facebook", "other"])
        })
    })

# Create transaction data
statuses = ["completed", "pending", "failed", "refunded"]
currencies = ["USD", "EUR", "GBP"]
merchants = [f"MERCHANT_{i:04d}" for i in range(100)]
customers = [f"CUST_{i:06d}" for i in range(500)]

transactions_data = []
for i in range(config["num_transactions"]):
    days_back = random.randint(0, config["num_days"] - 1)
    hours_offset = random.randint(0, 23)
    minutes_offset = random.randint(0, 59)
    
    transaction_date = (datetime.now() - timedelta(days=days_back)).date()
    transaction_timestamp = datetime.combine(
        transaction_date,
        datetime.min.time()
    ) + timedelta(hours=hours_offset, minutes=minutes_offset)
    
    transactions_data.append({
        "transaction_id": f"TXN_{i:010d}",
        "transaction_date": transaction_date,
        "transaction_timestamp": transaction_timestamp,
        "amount": round(random.uniform(10, 5000), 2),
        "currency": random.choice(currencies),
        "customer_id": random.choice(customers),
        "merchant_id": random.choice(merchants),
        "status": random.choice(statuses)
    })

# Create DataFrames
events_schema = StructType([
    StructField("event_id", StringType()),
    StructField("event_type", StringType()),
    StructField("event_timestamp", TimestampType()),
    StructField("source_system", StringType()),
    StructField("user_id", StringType()),
    StructField("properties", StringType())
])

transactions_schema = StructType([
    StructField("transaction_id", StringType()),
    StructField("transaction_date", DateType()),
    StructField("transaction_timestamp", TimestampType()),
    StructField("amount", DecimalType(18, 2)),
    StructField("currency", StringType()),
    StructField("customer_id", StringType()),
    StructField("merchant_id", StringType()),
    StructField("status", StringType())
])

events_df = spark.createDataFrame(events_data, schema=events_schema)
transactions_df = spark.createDataFrame(transactions_data, schema=transactions_schema)

# Write to Files folder as CSV for ingestion
print("\n📝 Writing sample data to Files folder...")
events_df.coalesce(1).write.mode("overwrite").format("csv").option("header", "true").save(f"{config['sample_data_path']}/events.csv")
transactions_df.coalesce(1).write.mode("overwrite").format("csv").option("header", "true").save(f"{config['sample_data_path']}/transactions.csv")

# Print summary
print("\n✅ Sample data generation complete!")
print(f"Events generated: {len(events_data):,}")
print(f"Transactions generated: {len(transactions_data):,}")
print(f"Date range: Last {config['num_days']} days")
print(f"Saved to: {config['sample_data_path']}")
print(f"Events sample:\n{events_df.limit(5).toPandas().to_string()}")
print(f"\nTransactions sample:\n{transactions_df.limit(5).toPandas().to_string()}")
