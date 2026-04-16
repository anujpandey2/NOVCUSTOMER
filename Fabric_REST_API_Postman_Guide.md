# Microsoft Fabric REST APIs via Postman — Practical Step-by-Step Guide
### From Zero to API Calls in 30 Minutes

---

## TABLE OF CONTENTS

| #  | Section                                           |
|----|---------------------------------------------------|
| 1  | Prerequisites & What You'll Need                  |
| 2  | Step 1 — Register an App in Microsoft Entra       |
| 3  | Step 2 — Configure API Permissions                |
| 4  | Step 3 — Set Up Postman Environment               |
| 5  | Step 4 — Configure OAuth 2.0 in Postman           |
| 6  | Step 5 — Get Your First Access Token              |
| 7  | API Recipes — 20+ Ready-to-Use Requests           |
| 8  | Automating Token Refresh (Pre-Request Scripts)    |
| 9  | Error Handling & Troubleshooting                  |
| 10 | Postman Collection JSON (Import-Ready)            |

---

## 1. PREREQUISITES & WHAT YOU'LL NEED

```
✅ Postman Desktop (free tier is fine)      → https://www.postman.com/downloads/
✅ Microsoft Fabric workspace               → https://app.fabric.microsoft.com
✅ Microsoft Entra admin access              → https://entra.microsoft.com
   (or ask your tenant admin to register the app for you)
✅ A Fabric capacity (Trial, P1, or F SKU)
```

**Key URLs you'll use throughout this guide:**

| Purpose              | URL                                                              |
|----------------------|------------------------------------------------------------------|
| Fabric API Base      | `https://api.fabric.microsoft.com/v1`                           |
| Token Endpoint       | `https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token` |
| Auth Endpoint        | `https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize` |
| API Scope            | `https://api.fabric.microsoft.com/.default`                     |
| Postman Callback     | `https://oauth.pstmn.io/v1/callback`                           |

---

## 2. STEP 1 — REGISTER AN APP IN MICROSOFT ENTRA

### 2.1 Navigate to App Registrations

1. Open **https://entra.microsoft.com**
2. Left sidebar → **Identity** → **Applications** → **App registrations**
3. Click **"+ New registration"**

### 2.2 Fill in Registration Details

```
Name:                    Postman-Fabric-API
Supported account types: Accounts in this organizational directory only (Single tenant)
Redirect URI:
  Platform:  Web
  URI:       https://oauth.pstmn.io/v1/callback
```

> ⚠️ **The redirect URI must be exactly `https://oauth.pstmn.io/v1/callback`** — this is Postman's OAuth callback endpoint.

4. Click **Register**

### 2.3 Collect Your Values (Save These!)

After registration, you'll land on the app's **Overview** page. Copy these three values:

```
┌─────────────────────────────────────────────────────────────┐
│  Application (client) ID:   xxxxxxxx-xxxx-xxxx-xxxx-xxxxx  │  ← client_id
│  Directory (tenant) ID:     xxxxxxxx-xxxx-xxxx-xxxx-xxxxx  │  ← tenant_id
│  Object ID:                 xxxxxxxx-xxxx-xxxx-xxxx-xxxxx  │  ← (for reference)
└─────────────────────────────────────────────────────────────┘
```

### 2.4 Create a Client Secret

1. Left sidebar → **Certificates & secrets**
2. Click **"+ New client secret"**
3. Description: `Postman-Secret`
4. Expiry: **6 months** (or your org policy)
5. Click **Add**
6. **⚠️ IMMEDIATELY copy the "Value" column** — it's only shown once!

```
┌──────────────────────────────────────────────────┐
│  Client Secret Value:  xYz...your_secret_here    │  ← client_secret
│  Secret ID:            xxxxxxxx-xxxx-xxxx-xxxxx  │
│  Expires:              2026-10-16                 │
└──────────────────────────────────────────────────┘
```

---

## 3. STEP 2 — CONFIGURE API PERMISSIONS

### 3.1 Add Fabric API Permissions

1. In your app registration → Left sidebar → **API permissions**
2. Click **"+ Add a permission"**
3. Select tab **"APIs my organization uses"**
4. Search for: **`Power BI Service`** (Fabric permissions are under Power BI Service)
5. Select **Delegated permissions**
6. Check the following:

