import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import json
import os
from google import genai


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

# DataFrame.last() was removed in newer pandas versions; filter the DatetimeIndex instead.
if not hist.empty:
    latest_date = hist.index.max()
    cutoff_date = latest_date - pd.Timedelta(days=365)
    fifty_two_week_data = hist.loc[hist.index >= cutoff_date]
else:
    fifty_two_week_data = hist
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
def get_first_available_row(df, possible_names):
    for name in possible_names:
        if name in df.index:
            return df.loc[name]
    return None



st.subheader("🏦 Balance Sheet Overview")

assets_row = get_first_available_row(
    balance_sheet,
    ["Total Assets"]
)

liabilities_row = get_first_available_row(
    balance_sheet,
    [
        "Total Liab",
        "Total Liabilities",
        "Total Liabilities Net Minority Interest"
    ]
)

if assets_row is not None and liabilities_row is not None:
    bs_df = pd.DataFrame({
        "Total Assets": assets_row,
        "Total Liabilities": liabilities_row
    })
    bs_df.index = bs_df.index.year

    fig_bs = go.Figure()
    fig_bs.add_trace(go.Scatter(
        x=bs_df.index,
        y=bs_df["Total Assets"],
        name="Total Assets"
    ))
    fig_bs.add_trace(go.Scatter(
        x=bs_df.index,
        y=bs_df["Total Liabilities"],
        name="Total Liabilities"
    ))

    fig_bs.update_layout(
        xaxis_title="Year",
        yaxis_title="USD",
        hovermode="x unified"
    )

    st.plotly_chart(fig_bs, use_container_width=True)
else:
    st.warning("Balance sheet data unavailable for this company.")


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
# AI FINANCIAL ANALYST CHAT
# ============================================================
st.markdown("---")
st.subheader("💬 AI Financial Analyst")
st.markdown(
    "Ask questions about the selected company's financial health. "
    "Python supplies the financial figures; Gemini explains them in plain language."
)

with st.expander("About this AI analyst", expanded=False):
    st.write(
        "The analyst uses the current ticker's retrieved financial data, key ratios, "
        "and health score as context. It is designed to disclose missing information "
        "rather than invent figures. This tool is for education, not investment advice."
    )

def _safe_frame_context(frame, wanted_rows, max_periods=5):
    if frame is None or frame.empty:
        return {}
    available = [row for row in wanted_rows if row in frame.index]
    if not available:
        return {}
    subset = frame.loc[available].iloc[:, :max_periods].copy()
    subset = subset.astype(object).where(pd.notna(subset), None)
    result = {}
    for column in subset.columns:
        result[str(getattr(column, "year", column))] = {
            str(index): (float(value) if isinstance(value, (int, float)) else value)
            for index, value in subset[column].items()
        }
    return result

financial_context = {
    "ticker": ticker_symbol,
    "company_name": info.get("longName") or info.get("shortName") or ticker_symbol,
    "sector": info.get("sector"),
    "industry": info.get("industry"),
    "currency": info.get("currency"),
    "market_cap": info.get("marketCap"),
    "key_ratios_as_returned_by_yahoo_finance": ratios,
    "app_financial_health_score_out_of_100": score,
    "income_statement_recent_periods": _safe_frame_context(
        financials,
        ["Total Revenue", "Net Income", "Operating Income", "Gross Profit"],
    ),
    "balance_sheet_recent_periods": _safe_frame_context(
        balance_sheet,
        [
            "Total Assets", "Total Liab", "Total Liabilities",
            "Total Liabilities Net Minority Interest", "Total Debt",
            "Stockholders Equity", "Total Stockholder Equity",
            "Current Assets", "Current Liabilities",
        ],
    ),
    "cash_flow_recent_periods": _safe_frame_context(
        cashflow,
        [
            "Operating Cash Flow", "Free Cash Flow", "Capital Expenditure",
            "Capital Expenditures",
        ],
    ),
    "data_source": "Yahoo Finance via yfinance",
    "limitations": [
        "Available statement rows and periods vary by company.",
        "Yahoo Finance data can be incomplete or delayed.",
        "The health score is a simple rule-based indicator created by this app, not a validated credit rating.",
    ],
}

api_key = None
try:
    api_key = st.secrets.get("GOOGLE_API_KEY")
except Exception:
    pass
api_key = api_key or os.getenv("GOOGLE_API_KEY")

if not api_key:
    st.info(
        "To enable chat, add a Gemini API key as GOOGLE_API_KEY in "
        "Streamlit Community Cloud App settings → Secrets. "
        "Do not paste your API key into this chat or commit it to GitHub."
    )
else:
    analyst_history = st.session_state.setdefault("financial_analyst_history", [])
    st.caption(f"Current company context: {financial_context['company_name']} ({ticker_symbol})")

    for message in analyst_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    user_question = st.chat_input(
        f"Ask the analyst about {ticker_symbol}...",
        key="financial_analyst_question",
    )

    if user_question:
        analyst_history.append({"role": "user", "content": user_question})
        with st.chat_message("user"):
            st.markdown(user_question)

        system_instruction = """
You are an AI Financial Analyst inside an educational company-analysis application.
Use the provided JSON financial context for all company-specific numeric claims.
Never invent financial figures, reporting periods, or causes for changes. If data is
missing, say so explicitly. Distinguish retrieved facts from your interpretation.
Explain ratios in clear language and mention relevant caveats. The displayed health
score is a simple heuristic, not a validated credit rating. Do not provide personalized
investment advice, guaranteed outcomes, or unsupported buy/sell recommendations.
State when the supplied data is insufficient for a conclusion. Keep responses useful,
structured, and concise.
"""
        recent_messages = analyst_history[-10:]
        conversation = "\n\n".join(
            f"{message['role'].upper()}: {message['content']}"
            for message in recent_messages
        )
        prompt = (
            f"{system_instruction}\n\n"
            f"FINANCIAL CONTEXT JSON:\n"
            f"{json.dumps(financial_context, default=str, ensure_ascii=False)}\n\n"
            f"RECENT CONVERSATION:\n{conversation}\n\n"
            "Answer the latest user question using the supplied context."
        )

        with st.chat_message("assistant"):
            try:
                with st.spinner("Analyzing the company's financial data..."):
                    gemini_client = genai.Client(api_key=api_key)
                    gemini_response = gemini_client.interactions.create(
                        model="gemini-3.8-flash",
                        input=prompt,
                    )
                    answer = (gemini_response.output_text or "").strip()
                    if not answer:
                        answer = "The AI returned an empty response. Please try asking in a different way."
                st.markdown(answer)
                analyst_history.append({"role": "assistant", "content": answer})
            except Exception as exc:
                st.error(
                    "The AI request failed. Verify that the Gemini API key is valid, "
                    "the API is enabled, and your usage quota is available. "
                    f"Technical detail: {exc}"
                )

    if analyst_history and st.button("Clear analyst chat", key="clear_financial_analyst_history"):
        st.session_state["financial_analyst_history"] = []
        st.rerun()





# ============================================================
# FOOTER
# ============================================================
st.caption(
    "Educational use only. Data sourced via Yahoo Finance. "
    "Not investment advice."
)
