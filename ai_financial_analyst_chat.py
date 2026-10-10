"""
AI Financial Analyst chat panel for Streamlit.
Add this file to the same folder as app.py, then call:
    from ai_financial_analyst_chat import render_ai_financial_analyst_chat
    render_ai_financial_analyst_chat()

Configure GOOGLE_API_KEY in Streamlit Community Cloud -> App -> Settings -> Secrets:
    GOOGLE_API_KEY = "your-Gemini-API-key"
"""

import json
import os
from typing import Any

import pandas as pd
import streamlit as st
import yfinance as yf
from google import genai


def _clean_number(value: Any):
    try:
        if pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _find_row(df: pd.DataFrame, candidates: list[str]):
    if df is None or df.empty:
        return None
    lookup = {str(idx).strip().lower(): idx for idx in df.index}
    for candidate in candidates:
        key = candidate.lower()
        if key in lookup:
            return lookup[key]
    for idx in df.index:
        label = str(idx).strip().lower()
        if any(candidate.lower() in label for candidate in candidates):
            return idx
    return None


def _series_values(df: pd.DataFrame, candidates: list[str], max_periods: int = 5):
    row = _find_row(df, candidates)
    if row is None:
        return {}
    result = {}
    try:
        for col in list(df.columns)[:max_periods]:
            val = _clean_number(df.loc[row, col])
            if val is not None:
                result[str(col)] = val
    except Exception:
        return {}
    return result


def _build_financial_context(ticker_symbol: str) -> dict:
    company = yf.Ticker(ticker_symbol)
    info = {}
    try:
        info = company.get_info() or {}
    except Exception:
        pass

    income = company.financials
    balance = company.balance_sheet
    cashflow = company.cashflow

    context = {
        "ticker": ticker_symbol.upper(),
        "company_name": info.get("longName") or info.get("shortName") or ticker_symbol.upper(),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "currency": info.get("currency"),
        "market_cap": info.get("marketCap"),
        "data_source": "Yahoo Finance via yfinance",
        "income_statement": {
            "revenue": _series_values(income, ["Total Revenue", "Operating Revenue"]),
            "net_income": _series_values(income, ["Net Income", "Net Income Common Stockholders"]),
            "operating_income": _series_values(income, ["Operating Income"]),
            "gross_profit": _series_values(income, ["Gross Profit"]),
        },
        "balance_sheet": {
            "total_assets": _series_values(balance, ["Total Assets"]),
            "total_liabilities": _series_values(balance, ["Total Liabilities Net Minority Interest", "Total Liabilities"]),
            "total_debt": _series_values(balance, ["Total Debt", "Long Term Debt And Capital Lease Obligation"]),
            "current_assets": _series_values(balance, ["Current Assets", "Total Current Assets"]),
            "current_liabilities": _series_values(balance, ["Current Liabilities", "Total Current Liabilities"]),
            "stockholders_equity": _series_values(balance, ["Stockholders Equity", "Total Stockholder Equity", "Common Stock Equity"]),
        },
        "cash_flow": {
            "operating_cash_flow": _series_values(cashflow, ["Operating Cash Flow", "Cash Flow From Continuing Operating Activities"]),
            "capital_expenditure": _series_values(cashflow, ["Capital Expenditure", "Capital Expenditures"]),
            "free_cash_flow": _series_values(cashflow, ["Free Cash Flow"]),
        },
        "ratios": {},
        "notes": [
            "Financial statements and available periods depend on Yahoo Finance coverage.",
            "A missing value means data was not available in the retrieved statements; it should not be interpreted as zero.",
        ],
    }

    # Calculate ratios deterministically from the latest common available period.
    def latest(values):
        return next(iter(values.values()), None) if values else None

    rev = latest(context["income_statement"]["revenue"])
    net_income = latest(context["income_statement"]["net_income"])
    assets = latest(context["balance_sheet"]["total_assets"])
    debt = latest(context["balance_sheet"]["total_debt"])
    equity = latest(context["balance_sheet"]["stockholders_equity"])
    current_assets = latest(context["balance_sheet"]["current_assets"])
    current_liabilities = latest(context["balance_sheet"]["current_liabilities"])

    ratios = {}
    if rev not in (None, 0) and net_income is not None:
        ratios["net_profit_margin_percent"] = round(net_income / rev * 100, 2)
    if equity not in (None, 0) and net_income is not None:
        ratios["return_on_equity_percent"] = round(net_income / equity * 100, 2)
    if equity not in (None, 0) and debt is not None:
        ratios["debt_to_equity"] = round(debt / equity, 2)
    if current_liabilities not in (None, 0) and current_assets is not None:
        ratios["current_ratio"] = round(current_assets / current_liabilities, 2)
    if assets not in (None, 0) and net_income is not None:
        ratios["return_on_assets_percent"] = round(net_income / assets * 100, 2)
    context["ratios"] = ratios

    if not any(context["income_statement"].values()) and not any(context["balance_sheet"].values()):
        raise ValueError(
            "Yahoo Finance returned no usable financial statement data for this ticker. "
            "Check the ticker symbol or try another listed company."
        )
    return context