```
Recommended Permissions (Delegated):
  ✅ Workspace.ReadWrite.All      — Read/write workspaces
  ✅ Item.ReadWrite.All            — Read/write items (lakehouses, notebooks, etc.)
  ✅ Item.Execute.All              — Execute items (run notebooks, pipelines)
  ✅ Capacity.ReadWrite.All        — Manage capacity (optional, admin only)
  ✅ Dataset.ReadWrite.All         — Semantic models (optional, for Power BI)
  ✅ Report.ReadWrite.All          — Reports (optional, for Power BI)
```

7. Click **"Add permissions"**
8. Click **"✅ Grant admin consent for [Your Org]"** (requires admin role)

> 💡 **Tip:** If you don't have admin consent rights, ask your tenant admin to grant consent.

### 3.2 Verify Permissions

Your API permissions page should look like:

```
┌────────────────────────────────────────────────────────────────┐
│  API / Permission name          │ Type       │ Status          │
├────────────────────────────────────────────────────────────────┤
│  Power BI Service                                              │
│    Workspace.ReadWrite.All      │ Delegated  │ ✅ Granted      │
│    Item.ReadWrite.All           │ Delegated  │ ✅ Granted      │
│    Item.Execute.All             │ Delegated  │ ✅ Granted      │
│  Microsoft Graph                                               │
│    User.Read                    │ Delegated  │ ✅ Granted      │
└────────────────────────────────────────────────────────────────┘
```

---

## 4. STEP 3 — SET UP POSTMAN ENVIRONMENT

### 4.1 Create a New Environment

1. In Postman → click **Environments** (left sidebar)
2. Click **"+"** to create a new environment
3. Name it: **`Microsoft Fabric`**

### 4.2 Add Variables

Add these variables (set **Current Value** = **Initial Value**):

```
┌───────────────────┬──────────────────────────────────────────────────────────┬───────┐
│  Variable          │  Value                                                   │ Type  │
├───────────────────┼──────────────────────────────────────────────────────────┼───────┤
│  tenant_id         │  YOUR-TENANT-ID-GUID                                     │ default│
│  client_id         │  YOUR-CLIENT-ID-GUID                                     │ default│
│  client_secret     │  YOUR-SECRET-VALUE                                       │ secret│
│  base_url          │  https://api.fabric.microsoft.com/v1                     │ default│
│  auth_url          │  https://login.microsoftonline.com/{{tenant_id}}/oauth2/v2.0/authorize │ default│
│  token_url         │  https://login.microsoftonline.com/{{tenant_id}}/oauth2/v2.0/token     │ default│
│  scope             │  https://api.fabric.microsoft.com/.default               │ default│
│  callback_url      │  https://oauth.pstmn.io/v1/callback                     │ default│
│  workspace_id      │  (fill after first API call)                             │ default│
│  access_token      │  (auto-populated)                                        │ secret│
└───────────────────┴──────────────────────────────────────────────────────────┴───────┘
```

4. Click **Save**
5. Select **"Microsoft Fabric"** as your active environment (top-right dropdown)

---

## 5. STEP 4 — CONFIGURE OAUTH 2.0 IN POSTMAN

### Option A: Authorization Code Flow (Recommended — User Context)

This flow prompts you to sign in with your Microsoft account. Best for interactive development.

1. Create a new **Collection** → name it **"Fabric REST APIs"**
2. Click the collection → go to the **Authorization** tab
3. Configure:

```
Type:                    OAuth 2.0
Add auth data to:        Request Headers

── Configure New Token ─────────────────────────────────────────

Token Name:              Fabric Token
Grant Type:              Authorization Code

Callback URL:            {{callback_url}}
                         ✅ Authorize using browser (check this box!)

Auth URL:                {{auth_url}}
Access Token URL:        {{token_url}}
Client ID:               {{client_id}}
Client Secret:           {{client_secret}}
Scope:                   {{scope}}
State:                   (leave empty)
Client Authentication:   Send as Basic Auth Header
```

4. Click **"Get New Access Token"**
5. A browser window opens → sign in with your Microsoft account
6. After consent → Postman receives the token
7. Click **"Use Token"**

> ✅ **All requests in this collection now inherit this token automatically!**

---

### Option B: Client Credentials Flow (Service Principal — No User Interaction)

Best for automation, CI/CD, and scripts. Requires the app to have **Application permissions** (not Delegated).

1. Same setup, but change:

```
Grant Type:              Client Credentials
Access Token URL:        {{token_url}}
Client ID:               {{client_id}}
Client Secret:           {{client_secret}}
Scope:                   {{scope}}
Client Authentication:   Send as Basic Auth Header
```

