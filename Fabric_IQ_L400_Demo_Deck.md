# Microsoft Fabric IQ — L400 Deep-Dive Demo
### Target Audience: Data Engineers & Architects
### Duration: ~4 hours (adjust per section)

---

## 📌 AGENDA

| #  | Section                                      | Duration | Depth |
|----|----------------------------------------------|----------|-------|
| 1  | Why Fabric? — Platform Value Proposition     | 20 min   | L200  |
| 2  | OneLake — Unified Storage Architecture       | 30 min   | L400  |
| 3  | Lakehouse — Delta Tables & SQL Analytics     | 30 min   | L400  |
| 4  | Medallion Architecture — Bronze/Silver/Gold  | 45 min   | L400  |
| 5  | Spark Processing — PySpark Deep-Dive         | 30 min   | L400  |
| 6  | Data Quality — Rules Engine & Validation     | 25 min   | L400  |
| 7  | Pipelines & Orchestration                    | 30 min   | L400  |
| 8  | Monitoring, Observability & Operations       | 20 min   | L400  |
| 9  | Live Demo — End-to-End Pipeline Run          | 30 min   | L400  |
| 10 | Q&A + Next Steps                             | 20 min   | —     |

---

## ═══════════════════════════════════════════════
## SLIDE 1 — TITLE SLIDE
## ═══════════════════════════════════════════════

### Microsoft Fabric IQ — L400 Technical Deep-Dive
**Subtitle:** Enterprise Medallion Architecture on Microsoft Fabric  
**Audience:** Data Engineers & Architects  

**Talking Points:**
- This is an L400 session — we go deep into architecture decisions, Spark internals, Delta optimization, and production-grade patterns
- We will use a fully operational implementation with 150K+ sample records, 40+ notebooks, and production configs
- Everything shown is deployable to your Fabric workspace today

---

## ═══════════════════════════════════════════════
## SECTION 1 — WHY FABRIC? PLATFORM VALUE PROPOSITION
## ═══════════════════════════════════════════════

### SLIDE 2 — The Data Engineering Problem Today

**Visual:** Diagram showing fragmented tools — separate storage, compute, ETL, BI, ML

**Talking Points:**
- Traditional architectures require stitching 5–8 separate services (ADLS, Synapse, ADF, Databricks, Power BI, Purview…)
- Each service has its own: auth model, networking, billing, monitoring, SDK
- Data copies proliferate → cost explosion, stale data, governance gaps
- Team silos: data engineers don't speak the same "tool language" as analysts

> **L400 Insight:** "The hidden cost isn't licensing — it's the integration tax. Every cross-service data movement adds latency, failure modes, and debugging complexity."

---

### SLIDE 3 — Microsoft Fabric: One Platform, One Copy

**Visual:** Fabric SaaS architecture diagram — OneLake at base, workloads on top

**Talking Points:**
- **SaaS model** — no infrastructure provisioning, patching, or scaling decisions
- **OneLake** — single storage layer, Delta/Parquet native, ADLS Gen2 compatible
- **Unified compute** — Spark, SQL, KQL, and Dataflows on one capacity
- **Single security model** — workspace RBAC, row-level security, sensitivity labels
- **One billing model** — Capacity Units (CUs) across all workloads

> **L400 Insight:** "Fabric eliminates the ETL between storage tiers. OneLake IS your data lake, warehouse, and lakehouse — simultaneously."

---

## ═══════════════════════════════════════════════
## SECTION 2 — ONELAKE: UNIFIED STORAGE ARCHITECTURE
## ═══════════════════════════════════════════════

### SLIDE 4 — OneLake Architecture Deep-Dive

**Visual:** OneLake hierarchy — Tenant → Capacity → Workspace → Lakehouse → Tables/Files

**Talking Points:**
- OneLake = **one data lake per tenant**, built on ADLS Gen2
- Every Fabric item (Lakehouse, Warehouse, KQL DB) stores data in OneLake automatically
- Data is stored as **Delta Parquet** — open format, no lock-in
- **Shortcuts** allow referencing external data (AWS S3, GCS, ADLS) without copying
- **OneLake file explorer** — mount OneLake as a local drive on Windows

