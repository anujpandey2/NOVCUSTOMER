# Example: IoT Time Series Medallion Architecture
# Purpose: Domain-specific implementation for IoT sensor data
# This example shows how to adapt medallion architecture for IoT time series use cases

from pyspark.sql.functions import *
from pyspark.sql.types import *
from datetime import datetime
import json

print(f"📡 IoT Time Series Medallion Architecture Example - {datetime.now()}")

# IoT Specific Schema
print("\n📋 IoT Time Series Tables:")

# Bronze Layer - Raw Sensor Data
bronze_sensors_schema = StructType([
    StructField("sensor_id", StringType()),
    StructField("sensor_timestamp", TimestampType()),
    StructField("temperature", DoubleType()),
    StructField("humidity", DoubleType()),
    StructField("pressure", DoubleType()),
    StructField("location", StringType()),
    StructField("device_id", StringType()),
    StructField("ingestion_timestamp", TimestampType()),
    StructField("source_file", StringType()),
    StructField("batch_id", StringType())
])

print("✓ Bronze: sensor_readings_raw")

# Silver Layer - Cleaned Time Series
silver_sensors_schema = StructType([
    StructField("sensor_id", StringType()),
    StructField("sensor_date", DateType()),
    StructField("sensor_hour", IntegerType()),
    StructField("temperature", DoubleType()),
    StructField("humidity", DoubleType()),
    StructField("pressure", DoubleType()),
    StructField("location", StringType()),
    StructField("temperature_quality_flag", StringType()),
    StructField("humidity_quality_flag", StringType()),
    StructField("anomaly_score", DoubleType())
])

print("✓ Silver: sensor_readings_cleaned")

# Gold Layer - Time Series Aggregations
print("✓ Gold: hourly_sensor_summary, daily_statistics, anomaly_alerts")

# Gold Layer - Key Metrics
gold_aggregations = {
    "hourly_sensor_summary": {
        "grain": "hourly",
        "dimensions": ["sensor_id", "location", "hour"],
        "measures": [
            "avg_temperature",
            "min_temperature",
            "max_temperature",
            "avg_humidity",
            "avg_pressure",
            "reading_count",
            "data_quality_score"
        ]
    },
    "daily_statistics": {
        "grain": "daily",
        "dimensions": ["sensor_id", "location", "date"],
        "measures": [
            "daily_temp_avg",
            "daily_temp_min",
            "daily_temp_max",
            "daily_humidity_avg",
            "daily_pressure_avg",
            "temp_variance",
            "anomaly_count"
        ]
    },
    "anomaly_alerts": {
        "grain": "event",
        "dimensions": ["sensor_id", "location", "anomaly_type"],
        "measures": [
            "anomaly_timestamp",
            "anomaly_severity",
            "anomaly_value",
            "expected_value_range"
        ]
    }
}

print("\n📊 IoT Gold Layer Aggregations:")
for table, spec in gold_aggregations.items():
    print(f"\n{table} ({spec['grain']}):")
    print(f"  Dimensions: {', '.join(spec['dimensions'])}")
    print(f"  Measures: {', '.join(spec['measures'])}")

# Time Series Quality Rules
iot_quality_rules = {
    "sensor_readings": {
        "required_fields": ["sensor_id", "sensor_timestamp", "temperature", "humidity"],
        "validations": [
            {"field": "temperature", "rule": "-50 <= temp <= 150"},
            {"field": "humidity", "rule": "0 <= humidity <= 100"},
            {"field": "pressure", "rule": "800 <= pressure <= 1100"},
            {"field": "sensor_timestamp", "rule": "not future-dated"}
        ],
        "anomaly_detection": [
            {"type": "outlier", "method": "iqr", "threshold": 1.5},
            {"type": "spike", "method": "rate_of_change", "threshold": 10},
            {"type": "missing_data", "method": "gap_detection", "max_gap_minutes": 60}
        ]
    }
}

print("\n⏰ Time Series Patterns:")
print("✓ Incremental ingestion with watermark support")
print("✓ Hourly aggregations with time windowing")
print("✓ Anomaly detection with statistical methods")
print("✓ Time series forecasting integration")

print("\n✅ IoT Time Series Medallion Architecture Example complete!")
print(f"\nQuality Rules Defined: {json.dumps(iot_quality_rules, indent=2)}")