> ⚠️ **For Client Credentials to work with Fabric APIs**, you must:
> - Add your service principal to the Fabric workspace as **Admin** or **Member**
> - Enable "Service principals can use Fabric APIs" in the **Fabric Admin Portal** → Tenant settings

---

## 6. STEP 5 — YOUR FIRST API CALL

### Test: List All Workspaces

```
Method:  GET
URL:     {{base_url}}/workspaces
Auth:    Inherit from parent (OAuth 2.0)
```

**Expected Response (200 OK):**
```json
{
  "value": [
    {
      "id": "cfafbeb1-8037-4d0c-896e-a46fb27ff229",
      "displayName": "My Fabric Workspace",
      "description": "Production workspace",
      "type": "Workspace",
      "state": "Active",
      "capacityId": "a1b2c3d4-..."
    }
  ]
}
```

> 🎉 **If you see your workspaces, everything is working!** Copy a `workspace_id` and save it to your Postman environment variable.

---

## 7. API RECIPES — 20+ READY-TO-USE REQUESTS

### ─── WORKSPACE MANAGEMENT ───────────────────────────

#### 7.1 List All Workspaces
```
GET {{base_url}}/workspaces
```

#### 7.2 Get a Specific Workspace
```
GET {{base_url}}/workspaces/{{workspace_id}}
```

#### 7.3 Create a New Workspace
```
POST {{base_url}}/workspaces
Content-Type: application/json

{
  "displayName": "Dev-Analytics-Workspace",
  "description": "Development workspace for analytics team",
  "capacityId": "{{capacity_id}}"
}
```

#### 7.4 Update Workspace
```
PATCH {{base_url}}/workspaces/{{workspace_id}}
Content-Type: application/json

{
  "displayName": "Dev-Analytics-Workspace-v2",
  "description": "Updated description"
}
```

#### 7.5 Delete Workspace
```
DELETE {{base_url}}/workspaces/{{workspace_id}}
```
> ⚠️ **Destructive!** Use with caution.

---

### ─── LAKEHOUSE OPERATIONS ───────────────────────────

#### 7.6 List Lakehouses in Workspace
```
GET {{base_url}}/workspaces/{{workspace_id}}/lakehouses
```

**Response:**
```json
{
  "value": [
    {
      "id": "5b218778-e7a5-4d73-8187-f10824047715",
      "displayName": "bronze_lakehouse",
      "type": "Lakehouse",
      "properties": {
        "oneLakeTablesPath": "https://onelake.dfs.fabric.microsoft.com/...",
        "oneLakeFilesPath": "https://onelake.dfs.fabric.microsoft.com/...",
        "sqlEndpointProperties": {
          "connectionString": "xxxx.datawarehouse.fabric.microsoft.com",
          "id": "...",
          "provisioningStatus": "Success"
        }
      }
    }
  ]
}
```

#### 7.7 Create a Lakehouse
```
POST {{base_url}}/workspaces/{{workspace_id}}/lakehouses
Content-Type: application/json

{
  "displayName": "silver_lakehouse",
  "description": "Silver layer - cleansed and validated data"
}
```

#### 7.8 Get a Specific Lakehouse
```
GET {{base_url}}/workspaces/{{workspace_id}}/lakehouses/{{lakehouse_id}}
```

#### 7.9 Delete a Lakehouse
```
DELETE {{base_url}}/workspaces/{{workspace_id}}/lakehouses/{{lakehouse_id}}
```

---

### ─── ITEMS (GENERIC — Works for Any Item Type) ─────

#### 7.10 List All Items in Workspace
```
GET {{base_url}}/workspaces/{{workspace_id}}/items
```

#### 7.11 List Items by Type
```
GET {{base_url}}/workspaces/{{workspace_id}}/items?type=Notebook
```

**Supported type values:**
```
Notebook, Lakehouse, Warehouse, DataPipeline,
SemanticModel, Report, Dashboard, Dataflow,
Environment, MLModel, MLExperiment, Eventstream,
KQLDatabase, KQLDashboard, SQLEndpoint
```

#### 7.12 Get a Specific Item
```
GET {{base_url}}/workspaces/{{workspace_id}}/items/{{item_id}}
```

#### 7.13 Delete an Item
```
DELETE {{base_url}}/workspaces/{{workspace_id}}/items/{{item_id}}
```

---

### ─── NOTEBOOKS ─────────────────────────────────────

#### 7.14 List Notebooks
```
GET {{base_url}}/workspaces/{{workspace_id}}/notebooks
```