> **L400 Insight:** "OneLake shortcuts are metadata pointers, not data copies. You can query 10TB in S3 from a Fabric notebook without moving a single byte."

**Key Architecture Decisions:**
```
┌─────────────────────────────────────────────────────┐
│                    TENANT (OneLake)                  │
│  ┌──────────────────────────────────────────────┐   │
│  │              WORKSPACE                        │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐     │   │
│  │  │ Lakehouse│ │ Lakehouse│ │ Lakehouse│     │   │
│  │  │ (Bronze) │ │ (Silver) │ │  (Gold)  │     │   │
│  │  │          │ │          │ │          │     │   │
│  │  │ /Tables  │ │ /Tables  │ │ /Tables  │     │   │
│  │  │ /Files   │ │ /Files   │ │ /Files   │     │   │
│  │  └──────────┘ └──────────┘ └──────────┘     │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

---

### SLIDE 5 — OneLake: Shortcuts, Mirroring & Cross-Cloud

**Visual:** Shortcut topology — internal shortcuts between lakehouses, external to S3/GCS

**Talking Points:**
- **Internal shortcuts** — reference tables across workspaces without duplication
- **External shortcuts** — mount AWS S3 or Google Cloud Storage as read-only tables
- **Mirroring** — real-time replication from Azure SQL, Cosmos DB, Snowflake into OneLake
- **Open Delta format** — any tool that reads Delta/Parquet can access OneLake data
- **Multi-workspace pattern** — dev/test/prod workspaces sharing a single OneLake tenant

> **L400 Insight:** "In production, use OneLake shortcuts to create a 'virtual gold layer' that spans multiple team workspaces — no data movement, instant federation."

---

## ═══════════════════════════════════════════════
## SECTION 3 — LAKEHOUSE: DELTA TABLES & SQL ANALYTICS
## ═══════════════════════════════════════════════

### SLIDE 6 — Lakehouse Architecture

**Visual:** Lakehouse = Spark Engine + SQL Endpoint + Delta Tables

**Talking Points:**
- Lakehouse combines **data lake flexibility** with **warehouse performance**
- Two access modes:
  - **Spark (notebooks)** — full PySpark/Scala/R for ETL, ML, complex transforms
  - **SQL endpoint** — auto-generated T-SQL endpoint for every managed table
- Tables are **managed Delta tables** — ACID transactions, time travel, schema evolution
- Files folder for unstructured/semi-structured data (images, logs, raw JSON)

> **L400 Insight:** "The SQL endpoint is auto-generated and read-only. It's not a warehouse — it's a SQL view over Delta tables. For write operations, use Spark or Dataflows."

**Architecture:**
```
┌───────────────────────────────────────────────────┐
│                   LAKEHOUSE                        │
│                                                    │
│  ┌─────────────┐          ┌─────────────────────┐ │
│  │   /Tables    │          │    /Files            │ │
│  │  (Managed    │          │  (Unmanaged)         │ │
│  │   Delta)     │          │  CSV, JSON, Parquet  │ │
│  │              │          │  Images, Logs        │ │
│  └──────┬───────┘          └─────────────────────┘ │
│         │                                          │
│  ┌──────▼──────────────────────────────────────┐  │
│  │        Spark Engine (Read + Write)           │  │
│  └──────┬──────────────────────────────────────┘  │
│         │                                          │
│  ┌──────▼──────────────────────────────────────┐  │
│  │     SQL Endpoint (Read-Only, Auto-Gen)       │  │
│  └─────────────────────────────────────────────┘  │
│         │                                          │
│  ┌──────▼──────────────────────────────────────┐  │
│  │     DirectLake → Power BI (No Import)        │  │
│  └─────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────┘
```

---

### SLIDE 7 — Delta Table Internals (L400)

**Visual:** Delta log structure — _delta_log/, Parquet data files, checkpoint files

**Talking Points:**
- Delta tables = Parquet data files + JSON transaction log (`_delta_log/`)
- **ACID transactions** — concurrent reads/writes without corruption
- **Time travel** — query any past version: `SELECT * FROM table VERSION AS OF 5`
- **Schema evolution** — `mergeSchema = true` handles new columns gracefully
- **V-Order optimization** — Fabric-specific columnar sorting for 10–50% faster reads
- **OPTIMIZE + ZORDER** — bin-packing + multi-dimensional clustering

> **L400 Insight:** "V-Order is a write-time optimization unique to Fabric. It reorders data within Parquet row groups for optimal column compression. Always enable it for Gold tables."

**Our Implementation:**
| Layer   | V-Order | ZORDER Columns                        | Compression |
|---------|---------|---------------------------------------|-------------|
| Bronze  | ❌ Off  | None (append-only)                    | Snappy      |
| Silver  | ✅ On   | `business_date`                       | Snappy      |
| Gold    | ✅ On   | `period_date, category, region`       | Snappy      |

---

## ═══════════════════════════════════════════════
## SECTION 4 — MEDALLION ARCHITECTURE: BRONZE / SILVER / GOLD
## ═══════════════════════════════════════════════

### SLIDE 8 — Medallion Architecture Overview

**Visual:** Three-layer flow diagram with data characteristics at each layer

**Talking Points:**
- **Medallion** = a data quality progression pattern, not a Fabric feature
- Each layer has distinct responsibilities, SLAs, and optimization strategies
- Data flows **Bronze → Silver → Gold** with quality gates between layers
- Our implementation: **3 dedicated lakehouses**, one per layer

> **L400 Insight:** "Separate lakehouses per layer is a deliberate architecture decision — it enables independent RBAC, capacity allocation, and lifecycle management."

**Architecture:**
```
  RAW SOURCES                BRONZE              SILVER               GOLD
