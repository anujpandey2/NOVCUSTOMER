"""
ADO Work Items Extraction Script
Extracts Feature and Bug work items from ADO project A365, Area Path A365/Trident
"""

import requests
import json
import base64
import os
from datetime import datetime
import pandas as pd

# ADO Configuration
ADO_ORG = "msdata"
ADO_PROJECT = "A365"
ADO_AREA_PATH = "A365/Trident"
ADO_PAT = os.environ.get("ADO_PAT", "<YOUR_ADO_PAT_HERE>")

# Encode PAT for basic auth
auth_string = base64.b64encode(f":{ADO_PAT}".encode()).decode()
headers = {
    "Authorization": f"Basic {auth_string}",
    "Content-Type": "application/json"
}

def get_work_items():
    """
    Query ADO for Features and Bugs in A365/Trident area modified in last 90 days
    """
    # WIQL Query to fetch Feature and Bug work items from A365/Trident area
    # Filter by changed date to limit results
    from datetime import datetime, timedelta
    past_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
    
    wiql_query = {
        "query": f"SELECT [System.Id] FROM workitems WHERE [System.WorkItemType] IN ('Feature', 'Bug') AND [System.AreaPath] UNDER 'A365\\Trident' AND [System.ChangedDate] > '{past_date}'"
    }
    
    url = f"https://dev.azure.com/{ADO_ORG}/{ADO_PROJECT}/_apis/wit/wiql?api-version=7.1"
    
    try:
        print(f"Querying ADO at: {url}")
        response = requests.post(url, headers=headers, json=wiql_query)
        print(f"Response Status: {response.status_code}")
        print(f"Response Body: {response.text}")
        response.raise_for_status()
        
        query_results = response.json()
        work_item_ids = [item['id'] for item in query_results.get('workItems', [])]
        
        print(f"Found {len(work_item_ids)} work items")
        
        if not work_item_ids:
            print("No work items found in the specified area path")
            return pd.DataFrame()
        
        # Get detailed information for each work item
        return fetch_work_item_details(work_item_ids)
        
    except requests.exceptions.RequestException as e:
        print(f"Error querying ADO: {e}")
        return pd.DataFrame()

def fetch_work_item_details(work_item_ids):
    """
    Fetch detailed information for work items
    """
    url = f"https://dev.azure.com/{ADO_ORG}/{ADO_PROJECT}/_apis/wit/workitems?ids={','.join(map(str, work_item_ids))}&api-version=7.1&$expand=relations&fields=System.Id,System.Title,System.Description,System.State,System.CreatedDate,System.CreatedBy,System.AssignedTo,System.AreaPath,System.Tags,System.WorkItemType,Custom.CustomerAccount,Custom.CustomerPromise"
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        work_items_data = response.json()
        
        # Transform to DataFrame
        records = []
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
                'CreatedBy': fields.get('System.CreatedBy', {}).get('displayName', 'Unknown'),
                'AssignedTo': fields.get('System.AssignedTo', {}).get('displayName', 'Unassigned'),
                'AreaPath': fields.get('System.AreaPath'),
                'Tags': fields.get('System.Tags'),
                'WorkItemType': fields.get('System.WorkItemType'),
                'CustomAccount': fields.get('Custom.CustomerAccount'),
                'CustomerPromise': fields.get('Custom.CustomerPromise', False),
                'Url': item.get('url'),
                '_links': item.get('_links', {})
            }
            records.append(record)
        
        df = pd.DataFrame(records)
        print(f"Successfully fetched {len(df)} work item details")
        return df
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching work item details: {e}")
        return pd.DataFrame()

def save_to_json(df, filename):
    """Save DataFrame to JSON for Fabric ingestion"""
    if df.empty:
        print("No data to save")
        return
    
    # Convert to records format
    records = df.to_dict('records')
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(records, f, indent=2, default=str)
    
    print(f"Saved {len(records)} records to {filename}")
    return filename

if __name__ == "__main__":
    print("Starting ADO Work Items Extraction...")
    print(f"Organization: {ADO_ORG}")
    print(f"Project: {ADO_PROJECT}")
    print(f"Area Path: {ADO_AREA_PATH}")
    print()
    
    # Get work items
    df = get_work_items()
    
    if not df.empty:
        print(f"\nExtracted {len(df)} work items")
        print(f"Columns: {', '.join(df.columns.tolist())}")
        print(f"\nSample record:")
        print(df.iloc[0].to_dict() if len(df) > 0 else "No data")
        
        # Save to JSON
        output_file = "C:/Users/anujpandey/ado_work_items.json"
        save_to_json(df, output_file)
        
        # Also save as CSV for reference
        csv_file = "C:/Users/anujpandey/ado_work_items.csv"
        df.to_csv(csv_file, index=False)
        print(f"Also saved to CSV: {csv_file}")
    else:
        print("No work items were extracted")