#### 7.15 Create a Notebook
```
POST {{base_url}}/workspaces/{{workspace_id}}/notebooks
Content-Type: application/json

{
  "displayName": "01_Bronze_Ingestion",
  "description": "Bronze layer ingestion notebook"
}
```

#### 7.16 Get Notebook Definition (Download Code)
```
POST {{base_url}}/workspaces/{{workspace_id}}/notebooks/{{notebook_id}}/getDefinition
Content-Type: application/json
```

> 💡 This is a **Long Running Operation (LRO)**. The response returns a `202 Accepted` with a `Location` header. Poll that URL until you get the notebook content.

---

### ─── DATA PIPELINES ────────────────────────────────

#### 7.17 List Pipelines
```
GET {{base_url}}/workspaces/{{workspace_id}}/dataPipelines
```

#### 7.18 Create a Pipeline
```
POST {{base_url}}/workspaces/{{workspace_id}}/dataPipelines
Content-Type: application/json

{
  "displayName": "medallion_master_pipeline",
  "description": "Master orchestration pipeline for Bronze → Silver → Gold"
}
```

---

### ─── WAREHOUSE ─────────────────────────────────────

#### 7.19 List Warehouses
```
GET {{base_url}}/workspaces/{{workspace_id}}/warehouses
```

#### 7.20 Create a Warehouse
```
POST {{base_url}}/workspaces/{{workspace_id}}/warehouses
Content-Type: application/json

{
  "displayName": "analytics_warehouse",
  "description": "SQL analytics warehouse"
}
```

---

### ─── SPARK JOB DEFINITIONS ─────────────────────────

#### 7.21 List Spark Job Definitions
```
GET {{base_url}}/workspaces/{{workspace_id}}/sparkJobDefinitions
```

#### 7.22 Run a Spark Job On-Demand
```
POST {{base_url}}/workspaces/{{workspace_id}}/items/{{item_id}}/jobs/instances?jobType=sparkjob
```

> Returns `202 Accepted` with `Location` header for polling job status.

---

### ─── CAPACITY & ADMIN ──────────────────────────────

#### 7.23 List Capacities
```
GET {{base_url}}/capacities
```

#### 7.24 Get Capacity Details
```
GET {{base_url}}/capacities/{{capacity_id}}
```

---

### ─── LONG RUNNING OPERATIONS (LRO) ─────────────────

Many Fabric API calls return `202 Accepted` with a polling URL.

#### 7.25 Poll Operation Status
```
GET {{base_url}}/operations/{{operation_id}}
```

**Response states:**
```json
{ "status": "NotStarted" }     // Still queued
{ "status": "Running" }        // In progress
{ "status": "Succeeded" }      // Done — check 'Location' header for result
{ "status": "Failed" }         // Error — check 'error' object
```

**Postman Tip:** Use a pre-request script to auto-poll (see Section 8).

---

### ─── ONELAKE FILE OPERATIONS (ADLS Gen2 API) ──────

OneLake uses the **Azure Data Lake Storage Gen2** REST API, not the Fabric API.

#### 7.26 List Files in Lakehouse
```
GET https://onelake.dfs.fabric.microsoft.com/{{workspace_id}}/{{lakehouse_id}}/Files?resource=filesystem&recursive=false
Authorization: Bearer {{access_token}}
```

#### 7.27 Upload a File to Lakehouse
**Step 1 — Create the file:**
```
PUT https://onelake.dfs.fabric.microsoft.com/{{workspace_id}}/{{lakehouse_id}}/Files/raw/sample.csv?resource=file
Authorization: Bearer {{access_token}}
```

**Step 2 — Append content:**
```
PATCH https://onelake.dfs.fabric.microsoft.com/{{workspace_id}}/{{lakehouse_id}}/Files/raw/sample.csv?action=append&position=0
Authorization: Bearer {{access_token}}
Content-Type: text/csv

id,name,value
1,alpha,100
2,beta,200
3,gamma,300
```

**Step 3 — Flush (commit):**
```
PATCH https://onelake.dfs.fabric.microsoft.com/{{workspace_id}}/{{lakehouse_id}}/Files/raw/sample.csv?action=flush&position=42
Authorization: Bearer {{access_token}}
```
> ⚠️ `position` must equal the total bytes uploaded.

#### 7.28 Read/Download a File
```
GET https://onelake.dfs.fabric.microsoft.com/{{workspace_id}}/{{lakehouse_id}}/Files/raw/sample.csv
Authorization: Bearer {{access_token}}
```