┌──────────────┐        ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  CSV / JSON  │───────▶│ Append-Only  │───▶│ Deduplicated │───▶│ Aggregated   │
│  Parquet     │        │ + Metadata   │    │ + Validated  │    │ + Optimized  │
│  APIs        │        │ + Batch ID   │    │ + Enriched   │    │ + Star Schema│
│  Streaming   │        │              │    │              │    │              │
└──────────────┘        │ Retention:   │    │ Retention:   │    │ Retention:   │
                        │   90 days    │    │   730 days   │    │   7+ years   │
                        │ Quality: 98%+│    │ Quality: 97%+│    │ Quality: 96%+│
                        └──────────────┘    └──────────────┘    └──────────────┘
                         ▲                   ▲                   ▲
                         │                   │                   │
                    01_Bronze_          02_Silver_          03_Gold_
                    Ingestion.py        Transform.py        Aggregations.py
```

---

### SLIDE 9 — Bronze Layer: Raw Ingestion (L400)

**Visual:** Bronze ingestion flow with metadata enrichment

**Talking Points:**
- **Philosophy:** Capture everything, transform nothing
- Append-only writes — never update or delete raw data
- Auto-add metadata columns on every record:
  - `ingestion_timestamp` — when the record was ingested
  - `source_file` — original file path (`input_file_name()`)
  - `batch_id` — UUID per ingestion run for lineage
  - `ingestion_date` — business date partition key
- Multi-format reader: CSV, Parquet, JSON, Delta — single code path
- Partition by `ingestion_date` for efficient replay & purge

> **L400 Insight:** "Never skip the Bronze layer. Raw data replay is your disaster recovery. If Silver logic changes, you re-derive from Bronze — you don't re-ingest from source."

**Config-Driven Design (bronze_config.json):**
```json
{
  "tables": [
    {
      "name": "events_raw",
      "source_path": "Files/raw/events/",
      "format": "csv",
      "metadata_columns": [
        { "name": "ingestion_timestamp", "expression": "current_timestamp()" },
        { "name": "source_file",         "expression": "input_file_name()" },
        { "name": "batch_id",            "expression": "uuid()" }
      ],
      "partition_by": ["ingestion_date"]
    }
  ]
}
```

**Key Notebook:** `01_Bronze_Ingestion.py`
- Generic multi-format reader with error handling
- Configurable from JSON — no hardcoded table names
- 3 retries with 30-second timeout per ingestion

---

### SLIDE 10 — Silver Layer: Cleansed & Validated (L400)

**Visual:** Silver transformation pipeline — dedup → validate → enrich → write

**Talking Points:**
- **Philosophy:** One version of the truth — clean, typed, deduplicated
- **Deduplication:** Window functions with `keep_latest` strategy (by `updated_at`)
- **Null handling:** Required columns enforced; configurable defaults for optional fields
- **Range validation:** Business rules for amounts (>0), dates (within 2 years), etc.
- **Schema standardization:** All columns → `snake_case`, lowercase
- **Derived columns:** `day_of_week`, `hour_of_day`, `month`, `year` from timestamps
- **Merge schema enabled** — new source columns auto-propagate

> **L400 Insight:** "The Quality Rules Engine is the most critical Silver component. It's a configurable JSON-driven validator that scores every batch 0–100%. Batches below 95% trigger alerts."

**Quality Rules Engine (02_Quality_Rules_Engine.py):**
```
Rule Types Supported:
  ✅ not_null        — Required column validation
  ✅ unique          — Uniqueness constraint
  ✅ range           — Min/max bounds (numeric, date)
  ✅ pattern         — Regex matching (email, phone, codes)
  ✅ referential     — Cross-table integrity
  ✅ custom_sql      — Arbitrary SQL predicates
  
