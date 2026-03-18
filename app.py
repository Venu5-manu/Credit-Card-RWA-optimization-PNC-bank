"""
Profit Insight Basel RWA Analytics Dashboard
PNC Bank Credit Card Portfolio - US Standardized Approach

Features:
- Multi-tab navigation with Basel-compliant KPIs
- Stress testing scenarios (PD/LGD/Macro)
- Transactor vs Revolver analysis
- Income segment performance
- RWA optimization pathways
- Proper Basel terminology on all axes and headings
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="Profit Insight | Basel RWA Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Profit Insight Branding - Professional Navy/Gold Theme
st.markdown("""
<style>
    /* Profit Insight Brand Colors */
    :root {
        --pi-navy: #1B3B6F;
        --pi-gold: #D4AF37;
        --pi-light-blue: #4A90E2;
        --pi-gray: #F5F7FA;
    }
    
    .stApp {
        background-color: #FAFBFC;
    }
    
    /* Sidebar branding */
    .css-1d391kg {
        background: linear-gradient(180deg, #1B3B6F 0%, #2C5282 100%);
    }
    
    /* Main header */
    h1 {
        color: #1B3B6F;
        font-weight: 700;
        font-family: 'Helvetica Neue', Arial, sans-serif;
        border-bottom: 4px solid #D4AF37;
        padding-bottom: 15px;
    }
    
    h2 {
        color: #2C5282;
        font-weight: 600;
        margin-top: 25px;
    }
    
    h3 {
        color: #4A90E2;
        font-weight: 500;
    }
    
    /* Metric cards */
    [data-testid="stMetricValue"] {
        font-size: 36px;
        color: #1B3B6F;
        font-weight: 700;
    }
    
    [data-testid="stMetricDelta"] {
        font-size: 18px;
    }
    
    /* Info boxes */
    .stAlert {
        background-color: #EBF5FB;
        border-left: 5px solid #4A90E2;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: #E8EDF2;
        border-radius: 8px 8px 0px 0px;
        padding: 12px 24px;
        font-weight: 600;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #1B3B6F;
        color: white !important;
    }
    
    /* Branding footer */
    .pi-footer {
        text-align: center;
        color: #6B7280;
        padding: 20px;
        margin-top: 40px;
        border-top: 2px solid #D4AF37;
        font-size: 14px;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# DATA LOADING
# ============================================================================

@st.cache_data
def load_data():
    """Load PNC/IndusInd credit card dataset"""
    try:
        df = pd.read_csv('pnc_indusind_cc_portfolio_1M.csv')
        return df
    except FileNotFoundError:
        st.error("⚠️ Dataset not found. Please run pnc_indusind_data_generator.py first.")
        st.stop()

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def format_currency(value, decimals=2):
    """Format value as currency"""
    if abs(value) >= 1e9:
        return f"${value/1e9:,.{decimals}f}B"
    elif abs(value) >= 1e6:
        return f"${value/1e6:,.{decimals}f}M"
    elif abs(value) >= 1e3:
        return f"${value/1e3:,.{decimals}f}K"
    else:
        return f"${value:,.{decimals}f}"

def format_percentage(value, decimals=2):
    """Format value as percentage"""
    return f"{value*100:.{decimals}f}%"

def format_bps(value):
    """Format value as basis points"""
    return f"{value*10000:.0f} bps"

def calculate_rwa_reduction(df):
    """Calculate RWA reduction potential from optimization pathways"""
    
    # Pathway 1: Transactor Credit Limit Reduction (30% reduction scenario)
    transactors = df[df['is_transactor'] == 1].copy()
    reduction_pct = 0.30  # 30% limit reduction
    
    # Calculate new exposures after limit reduction
    new_limit = transactors['credit_limit'] * (1 - reduction_pct)
    new_unused = new_limit - transactors['cc_outstanding_b']
    new_unused = new_unused.clip(lower=0)  # Can't be negative
    
    # New EAD with reduced limits
    new_ead = transactors['cc_outstanding_b'] + new_unused * 0.10
    new_rwa_transactor = new_ead * 1.0
    
    # RWA saved from transactor optimization
    rwa_saved_transactor = (transactors['total_cc_rwa_b'].sum() - new_rwa_transactor.sum())
    
    # Pathway 2: Overdraft Conversion (eligible accounts)
    eligible_od = df[df['eligible_for_overdraft_conversion'] == 1].copy()
    
    # Assume 20% of eligible get overdraft, 80% netting coverage
    od_conversion_rate = 0.20
    netting_coverage = 0.80
    
    # Reduced exposure from overdraft netting
    od_accounts = eligible_od.sample(frac=od_conversion_rate, random_state=42)
    od_ead_reduction = od_accounts['ead_b'].sum() * netting_coverage
    rwa_saved_overdraft = od_ead_reduction * 1.0
    
    # Total RWA reduction
    total_rwa_reduction = rwa_saved_transactor + rwa_saved_overdraft
    
    # Calculate capital relief (8.5% Tier 1)
    tier1_relief = total_rwa_reduction * 0.085
    
    return {
        'total_rwa_reduction': total_rwa_reduction,
        'transactor_pathway': rwa_saved_transactor,
        'overdraft_pathway': rwa_saved_overdraft,
        'tier1_relief': tier1_relief,
        'reduction_pct': (total_rwa_reduction / df['total_cc_rwa_b'].sum()) * 100
    }

# ============================================================================
# BASEL REGULATORY DICTIONARY
# ============================================================================

BASEL_DICTIONARY = {
    'EAD': {
        'term': 'Exposure at Default',
        'formula': 'EAD = Outstanding + (Unused × CCF)',
        'us_sa': 'Outstanding + (Unused × 10%)',
        'reference': '12 CFR Part 3 §3.33'
    },
    'RWA': {
        'term': 'Risk-Weighted Assets',
        'formula': 'RWA = EAD × Risk Weight',
        'us_sa': 'EAD × 100% for credit cards',
        'reference': '12 CFR Part 3 §3.32(l)'
    },
    'CCF': {
        'term': 'Credit Conversion Factor',
        'formula': 'Off-Balance = Unused × CCF',
        'us_sa': '10% for unconditionally cancellable lines',
        'reference': '12 CFR Part 3 §3.33(b)(2)'
    },
    'Tier 1 Ratio': {
        'term': 'Tier 1 Capital / RWA',
        'formula': 'T1 Ratio = Tier 1 Capital / Total RWA',
        'us_sa': 'Minimum 8.5% (4.5% + 2.5% buffer + 1.5% AT1)',
        'reference': 'Basel III + 12 CFR Part 3 §3.11'
    },
    'NCO': {
        'term': 'Net Charge-Off Rate',
        'formula': 'NCO = Charge-offs − Recoveries',
        'us_sa': 'Annualized % of average balances',
        'reference': 'FDIC Call Report'
    }
}

def show_basel_dictionary():
    """Display Basel dictionary in sidebar"""
    with st.sidebar.expander("📖 Basel Regulatory Dictionary", expanded=False):
        term = st.selectbox(
            "Select Basel term:",
            options=list(BASEL_DICTIONARY.keys()),
            format_func=lambda x: f"{x} - {BASEL_DICTIONARY[x]['term']}"
        )
        
        info = BASEL_DICTIONARY[term]
        st.markdown(f"**{term}** - {info['term']}")
        st.code(f"General: {info['formula']}", language='text')
        st.code(f"US SA: {info['us_sa']}", language='text')
        st.caption(f"📌 Reference: {info['reference']}")

# ============================================================================
# SIDEBAR FILTERS & CONTROLS
# ============================================================================

def create_sidebar_filters(df):
    """Create Profit Insight sidebar with filters and stress scenarios"""
    
    # Profit Insight Header
    st.sidebar.markdown("""
    <div style='text-align: center; padding: 20px 0;'>
        <h1 style='color: #D4AF37; font-size: 24px; margin: 0;'>PROFIT INSIGHT</h1>
        <p style='color: #9CA3AF; font-size: 12px; margin: 5px 0;'>Basel RWA Analytics Platform</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.sidebar.markdown("---")
    
    # Stress Testing Mode
    st.sidebar.title("📊 Stress Testing")
    
    stress_mode = st.sidebar.checkbox("Enable Stress Scenarios", value=False)
    
    if stress_mode:
        st.sidebar.subheader("Scenario Parameters")
        
        scenario_type = st.sidebar.selectbox(
            "Pre-defined Scenario",
            ["Custom", "Baseline", "Mild Recession", "Severe Recession", "Financial Crisis"]
        )
        
        if scenario_type == "Baseline":
            pd_stress, nco_stress, macro_stress = 1.0, 1.0, 1.0
        elif scenario_type == "Mild Recession":
            pd_stress, nco_stress, macro_stress = 1.5, 1.3, 0.95
        elif scenario_type == "Severe Recession":
            pd_stress, nco_stress, macro_stress = 2.5, 2.0, 0.85
        elif scenario_type == "Financial Crisis":
            pd_stress, nco_stress, macro_stress = 4.0, 3.5, 0.70
        else:  # Custom
            pd_stress = st.sidebar.slider("PD Stress Factor", 0.5, 5.0, 1.0, 0.1)
            nco_stress = st.sidebar.slider("NCO Stress Factor", 0.5, 5.0, 1.0, 0.1)
            macro_stress = st.sidebar.slider("GDP Impact", 0.5, 1.2, 1.0, 0.05)
    else:
        pd_stress, nco_stress, macro_stress = 1.0, 1.0, 1.0
        scenario_type = "Baseline"
    
    st.sidebar.markdown("---")
    
    # Portfolio Filters
    st.sidebar.title("🔧 Portfolio Filters")
    
    # Income Segment Filter
    income_segments = st.sidebar.multiselect(
        "Income Segments",
        options=df['income_segment'].unique(),
        default=df['income_segment'].unique()
    )
    
    # Behavioral Type Filter
    behavioral_types = st.sidebar.multiselect(
        "Behavioral Type",
        options=['Transactor', 'Revolver'],
        default=['Transactor', 'Revolver']
    )
    
    # FICO Tier Filter
    fico_tiers = st.sidebar.multiselect(
        "FICO Risk Tier",
        options=df['fico_tier'].unique(),
        default=df['fico_tier'].unique()
    )
    
    # Region Filter
    regions = st.sidebar.multiselect(
        "Geographic Region",
        options=df['region'].unique(),
        default=df['region'].unique()
    )
    
    # Card Type Filter
    card_types = st.sidebar.multiselect(
        "Card Type",
        options=df['card_type'].unique(),
        default=df['card_type'].unique()
    )
    
    # Vintage Range
    vintage_range = st.sidebar.slider(
        "Account Vintage (Months)",
        min_value=int(df['vintage_months'].min()),
        max_value=int(df['vintage_months'].max()),
        value=(int(df['vintage_months'].min()), int(df['vintage_months'].max()))
    )
    
    # FICO Score Range
    fico_range = st.sidebar.slider(
        "FICO Score Range",
        min_value=int(df['fico_score'].min()),
        max_value=int(df['fico_score'].max()),
        value=(int(df['fico_score'].min()), int(df['fico_score'].max()))
    )
    
    st.sidebar.markdown("---")
    
    # Basel Dictionary
    show_basel_dictionary()
    
    return {
        'stress_mode': stress_mode,
        'scenario_type': scenario_type,
        'pd_stress': pd_stress,
        'nco_stress': nco_stress,
        'macro_stress': macro_stress,
        'income_segments': income_segments,
        'behavioral_types': behavioral_types,
        'fico_tiers': fico_tiers,
        'regions': regions,
        'card_types': card_types,
        'vintage_range': vintage_range,
        'fico_range': fico_range
    }

# ============================================================================
# DATA FILTERING & STRESS APPLICATION
# ============================================================================

def apply_filters_and_stress(df, filters):
    """Apply filters and stress scenarios to dataset"""
    df_filtered = df.copy()
    
    # Apply stress scenarios
    if filters['stress_mode']:
        df_filtered['pd'] = df_filtered['pd_base'] * filters['pd_stress']
        df_filtered['nco_rate'] = df_filtered['nco_rate'] * filters['nco_stress']
        df_filtered['expected_loss_b'] = (
            df_filtered['ead_b'] * df_filtered['pd'] * df_filtered['lgd']
        )
        # Recalculate net income with stressed losses
        df_filtered['net_income_b'] = (
            df_filtered['total_revenue_b'] -
            df_filtered['funding_cost_b'] -
            df_filtered['operating_expense_b'] -
            df_filtered['expected_loss_b']
        )
    
    # Apply portfolio filters
    df_filtered = df_filtered[
        (df_filtered['income_segment'].isin(filters['income_segments'])) &
        (df_filtered['behavioral_type'].isin(filters['behavioral_types'])) &
        (df_filtered['fico_tier'].isin(filters['fico_tiers'])) &
        (df_filtered['region'].isin(filters['regions'])) &
        (df_filtered['card_type'].isin(filters['card_types'])) &
        (df_filtered['vintage_months'] >= filters['vintage_range'][0]) &
        (df_filtered['vintage_months'] <= filters['vintage_range'][1]) &
        (df_filtered['fico_score'] >= filters['fico_range'][0]) &
        (df_filtered['fico_score'] <= filters['fico_range'][1])
    ]
    
    return df_filtered

# ============================================================================
# VISUALIZATION FUNCTIONS
# ============================================================================

def plot_portfolio_overview(df):
    """Portfolio Overview Tab Charts"""
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Chart 1: EAD by Income Segment ($ Billions)
        segment_ead = df.groupby('income_segment')['ead_b'].sum().reset_index()
        segment_ead['ead_b'] = segment_ead['ead_b'] / 1e9
        
        fig = px.bar(
            segment_ead,
            x='income_segment',
            y='ead_b',
            title='Exposure at Default (EAD) by Income Segment',
            labels={'ead_b': 'Total EAD ($B)', 'income_segment': 'Income Segment'},
            color='ead_b',
            color_continuous_scale='Blues'
        )
        fig.update_layout(
            title_font_size=16,
            title_font_color='#1B3B6F',
            showlegend=False,
            yaxis_title='Total EAD ($B)',
            xaxis_title='Income Segment'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Chart 2: RWA by Behavioral Type ($ Billions)
        behavioral_rwa = df.groupby('behavioral_type')['total_cc_rwa_b'].sum().reset_index()
        behavioral_rwa['total_cc_rwa_b'] = behavioral_rwa['total_cc_rwa_b'] / 1e9
        
        fig = px.pie(
            behavioral_rwa,
            values='total_cc_rwa_b',
            names='behavioral_type',
            title='Risk-Weighted Assets (RWA) by Behavioral Type',
            color_discrete_sequence=['#1B3B6F', '#D4AF37']
        )
        fig.update_layout(
            title_font_size=16,
            title_font_color='#1B3B6F'
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)
    
    col3, col4 = st.columns(2)
    
    with col3:
        # Chart 3: FICO Score Distribution (Accounts)
        fig = px.histogram(
            df,
            x='fico_score',
            nbins=50,
            title='FICO Score Distribution',
            labels={'fico_score': 'FICO Score', 'count': 'Number of Accounts'},
            color_discrete_sequence=['#4A90E2']
        )
        fig.update_layout(
            title_font_size=16,
            title_font_color='#1B3B6F',
            xaxis_title='FICO Score',
            yaxis_title='Number of Accounts'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col4:
        # Chart 4: Utilization Rate Distribution (%)
        fig = px.histogram(
            df,
            x='utilization_rate',
            nbins=50,
            title='Credit Utilization Rate Distribution',
            labels={'utilization_rate': 'Utilization Rate', 'count': 'Number of Accounts'},
            color_discrete_sequence=['#2C5282']
        )
        fig.update_layout(
            title_font_size=16,
            title_font_color='#1B3B6F',
            xaxis_title='Utilization Rate (%)',
            yaxis_title='Number of Accounts',
            xaxis_tickformat='.0%'
        )
        st.plotly_chart(fig, use_container_width=True)

def plot_risk_analytics(df):
    """Risk Analytics Tab Charts"""
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Chart 5: PD Distribution by FICO Tier (%)
        fig = px.box(
            df,
            x='fico_tier',
            y='pd',
            title='Probability of Default (PD) by FICO Tier',
            labels={'pd': 'PD (%)', 'fico_tier': 'FICO Risk Tier'},
            color='fico_tier',
            color_discrete_sequence=px.colors.sequential.Reds
        )
        fig.update_layout(
            title_font_size=16,
            title_font_color='#1B3B6F',
            yaxis_tickformat='.2%',
            yaxis_title='Probability of Default (PD) %',
            xaxis_title='FICO Risk Tier',
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Chart 6: NCO Rate by Income Segment (bps)
        nco_by_segment = df.groupby('income_segment')['nco_rate'].mean().reset_index()
        
        fig = px.bar(
            nco_by_segment,
            x='income_segment',
            y='nco_rate',
            title='Net Charge-Off (NCO) Rate by Income Segment',
            labels={'nco_rate': 'NCO Rate (%)', 'income_segment': 'Income Segment'},
            color='nco_rate',
            color_continuous_scale='Oranges'
        )
        fig.update_layout(
            title_font_size=16,
            title_font_color='#1B3B6F',
            yaxis_tickformat='.2%',
            yaxis_title='NCO Rate (%)',
            xaxis_title='Income Segment'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    col3, col4 = st.columns(2)
    
    with col3:
        # Chart 7: Expected Loss by Segment ($ Millions)
        el_by_segment = df.groupby('income_segment')['expected_loss_b'].sum().reset_index()
        el_by_segment['expected_loss_b'] = el_by_segment['expected_loss_b'] / 1e6
        
        fig = px.pie(
            el_by_segment,
            values='expected_loss_b',
            names='income_segment',
            title='Expected Loss (EL) Distribution by Income Segment',
            color_discrete_sequence=px.colors.sequential.YlOrRd
        )
        fig.update_layout(
            title_font_size=16,
            title_font_color='#1B3B6F'
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)
    
    with col4:
        # Chart 8: FICO Score vs PD Scatter
        sample = df.sample(min(10000, len(df)))
        fig = px.scatter(
            sample,
            x='fico_score',
            y='pd',
            color='behavioral_type',
            title='FICO Score vs Probability of Default (PD)',
            labels={'fico_score': 'FICO Score', 'pd': 'PD (%)'},
            opacity=0.6,
            color_discrete_map={'Transactor': '#1B3B6F', 'Revolver': '#D4AF37'}
        )
        fig.update_layout(
            title_font_size=16,
            title_font_color='#1B3B6F',
            yaxis_tickformat='.1%',
            xaxis_title='FICO Score',
            yaxis_title='Probability of Default (PD) %'
        )
        st.plotly_chart(fig, use_container_width=True)

def plot_exposure_analysis(df):
    """Exposure & Balance Analysis Charts"""
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Chart 9: On-Balance vs Off-Balance Exposure ($B)
        exposure_comp = pd.DataFrame({
            'Exposure Type': ['On-Balance\n(Drawn)', 'Off-Balance\n(Undrawn × 10% CCF)'],
            'Amount ($B)': [
                df['on_balance_exposure_b'].sum() / 1e9,
                df['off_balance_exposure_b'].sum() / 1e9
            ]
        })
        
        fig = px.bar(
            exposure_comp,
            x='Exposure Type',
            y='Amount ($B)',
            title='On-Balance vs Off-Balance Exposure Components',
            labels={'Amount ($B)': 'Total Exposure ($B)'},
            color='Exposure Type',
            color_discrete_map={
                'On-Balance\n(Drawn)': '#1B3B6F',
                'Off-Balance\n(Undrawn × 10% CCF)': '#4A90E2'
            }
        )
        fig.update_layout(
            title_font_size=16,
            title_font_color='#1B3B6F',
            showlegend=False,
            yaxis_title='Total Exposure ($B)',
            xaxis_title='Exposure Component'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Chart 10: Credit Limit Distribution by Income Segment ($)
        fig = px.box(
            df,
            x='income_segment',
            y='credit_limit',
            title='Credit Limit Distribution by Income Segment',
            labels={'credit_limit': 'Credit Limit ($)', 'income_segment': 'Income Segment'},
            color='income_segment'
        )
        fig.update_layout(
            title_font_size=16,
            title_font_color='#1B3B6F',
            yaxis_title='Credit Limit ($)',
            xaxis_title='Income Segment',
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)
    
    col3, col4 = st.columns(2)
    
    with col3:
        # Chart 11: Utilization Rate by Behavioral Type (%)
        util_comparison = df.groupby('behavioral_type')['utilization_rate'].mean().reset_index()
        
        fig = px.bar(
            util_comparison,
            x='behavioral_type',
            y='utilization_rate',
            title='Average Utilization Rate by Behavioral Type',
            labels={'utilization_rate': 'Avg Utilization Rate (%)', 'behavioral_type': 'Behavioral Type'},
            color='behavioral_type',
            color_discrete_map={'Transactor': '#1B3B6F', 'Revolver': '#D4AF37'}
        )
        fig.update_layout(
            title_font_size=16,
            title_font_color='#1B3B6F',
            yaxis_tickformat='.1%',
            yaxis_title='Average Utilization Rate (%)',
            xaxis_title='Behavioral Type',
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col4:
        # Chart 12: Outstanding Balance by Card Type ($M)
        balance_by_type = df.groupby('card_type')['cc_outstanding_b'].sum().reset_index()
        balance_by_type['cc_outstanding_b'] = balance_by_type['cc_outstanding_b'] / 1e6
        
        fig = px.bar(
            balance_by_type,
            x='card_type',
            y='cc_outstanding_b',
            title='Total Outstanding Balance by Card Type',
            labels={'cc_outstanding_b': 'Outstanding Balance ($M)', 'card_type': 'Card Type'},
            color='cc_outstanding_b',
            color_continuous_scale='Greens'
        )
        fig.update_layout(
            title_font_size=16,
            title_font_color='#1B3B6F',
            yaxis_title='Outstanding Balance ($M)',
            xaxis_title='Card Type'
        )
        st.plotly_chart(fig, use_container_width=True)

def plot_capital_requirements(df):
    """Capital & Regulatory Analysis Charts"""
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Chart 13: Tier 1 Capital Requirement by Income Segment ($M)
        t1_by_segment = df.groupby('income_segment')['tier1_requirement_b'].sum().reset_index()
        t1_by_segment['tier1_requirement_b'] = t1_by_segment['tier1_requirement_b'] / 1e6
        
        fig = px.bar(
            t1_by_segment,
            x='income_segment',
            y='tier1_requirement_b',
            title='Tier 1 Capital Requirement by Income Segment',
            labels={'tier1_requirement_b': 'Tier 1 Capital Req ($M)', 'income_segment': 'Income Segment'},
            color='tier1_requirement_b',
            color_continuous_scale='Blues'
        )
        fig.update_layout(
            title_font_size=16,
            title_font_color='#1B3B6F',
            yaxis_title='Tier 1 Capital Required ($M)',
            xaxis_title='Income Segment'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Chart 14: RWA Composition - Transactor vs Revolver ($B)
        rwa_composition = pd.DataFrame({
            'Type': ['Transactor RWA', 'Revolver RWA'],
            'RWA ($B)': [
                df['transactor_rwa_b'].sum() / 1e9,
                df['revolver_rwa_b'].sum() / 1e9
            ]
        })
        
        fig = px.pie(
            rwa_composition,
            values='RWA ($B)',
            names='Type',
            title='RWA Composition: Transactor vs Revolver',
            color='Type',
            color_discrete_map={'Transactor RWA': '#1B3B6F', 'Revolver RWA': '#D4AF37'}
        )
        fig.update_layout(
            title_font_size=16,
            title_font_color='#1B3B6F'
        )
        fig.update_traces(textposition='inside', textinfo='percent+value')
        st.plotly_chart(fig, use_container_width=True)

def plot_profitability_analysis(df):
    """Profitability & Performance Charts"""
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Chart 15: Revenue Components by Income Segment ($M)
        revenue_components = df.groupby('income_segment').agg({
            'interest_income_b': 'sum',
            'fee_income_b': 'sum'
        }).reset_index()
        
        revenue_components['interest_income_b'] = revenue_components['interest_income_b'] / 1e6
        revenue_components['fee_income_b'] = revenue_components['fee_income_b'] / 1e6
        
        fig = go.Figure(data=[
            go.Bar(name='Interest Income', x=revenue_components['income_segment'], 
                   y=revenue_components['interest_income_b'], marker_color='#1B3B6F'),
            go.Bar(name='Fee Income', x=revenue_components['income_segment'], 
                   y=revenue_components['fee_income_b'], marker_color='#D4AF37')
        ])
        
        fig.update_layout(
            title='Revenue Components by Income Segment',
            barmode='stack',
            title_font_size=16,
            title_font_color='#1B3B6F',
            xaxis_title='Income Segment',
            yaxis_title='Revenue ($M)',
            legend_title='Revenue Type'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Chart 16: Net Income by Behavioral Type ($M)
        ni_by_type = df.groupby('behavioral_type')['net_income_b'].sum().reset_index()
        ni_by_type['net_income_b'] = ni_by_type['net_income_b'] / 1e6
        
        fig = px.bar(
            ni_by_type,
            x='behavioral_type',
            y='net_income_b',
            title='Net Income by Behavioral Type',
            labels={'net_income_b': 'Net Income ($M)', 'behavioral_type': 'Behavioral Type'},
            color='behavioral_type',
            color_discrete_map={'Transactor': '#1B3B6F', 'Revolver': '#D4AF37'}
        )
        fig.update_layout(
            title_font_size=16,
            title_font_color='#1B3B6F',
            yaxis_title='Net Income ($M)',
            xaxis_title='Behavioral Type',
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)
    
    col3, col4 = st.columns(2)
    
    with col3:
        # Chart 17: ROE by Income Segment (%)
        roe_by_segment = df.groupby('income_segment')['roe'].mean().reset_index()
        
        fig = px.bar(
            roe_by_segment,
            x='income_segment',
            y='roe',
            title='Return on Equity (ROE) by Income Segment',
            labels={'roe': 'ROE (%)', 'income_segment': 'Income Segment'},
            color='roe',
            color_continuous_scale='RdYlGn'
        )
        fig.update_layout(
            title_font_size=16,
            title_font_color='#1B3B6F',
            yaxis_tickformat='.1%',
            yaxis_title='Return on Equity (ROE) %',
            xaxis_title='Income Segment'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col4:
        # Chart 18: Expected Loss vs Net Income ($M)
        comparison = df.groupby('income_segment').agg({
            'expected_loss_b': 'sum',
            'net_income_b': 'sum'
        }).reset_index()
        
        comparison['expected_loss_b'] = comparison['expected_loss_b'] / 1e6
        comparison['net_income_b'] = comparison['net_income_b'] / 1e6
        
        fig = go.Figure(data=[
            go.Bar(name='Expected Loss', x=comparison['income_segment'], 
                   y=comparison['expected_loss_b'], marker_color='#E74C3C'),
            go.Bar(name='Net Income', x=comparison['income_segment'], 
                   y=comparison['net_income_b'], marker_color='#27AE60')
        ])
        
        fig.update_layout(
            title='Expected Loss vs Net Income by Segment',
            barmode='group',
            title_font_size=16,
            title_font_color='#1B3B6F',
            xaxis_title='Income Segment',
            yaxis_title='Amount ($M)',
            legend_title='Metric'
        )
        st.plotly_chart(fig, use_container_width=True)

def plot_optimization_scenarios(df):
    """RWA Optimization Pathway Analysis"""
    
    st.subheader("💡 RWA Optimization Pathways")
    
    # Pathway 1: Transactor Limit Reduction
    st.markdown("### Pathway 1: Transactor Credit Limit Reduction")
    
    transactors = df[df['is_transactor'] == 1].copy()
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Chart 19: Limit Reduction Impact on RWA
        reduction_scenarios = []
        for reduction_pct in [0, 0.10, 0.20, 0.30, 0.40, 0.50]:
            scenario_df = transactors.copy()
            new_limit = scenario_df['credit_limit'] * (1 - reduction_pct)
            new_unused = new_limit - scenario_df['cc_outstanding_b']
            new_ead = scenario_df['cc_outstanding_b'] + new_unused * 0.10
            new_rwa = new_ead * 1.0
            
            reduction_scenarios.append({
                'Reduction %': f"{reduction_pct*100:.0f}%",
                'Total RWA ($B)': new_rwa.sum() / 1e9,
                'RWA Saved ($M)': (transactors['total_cc_rwa_b'].sum() - new_rwa.sum()) / 1e6
            })
        
        scenario_df_plot = pd.DataFrame(reduction_scenarios)
        
        fig = px.line(
            scenario_df_plot,
            x='Reduction %',
            y='RWA Saved ($M)',
            title='Transactor Limit Reduction: RWA Savings',
            markers=True,
            line_shape='spline'
        )
        fig.update_layout(
            title_font_size=16,
            title_font_color='#1B3B6F',
            xaxis_title='Credit Limit Reduction %',
            yaxis_title='RWA Saved ($M)'
        )
        fig.update_traces(line_color='#1B3B6F', marker=dict(size=10, color='#D4AF37'))
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Chart 20: Capital Relief from Optimization
        fig = px.bar(
            scenario_df_plot,
            x='Reduction %',
            y='RWA Saved ($M)',
            title='Tier 1 Capital Relief Opportunity',
            labels={'RWA Saved ($M)': 'Capital Relief ($M)'},
            color='RWA Saved ($M)',
            color_continuous_scale='Greens'
        )
        
        # Add T1 capital line
        scenario_df_plot['T1 Capital Relief ($M)'] = scenario_df_plot['RWA Saved ($M)'] * 0.085
        
        fig.update_layout(
            title_font_size=16,
            title_font_color='#1B3B6F',
            xaxis_title='Credit Limit Reduction %',
            yaxis_title='Capital Relief ($M)'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Pathway 2: Segment Performance Analysis
    st.markdown("### Pathway 2: Income Segment Optimization")
    
    col3, col4 = st.columns(2)
    
    with col3:
        # Chart 21: RWA Efficiency by Segment (Revenue per $ RWA)
        segment_efficiency = df.groupby('income_segment').agg({
            'total_revenue_b': 'sum',
            'total_cc_rwa_b': 'sum'
        })
        segment_efficiency['revenue_per_rwa'] = (
            segment_efficiency['total_revenue_b'] / segment_efficiency['total_cc_rwa_b']
        ).round(4)
        
        fig = px.bar(
            segment_efficiency.reset_index(),
            x='income_segment',
            y='revenue_per_rwa',
            title='Revenue Efficiency: Revenue per $ of RWA',
            labels={'revenue_per_rwa': 'Revenue per $ RWA', 'income_segment': 'Income Segment'},
            color='revenue_per_rwa',
            color_continuous_scale='Viridis'
        )
        fig.update_layout(
            title_font_size=16,
            title_font_color='#1B3B6F',
            xaxis_title='Income Segment',
            yaxis_title='Revenue per $ RWA'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col4:
        # Chart 22: Optimization Eligibility (Accounts)
        optimization_stats = pd.DataFrame({
            'Category': [
                'Eligible for\nLimit Reduction',
                'Eligible for\nOverdraft Conversion',
                'All Other\nAccounts'
            ],
            'Accounts': [
                df['eligible_for_limit_reduction'].sum(),
                df['eligible_for_overdraft_conversion'].sum(),
                len(df) - df['eligible_for_limit_reduction'].sum()
            ]
        })
        
        fig = px.pie(
            optimization_stats,
            values='Accounts',
            names='Category',
            title='RWA Optimization Eligibility',
            color_discrete_sequence=['#1B3B6F', '#D4AF37', '#9CA3AF']
        )
        fig.update_layout(
            title_font_size=16,
            title_font_color='#1B3B6F'
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)

def plot_rwa_reduction_analysis(df):
    """Comprehensive RWA Reduction Analysis Charts"""
    
    st.header("📉 RWA Reduction Analysis - Multi-Level Breakdown")
    
    # Calculate baseline and optimized scenarios
    baseline_rwa = df['total_cc_rwa_b'].sum()
    
    # Scenario: 30% transactor limit reduction
    transactors = df[df['is_transactor'] == 1].copy()
    reduction_pct = 0.30
    
    trans_new_limit = transactors['credit_limit'] * (1 - reduction_pct)
    trans_new_unused = (trans_new_limit - transactors['cc_outstanding_b']).clip(lower=0)
    trans_new_ead = transactors['cc_outstanding_b'] + trans_new_unused * 0.10
    trans_new_rwa = trans_new_ead * 1.0
    
    transactors['rwa_optimized'] = trans_new_rwa
    transactors['rwa_reduction'] = transactors['total_cc_rwa_b'] - trans_new_rwa
    
    # Revolvers unchanged
    revolvers = df[df['is_revolver'] == 1].copy()
    revolvers['rwa_optimized'] = revolvers['total_cc_rwa_b']
    revolvers['rwa_reduction'] = 0
    
    # Combined optimized portfolio
    df_optimized = pd.concat([transactors, revolvers])
    
    # Chart Set 1: Overall RWA Reduction
    st.subheader("1️⃣ Overall Portfolio RWA Reduction")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Chart 1A: Total RWA - Before vs After
        total_comparison = pd.DataFrame({
            'Scenario': ['Current RWA', 'Post-Optimization RWA', 'RWA Reduction'],
            'Amount ($M)': [
                baseline_rwa / 1e6,
                df_optimized['rwa_optimized'].sum() / 1e6,
                (baseline_rwa - df_optimized['rwa_optimized'].sum()) / 1e6
            ]
        })
        
        fig = go.Figure(data=[
            go.Bar(
                x=total_comparison['Scenario'],
                y=total_comparison['Amount ($M)'],
                text=total_comparison['Amount ($M)'].round(1),
                textposition='outside',
                marker_color=['#1B3B6F', '#4A90E2', '#27AE60']
            )
        ])
        
        fig.update_layout(
            title='Total RWA: Current vs Post-Optimization',
            title_font_size=16,
            title_font_color='#1B3B6F',
            xaxis_title='Scenario',
            yaxis_title='RWA ($M)',
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Chart 1B: RWA Reduction Waterfall
        waterfall_values = [
            baseline_rwa / 1e6,
            -(baseline_rwa - df_optimized['rwa_optimized'].sum()) / 1e6,
            df_optimized['rwa_optimized'].sum() / 1e6
        ]
        
        fig = go.Figure(go.Waterfall(
            x=['Current RWA', 'Transactor\nOptimization', 'Post-Opt RWA'],
            y=waterfall_values,
            measure=['absolute', 'relative', 'total'],
            text=[f"${abs(v):.1f}M" for v in waterfall_values],
            textposition='outside',
            connector={'line': {'color': '#6B7280'}},
            decreasing={'marker': {'color': '#27AE60'}},
            increasing={'marker': {'color': '#E74C3C'}},
            totals={'marker': {'color': '#1B3B6F'}}
        ))
        
        fig.update_layout(
            title='RWA Reduction Waterfall',
            title_font_size=16,
            title_font_color='#1B3B6F',
            yaxis_title='RWA ($M)',
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Chart Set 2: RWA Reduction by Income Segment
    st.subheader("2️⃣ RWA Reduction by Income Segment")
    
    col3, col4 = st.columns(2)
    
    with col3:
        # Chart 2A: RWA Reduction Amount by Segment
        segment_reduction = df_optimized.groupby('income_segment').agg({
            'total_cc_rwa_b': 'sum',
            'rwa_optimized': 'sum',
            'rwa_reduction': 'sum'
        }).reset_index()
        
        segment_reduction['total_cc_rwa_b'] = segment_reduction['total_cc_rwa_b'] / 1e6
        segment_reduction['rwa_optimized'] = segment_reduction['rwa_optimized'] / 1e6
        segment_reduction['rwa_reduction'] = segment_reduction['rwa_reduction'] / 1e6
        
        fig = go.Figure(data=[
            go.Bar(name='Current RWA', x=segment_reduction['income_segment'], 
                   y=segment_reduction['total_cc_rwa_b'], marker_color='#1B3B6F'),
            go.Bar(name='Post-Optimization RWA', x=segment_reduction['income_segment'], 
                   y=segment_reduction['rwa_optimized'], marker_color='#4A90E2')
        ])
        
        fig.update_layout(
            title='RWA by Income Segment: Before vs After',
            barmode='group',
            title_font_size=16,
            title_font_color='#1B3B6F',
            xaxis_title='Income Segment',
            yaxis_title='RWA ($M)',
            legend_title='Scenario'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col4:
        # Chart 2B: RWA Reduction % by Segment
        segment_reduction['reduction_pct'] = (
            segment_reduction['rwa_reduction'] / segment_reduction['total_cc_rwa_b'] * 100
        )
        
        fig = px.bar(
            segment_reduction,
            x='income_segment',
            y='reduction_pct',
            title='RWA Reduction % by Income Segment',
            labels={'reduction_pct': 'RWA Reduction (%)', 'income_segment': 'Income Segment'},
            color='reduction_pct',
            color_continuous_scale='Greens',
            text='reduction_pct'
        )
        
        fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        fig.update_layout(
            title_font_size=16,
            title_font_color='#1B3B6F',
            xaxis_title='Income Segment',
            yaxis_title='RWA Reduction (%)'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Chart Set 3: RWA Reduction by Behavioral Type
    st.subheader("3️⃣ RWA Reduction by Behavioral Type")
    
    col5, col6 = st.columns(2)
    
    with col5:
        # Chart 3A: RWA Reduction by Behavioral Type
        behavioral_reduction = df_optimized.groupby('behavioral_type').agg({
            'total_cc_rwa_b': 'sum',
            'rwa_optimized': 'sum',
            'rwa_reduction': 'sum'
        }).reset_index()
        
        behavioral_reduction['total_cc_rwa_b'] = behavioral_reduction['total_cc_rwa_b'] / 1e6
        behavioral_reduction['rwa_optimized'] = behavioral_reduction['rwa_optimized'] / 1e6
        behavioral_reduction['rwa_reduction'] = behavioral_reduction['rwa_reduction'] / 1e6
        
        fig = go.Figure(data=[
            go.Bar(name='Current RWA', x=behavioral_reduction['behavioral_type'], 
                   y=behavioral_reduction['total_cc_rwa_b'], marker_color='#1B3B6F'),
            go.Bar(name='RWA Reduction', x=behavioral_reduction['behavioral_type'], 
                   y=behavioral_reduction['rwa_reduction'], marker_color='#27AE60')
        ])
        
        fig.update_layout(
            title='RWA Reduction Amount by Behavioral Type',
            barmode='group',
            title_font_size=16,
            title_font_color='#1B3B6F',
            xaxis_title='Behavioral Type',
            yaxis_title='RWA ($M)',
            legend_title='Metric'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col6:
        # Chart 3B: Contribution to Total RWA Reduction
        behavioral_reduction['contribution_pct'] = (
            behavioral_reduction['rwa_reduction'] / behavioral_reduction['rwa_reduction'].sum() * 100
        )
        
        fig = px.pie(
            behavioral_reduction,
            values='rwa_reduction',
            names='behavioral_type',
            title='Contribution to Total RWA Reduction',
            color_discrete_map={'Transactor': '#1B3B6F', 'Revolver': '#D4AF37'}
        )
        
        fig.update_layout(
            title_font_size=16,
            title_font_color='#1B3B6F'
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)
    
    # Chart Set 4: RWA Reduction by FICO Tier
    st.subheader("4️⃣ RWA Reduction by FICO Risk Tier")
    
    col7, col8 = st.columns(2)
    
    with col7:
        # Chart 4A: RWA Reduction by FICO Tier
        fico_reduction = df_optimized.groupby('fico_tier').agg({
            'total_cc_rwa_b': 'sum',
            'rwa_reduction': 'sum'
        }).reset_index()
        
        fico_reduction['total_cc_rwa_b'] = fico_reduction['total_cc_rwa_b'] / 1e6
        fico_reduction['rwa_reduction'] = fico_reduction['rwa_reduction'] / 1e6
        fico_reduction['reduction_pct'] = (
            fico_reduction['rwa_reduction'] / fico_reduction['total_cc_rwa_b'] * 100
        )
        
        fig = px.bar(
            fico_reduction,
            x='fico_tier',
            y='rwa_reduction',
            title='RWA Reduction Amount by FICO Risk Tier',
            labels={'rwa_reduction': 'RWA Reduction ($M)', 'fico_tier': 'FICO Risk Tier'},
            color='rwa_reduction',
            color_continuous_scale='Blues',
            text='rwa_reduction'
        )
        
        fig.update_traces(texttemplate='$%{text:.1f}M', textposition='outside')
        fig.update_layout(
            title_font_size=16,
            title_font_color='#1B3B6F',
            xaxis_title='FICO Risk Tier',
            yaxis_title='RWA Reduction ($M)'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col8:
        # Chart 4B: RWA Reduction % by FICO Tier
        fig = px.line(
            fico_reduction,
            x='fico_tier',
            y='reduction_pct',
            title='RWA Reduction % by FICO Risk Tier',
            labels={'reduction_pct': 'RWA Reduction (%)', 'fico_tier': 'FICO Risk Tier'},
            markers=True,
            line_shape='spline'
        )
        
        fig.update_traces(line_color='#1B3B6F', marker=dict(size=12, color='#D4AF37'))
        fig.update_layout(
            title_font_size=16,
            title_font_color='#1B3B6F',
            xaxis_title='FICO Risk Tier',
            yaxis_title='RWA Reduction (%)'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Chart Set 5: RWA Reduction by Region
    st.subheader("5️⃣ RWA Reduction by Geographic Region")
    
    col9, col10 = st.columns(2)
    
    with col9:
        # Chart 5A: RWA Reduction by Region
        region_reduction = df_optimized.groupby('region').agg({
            'total_cc_rwa_b': 'sum',
            'rwa_reduction': 'sum'
        }).reset_index()
        
        region_reduction['total_cc_rwa_b'] = region_reduction['total_cc_rwa_b'] / 1e6
        region_reduction['rwa_reduction'] = region_reduction['rwa_reduction'] / 1e6
        
        fig = go.Figure(data=[
            go.Bar(name='Current RWA', x=region_reduction['region'], 
                   y=region_reduction['total_cc_rwa_b'], marker_color='#1B3B6F', opacity=0.7),
            go.Bar(name='RWA Reduction', x=region_reduction['region'], 
                   y=region_reduction['rwa_reduction'], marker_color='#27AE60')
        ])
        
        fig.update_layout(
            title='RWA Reduction by Geographic Region',
            barmode='group',
            title_font_size=16,
            title_font_color='#1B3B6F',
            xaxis_title='Region',
            yaxis_title='RWA ($M)',
            legend_title='Metric'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col10:
        # Chart 5B: Regional Contribution to RWA Reduction
        region_reduction['contribution_pct'] = (
            region_reduction['rwa_reduction'] / region_reduction['rwa_reduction'].sum() * 100
        )
        
        fig = px.bar(
            region_reduction.sort_values('contribution_pct', ascending=False),
            x='region',
            y='contribution_pct',
            title='Regional Contribution to Total RWA Reduction',
            labels={'contribution_pct': 'Contribution (%)', 'region': 'Region'},
            color='contribution_pct',
            color_continuous_scale='Viridis',
            text='contribution_pct'
        )
        
        fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        fig.update_layout(
            title_font_size=16,
            title_font_color='#1B3B6F',
            xaxis_title='Region',
            yaxis_title='Contribution to Total Reduction (%)'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Chart Set 6: Capital Relief Analysis
    st.subheader("6️⃣ Tier 1 Capital Relief Analysis")
    
    col11, col12 = st.columns(2)
    
    with col11:
        # Chart 6A: Capital Relief by Segment
        segment_capital_relief = segment_reduction.copy()
        segment_capital_relief['tier1_relief'] = segment_capital_relief['rwa_reduction'] * 0.085
        
        fig = px.bar(
            segment_capital_relief,
            x='income_segment',
            y='tier1_relief',
            title='Tier 1 Capital Relief by Income Segment',
            labels={'tier1_relief': 'T1 Capital Relief ($M)', 'income_segment': 'Income Segment'},
            color='tier1_relief',
            color_continuous_scale='Greens',
            text='tier1_relief'
        )
        
        fig.update_traces(texttemplate='$%{text:.1f}M', textposition='outside')
        fig.update_layout(
            title_font_size=16,
            title_font_color='#1B3B6F',
            xaxis_title='Income Segment',
            yaxis_title='Tier 1 Capital Relief ($M)'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col12:
        # Chart 6B: Combined Segment + Behavioral Analysis (Sunburst)
        combo_reduction = df_optimized.groupby(['income_segment', 'behavioral_type']).agg({
            'rwa_reduction': 'sum'
        }).reset_index()
        combo_reduction['rwa_reduction'] = combo_reduction['rwa_reduction'] / 1e6
        
        fig = px.sunburst(
            combo_reduction,
            path=['income_segment', 'behavioral_type'],
            values='rwa_reduction',
            title='RWA Reduction: Income Segment → Behavioral Type',
            color='rwa_reduction',
            color_continuous_scale='Blues'
        )
        
        fig.update_layout(
            title_font_size=16,
            title_font_color='#1B3B6F'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Summary Statistics
    st.markdown("---")
    st.subheader("📊 RWA Reduction Summary Statistics")
    
    summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)
    
    total_reduction = (baseline_rwa - df_optimized['rwa_optimized'].sum()) / 1e6
    reduction_pct = (total_reduction / (baseline_rwa / 1e6)) * 100
    
    with summary_col1:
        st.metric("Total RWA Reduction", f"${total_reduction:.1f}M", f"-{reduction_pct:.1f}%")
    
    with summary_col2:
        st.metric("Tier 1 Capital Relief", f"${total_reduction * 0.085:.1f}M", "8.5% of reduction")
    
    with summary_col3:
        accounts_impacted = df_optimized[df_optimized['rwa_reduction'] > 0].shape[0]
        st.metric("Accounts Impacted", f"{accounts_impacted:,}", f"{accounts_impacted/len(df)*100:.1f}% of portfolio")
    
    with summary_col4:
        avg_reduction_per_account = total_reduction * 1e6 / max(accounts_impacted, 1)
        st.metric("Avg RWA Reduction/Account", f"${avg_reduction_per_account:.0f}", "For impacted accounts")

# ============================================================================
# MAIN DASHBOARD
# ============================================================================

def main():
    """Main Profit Insight dashboard application"""
    
    # Header
    st.markdown("""
    <div style='text-align: center; padding: 20px 0;'>
        <h1 style='font-size: 42px; color: #1B3B6F; margin: 0;'>
            PROFIT INSIGHT BASEL RWA ANALYTICS
        </h1>
        <p style='font-size: 18px; color: #6B7280; margin: 10px 0;'>
            PNC Bank Credit Card Portfolio | US Standardized Approach
        </p>
        <p style='font-size: 14px; color: #9CA3AF; margin: 5px 0;'>
            Regulatory Capital & Risk-Weighted Asset Optimization Platform
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Load data
    df = load_data()
    
    # Sidebar filters
    filters = create_sidebar_filters(df)
    
    # Apply filters and stress
    df_filtered = apply_filters_and_stress(df, filters)
    
    # Stress mode indicator
    if filters['stress_mode']:
        st.warning(
            f"📊 **Stress Scenario Active: {filters['scenario_type']}** | "
            f"PD Stress: {filters['pd_stress']:.1f}x | "
            f"NCO Stress: {filters['nco_stress']:.1f}x | "
            f"GDP Impact: {filters['macro_stress']:.2f}x"
        )
    
    # Calculate RWA Reduction Potential
    rwa_reduction = calculate_rwa_reduction(df_filtered)
    
    # Key Performance Indicators
    st.subheader("📊 Portfolio Key Performance Indicators")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            "Total Accounts",
            f"{len(df_filtered):,}",
            f"{(len(df_filtered)/len(df)*100):.1f}% of portfolio"
        )
    
    with col2:
        total_ead = df_filtered['ead_b'].sum()
        baseline_ead = df['ead_b'].sum()
        st.metric(
            "Total EAD",
            format_currency(total_ead),
            f"{((total_ead - baseline_ead)/baseline_ead*100):.1f}% vs base" if filters['stress_mode'] else None
        )
    
    with col3:
        total_rwa = df_filtered['total_cc_rwa_b'].sum()
        baseline_rwa = df['total_cc_rwa_b'].sum()
        st.metric(
            "Total RWA",
            format_currency(total_rwa),
            f"{((total_rwa - baseline_rwa)/baseline_rwa*100):.1f}% vs base" if filters['stress_mode'] else None
        )
    
    with col4:
        st.metric(
            "RWA Reduction Potential",
            format_currency(rwa_reduction['total_rwa_reduction']),
            f"-{rwa_reduction['reduction_pct']:.1f}% achievable",
            delta_color="inverse"
        )
    
    with col5:
        st.metric(
            "T1 Capital Relief",
            format_currency(rwa_reduction['tier1_relief']),
            f"From RWA optimization",
            delta_color="normal"
        )
    
    st.markdown("---")
    
    # Additional KPI Row - RWA Reduction Breakdown
    col6, col7, col8, col9, col10 = st.columns(5)
    
    with col6:
        st.metric(
            "Current RWA Density",
            "100.0%",
            "US SA Fixed Rate"
        )
    
    with col7:
        st.metric(
            "Pathway 1: Transactor",
            format_currency(rwa_reduction['transactor_pathway']),
            "Limit Reduction (30%)"
        )
    
    with col8:
        st.metric(
            "Pathway 2: Overdraft",
            format_currency(rwa_reduction['overdraft_pathway']),
            "Conversion & Netting"
        )
    
    with col9:
        eligible_pct = (df_filtered['eligible_for_limit_reduction'].sum() / len(df_filtered)) * 100
        st.metric(
            "Optimization Eligible",
            f"{df_filtered['eligible_for_limit_reduction'].sum():,}",
            f"{eligible_pct:.1f}% of portfolio"
        )
    
    with col10:
        avg_pd = df_filtered['pd'].mean()
        baseline_pd = df['pd_base'].mean()
        st.metric(
            "Avg PD",
            format_percentage(avg_pd),
            format_bps(avg_pd - baseline_pd) if filters['stress_mode'] else f"{avg_pd*10000:.0f} bps"
        )
    
    st.markdown("---")
    
    # Tab Navigation
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📊 Portfolio Overview",
        "⚠️ Risk Analytics",
        "💳 Exposure & Balances",
        "🏛️ Capital Requirements",
        "💰 Profitability",
        "🎯 RWA Optimization",
        "📉 RWA Reduction Analysis"
    ])
    
    with tab1:
        st.header("Portfolio Overview")
        plot_portfolio_overview(df_filtered)
    
    with tab2:
        st.header("Risk Analytics")
        plot_risk_analytics(df_filtered)
    
    with tab3:
        st.header("Exposure & Balance Analysis")
        plot_exposure_analysis(df_filtered)
    
    with tab4:
        st.header("Capital Requirements & Regulatory Metrics")
        plot_capital_requirements(df_filtered)
    
    with tab5:
        st.header("Profitability & Performance Analysis")
        plot_profitability_analysis(df_filtered)
    
    with tab6:
        st.header("RWA Optimization Pathways")
        plot_optimization_scenarios(df_filtered)
    
    with tab7:
        st.header("RWA Reduction Analysis - Multi-Level Breakdown")
        plot_rwa_reduction_analysis(df_filtered)
    
    # Footer with export options
    st.markdown("---")
    st.subheader("📥 Export & Download")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Export Filtered Portfolio (CSV)"):
            csv = df_filtered.to_csv(index=False)
            st.download_button(
                label="Download Portfolio CSV",
                data=csv,
                file_name=f"pnc_portfolio_filtered_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
    
    with col2:
        if st.button("Export Summary Report (CSV)"):
            summary = df_filtered.groupby('income_segment').agg({
                'ead_b': 'sum',
                'total_cc_rwa_b': 'sum',
                'pd': 'mean',
                'nco_rate': 'mean',
                'expected_loss_b': 'sum',
                'net_income_b': 'sum',
                'tier1_requirement_b': 'sum'
            })
            summary_csv = summary.to_csv()
            st.download_button(
                label="Download Summary CSV",
                data=summary_csv,
                file_name=f"pnc_summary_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
    
    with col3:
        st.info(f"**Filtered Data**: {len(df_filtered):,} / {len(df):,} accounts ({len(df_filtered)/len(df)*100:.1f}%)")
    
    # Profit Insight Footer
    st.markdown("""
    <div class='pi-footer'>
        <strong>PROFIT INSIGHT</strong> Basel RWA Analytics Platform<br/>
        PNC Bank Credit Card Portfolio Analysis | US Standardized Approach (12 CFR Part 3)<br/>
        Dashboard Version 1.0 | Last Updated: {date}<br/>
        <em>Proprietary & Confidential</em>
    </div>
    """.format(date=datetime.now().strftime('%Y-%m-%d')), unsafe_allow_html=True)
    
    # Sidebar info
    st.sidebar.markdown("---")
    st.sidebar.info(
        f"**Dashboard Info**\n\n"
        f"- Filtered Accounts: {len(df_filtered):,}\n"
        f"- Total Portfolio: {len(df):,}\n"
        f"- Stress Scenario: {filters['scenario_type']}\n"
        f"- Last Refresh: {datetime.now().strftime('%H:%M:%S')}\n\n"
        f"*Powered by Profit Insight*"
    )

if __name__ == "__main__":
    main()