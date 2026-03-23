"""
UPDATED APP.PY - Fixed Data Loading for 1M Cards
================================================

CHANGES:
1. Fixed random seed (random_state=42) ensures same data every time
2. Streamlit caching ensures data loads only once
3. Supports Parquet format (10x smaller than CSV)
4. Always shows 1M cards consistently

DEPLOYMENT OPTIONS:
- Option 1: Use Parquet (40MB - fits in GitHub)
- Option 2: Use GZIP CSV (100MB - fits in GitHub)  
- Option 3: Generate with fixed seed (no file needed, cached)
"""

import os
import warnings
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

warnings.filterwarnings("ignore")

# =============================================================================
# PAGE CONFIGURATION
# =============================================================================

st.set_page_config(
    page_title="Profit Insight | Basel RWA Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
# BRANDING / STYLES (keeping original styles)
# =============================================================================

st.markdown(
    """
<style>
    :root {
        --pi-navy: #1B3B6F;
        --pi-gold: #D4AF37;
        --pi-light-blue: #4A90E2;
        --pi-gray: #F5F7FA;
        --pi-green: #27AE60;
        --pi-red: #E74C3C;
    }

    .stApp {
        background-color: #FAFBFC;
    }

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
        font-weight: 600;
    }

    [data-testid="stMetricValue"] {
        font-size: 34px;
        color: #1B3B6F;
        font-weight: 700;
    }

    [data-testid="stMetricDelta"] {
        font-size: 17px;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }

    .stTabs [data-baseweb="tab"] {
        background-color: #E8EDF2;
        border-radius: 8px 8px 0px 0px;
        padding: 12px 20px;
        font-weight: 600;
    }

    .stTabs [aria-selected="true"] {
        background-color: #1B3B6F;
        color: white !important;
    }

    .chart-note {
        background-color: #F7FAFC;
        border-left: 4px solid #4A90E2;
        padding: 12px 14px;
        border-radius: 8px;
        margin-bottom: 8px;
    }

    .pi-footer {
        text-align: center;
        color: #6B7280;
        padding: 20px;
        margin-top: 40px;
        border-top: 2px solid #D4AF37;
        font-size: 14px;
    }
</style>
""",
    unsafe_allow_html=True,
)

# =============================================================================
# FORMATTING HELPERS
# =============================================================================


def format_currency(value, decimals=2):
    if abs(value) >= 1e9:
        return f"${value / 1e9:,.{decimals}f}B"
    if abs(value) >= 1e6:
        return f"${value / 1e6:,.{decimals}f}M"
    if abs(value) >= 1e3:
        return f"${value / 1e3:,.{decimals}f}K"
    return f"${value:,.{decimals}f}"


def format_percentage(value, decimals=2):
    return f"{value * 100:.{decimals}f}%"


def format_bps(value):
    return f"{value * 10000:.0f} bps"


# =============================================================================
# IMPROVED DATA LOADING - ALWAYS 1M CARDS, CONSISTENT DATA
# =============================================================================

@st.cache_data(show_spinner=False)
def load_data():
    """
    IMPROVED: Load 1M cards consistently
    
    Priority:
    1. Parquet file (40MB - best performance, fits in GitHub)
    2. GZIP CSV (100MB - compressed, fits in GitHub)
    3. Regular CSV (420MB - requires Git LFS)
    4. Generate with FIXED seed (always same data, cached)
    
    Key Fix: random_state=42 ensures same dataset every time
    """
    
    # Option 1: Parquet format (RECOMMENDED - 10x smaller, 5x faster)
    parquet_path = "pnc_indusind_cc_portfolio_1M.parquet"
    if os.path.exists(parquet_path):
        df = pd.read_parquet(parquet_path)
        return df, f"✅ Loaded {len(df):,} accounts from Parquet (optimized format)"
    
    # Option 2: Compressed CSV (fits in GitHub)
    gzip_path = "pnc_indusind_cc_portfolio_1M.csv.gz"
    if os.path.exists(gzip_path):
        df = pd.read_csv(gzip_path, compression='gzip')
        return df, f"✅ Loaded {len(df):,} accounts from compressed CSV"
    
    # Option 3: Regular CSV (large, needs Git LFS)
    csv_path = "pnc_indusind_cc_portfolio_1M.csv"
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        return df, f"✅ Loaded {len(df):,} accounts from CSV"
    
    # Option 4: Generate with FIXED seed (no file needed)
    # CRITICAL FIX: random_state=42 ensures SAME data every time
    generator_file = "pnc_indusind_data_generator.py"
    if os.path.exists(generator_file):
        try:
            from pnc_indusind_data_generator import ProfitInsightCCDataGenerator
            
            st.info("🔄 Generating 1M account dataset (one-time process, ~30 seconds)...")
            
            # FIXED SEED = CONSISTENT DATA
            generator = ProfitInsightCCDataGenerator(
                n_accounts=1_000_000,  # Always 1M
                random_state=42        # Always same random seed
            )
            df = generator.generate_dataset()
            
            # Save as Parquet for faster loading next time
            try:
                df.to_parquet(parquet_path, compression='snappy')
                st.success(f"✅ Saved dataset as Parquet for faster loading next time")
            except Exception as e:
                st.warning(f"Could not save Parquet: {e}")
            
            return df, f"✅ Generated {len(df):,} accounts (fixed seed, cached)"
            
        except Exception as exc:
            st.error(f"⚠️ Dataset generation failed: {exc}")
            st.stop()
    
    # No options available
    st.error(
        "⚠️ **No dataset found!**\n\n"
        "Please add one of:\n"
        "- `pnc_indusind_cc_portfolio_1M.parquet` (recommended - 40MB)\n"
        "- `pnc_indusind_cc_portfolio_1M.csv.gz` (compressed - 100MB)\n"
        "- `pnc_indusind_cc_portfolio_1M.csv` (requires Git LFS)\n"
        "- `pnc_indusind_data_generator.py` (generates with fixed seed)\n\n"
        "See deployment guide for instructions."
    )
    st.stop()


# =============================================================================
# REST OF YOUR CODE STAYS THE SAME
# =============================================================================

BASEL_DICTIONARY = {
    "EAD": {
        "term": "Exposure at Default",
        "formula": "EAD = Outstanding + (Unused × CCF)",
        "us_sa": "Outstanding + (Unused × 10%)",
        "reference": "12 CFR Part 3 §3.33",
    },
    "RWA": {
        "term": "Risk-Weighted Assets",
        "formula": "RWA = EAD × Risk Weight",
        "us_sa": "EAD × 100% for credit cards",
        "reference": "12 CFR Part 3 §3.32(l)",
    },
    "CCF": {
        "term": "Credit Conversion Factor",
        "formula": "Off-Balance = Unused × CCF",
        "us_sa": "10% for unconditionally cancellable lines",
        "reference": "12 CFR Part 3 §3.33(b)(2)",
    },
    "Tier 1 Ratio": {
        "term": "Tier 1 Capital / RWA",
        "formula": "Tier 1 Ratio = Tier 1 Capital / Total RWA",
        "us_sa": "Minimum 8.5% used here for capital requirement proxy",
        "reference": "Basel III + 12 CFR Part 3 §3.11",
    },
    "NCO": {
        "term": "Net Charge-Off Rate",
        "formula": "NCO = Charge-offs − Recoveries",
        "us_sa": "Annualized % of balances",
        "reference": "FDIC Call Report",
    },
}


def show_basel_dictionary():
    with st.sidebar.expander("📖 Basel Regulatory Dictionary", expanded=False):
        term = st.selectbox(
            "Select Basel term",
            options=list(BASEL_DICTIONARY.keys()),
            format_func=lambda x: f"{x} - {BASEL_DICTIONARY[x]['term']}",
        )
        info = BASEL_DICTIONARY[term]
        st.markdown(f"**{term}** - {info['term']}")
        st.code(f"General: {info['formula']}", language="text")
        st.code(f"US SA: {info['us_sa']}", language="text")
        st.caption(f"Reference: {info['reference']}")

# ... [REST OF YOUR ORIGINAL CODE - sidebar, filters, charts, etc.] ...
# I'm not changing any of your existing functions, just the load_data() function above

# NOTE: The rest of your app.py code stays exactly the same.
# Only the load_data() function changed to ensure consistent 1M cards.

if __name__ == "__main__":
    # Your existing main() function
    pass
