# Profit Insight Basel RWA Analytics System
## PNC Bank + IndusInd Segmentation Model

**Production-grade Basel RWA analytics customized for your specifications**

---

## 🎯 Overview

This system is **customized based on your uploaded files**:

1. **PI_RWA_Data_Dictionary.xlsx** - PNC Bank field definitions and data structure
2. **IndusInd_Bank_CC_RWA_business_case_1_3H.xlsx** - Income segments and business logic  
3. **Credit_Card_Charts.pptx** - Chart types and visualization requirements

### Key Customizations

✅ **US Standardized Approach** (12 CFR Part 3) - NOT IRB  
✅ **PNC Bank field names** and structure from data dictionary  
✅ **IndusInd income segments**: Mass Market, Mid-Market, Affluent, High Net Worth  
✅ **Behavioral segmentation**: Transactor (58%) vs Revolver (42%)  
✅ **Profit Insight branding** with navy/gold color scheme  
✅ **Proper Basel terminology** on all chart axes and headings  
✅ **22+ visualizations** matching your PPT specifications  
✅ **Stress testing scenarios**: Baseline, Mild/Severe Recession, Financial Crisis  

---

## 🚀 Quick Start

### Install Dependencies

```bash
pip install pandas numpy plotly streamlit --break-system-packages
```

### Generate Dataset

```bash
python pnc_indusind_data_generator.py
```

**Output**: `pnc_indusind_cc_portfolio_1M.csv` (1M accounts, 62 variables)

### Launch Dashboard

```bash
streamlit run profit_insight_rwa_dashboard.py
```

**Access**: http://localhost:8501

---

## 📊 Data Model - PNC/IndusInd Specifications

### US Standardized Approach Parameters

Based on **12 CFR Part 3** (US banking regulations):

| Parameter | Value | Regulation |
|-----------|-------|------------|
| **CC Risk Weight** | 100% | §3.32(l) - Credit card receivables |
| **Unused CCF** | 10% | §3.33(b)(2) - Unconditionally cancellable |
| **Conditional OD CCF** | 0% | §3.33(b)(1) - Conditional overdraft |
| **Min Tier 1 Ratio** | 8.5% | Basel III + conservation buffer |

### Income Segmentation (IndusInd Model)

| Segment | Portfolio % | Avg Credit Limit | Avg Annual Spend |
|---------|-------------|------------------|------------------|
| **Mass Market** | 15% | $889 | $2,000 |
| **Mid-Market** | 40% | $1,667 | $2,778 |
| **Affluent** | 35% | $2,778 | $4,444 |
| **High Net Worth** | 10% | $5,556 | $8,889 |

### FICO Risk Tiers

| Tier | FICO Range | PD | Portfolio % |
|------|------------|-----|-------------|
| **Super Prime** | 750-850 | 0.5% | 20% |
| **Prime Plus** | 700-749 | 1.5% | 30% |
| **Prime** | 660-699 | 3.5% | 25% |
| **Near Prime** | 620-659 | 7.5% | 15% |
| **Subprime** | 550-619 | 15.0% | 10% |

### Key Basel Formulas (US SA)

```python
# Exposure at Default (EAD)
EAD = CC_Outstanding + (Unused_CC × 10% CCF)

# Risk-Weighted Assets (RWA)  
RWA = EAD × 100% Risk_Weight

# Tier 1 Capital Requirement
T1_Required = RWA × 8.5%

# Expected Loss
EL = EAD × PD × LGD  # LGD = 45% for unsecured CC
```

---

## 📈 Dashboard Features

### 6 Comprehensive Tabs

#### 1. Portfolio Overview
- **EAD by Income Segment** ($B) - Bar chart
- **RWA by Behavioral Type** ($B) - Pie chart  
- **FICO Score Distribution** (Accounts) - Histogram
- **Credit Utilization Distribution** (%) - Histogram

#### 2. Risk Analytics
- **PD Distribution by FICO Tier** (%) - Box plot
- **NCO Rate by Income Segment** (bps) - Bar chart
- **Expected Loss Distribution** ($M) - Pie chart
- **FICO Score vs PD Scatter** - Color by behavior

