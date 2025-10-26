# Crown Safe - Agent Cleanup Plan

## Overview
Remove baby/recall-specific agents that are not needed for Crown Safe (hair product safety).

---

## ❌ Agents to REMOVE (Baby/Recall-Specific)

### 1. **Recall Data Agent**
- `agents/recall_data_agent/` - Queries baby product recall databases

### 2. **Baby-Specific Premium Features**
- `agents/premium/pregnancy_product_safety_agent/` - Pregnancy safety (not relevant to hair)
- `agents/premium/allergy_sensitivity_agent/` - Baby food allergies (different from hair sensitivities)

### 3. **Baby Product Features**
- `agents/value_add/alternatives_agent/` - Suggests baby product alternatives
- `agents/engagement/community_alert_agent/` - Community baby safety alerts

### 4. **Business/Governance**
- `agents/business/` - Baby business logic
- `agents/governance/` - Recall governance
- `agents/processing/` - Recall processing  
- `agents/reporting/` - Baby safety reports
- `agents/research/` - Baby research

---

## ✅ Agents to KEEP (Crown Safe-Relevant)

### 1. **Core Workflow & Orchestration**
- `agents/command/commander_agent/` - ✅ Orchestrates Crown Safe workflow
  - **Status**: Already renamed to `CrownSafeCommanderLogic`
  - **Purpose**: Main entry point for safety checks
- `agents/planning/planner_agent/` - ✅ Plans analysis strategy
  - **Purpose**: Plans which checks to run for hair products
- `agents/routing/router_agent/` - ✅ Routes to appropriate analysis agents
  - **Purpose**: Routes to ingredient/hazard/visual agents

### 2. **Product Recognition**
- `agents/visual/visual_search_agent/` - ✅ Visual recognition for product labels
  - **Purpose**: Scan hair product labels/bottles with camera
- `agents/product_identifier_agent/` - ✅ Identifies products by barcode/name
  - **Purpose**: Barcode scanning for hair products

### 3. **Ingredient Analysis**
- `agents/ingredient_analysis_agent/` - ✅ Analyzes hair product ingredients
  - **Purpose**: Crown Score calculation for ingredients
- `agents/hazard_analysis_agent/` - ✅ Identifies harmful chemicals
  - **Purpose**: Detects sulfates, parabens, harmful chemicals for 3C-4C hair

### 4. **Chat/Consultation**
- `agents/chat/` - ✅ AI chat for hair consultations
  - **Purpose**: Answer hair care questions, recommend products

---

## 📝 Code Changes Required

### 1. **Remove Imports in `api/main_babyshield.py`**

**Lines 2391-2416:** Remove pregnancy safety agent
```python
# REMOVE THIS BLOCK:
from agents.premium.pregnancy_product_safety_agent.agent_logic import (
    PregnancyProductSafetyAgentLogic,
)
pregnancy_agent = PregnancyProductSafetyAgentLogic(...)
# ... entire pregnancy check block
```

**Lines 2422-2444:** Remove allergy agent
```python
# REMOVE THIS BLOCK:
from agents.premium.allergy_sensitivity_agent.agent_logic import (
    AllergySensitivityAgentLogic,
)
allergy_agent = AllergySensitivityAgentLogic(...)
# ... entire allergy check block
```

**Lines 2460+:** Remove alternatives agent
```python
# REMOVE THIS BLOCK:
from agents.value_add.alternatives_agent.agent_logic import (
    AlternativesAgentLogic,
)
alternatives_agent = AlternativesAgentLogic(...)
# ... entire alternatives block
```

### 2. **Update Commander Agent References**

**In `agents/command/commander_agent/agent_logic.py`:**
- Remove imports to: `BabyShieldPlannerLogic`, `BabyShieldRouterLogic`
- These stub classes reference recall databases

---

## 🔧 Execution Steps

### Step 1: Backup
```powershell
git add -A
git commit -m "Backup before agent cleanup"
```

### Step 2: Run Removal Script
```powershell
.\remove_baby_agents.ps1
```

### Step 3: Update Main File
Manually comment out the 3 agent import blocks in `api/main_babyshield.py`:
- Lines 2391-2416 (pregnancy)
- Lines 2422-2444 (allergy)  
- Lines 2460+ (alternatives)

### Step 4: Test
```powershell
python test_endpoints.py
python test_chat_agent.py
```

### Step 5: Verify
```powershell
# Should show only Crown Safe agents
Get-ChildItem agents -Directory -Recurse -Depth 2 | Select-Object FullName
```

---

## 📊 Expected Results

**Before Cleanup:**
- 12+ agent directories (baby-focused)
- Imports to recall/pregnancy/allergy agents
- Mixed baby + hair logic

**After Cleanup:**
- 8 agent directories (hair-focused)
- Clean Crown Safe imports
- Pure hair product safety focus

**Directory Size Reduction:**
- Estimated: ~400-600 files removed
- Estimated: ~40,000+ lines of code removed
- Focus: Hair product safety only

---

## ⚠️ Important Notes

1. **Don't delete chat agent** - Used for hair consultations
2. **Keep visual agent** - Used for label scanning
3. **Keep commander agent** - Already renamed to CrownSafeCommanderLogic
4. **Update tests** - Remove tests for deleted agents

---

## ✅ Success Criteria

- [ ] All baby/recall agents removed
- [ ] Crown Safe agents remain functional
- [ ] No import errors in main app
- [ ] Chat agent still works
- [ ] Visual scanning still works
- [ ] Server starts without errors
- [ ] All endpoints still operational (324 routes)

---

**Next:** Run `.\remove_baby_agents.ps1` to execute cleanup
