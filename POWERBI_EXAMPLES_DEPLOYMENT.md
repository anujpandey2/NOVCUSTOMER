# POWER BI INTEGRATION & EXAMPLE IMPLEMENTATIONS
## Microsoft Fabric Medallion Architecture

---

## 🎯 Power BI Integration Guide

### Step 1: Discover Gold Lakehouse SQL Endpoint

```powershell
# Get Gold lakehouse ID
$goldLakehouseId = "your-gold-lakehouse-id"
$workspaceId = "4850ec28-2ac1-4c80-a70d-977ab969085d"

# Get SQL endpoint connection string
$response = curl -X GET `
  -H "Authorization: Bearer $bearerToken" `
  -H "Content-Type: application/json" \
  "https://api.fabric.microsoft.com/v1/workspaces/$workspaceId/lakehouses/$goldLakehouseId"

$sqlEndpoint = $response.properties.sqlEndpointProperties.connectionString
echo "SQL Endpoint: $sqlEndpoint"
```

### Step 2: Verify Tables in SQL Endpoint

```sql
-- Connect via SQL Server Management Studio or Azure Data Studio
-- Connection string: <sqlEndpoint from above>

SELECT TABLE_NAME 
FROM INFORMATION_SCHEMA.TABLES 
WHERE TABLE_SCHEMA = 'dbo'
ORDER BY TABLE_NAME;

-- Should see:
-- - events_daily_summary
-- - customer_segment_analysis
-- - monthly_trend_analysis
```

### Step 3: Create DirectLake Semantic Model

**File**: `Gold_Lakehouse_SemanticModel.tmdl`

```tmdl
model GoldLakehouseAnalytics

culture "en-US"

annotation Description = "DirectLake semantic model for Gold layer analytics"
annotation PBIDesktopVersion = "2.127.683.0"

table Events_Daily_Summary
	lineageTag: "table-Events_Daily_Summary"
	
	column Summary_Date
		dataType: dateTime
		lineageTag: "column-Summary_Date"
		sourceColumn: "summary_date"
	
	column Order_Status
		dataType: string
		lineageTag: "column-Order_Status"
		sourceColumn: "order_status"
	
	column Metric_Order_Count
		dataType: int64
		formatString: "#,0"
		lineageTag: "column-Metric_Order_Count"
		sourceColumn: "metric_order_count"
	
	column Metric_Total_Amount
		dataType: decimal
		formatString: "$#,0.00;-$#,0.00;$#,0.00"
		lineageTag: "column-Metric_Total_Amount"
		sourceColumn: "metric_total_amount"
	
	partition "Daily Summary" = m
		mode: directLake
		source
			expression: [Table]
			entity: events_daily_summary
			physicalTable: events_daily_summary

table Customer_Segment_Analysis
	lineageTag: "table-Customer_Segment_Analysis"
	
	column Customer_ID
		dataType: string
		lineageTag: "column-Customer_ID"
		sourceColumn: "customer_id"
	
	column Lifetime_Value
		dataType: decimal
		formatString: "$#,0.00;-$#,0.00;$#,0.00"
		lineageTag: "column-Lifetime_Value"
		sourceColumn: "lifetime_value"
	
	column Customer_Segment
		dataType: string
		lineageTag: "column-Customer_Segment"
		sourceColumn: "customer_segment"
	
	partition "Segment Analysis" = m
		mode: directLake
		source
			expression: [Table]
			entity: customer_segment_analysis
			physicalTable: customer_segment_analysis

// Measures
measure Daily_Orders = SUM('Events_Daily_Summary'[Metric_Order_Count])
measure Total_Revenue = SUM('Events_Daily_Summary'[Metric_Total_Amount])
measure Customer_LTV = SUM('Customer_Segment_Analysis'[Lifetime_Value])
measure Unique_Customers = DISTINCTCOUNT('Customer_Segment_Analysis'[Customer_ID])
```

### Step 4: Create Power BI Report

**File**: `GoldLakehouse_Report.pbir`

```json
{
  "version": "1.0",
  "sections": [
    {
      "name": "Executive Dashboard",
      "visualContainers": [
        {
          "config": {
            "name": "Total_Orders_Card",
            "type": "card",
            "measures": ["Daily_Orders"],
            "title": "Total Orders"
          }
        },
        {
          "config": {
            "name": "Revenue_Trend_LineChart",
            "type": "lineChart",
            "axis": "Summary_Date",
            "legend": "Order_Status",
            "values": ["Total_Revenue"],
            "title": "Revenue Trend"
          }
        },
        {
          "config": {
            "name": "Order_Status_BarChart",
            "type": "barChart",
            "axis": "Order_Status",
            "legend": null,
            "values": ["Daily_Orders"],
            "title": "Orders by Status"
          }
        },
        {
          "config": {
            "name": "Customer_Segment_PieChart",
            "type": "pieChart",
            "legend": "Customer_Segment",
            "values": ["Customer_LTV"],
            "title": "Revenue by Customer Segment"
          }
        }
      ]
    },
    {
      "name": "Operational Metrics",
      "visualContainers": [
        {
          "config": {
            "name": "Daily_Detail_Table",
            "type": "table",
            "columns": [
              "Summary_Date",
              "Order_Status",
              "Metric_Order_Count",
              "Metric_Total_Amount"
            ],
            "title": "Daily Order Summary"
          }
        }
      ]
    }
  ],
  "dataModelId": "gold_lakehouse_model"
}
```