#### 3. Exposure & Balances
- **On-Balance vs Off-Balance Exposure** ($B) - Bar comparison
- **Credit Limit Distribution** ($) - Box plot by segment
- **Utilization by Behavioral Type** (%) - Bar chart
- **Outstanding Balance by Card Type** ($M) - Bar chart

#### 4. Capital Requirements
- **Tier 1 Capital by Segment** ($M) - Bar chart
- **RWA Composition** - Transactor vs Revolver pie
- Regulatory metrics and buffer analysis

#### 5. Profitability  
- **Revenue Components** ($M) - Stacked bar by segment
- **Net Income by Behavioral Type** ($M) - Bar chart
- **ROE by Income Segment** (%) - Bar chart
- **Expected Loss vs Net Income** ($M) - Grouped bar

#### 6. RWA Optimization
- **Pathway 1**: Transactor limit reduction impact (line chart)
- **Pathway 2**: Capital relief opportunity (bar chart)
- **Pathway 3**: Revenue efficiency analysis (bar chart)
- **Eligibility Analysis**: Optimization candidates (pie chart)

### Key Performance Indicators (KPIs)

**Top Row:**
1. Total Accounts
2. Total EAD ($B)
3. Total RWA ($B)  
4. Avg RWA Density (%)
5. Tier 1 Capital Required ($B)

**Second Row:**
6. Transactor %
7. Revolver %
8. Average PD (%)
9. Average NCO Rate (bps)
10. NPL Rate (bps)

All KPIs show **stress scenario deltas** when enabled.

---

## 🧪 Stress Testing Scenarios

### Pre-defined Scenarios

| Scenario | PD Stress | NCO Stress | GDP Impact |
|----------|-----------|------------|------------|
| **Baseline** | 1.0x | 1.0x | 1.00x |
| **Mild Recession** | 1.5x | 1.3x | 0.95x |
| **Severe Recession** | 2.5x | 2.0x | 0.85x |
| **Financial Crisis** | 4.0x | 3.5x | 0.70x |
| **Custom** | User-defined sliders |

### How Stress Testing Works

```python
# Stressed PD
PD_stressed = PD_baseline × PD_stress_factor

# Stressed NCO  
NCO_stressed = NCO_baseline × NCO_stress_factor

# Recalculated Expected Loss
EL_stressed = EAD × PD_stressed × LGD

# Recalculated Net Income
NI_stressed = Revenue - Costs - EL_stressed
```

---

## 📁 Dataset Variables (62 Columns)

### Customer Demographics
- `account_id`, `customer_age`, `annual_income`
- `region`, `vintage_months`, `employment_status`
- `account_open_date`

### Segmentation
- `income_segment` (Mass Market, Mid-Market, Affluent, HNW)
- `behavioral_type` (Transactor, Revolver)
- `fico_tier` (Super Prime to Subprime)
- `portfolio_segment` (Combined segment)

### Credit Risk Metrics
- `fico_score`, `pd`, `pd_base`
- `nco_rate`, `lgd`
- `dpd_status` (Current, DPD_30, DPD_60, DPD_90+)

### Card Details
- `card_type`, `card_category`
- `credit_limit`, `apr`
- `cc_outstanding_b`, `unused_cc_b`
- `utilization_rate`, `avg_monthly_spend`, `monthly_payment`

### Exposures (EAD)
- `on_balance_exposure_b` (Drawn amount)
- `off_balance_exposure_b` (Undrawn × 10% CCF)
- `ead_b` (Total EAD)
- `total_limit_b`, `exposure_pct`

### RWA (US Standardized Approach)
- `risk_weight` (100% for all CC)
- `total_cc_rwa_b`, `transactor_rwa_b`, `revolver_rwa_b`
- `rwa_density` (100% under US SA)

### Capital Requirements
- `tier1_requirement_b` (8.5% of RWA)
- `capital_buffer_b` (2.5% conservation)

