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
    page_title="Profit Insight | Basel RWA Analytics- Credit Cards",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
# BRANDING / STYLES
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
# DATA LOADING
# =============================================================================


@st.cache_data(show_spinner=False)
def load_data():
    from pnc_indusind_data_generator import ProfitInsightCCDataGenerator
    
    # FIXED SEED = SAME DATA EVERY TIME
    generator = ProfitInsightCCDataGenerator(
        n_accounts=1_000_000,
        random_state=42  # Critical!
    )
    df = generator.generate_dataset()
    return df, f"✅ Generated {len(df):,} accounts (cached)"
# =============================================================================
# BASEL DICTIONARY
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


# =============================================================================
# SIDEBAR
# =============================================================================


def create_sidebar_filters(df):
    st.sidebar.markdown(
        """
        <div style='text-align: center; padding: 20px 0;'>
            <h1 style='color: #D4AF37; font-size: 24px; margin: 0;'>PROFIT INSIGHT</h1>
            <p style='color: #9CA3AF; font-size: 12px; margin: 5px 0;'>Basel RWA Analytics Platform</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.markdown("---")

    st.sidebar.title("📊 Stress Testing")
    stress_mode = st.sidebar.checkbox("Enable Stress Scenarios", value=False)

    if stress_mode:
        scenario_type = st.sidebar.selectbox(
            "Pre-defined Scenario",
            ["Custom", "Baseline", "Mild Recession", "Severe Recession", "Financial Crisis"],
        )

        if scenario_type == "Baseline":
            pd_stress, nco_stress, macro_stress = 1.0, 1.0, 1.0
        elif scenario_type == "Mild Recession":
            pd_stress, nco_stress, macro_stress = 1.5, 1.3, 0.95
        elif scenario_type == "Severe Recession":
            pd_stress, nco_stress, macro_stress = 2.5, 2.0, 0.85
        elif scenario_type == "Financial Crisis":
            pd_stress, nco_stress, macro_stress = 4.0, 3.5, 0.70
        else:
            pd_stress = st.sidebar.slider("PD Stress Factor", 0.5, 5.0, 1.0, 0.1)
            nco_stress = st.sidebar.slider("NCO Stress Factor", 0.5, 5.0, 1.0, 0.1)
            macro_stress = st.sidebar.slider("GDP Impact", 0.5, 1.2, 1.0, 0.05)
    else:
        scenario_type = "Baseline"
        pd_stress, nco_stress, macro_stress = 1.0, 1.0, 1.0

    st.sidebar.markdown("---")
    st.sidebar.title("🔧 Portfolio Filters")

    income_segments = st.sidebar.multiselect(
        "Income Segments",
        options=sorted(df["income_segment"].dropna().unique()),
        default=sorted(df["income_segment"].dropna().unique()),
    )

    behavioral_types = st.sidebar.multiselect(
        "Behavioral Type",
        options=sorted(df["behavioral_type"].dropna().unique()),
        default=sorted(df["behavioral_type"].dropna().unique()),
    )

    fico_tiers = st.sidebar.multiselect(
        "FICO Risk Tier",
        options=sorted(df["fico_tier"].dropna().unique()),
        default=sorted(df["fico_tier"].dropna().unique()),
    )

    regions = st.sidebar.multiselect(
        "Geographic Region",
        options=sorted(df["region"].dropna().unique()),
        default=sorted(df["region"].dropna().unique()),
    )

    card_types = st.sidebar.multiselect(
        "Card Type",
        options=sorted(df["card_type"].dropna().unique()),
        default=sorted(df["card_type"].dropna().unique()),
    )

    vintage_range = st.sidebar.slider(
        "Account Vintage (Months)",
        min_value=int(df["vintage_months"].min()),
        max_value=int(df["vintage_months"].max()),
        value=(int(df["vintage_months"].min()), int(df["vintage_months"].max())),
    )

    fico_range = st.sidebar.slider(
        "FICO Score Range",
        min_value=int(df["fico_score"].min()),
        max_value=int(df["fico_score"].max()),
        value=(int(df["fico_score"].min()), int(df["fico_score"].max())),
    )

    st.sidebar.markdown("---")
    show_basel_dictionary()

    return {
        "stress_mode": stress_mode,
        "scenario_type": scenario_type,
        "pd_stress": pd_stress,
        "nco_stress": nco_stress,
        "macro_stress": macro_stress,
        "income_segments": income_segments,
        "behavioral_types": behavioral_types,
        "fico_tiers": fico_tiers,
        "regions": regions,
        "card_types": card_types,
        "vintage_range": vintage_range,
        "fico_range": fico_range,
    }


# =============================================================================
# FILTER / STRESS
# =============================================================================


def apply_filters_and_stress(df, filters):
    df_filtered = df.copy()

    if filters["stress_mode"]:
        df_filtered["pd"] = df_filtered["pd_base"] * filters["pd_stress"]
        df_filtered["nco_rate"] = df_filtered["nco_rate"] * filters["nco_stress"]
        df_filtered["expected_loss_b"] = (
            df_filtered["ead_b"] * df_filtered["pd"] * df_filtered["lgd"]
        )
        df_filtered["net_income_b"] = (
            df_filtered["total_revenue_b"]
            - df_filtered["funding_cost_b"]
            - df_filtered["operating_expense_b"]
            - df_filtered["expected_loss_b"]
        )
        df_filtered["roa"] = (
            df_filtered["net_income_b"] * 12 / df_filtered["ead_b"].replace(0, 1)
        )
        df_filtered["roe"] = (
            df_filtered["net_income_b"] * 12
            / (df_filtered["total_cc_rwa_b"] * 0.085).replace(0, 1)
        )

    df_filtered = df_filtered[
        (df_filtered["income_segment"].isin(filters["income_segments"]))
        & (df_filtered["behavioral_type"].isin(filters["behavioral_types"]))
        & (df_filtered["fico_tier"].isin(filters["fico_tiers"]))
        & (df_filtered["region"].isin(filters["regions"]))
        & (df_filtered["card_type"].isin(filters["card_types"]))
        & (df_filtered["vintage_months"] >= filters["vintage_range"][0])
        & (df_filtered["vintage_months"] <= filters["vintage_range"][1])
        & (df_filtered["fico_score"] >= filters["fico_range"][0])
        & (df_filtered["fico_score"] <= filters["fico_range"][1])
    ].copy()

    return df_filtered


# =============================================================================
# OPTIMIZATION / FINAL RWA
# =============================================================================


def calculate_rwa_reduction(df):
    transactors = df[df["is_transactor"] == 1].copy()
    reduction_pct = 0.30

    if len(transactors) > 0:
        new_limit = transactors["credit_limit"] * (1 - reduction_pct)
        new_unused = (new_limit - transactors["cc_outstanding_b"]).clip(lower=0)
        new_ead = transactors["cc_outstanding_b"] + new_unused * 0.10
        new_rwa_transactor = new_ead * 1.0
        rwa_saved_transactor = (
            transactors["total_cc_rwa_b"].sum() - new_rwa_transactor.sum()
        )
    else:
        rwa_saved_transactor = 0.0

    eligible_od = df[df["eligible_for_overdraft_conversion"] == 1].copy()
    if len(eligible_od) > 0:
        od_conversion_rate = 0.20
        netting_coverage = 0.80
        od_accounts = eligible_od.sample(
            frac=min(od_conversion_rate, 1.0), random_state=42
        )
        od_ead_reduction = od_accounts["ead_b"].sum() * netting_coverage
        rwa_saved_overdraft = od_ead_reduction * 1.0
    else:
        rwa_saved_overdraft = 0.0

    total_rwa = df["total_cc_rwa_b"].sum()
    total_rwa_reduction = max(rwa_saved_transactor + rwa_saved_overdraft, 0.0)
    final_rwa = max(total_rwa - total_rwa_reduction, 0.0)
    tier1_relief = total_rwa_reduction * 0.085

    return {
        "current_rwa": total_rwa,
        "total_rwa_reduction": total_rwa_reduction,
        "transactor_pathway": rwa_saved_transactor,
        "overdraft_pathway": rwa_saved_overdraft,
        "final_rwa": final_rwa,
        "tier1_relief": tier1_relief,
        "reduction_pct": (total_rwa_reduction / total_rwa * 100) if total_rwa else 0.0,
    }


# =============================================================================
# CHART EXPLAINER HELPER
# =============================================================================


def render_chart_with_explainer(
    fig,
    expander_title,
    x_axis_text,
    y_axis_text,
    interpretation_text,
    insight_text,
):
    st.plotly_chart(fig, use_container_width=True)
    with st.expander(f"📘 {expander_title}", expanded=False):
        st.markdown(f"**X-axis:** {x_axis_text}")
        st.markdown(f"**Y-axis:** {y_axis_text}")
        st.markdown(f"**How to read this:** {interpretation_text}")
        st.markdown(f"**What this shows:** {insight_text}")


# =============================================================================
# CHARTS
# =============================================================================


def plot_rwa_summary_charts(df, rwa_reduction):
    st.subheader("Current vs Final RWA Snapshot")

    col1, col2 = st.columns(2)

    with col1:
        summary_df = pd.DataFrame(
            {
                "Metric": ["Current RWA", "Target / Final RWA", "RWA Reduction"],
                "Amount": [
                    rwa_reduction["current_rwa"] / 1e6,
                    rwa_reduction["final_rwa"] / 1e6,
                    rwa_reduction["total_rwa_reduction"] / 1e6,
                ],
            }
        )

        fig = go.Figure(
            data=[
                go.Bar(
                    x=summary_df["Metric"],
                    y=summary_df["Amount"],
                    text=summary_df["Amount"].round(1),
                    textposition="outside",
                )
            ]
        )
        fig.update_layout(
            title="Current RWA vs Final RWA",
            xaxis_title="Scenario",
            yaxis_title="RWA ($M)",
            title_font_color="#1B3B6F",
        )

        render_chart_with_explainer(
            fig,
            "Current RWA vs Final RWA explanation",
            "Scenario buckets: current portfolio RWA, optimized/final RWA, and reduction amount.",
            "Risk-weighted assets measured in millions of dollars.",
            "Higher bars mean more capital-consuming exposure. The gap between current and final shows the optimization benefit.",
            "This chart answers the basic business question: how much RWA exists now, how much can be removed, and where the portfolio lands after reduction.",
        )

    with col2:
        fig = go.Figure(
            go.Waterfall(
                x=["Current RWA", "Optimization Benefit", "Final RWA"],
                y=[
                    rwa_reduction["current_rwa"] / 1e6,
                    -(rwa_reduction["total_rwa_reduction"] / 1e6),
                    rwa_reduction["final_rwa"] / 1e6,
                ],
                measure=["absolute", "relative", "total"],
                text=[
                    f"${rwa_reduction['current_rwa']/1e6:,.1f}M",
                    f"-${rwa_reduction['total_rwa_reduction']/1e6:,.1f}M",
                    f"${rwa_reduction['final_rwa']/1e6:,.1f}M",
                ],
                textposition="outside",
                connector={"line": {"color": "#6B7280"}},
            )
        )
        fig.update_layout(
            title="RWA Reduction Waterfall",
            yaxis_title="RWA ($M)",
            title_font_color="#1B3B6F",
            showlegend=False,
        )

        render_chart_with_explainer(
            fig,
            "RWA waterfall explanation",
            "The steps in the optimization story: starting point, savings, and end point.",
            "RWA in millions of dollars.",
            "The first column is the starting burden, the middle step shows what is removed, and the last bar is the final optimized level.",
            "This is the easiest chart for management to understand because it tells the before-and-after story in one visual.",
        )


def plot_portfolio_overview(df):
    col1, col2 = st.columns(2)

    with col1:
        segment_ead = df.groupby("income_segment", as_index=False)["ead_b"].sum()
        segment_ead["ead_b"] = segment_ead["ead_b"] / 1e9

        fig = px.bar(
            segment_ead,
            x="income_segment",
            y="ead_b",
            title="Exposure at Default (EAD) by Income Segment",
            labels={"ead_b": "Total EAD ($B)", "income_segment": "Income Segment"},
            color="ead_b",
            color_continuous_scale="Blues",
        )
        fig.update_layout(title_font_color="#1B3B6F")

        render_chart_with_explainer(
            fig,
            "EAD by income segment explanation",
            "Income segment buckets such as Mass Market, Mid Market, Affluent, and High Net Worth.",
            "Total exposure at default in billions of dollars.",
            "Taller bars mean that segment contributes more exposure if customers default. This is your exposure concentration view.",
            "This chart shows where portfolio size sits across customer segments and which segment drives Basel exposure the most.",
        )

    with col2:
        behavioral_rwa = df.groupby("behavioral_type", as_index=False)["total_cc_rwa_b"].sum()
        behavioral_rwa["total_cc_rwa_b"] = behavioral_rwa["total_cc_rwa_b"] / 1e9

        fig = px.pie(
            behavioral_rwa,
            values="total_cc_rwa_b",
            names="behavioral_type",
            title="Risk-Weighted Assets (RWA) by Behavioral Type",
            color_discrete_sequence=["#1B3B6F", "#D4AF37"],
        )
        fig.update_layout(title_font_color="#1B3B6F")
        fig.update_traces(textposition="inside", textinfo="percent+label")

        render_chart_with_explainer(
            fig,
            "RWA by behavioral type explanation",
            "Behavioral groups: Transactor vs Revolver.",
            "Each slice represents share of total RWA.",
            "A bigger slice means that customer behavior type consumes more regulatory capital.",
            "This helps you see whether the RWA burden is dominated by revolving customers or customers who tend to pay off balances.",
        )

    col3, col4 = st.columns(2)

    with col3:
        fig = px.histogram(
            df,
            x="fico_score",
            nbins=50,
            title="FICO Score Distribution",
            labels={"fico_score": "FICO Score", "count": "Number of Cards"},
            color_discrete_sequence=["#4A90E2"],
        )
        fig.update_layout(title_font_color="#1B3B6F")

        render_chart_with_explainer(
            fig,
            "FICO distribution explanation",
            "FICO score bands from lower-risk to higher-risk borrowers.",
            "Number of cards in each score band.",
            "Bars show where most customers sit on the credit-quality spectrum. A shift to the right means better credit quality.",
            "This gives the risk-quality shape of the portfolio and helps explain PD patterns later in the dashboard.",
        )

    with col4:
        fig = px.histogram(
            df,
            x="utilization_rate",
            nbins=50,
            title="Credit Utilization Rate Distribution",
            labels={"utilization_rate": "Utilization Rate", "count": "Number of Cards"},
            color_discrete_sequence=["#2C5282"],
        )
        fig.update_layout(title_font_color="#1B3B6F", xaxis_tickformat=".0%")

        render_chart_with_explainer(
            fig,
            "Utilization distribution explanation",
            "Utilization rate from low usage to high line usage.",
            "Number of cards in each utilization bucket.",
            "Bars on the left mean customers are using little of their limit. Bars on the right mean customers are using much more of their available credit.",
            "This chart shows how much of total card limits are actually being used, which is important for EAD and limit optimization opportunities.",
        )


def plot_risk_analytics(df):
    col1, col2 = st.columns(2)

    with col1:
        fig = px.box(
            df,
            x="fico_tier",
            y="pd",
            title="Probability of Default (PD) by FICO Tier",
            labels={"pd": "PD (%)", "fico_tier": "FICO Risk Tier"},
            color="fico_tier",
            color_discrete_sequence=px.colors.sequential.Reds,
        )
        fig.update_layout(title_font_color="#1B3B6F", yaxis_tickformat=".2%", showlegend=False)

        render_chart_with_explainer(
            fig,
            "PD by FICO tier explanation",
            "FICO risk tiers ordered from stronger to weaker credit quality.",
            "Probability of default as a percentage.",
            "Higher boxes mean that tier carries a higher default likelihood. The spread of the box shows variation within the tier.",
            "This confirms the expected credit story: weaker FICO tiers should carry higher PD and therefore higher expected loss.",
        )

    with col2:
        nco_by_segment = df.groupby("income_segment", as_index=False)["nco_rate"].mean()
        fig = px.bar(
            nco_by_segment,
            x="income_segment",
            y="nco_rate",
            title="Net Charge-Off (NCO) Rate by Income Segment",
            labels={"nco_rate": "NCO Rate (%)", "income_segment": "Income Segment"},
            color="nco_rate",
            color_continuous_scale="Oranges",
        )
        fig.update_layout(title_font_color="#1B3B6F", yaxis_tickformat=".2%")

        render_chart_with_explainer(
            fig,
            "NCO by income segment explanation",
            "Income segments.",
            "Average net charge-off rate.",
            "Taller bars mean a segment is losing more balance through write-offs after recoveries.",
            "This shows which customer segment is hurting portfolio credit performance the most from a loss perspective.",
        )

    col3, col4 = st.columns(2)

    with col3:
        el_by_segment = df.groupby("income_segment", as_index=False)["expected_loss_b"].sum()
        el_by_segment["expected_loss_b"] = el_by_segment["expected_loss_b"] / 1e6

        fig = px.pie(
            el_by_segment,
            values="expected_loss_b",
            names="income_segment",
            title="Expected Loss Distribution by Income Segment",
            color_discrete_sequence=px.colors.sequential.YlOrRd,
        )
        fig.update_layout(title_font_color="#1B3B6F")
        fig.update_traces(textposition="inside", textinfo="percent+label")

        render_chart_with_explainer(
            fig,
            "Expected loss by segment explanation",
            "Income segments shown as shares of total expected loss.",
            "Each slice is expected loss in millions of dollars.",
            "Bigger slices mean that segment contributes more to expected loss across the portfolio.",
            "This chart shows where economic credit loss is concentrated, not just where exposure is concentrated.",
        )

    with col4:
        sample = df.sample(min(10000, len(df)), random_state=42) if len(df) > 0 else df
        fig = px.scatter(
            sample,
            x="fico_score",
            y="pd",
            color="behavioral_type",
            title="FICO Score vs Probability of Default (PD)",
            labels={"fico_score": "FICO Score", "pd": "PD (%)"},
            opacity=0.6,
            color_discrete_map={"Transactor": "#1B3B6F", "Revolver": "#D4AF37"},
        )
        fig.update_layout(title_font_color="#1B3B6F", yaxis_tickformat=".1%")

        render_chart_with_explainer(
            fig,
            "FICO vs PD scatter explanation",
            "Individual account FICO score.",
            "Individual account probability of default.",
            "Points further left and higher up are weaker-quality Cards. Patterns by color show whether transactors and revolvers behave differently.",
            "This chart helps validate the risk relationship between score quality and default risk, while also showing behavior-type clustering.",
        )


def plot_exposure_analysis(df):
    col1, col2 = st.columns(2)

    with col1:
        exposure_comp = pd.DataFrame(
            {
                "Exposure Type": ["On-Balance (Drawn)", "Off-Balance (Unused × 10% CCF)"],
                "Amount ($B)": [
                    df["on_balance_exposure_b"].sum() / 1e9,
                    df["off_balance_exposure_b"].sum() / 1e9,
                ],
            }
        )

        fig = px.bar(
            exposure_comp,
            x="Exposure Type",
            y="Amount ($B)",
            title="On-Balance vs Off-Balance Exposure Components",
            color="Exposure Type",
            color_discrete_map={
                "On-Balance (Drawn)": "#1B3B6F",
                "Off-Balance (Unused × 10% CCF)": "#4A90E2",
            },
        )
        fig.update_layout(title_font_color="#1B3B6F", showlegend=False)

        render_chart_with_explainer(
            fig,
            "On-balance vs off-balance explanation",
            "Two exposure components: drawn balances and unused commitments converted with CCF.",
            "Exposure amount in billions of dollars.",
            "This compares what customers already owe versus what could still become exposure through undrawn limits.",
            "This is important because Basel RWA for cards is not only about balances already drawn; unused lines also contribute through CCF.",
        )

    with col2:
        fig = px.box(
            df,
            x="income_segment",
            y="credit_limit",
            title="Credit Limit Distribution by Income Segment",
            labels={"credit_limit": "Credit Limit ($)", "income_segment": "Income Segment"},
            color="income_segment",
        )
        fig.update_layout(title_font_color="#1B3B6F", showlegend=False)

        render_chart_with_explainer(
            fig,
            "Credit limit distribution explanation",
            "Income segments.",
            "Assigned credit limits in dollars.",
            "Higher boxes and medians mean that segment carries larger granted limits. Wide boxes mean greater variation in line assignment.",
            "This shows line allocation policy across the portfolio and highlights where limit optimization headroom may exist.",
        )

    col3, col4 = st.columns(2)

    with col3:
        util_comparison = df.groupby("behavioral_type", as_index=False)["utilization_rate"].mean()
        fig = px.bar(
            util_comparison,
            x="behavioral_type",
            y="utilization_rate",
            title="Average Utilization Rate by Behavioral Type",
            labels={"utilization_rate": "Avg Utilization Rate (%)", "behavioral_type": "Behavioral Type"},
            color="behavioral_type",
            color_discrete_map={"Transactor": "#1B3B6F", "Revolver": "#D4AF37"},
        )
        fig.update_layout(title_font_color="#1B3B6F", yaxis_tickformat=".1%", showlegend=False)

        render_chart_with_explainer(
            fig,
            "Average utilization by behavior explanation",
            "Behavioral type groups.",
            "Average utilization percentage.",
            "Higher bars mean that group uses more of its available limit on average.",
            "This highlights why revolvers usually drive more exposure pressure and why low-utilization transactors are attractive for line optimization.",
        )

    with col4:
        balance_by_type = df.groupby("card_type", as_index=False)["cc_outstanding_b"].sum()
        balance_by_type["cc_outstanding_b"] = balance_by_type["cc_outstanding_b"] / 1e6

        fig = px.bar(
            balance_by_type,
            x="card_type",
            y="cc_outstanding_b",
            title="Outstanding Balance by Card Type",
            labels={"cc_outstanding_b": "Outstanding Balance ($M)", "card_type": "Card Type"},
            color="cc_outstanding_b",
            color_continuous_scale="Greens",
        )
        fig.update_layout(title_font_color="#1B3B6F")

        render_chart_with_explainer(
            fig,
            "Outstanding balance by card type explanation",
            "Card product types such as Standard, Cash Back, Rewards, and Premium.",
            "Total outstanding balance in millions of dollars.",
            "Taller bars mean that product type carries more drawn exposure today.",
            "This shows which products are driving actual balances and can support product-level pricing or capital strategy discussions.",
        )


def plot_capital_requirements(df):
    col1, col2 = st.columns(2)

    with col1:
        t1_by_segment = df.groupby("income_segment", as_index=False)["tier1_requirement_b"].sum()
        t1_by_segment["tier1_requirement_b"] = t1_by_segment["tier1_requirement_b"] / 1e6

        fig = px.bar(
            t1_by_segment,
            x="income_segment",
            y="tier1_requirement_b",
            title="Tier 1 Capital Requirement by Income Segment",
            labels={"tier1_requirement_b": "Tier 1 Capital Req ($M)", "income_segment": "Income Segment"},
            color="tier1_requirement_b",
            color_continuous_scale="Blues",
        )
        fig.update_layout(title_font_color="#1B3B6F")

        render_chart_with_explainer(
            fig,
            "Tier 1 capital by segment explanation",
            "Income segments.",
            "Tier 1 capital requirement in millions of dollars.",
            "Taller bars mean that segment needs more capital support under the modeled framework.",
            "This translates exposure and RWA into a more finance-friendly capital requirement view.",
        )

    with col2:
        rwa_composition = pd.DataFrame(
            {
                "Type": ["Transactor RWA", "Revolver RWA"],
                "RWA ($B)": [
                    df["transactor_rwa_b"].sum() / 1e9,
                    df["revolver_rwa_b"].sum() / 1e9,
                ],
            }
        )

        fig = px.pie(
            rwa_composition,
            values="RWA ($B)",
            names="Type",
            title="RWA Composition: Transactor vs Revolver",
            color="Type",
            color_discrete_map={"Transactor RWA": "#1B3B6F", "Revolver RWA": "#D4AF37"},
        )
        fig.update_layout(title_font_color="#1B3B6F")
        fig.update_traces(textposition="inside", textinfo="percent+value")

        render_chart_with_explainer(
            fig,
            "RWA composition explanation",
            "Behavior-based RWA buckets.",
            "Share of total portfolio RWA.",
            "A larger slice means that group contributes more to capital consumption.",
            "This quickly shows whether capital pressure is coming more from revolvers or transactors.",
        )


def plot_profitability_analysis(df):
    col1, col2 = st.columns(2)

    with col1:
        revenue_components = (
            df.groupby("income_segment", as_index=False)[["interest_income_b", "fee_income_b"]].sum()
        )
        revenue_components["interest_income_b"] = revenue_components["interest_income_b"] / 1e6
        revenue_components["fee_income_b"] = revenue_components["fee_income_b"] / 1e6

        fig = go.Figure(
            data=[
                go.Bar(
                    name="Interest Income",
                    x=revenue_components["income_segment"],
                    y=revenue_components["interest_income_b"],
                    marker_color="#1B3B6F",
                ),
                go.Bar(
                    name="Fee Income",
                    x=revenue_components["income_segment"],
                    y=revenue_components["fee_income_b"],
                    marker_color="#D4AF37",
                ),
            ]
        )
        fig.update_layout(
            title="Revenue Components by Income Segment",
            barmode="stack",
            xaxis_title="Income Segment",
            yaxis_title="Revenue ($M)",
            title_font_color="#1B3B6F",
        )

        render_chart_with_explainer(
            fig,
            "Revenue components explanation",
            "Income segments.",
            "Stacked revenue in millions of dollars split into interest income and fee income.",
            "The total bar height is total revenue for that segment. The colors show what portion comes from interest versus fees.",
            "This shows whether a segment is monetized mostly through revolving balances or through transaction-related fees.",
        )

    with col2:
        ni_by_type = df.groupby("behavioral_type", as_index=False)["net_income_b"].sum()
        ni_by_type["net_income_b"] = ni_by_type["net_income_b"] / 1e6

        fig = px.bar(
            ni_by_type,
            x="behavioral_type",
            y="net_income_b",
            title="Net Income by Behavioral Type",
            labels={"net_income_b": "Net Income ($M)", "behavioral_type": "Behavioral Type"},
            color="behavioral_type",
            color_discrete_map={"Transactor": "#1B3B6F", "Revolver": "#D4AF37"},
        )
        fig.update_layout(title_font_color="#1B3B6F", showlegend=False)

        render_chart_with_explainer(
            fig,
            "Net income by behavior explanation",
            "Behavioral groups.",
            "Net income in millions of dollars.",
            "Higher bars mean that group contributes more profit after funding, operating costs, and expected loss.",
            "This helps compare profitability against the capital and risk burden shown elsewhere in the dashboard.",
        )

    col3, col4 = st.columns(2)

    with col3:
        roe_by_segment = df.groupby("income_segment", as_index=False)["roe"].mean()
        fig = px.bar(
            roe_by_segment,
            x="income_segment",
            y="roe",
            title="Return on Equity (ROE) by Income Segment",
            labels={"roe": "ROE (%)", "income_segment": "Income Segment"},
            color="roe",
            color_continuous_scale="RdYlGn",
        )
        fig.update_layout(title_font_color="#1B3B6F", yaxis_tickformat=".1%")

        render_chart_with_explainer(
            fig,
            "ROE by segment explanation",
            "Income segments.",
            "Average return on equity percentage.",
            "Higher bars mean better return generated relative to the capital tied to that segment.",
            "This helps identify which segment is producing the best capital efficiency.",
        )

    with col4:
        comparison = df.groupby("income_segment", as_index=False)[["expected_loss_b", "net_income_b"]].sum()
        comparison["expected_loss_b"] = comparison["expected_loss_b"] / 1e6
        comparison["net_income_b"] = comparison["net_income_b"] / 1e6

        fig = go.Figure(
            data=[
                go.Bar(
                    name="Expected Loss",
                    x=comparison["income_segment"],
                    y=comparison["expected_loss_b"],
                    marker_color="#E74C3C",
                ),
                go.Bar(
                    name="Net Income",
                    x=comparison["income_segment"],
                    y=comparison["net_income_b"],
                    marker_color="#27AE60",
                ),
            ]
        )
        fig.update_layout(
            title="Expected Loss vs Net Income by Segment",
            barmode="group",
            xaxis_title="Income Segment",
            yaxis_title="Amount ($M)",
            title_font_color="#1B3B6F",
        )

        render_chart_with_explainer(
            fig,
            "Expected loss vs net income explanation",
            "Income segments.",
            "Amount in millions of dollars for both expected loss and net income.",
            "If the green bar is much larger than the red bar, that segment is earning well above its modeled loss burden. If red begins to catch up, economics are weaker.",
            "This chart compares the good news and bad news for each segment in one view.",
        )


def plot_optimization_scenarios(df, rwa_reduction):
    st.subheader("💡 RWA Optimization Pathways")

    transactors = df[df["is_transactor"] == 1].copy()

    st.markdown("### Pathway 1: Transactor Credit Limit Reduction")
    col1, col2 = st.columns(2)

    with col1:
        reduction_scenarios = []
        base_transactor_rwa = transactors["total_cc_rwa_b"].sum() if len(transactors) > 0 else 0

        for reduction_pct in [0, 0.10, 0.20, 0.30, 0.40, 0.50]:
            if len(transactors) > 0:
                new_limit = transactors["credit_limit"] * (1 - reduction_pct)
                new_unused = (new_limit - transactors["cc_outstanding_b"]).clip(lower=0)
                new_ead = transactors["cc_outstanding_b"] + new_unused * 0.10
                new_rwa = new_ead * 1.0
                rwa_saved = base_transactor_rwa - new_rwa.sum()
            else:
                rwa_saved = 0

            reduction_scenarios.append(
                {
                    "Reduction %": f"{int(reduction_pct * 100)}%",
                    "RWA Saved ($M)": rwa_saved / 1e6,
                }
            )

        scenario_df = pd.DataFrame(reduction_scenarios)

        fig = px.line(
            scenario_df,
            x="Reduction %",
            y="RWA Saved ($M)",
            title="Transactor Limit Reduction: RWA Savings",
            markers=True,
            line_shape="spline",
        )
        fig.update_layout(title_font_color="#1B3B6F")

        render_chart_with_explainer(
            fig,
            "Transactor limit reduction savings explanation",
            "Credit limit reduction scenarios from 0% to 50%.",
            "RWA saved in millions of dollars.",
            "The line climbs as more unused limits are reduced, which lowers off-balance EAD and therefore RWA.",
            "This shows the size of the optimization opportunity if low-utilization transactors are managed more tightly.",
        )

    with col2:
        scenario_df["T1 Capital Relief ($M)"] = scenario_df["RWA Saved ($M)"] * 0.085
        fig = px.bar(
            scenario_df,
            x="Reduction %",
            y="T1 Capital Relief ($M)",
            title="Tier 1 Capital Relief from Limit Reduction",
            color="T1 Capital Relief ($M)",
            color_continuous_scale="Greens",
        )
        fig.update_layout(title_font_color="#1B3B6F")

        render_chart_with_explainer(
            fig,
            "Tier 1 relief explanation",
            "Credit limit reduction scenarios.",
            "Tier 1 capital relief in millions of dollars.",
            "Higher bars mean more capital released from the optimization scenario.",
            "This converts RWA savings into a capital story that finance and senior management can act on.",
        )

    st.markdown("### Pathway 2: Final RWA vs Current RWA")
    col3, col4 = st.columns(2)

    with col3:
        compare_df = pd.DataFrame(
            {
                "Scenario": ["Current RWA", "Final / Target RWA"],
                "RWA ($M)": [
                    rwa_reduction["current_rwa"] / 1e6,
                    rwa_reduction["final_rwa"] / 1e6,
                ],
            }
        )
        fig = px.bar(
            compare_df,
            x="Scenario",
            y="RWA ($M)",
            title="Current RWA vs Target / Final RWA",
            color="Scenario",
            color_discrete_map={
                "Current RWA": "#1B3B6F",
                "Final / Target RWA": "#27AE60",
            },
        )
        fig.update_layout(title_font_color="#1B3B6F", showlegend=False)

        render_chart_with_explainer(
            fig,
            "Current vs target RWA explanation",
            "Current portfolio and optimized target portfolio.",
            "RWA in millions of dollars.",
            "The green bar should be lower if the optimization works. The size of the drop is the value created.",
            "This is the clean target-setting chart for project discussions and executive updates.",
        )

    with col4:
        optimization_stats = pd.DataFrame(
            {
                "Category": [
                    "Eligible for Limit Reduction",
                    "Eligible for Overdraft Conversion",
                    "All Other Cards",
                ],
                "Cards": [
                    int(df["eligible_for_limit_reduction"].sum()),
                    int(df["eligible_for_overdraft_conversion"].sum()),
                    int(len(df) - df["eligible_for_limit_reduction"].sum()),
                ],
            }
        )

        fig = px.pie(
            optimization_stats,
            values="Cards",
            names="Category",
            title="Optimization Eligibility",
            color_discrete_sequence=["#1B3B6F", "#D4AF37", "#9CA3AF"],
        )
        fig.update_layout(title_font_color="#1B3B6F")
        fig.update_traces(textposition="inside", textinfo="percent+label")

        render_chart_with_explainer(
            fig,
            "Optimization eligibility explanation",
            "Portfolio split across optimization-eligible and non-eligible groups.",
            "Each slice shows account count share.",
            "Bigger eligible slices mean more room to act without touching the full portfolio.",
            "This tells you how much of the book is immediately actionable under the modeled strategy.",
        )


def plot_rwa_reduction_analysis(df):
    baseline_rwa = df["total_cc_rwa_b"].sum()

    transactors = df[df["is_transactor"] == 1].copy()
    reduction_pct = 0.30

    if len(transactors) > 0:
        trans_new_limit = transactors["credit_limit"] * (1 - reduction_pct)
        trans_new_unused = (trans_new_limit - transactors["cc_outstanding_b"]).clip(lower=0)
        trans_new_ead = transactors["cc_outstanding_b"] + trans_new_unused * 0.10
        trans_new_rwa = trans_new_ead * 1.0
        transactors["rwa_optimized"] = trans_new_rwa
        transactors["rwa_reduction"] = transactors["total_cc_rwa_b"] - trans_new_rwa
    else:
        transactors["rwa_optimized"] = []
        transactors["rwa_reduction"] = []

    revolvers = df[df["is_revolver"] == 1].copy()
    revolvers["rwa_optimized"] = revolvers["total_cc_rwa_b"]
    revolvers["rwa_reduction"] = 0.0

    df_opt = pd.concat([transactors, revolvers], ignore_index=True)

    st.subheader("RWA Reduction Breakdown")
    col1, col2 = st.columns(2)

    with col1:
        total_comparison = pd.DataFrame(
            {
                "Scenario": ["Current RWA", "Post-Optimization RWA", "RWA Reduction"],
                "Amount ($M)": [
                    baseline_rwa / 1e6,
                    df_opt["rwa_optimized"].sum() / 1e6,
                    (baseline_rwa - df_opt["rwa_optimized"].sum()) / 1e6,
                ],
            }
        )
        fig = px.bar(
            total_comparison,
            x="Scenario",
            y="Amount ($M)",
            title="Total RWA: Before vs After",
            text="Amount ($M)",
            color="Scenario",
            color_discrete_map={
                "Current RWA": "#1B3B6F",
                "Post-Optimization RWA": "#4A90E2",
                "RWA Reduction": "#27AE60",
            },
        )
        fig.update_traces(texttemplate="$%{text:.1f}M", textposition="outside")
        fig.update_layout(title_font_color="#1B3B6F", showlegend=False)

        render_chart_with_explainer(
            fig,
            "Before vs after RWA explanation",
            "Portfolio state before optimization, after optimization, and the difference.",
            "RWA in millions of dollars.",
            "This is a direct before-and-after capital view.",
            "It shows whether the proposed optimization makes a meaningful difference at total portfolio level.",
        )

    with col2:
        segment_reduction = (
            df_opt.groupby("income_segment", as_index=False)[["total_cc_rwa_b", "rwa_optimized"]].sum()
        )
        segment_reduction["reduction_pct"] = np.where(
            segment_reduction["total_cc_rwa_b"] > 0,
            (segment_reduction["total_cc_rwa_b"] - segment_reduction["rwa_optimized"])
            / segment_reduction["total_cc_rwa_b"]
            * 100,
            0,
        )

        fig = px.bar(
            segment_reduction,
            x="income_segment",
            y="reduction_pct",
            title="RWA Reduction % by Income Segment",
            labels={"reduction_pct": "Reduction (%)", "income_segment": "Income Segment"},
            color="reduction_pct",
            color_continuous_scale="Greens",
            text="reduction_pct",
        )
        fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig.update_layout(title_font_color="#1B3B6F")

        render_chart_with_explainer(
            fig,
            "Reduction by income segment explanation",
            "Income segments.",
            "Percentage reduction in RWA after optimization.",
            "Higher bars mean that segment benefits more from the modeled optimization path.",
            "This tells you where the optimization is most powerful, not just where the biggest balances sit.",
        )

    col3, col4 = st.columns(2)

    with col3:
        behavioral_reduction = (
            df_opt.groupby("behavioral_type", as_index=False)[["total_cc_rwa_b", "rwa_reduction"]].sum()
        )
        behavioral_reduction["total_cc_rwa_b"] = behavioral_reduction["total_cc_rwa_b"] / 1e6
        behavioral_reduction["rwa_reduction"] = behavioral_reduction["rwa_reduction"] / 1e6

        fig = go.Figure(
            data=[
                go.Bar(
                    name="Current RWA",
                    x=behavioral_reduction["behavioral_type"],
                    y=behavioral_reduction["total_cc_rwa_b"],
                    marker_color="#1B3B6F",
                ),
                go.Bar(
                    name="RWA Reduction",
                    x=behavioral_reduction["behavioral_type"],
                    y=behavioral_reduction["rwa_reduction"],
                    marker_color="#27AE60",
                ),
            ]
        )
        fig.update_layout(
            title="RWA Reduction Amount by Behavioral Type",
            barmode="group",
            yaxis_title="Amount ($M)",
            title_font_color="#1B3B6F",
        )

        render_chart_with_explainer(
            fig,
            "Behavioral reduction explanation",
            "Behavioral groups.",
            "Current RWA and RWA reduction in millions of dollars.",
            "This compares how much burden each group has today and how much can actually be removed.",
            "It helps prove whether transactor optimization is the real driver of savings.",
        )

    with col4:
        combo_reduction = (
            df_opt.groupby(["income_segment", "behavioral_type"], as_index=False)["rwa_reduction"].sum()
        )
        combo_reduction["rwa_reduction"] = combo_reduction["rwa_reduction"] / 1e6

        fig = px.sunburst(
            combo_reduction,
            path=["income_segment", "behavioral_type"],
            values="rwa_reduction",
            title="RWA Reduction: Income Segment → Behavioral Type",
            color="rwa_reduction",
            color_continuous_scale="Blues",
        )
        fig.update_layout(title_font_color="#1B3B6F")

        render_chart_with_explainer(
            fig,
            "Sunburst explanation",
            "Inner ring is income segment; outer ring is behavioral type inside each segment.",
            "Area size represents RWA reduction contribution.",
            "Larger blocks mean that combination contributes more to the savings story.",
            "This gives a manager a fast way to spot which segment-behavior mix is producing the optimization benefit.",
        )


# =============================================================================
# MAIN
# =============================================================================


def main():
    st.markdown(
        """
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
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")

    df, data_msg = load_data()
    st.success(f"✅ {data_msg}")

    filters = create_sidebar_filters(df)
    df_filtered = apply_filters_and_stress(df, filters)

    if filters["stress_mode"]:
        st.warning(
            f"📊 Stress Scenario Active: {filters['scenario_type']} | "
            f"PD Stress: {filters['pd_stress']:.1f}x | "
            f"NCO Stress: {filters['nco_stress']:.1f}x | "
            f"GDP Impact: {filters['macro_stress']:.2f}x"
        )

    rwa_reduction = calculate_rwa_reduction(df_filtered)

    st.subheader("📊 Portfolio Key Performance Indicators")

    col1, col2, col3, col4, col5 = st.columns(5)

    baseline_rwa_full = df["total_cc_rwa_b"].sum()
    current_rwa = rwa_reduction["current_rwa"]

    with col1:
        st.metric("Total Cards", f"{len(df_filtered):,}")

    with col2:
        st.metric("Total EAD", format_currency(df_filtered["ead_b"].sum()))

    with col3:
        stress_delta = (
            f"{((current_rwa - baseline_rwa_full) / baseline_rwa_full * 100):.1f}% vs full book"
            if baseline_rwa_full > 0
            else None
        )
        st.metric("Current RWA", format_currency(current_rwa), stress_delta)

    with col4:
        st.metric(
            "RWA Reduction Potential",
            format_currency(rwa_reduction["total_rwa_reduction"]),
            f"-{rwa_reduction['reduction_pct']:.1f}%",
            delta_color="inverse",
        )

    with col5:
        st.metric(
            "Final RWA After Reduction",
            format_currency(rwa_reduction["final_rwa"]),
            f"Target after optimization",
            delta_color="normal",
        )

    col6, col7, col8, col9, col10 = st.columns(5)

    with col6:
        st.metric("Tier 1 Relief", format_currency(rwa_reduction["tier1_relief"]))

    with col7:
        st.metric("Transactor Pathway", format_currency(rwa_reduction["transactor_pathway"]))

    with col8:
        st.metric("Overdraft Pathway", format_currency(rwa_reduction["overdraft_pathway"]))

    with col9:
        eligible_pct = (
            df_filtered["eligible_for_limit_reduction"].sum() / len(df_filtered) * 100
            if len(df_filtered) > 0
            else 0
        )
        st.metric(
            "Optimization Eligible",
            f"{int(df_filtered['eligible_for_limit_reduction'].sum()):,}",
            f"{eligible_pct:.1f}% of filtered book",
        )

    with col10:
        avg_pd = df_filtered["pd"].mean() if len(df_filtered) > 0 else 0
        st.metric("Avg PD", format_percentage(avg_pd), f"{avg_pd*10000:.0f} bps")

    st.markdown(
        """
        <div class="chart-note">
            The dashboard now explains every chart in plain language. Open each chart expander to see what the axes mean,
            how to interpret the chart, and what business result it is showing.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")

    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(
        [
            "📌 RWA Snapshot",
            "📊 Portfolio Overview",
            "⚠️ Risk Analytics",
            "💳 Exposure & Balances",
            "🏛️ Capital Requirements",
            "💰 Profitability",
            "🎯 Optimization & Reduction",
        ]
    )

    with tab1:
        plot_rwa_summary_charts(df_filtered, rwa_reduction)

    with tab2:
        plot_portfolio_overview(df_filtered)

    with tab3:
        plot_risk_analytics(df_filtered)

    with tab4:
        plot_exposure_analysis(df_filtered)

    with tab5:
        plot_capital_requirements(df_filtered)

    with tab6:
        plot_profitability_analysis(df_filtered)

    with tab7:
        plot_optimization_scenarios(df_filtered, rwa_reduction)
        st.markdown("---")
        plot_rwa_reduction_analysis(df_filtered)

    st.markdown("---")
    st.subheader("📥 Export & Download")

    col_a, col_b, col_c = st.columns(3)

    with col_a:
        csv_portfolio = df_filtered.to_csv(index=False)
        st.download_button(
            label="Download Filtered Portfolio CSV",
            data=csv_portfolio,
            file_name=f"pnc_portfolio_filtered_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )

    with col_b:
        summary = df_filtered.groupby("income_segment").agg(
            {
                "ead_b": "sum",
                "total_cc_rwa_b": "sum",
                "pd": "mean",
                "nco_rate": "mean",
                "expected_loss_b": "sum",
                "net_income_b": "sum",
                "tier1_requirement_b": "sum",
            }
        )
        summary_csv = summary.to_csv()
        st.download_button(
            label="Download Summary CSV",
            data=summary_csv,
            file_name=f"pnc_summary_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )

    with col_c:
        st.info(
            f"Filtered Cards: {len(df_filtered):,} / {len(df):,}\n\n"
            f"Scenario: {filters['scenario_type']}"
        )

    st.markdown(
        f"""
        <div class='pi-footer'>
            <strong>PROFIT INSIGHT</strong> Basel RWA Analytics Platform<br/>
            PNC Bank Credit Card Portfolio Analysis | US Standardized Approach (12 CFR Part 3)<br/>
            Dashboard Version 2.0 | Last Updated: {datetime.now().strftime('%Y-%m-%d')}<br/>
            <em>Proprietary & Confidential</em>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.markdown("---")
    st.sidebar.info(
        f"**Dashboard Info**\n\n"
        f"- Filtered Cards: {len(df_filtered):,}\n"
        f"- Total Portfolio: {len(df):,}\n"
        f"- Stress Scenario: {filters['scenario_type']}\n"
        f"- Last Refresh: {datetime.now().strftime('%H:%M:%S')}"
    )


if __name__ == "__main__":
    main()