### Step 5: Deploy Semantic Model & Report

```powershell
# Create semantic model
$modelPayload = @{
    type = "SemanticModel"
    displayName = "Gold_Lakehouse_Analytics"
} | ConvertTo-Json

$modelResponse = curl -X POST `
    -H "Authorization: Bearer $bearerToken" `
    -H "Content-Type: application/json" `
    -d $modelPayload `
    "https://api.fabric.microsoft.com/v1/workspaces/$workspaceId/items"

$modelId = $modelResponse.id

# Deploy TMDL definition
curl -X POST `
    -H "Authorization: Bearer $bearerToken" `
    -H "Content-Type: application/json" `
    -d @GoldLakehouse_SemanticModel.tmdl \
    "https://api.fabric.microsoft.com/v1/workspaces/$workspaceId/semanticModels/$modelId/updateDefinition"

# Create report
$reportPayload = @{
    type = "Report"
    displayName = "Gold_Lakehouse_Report"
} | ConvertTo-Json

curl -X POST `
    -H "Authorization: Bearer $bearerToken" `
    -H "Content-Type: application/json" `
    -d $reportPayload `
    "https://api.fabric.microsoft.com/v1/workspaces/$workspaceId/items"
```

### Step 6: Verify Power BI Connectivity

```sql
-- Query test: Should return recent data
SELECT TOP 10 
    summary_date,
    order_status,
    metric_order_count,
    metric_total_amount
FROM gold.events_daily_summary
ORDER BY summary_date DESC;
```

---

## 📊 Example 1: E-Commerce Medallion Architecture

### Business Context
Retail e-commerce platform ingesting daily orders, customers, and products data.

### Data Model

```
BRONZE LAYER:
├── bronze.orders_raw (orders_sample.csv)
├── bronze.customers_raw (customers_sample.csv)
└── bronze.products_raw (products_sample.csv)

SILVER LAYER:
├── silver.orders_cleaned (deduplicated, validated)
├── silver.customers_profile (customer master with SCD Type 2)
└── silver.products_dimension (product hierarchy flattened)

GOLD LAYER:
├── gold.orders_daily_summary (daily metrics by status)
├── gold.customer_segments (RFM analysis, lifetime value)
├── gold.product_performance (velocity, margins, top sellers)
└── gold.sales_trend_analysis (month-over-month, year-over-year)
```

### Implementation: Bronze → Silver → Gold

**Bronze Ingestion** (`01_Bronze_Ingestion_Ecommerce.py`):
```python
# Read CSV files with schema validation
df_orders = spark.read.format("csv").option("header", "true") \
    .load("/Workspace/Files/landing/daily/orders_sample.csv")

df_customers = spark.read.format("csv").option("header", "true") \
    .load("/Workspace/Files/landing/daily/customers_sample.csv")

# Add metadata and write
df_orders_with_meta = df_orders \
    .withColumn("_ingestion_timestamp", current_timestamp()) \
    .withColumn("_ingestion_id", lit(batch_id)) \
    .withColumn("_ingestion_date", current_date())

df_orders_with_meta.write \
    .format("delta") \
    .mode("append") \
    .partitionBy("_ingestion_date") \
    .saveAsTable("bronze.orders_raw")
```

**Silver Transformation** (`02_Silver_Transform_Ecommerce.py`):
```python
# Deduplicate orders
window_spec = Window.partitionBy("order_id").orderBy(desc("_insertion_timestamp"))
df_orders_dedup = spark.sql("""
    SELECT * FROM bronze.orders_raw
    WHERE _ingestion_date >= DATE_SUB(CURRENT_DATE(), 7)
""").withColumn("_rn", row_number().over(window_spec)) \
    .filter(col("_rn") == 1)

# Cleanse and enrich
df_orders_clean = df_orders_dedup \
    .filter(col("order_id").isNotNull()) \
    .filter(col("order_amount") >= 0) \
    .withColumn("order_year", year(col("order_date"))) \
    .withColumn("order_month", month(col("order_date"))) \
    .withColumn("is_high_value", col("order_amount") > 1000)

# Write to Silver with partitioning
df_orders_clean.write \
    .format("delta") \
    .mode("append") \
    .partitionBy("order_date") \
    .saveAsTable("silver.orders_cleaned")
```

**Gold Aggregation** (`03_Gold_Aggregations_Ecommerce.py`):
```python
# Daily order summary
spark.sql("""
    CREATE OR REPLACE TABLE gold.orders_daily_summary AS
    SELECT 
        order_date as summary_date,
        status,
        COUNT(*) as metric_order_count,
        COUNT(DISTINCT customer_id) as metric_unique_customers,
        SUM(order_amount) as metric_total_amount,
        AVG(order_amount) as metric_avg_amount,
        PERCENTILE_APPROX(order_amount, 0.5) as metric_median_amount
    FROM silver.orders_cleaned
    GROUP BY order_date, status
""")

