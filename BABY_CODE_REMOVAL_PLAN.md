# Baby-Specific Code Removal Plan
**Crown Safe Migration - Phase 1: Cleanup**

## 🗑️ Agents to DELETE (Baby Product Specific)

### Critical Removal (Baby Safety Core)
- ❌ `agents/recall_data_agent/` - Queries CPSC/FDA baby recalls
- ❌ `agents/hazard_analysis_agent/` - Analyzes baby product hazards
- ❌ `agents/premium/pregnancy_product_safety_agent/` - Pregnancy safety checks
- ❌ `agents/premium/allergy_sensitivity_agent/` - Baby allergy checking
- ❌ `agents/governance/coppa_compliance_agent/` - Children's privacy (not needed for adult hair app)
- ❌ `agents/governance/childrenscode_compliance_agent/` - UK Children's Code

### Keep & Adapt (Reusable)
- ✅ `agents/command/commander_agent/` - Keep but adapt for hair products
- ✅ `agents/product_identifier_agent/` - Keep but adapt for hair products
- ✅ `agents/visual/visual_search_agent/` - Keep for visual product matching
- ✅ `agents/routing/router_agent/` - Keep (generic routing logic)
- ✅ `agents/chat/chat_agent/` - Keep (generic chat)
- ✅ `agents/value_add/alternatives_agent/` - Keep but adapt (find alternative hair products)
- ✅ `agents/reporting/report_builder_agent/` - Keep (generic reporting)
- ✅ `agents/business/monetization_agent/` - Keep (revenue tracking)
- ✅ `agents/business/metrics_agent/` - Keep (analytics)
- ✅ `agents/engagement/push_notification_agent/` - Keep (generic notifications)
- ✅ `agents/engagement/onboarding_agent/` - Keep but adapt for hair onboarding
- ✅ `agents/governance/legalcontent_agent/` - Keep (generic legal)
- ✅ `agents/governance/datagovernance_agent/` - Keep (GDPR compliance needed)

## 🔧 Files to MODIFY (Replace Baby Logic with Hair Logic)

### Core Infrastructure
1. **`core_infra/database.py`**
   - Remove: `RecallDB`, `FamilyMember`, `Allergies` models
   - Add: Import Crown Safe models from `crown_safe_models.py`
   - Keep: `User`, `Session`, auth models

2. **`api/main_babyshield.py`** → Rename to `api/main_crownsafe.py`
   - Update app title: "BabyShield API" → "Crown Safe API"
   - Replace safety check logic
   - Update all endpoints

3. **`agents/command/commander_agent/agent_logic.py`**
   - Replace: Baby recall checking → Hair ingredient analysis
   - Replace: Hazard analysis → Crown Score calculation
   - Keep: Routing logic structure

## 📋 Step-by-Step Execution

### Step 1: Delete Baby-Specific Agents
```powershell
# Delete these directories completely
Remove-Item -Recurse -Force "agents/recall_data_agent"
Remove-Item -Recurse -Force "agents/hazard_analysis_agent"
Remove-Item -Recurse -Force "agents/premium/pregnancy_product_safety_agent"
Remove-Item -Recurse -Force "agents/premium/allergy_sensitivity_agent"
Remove-Item -Recurse -Force "agents/governance/coppa_compliance_agent"
Remove-Item -Recurse -Force "agents/governance/childrenscode_compliance_agent"
```

### Step 2: Rename Core Files
```powershell
# Rename main API file
Rename-Item "api/main_babyshield.py" "api/main_crownsafe.py"
```

### Step 3: Update Database Models
- Integrate Crown Safe models
- Create migration script

## 📊 Impact Analysis

### Files Affected: ~150 files
### Lines of Code to Remove: ~8,000
### Lines of Code to Modify: ~12,000
### New Code to Write: ~5,000

## ✅ Verification Checklist
- [ ] All baby-specific agents deleted
- [ ] Database models replaced
- [ ] Main API file renamed and updated
- [ ] Commander agent adapted for hair products
- [ ] Product identifier adapted for hair products
- [ ] All imports updated
- [ ] No references to recalls, CPSC, FDA baby products
- [ ] Tests updated or removed

---
**Status**: Planning Complete - Ready for Execution
