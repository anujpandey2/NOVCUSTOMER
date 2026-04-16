# Medallion Architecture - Notebook Templates & Code

This directory contains all production-ready notebooks for the medallion architecture.

## 📂 Notebook Organization

### Phase 0: Setup & Testing
- `00_Generate_Sample_Data.py` - Create realistic test data (e-commerce, IoT, hierarchy)
- `00_Workspace_Setup.py` - Create folder structure and configuration

### Phase 1: Bronze Layer (Raw Ingestion)
- `01_Bronze_Ingestion.py` - Generic ingestion notebook (CSV, Parquet, JSON, Delta)
- `01_Bronze_Validation.py` - Validate Bronze ingestion success

### Phase 2: Silver Layer (Cleaning & Validation)
- `02_Quality_Rules_Engine.py` - Configurable data quality framework
- `02_Silver_Transform.py` - Generic transformation (dedup, validation, conformance)
- `02_Silver_Validation.py` - Track metrics, lineage, reconciliation

### Phase 3: Gold Layer (Analytics Ready)
- `03_Gold_Aggregations.py` - Business-ready aggregations and materialized views
- `03_Gold_Validation.py` - Optimization (ZORDER, OPTIMIZE), performance stats

### Phase 4: Orchestration & Monitoring
- `04_Master_Orchestration_Pipeline.json` - Pipeline definition (Bronze→Silver→Gold)
- `04_Pipeline_Monitoring.py` - Health dashboard and alerting

### Phase 5: Examples
- `example_ecommerce_medallion.py` - Complete e-commerce example
- `example_iot_timeseries_medallion.py` - IoT metrics example
- `example_hierarchical_data_medallion.py` - Organizational structure example

---

## 🚀 Quick Start

### 1. Create Sample Data
```python
%run /Workspace/Notebooks/00_Generate_Sample_Data
```

### 2. Run Bronze Ingestion
```python
%run /Workspace/Notebooks/01_Bronze_Ingestion
```

### 3. Run Silver Transformation
```python
%run /Workspace/Notebooks/02_Silver_Transform
```

### 4. Run Gold Aggregations
```python
%run /Workspace/Notebooks/03_Gold_Aggregations
```

### 5. Monitor Results
```python
%run /Workspace/Notebooks/04_Pipeline_Monitoring
```

---

## 📋 Deployment Order

1. **Infrastructure**: Create lakehouses and folder structure
2. **Sample Data**: Generate test data
3. **Bronze**: Ingestion and validation
4. **Silver**: Transformation and quality checks
5. **Gold**: Analytics and optimization
6. **Pipeline**: Orchestration automation
7. **Monitoring**: Health tracking and alerts
8. **Power BI**: Semantic model and reports
9. **Documentation**: Usage guides and examples

---

## 🔧 Configuration

All notebooks reference configuration files in `Files/config/`:

```
/Workspace/
├── Files/
│   ├── config/
│   │   ├── bronze_config.json      # Ingestion sources and settings
│   │   ├── silver_config.json      # Quality rules and transformations
│   │   ├── gold_config.json        # Analytics aggregations
│   │   └── orchestration_config.json # Pipeline parameters
│   ├── landing/
│   │   ├── daily/                  # Daily ingestion landing zone
│   │   └── archive/                # Archive of processed files
│   └── logs/
│       ├── ingestion/              # Bronze ingestion logs
│       ├── transformation/         # Silver transformation logs
│       └── aggregation/            # Gold aggregation logs
├── Notebooks/                      # All notebooks stored here
└── Tables/                         # Delta tables (Bronze, Silver, Gold)
```

---

## 🔍 Notebook Parameters

Each notebook supports optional parameters for flexibility:

### Bronze Ingestion
```python
dbutils.widgets.text("source_config", "default_source", "Source configuration JSON")
dbutils.widgets.text("processing_date", date.today().isoformat(), "Processing date (YYYY-MM-DD)")
dbutils.widgets.dropdown("mode", "append", ["append", "overwrite"], "Write mode")
```

### Silver Transformation
```python
dbutils.widgets.text("processing_date", date.today().isoformat(), "Processing date")
dbutils.widgets.dropdown("full_refresh", "false", ["true", "false"], "Full vs incremental")
dbutils.widgets.text("quality_rule_set", "default", "Quality rules configuration")
```

### Gold Aggregations
```python
dbutils.widgets.text("processing_date", date.today().isoformat(), "Processing date")
dbutils.widgets.text("aggregation_types", "daily,monthly", "Comma-separated aggregation types")
dbutils.widgets.dropdown("optimize", "true", ["true", "false"], "Run OPTIMIZE after write")
```

---

## 📊 Data Dictionary

### Bronze Layer Tables

#### `bronze.events_raw`
Raw event data with metadata columns
```
ingestion_timestamp (timestamp) - When data was ingested
ingestion_id (string) - Unique batch identifier
source_system (string) - Data source system name
source_file (string) - Original file name/path
row_num (int) - Row number in source
[source_columns...] - Original data columns
```

### Silver Layer Tables