#### 7.29 Delete a File
```
DELETE https://onelake.dfs.fabric.microsoft.com/{{workspace_id}}/{{lakehouse_id}}/Files/raw/sample.csv
Authorization: Bearer {{access_token}}
```

> 💡 **Scope for OneLake:** Use `https://storage.azure.com/.default` as the scope for OneLake/ADLS Gen2 operations, **not** the Fabric scope.

---

## 8. AUTOMATING TOKEN REFRESH (PRE-REQUEST SCRIPTS)

### Auto-Refresh Token Script

Add this as a **Pre-request Script** at the Collection level:

```javascript
// Auto-refresh access token using Client Credentials
const tokenUrl = pm.environment.get("token_url");
const clientId = pm.environment.get("client_id");
const clientSecret = pm.environment.get("client_secret");
const scope = pm.environment.get("scope");

// Check if token exists and is not expired
const currentToken = pm.environment.get("access_token");
const tokenExpiry = pm.environment.get("token_expiry");
const now = Math.floor(Date.now() / 1000);

if (currentToken && tokenExpiry && now < parseInt(tokenExpiry) - 300) {
    // Token still valid (with 5-min buffer), skip refresh
    console.log("Token still valid, skipping refresh");
    return;
}

// Request new token
pm.sendRequest({
    url: tokenUrl,
    method: 'POST',
    header: {
        'Content-Type': 'application/x-www-form-urlencoded'
    },
    body: {
        mode: 'urlencoded',
        urlencoded: [
            { key: 'grant_type',    value: 'client_credentials' },
            { key: 'client_id',     value: clientId },
            { key: 'client_secret', value: clientSecret },
            { key: 'scope',         value: scope }
        ]
    }
}, function (err, res) {
    if (err) {
        console.error("Token request failed:", err);
        return;
    }

    const jsonResponse = res.json();

    if (jsonResponse.access_token) {
        pm.environment.set("access_token", jsonResponse.access_token);
        pm.environment.set("token_expiry", (now + jsonResponse.expires_in).toString());
        console.log("Token refreshed successfully. Expires in", jsonResponse.expires_in, "seconds");
    } else {
        console.error("Token response error:", JSON.stringify(jsonResponse));
    }
});
```

### Auto-Capture workspace_id from Response

Add as a **Test script** on the "List Workspaces" request:

```javascript
// Auto-save first workspace_id to environment
const response = pm.response.json();
if (response.value && response.value.length > 0) {
    pm.environment.set("workspace_id", response.value[0].id);
    console.log("Saved workspace_id:", response.value[0].id);
}
```

---

## 9. ERROR HANDLING & TROUBLESHOOTING

### Common Errors & Fixes

```
┌─────────┬──────────────────────────────────────┬────────────────────────────────────────┐
│  Code   │  Error                                │  Fix                                   │
├─────────┼──────────────────────────────────────┼────────────────────────────────────────┤
│  401    │  Unauthorized / Invalid token         │  Token expired → click "Get New         │
│         │                                       │  Access Token" or check client_secret   │
├─────────┼──────────────────────────────────────┼────────────────────────────────────────┤
│  403    │  Forbidden / Insufficient privileges  │  Missing API permissions or workspace   │
│         │                                       │  role. Check Entra permissions & RBAC   │
├─────────┼──────────────────────────────────────┼────────────────────────────────────────┤
│  404    │  Resource not found                   │  Wrong workspace_id/item_id or item     │
│         │                                       │  was deleted. Re-list to get current IDs│
├─────────┼──────────────────────────────────────┼────────────────────────────────────────┤
│  429    │  Too Many Requests (Rate Limit)       │  Wait and retry. Fabric APIs have       │
│         │                                       │  rate limits. Check Retry-After header   │
├─────────┼──────────────────────────────────────┼────────────────────────────────────────┤
│  400    │  Bad Request                          │  Check JSON body syntax. Validate        │
│         │                                       │  displayName doesn't contain specials    │
├─────────┼──────────────────────────────────────┼────────────────────────────────────────┤
│ AADSTS  │  AADSTS70011: Invalid scope           │  Use https://api.fabric.microsoft.com/  │
│         │                                       │  .default (not individual scopes)        │
├─────────┼──────────────────────────────────────┼────────────────────────────────────────┤
│ AADSTS  │  AADSTS700016: App not found          │  Wrong tenant_id or client_id. Verify   │
│         │                                       │  in Entra portal → App registrations     │
└─────────┴──────────────────────────────────────┴────────────────────────────────────────┘
```