def render_ai_financial_analyst_chat():
    """Render an AI chat panel with context grounded in retrieved financial data."""
    st.markdown("---")
    st.subheader("💬 AI Financial Analyst")
    st.caption(
        "Ask questions about the selected company's financial statements and ratios. "
        "The assistant uses retrieved financial data and identifies missing information."
    )

    with st.expander("How this AI analyst works", expanded=False):
        st.write(
            "Python retrieves financial statements and calculates ratios. Gemini explains "
            "those results in natural language. The assistant is instructed not to invent "
            "missing figures or present its output as investment advice."
        )

    default_ticker = st.session_state.get("financial_analyst_ticker", "AAPL")
    ticker_symbol = st.text_input(
        "Company ticker for the AI analyst",
        value=default_ticker,
        key="financial_analyst_ticker_input",
        help="Examples: AAPL, MSFT, RELIANCE.NS, TCS.NS, SBIN.NS",
    ).strip().upper()

    api_key = None
    try:
        api_key = st.secrets.get("GOOGLE_API_KEY")
    except Exception:
        pass
    api_key = api_key or os.getenv("GOOGLE_API_KEY")

    if not api_key:
        st.warning(
            "Gemini API key not configured. Add GOOGLE_API_KEY to Streamlit Secrets "
            "or your local environment to enable the AI chat."
        )
        st.code('GOOGLE_API_KEY = "your-Gemini-API-key"', language="toml")
        return

    if st.button("Load financial context", key="load_financial_analyst_context"):
        try:
            with st.spinner("Retrieving financial statements..."):
                context = _build_financial_context(ticker_symbol)
            st.session_state["financial_analyst_context"] = context
            st.session_state["financial_analyst_history"] = []
            st.session_state["financial_analyst_loaded_ticker"] = ticker_symbol
            st.success(
                f"Loaded financial context for {context['company_name']} "
                f"({context['ticker']})."
            )
        except Exception as exc:
            st.error(f"Could not load financial data: {exc}")
            return

    context = st.session_state.get("financial_analyst_context")
    loaded_ticker = st.session_state.get("financial_analyst_loaded_ticker")
    if not context or loaded_ticker != ticker_symbol:
        st.info("Enter a ticker and select **Load financial context** to start chatting.")
        return

    with st.expander("Financial data supplied to the AI", expanded=False):
        st.json(context)

    history = st.session_state.setdefault("financial_analyst_history", [])
    for message in history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    prompt = st.chat_input(
        f"Ask about {context['company_name']}'s financial health...",
        key="financial_analyst_chat_input",
    )
    if prompt:
        history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        system_instruction = """
You are an AI Financial Analyst for an educational analytics application.
Use only the supplied financial context for company-specific numerical claims.
Do not invent data, dates, ratios, or causes. If the context does not contain enough
evidence, clearly say what is missing. Distinguish facts from interpretations.
Explain financial concepts in accessible language. When comparing periods, use the
period labels supplied in the data and do not assume their order if unclear.
Do not provide personalized investment recommendations, price targets, or guarantees.
Mention that Yahoo Finance data may be incomplete or delayed and that this is educational
analysis, not professional financial advice. Keep answers structured and concise.
"""
        # Keep the most recent conversation turns to limit request size.
        recent_history = history[-10:]
        conversation = "\n\n".join(
            f"{m['role'].upper()}: {m['content']}" for m in recent_history
        )
        full_prompt = (
            f"{system_instruction}\n\nFINANCIAL CONTEXT (JSON):\n"
            f"{json.dumps(context, ensure_ascii=False, default=str)}\n\n"
            f"CONVERSATION:\n{conversation}\n\n"
            "Respond to the latest user question. Ground all company-specific claims "
            "in the financial context above."
        )

        with st.chat_message("assistant"):
            try:
                with st.spinner("Analyzing the financial context..."):
                    client = genai.Client(api_key=api_key)
                    response = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=full_prompt,
                    )
                    answer = (response.text or "").strip()
                    if not answer:
                        answer = "The AI model returned an empty response. Please try again."
                st.markdown(answer)
                history.append({"role": "assistant", "content": answer})
            except Exception as exc:
                st.error(
                    "The AI request failed. Check that the API key is valid, the Gemini "
                    "API is enabled, and your quota is available. Technical details: "
                    f"{exc}"
                )

    if history and st.button("Clear chat", key="clear_financial_analyst_chat"):
        st.session_state["financial_analyst_history"] = []
        st.rerun()