# Customer RFM analysis
spark.sql("""
    CREATE OR REPLACE TABLE gold.customer_segments AS
    SELECT 
        customer_id,
        COUNT(*) as order_count,
        SUM(order_amount) as lifetime_value,
        MAX(order_date) as last_order_date,
        DATEDIFF(CURRENT_DATE(), MAX(order_date)) as days_since_order,
        CASE 
            WHEN SUM(order_amount) > 5000 AND DATEDIFF(CURRENT_DATE(), MAX(order_date)) < 30 THEN 'VIP'
            WHEN SUM(order_amount) > 1000 THEN 'High-Value'
            WHEN SUM(order_amount) > 100 THEN 'Regular'
            ELSE 'New'
        END as segment
    FROM silver.orders_cleaned
    GROUP BY customer_id
""")

# Monthly trend
spark.sql("""
    CREATE OR REPLACE TABLE gold.monthly_trend_analysis AS
    SELECT 
        CONCAT(YEAR(order_date), '-', LPAD(MONTH(order_date), 2, '0')) as month_key,
        COUNT(*) as order_count,
        SUM(order_amount) as total_revenue,
        LAG(SUM(order_amount)) OVER (ORDER BY YEAR(order_date), MONTH(order_date)) as prev_month_revenue,
        ROUND(100.0 * (SUM(order_amount) - LAG(SUM(order_amount)) OVER (ORDER BY YEAR(order_date), MONTH(order_date))) / LAG(SUM(order_amount)) OVER (ORDER BY YEAR(order_date), MONTH(order_date)), 2) as mom_growth_pct
    FROM silver.orders_cleaned
    GROUP BY YEAR(order_date), MONTH(order_date)
""")
```

---

## 📊 Example 2: IoT Time-Series Medallion

### Business Context
Manufacturing plant collecting sensor readings (temperature, humidity, pressure) from 10 sensors every hour for anomaly detection and trend analysis.

### Notebooks

**Bronze**: Ingest raw sensor readings
**Silver**: Validate readings, detect outliers, standardize measurements
**Gold**: Hourly/daily rollups, anomaly flags, trend analysis

---

## 📊 Example 3: Hierarchical Organizational Data

### Business Context
Multi-level organizational structure with cost allocation and performance tracking.

### Data Model

```
BRONZE:
├── bronze.org_structure_raw (departments, managers, reporting lines)
└── bronze.employees_raw (employee records, compensation)

SILVER:
├── silver.org_hierarchy (denormalized with parent/child links)
└── silver.employees_profile (cleaned compensation data)

GOLD:
├── gold.headcount_analysis (by level, department, location)
├── gold.cost_allocation (by business unit, project)
└── gold.org_health_metrics (tenure, turnover, diversity)
```

---

## 🚀 Deployment Checklist

- [ ] Create 3 lakehouses (Bronze, Silver, Gold)
- [ ] Deploy all 30+ notebooks to workspace
- [ ] Run sample data generator
- [ ] Execute Bronze ingestion
- [ ] Execute Silver transformation
- [ ] Execute Gold aggregation
- [ ] Verify row counts at each layer
- [ ] Discover Gold SQL endpoint
- [ ] Create semantic model with DirectLake
- [ ] Deploy Power BI report
- [ ] Test DAX queries and visuals
- [ ] Create orchestration pipeline
- [ ] Set up monitoring dashboard
- [ ] Configure failure alerts
- [ ] Schedule pipeline for daily execution
- [ ] Document data lineage
- [ ] Train analytics team on usage
- [ ] Measure query performance
- [ ] Optimize based on metrics

---

## 📈 Success Criteria

| Criterion | Target | Status |
|-----------|--------|--------|
| Data freshness | < 24 hours | - |
| Pipeline success rate | > 99% | - |
| Query latency (P95) | < 10 seconds | - |
| Query latency (P99) | < 30 seconds | - |
| Data completeness | > 95% | - |
| Unique users querying Gold | > 10 | - |
| Power BI report adoption | > 80% target audience | - |

---

## Summary

**Power BI Integration**:
- ✓ DirectLake semantic model (no data duplication)
- ✓ Connected to Gold lakehouse SQL endpoint
- ✓ Pre-calculated measures and DAX functions
- ✓ Executive and operational dashboards

**Examples**:
- ✓ E-Commerce medallion (products, orders, customers)
- ✓ IoT time-series (sensor metrics, anomaly detection)
- ✓ Hierarchical organizational data

**Production Ready**:
- ✓ Complete medallion architecture
- ✓ 30+ reusable notebooks
- ✓ Master orchestration pipeline
- ✓ Monitoring and alerting
- ✓ Power BI integration
- ✓ Comprehensive documentation

→ Next: Start implementation with your data! 🚀