### Debugging Checklist

```
□ Is the correct Postman environment selected? (top-right dropdown)
□ Are environment variables populated? (no {{variable}} in URLs)
□ Is the access token still valid? (tokens expire in ~60 min)
□ Is the app registration in the correct tenant?
□ Is admin consent granted for API permissions?
□ For service principal: is it added to the Fabric workspace?
□ For OneLake calls: are you using the storage scope instead of Fabric scope?
```

### View Your Token Claims (Debugging)

Paste your access token at **https://jwt.ms** to decode it and verify:
- `aud` (audience) = `https://api.fabric.microsoft.com`
- `scp` (scopes) = your granted permissions
- `tid` (tenant) = your tenant ID
- `exp` (expiry) = token expiration timestamp

---

## 10. POSTMAN COLLECTION JSON (IMPORT-READY)

Save the JSON below as `Fabric_REST_API.postman_collection.json` and import it into Postman via **File → Import**.

```json
{
  "info": {
    "name": "Microsoft Fabric REST APIs",
    "description": "Complete collection for Microsoft Fabric REST API operations",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "auth": {
    "type": "oauth2",
    "oauth2": [
      { "key": "tokenName",          "value": "Fabric Token" },
      { "key": "grant_type",         "value": "authorization_code" },
      { "key": "callBackUrl",        "value": "{{callback_url}}" },
      { "key": "authUrl",            "value": "{{auth_url}}" },
      { "key": "accessTokenUrl",     "value": "{{token_url}}" },
      { "key": "clientId",           "value": "{{client_id}}" },
      { "key": "clientSecret",       "value": "{{client_secret}}" },
      { "key": "scope",              "value": "{{scope}}" },
      { "key": "useBrowser",         "value": true },
      { "key": "client_authentication", "value": "header" },
      { "key": "addTokenTo",         "value": "header" }
    ]
  },
  "item": [
    {
      "name": "Workspaces",
      "item": [
        {
          "name": "List All Workspaces",
          "request": {
            "method": "GET",
            "url": { "raw": "{{base_url}}/workspaces", "host": ["{{base_url}}"], "path": ["workspaces"] },
            "auth": { "type": "noauth" }
          },
          "event": [
            {
              "listen": "test",
              "script": {
                "exec": [
                  "const res = pm.response.json();",
                  "if (res.value && res.value.length > 0) {",
                  "    pm.environment.set('workspace_id', res.value[0].id);",
                  "    console.log('Saved workspace_id:', res.value[0].id);",
                  "}"
                ]
              }
            }
          ]
        },
        {
          "name": "Get Workspace by ID",
          "request": {
            "method": "GET",
            "url": { "raw": "{{base_url}}/workspaces/{{workspace_id}}", "host": ["{{base_url}}"], "path": ["workspaces", "{{workspace_id}}"] }
          }
        },
        {
          "name": "Create Workspace",
          "request": {
            "method": "POST",
            "url": { "raw": "{{base_url}}/workspaces", "host": ["{{base_url}}"], "path": ["workspaces"] },
            "header": [{ "key": "Content-Type", "value": "application/json" }],
            "body": {
              "mode": "raw",
              "raw": "{\n  \"displayName\": \"New-Workspace\",\n  \"description\": \"Created via Postman\",\n  \"capacityId\": \"{{capacity_id}}\"\n}"
            }
          }
        },
        {
          "name": "Delete Workspace",
          "request": {
            "method": "DELETE",
            "url": { "raw": "{{base_url}}/workspaces/{{workspace_id}}", "host": ["{{base_url}}"], "path": ["workspaces", "{{workspace_id}}"] }
          }
        }
      ]
    },
    {
      "name": "Lakehouses",
      "item": [
        {
          "name": "List Lakehouses",
          "request": {
            "method": "GET",
            "url": { "raw": "{{base_url}}/workspaces/{{workspace_id}}/lakehouses", "host": ["{{base_url}}"], "path": ["workspaces", "{{workspace_id}}", "lakehouses"] }
          }
        },
        {
          "name": "Create Lakehouse",
          "request": {
            "method": "POST",
            "url": { "raw": "{{base_url}}/workspaces/{{workspace_id}}/lakehouses", "host": ["{{base_url}}"], "path": ["workspaces", "{{workspace_id}}", "lakehouses"] },
            "header": [{ "key": "Content-Type", "value": "application/json" }],
            "body": {
              "mode": "raw",
              "raw": "{\n  \"displayName\": \"my_lakehouse\",\n  \"description\": \"Created via Postman\"\n}"
            }
          }
        },
        {
          "name": "Get Lakehouse",
          "request": {
            "method": "GET",
            "url": { "raw": "{{base_url}}/workspaces/{{workspace_id}}/lakehouses/{{lakehouse_id}}", "host": ["{{base_url}}"], "path": ["workspaces", "{{workspace_id}}", "lakehouses", "{{lakehouse_id}}"] }
          }
        },
        {
          "name": "Delete Lakehouse",
          "request": {
            "method": "DELETE",
            "url": { "raw": "{{base_url}}/workspaces/{{workspace_id}}/lakehouses/{{lakehouse_id}}", "host": ["{{base_url}}"], "path": ["workspaces", "{{workspace_id}}", "lakehouses", "{{lakehouse_id}}"] }
          }
        }
      ]
    },
    {
      "name": "Items (Generic)",
      "item": [
        {
          "name": "List All Items",
          "request": {
            "method": "GET",
            "url": { "raw": "{{base_url}}/workspaces/{{workspace_id}}/items", "host": ["{{base_url}}"], "path": ["workspaces", "{{workspace_id}}", "items"] }
          }
        },
        {
          "name": "List Items by Type (Notebook)",
          "request": {
            "method": "GET",
            "url": { "raw": "{{base_url}}/workspaces/{{workspace_id}}/items?type=Notebook", "host": ["{{base_url}}"], "path": ["workspaces", "{{workspace_id}}", "items"], "query": [{ "key": "type", "value": "Notebook" }] }
          }
        },
        {
          "name": "Get Item by ID",
          "request": {
            "method": "GET",
            "url": { "raw": "{{base_url}}/workspaces/{{workspace_id}}/items/{{item_id}}", "host": ["{{base_url}}"], "path": ["workspaces", "{{workspace_id}}", "items", "{{item_id}}"] }
          }
        },
        {
          "name": "Delete Item",
          "request": {
            "method": "DELETE",
            "url": { "raw": "{{base_url}}/workspaces/{{workspace_id}}/items/{{item_id}}", "host": ["{{base_url}}"], "path": ["workspaces", "{{workspace_id}}", "items", "{{item_id}}"] }
          }
        }
      ]
    },
    {
      "name": "Notebooks",
      "item": [
        {
          "name": "List Notebooks",
          "request": {
            "method": "GET",
            "url": { "raw": "{{base_url}}/workspaces/{{workspace_id}}/notebooks", "host": ["{{base_url}}"], "path": ["workspaces", "{{workspace_id}}", "notebooks"] }
          }
        },
        {
          "name": "Create Notebook",
          "request": {
            "method": "POST",
            "url": { "raw": "{{base_url}}/workspaces/{{workspace_id}}/notebooks", "host": ["{{base_url}}"], "path": ["workspaces", "{{workspace_id}}", "notebooks"] },
            "header": [{ "key": "Content-Type", "value": "application/json" }],
            "body": {
              "mode": "raw",
              "raw": "{\n  \"displayName\": \"New_Notebook\",\n  \"description\": \"Created via Postman\"\n}"
            }
          }
        }
      ]
    },
    {
      "name": "Data Pipelines",
      "item": [
        {
          "name": "List Pipelines",
          "request": {
            "method": "GET",
            "url": { "raw": "{{base_url}}/workspaces/{{workspace_id}}/dataPipelines", "host": ["{{base_url}}"], "path": ["workspaces", "{{workspace_id}}", "dataPipelines"] }
          }
        },
        {
          "name": "Create Pipeline",
          "request": {
            "method": "POST",
            "url": { "raw": "{{base_url}}/workspaces/{{workspace_id}}/dataPipelines", "host": ["{{base_url}}"], "path": ["workspaces", "{{workspace_id}}", "dataPipelines"] },
            "header": [{ "key": "Content-Type", "value": "application/json" }],
            "body": {
              "mode": "raw",
              "raw": "{\n  \"displayName\": \"new_pipeline\",\n  \"description\": \"Created via Postman\"\n}"
            }
          }
        }
      ]
    },
    {
      "name": "Warehouses",
      "item": [
        {
          "name": "List Warehouses",
          "request": {
            "method": "GET",
            "url": { "raw": "{{base_url}}/workspaces/{{workspace_id}}/warehouses", "host": ["{{base_url}}"], "path": ["workspaces", "{{workspace_id}}", "warehouses"] }
          }
        },
        {
          "name": "Create Warehouse",
          "request": {
            "method": "POST",
            "url": { "raw": "{{base_url}}/workspaces/{{workspace_id}}/warehouses", "host": ["{{base_url}}"], "path": ["workspaces", "{{workspace_id}}", "warehouses"] },
            "header": [{ "key": "Content-Type", "value": "application/json" }],
            "body": {
              "mode": "raw",
              "raw": "{\n  \"displayName\": \"analytics_warehouse\",\n  \"description\": \"Created via Postman\"\n}"
            }
          }
        }
      ]
    },
    {
      "name": "Capacities",
      "item": [
        {
          "name": "List Capacities",
          "request": {
            "method": "GET",
            "url": { "raw": "{{base_url}}/capacities", "host": ["{{base_url}}"], "path": ["capacities"] }
          }
        }
      ]
    },
    {
      "name": "OneLake (ADLS Gen2)",
      "item": [
        {
          "name": "List Files in Lakehouse",
          "request": {
            "method": "GET",
            "url": {
              "raw": "https://onelake.dfs.fabric.microsoft.com/{{workspace_id}}/{{lakehouse_id}}/Files?resource=filesystem&recursive=false",
              "protocol": "https",
              "host": ["onelake", "dfs", "fabric", "microsoft", "com"],
              "path": ["{{workspace_id}}", "{{lakehouse_id}}", "Files"],
              "query": [
                { "key": "resource", "value": "filesystem" },
                { "key": "recursive", "value": "false" }
              ]
            },
            "header": [{ "key": "Authorization", "value": "Bearer {{access_token}}" }]
          }
        }
      ]
    },
    {
      "name": "Operations (LRO Polling)",
      "item": [
        {
          "name": "Get Operation Status",
          "request": {
            "method": "GET",
            "url": { "raw": "{{base_url}}/operations/{{operation_id}}", "host": ["{{base_url}}"], "path": ["operations", "{{operation_id}}"] }
          }
        }
      ]
    }
  ]
}
```