Output:
  → Quality score (0–100%)
  → Violation report (column, rule, count, sample)
  → Pass/fail gate for downstream processing
```

**Silver Config Excerpt:**
```json
{
  "quality_rules": {
    "deduplication": { "strategy": "keep_latest", "key_columns": ["id"], "order_by": "updated_at" },
    "null_checks":  { "required_columns": ["id", "customer_id", "amount", "transaction_date"] },
    "range_checks": [
      { "column": "amount", "min": 0, "max": 1000000 },
      { "column": "transaction_date", "min": "2020-01-01", "max": "2030-12-31" }
    ]
  },
  "transformations": {
    "column_naming": "snake_case",
    "derived_columns": [
      { "name": "day_of_week",  "expression": "dayofweek(transaction_date)" },
      { "name": "hour_of_day",  "expression": "hour(transaction_timestamp)" }
    ]
  }
}
```

---

### SLIDE 11 — Gold Layer: Analytics-Ready (L400)

**Visual:** Gold aggregation patterns — daily, monthly, customer analytics

**Talking Points:**
- **Philosophy:** Pre-computed, optimized for consumption — BI, APIs, ML features
- **Three aggregation patterns implemented:**
  1. **Daily Summary** — revenue, order count, avg order value by category/region
  2. **Monthly Summary** — period-over-period trends
  3. **Customer Analytics** — RFM (Recency, Frequency, Monetary), lifetime value, segmentation
- **Optimization stack:**
  - V-Order enabled (columnar re-sorting at write time)
  - ZORDER on `period_date, category, region` (multi-dim clustering)
  - OPTIMIZE for bin-packing small files
  - ANALYZE TABLE for statistics collection

> **L400 Insight:** "Gold tables should be wide and denormalized. Joins are expensive at query time — pre-compute them in Gold. Think star schema without the foreign keys."

**Gold Tables:**
```
┌─────────────────────────────────────────────────────────┐
│  gold_transactions_daily                                 │
│  ─────────────────────                                   │
│  period_date  │ category │ region │ customer_segment     │
│  total_revenue│ order_count │ avg_order_value            │
│  return_rate  │ unique_customers │ new_vs_returning      │
│  Partitioned by: period_date                             │
│  ZORDERed by: category, region                           │
├─────────────────────────────────────────────────────────┤
│  gold_customer_metrics                                   │
│  ─────────────────────                                   │
│  customer_id  │ lifetime_value │ transaction_count       │
│  recency_days │ frequency_score │ monetary_score         │
│  rfm_segment  │ first_purchase │ last_purchase           │
│  Partitioned by: rfm_segment                             │
├─────────────────────────────────────────────────────────┤
│  gold_summary_monthly                                    │
│  ─────────────────────                                   │
│  year │ month │ total_revenue │ total_orders             │
│  avg_order_value │ yoy_growth │ mom_growth               │
│  Partitioned by: year                                    │
└─────────────────────────────────────────────────────────┘
```

**Performance Targets & Actuals:**
| Metric              | Target     | Actual     | Status |
|----------------------|-----------|------------|--------|
| Query P95 Latency   | < 10 sec  | 8.3 sec    | ✅     |
| Query P99 Latency   | < 30 sec  | 24.1 sec   | ✅     |
| Gold Quality Score  | > 96%     | 98.1%      | ✅     |
| Aggregation Runtime | < 20 min  | 12.3 min   | ✅     |

---

## ═══════════════════════════════════════════════
## SECTION 5 — SPARK PROCESSING: PYSPARK DEEP-DIVE
## ═══════════════════════════════════════════════

### SLIDE 12 — Fabric Spark Runtime (L400)

**Visual:** Spark architecture in Fabric — Driver + Executors + OneLake

**Talking Points:**
- Fabric Spark is **Apache Spark 3.5+** with Fabric-specific optimizations
- **Starter pools** — pre-warmed Spark sessions (< 30 sec cold start vs. minutes)
- **Autoscale** — nodes scale 1–N based on workload
- **Native Delta Lake integration** — `spark.read.format("delta")` is first-class
- **Lakehouse auto-discovery** — attached lakehouse tables available as `spark.sql("SELECT * FROM lakehouse.table")`
- **V-Order writer** — Fabric's custom Parquet writer for columnar optimization

> **L400 Insight:** "Use starter pools for interactive development. For production pipelines, allocate dedicated capacity with fixed node counts to ensure predictable performance."

---

### SLIDE 13 — Key Spark Patterns Used (L400)

**Visual:** Code snippets with annotations

**Pattern 1: Config-Driven Multi-Format Reader**
```python
def read_source(spark, config):
    reader = spark.read.format(config["format"])
    if config["format"] == "csv":
        reader = reader.option("header", True).option("inferSchema", True)
    return reader.load(config["source_path"])