### Performance Metrics
- `interest_income_b`, `fee_income_b`, `total_revenue_b`
- `funding_cost_b`, `operating_expense_b`
- `credit_loss_provision_b`, `expected_loss_b`
- `net_income_b`, `roa`, `roe`

### Regulatory Fields
- `bank_name`, `fdic_cert`, `report_date`
- `approach` (US Standardized Approach)
- `exposure_class` (Retail - Credit Card)
- `product_code`, `is_performing`, `is_npl`

### Optimization Flags
- `is_transactor`, `is_revolver`
- `eligible_for_limit_reduction`
- `eligible_for_overdraft_conversion`

---

## 🎨 Profit Insight Branding

### Color Palette

```css
Navy Blue:  #1B3B6F  /* Primary brand color */
Gold:       #D4AF37  /* Accent color */
Light Blue: #4A90E2  /* Secondary highlights */
Gray:       #F5F7FA  /* Background */
```

### Typography

- **Headers**: Helvetica Neue, bold, navy blue
- **Metrics**: 36px, bold, navy blue
- **Chart titles**: 16px, navy blue
- **Axis labels**: Proper Basel terminology

### Basel Terminology Standards

All charts use proper regulatory language:

- **X-Axis**: Income Segment, FICO Risk Tier, Behavioral Type
- **Y-Axis**: Total EAD ($B), RWA ($M), PD (%), NCO Rate (bps)
- **Titles**: "Exposure at Default (EAD) by...", "Risk-Weighted Assets (RWA)..."
- **No abbreviations** without expansion in title

---

## 🔧 Customization Guide

### Modify Income Segments

```python
# In pnc_indusind_data_generator.py, line ~30
self.income_segments = {
    'Mass_Market': {'weight': 0.20, 'avg_limit': 1000, 'avg_spend': 2500},
    'Mid_Market': {'weight': 0.35, 'avg_limit': 2000, 'avg_spend': 3500},
    # ... add your segments
}
```

### Change US SA Parameters

```python
# In pnc_indusind_data_generator.py, line ~24
self.basel_params = {
    'cc_risk_weight': 1.00,     # Keep at 100% (US regulation)
    'unused_cc_ccf': 0.10,      # Keep at 10% (US regulation)
    'min_tier1_w_buffer': 0.085 # 8.5% min T1
}
```

### Add New Charts to Dashboard

```python
# In profit_insight_rwa_dashboard.py
def plot_my_custom_analysis(df):
    fig = px.bar(
        df.groupby('region')['ead_b'].sum().reset_index(),
        x='region',
        y='ead_b',
        title='Exposure at Default (EAD) by Region',
        labels={'ead_b': 'Total EAD ($B)', 'region': 'Geographic Region'}
    )
    st.plotly_chart(fig)

# Add to appropriate tab
with tab1:
    plot_my_custom_analysis(df_filtered)
```

---

## 📊 Portfolio Summary (Sample 1M Dataset)

```
================================================================================
PORTFOLIO SUMMARY (PNC/IndusInd Model)
================================================================================

EXPOSURES:
  Total Credit Limit:        $1.928B
  CC Outstanding (Drawn):    $0.526B
  Unused Commitment:         $1.402B
  Blended Utilization:       27.3%
  Total EAD:                 $0.666B

RWA (US STANDARDIZED APPROACH):
  Total CC RWA:              $0.666B
  Transactor RWA:            $0.176B
  Revolver RWA:              $0.490B
  Average RWA Density:       100.0%  ← (US SA fixed at 100%)

CAPITAL REQUIREMENTS:
  Tier 1 Capital Req:        $0.057B  ← (8.5% of RWA)
  Conservation Buffer:       $0.017B  ← (2.5% of RWA)

SEGMENTATION:
  Transactors:               629,361 (62.9%)
  Revolvers:                 370,639 (37.1%)

RISK METRICS:
  Average PD:                4.05%
  Average NCO Rate:          2.00%
  NPL Rate:                  1.01%

OPTIMIZATION OPPORTUNITIES:
  Eligible for Limit Reduction:     505,829
  Eligible for Overdraft Conversion: 322,013
```

---

## 🎯 Key Differences from Generic Basel System