### How to Import

1. Save the JSON above as **`Fabric_REST_API.postman_collection.json`**
2. In Postman → **File** → **Import** → drag the file
3. Also create the environment variables from Section 4
4. Select the **Microsoft Fabric** environment
5. Click the collection → **Authorization** → **Get New Access Token**
6. Start making API calls! 🚀

---

## QUICK REFERENCE CARD

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     FABRIC REST API CHEAT SHEET                         │
├─────────────────────────────────────────────────────────────────────────┤
│  BASE URL:    https://api.fabric.microsoft.com/v1                      │
│  AUTH:        Bearer token (OAuth 2.0 via Microsoft Entra)             │
│  SCOPE:       https://api.fabric.microsoft.com/.default                │
│  ONELAKE:     https://onelake.dfs.fabric.microsoft.com                 │
│  ONELAKE SCOPE: https://storage.azure.com/.default                     │
├─────────────────────────────────────────────────────────────────────────┤
│  Workspaces:  GET/POST/PATCH/DELETE .../workspaces                     │
│  Lakehouses:  GET/POST/DELETE       .../workspaces/{id}/lakehouses     │
│  Notebooks:   GET/POST              .../workspaces/{id}/notebooks      │
│  Pipelines:   GET/POST              .../workspaces/{id}/dataPipelines  │
│  Warehouses:  GET/POST              .../workspaces/{id}/warehouses     │
│  Items:       GET/DELETE            .../workspaces/{id}/items          │
│  Capacities:  GET                   .../capacities                     │
│  Operations:  GET                   .../operations/{id}                │
├─────────────────────────────────────────────────────────────────────────┤
│  Token Lifetime:  ~60 minutes (refresh 5 min before expiry)            │
│  Rate Limits:     Check Retry-After header on 429 responses            │
│  LRO Pattern:     202 → poll Location header → 200 with result         │
│  Docs:            https://learn.microsoft.com/en-us/rest/api/fabric/   │
│  Swagger:         https://github.com/microsoft/fabric-rest-api-specs   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

*Guide prepared for Microsoft Fabric REST API exploration via Postman*
*References: [Microsoft Fabric REST API Docs](https://learn.microsoft.com/en-us/rest/api/fabric/) | [Fabric API Specs (GitHub)](https://github.com/microsoft/fabric-rest-api-specs)*
