# Notebook: ADO Work Items Extraction - Bronze Table
# Purpose: Extract work items from Azure DevOps and create Bronze Delta table
# Author: Fabric Analytics Pipeline
# Date: 2025-03-30

# CELL 1: CONFIGURATION & IMPORTS ==========================================

import requests
import json
import base64
import pandas as pd
import os
from datetime import datetime, timedelta
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, TimestampType, BooleanType

# Configuration
ADO_ORG = "https://msdata.visualstudio.com"
ADO_PROJECT = "A365"
ADO_PAT = os.environ.get("ADO_PAT", "<YOUR_ADO_PAT_HERE>")
AREA_PATH = "A365/Trident"
WORKSPACE_ID = None  # Will be populated
LAKEHOUSE_ID = None  # Will be populated
LAKEHOUSE_NAME = "Fabric_Product_LKH"

# Table names
BRONZE_TABLE = "WorkItems_Bronze"

# Encoding PAT for Basic Auth
pat_bytes = ADO_PAT.encode('utf-8')
b64_pat = base64.b64encode(pat_bytes).decode('utf-8')
headers = {'Authorization': f'Basic {b64_pat}', 'Content-Type': 'application/json'}

print("✓ Configuration loaded")
print(f"  ADO Organization: {ADO_ORG}")
print(f"  Project: {ADO_PROJECT}")
print(f"  Area Path: {AREA_PATH}")
print(f"  Target Table: {BRONZE_TABLE}")

# CELL 2: WIQL QUERY SETUP ==========================================

# WIQL (Work Item Query Language) to fetch Features and Bugs
def build_wiql_query():
    """Build WIQL query for Features and Bugs in specific area path"""
    
    # Calculate date threshold (365 days back)
    date_threshold = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    
    wiql = f"""
    SELECT 
        [System.Id],
        [System.Title],
        [System.Description],
        [System.State],
        [System.Status],
        [System.CreatedDate],
        [System.CreatedBy],
        [System.AssignedTo],
        [System.AreaPath],
        [System.Tags],
        [System.WorkItemType],
        [Custom.CustomerAccount],
        [Custom.CustomerPromise]
    FROM workitems
    WHERE 
        [System.WorkItemType] IN ('Feature', 'Bug')
        AND [System.AreaPath] UNDER '{AREA_PATH}'
        AND [System.ChangedDate] > '{date_threshold}'
    ORDER BY [System.Id] DESC
    """
    
    return wiql.strip()

wiql_query = build_wiql_query()
print("✓ WIQL query constructed")
print(f"  Query lines: {len(wiql_query.splitlines())}")

# CELL 3: FETCH WORK ITEMS FROM ADO ==========================================