```

**Pattern 2: Deduplication with Window Functions**
```python
from pyspark.sql.window import Window
from pyspark.sql.functions import row_number

window = Window.partitionBy("id").orderBy(col("updated_at").desc())
deduped = df.withColumn("rn", row_number().over(window)).filter("rn = 1").drop("rn")
```

**Pattern 3: Incremental Writes with Merge**
```python
from delta.tables import DeltaTable

target = DeltaTable.forPath(spark, target_path)
target.alias("t").merge(
    source.alias("s"), "t.id = s.id"
).whenMatchedUpdateAll().whenNotMatchedInsertAll().execute()
```

**Pattern 4: Delta Optimization**
```python
spark.sql("OPTIMIZE gold_table ZORDER BY (category, region)")
spark.sql("ANALYZE TABLE gold_table COMPUTE STATISTICS FOR ALL COLUMNS")
```

> **L400 Insight:** "Always run OPTIMIZE after bulk writes. Small file proliferation (< 128 MB each) kills read performance. ZORDER is critical for Gold tables with multi-column filters."

---

## ═══════════════════════════════════════════════
## SECTION 6 — DATA QUALITY: RULES ENGINE & VALIDATION
## ═══════════════════════════════════════════════

### SLIDE 14 — Data Quality Framework (L400)

**Visual:** Quality pipeline — Ingest → Validate → Score → Gate → Alert

**Talking Points:**
- Quality is **not optional** — every layer has validation notebooks
- **Quality Rules Engine** (`02_Quality_Rules_Engine.py`):
  - JSON-configurable rule definitions
  - 6 rule types: `not_null`, `unique`, `range`, `pattern`, `referential`, `custom_sql`
  - Outputs: quality score (0–100%), violation report, pass/fail decision
- **Validation gates** between layers:
  - Bronze Validation: schema check, row count, metadata presence
  - Silver Validation: dedup verification, null counts, reconciliation
  - Gold Validation: aggregation accuracy, OPTIMIZE/ZORDER verification
- **Quality threshold:** 95% overall score required to proceed

> **L400 Insight:** "Implement quality gates as separate notebooks, not inline checks. This lets you re-run validation independently and makes debugging easier."

**Quality Scores (Production Run):**
```
┌──────────────────────────────────────────┐
│  Layer    │ Target │ Actual │ Status     │
├──────────────────────────────────────────┤
│  Bronze   │  >98%  │ 99.2%  │ ✅ PASS   │
│  Silver   │  >97%  │ 97.8%  │ ✅ PASS   │
│  Gold     │  >96%  │ 98.1%  │ ✅ PASS   │
│  Overall  │  >95%  │ 96.8%  │ ✅ PASS   │
└──────────────────────────────────────────┘
```

---

## ═══════════════════════════════════════════════
## SECTION 7 — PIPELINES & ORCHESTRATION
## ═══════════════════════════════════════════════

### SLIDE 15 — Master Orchestration Pipeline (L400)

**Visual:** Pipeline DAG — sequential flow with gates and error handling

**Talking Points:**
- Single **master pipeline** orchestrates the full medallion flow
- 8 activities with explicit dependencies:

```
  Check_Data_Freshness
          │
          ▼
  Bronze_Ingestion ──────▶ Bronze_Validation
                                    │
                                    ▼
                          Quality_Rules_Engine
                                    │
                                    ▼
                          Silver_Transformation ──────▶ Silver_Validation
                                                              │
                                                              ▼
                                                    Gold_Aggregations
                                                              │
                                                              ▼
                                                    Gold_Validation
                                                              │
                                                              ▼
                                                    Pipeline_Monitoring
