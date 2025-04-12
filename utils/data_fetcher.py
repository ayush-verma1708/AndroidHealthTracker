import pandas as pd
import numpy as np
import yfinance as yf
import time
import re

def get_available_stocks(search_term):
    """
    Searches for available stocks based on the search term.
    
    Args:
        search_term (str): The search term to look for in stock tickers or names.
        
    Returns:
        list: A list of matching stock tickers.
    """
    # Common stock tickers from major markets as a fallback
    common_stocks = {
        'AAPL': 'Apple Inc.',
        'MSFT': 'Microsoft Corporation',
        'AMZN': 'Amazon.com, Inc.',
        'GOOGL': 'Alphabet Inc.',
        'META': 'Meta Platforms, Inc.',
        'TSLA': 'Tesla, Inc.',
        'NVDA': 'NVIDIA Corporation',
        'JPM': 'JPMorgan Chase & Co.',
        'V': 'Visa Inc.',
        'JNJ': 'Johnson & Johnson',
        'WMT': 'Walmart Inc.',
        'PG': 'Procter & Gamble Co.',
        'MA': 'Mastercard Incorporated',
        'UNH': 'UnitedHealth Group Incorporated',
        'HD': 'The Home Depot, Inc.',
        'BAC': 'Bank of America Corporation',
        'XOM': 'Exxon Mobil Corporation',
        'INTC': 'Intel Corporation',
        'VZ': 'Verizon Communications Inc.',
        'CSCO': 'Cisco Systems, Inc.',
        'NFLX': 'Netflix, Inc.',
        'ADBE': 'Adobe Inc.',
        'DIS': 'The Walt Disney Company',
        'CRM': 'Salesforce, Inc.',
        'KO': 'The Coca-Cola Company'
    }
    
    # Check if the search term is a valid ticker
    search_term = search_term.upper()
    
    if search_term in common_stocks:
        return [search_term]
    
    # If not an exact match, look for partial matches
    matches = []
    for ticker, name in common_stocks.items():
        if search_term in ticker or search_term.lower() in name.lower():
            matches.append(ticker)
    
    # If we have too many matches, limit to 10
    if len(matches) > 10:
        matches = matches[:10]
        
    return matches

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
        # Download data from Yahoo Finance
        stock = yf.Ticker(ticker)
        df = stock.history(period=period, interval=interval)
        
        # If DataFrame is empty, return None
        if df.empty:
            return None
        
        # Calculate percentage change
        df['Close_pct_change'] = df['Close'].pct_change() * 100
        
        return df
    except Exception as e:
        print(f"Error fetching data for {ticker}: {e}")
        return None
