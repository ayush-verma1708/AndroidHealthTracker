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
    # Current price to use as reference
    current_price = latest_data['Close']
    
    # Calculate ATR for determining stop-loss distance
    atr = calculate_atr(historical_data)
    latest_atr = atr.iloc[-1] if not atr.empty and not np.isnan(atr.iloc[-1]) else current_price * 0.01
    
    # Get composite score for directional bias
    composite_score = latest_data.get('composite_score', 0.5)
    
    # Determine if we're bullish (> 0.6) or bearish (< 0.4)
    is_bullish = composite_score > 0.6
    is_bearish = composite_score < 0.4
    
    # Calculate support and resistance
    support, resistance = calculate_support_resistance(historical_data)
    
    # Adjust for missing or invalid values
    if np.isnan(support) or support <= 0:
        support = current_price * 0.95
    if np.isnan(resistance) or resistance <= 0:
        resistance = current_price * 1.05
    
    # Default risk parameters
    entry_price = current_price
    stop_loss = current_price * 0.95
    take_profit = current_price * 1.05
    
    # Adjust based on market bias
    if is_bullish:
        # For bullish signals, entry at current price or slightly below
        entry_price = current_price
        
        # Stop loss below support or using ATR
        stop_loss = max(support * 0.99, current_price - (2 * latest_atr))
        
        # Take profit at resistance or with risk-reward ratio of 2:1
        risk_amount = entry_price - stop_loss
        take_profit = entry_price + (risk_amount * 2)
    
    elif is_bearish:
        # For bearish signals, entry at current price or slightly above
        entry_price = current_price
        
        # Stop loss above resistance or using ATR
        stop_loss = min(resistance * 1.01, current_price + (2 * latest_atr))
        
        # Take profit at support or with risk-reward ratio of 2:1
        risk_amount = stop_loss - entry_price
        take_profit = entry_price - (risk_amount * 2)
    
    else:
        # Neutral - use technical levels
        entry_price = current_price
        stop_loss = current_price - latest_atr
        take_profit = current_price + latest_atr
    
    # Ensure stop loss doesn't exceed risk percentage of account
    # This is a placeholder - in a real system you'd use account equity
    # For now we'll assume it's proportional to the stock price
    max_risk_amount = current_price * (risk_percentage / 100)
    
    if is_bullish and (entry_price - stop_loss) > max_risk_amount:
        stop_loss = entry_price - max_risk_amount
    elif is_bearish and (stop_loss - entry_price) > max_risk_amount:
        stop_loss = entry_price + max_risk_amount
    
    # Round to 2 decimal places for readability
    entry_price = round(entry_price, 2)
    stop_loss = round(stop_loss, 2)
    take_profit = round(take_profit, 2)
    
    return {
        'entry_price': entry_price,
        'stop_loss': stop_loss,
        'take_profit': take_profit
    }