```

**Error Handling:**
- **Retries:** 3 for Bronze, 2 for Silver, 1 for Gold (exponential backoff)
- **Timeouts:** 30 min per transformation, 15 min per validation
- **Failure mode:** Stop-on-failure for validation gates
- **Notifications:** Email + Webhook (Slack/Teams) on failure/timeout

> **L400 Insight:** "Validation activities use 'stop-on-failure' — if Bronze validation fails, Silver never starts. This prevents propagating bad data through the pipeline."

---

### SLIDE 16 — Pipeline Configuration (L400)

**Visual:** orchestration_config.json structure

**Talking Points:**
- **Parameterized execution:**
  - `processing_date` — defaults to `{{ yesterday() }}`
  - `incremental_mode` — `true` for daily runs, `false` for full reload
  - `data_quality_threshold` — 95% minimum to pass
- **Scheduling:** Daily at 02:00 UTC (configurable)
- **Retry strategy:**
  ```
  Base delay:   30 seconds
  Multiplier:   2x (exponential)
  Max retries:  3 (Bronze), 2 (Silver), 1 (Gold)
  ```
- **Alerting channels:**
  - Email — on failure, timeout, or quality threshold breach
  - Webhook — Slack/Teams/Log Analytics integration
  - Pipeline monitoring dashboard — real-time status

> **L400 Insight:** "Decrease retry counts as you move downstream. Bronze deals with external sources (flaky) — retry aggressively. Gold is internal computation — if it fails once, something fundamental is wrong."

---

## ═══════════════════════════════════════════════
## SECTION 8 — MONITORING, OBSERVABILITY & OPERATIONS
## ═══════════════════════════════════════════════

### SLIDE 17 — Monitoring Dashboard (L400)

**Visual:** Monitoring dashboard mockup with KPIs

**Talking Points:**
- **04_Pipeline_Monitoring.py** — real-time health dashboard
- **Key metrics tracked:**
  - Pipeline success rate (target: > 99%)
  - Duration by stage (P50 / P95 / P99)
  - Data freshness (hours since last successful run)
  - Quality scores per layer (Bronze / Silver / Gold)
  - Record counts & throughput (records/sec)
- **Alerting rules:**
  - Pipeline failure → immediate email + webhook
  - Quality score < 95% → warning notification
  - Duration > 2x baseline → performance alert
  - Data freshness > 4 hours → staleness alert

> **L400 Insight:** "Track P95 and P99, not just averages. A pipeline that's fast 90% of the time but slow on month-end (large volume) will surprise you in production."

**Operational Metrics (Current):**
```
┌──────────────────────────────────────────────────────┐
│  Metric                   │ Target    │ Actual       │
├──────────────────────────────────────────────────────┤
│  Pipeline Success Rate    │ >99%      │ 100% (4/4)   │
│  Bronze Ingestion Time    │ <15 min   │ 8.2 min      │
│  Silver Transform Time    │ <30 min   │ 18.5 min     │
│  Gold Aggregation Time    │ <20 min   │ 12.3 min     │
│  End-to-End Duration      │ <60 min   │ 39.0 min     │
│  Data Quality (Overall)   │ >95%      │ 96.8%        │
└──────────────────────────────────────────────────────┘
```

---

### SLIDE 18 — Operational Runbook

**Visual:** Decision tree for common failure scenarios

**Talking Points:**
- Pre-built runbooks for common scenarios:
  1. **Bronze ingestion failure** → check source availability, retry, alert data owners
  2. **Quality score below threshold** → inspect violation report, quarantine bad records
  3. **Performance degradation** → run OPTIMIZE, check for small file proliferation
  4. **Schema evolution** → Silver handles `mergeSchema`; Gold may need manual adjustment
  5. **Full reload needed** → set `incremental_mode = false`, clear watermarks

> **L400 Insight:** "Invest in runbooks early. The pipeline will fail at 3 AM — the runbook is what separates a 10-minute fix from a 4-hour firefight."

---

## ═══════════════════════════════════════════════
## SECTION 9 — LIVE DEMO: END-TO-END PIPELINE RUN
## ═══════════════════════════════════════════════

### SLIDE 19 — Demo Walkthrough

**Visual:** Step-by-step demo sequence with expected outputs

**Live Demo Steps (30 minutes):**

```
STEP 1: Workspace Tour (5 min)
─────────────────────────────
→ Show 3 lakehouses (bronze, silver, gold) in Fabric workspace
→ Show OneLake folder structure (/Tables, /Files)
→ Show SQL endpoint for Gold lakehouse
→ Show attached configurations in /Files

