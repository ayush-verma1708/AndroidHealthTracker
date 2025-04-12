import pandas as pd
import numpy as np
from utils.indicators import calculate_atr, calculate_support_resistance

def calculate_risk_parameters(latest_data, historical_data, risk_percentage=1.0):
    """
    Calculate risk management parameters including stop-loss and take-profit levels.
    
    Args:
        latest_data (pandas.Series): The latest data point with calculated indicators.
        historical_data (pandas.DataFrame): Historical data for additional calculations.
        risk_percentage (float): Risk percentage per trade (1.0 = 1%).
        
    Returns:
        dict: Dictionary containing entry price, stop-loss and take-profit levels.
    """
    # Current price is the entry price
    entry_price = latest_data['Close']
    
    # Calculate ATR for volatility-based stop loss
    atr = calculate_atr(historical_data).iloc[-1]
    
    # Calculate support/resistance levels
    support_resistance = calculate_support_resistance(historical_data)
    support = support_resistance['support']
    resistance = support_resistance['resistance']
    
    # Determine trend direction
    if 'MA_20' in latest_data and 'MA_50' in latest_data:
        short_ma = latest_data['MA_20']
        long_ma = latest_data['MA_50']
        uptrend = short_ma > long_ma
    else:
        # Fallback if moving averages are not available
        recent_data = historical_data.tail(10)
        uptrend = recent_data['Close'].iloc[-1] > recent_data['Close'].iloc[0]
    
    # Set stop loss based on trend, volatility (ATR), and support/resistance
    if uptrend:
        # In uptrend, stop loss is below the current price
        # We use max of (entry - ATR * 2) and support for stop loss
        stop_loss = max(entry_price - (atr * 2), support)
        # Target is 1.5-2.5x the risk (risk/reward ratio)
        risk = entry_price - stop_loss
        take_profit = entry_price + (risk * 2)
    else:
        # In downtrend, stop loss is above the current price
        # We use min of (entry + ATR * 2) and resistance for stop loss
        stop_loss = min(entry_price + (atr * 2), resistance)
        # Target is 1.5-2.5x the risk (risk/reward ratio)
        risk = stop_loss - entry_price
        take_profit = entry_price - (risk * 2)
    
    # Adjust based on risk percentage
    risk_in_price = entry_price * (risk_percentage / 100)
    if uptrend:
        # Long position: we want to lose at most risk_percentage of our capital
        if entry_price - stop_loss > risk_in_price:
            stop_loss = entry_price - risk_in_price
            take_profit = entry_price + (risk_in_price * 2)
    else:
        # Short position: we want to lose at most risk_percentage of our capital
        if stop_loss - entry_price > risk_in_price:
            stop_loss = entry_price + risk_in_price
            take_profit = entry_price - (risk_in_price * 2)
    
    return {
        'entry_price': entry_price,
        'stop_loss': stop_loss,
        'take_profit': take_profit,
        'atr': atr,
        'support': support,
        'resistance': resistance,
        'uptrend': uptrend
    }