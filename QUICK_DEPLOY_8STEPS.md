# ⚡ QUICK DEPLOYMENT REFERENCE - 8 STEPS, 30-40 MINUTES

## 🎯 GOAL
Manually create workspace, lakehouse, and deploy notebooks in Fabric UI

---

## STEP-BY-STEP

### **STEP 1: Workspace**
```
https://app.fabric.microsoft.com
→ Create → Workspace
  Name: Fabric_Product_Analytics26
  Capacity: f64anuj
  → Save
⏱️ 2-3 minutes
```

### **STEP 2: Lakehouse**
```
New → Lakehouse
  Name: Fabric_Product_LKH
  → Create
⏱️ 2-3 minutes
```

### **STEP 3: Spark Environment**
```
New → Spark Environment
  Name: Fabric_HighPerf_Env
  Driver memory: 14GB
  Executor memory: 28GB
  Executor cores: 8
  → Save
⏱️ 2-3 minutes
```

### **STEP 4: Notebook 1**
```
New → Notebook
  Name: 1_ADO_WorkItems_Extraction
  → Paste content from: C:\Users\anujpandey\1_ADO_WorkItems_Extraction.py
  → Run all
  ✅ Look for: "✅ BRONZE TABLE CREATION COMPLETE"
⏱️ 5-10 minutes
✓ Creates: WorkItems_Bronze table
```

### **STEP 5: Notebook 2**
```
New → Notebook
  Name: 2_WorkItems_Silver_Transform
  → Paste content from: C:\Users\anujpandey\2_WorkItems_Silver_Transform.py
  → Run all
  ✅ Look for: "✅ SILVER TABLE TRANSFORMATION COMPLETE"
⏱️ 3-5 minutes
✓ Creates: Cleaned_Items_Silver table
```

### **STEP 6: Semantic Model**
```
New → Semantic Model
  Name: ADO_Workitems_Model
  Select table: Cleaned_Items_Silver
  
→ Add 6 DAX Measures (copy-paste):
  1. Count Active Bugs
  2. Total Bugs
  3. % Active Bugs
  4. Count Customer Promise Features
  5. Total Features
  6. % Customer Promise
  
  (See DEPLOYMENT_PHASE2_COMPLETE.md for formulas)
  → Save → Publish
⏱️ 3-5 minutes
```

### **STEP 7: Report 1**
```
New → Report
  Name: Active_Bugs_Report
  Data source: ADO_Workitems_Model
  
→ Create 6 visualizations:
  1. Card: Count Active Bugs
  2. Card: Total Bugs
  3. KPI: % Active Bugs
  4. Matrix: State × AssignedTo
  5. Bar Chart: Top 10 Assignees
  6. Slicer: AreaPath
  
  → Save
⏱️ 5 minutes
```

### **STEP 8: Report 2**
```
New → Report
  Name: Customer_Promise_Features_Report
  Data source: ADO_Workitems_Model
  
→ Create 6 visualizations:
  1. Card: Count Customer Promise Features
  2. Card: Total Features
  3. KPI: % Customer Promise
  4. Matrix: CustomerAccount × State
  5. Column Chart: CreatedDate Trend
  6. Slicer: AreaPath
  
  → Save
⏱️ 5 minutes
```

---

## ✅ VERIFY

After all 8 steps:

```
Workspace: Fabric_Product_Analytics26 ✓
├── Lakehouse: Fabric_Product_LKH ✓
│   ├── WorkItems_Bronze (13 cols, ~20K rows)
│   └── Cleaned_Items_Silver (13 cols, fewer rows)
├── Spark Environment: Fabric_HighPerf_Env ✓
├── Notebooks: 2 ✓
├── Semantic Model: ADO_Workitems_Model (6 measures) ✓
└── Reports: 2 ✓
    ├── Active_Bugs_Report (6 visuals)
    └── Customer_Promise_Features_Report (6 visuals)
```

---

## 📁 RESOURCES

- Notebook 1 code: `C:\Users\anujpandey\1_ADO_WorkItems_Extraction.py`
- Notebook 2 code: `C:\Users\anujpandey\2_WorkItems_Silver_Transform.py`
- DAX formulas: `DEPLOYMENT_PHASE2_COMPLETE.md`
- Full guide: `DEPLOY_NOW.md`

---

## ⏱️ TOTAL TIME: ~30-40 minutes

✅ You've got this! 🚀