STEP 2: Generate Sample Data (3 min)
─────────────────────────────────────
→ Run 00_Generate_Sample_Data.py
→ Show 150K+ records in /Files/raw/
→ Formats: CSV (events), Parquet (transactions)

STEP 3: Bronze Ingestion (5 min)
────────────────────────────────
→ Run 01_Bronze_Ingestion.py
→ Show metadata columns (batch_id, ingestion_timestamp, source_file)
→ Query: SELECT count(*), min(ingestion_timestamp) FROM bronze.events_raw
→ Show partition structure in OneLake

STEP 4: Quality Rules Engine (5 min)
────────────────────────────────────
→ Run 02_Quality_Rules_Engine.py
→ Show quality score output (99.2%)
→ Show violation report (null checks, range violations)
→ Demonstrate a deliberate quality failure (inject bad data)

STEP 5: Silver Transformation (5 min)
─────────────────────────────────────
→ Run 02_Silver_Transform.py
→ Show deduplication (before/after record counts)
→ Show derived columns (day_of_week, hour_of_day)
→ Query: Compare Bronze vs Silver row counts

STEP 6: Gold Aggregation (5 min)
────────────────────────────────
→ Run 03_Gold_Aggregations.py
→ Query gold_transactions_daily
→ Show ZORDER metadata
→ Query from SQL endpoint (same data, T-SQL syntax)

