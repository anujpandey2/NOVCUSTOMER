"""
Fabric Notebook: ADO to Analytics Pipeline
This notebook orchestrates:
1. ADO work item retrieval
2. Bronze table creation
3. Silver table transformation
4. Semantic model setup

Run this in Fabric Workspace: Fabric_Product_Analytics26
Lakehouse: Fabric_Product_LKH
"""

# Notebook Cell 1: Import Libraries and Setup
print("Cell 1: Importing libraries and configuration...")

import requests
import os
import json
import base64
from pyspark.sql import SparkSession
from pyspark.sql.types import *
import pandas as pd
from datetime import datetime, timedelta

# ADO Configuration
ADO_ORG = "msdata"
ADO_PROJECT = "A365"
ADO_AREA_PATH = "A365/Trident"
ADO_PAT = os.environ.get("ADO_PAT", "<YOUR_ADO_PAT_HERE>")

# Encode PAT for basic auth
auth_string = base64.b64encode(f":{ADO_PAT}".encode()).decode()
ado_headers = {
    "Authorization": f"Basic {auth_string}",
    "Content-Type": "application/json"
}

# Initialize Spark
spark = SparkSession.builder \
    .appName("ADOToFabricPipeline") \
    .getOrCreate()

print(f"✓ Spark Session initialized")
print(f"✓ ADO Configuration: {ADO_ORG}/{ADO_PROJECT}/{ADO_AREA_PATH}")

# Notebook Cell 2: Query ADO for Work Items
print("\n\nCell 2: Querying ADO for work items...")

def get_ado_work_items():
    """Query ADO WIQL for Features and Bugs"""
    
    # Filter by recent changes to avoid result size limit
    past_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
    
    wiql_query = {
        "query": f"SELECT [System.Id] FROM workitems WHERE [System.WorkItemType] IN ('Feature', 'Bug') AND [System.AreaPath] UNDER 'A365\\Trident' AND [System.ChangedDate] > '{past_date}'"
    }
    
    url = f"https://dev.azure.com/{ADO_ORG}/{ADO_PROJECT}/_apis/wit/wiql?api-version=7.1"
    
    print(f"Querying: {url}")
    print(f"WIQL: {wiql_query['query']}")
    
    try:
        response = requests.post(url, headers=ado_headers, json=wiql_query)
        print(f"Response Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Error: {response.text}")
            return []
        
        query_results = response.json()
        work_item_ids = [item['id'] for item in query_results.get('workItems', [])]
        
        print(f"✓ Found {len(work_item_ids)} work items")
        return work_item_ids
        
    except Exception as e:
        print(f"Error querying ADO: {e}")
        return []

# Get work item IDs
work_item_ids = get_ado_work_items()

# Notebook Cell 3: Fetch Work Item Details
print("\n\nCell 3: Fetching work item details...")

def fetch_work_item_details(ids):
    """Fetch detailed information for work items"""
    
    if not ids:
        print("No work items to fetch")
        return pd.DataFrame()
    
    # Process in batches (ADO has limits)
    batch_size = 200
    all_records = []
    
    for i in range(0, len(ids), batch_size):
        batch_ids = ids[i:i+batch_size]
        id_string = ','.join(map(str, batch_ids))
        
        url = f"https://dev.azure.com/{ADO_ORG}/{ADO_PROJECT}/_apis/wit/workitems?ids={id_string}&api-version=7.1&$expand=relations"
        
        try:
            response = requests.get(url, headers=ado_headers)
            
            if response.status_code != 200:
                print(f"Error fetching batch {i//batch_size + 1}: {response.status_code}")
                continue
            
            work_items_data = response.json()
            
            for item in work_items_data.get('value', []):
                fields = item.get('fields', {})
                record = {
                    'WorkItemId': item.get('id'),
                    'Name': fields.get('System.Title'),
                    'Title': fields.get('System.Title'),
                    'Description': fields.get('System.Description'),
                    'State': fields.get('System.State'),
                    'Status': fields.get('System.State'),
                    'CreatedDate': fields.get('System.CreatedDate'),
                    'CreatedBy': fields.get('System.CreatedBy', {}).get('displayName') if isinstance(fields.get('System.CreatedBy'), dict) else fields.get('System.CreatedBy'),
                    'AssignedTo': fields.get('System.AssignedTo', {}).get('displayName') if isinstance(fields.get('System.AssignedTo'), dict) else 'Unassigned',
                    'AreaPath': fields.get('System.AreaPath'),
                    'Tags': fields.get('System.Tags'),
                    'WorkItemType': fields.get('System.WorkItemType'),
                    'CustomAccount': fields.get('Custom.CustomerAccount'),
                    'CustomerPromise': fields.get('Custom.CustomerPromise', False),
                }
                all_records.append(record)
        
        except Exception as e:
            print(f"Error in batch {i//batch_size + 1}: {e}")
        
        print(f"Processed batch {i//batch_size + 1}/{(len(ids)-1)//batch_size + 1}: {len(all_records)} records total")
    
    df = pd.DataFrame(all_records)
    print(f"✓ Fetched {len(df)} work item details")
    return df

