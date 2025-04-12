import yfinance as yf
import pandas as pd
import streamlit as st
import time

# Cache of popular stocks for quick suggestions
POPULAR_STOCKS = {
    # US Stocks
    "AAPL": "Apple Inc.",
    "MSFT": "Microsoft Corporation",
    "GOOGL": "Alphabet Inc. (Google)",
    "AMZN": "Amazon.com Inc.",
    "TSLA": "Tesla Inc.",
    "META": "Meta Platforms Inc. (Facebook)",
    "NVDA": "NVIDIA Corporation",
    "JPM": "JPMorgan Chase & Co.",
    "V": "Visa Inc.",
    "WMT": "Walmart Inc.",
    # Indian Stocks
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
    # UK Stocks
    "BP.L": "BP p.l.c.",
    "HSBA.L": "HSBC Holdings plc",
    "GSK.L": "GSK plc",
    "SHEL.L": "Shell plc",
    "AZN.L": "AstraZeneca plc",
    # Tech Stocks
    "AMD": "Advanced Micro Devices, Inc.",
    "INTC": "Intel Corporation",
    "CRM": "Salesforce, Inc.",
    "PYPL": "PayPal Holdings, Inc.",
    # Finance Stocks
    "BAC": "Bank of America Corporation",
    "GS": "The Goldman Sachs Group, Inc.",
    "C": "Citigroup Inc.",
    # ETFs
    "SPY": "SPDR S&P 500 ETF Trust",
    "QQQ": "Invesco QQQ Trust",
    "DIA": "SPDR Dow Jones Industrial Average ETF"
}

@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_available_stocks(search_term):
    """
    Searches for available stocks based on the search term.
    
    Args:
        search_term (str): The search term to look for in stock tickers or names.
        
    Returns:
        list: A list of matching stock tickers.
    """
    if not search_term:
        # Return popular stocks as default suggestions
        return list(POPULAR_STOCKS.keys())
    
    search_term = search_term.lower()
    
    # First check our cached popular stocks for quick matches
    matches = []
    for ticker, name in POPULAR_STOCKS.items():
        if search_term in ticker.lower() or search_term in name.lower():
            matches.append(ticker)
    
    # If we found matches in our cached list, return them
    if matches:
        return matches
    
    # Otherwise try to search using yfinance
    try:
        # Use yfinance's search capability
        search_results = yf.Ticker(search_term)
        if hasattr(search_results, 'info') and 'symbol' in search_results.info:
            # Add the direct match if it exists
            matches.append(search_results.info['symbol'])
        
        # Try to get similar symbols
        # Note: yfinance doesn't provide a direct method for this,
        # so we'll try a few common variations
        variations = [
            f"{search_term}.NS",  # Indian stocks
            f"{search_term}.L",   # London stocks
            f"{search_term}.TO",  # Toronto stocks
            f"{search_term}.HK",  # Hong Kong stocks
        ]
        
        for var in variations:
            try:
                var_ticker = yf.Ticker(var)
                if hasattr(var_ticker, 'info') and 'symbol' in var_ticker.info:
                    matches.append(var_ticker.info['symbol'])
            except:
                continue
                
        return list(set(matches))  # Remove duplicates
    except Exception as e:
        st.warning(f"Error searching for stocks: {str(e)}")
        return []

@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_stock_data(ticker, period="1d", interval="1m"):
    """
    Fetches stock data from Yahoo Finance API.
    
    Args:
        ticker (str): The stock ticker symbol.
        period (str): The time period to fetch data for (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, etc.)
        interval (str): The data interval (1m, 2m, 5m, 15m, 30m, 60m, 1h, 1d, etc.)
        
    Returns:
        pandas.DataFrame: A DataFrame containing stock data or None if no data is available.
    """
    try:
        # Validate ticker format
        if not isinstance(ticker, str):
            st.error(f"Invalid ticker format: {ticker}")
            return None
            
        # Add retry mechanism
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Fetch data with explicit parameters
                data = yf.download(
                    tickers=ticker,
                    period=period,
                    interval=interval,
                    progress=False,
                    timeout=5,
                    prepost=True
                )
                
                # Validate returned data
                if data is None or data.empty:
                    if attempt < max_retries - 1:
                        time.sleep(1)  # Wait before retry
                        continue
                    st.warning(f"No data available for {ticker}")
                    return None
                
                # Ensure data has required columns
                required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
                if not all(col in data.columns for col in required_columns):
                    st.error(f"Incomplete data received for {ticker}")
                    return None
                    
                # Calculate percentage change
                data['Close_pct_change'] = data['Close'].pct_change() * 100
                
                return data
                
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(1)  # Wait before retry
                    continue
                st.error(f"Error fetching data for {ticker} (Attempt {attempt + 1}/{max_retries}): {str(e)}")
                return None
                
    except Exception as e:
        st.error(f"Critical error fetching data for {ticker}: {str(e)}")
        return None

def get_stock_suggestions(search_term):
    """
    Get stock suggestions based on search term.
    
    Args:
        search_term (str): The search term for stock suggestions.
        
    Returns:
        dict: Dictionary mapping ticker symbols to company names.
    """
    search_term = search_term.lower()
    suggestions = {}
    
    # Search in our predefined popular stocks first (efficient)
    for ticker, name in POPULAR_STOCKS.items():
        if search_term in ticker.lower() or search_term in name.lower():
            suggestions[ticker] = name
    
    # Limit to first 10 suggestions for performance
    if len(suggestions) > 10:
        return dict(list(suggestions.items())[:10])
        
    return suggestions