STEP 7: Pipeline & Monitoring (2 min)
─────────────────────────────────────
→ Show orchestration_config.json
→ Show 04_Pipeline_Monitoring.py output
→ Show success metrics, quality scores, duration
```

---

## ═══════════════════════════════════════════════
## SECTION 10 — Q&A + NEXT STEPS
## ═══════════════════════════════════════════════

### SLIDE 20 — Architecture Decision Summary

| Decision                      | Choice                          | Why                                               |
|-------------------------------|----------------------------------|---------------------------------------------------|
| Storage                       | 3 Separate Lakehouses           | Independent RBAC, lifecycle, capacity              |
| Configuration                 | JSON configs per layer           | No hardcoding, environment-agnostic               |
| Quality Framework             | Configurable Rules Engine        | Extensible, auditable, threshold-gated            |
| Partitioning (Bronze)         | By `ingestion_date`             | Efficient replay, time-based purge                |
| Partitioning (Gold)           | By `period_date`                | Query performance for time-range filters          |
| Optimization                  | V-Order + ZORDER (Gold only)    | Read performance where it matters most            |
| Error Handling                | Exponential backoff, decreasing | More retries for external, fewer for internal     |
| Orchestration                 | Single master pipeline           | Simplified monitoring, clear dependency chain     |

---

### SLIDE 21 — Customer Next Steps

**Immediate Actions (This Week):**
1. ✅ Deploy workspace with `00_Workspace_Setup.py`
2. ✅ Run end-to-end pipeline with sample data
3. ✅ Review quality rules and customize for your domain

**Short-Term (This Month):**
4. 🔧 Replace sample data sources with real data connections
5. 🔧 Customize Gold aggregations for your business KPIs
6. 🔧 Connect Power BI via DirectLake for real-time dashboards
7. 🔧 Set up production scheduling (daily 02:00 UTC)

**Long-Term (This Quarter):**
8. 📈 Add streaming ingestion (Event Hub → Bronze)
9. 📈 Implement CI/CD with Fabric Git integration
10. 📈 Scale to multi-workspace (dev/test/prod) with shortcuts
11. 📈 Integrate ML models consuming Gold layer features

---

### SLIDE 22 — Resources & References

| Resource                               | Location                                       |
|----------------------------------------|------------------------------------------------|
| Architecture Plan                      | `MEDALLION_ARCHITECTURE_PLAN.md`               |
| Executive Summary                      | `MEDALLION_EXECUTIVE_SUMMARY.md`               |
| Bronze Layer Notebooks                 | `BRONZE_LAYER_NOTEBOOKS.md`                    |
| Silver & Gold Notebooks                | `SILVER_GOLD_LAYER_NOTEBOOKS.md`               |
| Orchestration & Monitoring             | `ORCHESTRATION_MONITORING.md`                  |
| Configuration Guide                    | `CONFIGURATION_IMPLEMENTATION_GUIDE.md`        |
| Quick Deploy (8 Steps)                 | `QUICK_DEPLOY_8STEPS.md`                       |
| Power BI Examples                      | `POWERBI_EXAMPLES_DEPLOYMENT.md`               |
| Skills for Fabric (AI-assisted dev)    | `skills-for-fabric/`                           |
| Fabric IQ Solution Accelerator         | `FabricIQ/`                                    |

---

### SLIDE 23 — Key Takeaways

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                  │
│  1. OneLake eliminates data copies — one storage, many engines  │
│                                                                  │
│  2. Lakehouse = best of data lake + warehouse in one artifact   │
│                                                                  │
│  3. Medallion architecture enforces data quality progression     │
│                                                                  │
│  4. Config-driven design = reusable across domains & teams      │
│                                                                  │
│  5. Quality gates prevent bad data from reaching consumers      │
│                                                                  │
│  6. V-Order + ZORDER = 10–50% read performance improvement     │
│                                                                  │
│  7. Production-grade = monitoring, alerting, runbooks, retries  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

*© Microsoft Fabric IQ — L400 Technical Deep-Dive*
*Prepared for Data Engineers & Architects*
