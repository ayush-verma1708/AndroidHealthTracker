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
    # Make a copy to avoid SettingWithCopyWarning
    dataframe = df.copy()
    
    # Initialize signal column with 0 (no signal)
    dataframe['signal'] = 0
    
    # Look for short_ma and long_ma columns
    ma_columns = [col for col in dataframe.columns if col.startswith('MA_')]
    if len(ma_columns) >= 2:
        short_ma_col = min(ma_columns, key=lambda x: int(x.split('_')[1]))
        long_ma_col = max(ma_columns, key=lambda x: int(x.split('_')[1]))
        
        # Moving Average Crossover Signal
        # Buy when short MA crosses above long MA
        ma_crossover_buy = (dataframe[short_ma_col] > dataframe[long_ma_col]) & \
                           (dataframe[short_ma_col].shift() <= dataframe[long_ma_col].shift())
        
        # Sell when short MA crosses below long MA
        ma_crossover_sell = (dataframe[short_ma_col] < dataframe[long_ma_col]) & \
                            (dataframe[short_ma_col].shift() >= dataframe[long_ma_col].shift())
        
        # Update signals based on MA crossover
        dataframe.loc[ma_crossover_buy, 'signal'] = 1
        dataframe.loc[ma_crossover_sell, 'signal'] = -1
    
    # RSI Signals
    if 'RSI' in dataframe.columns:
        # Buy when RSI crosses above oversold threshold from below
        rsi_buy = (dataframe['RSI'] > rsi_oversold) & (dataframe['RSI'].shift() <= rsi_oversold)
        
        # Sell when RSI crosses below overbought threshold from above
        rsi_sell = (dataframe['RSI'] < rsi_overbought) & (dataframe['RSI'].shift() >= rsi_overbought)
        
        # Update signals based on RSI
        dataframe.loc[rsi_buy & (dataframe['signal'] == 0), 'signal'] = 1
        dataframe.loc[rsi_sell & (dataframe['signal'] == 0), 'signal'] = -1
    
    # MACD Signals
    if all(col in dataframe.columns for col in ['MACD', 'MACD_signal']):
        # Buy when MACD crosses above signal line
        macd_buy = (dataframe['MACD'] > dataframe['MACD_signal']) & \
                   (dataframe['MACD'].shift() <= dataframe['MACD_signal'].shift())
        
        # Sell when MACD crosses below signal line
        macd_sell = (dataframe['MACD'] < dataframe['MACD_signal']) & \
                    (dataframe['MACD'].shift() >= dataframe['MACD_signal'].shift())
        
        # Update signals based on MACD
        dataframe.loc[macd_buy & (dataframe['signal'] == 0), 'signal'] = 1
        dataframe.loc[macd_sell & (dataframe['signal'] == 0), 'signal'] = -1
    
    # Bollinger Bands Signals
    if all(col in dataframe.columns for col in ['BB_upper', 'BB_lower']):
        # Buy when price touches or crosses below the lower band
        bb_buy = dataframe['Close'] <= dataframe['BB_lower']
        
        # Sell when price touches or crosses above the upper band
        bb_sell = dataframe['Close'] >= dataframe['BB_upper']
        
        # Update signals based on Bollinger Bands
        dataframe.loc[bb_buy & (dataframe['signal'] == 0), 'signal'] = 1
        dataframe.loc[bb_sell & (dataframe['signal'] == 0), 'signal'] = -1
    
    return dataframe

def calculate_composite_score(df):
    """
    Calculate a composite score for trading signals based on multiple indicators.
    
    Args:
        df (pandas.DataFrame): The stock data DataFrame with calculated indicators.
        
    Returns:
        pandas.DataFrame: The updated DataFrame with composite score.
    """
    # Make a copy to avoid SettingWithCopyWarning
    dataframe = df.copy()
    
    # Initialize the composite score
    dataframe['composite_score'] = 0.5  # Neutral starting point
    
    # Count how many indicators we have to normalize the score
    indicator_count = 0
    
    # RSI contribution (normalize to 0-1 range)
    if 'RSI' in dataframe.columns:
        # Transform RSI (0-100) to a 0-1 score
        # RSI near 0 is strong buy (1.0), RSI near 100 is strong sell (0.0)
        rsi_score = 1 - (dataframe['RSI'] / 100)
        dataframe['composite_score'] += rsi_score
        indicator_count += 1
    
    # Moving Average contribution
    ma_columns = [col for col in dataframe.columns if col.startswith('MA_')]
    if len(ma_columns) >= 2:
        short_ma_col = min(ma_columns, key=lambda x: int(x.split('_')[1]))
        long_ma_col = max(ma_columns, key=lambda x: int(x.split('_')[1]))
        
        # If price > short MA > long MA: bullish (1.0)
        # If price < short MA < long MA: bearish (0.0)
        # Other cases: neutral (0.5)
        ma_score = np.where(
            (dataframe['Close'] > dataframe[short_ma_col]) & 
            (dataframe[short_ma_col] > dataframe[long_ma_col]),
            1.0,  # Bullish
            np.where(
                (dataframe['Close'] < dataframe[short_ma_col]) & 
                (dataframe[short_ma_col] < dataframe[long_ma_col]),
                0.0,  # Bearish
                0.5   # Neutral
            )
        )
        dataframe['composite_score'] += ma_score
        indicator_count += 1
    
    # MACD contribution
    if all(col in dataframe.columns for col in ['MACD', 'MACD_signal']):
        # MACD above signal line and positive histogram: bullish
        # MACD below signal line and negative histogram: bearish
        macd_score = np.where(
            (dataframe['MACD'] > dataframe['MACD_signal']) & (dataframe['MACD_hist'] > 0),
            1.0,  # Bullish
            np.where(
                (dataframe['MACD'] < dataframe['MACD_signal']) & (dataframe['MACD_hist'] < 0),
                0.0,  # Bearish
                0.5   # Neutral
            )
        )
        dataframe['composite_score'] += macd_score
        indicator_count += 1
    
    # Bollinger Bands contribution
    if all(col in dataframe.columns for col in ['BB_upper', 'BB_middle', 'BB_lower']):
        # Price near lower band: bullish
        # Price near upper band: bearish
        # Price near middle band: neutral
        bb_range = dataframe['BB_upper'] - dataframe['BB_lower']
        normalized_price = (dataframe['Close'] - dataframe['BB_lower']) / bb_range
        
        # Transform to 0-1 score where 0 is upper band (bearish) and 1 is lower band (bullish)
        bb_score = 1 - normalized_price
        
        # Clip to handle outliers
        bb_score = np.clip(bb_score, 0, 1)
        
        dataframe['composite_score'] += bb_score
        indicator_count += 1
    
    # Normalize the composite score by the number of indicators
    if indicator_count > 0:
        dataframe['composite_score'] = dataframe['composite_score'] / (indicator_count + 1)  # +1 for the initial neutral score
    
    return dataframe
