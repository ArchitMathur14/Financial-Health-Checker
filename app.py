import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go


# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(page_title="Financial Health Checker", layout="centered")
st.title("🏦 Financial Health Checker")
st.markdown(
    "A **comprehensive company analysis** covering market performance, financial strength, valuation, and risk indicators."
)

# ============================================================
# USER INPUT
# ============================================================
ticker_symbol = st.text_input(
    "Enter Stock Ticker (e.g. AAPL, MSFT, RELIANCE.NS)",
    value="AAPL"
).upper()

if not ticker_symbol:
    st.stop()

# ============================================================
# FETCH DATA
# ============================================================
@st.cache_data
def load_company_data(ticker):
    stock = yf.Ticker(ticker)
    hist = stock.history(period="max")
    info = stock.info
    financials = stock.financials
    balance_sheet = stock.balance_sheet
    cashflow = stock.cashflow
    return hist, info, financials, balance_sheet, cashflow

try:
    hist, info, financials, balance_sheet, cashflow = load_company_data(ticker_symbol)
except Exception:
    st.error("Invalid ticker or data unavailable.")
    st.stop()

# ============================================================
# COMPANY SNAPSHOT
# ============================================================
st.subheader("🏢 Company Snapshot")

col1, col2, col3 = st.columns(3)

col1.metric("Company", info.get("shortName", "N/A"))
col2.metric("Sector", info.get("sector", "N/A"))
col3.metric("Market Cap", f"${info.get('marketCap', 0):,.0f}")

# ============================================================
# MARKET PRICE METRICS
# ============================================================
st.subheader("📈 Market Price Overview")

all_time_high = hist["High"].max()
all_time_low = hist["Low"].min()

fifty_two_week_data = hist.last("365D")
high_52w = fifty_two_week_data["High"].max()
low_52w = fifty_two_week_data["Low"].min()

col1, col2 = st.columns(2)
col1.metric("All-Time High", f"${all_time_high:,.2f}")
col1.metric("52-Week High", f"${high_52w:,.2f}")
col2.metric("All-Time Low", f"${all_time_low:,.2f}")
col2.metric("52-Week Low", f"${low_52w:,.2f}")

# ============================================================
# PRICE CHART
# ============================================================
st.subheader("📉 Share Price History")

fig_price = go.Figure()
fig_price.add_trace(go.Scatter(
    x=hist.index,
    y=hist["Close"],
    name="Close Price",
    line=dict(color="royalblue")
))
fig_price.update_layout(
    xaxis_title="Date",
    yaxis_title="Price",
    hovermode="x unified"
)
st.plotly_chart(fig_price, use_container_width=True)

# ============================================================
# FINANCIAL PERFORMANCE (TRENDS)
# ============================================================
st.subheader("📊 Financial Performance Trends")

if not financials.empty:
    fin_df = financials.loc[["Total Revenue", "Net Income"]].T
    fin_df.index = fin_df.index.year

    fig_fin = go.Figure()
    fig_fin.add_trace(go.Bar(
        x=fin_df.index,
        y=fin_df["Total Revenue"],
        name="Revenue"
    ))
    fig_fin.add_trace(go.Bar(
        x=fin_df.index,
        y=fin_df["Net Income"],
        name="Net Income"
    ))

    fig_fin.update_layout(
        barmode="group",
        xaxis_title="Year",
        yaxis_title="USD"
    )

    st.plotly_chart(fig_fin, use_container_width=True)
else:
    st.warning("Financial performance data unavailable.")

# ============================================================
# BALANCE SHEET OVERVIEW
# ============================================================
st.subheader("🏦 Balance Sheet Overview")

if not balance_sheet.empty:
    bs_df = balance_sheet.loc[["Total Assets", "Total Liab"]].T
    bs_df.index = bs_df.index.year

    fig_bs = go.Figure()
    fig_bs.add_trace(go.Scatter(
        x=bs_df.index,
        y=bs_df["Total Assets"],
        name="Total Assets"
    ))
    fig_bs.add_trace(go.Scatter(
        x=bs_df.index,
        y=bs_df["Total Liab"],
        name="Total Liabilities"
    ))

    fig_bs.update_layout(
        xaxis_title="Year",
        yaxis_title="USD",
        hovermode="x unified"
    )

    st.plotly_chart(fig_bs, use_container_width=True)
else:
    st.warning("Balance sheet data unavailable.")

# ============================================================
# KEY FINANCIAL RATIOS
# ============================================================
st.subheader("📐 Key Financial Ratios")

def safe_get(key):
    value = info.get(key)
    return round(value, 2) if isinstance(value, (int, float)) else None

ratios = {
    "P/E Ratio": safe_get("trailingPE"),
    "Price to Book": safe_get("priceToBook"),
    "Debt to Equity": safe_get("debtToEquity"),
    "Profit Margin (%)": safe_get("profitMargins"),
    "Return on Equity (%)": safe_get("returnOnEquity"),
    "Operating Margin (%)": safe_get("operatingMargins"),
}

ratio_df = pd.DataFrame(
    [(k, v if v is not None else "N/A") for k, v in ratios.items()],
    columns=["Metric", "Value"]
)

st.dataframe(ratio_df, use_container_width=True)

# ============================================================
# FINANCIAL HEALTH SCORE (0–100)
# ============================================================
st.subheader("🧠 Financial Health Score")

score = 50

if ratios["Profit Margin (%)"] and ratios["Profit Margin (%)"] > 0:
    score += 15
if ratios["Return on Equity (%)"] and ratios["Return on Equity (%)"] > 0.15:
    score += 15
if ratios["Debt to Equity"] and ratios["Debt to Equity"] < 150:
    score += 10
if ratios["P/E Ratio"] and ratios["P/E Ratio"] < 30:
    score += 10

score = min(score, 100)

st.metric("Overall Financial Health Score", f"{score} / 100")

if score >= 75:
    st.success("Strong financial position with healthy profitability and balance sheet.")
elif score >= 50:
    st.warning("Moderate financial health. Some risk factors present.")
else:
    st.error("Weak financial health. High risk indicators detected.")

# ============================================================
# FOOTER
# ============================================================
st.caption(
    "Educational use only. Data sourced via Yahoo Finance. "
    "Not investment advice."
)