def fetch_work_items_paginated(wiql_query, batch_size=200):
    """Fetch work items from ADO WIQL API with pagination"""
    
    url = f"{ADO_ORG}/{ADO_PROJECT}/_apis/wit/wiql"
    
    print(f"\n📋 Fetching work items from ADO...")
    print(f"   Endpoint: {url}")
    
    all_items = []
    skip = 0
    batch_count = 0
    
    try:
        # First request to get count
        body = {'query': wiql_query}
        response = requests.post(url, headers=headers, json=body, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        total_items = result.get('workItems', [])
        print(f"✓ Query returned {len(total_items)} work items")
        
        if not total_items:
            print("⚠️  No work items found matching criteria")
            return []
        
        # Extract IDs from WIQL results
        work_item_ids = [str(item['id']) for item in total_items[:200]]  # Limit to 200
        
        print(f"✓ Processing {len(work_item_ids)} items")
        
        # Batch fetch full work item details
        for i in range(0, len(work_item_ids), batch_size):
            batch = work_item_ids[i:i+batch_size]
            batch_ids = ','.join(batch)
            
            detail_url = f"{ADO_ORG}/{ADO_PROJECT}/_apis/wit/workitems?ids={batch_ids}&$expand=fields&api-version=6.0"
            
            detail_response = requests.get(detail_url, headers=headers, timeout=60)
            detail_response.raise_for_status()
            
            batch_data = detail_response.json()
            all_items.extend(batch_data.get('value', []))
            
            batch_count += 1
            print(f"  ✓ Batch {batch_count}: {len(batch_data.get('value', []))} items fetched")
        
        print(f"✓ Total items fetched: {len(all_items)}")
        
    except requests.exceptions.RequestException as e:
        print(f"✗ Error fetching work items: {str(e)}")
        raise
    
    return all_items

work_items = fetch_work_items_paginated(wiql_query)

# CELL 4: PARSE & CREATE DATAFRAME ==========================================

def parse_work_items(work_items):
    """Parse ADO work items into standardized format"""
    
    print(f"\n📊 Parsing {len(work_items)} work items...")
    
    records = []
    
    for item in work_items:
        try:
            fields = item.get('fields', {})
            
            # Extract core fields
            record = {
                'WorkItemId': item.get('id'),
                'Title': fields.get('System.Title', ''),
                'Description': fields.get('System.Description', ''),
                'State': fields.get('System.State', ''),
                'Status': fields.get('System.Status', ''),
                'CreatedDate': fields.get('System.CreatedDate', ''),
                'CreatedBy': fields.get('System.CreatedBy', {}).get('displayName', '') if isinstance(fields.get('System.CreatedBy'), dict) else fields.get('System.CreatedBy', ''),
                'AssignedTo': fields.get('System.AssignedTo', {}).get('displayName', '') if isinstance(fields.get('System.AssignedTo'), dict) else fields.get('System.AssignedTo', ''),
                'AreaPath': fields.get('System.AreaPath', ''),
                'Tags': fields.get('System.Tags', ''),
                'WorkItemType': fields.get('System.WorkItemType', ''),
                'CustomAccount': fields.get('Custom.CustomerAccount', ''),
                'CustomerPromise': fields.get('Custom.CustomerPromise', False)
            }
            
            records.append(record)
            
        except Exception as e:
            print(f"  ⚠️  Error parsing item {item.get('id')}: {str(e)}")
            continue
    
    # Convert to DataFrame
    df = pd.DataFrame(records)
    
    print(f"✓ Parsed {len(records)} records")
    print(f"  Columns: {', '.join(df.columns.tolist())}")
    print(f"  Data types:\n{df.dtypes}")
    print(f"\n  Sample data:")
    print(df.head(3).to_string())
    
    return df

parsed_df = parse_work_items(work_items)

# CELL 5: CREATE DELTA TABLE ==========================================

def create_bronze_table(df):
    """Create Bronze Delta table in Lakehouse"""
    
    print(f"\n💾 Creating Delta table: {BRONZE_TABLE}...")
    
    # Initialize Spark
    spark = SparkSession.builder.appName("ADOExtraction").getOrCreate()
    
    # Convert Pandas to Spark DataFrame
    spark_df = spark.createDataFrame(parsed_df)
    
    # Write as Delta table
    table_path = f"abfss://{LAKEHOUSE_NAME}@onelake.dfs.fabric.microsoft.com/Tables/{BRONZE_TABLE}"
    
    try:
        spark_df.write \
            .format("delta") \
            .mode("overwrite") \
            .option("mergeSchema", "true") \
            .save(table_path)
        
        print(f"✓ Delta table created: {BRONZE_TABLE}")
        print(f"  Path: {table_path}")
        print(f"  Records: {spark_df.count()}")
        print(f"  Partitions: {spark_df.rdd.getNumPartitions()}")
        
    except Exception as e:
        print(f"✗ Error creating Delta table: {str(e)}")
        raise
    
    # Verify table
    verify_df = spark.read.format("delta").load(table_path)
    print(f"\n✓ Verification:")
    print(f"  Total rows: {verify_df.count()}")
    print(f"  Schema:")
    verify_df.printSchema()
    
    return verify_df

bronze_df = create_bronze_table(parsed_df)

# ═══════════════════════════════════════════════════════════════════════════

print("\n" + "="*70)
print("✅ BRONZE TABLE CREATION COMPLETE")
print("="*70)
print(f"\nNext step: Run notebook '2_WorkItems_Silver_Transform'")
print(f"This will clean and transform the Bronze table into Silver layer")