# Fetch details
df_work_items = fetch_work_item_details(work_item_ids)

# Notebook Cell 4: Create Bronze Delta Table
print("\n\nCell 4: Creating Bronze Delta Table...")

if not df_work_items.empty:
    # Convert to Spark DataFrame
    df_bronze = spark.createDataFrame(df_work_items)
    
    # Write as Delta table
    bronze_table_name = "WorkItems_Bronze"
    bronze_path = f"/lakehouse/default/Tables/{bronze_table_name}"
    
    df_bronze.write \
        .format("delta") \
        .mode("overwrite") \
        .option("mergeSchema", "true") \
        .save(bronze_path)
    
    print(f"✓ Created Bronze Delta table: {bronze_table_name}")
    print(f"  Records: {df_bronze.count()}")
    print(f"  Schema:")
    df_bronze.printSchema()
else:
    print("No data to create Bronze table")

# Notebook Cell 5: Transform to Silver Delta Table
print("\n\nCell 5: Transforming to Silver Delta Table...")

if not df_work_items.empty:
    # Read Bronze table
    df_bronze_read = spark.read.format("delta").load(bronze_path)
    
    # Filter: Remove rows where Name/Title or Description is NULL
    df_silver = df_bronze_read.filter(
        (df_bronze_read.Title.isNotNull()) & 
        (df_bronze_read.Title != "") &
        (df_bronze_read.Description.isNotNull()) & 
        (df_bronze_read.Description != "")
    )
    
    # Write as Delta table
    silver_table_name = "Cleaned_Items_Silver"
    silver_path = f"/lakehouse/default/Tables/{silver_table_name}"
    
    df_silver.write \
        .format("delta") \
        .mode("overwrite") \
        .option("mergeSchema", "true") \
        .save(silver_path)
    
    print(f"✓ Created Silver Delta table: {silver_table_name}")
    print(f"  Records (after cleaning): {df_silver.count()}")
    print(f"  Records removed: {df_bronze_read.count() - df_silver.count()}")
    
    # Show sample
    df_silver.limit(5).show(truncate=False)
else:
    print("No data to transform")

# Notebook Cell 6: Display Transformation Summary
print("\n\nCell 6: Transformation Summary")

print("\n=== PIPELINE EXECUTION SUMMARY ===")
print(f"ADO Query: {ADO_ORG}/{ADO_PROJECT} - Area: {ADO_AREA_PATH}")
print(f"Work Items Retrieved: {len(work_item_ids) if work_item_ids else 0}")
print(f"Bronze Table Records: {df_bronze.count() if not df_work_items.empty else 0}")
print(f"Silver Table Records: {df_silver.count() if not df_work_items.empty else 0}")
print(f"Null/Empty Records Removed: {(df_bronze.count() - df_silver.count()) if not df_work_items.empty else 0}")
print("\nBronze Table: WorkItems_Bronze")
print("Silver Table: Cleaned_Items_Silver")
print("\n✓ Pipeline execution complete!")
print("Next steps:")
print("1. Create Power BI semantic model on Cleaned_Items_Silver")
print("2. Create report for Active Bugs (State = Active)")
print("3. Create report for Customer Promise Features (CustomerPromise = True)")