#### `silver.events_cleaned`
Deduplicated, validated events
```
event_id (string) - Unique identifier (primary key)
event_date (date) - Date of event
event_type (string) - Categorized event type
customer_id (string) - Foreign key to customer
amount (decimal) - Standardized numeric amount
currency (string) - 3-letter currency code
is_valid (boolean) - Quality check result
quality_flags (array<string>) - Issues detected
dbt_valid_from (timestamp) - SCD Type 2 start
dbt_valid_to (timestamp) - SCD Type 2 end
dbt_is_current (boolean) - Current row indicator
_bronze_ingestion_id (string) - Lineage to bronze
```

### Gold Layer Tables

#### `gold.events_daily_summary`
Pre-aggregated daily metrics
```
summary_date (date) - Business date
event_type (string) - Event category
customer_segment (string) - Customer classification
metric_event_count (long) - Count of events
metric_total_amount (decimal) - Total amount
metric_avg_amount (decimal) - Average amount
metric_min_amount (decimal) - Minimum amount
metric_max_amount (decimal) - Maximum amount
created_timestamp (timestamp) - When summary was created
```

---

## ✅ Quality Assurance

Each layer includes validation:

### Bronze Quality Gate
- Row count > 0
- All required columns present
- Metadata columns populated
- No duplicate batch_ids within same date

### Silver Quality Gate
- Row count Bronze > Row count Silver (after dedup)
- No records with quality_flags non-empty (unless flagged for manual review)
- Primary key uniqueness check
- Schema matches expected structure

### Gold Quality Gate
- Aggregated values mathematically consistent
- No null values in aggregation columns
- Metrics match spot-check calculations
- Data freshness within SLA

---

## 🐛 Debugging Tips

### View Recent Logs
```python
# Bronze ingestion
dbutils.fs.ls("/Workspace/Files/logs/ingestion/")

# Transformation errors
spark.sql("SELECT * FROM bronze.ingestion_log WHERE status = 'error' ORDER BY timestamp DESC LIMIT 20")
```

### Test Quality Rules
```python
# Dry-run quality checks
quality_results = validate_dataframe(df, quality_rules, dry_run=True)
print(quality_results)  # See violations before applying
```

### Inspect Table Lineage
```python
# Show lineage from bronze to gold
spark.sql("""
  SELECT 
    bronze_table, 
    silver_table, 
    gold_table, 
    row_count_bronze, 
    row_count_silver, 
    row_count_gold,
    lineage_last_updated
  FROM gold.table_lineage
  ORDER BY lineage_last_updated DESC
""")
```

### Profile Data Before/After Transform
```python
# Compare Bronze vs Silver statistics
print(f"Bronze row count: {bronze_df.count()}")
print(f"Silver row count: {silver_df.count()}")
print(f"Duplicates removed: {bronze_df.count() - silver_df.count()}")
bronze_df.describe().show()
silver_df.describe().show()
```

---

## 📈 Performance Tuning

### Cluster Configuration
- **Bronze ingestion**: Standard cluster (8-16 cores)
- **Silver transformation**: Standard cluster (16-32 cores)
- **Gold aggregations**: Interactive cluster (8-24 cores, persistent)
- **Complex queries**: High-concurrency cluster (4 cores per user)

### Spark Configuration
See `MEDALLION_ARCHITECTURE_PLAN.md` → "Performance Tuning" section

### Query Optimization
- Use predicate pushdown (filter early in query)
- Partition pruning (filter on partition column)
- V-Order for columnar performance
- ZORDER for high-cardinality filters
- Run ANALYZE TABLE COMPUTE STATISTICS after bulk inserts

---

## 🔄 Incremental Processing

Medallion architecture supports two refresh modes:

### Incremental (Recommended)
- Only processes data since last successful run
- Uses watermark pattern (max timestamp)
- MERGE-based updates in Silver/Gold
- ~5-10x faster than full refresh
- Default for daily scheduled runs

### Full Refresh
- Reprocesses entire dataset
- Useful for corrections or schema changes
- Slower but ensures consistency
- Optional manual trigger via pipeline

---

## 📞 Common Tasks

### Add New Data Source
1. Add source definition to `/Files/config/bronze_config.json`
2. Update `01_Bronze_Ingestion.py` with new source handler
3. Add Silver transformation rules to `/Files/config/silver_config.json`
4. Extend `02_Silver_Transform.py` with new transformations
5. Add Gold aggregations to `03_Gold_Aggregations.py`
6. Test end-to-end with sample data

### Adjust Quality Rules
1. Edit `/Files/config/silver_config.json`
2. Add/modify rule definitions
3. Re-run `02_Quality_Rules_Engine.py` to validate rule syntax
4. Execute Silver transformation to apply updated rules

### Update Gold Aggregations
1. Edit `03_Gold_Aggregations.py`
2. Add new aggregation tables or metrics
3. Run notebook to regenerate Gold layer
4. Update Power BI semantic model to include new tables/columns

### Fix Data Issues
1. Identify issue in Silver layer via quality reports
2. Add exception handling or data correction logic
3. Reprocess affected data (full or incremental)
4. Log correction in change management
5. Update Gold layer to reflect correction

---

## 🎯 Next: Notebook Templates

Detailed notebook templates follow in separate documents:
- `BRONZE_LAYER_NOTEBOOKS.md`
- `SILVER_LAYER_NOTEBOOKS.md`
- `GOLD_LAYER_NOTEBOOKS.md`
- `ORCHESTRATION_PIPELINE.md`
