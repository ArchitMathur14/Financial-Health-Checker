import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go


# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Financial Health Checker",
    layout="centered"
)

st.title("🏦 Financial Health Checker")
st.markdown("Analyze a company’s **market performance, financial strength, and valuation**.")

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
    return hist, info, financials, balance_sheet

try:
    hist, info, financials, balance_sheet = load_company_data(ticker_symbol)
except Exception:
    st.error("Invalid ticker or data unavailable.")
    st.stop()

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
    name="Close Price"
))

fig_price.update_layout(
    xaxis_title="Date",
    yaxis_title="Price",
    hovermode="x unified"
)

st.plotly_chart(fig_price, use_container_width=True)

# ============================================================
# KEY FINANCIAL RATIOS
# ============================================================
st.subheader("📊 Key Financial Ratios")

def safe_get(key):
    value = info.get(key)
    return round(value, 2) if isinstance(value, (int, float)) else "N/A"

ratios = {
    "P/E Ratio": safe_get("trailingPE"),
    "Price to Book": safe_get("priceToBook"),
    "Debt to Equity": safe_get("debtToEquity"),
    "Profit Margin": safe_get("profitMargins"),
    "Return on Equity (ROE)": safe_get("returnOnEquity"),
}

st.table(pd.DataFrame(ratios.items(), columns=["Metric", "Value"]))

# ============================================================
# FINANCIAL STATEMENTS SNAPSHOT
# ============================================================
st.subheader("💰 Financial Snapshot")

try:
    revenue = financials.loc["Total Revenue"].iloc[0]
    net_income = financials.loc["Net Income"].iloc[0]
    total_assets = balance_sheet.loc["Total Assets"].iloc[0]
    total_liabilities = balance_sheet.loc["Total Liab"].iloc[0]

    fin_col1, fin_col2 = st.columns(2)

    fin_col1.metric("Total Revenue", f"${revenue:,.0f}")
    fin_col1.metric("Net Income", f"${net_income:,.0f}")

    fin_col2.metric("Total Assets", f"${total_assets:,.0f}")
    fin_col2.metric("Total Liabilities", f"${total_liabilities:,.0f}")

except Exception:
    st.warning("Detailed financial statements not available.")

# ============================================================
# BASIC HEALTH INTERPRETATION
# ============================================================
st.subheader("🧠 Financial Health Interpretation")

interpretation = []

if isinstance(ratios["Debt to Equity"], (int, float)) and ratios["Debt to Equity"] > 150:
    interpretation.append("⚠️ High leverage — company relies heavily on debt.")
else:
    interpretation.append("✅ Debt levels appear manageable.")

if isinstance(ratios["Profit Margin"], (int, float)) and ratios["Profit Margin"] < 0:
    interpretation.append("⚠️ Company is currently unprofitable.")
else:
    interpretation.append("✅ Company is generating profits.")

if isinstance(ratios["P/E Ratio"], (int, float)) and ratios["P/E Ratio"] > 30:
    interpretation.append("⚠️ Valuation appears expensive relative to earnings.")
else:
    interpretation.append("✅ Valuation appears reasonable.")

for point in interpretation:
    st.write(point)

# ============================================================
# FOOTER
# ============================================================
st.caption(
    "Educational use only. Data sourced via Yahoo Finance. "
    "Not investment advice."
)