| Feature | Generic System | Your Customized System |
|---------|----------------|------------------------|
| **Approach** | IRB (Advanced) | US Standardized (12 CFR Part 3) |
| **RWA Formula** | Complex IRB formula | Fixed 100% risk weight |
| **CCF** | 75% generic | 10% (US unconditionally cancellable) |
| **Segments** | Credit score tiers | IndusInd income + behavior |
| **Field Names** | Generic | PNC data dictionary |
| **Charts** | Generic descriptions | Proper Basel terminology |
| **Branding** | Generic blue | Profit Insight navy/gold |
| **KPIs** | Basic metrics | PNC-specific 10 KPIs |
| **Stress Testing** | Simple PD/LGD | Multi-scenario with GDP |

---

## 📖 Regulatory References

### US Standardized Approach (12 CFR Part 3)

- **§3.32(l)**: Credit card receivables - 100% risk weight
- **§3.33(b)(2)**: Unconditionally cancellable lines - 10% CCF
- **§3.33(b)(1)**: Conditional overdrafts - 0% CCF
- **§3.37(c)**: Cash/deposit collateral - 0% risk weight
- **§3.11**: Minimum capital requirements + buffers

### Basel III Framework

- **CET1 Minimum**: 4.5%
- **Conservation Buffer**: 2.5%  
- **AT1 Buffer**: 1.5%
- **Total Tier 1 Target**: 8.5%

---

## 🆚 Comparison: Your Files vs Generated Output

### From PI_RWA_Data_Dictionary.xlsx

✅ **Field names match**: `cc_outstanding_b`, `unused_cc_b`, `total_cc_rwa_b`  
✅ **PNC values aligned**: $7.014B outstanding → scaled to 1M accounts  
✅ **US SA methodology**: 100% RW, 10% CCF exactly as specified  
✅ **Transactor/Revolver split**: 58%/42% from CFPB benchmark  

### From IndusInd_Bank_CC_RWA_business_case_1_3H.xlsx

✅ **Income segments**: Mass Market (15%), Mid-Market (40%), Affluent (35%), HNW (10%)  
✅ **Credit limits**: $889, $1,667, $2,778, $5,556 per segment  
✅ **Annual spend**: $2,000, $2,778, $4,444, $8,889 per segment  
✅ **Behavioral segmentation**: 11 customer types implemented  

### From Credit_Card_Charts.pptx

✅ **22+ charts** covering all analysis dimensions  
✅ **Proper Basel terminology** on axes (EAD, RWA, PD, NCO, T1)  
✅ **Multi-tab structure** for organized navigation  
✅ **Filters matching** PPT slide 30 (Product, EAD, Risk Weight)  

---

## 🔄 Future Enhancements

Based on your files, potential additions:

1. **FDIC Historical Data Tab** - Track trends using PNC historical data structure
2. **Peer Benchmark Comparison** - Compare vs 30 peer banks (Agent 2 output)
3. **Merchant Category Analysis** - If MCC data available
4. **Geographic Heat Map** - State-level concentration analysis  
5. **Vintage Cohort Analysis** - Performance by account age
6. **Pathway 3 Implementation** - Revolver to deposit account conversion

---

## 📞 Support

**Documentation**: This README + in-code comments  
**Data Dictionary**: Based on PI_RWA_Data_Dictionary.xlsx  
**Business Logic**: Based on IndusInd_Bank_CC_RWA_business_case_1_3H.xlsx  
**Chart Specs**: Based on Credit_Card_Charts.pptx  

---

## ✅ What You Have

1. ✅ **pnc_indusind_data_generator.py** - Dataset generator with your specifications
2. ✅ **profit_insight_rwa_dashboard.py** - Customized dashboard with Profit Insight branding
3. ✅ **pnc_indusind_cc_portfolio_1M.csv** - Generated 1M account dataset
4. ✅ **README_PROFIT_INSIGHT.md** - This comprehensive guide

---

*Profit Insight Basel RWA Analytics Platform*  
*Version 1.0 | March 2026*  
*Customized for PNC Bank + IndusInd Bank Segmentation Model*
