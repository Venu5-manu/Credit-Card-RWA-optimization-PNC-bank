"""
Profit Insight - Basel RWA Credit Card Dataset Generator
Based on PNC Bank (US Standardized Approach) and IndusInd Bank Segmentation

Data Dictionary: PI_RWA_Data_Dictionary.xlsx
Business Logic: IndusInd_Bank_CC_RWA_business_case_1_3H.xlsx

US Standardized Approach (12 CFR Part 3):
- CC Outstanding Risk Weight: 100%
- Unused CC CCF: 10%
- No IRB formulas (uses fixed risk weights)
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

class ProfitInsightCCDataGenerator:
    def __init__(self, n_accounts=1_000_000, random_state=42):
        """Initialize with PNC/IndusInd parameters"""
        self.n_accounts = n_accounts
        np.random.seed(random_state)
        
        # US Standardized Approach Parameters (12 CFR Part 3)
        self.basel_params = {
            'cc_risk_weight': 1.00,  # 100% RW for CC outstanding (§3.32(l))
            'unused_cc_ccf': 0.10,   # 10% CCF for unconditionally cancellable lines (§3.33(b)(2))
            'conditional_od_ccf': 0.00,  # 0% CCF for conditional overdraft
            'cash_collateral_rw': 0.00,  # 0% RW for cash/deposit secured (§3.37(c))
            'min_tier1_w_buffer': 0.085,  # 8.5% (4.5% min + 2.5% conservation + 1.5% AT1)
        }
        
        # IndusInd Segments - Income-based
        self.income_segments = {
            'Mass_Market': {'weight': 0.15, 'avg_limit': 889, 'avg_spend': 2000},
            'Mid_Market': {'weight': 0.40, 'avg_limit': 1667, 'avg_spend': 2778},
            'Affluent': {'weight': 0.35, 'avg_limit': 2778, 'avg_spend': 4444},
            'High_Net_Worth': {'weight': 0.10, 'avg_limit': 5556, 'avg_spend': 8889}
        }
        
        # Behavioral Segments - Transactor vs Revolver
        self.behavioral_split = {
            'transactor_pct': 0.58,  # 58% transactors (CFPB/Fed G.19)
            'revolver_pct': 0.42     # 42% revolvers
        }
        
        # FICO Score to PD Mapping (conservative - US banks)
        self.fico_pd_mapping = {
            'Super_Prime': {'fico_range': (750, 850), 'pd': 0.005, 'weight': 0.20},
            'Prime_Plus': {'fico_range': (700, 749), 'pd': 0.015, 'weight': 0.30},
            'Prime': {'fico_range': (660, 699), 'pd': 0.035, 'weight': 0.25},
            'Near_Prime': {'fico_range': (620, 659), 'pd': 0.075, 'weight': 0.15},
            'Subprime': {'fico_range': (550, 619), 'pd': 0.150, 'weight': 0.10}
        }
        
    def generate_dataset(self):
        """Generate PNC-style credit card portfolio"""
        print(f"Generating {self.n_accounts:,} credit card accounts (PNC/IndusInd model)...")
        
        # Step 1: Customer Demographics
        print("  [1/9] Generating customer demographics...")
        df = self._generate_demographics()
        
        # Step 2: Income Segmentation (IndusInd model)
        print("  [2/9] Applying income segmentation...")
        df = self._add_income_segments(df)
        
        # Step 3: FICO Scores and Credit Risk
        print("  [3/9] Generating FICO scores and credit risk...")
        df = self._add_fico_and_risk(df)
        
        # Step 4: Card Details and Limits
        print("  [4/9] Generating card details and credit limits...")
        df = self._add_card_details(df)
        
        # Step 5: Behavioral Classification (Transactor/Revolver)
        print("  [5/9] Classifying behavioral segments...")
        df = self._add_behavioral_segments(df)
        
        # Step 6: Exposure Calculations (US SA approach)
        print("  [6/9] Calculating exposures (EAD)...")
        df = self._calculate_exposures(df)
        
        # Step 7: RWA Calculations (US Standardized Approach)
        print("  [7/9] Calculating RWA (US SA methodology)...")
        df = self._calculate_rwa_us_sa(df)
        
        # Step 8: Performance Metrics
        print("  [8/9] Generating performance metrics...")
        df = self._add_performance_metrics(df)
        
        # Step 9: PNC-specific Fields
        print("  [9/9] Adding PNC regulatory fields...")
        df = self._add_pnc_fields(df)
        
        print(f"\n✓ Dataset generated: {len(df):,} accounts, {len(df.columns)} columns")
        return df
    
    def _generate_demographics(self):
        """Generate customer demographics"""
        account_ids = [f"CC{str(i+1).zfill(9)}" for i in range(self.n_accounts)]
        
        # Age distribution
        ages = np.random.choice(
            [28, 38, 48, 58, 68],
            size=self.n_accounts,
            p=[0.20, 0.35, 0.25, 0.15, 0.05]
        ) + np.random.randint(-3, 4, self.n_accounts)
        
        # Income distribution (realistic US distribution)
        incomes = np.random.lognormal(mean=10.9, sigma=0.65, size=self.n_accounts)
        incomes = np.clip(incomes, 25000, 750000)
        
        # Geographic distribution (US regions)
        regions = np.random.choice(
            ['Northeast', 'South', 'Midwest', 'West'],
            size=self.n_accounts,
            p=[0.18, 0.38, 0.21, 0.23]
        )
        
        # Account vintage
        vintage_months = np.random.exponential(scale=42, size=self.n_accounts)
        vintage_months = np.clip(vintage_months, 1, 300).astype(int)
        
        # Employment status
        employment_status = np.random.choice(
            ['Employed', 'Self-Employed', 'Retired', 'Other'],
            size=self.n_accounts,
            p=[0.70, 0.15, 0.10, 0.05]
        )
        
        return pd.DataFrame({
            'account_id': account_ids,
            'customer_age': ages.astype(int),
            'annual_income': incomes.round(0),
            'region': regions,
            'vintage_months': vintage_months,
            'employment_status': employment_status,
            'account_open_date': [
                datetime.now() - timedelta(days=int(m*30)) 
                for m in vintage_months
            ]
        })
    
    def _add_income_segments(self, df):
        """Add IndusInd-style income segments"""
        
        # Assign segments based on income levels
        def assign_income_segment(income):
            if income < 40000:
                return 'Mass_Market'
            elif income < 75000:
                return 'Mid_Market'
            elif income < 150000:
                return 'Affluent'
            else:
                return 'High_Net_Worth'
        
        df['income_segment'] = df['annual_income'].apply(assign_income_segment)
        
        # Segment details
        df['segment_avg_limit'] = df['income_segment'].map(
            {k: v['avg_limit'] for k, v in self.income_segments.items()}
        )
        
        df['segment_avg_spend'] = df['income_segment'].map(
            {k: v['avg_spend'] for k, v in self.income_segments.items()}
        )
        
        return df
    
    def _add_fico_and_risk(self, df):
        """Add FICO scores and risk classification"""
        
        # Assign FICO risk tiers
        segments = []
        segment_names = list(self.fico_pd_mapping.keys())
        weights = [self.fico_pd_mapping[s]['weight'] for s in segment_names]
        
        for _ in range(len(df)):
            segment = np.random.choice(segment_names, p=weights)
            segments.append(segment)
        
        df['fico_tier'] = segments
        
        # Generate FICO scores within tiers
        fico_scores = []
        for tier in segments:
            fico_range = self.fico_pd_mapping[tier]['fico_range']
            score = np.random.randint(fico_range[0], fico_range[1] + 1)
            fico_scores.append(score)
        
        df['fico_score'] = fico_scores
        
        # Probability of Default (from FICO tier)
        df['pd'] = df['fico_tier'].map(
            {k: v['pd'] for k, v in self.fico_pd_mapping.items()}
        )
        
        # Add PD stress factor for stress testing
        df['pd_base'] = df['pd']  # Baseline PD
        
        # Delinquency status
        df['dpd_status'] = np.random.choice(
            ['Current', 'DPD_30', 'DPD_60', 'DPD_90+'],
            size=len(df),
            p=[0.96, 0.02, 0.01, 0.01]
        )
        
        # Net Charge-Off Rate (NCO) by segment
        df['nco_rate'] = df['fico_tier'].map({
            'Super_Prime': 0.003,
            'Prime_Plus': 0.008,
            'Prime': 0.015,
            'Near_Prime': 0.035,
            'Subprime': 0.080
        })
        
        return df
    
    def _add_card_details(self, df):
        """Add credit card details and limits"""
        
        # Credit limit based on income and segment
        df['credit_limit'] = (
            df['segment_avg_limit'] * 
            (df['fico_score'] / 700) * 
            np.random.uniform(0.7, 1.3, len(df))
        ).round(0)
        
        df['credit_limit'] = np.clip(df['credit_limit'], 300, 25000)
        
        # Card type
        df['card_type'] = np.random.choice(
            ['Standard', 'Cash_Back', 'Rewards', 'Premium'],
            size=len(df),
            p=[0.45, 0.30, 0.18, 0.07]
        )
        
        # Card category
        df['card_category'] = np.where(
            df['card_type'].isin(['Premium', 'Rewards']),
            'Premium',
            'Standard'
        )
        
        # APR (Annual Percentage Rate)
        df['apr'] = np.random.uniform(0.15, 0.28, len(df))
        
        return df
    
    def _add_behavioral_segments(self, df):
        """Add Transactor vs Revolver behavioral classification"""
        
        # Assign behavioral type (biased by income and FICO)
        def assign_behavioral_type(row):
            # Higher income/FICO → more likely to be transactor
            if row['income_segment'] in ['Affluent', 'High_Net_Worth']:
                return np.random.choice(['Transactor', 'Revolver'], p=[0.75, 0.25])
            elif row['fico_tier'] in ['Super_Prime', 'Prime_Plus']:
                return np.random.choice(['Transactor', 'Revolver'], p=[0.70, 0.30])
            else:
                return np.random.choice(['Transactor', 'Revolver'], p=[0.45, 0.55])
        
        df['behavioral_type'] = df.apply(assign_behavioral_type, axis=1)
        
        # Set utilization based on behavioral type
        df['utilization_rate'] = np.where(
            df['behavioral_type'] == 'Transactor',
            np.random.beta(2, 8, len(df)),  # Low utilization (avg ~20%)
            np.random.beta(6, 2, len(df))   # High utilization (avg ~75%)
        )
        
        # Outstanding balance
        df['cc_outstanding_b'] = (
            df['credit_limit'] * df['utilization_rate']
        ).round(2)
        
        # Ensure transactors pay off monthly (low balance)
        df.loc[df['behavioral_type'] == 'Transactor', 'cc_outstanding_b'] = (
            df.loc[df['behavioral_type'] == 'Transactor', 'cc_outstanding_b'] * 
            np.random.uniform(0.1, 0.3, (df['behavioral_type'] == 'Transactor').sum())
        )
        
        # Unused commitment
        df['unused_cc_b'] = (df['credit_limit'] - df['cc_outstanding_b']).round(2)
        
        # Monthly spending
        df['avg_monthly_spend'] = (
            df['segment_avg_spend'] / 12 * 
            np.random.uniform(0.7, 1.3, len(df))
        ).round(2)
        
        # Payment behavior
        df['monthly_payment'] = np.where(
            df['behavioral_type'] == 'Transactor',
            df['cc_outstanding_b'],  # Pay in full
            df['cc_outstanding_b'] * np.random.uniform(0.02, 0.15, len(df))  # Minimum payment
        ).round(2)
        
        # Transactor/Revolver flags
        df['is_transactor'] = (df['behavioral_type'] == 'Transactor').astype(int)
        df['is_revolver'] = (df['behavioral_type'] == 'Revolver').astype(int)
        
        return df
    
    def _calculate_exposures(self, df):
        """Calculate exposures (EAD) using US SA methodology"""
        
        # On-balance sheet exposure (drawn amount)
        df['on_balance_exposure_b'] = df['cc_outstanding_b']
        
        # Off-balance sheet exposure (undrawn × CCF)
        # US SA: 10% CCF for unconditionally cancellable CC lines
        df['off_balance_exposure_b'] = (
            df['unused_cc_b'] * self.basel_params['unused_cc_ccf']
        ).round(2)
        
        # Total Exposure at Default (EAD)
        df['ead_b'] = (
            df['on_balance_exposure_b'] + df['off_balance_exposure_b']
        ).round(2)
        
        # Total committed exposure (for reporting)
        df['total_limit_b'] = df['credit_limit']
        
        # Exposure percentage
        df['exposure_pct'] = (
            df['ead_b'] / df['total_limit_b'].replace(0, 1)
        ).round(4)
        
        return df
    
    def _calculate_rwa_us_sa(self, df):
        """Calculate RWA using US Standardized Approach (12 CFR Part 3)"""
        
        # US SA: 100% risk weight for credit card receivables
        df['risk_weight'] = self.basel_params['cc_risk_weight']
        
        # RWA = EAD × Risk Weight
        df['total_cc_rwa_b'] = (df['ead_b'] * df['risk_weight']).round(2)
        
        # RWA by behavioral type
        df['transactor_rwa_b'] = np.where(
            df['is_transactor'] == 1,
            df['total_cc_rwa_b'],
            0
        )
        
        df['revolver_rwa_b'] = np.where(
            df['is_revolver'] == 1,
            df['total_cc_rwa_b'],
            0
        )
        
        # RWA Density
        df['rwa_density'] = (
            df['total_cc_rwa_b'] / df['ead_b'].replace(0, 1)
        ).round(4)
        
        # Expected Loss (for comparison)
        # Using LGD of 45% for unsecured CC (typical US bank assumption)
        df['lgd'] = 0.45
        df['expected_loss_b'] = (
            df['ead_b'] * df['pd'] * df['lgd']
        ).round(2)
        
        return df
    
    def _add_performance_metrics(self, df):
        """Add income, expenses, and profitability metrics"""
        
        # Interest income (on revolver balances)
        df['interest_income_b'] = (
            df['cc_outstanding_b'] * df['apr'] / 12
        ).round(2)
        
        # Fee income (interchange, late fees, etc.)
        df['fee_income_b'] = np.where(
            df['avg_monthly_spend'] > 0,
            df['avg_monthly_spend'] * np.random.uniform(0.015, 0.025, len(df)),
            0
        ).round(2)
        
        # Total revenue
        df['total_revenue_b'] = (
            df['interest_income_b'] + df['fee_income_b']
        ).round(2)
        
        # Funding cost (cost of funds)
        df['funding_cost_b'] = (
            df['cc_outstanding_b'] * 0.03 / 12  # 3% annual COF
        ).round(2)
        
        # Operating expense
        df['operating_expense_b'] = np.random.uniform(8, 25, len(df)).round(2)
        
        # Credit loss provision
        df['credit_loss_provision_b'] = df['expected_loss_b']
        
        # Net income
        df['net_income_b'] = (
            df['total_revenue_b'] - 
            df['funding_cost_b'] - 
            df['operating_expense_b'] - 
            df['credit_loss_provision_b']
        ).round(2)
        
        # Return on Assets (ROA)
        df['roa'] = (
            df['net_income_b'] * 12 / df['ead_b'].replace(0, 1)
        ).round(4)
        
        # Return on Equity (ROE) - using T1 capital as equity proxy
        df['roe'] = (
            df['net_income_b'] * 12 / 
            (df['total_cc_rwa_b'] * self.basel_params['min_tier1_w_buffer']).replace(0, 1)
        ).round(4)
        
        return df
    
    def _add_pnc_fields(self, df):
        """Add PNC-specific regulatory and reporting fields"""
        
        # Bank metadata
        df['bank_name'] = 'PNC Bank, National Association'
        df['fdic_cert'] = 6384
        df['report_date'] = datetime.now().strftime('%Y%m%d')
        df['approach'] = 'US Standardized Approach'
        
        # Capital requirements (Tier 1)
        # Min Tier 1 ratio: 8.5% (4.5% base + 2.5% conservation + 1.5% AT1)
        df['tier1_requirement_b'] = (
            df['total_cc_rwa_b'] * self.basel_params['min_tier1_w_buffer']
        ).round(2)
        
        # Capital adequacy buffer
        df['capital_buffer_b'] = (
            df['total_cc_rwa_b'] * 0.025  # 2.5% conservation buffer
        ).round(2)
        
        # Regulatory exposure class
        df['exposure_class'] = 'Retail - Credit Card'
        
        # Product code
        df['product_code'] = 'CC_RETAIL'
        
        # Status flags
        df['is_performing'] = (df['dpd_status'] == 'Current').astype(int)
        df['is_npl'] = (df['dpd_status'] == 'DPD_90+').astype(int)
        
        # Optimization potential flags
        df['eligible_for_limit_reduction'] = (
            (df['is_transactor'] == 1) & 
            (df['utilization_rate'] < 0.30)
        ).astype(int)
        
        df['eligible_for_overdraft_conversion'] = (
            (df['eligible_for_limit_reduction'] == 1) &
            (df['income_segment'].isin(['Mid_Market', 'Affluent']))
        ).astype(int)
        
        # PNC portfolio identifiers
        df['portfolio_segment'] = df.apply(
            lambda x: f"{x['income_segment']}_{x['behavioral_type']}", axis=1
        )
        
        return df
    
    def save_dataset(self, df, filepath='pnc_cc_portfolio.csv'):
        """Save dataset to CSV"""
        df.to_csv(filepath, index=False)
        
        # Print summary statistics
        print(f"\n✓ Dataset saved: {filepath}")
        print(f"  Size: {len(df):,} rows × {len(df.columns)} columns")
        print(f"\n{'='*80}")
        print("PORTFOLIO SUMMARY (PNC/IndusInd Model)")
        print(f"{'='*80}")
        
        total_limit = df['total_limit_b'].sum() / 1e9
        total_outstanding = df['cc_outstanding_b'].sum() / 1e9
        total_unused = df['unused_cc_b'].sum() / 1e9
        total_ead = df['ead_b'].sum() / 1e9
        total_rwa = df['total_cc_rwa_b'].sum() / 1e9
        
        print(f"\nEXPOSURES:")
        print(f"  Total Credit Limit:        ${total_limit:.3f}B")
        print(f"  CC Outstanding (Drawn):    ${total_outstanding:.3f}B")
        print(f"  Unused Commitment:         ${total_unused:.3f}B")
        print(f"  Blended Utilization:       {(total_outstanding/total_limit)*100:.1f}%")
        print(f"  Total EAD:                 ${total_ead:.3f}B")
        
        print(f"\nRWA (US STANDARDIZED APPROACH):")
        print(f"  Total CC RWA:              ${total_rwa:.3f}B")
        print(f"  Transactor RWA:            ${df['transactor_rwa_b'].sum()/1e9:.3f}B")
        print(f"  Revolver RWA:              ${df['revolver_rwa_b'].sum()/1e9:.3f}B")
        print(f"  Average RWA Density:       {df['rwa_density'].mean()*100:.1f}%")
        
        print(f"\nCAPITAL REQUIREMENTS:")
        print(f"  Tier 1 Capital Req:        ${df['tier1_requirement_b'].sum()/1e9:.3f}B")
        print(f"  Conservation Buffer:       ${df['capital_buffer_b'].sum()/1e9:.3f}B")
        
        print(f"\nSEGMENTATION:")
        print(f"  Transactors:               {df['is_transactor'].sum():,} ({df['is_transactor'].mean()*100:.1f}%)")
        print(f"  Revolvers:                 {df['is_revolver'].sum():,} ({df['is_revolver'].mean()*100:.1f}%)")
        
        print(f"\nRISK METRICS:")
        print(f"  Average PD:                {df['pd'].mean()*100:.2f}%")
        print(f"  Average NCO Rate:          {df['nco_rate'].mean()*100:.2f}%")
        print(f"  NPL Rate:                  {df['is_npl'].mean()*100:.2f}%")
        
        print(f"\nOPTIMIZATION OPPORTUNITIES:")
        print(f"  Eligible for Limit Reduction:     {df['eligible_for_limit_reduction'].sum():,}")
        print(f"  Eligible for Overdraft Conversion: {df['eligible_for_overdraft_conversion'].sum():,}")

# Main execution
if __name__ == "__main__":
    print("\n" + "="*80)
    print("PROFIT INSIGHT - BASEL RWA CREDIT CARD DATASET GENERATOR")
    print("PNC Bank (US SA) + IndusInd Segmentation Model")
    print("="*80 + "\n")
    
    # Generate dataset
    generator = ProfitInsightCCDataGenerator(n_accounts=1_000_000)
    df = generator.generate_dataset()
    
    # Save dataset
    generator.save_dataset(df, filepath='/home/claude/pnc_indusind_cc_portfolio_1M.csv')
    
    # Display sample
    print("\n" + "="*80)
    print("SAMPLE DATA (First 5 Accounts)")
    print("="*80)
    display_cols = [
        'account_id', 'income_segment', 'behavioral_type', 'fico_score',
        'credit_limit', 'cc_outstanding_b', 'ead_b', 'total_cc_rwa_b', 'rwa_density'
    ]
    print(df[display_cols].head().to_string(index=False))
    
    print("\n✓ Generation complete!\n")
