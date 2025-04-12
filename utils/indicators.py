import pandas as pd
import numpy as np

def calculate_indicators(df, short_ma=20, long_ma=50, rsi_period=14, 
                        macd_fast=12, macd_slow=26, macd_signal=9,
                        bb_period=20, bb_std=2.0):
    """
    Calculate various technical indicators for the stock data.
    
    Args:
        df (pandas.DataFrame): The stock data DataFrame with OHLC data.
        short_ma (int): Period for short moving average.
        long_ma (int): Period for long moving average.
        rsi_period (int): Period for RSI calculation.
        macd_fast (int): Fast period for MACD.
        macd_slow (int): Slow period for MACD.
        macd_signal (int): Signal period for MACD.
        bb_period (int): Period for Bollinger Bands calculation.
        bb_std (float): Standard deviation multiplier for Bollinger Bands.
        
    Returns:
        pandas.DataFrame: The updated DataFrame with calculated indicators.
    """
    # Make a copy to avoid SettingWithCopyWarning
    dataframe = df.copy()
    
    # Moving Averages
    dataframe[f'MA_{short_ma}'] = dataframe['Close'].rolling(window=short_ma).mean()
    dataframe[f'MA_{long_ma}'] = dataframe['Close'].rolling(window=long_ma).mean()
    
    # Relative Strength Index (RSI)
    delta = dataframe['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
    
    rs = gain / loss
    dataframe['RSI'] = 100 - (100 / (1 + rs))
    
    # MACD
    ema_fast = dataframe['Close'].ewm(span=macd_fast, adjust=False).mean()
    ema_slow = dataframe['Close'].ewm(span=macd_slow, adjust=False).mean()
    dataframe['MACD'] = ema_fast - ema_slow
    dataframe['MACD_signal'] = dataframe['MACD'].ewm(span=macd_signal, adjust=False).mean()
    dataframe['MACD_hist'] = dataframe['MACD'] - dataframe['MACD_signal']
    
    # Bollinger Bands
    dataframe['BB_middle'] = dataframe['Close'].rolling(window=bb_period).mean()
    dataframe['BB_std'] = dataframe['Close'].rolling(window=bb_period).std()
    dataframe['BB_upper'] = dataframe['BB_middle'] + (dataframe['BB_std'] * bb_std)
    dataframe['BB_lower'] = dataframe['BB_middle'] - (dataframe['BB_std'] * bb_std)
    
    # Fill NaN values with 0
    dataframe.fillna(0, inplace=True)
    
    return dataframe

def calculate_atr(df, period=14):
    """
    Calculate Average True Range (ATR) for risk management.
    
    Args:
        df (pandas.DataFrame): The stock data DataFrame with OHLC data.
        period (int): Period for ATR calculation.
        
    Returns:
        pandas.Series: The ATR values.
    """
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = true_range.rolling(window=period).mean()
    
    return atr

def calculate_support_resistance(df, window=10):
    """
    Calculate basic support and resistance levels.
    
    Args:
        df (pandas.DataFrame): The stock data DataFrame with OHLC data.
        window (int): Look-back window to identify support/resistance points.
        
    Returns:
        dict: Dictionary containing support and resistance prices.
    """
    recent_df = df.tail(window)
    support = recent_df['Low'].min()
    resistance = recent_df['High'].max()
    
    return {'support': support, 'resistance': resistance}
