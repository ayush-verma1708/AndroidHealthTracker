import pandas as pd
import numpy as np

def generate_signals(df, rsi_overbought=70, rsi_oversold=30):
    """
    Generate trading signals based on various technical indicators.
    
    Args:
        df (pandas.DataFrame): The stock data DataFrame with calculated indicators.
        rsi_overbought (int): RSI threshold for overbought condition.
        rsi_oversold (int): RSI threshold for oversold condition.
        
    Returns:
        pandas.DataFrame: The updated DataFrame with trading signals.
    """
    # Create a copy to avoid SettingWithCopyWarning
    dataframe = df.copy()
    
    # Initialize signal column with 0 (no signal)
    dataframe['signal'] = 0
    
    # Moving Average Crossover
    ma_cols = [col for col in dataframe.columns if col.startswith('MA_')]
    if len(ma_cols) >= 2:
        # Get shortest and longest periods
        short_ma_col = min(ma_cols, key=lambda x: int(x.split('_')[1]))
        long_ma_col = max(ma_cols, key=lambda x: int(x.split('_')[1]))
        
        # Create crossover signals
        # 1 when short crosses above long (bullish), -1 when short crosses below long (bearish)
        dataframe['ma_cross'] = 0
        dataframe.loc[(dataframe[short_ma_col] > dataframe[long_ma_col]) & 
                     (dataframe[short_ma_col].shift(1) <= dataframe[long_ma_col].shift(1)), 'ma_cross'] = 1
        dataframe.loc[(dataframe[short_ma_col] < dataframe[long_ma_col]) & 
                     (dataframe[short_ma_col].shift(1) >= dataframe[long_ma_col].shift(1)), 'ma_cross'] = -1
    
    # RSI Signals
    if 'RSI' in dataframe.columns:
        dataframe['rsi_signal'] = 0
        # Oversold to normal - buy signal
        dataframe.loc[(dataframe['RSI'] > rsi_oversold) & 
                     (dataframe['RSI'].shift(1) <= rsi_oversold), 'rsi_signal'] = 1
        # Overbought to normal - sell signal
        dataframe.loc[(dataframe['RSI'] < rsi_overbought) & 
                     (dataframe['RSI'].shift(1) >= rsi_overbought), 'rsi_signal'] = -1
    
    # MACD Signals
    if all(x in dataframe.columns for x in ['MACD', 'MACD_signal']):
        dataframe['macd_cross'] = 0
        # MACD crosses above signal line - buy signal
        dataframe.loc[(dataframe['MACD'] > dataframe['MACD_signal']) & 
                     (dataframe['MACD'].shift(1) <= dataframe['MACD_signal'].shift(1)), 'macd_cross'] = 1
        # MACD crosses below signal line - sell signal
        dataframe.loc[(dataframe['MACD'] < dataframe['MACD_signal']) & 
                     (dataframe['MACD'].shift(1) >= dataframe['MACD_signal'].shift(1)), 'macd_cross'] = -1
    
    # Bollinger Bands Signals
    if all(x in dataframe.columns for x in ['BB_upper', 'BB_lower', 'Close']):
        dataframe['bb_signal'] = 0
        # Price crosses below lower band and then back above - buy signal
        below_lower = dataframe['Close'] < dataframe['BB_lower']
        cross_back_above_lower = (dataframe['Close'] > dataframe['BB_lower']) & (dataframe['Close'].shift(1) <= dataframe['BB_lower'].shift(1))
        dataframe.loc[below_lower.shift(1) & cross_back_above_lower, 'bb_signal'] = 1
        
        # Price crosses above upper band and then back below - sell signal
        above_upper = dataframe['Close'] > dataframe['BB_upper']
        cross_back_below_upper = (dataframe['Close'] < dataframe['BB_upper']) & (dataframe['Close'].shift(1) >= dataframe['BB_upper'].shift(1))
        dataframe.loc[above_upper.shift(1) & cross_back_below_upper, 'bb_signal'] = -1
    
    # Combine signals to generate overall trading signal
    # We'll use a simple approach here, but this can be made more sophisticated
    # If 2 or more indicators agree, we generate a signal
    signal_columns = [col for col in dataframe.columns if col.endswith('_signal') or col.endswith('_cross')]
    if signal_columns:
        # Count positive and negative signals for each row
        positive_signals = dataframe[signal_columns].apply(lambda row: sum(row > 0), axis=1)
        negative_signals = dataframe[signal_columns].apply(lambda row: sum(row < 0), axis=1)
        
        # Generate overall signal based on indicator agreement
        dataframe.loc[positive_signals >= 2, 'signal'] = 1  # Buy signal
        dataframe.loc[negative_signals >= 2, 'signal'] = -1  # Sell signal
    
    return dataframe

