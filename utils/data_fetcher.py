import yfinance as yf
import pandas as pd
import streamlit as st
import time

# Cache of popular stocks
POPULAR_STOCKS = {
    "AAPL": "Apple Inc.",
    "MSFT": "Microsoft Corporation",
    "GOOGL": "Alphabet Inc.",
    "AMZN": "Amazon.com Inc.",
    "TSLA": "Tesla Inc.",
    "META": "Meta Platforms Inc. (Facebook)",
    "NVDA": "NVIDIA Corporation",
    "JPM": "JPMorgan Chase & Co.",
    "V": "Visa Inc.",
    "WMT": "Walmart Inc.",
    "RELIANCE.NS": "Reliance Industries Ltd.",
    "TCS.NS": "Tata Consultancy Services Ltd.",
    "HDFCBANK.NS": "HDFC Bank Ltd.",
    "INFY.NS": "Infosys Ltd.",
    "ICICIBANK.NS": "ICICI Bank Ltd.",
    "HINDUNILVR.NS": "Hindustan Unilever Ltd.",
    "KOTAKBANK.NS": "Kotak Mahindra Bank Ltd.",
    "BAJFINANCE.NS": "Bajaj Finance Ltd.",
    "SBIN.NS": "State Bank of India",
    "ASIANPAINT.NS": "Asian Paints Ltd.",
    "BP.L": "BP p.l.c.",
    "HSBA.L": "HSBC Holdings plc",
    "GSK.L": "GSK plc",
    "SHEL.L": "Shell plc",
    "AZN.L": "AstraZeneca plc",
    "AMD": "Advanced Micro Devices, Inc.",
    "INTC": "Intel Corporation",
    "CRM": "Salesforce, Inc.",
    "PYPL": "PayPal Holdings, Inc.",
    "BAC": "Bank of America Corporation",
    "GS": "The Goldman Sachs Group, Inc.",
    "C": "Citigroup Inc.",
    "SPY": "SPDR S&P 500 ETF Trust",
    "QQQ": "Invesco QQQ Trust",
    "DIA": "SPDR Dow Jones Industrial Average ETF"
}

def sanitize_ticker(ticker):
    """Sanitize ticker input to handle various formats."""
    if not ticker:
        return None

    try:
        # Handle tuple/list case
        if isinstance(ticker, (list, tuple)):
            if not ticker:
                return None
            ticker = ticker[0]

        # Convert to string and clean
        ticker = str(ticker).strip().upper()

        # Remove any invalid characters
        ticker = ''.join(c for c in ticker if c.isalnum() or c in ['.','-'])

        return ticker if ticker else None

    except Exception:
        return None

@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_stock_data(ticker, period="1d", interval="1m"):
    """Fetch stock data with robust error handling."""
    try:
        # Sanitize ticker
        clean_ticker = sanitize_ticker(ticker)
        if not clean_ticker:
            st.error("Invalid ticker symbol")
            return None

        # Fetch data with retries
        for attempt in range(3):
            try:
                data = yf.download(
                    tickers=clean_ticker,
                    period=period,
                    interval=interval,
                    progress=False,
                    timeout=10
                )

                if data is None or data.empty:
                    time.sleep(1)
                    continue

                # Verify data structure
                required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
                if not all(col in data.columns for col in required_cols):
                    continue

                # Calculate percentage change
                data['Close_pct_change'] = data['Close'].pct_change() * 100
                return data

            except Exception as e:
                if attempt == 2:  # Last attempt
                    st.error(f"Failed to fetch data for {clean_ticker}: {str(e)}")
                time.sleep(1)
                continue

        return None

    except Exception as e:
        st.error(f"Error processing request: {str(e)}")
        return None

def get_stock_suggestions(search_term):
    """Get stock suggestions with error handling."""
    try:
        if not search_term:
            return dict(list(POPULAR_STOCKS.items())[:10])

        search_term = str(search_term).lower().strip()
        matches = {k: v for k, v in POPULAR_STOCKS.items() 
                  if search_term in k.lower() or search_term in v.lower()}

        return dict(list(matches.items())[:10]) if matches else {}

    except Exception:
        return {}

@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_available_stocks(search_term):
    """Get available stocks with error handling."""
    try:
        if not search_term:
            return list(POPULAR_STOCKS.keys())[:10]

        suggestions = get_stock_suggestions(search_term)
        return list(suggestions.keys())

    except Exception:
        return []