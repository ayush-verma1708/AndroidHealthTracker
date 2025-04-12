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
    "META": "Meta Platforms Inc.",
    "NVDA": "NVIDIA Corporation",
    "JPM": "JPMorgan Chase & Co.",
    "V": "Visa Inc.",
    "WMT": "Walmart Inc."
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

def fetch_stock_data(ticker, period="1d", interval="1m"):
    """
    Fetch stock data from Yahoo Finance with improved error handling.

    Args:
        ticker (str): Stock ticker symbol
        period (str): Data period (e.g., '1d', '5d', '1mo', '3mo', '1y')
        interval (str): Data interval (e.g., '1m', '5m', '15m', '30m', '60m', '1d')

    Returns:
        pandas.DataFrame or None: DataFrame with stock data or None if error
    """
    try:
        # Convert ticker to string if it's not already
        if isinstance(ticker, (list, tuple)):
            ticker = str(ticker[0])
        ticker = str(ticker).strip().upper()

        # Create Ticker object
        stock = yf.Ticker(ticker)

        # Fetch data with retry mechanism
        max_retries = 3
        for attempt in range(max_retries):
            try:
                data = stock.history(period=period, interval=interval)

                if data is None or data.empty:
                    if attempt < max_retries - 1:
                        time.sleep(1)
                        continue
                    st.warning(f"No data available for {ticker}")
                    return None

                # Calculate percentage change
                data['Close_pct_change'] = data['Close'].pct_change() * 100

                # Reset index to make datetime a column
                data = data.reset_index()
                return data

            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                st.error(f"Error fetching data for {ticker}: {str(e)}")
                return None

    except Exception as e:
        st.error(f"Critical error processing {ticker}: {str(e)}")
        return None

def get_stock_suggestions(search_term):
    """Get stock suggestions based on search term."""
    try:
        if not search_term:
            return dict(list(POPULAR_STOCKS.items())[:10])

        search_term = str(search_term).lower().strip()
        
        # First try exact matches
        exact_matches = {k: v for k, v in POPULAR_STOCKS.items() 
                        if search_term == k.lower() or search_term == v.lower()}
        if exact_matches:
            return exact_matches

        # Then try partial matches
        partial_matches = {k: v for k, v in POPULAR_STOCKS.items() 
                         if search_term in k.lower() or search_term in v.lower()}
        
        # If no matches found, try searching with yfinance
        if not partial_matches:
            try:
                import yfinance as yf
                ticker = yf.Ticker(search_term.upper())
                info = ticker.info
                if info and 'shortName' in info:
                    return {search_term.upper(): info['shortName']}
            except:
                pass

        return dict(list(partial_matches.items())[:10]) if partial_matches else {}

    except Exception as e:
        print(f"Error in get_stock_suggestions: {str(e)}")
        return {}

def get_available_stocks(search_term):
    """Get list of available stock tickers."""
    try:
        if not search_term:
            return list(POPULAR_STOCKS.keys())[:10]

        suggestions = get_stock_suggestions(search_term)
        return list(suggestions.keys())

    except Exception:
        return []