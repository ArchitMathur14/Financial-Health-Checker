import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(
    page_title="Financial Health Checker",
    layout="wide"
)

st.title("📊 Financial Health Checker")
st.write("Analyze a listed company’s financial health using key ratios and 5-year trends.")

# -----------------------------
# Helper function
# -----------------------------
def safe_get(df, row):
    try:
        return df.loc[row]
    except:
        return None

# -----------------------------
# Fetch 5-year financial data
# -----------------------------
def fetch_financials_5y(ticker):
    stock = yf.Ticker(ticker)

    income = stock.financials
    balance = stock.balance_sheet

    if income.empty or balance.empty:
        raise ValueError("Financial data not available for this company.")

    df = pd.DataFrame({
        "Revenue": safe_get(income, "Total Revenue"),
        "Net Income": safe_get(income, "Net Income"),
        "Current Assets": safe_get(balance, "Current Assets"),
        "Current Liabilities": safe_get(balance, "Current Liabilities"),
        "Total Liabilities": safe_get(balance, "Total Liabilities Net Minority Interest"),
        "Equity": safe_get(balance, "Stockholders Equity"),
    })

    return df.dropna()

# -----------------------------
# Calculate financial ratios
# -----------------------------
def calculate_ratios(df):
    ratios = pd.DataFrame(index=df.index)

    ratios["Net Profit Margin"] = df["Net Income"] / df["Revenue"]
    ratios["ROE"] = df["Net Income"] / df["Equity"]
    ratios["Debt to Equity"] = df["Total Liabilities"] / df["Equity"]
    ratios["Current Ratio"] = df["Current Assets"] / df["Current Liabilities"]

    return ratios.round(2)

# -----------------------------
# Rule-based health assessment
# -----------------------------
def financial_health_verdict(latest):
    score = 0
    observations = []

    if latest["Net Profit Margin"] > 0.10:
        score += 1
        observations.append("Healthy profitability")
    else:
        observations.append("Weak profit margins")

    if latest["ROE"] > 0.15:
        score += 1
        observations.append("Strong return on equity")
    else:
        observations.append("Low return on equity")

    if latest["Debt to Equity"] < 1.5:
        score += 1
        observations.append("Debt levels are manageable")
    else:
        observations.append("High leverage risk")

    if latest["Current Ratio"] > 1.2:
        score += 1
        observations.append("Good short-term liquidity")
    else:
        observations.append("Liquidity risk")

    if score >= 3:
        verdict = "🟢 Strong Financial Health"
    elif score == 2:
        verdict = "🟡 Moderate Financial Health"
    else:
        verdict = "🔴 Weak Financial Health"

    return verdict, observations

# -----------------------------
# Streamlit UI
# -----------------------------
ticker = st.text_input(
    "Enter listed company ticker (e.g. AAPL, MSFT, RELIANCE.NS, TCS.NS)"
)

if st.button("Analyze Company"):
    try:
        financials_df = fetch_financials_5y(ticker)
        ratios_df = calculate_ratios(financials_df)

        st.subheader("📌 Financial Data (Last 5 Years)")
        st.dataframe(financials_df)

        st.subheader("📈 Financial Ratios (5-Year Trend)")
        st.dataframe(ratios_df)

        st.subheader("📊 Ratio Trends")
        st.line_chart(ratios_df)

        latest_ratios = ratios_df.iloc[:, 0]
        verdict, notes = financial_health_verdict(latest_ratios)

        st.subheader("✅ Financial Health Verdict")
        st.success(verdict)

        st.subheader("🔍 Key Observations")
        for note in notes:
            st.write(f"- {note}")

    except Exception as e:
        st.error(str(e))
