# Crown Score Algorithm v1.0
## Enterprise-Grade Hair Product Safety & Compatibility Scoring

**Last Updated**: October 24, 2025  
**Version**: 1.0.0  
**Status**: Production-Ready

---

## 🎯 Executive Summary

The **Crown Score** is a scientifically-backed 0-100 rating system that evaluates hair products specifically for **Black hair types (3C-4C)**, considering:

- **Hair porosity** (Low, Medium, High)
- **Curl pattern** (3C, 4A, 4B, 4C, Mixed)
- **Current hair state** (Natural, Relaxed, Transitioning, Heat-damaged, Color-treated)
- **Hair goals** (Growth, Moisture retention, Edge recovery, Definition, Thickness)
- **Ingredient safety** (FDA compliance, endocrine disruptors, carcinogens)
- **Ingredient interactions** (protein overload, buildup potential, pH balance)

---

## 📊 Scoring Framework

### **Base Score: 100 Points**

Every product starts at 100 and points are **deducted** or **added** based on ingredient analysis.

---

## 🔬 Category 1: Harmful Ingredients (CRITICAL DEDUCTIONS)

### **Tier 1: Severe Health Hazards (-40 to -50 points each)**

| Ingredient                       | Deduction | Reason                                      | Source                                                                                          |
| -------------------------------- | --------- | ------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| **Formaldehyde** (and releasers) | -50       | Carcinogenic, respiratory damage            | [EPA](https://www.epa.gov/formaldehyde), [NTP](https://ntp.niehs.nih.gov/)                      |
| **Parabens** (Butyl, Propyl)     | -40       | Endocrine disruptors, hormone mimics        | [FDA CIR](https://www.fda.gov/cosmetics/cosmetic-ingredients/parabens-cosmetics)                |
| **Coal Tar Dyes** (FD&C, D&C)    | -45       | Carcinogenic, scalp irritation              | [IARC](https://monographs.iarc.who.int/)                                                        |
| **Phthalates** (DBP, DEP)        | -40       | Endocrine disruptors, reproductive toxicity | [CDC](https://www.cdc.gov/biomonitoring/Phthalates_FactSheet.html)                              |
| **Lead Acetate**                 | -50       | Neurotoxic, banned in EU                    | [EU Cosmetics Regulation](https://ec.europa.eu/health/scientific_committees/consumer_safety_en) |

### **Tier 2: Scalp & Hair Damage (-20 to -35 points each)**

| Ingredient                                                  | Deduction | Reason                                 | Hair Types Affected          |
| ----------------------------------------------------------- | --------- | -------------------------------------- | ---------------------------- |
| **Drying Alcohols** (Isopropyl, SD Alcohol 40, Ethanol)     | -30       | Severe moisture stripping, breakage    | 4B, 4C (High porosity worst) |
| **Sulfates** (SLS, SLES, ALS)                               | -25       | Strip natural oils, cause dryness      | 4A, 4B, 4C (All types)       |
| **Heavy Silicones** (Dimethicone without clarifying agents) | -20       | Buildup, prevents moisture penetration | High porosity hair           |
| **Mineral Oil** (Petrolatum in leave-ins)                   | -15       | Seals out moisture, not penetrating    | Low porosity hair            |
| **Synthetic Fragrance** (Parfum)                            | -10       | Scalp irritation, allergic reactions   | Sensitive scalps             |

---

## 💚 Category 2: Beneficial Ingredients (BONUSES)

### **Tier 1: Superstar Moisturizers (+15 to +20 points each)**

| Ingredient                             | Bonus | Reason                                          | Best For                                        |
| -------------------------------------- | ----- | ----------------------------------------------- | ----------------------------------------------- |
| **Shea Butter** (Butyrospermum parkii) | +20   | Deep moisture, scalp healing, anti-inflammatory | 4B, 4C, High porosity                           |
| **Coconut Oil** (Cocos nucifera)       | +18   | Penetrates hair shaft, reduces protein loss     | Low/Medium porosity (⚠️ protein-sensitive avoid) |
| **Avocado Oil**                        | +15   | Rich in vitamins, penetrates cortex             | All types                                       |
| **Argan Oil**                          | +15   | Antioxidants, shine, smoothness                 | 3C, 4A                                          |

### **Tier 2: Humectants & Conditioning (+10 to +15 points each)**

| Ingredient          | Bonus | Reason                                      | Best For                      |
| ------------------- | ----- | ------------------------------------------- | ----------------------------- |
| **Glycerin**        | +15   | Attracts moisture from air (humid climates) | High porosity, humid climates |
| **Aloe Vera**       | +12   | Hydrating, pH balancing, scalp soothing     | All types                     |
| **Honey**           | +10   | Humectant, antimicrobial                    | All types                     |
| **Hyaluronic Acid** | +12   | Extreme hydration retention                 | Dry, damaged hair             |

### **Tier 3: Proteins (CONDITIONAL +10 to -15)**

| Ingredient             | Effect | Rule                                                       |
| ---------------------- | ------ | ---------------------------------------------------------- |
| **Hydrolyzed Keratin** | +10    | **IF** hair is heat-damaged OR relaxed                     |
| **Wheat Protein**      | +8     | **IF** hair needs strength AND low protein use history     |
| **Silk Protein**       | -15    | **IF** user has protein-sensitive flag OR high protein use |

⚠️ **Protein Overload Detection**: If product has >2 protein ingredients AND user has "protein-sensitive" flag → Deduct **-20 points** with warning.

---

## 🧬 Category 3: Hair Type Compatibility Matrix

### **Porosity-Based Scoring**

| Ingredient Type                    | Low Porosity              | Medium Porosity | High Porosity           |
| ---------------------------------- | ------------------------- | --------------- | ----------------------- |
| **Heavy Butters** (Shea, Mango)    | -5 (buildup)              | +10             | +20 (seals moisture)    |
| **Light Oils** (Jojoba, Grapeseed) | +15                       | +10             | +5                      |
| **Humectants** (Glycerin)          | -5 (sits on surface)      | +10             | +15 (draws in moisture) |
| **Heat** (for product absorption)  | Required (+10 if co-wash) | Neutral         | Not needed              |

### **Curl Pattern Optimization**

| Ingredient              | 3C  | 4A  | 4B  | 4C  |
| ----------------------- | --- | --- | --- | --- |
| **Heavy Creams**        | +5  | +10 | +15 | +20 |
| **Lightweight Lotions** | +15 | +10 | +5  | 0   |
| **Gels (strong hold)**  | +10 | +15 | +12 | +8  |

---

## 🎯 Category 4: Goal-Based Adjustments

| User Goal              | Ingredients to Boost                                 | Ingredients to Penalize                           |
| ---------------------- | ---------------------------------------------------- | ------------------------------------------------- |
| **Growth**             | Biotin (+8), Castor Oil (+10), Peppermint (+5)       | Drying alcohols (-10 extra)                       |
| **Edge Recovery**      | Castor Oil (+15), Vitamin E (+8)                     | Tight hold gels (-10), Heavy waxes (-8)           |
| **Moisture Retention** | Shea Butter (+10 extra), Glycerin (+5 extra)         | Sulfates (-15 extra), Drying alcohols (-10 extra) |
| **Definition**         | Flaxseed gel (+12), Aloe vera (+8)                   | Heavy oils (-5), Petrolatum (-10)                 |
| **Thickness**          | Biotin (+10), Keratin (+12 if not protein-sensitive) | Silicones (-5 extra for buildup)                  |

---

## ⚖️ Category 5: pH Balance & Product Type

### **pH Scoring**
- **Ideal pH for hair: 4.5 - 5.5** (matches hair's natural acidity)

| pH Range               | Score Adjustment |
| ---------------------- | ---------------- |
| 4.5 - 5.5              | +10 (Perfect!)   |
| 4.0 - 4.4 OR 5.6 - 6.0 | 0 (Acceptable)   |
| 3.5 - 3.9 OR 6.1 - 7.0 | -5 (Caution)     |
| <3.5 OR >7.0           | -15 (Damaging)   |

### **Product Type Adjustments**

| Product Type         | Expected Characteristics                                               |
| -------------------- | ---------------------------------------------------------------------- |
| **Shampoo**          | Sulfates acceptable IF clarifying (not daily use) → -10 instead of -25 |
| **Conditioner**      | MUST have emollients (oils/butters) → +15 if present                   |
| **Leave-In**         | NO drying alcohols allowed → -40 instead of -30 if found               |
| **Deep Conditioner** | Expects heavy moisturizers → +20 for shea/mango butter                 |
| **Gel/Styler**       | Some hold alcohols OK → -15 instead of -30                             |

---

## 🚨 Category 6: Interaction Warnings (Auto-Alerts)

### **Dangerous Combinations**
1. **Protein Overload**: >2 protein ingredients → -20 points + "⚠️ Protein Overload Risk" alert
2. **Silicone Buildup**: Heavy silicones WITHOUT clarifying shampoo → -15 points + "🧴 Requires Clarifying Shampoo"
3. **Alcohol + Sulfate Combo**: Both present → -40 points (compounded drying)
4. **Fragrance + Sensitive Scalp**: User has sensitivity flag → -15 extra points

---

## 📐 Final Score Calculation

### **Formula**:
```
Crown Score = 100
  - Σ(Harmful Ingredients)
  + Σ(Beneficial Ingredients)
  + Porosity Adjustments
  + Curl Pattern Adjustments
  + Goal-Based Bonuses
  + pH Balance Score
  + Product Type Modifiers
  - Interaction Penalties
```

### **Score Ranges & Meanings**:

| Score  | Verdict              | Color    | Icon | Meaning                      |
| ------ | -------------------- | -------- | ---- | ---------------------------- |
| 90-100 | **CROWN APPROVED**   | 🟢 Green  | 👑    | Excellent for your hair type |
| 75-89  | **GOOD CHOICE**      | 🟡 Yellow | ✓    | Safe, minor concerns         |
| 50-74  | **USE WITH CAUTION** | 🟠 Orange | ⚠️    | Some problematic ingredients |
| 25-49  | **NOT RECOMMENDED**  | 🔴 Red    | ⛔    | Multiple red flags           |
| 0-24   | **AVOID**            | 🔴 Red    | 🚫    | Dangerous for your hair      |

---

## 🧪 Example Calculations

### **Example 1: "Moisture Max Leave-In Conditioner"**

**Ingredients**: Water, Shea Butter, Glycerin, Aloe Vera, Coconut Oil, Fragrance

**User Profile**: 4C, High Porosity, Growth Goal, Not protein-sensitive

**Calculation**:
```
Base Score:                    100
+ Shea Butter (superstar):     +20 (4C high porosity)
+ Glycerin (humectant):        +15 (high porosity)
+ Aloe Vera:                   +12
+ Coconut Oil:                 +18
- Fragrance:                   -10
+ Growth goal bonus:           +5 (Shea supports growth)
+ Leave-in product (no alcohols): +10
────────────────────────────────
CROWN SCORE:                   170 → Capped at 100
VERDICT: CROWN APPROVED 👑
```

### **Example 2: "Salon Pro Clarifying Shampoo"**

**Ingredients**: Water, Sodium Laureth Sulfate (SLES), Cocamidopropyl Betaine, Citric Acid, Fragrance, SD Alcohol 40

**User Profile**: 4B, Medium Porosity, Moisture Retention Goal

**Calculation**:
```
Base Score:                    100
- SLES (sulfate):              -25
- SD Alcohol 40:               -30
- Fragrance:                   -10
+ pH 4.5 (citric acid):        +10
+ Product Type: Clarifying:    +15 (sulfates expected here)
+ Co-surfactant present:       +5
- Moisture goal conflict:      -10 (sulfates bad for moisture)
- Alcohol + Sulfate combo:     -20
────────────────────────────────
CROWN SCORE:                   35
VERDICT: NOT RECOMMENDED ⛔
WARNING: "Use only 1x/month for buildup removal, not for daily use"
```

---

## 🔬 Scientific References

1. **Trichology & Hair Science**:
   - "The Science of Black Hair" - Audrey Davis-Sivasothy
   - Journal of Cosmetic Dermatology: "Porosity and Moisture Retention" (2023)

2. **Ingredient Safety**:
   - FDA Cosmetic Ingredient Database
   - EWG Skin Deep Database
   - European Commission SCCS Opinions

3. **Black Hair Research**:
   - "Textured Hair Science" - Dr. Ali Syed
   - Journal of Investigative Dermatology: "Structural Differences in African Hair" (2022)

---

## 🚀 Implementation Notes

### **Database Requirements**:
- **Ingredients Table**: 200+ ingredients with safety ratings
- **Interaction Rules Table**: Protein overload, silicone buildup rules
- **Hair Type Compatibility Matrix**: Porosity × Curl Pattern scores

### **Performance**:
- Pre-calculated ingredient scores for speed
- Cached Crown Scores for popular products
- Real-time calculation for new product scans (<500ms)

### **Updates**:
- Monthly ingredient database updates
- Quarterly algorithm refinement based on user feedback
- Annual peer review by licensed trichologists

---

**Version History**:
- v1.0.0 (Oct 2025): Initial enterprise-grade algorithm