def calculate_composite_score(df):
    """
    Calculate a composite score for trading signals based on multiple indicators.
    
    Args:
        df (pandas.DataFrame): The stock data DataFrame with calculated indicators.
        
    Returns:
        pandas.DataFrame: The updated DataFrame with composite score.
    """
    # Create a copy to avoid SettingWithCopyWarning
    dataframe = df.copy()
    
    # Initialize the composite score - default is 0.5 (neutral)
    dataframe['composite_score'] = 0.5
    
    # Weights for different components
    weights = {
        'rsi': 0.25,
        'macd': 0.25,
        'ma_trend': 0.25,
        'bb': 0.25
    }
    
    # Component 1: RSI (0-1 scale)
    if 'RSI' in dataframe.columns:
        # Convert RSI from 0-100 to 0-1 (higher RSI = higher score)
        dataframe['rsi_component'] = dataframe['RSI'] / 100
        
        # Adjust RSI component: lower RSI values are bullish, higher are bearish
        # Invert the scale: 1.0 - (RSI/100) to make oversold conditions (low RSI) more bullish
        # When RSI is near 30: component will be ~0.7
        # When RSI is near 70: component will be ~0.3
        dataframe['rsi_component'] = 1.0 - dataframe['rsi_component']
    else:
        dataframe['rsi_component'] = 0.5
    
    # Component 2: MACD (0-1 scale)
    if all(x in dataframe.columns for x in ['MACD', 'MACD_signal']):
        # Calculate MACD histogram
        dataframe['macd_hist'] = dataframe['MACD'] - dataframe['MACD_signal']
        
        # Normalize MACD histogram to 0-1 range
        hist_max = dataframe['macd_hist'].abs().max()
        if hist_max != 0:
            dataframe['macd_component'] = (dataframe['macd_hist'] / (2 * hist_max)) + 0.5
            dataframe['macd_component'] = dataframe['macd_component'].clip(0, 1)
        else:
            dataframe['macd_component'] = 0.5
    else:
        dataframe['macd_component'] = 0.5
    
    # Component 3: Moving Average Trend (0-1 scale)
    ma_cols = [col for col in dataframe.columns if col.startswith('MA_')]
    if len(ma_cols) >= 2:
        # Get shortest and longest periods
        short_ma_col = min(ma_cols, key=lambda x: int(x.split('_')[1]))
        long_ma_col = max(ma_cols, key=lambda x: int(x.split('_')[1]))
        
        # Calculate trend strength
        dataframe['ma_diff'] = (dataframe[short_ma_col] - dataframe[long_ma_col]) / dataframe[long_ma_col]
        
        # Normalize to 0-1 range
        max_diff = dataframe['ma_diff'].abs().max()
        if max_diff != 0:
            dataframe['ma_trend_component'] = (dataframe['ma_diff'] / (2 * max_diff)) + 0.5
            dataframe['ma_trend_component'] = dataframe['ma_trend_component'].clip(0, 1)
        else:
            dataframe['ma_trend_component'] = 0.5
    else:
        dataframe['ma_trend_component'] = 0.5
    
    # Component 4: Bollinger Band Position (0-1 scale)
    if all(x in dataframe.columns for x in ['BB_upper', 'BB_middle', 'BB_lower', 'Close']):
        # Calculate position within Bollinger Bands
        # 0 = at or below lower band, 0.5 = at middle band, 1 = at or above upper band
        bb_range = dataframe['BB_upper'] - dataframe['BB_lower']
        bb_position = (dataframe['Close'] - dataframe['BB_lower']) / bb_range
        
        # Invert the scale: when price is near lower band (oversold), component is high (bullish)
        # when price is near upper band (overbought), component is low (bearish)
        dataframe['bb_component'] = 1.0 - bb_position
        dataframe['bb_component'] = dataframe['bb_component'].clip(0, 1)
    else:
        dataframe['bb_component'] = 0.5
    
    # Combine components with weights to get composite score
    dataframe['composite_score'] = (
        weights['rsi'] * dataframe['rsi_component'] +
        weights['macd'] * dataframe['macd_component'] +
        weights['ma_trend'] * dataframe['ma_trend_component'] +
        weights['bb'] * dataframe['bb_component']
    )
    
    # Ensure the score is within 0-1 range
    dataframe['composite_score'] = dataframe['composite_score'].clip(0, 1)
    
    return dataframe