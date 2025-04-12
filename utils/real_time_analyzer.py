import pandas as pd
import numpy as np
import datetime
import time
import threading
import streamlit as st
from utils.data_fetcher import fetch_stock_data
from utils.indicators import calculate_indicators
from utils.signal_generator import generate_signals, calculate_composite_score
from utils.risk_manager import calculate_risk_parameters
from utils.alert_manager import send_trading_signal_alert, notify_app_alert

class RealTimeAnalyzer:
    """
    Class to handle real-time stock analysis and generating trading signals
    """
    
    def __init__(self, interval="1m", lookback_period="1d"):
        """
        Initialize the real-time analyzer
        
        Args:
            interval (str): Data interval for analysis (default: 1m)
            lookback_period (str): Period to look back for historical data (default: 1d)
        """
        self.interval = interval
        self.lookback_period = lookback_period
        self.monitoring_thread = None
        self.stop_event = threading.Event()
        self.last_signal_time = {}  # To track when last signal was generated for each stock
        self.monitoring_active = False
        
    def analyze_stock(self, ticker, indicator_settings):
        """
        Analyze a single stock and return the analysis results
        
        Args:
            ticker (str): Stock ticker symbol
            indicator_settings (dict): Technical indicator settings
            
        Returns:
            dict: Analysis results or None if error
        """
        try:
            # Fetch latest data
            df = fetch_stock_data(ticker, period=self.lookback_period, interval=self.interval)
            
            if df is None or df.empty:
                return None
                
            # Calculate indicators
            df = calculate_indicators(
                df,
                short_ma=indicator_settings.get('short_ma', 20),
                long_ma=indicator_settings.get('long_ma', 50),
                rsi_period=indicator_settings.get('rsi_period', 14),
                macd_fast=indicator_settings.get('macd_fast', 12),
                macd_slow=indicator_settings.get('macd_slow', 26),
                macd_signal=indicator_settings.get('macd_signal', 9),
                bb_period=indicator_settings.get('bb_period', 20),
                bb_std=indicator_settings.get('bb_std', 2)
            )
            
            # Generate signals
            df = generate_signals(
                df,
                rsi_overbought=indicator_settings.get('rsi_overbought', 70),
                rsi_oversold=indicator_settings.get('rsi_oversold', 30)
            )
            
            # Calculate composite score
            df = calculate_composite_score(df)
            
            # Calculate risk parameters for the latest data point
            latest_data = df.iloc[-1]
            risk_params = calculate_risk_parameters(
                latest_data,
                df,
                risk_percentage=indicator_settings.get('risk_percentage', 1.0)
            )
            
            # Determine signal type
            signal = self._determine_real_time_signal(df, ticker)
            
            # Return the analysis result
            return {
                'ticker': ticker,
                'timestamp': datetime.datetime.now(),
                'latest_data': latest_data,
                'risk_params': risk_params,
                'signal': signal,
                'data': df
            }
        
        except Exception as e:
            st.error(f"Error analyzing {ticker}: {str(e)}")
            return None
    
    def _determine_real_time_signal(self, df, ticker):
        """
        Determine real-time trading signal based on the latest data
        
        Args:
            df (pandas.DataFrame): DataFrame with calculated indicators
            ticker (str): Stock ticker symbol
            
        Returns:
            dict: Signal information
        """
        if df.empty:
            return {'type': 'UNKNOWN', 'strength': 0, 'desc': 'No data available'}
            
        # Get latest data point
        latest = df.iloc[-1]
        
        # Get previous data point for comparison (if available)
        prev = df.iloc[-2] if len(df) > 1 else latest
        
        # Determine trading signal strength (composite score)
        score = latest['composite_score']
        
        # Check if there's a signal in the last data point
        recent_signal = latest['signal']
        
        # Define price momentum
        price_rising = latest['Close'] > prev['Close']
        
        # Check for recent crossover of MACD
        macd_bullish_cross = (latest['MACD'] > latest['MACD_signal']) and (prev['MACD'] <= prev['MACD_signal'])
        macd_bearish_cross = (latest['MACD'] < latest['MACD_signal']) and (prev['MACD'] >= prev['MACD_signal'])
        
        # Check for recent crossover of moving averages
        ma_cols = [col for col in df.columns if col.startswith('MA_')]
        if len(ma_cols) >= 2:
            short_ma_col = min(ma_cols, key=lambda x: int(x.split('_')[1]))
            long_ma_col = max(ma_cols, key=lambda x: int(x.split('_')[1]))
            
            ma_bullish_cross = (latest[short_ma_col] > latest[long_ma_col]) and (prev[short_ma_col] <= prev[long_ma_col])
            ma_bearish_cross = (latest[short_ma_col] < latest[long_ma_col]) and (prev[short_ma_col] >= prev[long_ma_col])
        else:
            ma_bullish_cross = False
            ma_bearish_cross = False
        
        # Determine signal type based on portfolio state and indicators
        if ticker in st.session_state.portfolio:
            # We own this stock - should we HOLD or SELL?
            position = st.session_state.portfolio[ticker]
            position_type = position.get('position_type', 'LONG')
            
            if position_type == 'LONG':
                # For LONG positions
                if score < 0.4 or macd_bearish_cross or ma_bearish_cross:
                    signal_type = 'SELL'
                    signal_desc = "Sell signal triggered based on bearish indicators."
                    signal_strength = 1 - score  # Higher strength for lower scores
                else:
                    signal_type = 'HOLD'
                    signal_desc = "Continue holding the long position."
                    signal_strength = 0.5
            else:
                # For SHORT positions
                if score > 0.6 or macd_bullish_cross or ma_bullish_cross:
                    signal_type = 'COVER'
                    signal_desc = "Cover signal triggered based on bullish indicators."
                    signal_strength = score  # Higher strength for higher scores
                else:
                    signal_type = 'HOLD'
                    signal_desc = "Continue holding the short position."
                    signal_strength = 0.5
                
        else:
            # We don't own this stock - should we BUY or SHORT?
            if score > 0.6 or macd_bullish_cross or ma_bullish_cross:
                if recent_signal == 1:  # Bullish signal in indicators
                    signal_type = 'BUY'
                    signal_desc = "Buy signal triggered based on bullish indicators."
                    signal_strength = score
                else:
                    signal_type = 'WAIT'
                    signal_desc = "Watching for confirmation of bullish trend."
                    signal_strength = score * 0.7
            elif score < 0.4 or macd_bearish_cross or ma_bearish_cross:
                if recent_signal == -1:  # Bearish signal in indicators
                    signal_type = 'SHORT'
                    signal_desc = "Short signal triggered based on bearish indicators."
                    signal_strength = 1 - score
                else:
                    signal_type = 'WAIT'
                    signal_desc = "Watching for confirmation of bearish trend."
                    signal_strength = (1 - score) * 0.7
            else:
                signal_type = 'WAIT'
                signal_desc = "No clear signal. Wait for more definitive movement."
                signal_strength = 0.5
        
        # Return the signal information
        return {
            'type': signal_type,
            'strength': signal_strength,
            'score': score,
            'desc': signal_desc,
            'time': datetime.datetime.now()
        }
    
    def start_monitoring(self, watchlist, indicator_settings, alert_phone=None, alert_frequency=15):
        """
        Start monitoring stocks in the watchlist in real-time
        
        Args:
            watchlist (list): List of stock tickers to monitor
            indicator_settings (dict): Technical indicator settings
            alert_phone (str): Phone number to send alerts to
            alert_frequency (int): Minimum minutes between alerts for the same stock
            
        Returns:
            bool: True if monitoring thread started, False otherwise
        """
        if self.monitoring_active:
            return False
            
        self.stop_event.clear()
        self.monitoring_active = True
        
        # Initialize alert log if it doesn't exist
        if 'alert_log' not in st.session_state:
            st.session_state.alert_log = []
            
        # Initialize app alerts if they don't exist
        if 'app_alerts' not in st.session_state:
            st.session_state.app_alerts = []
            
        # Start monitoring thread
        self.monitoring_thread = threading.Thread(
            target=self._monitor_stocks,
            args=(watchlist, indicator_settings, alert_phone, alert_frequency),
            daemon=True
        )
        self.monitoring_thread.start()
        
        return True
    
    def stop_monitoring(self):
        """
        Stop the real-time monitoring thread
        
        Returns:
            bool: True if stopped, False if not monitoring
        """
        if not self.monitoring_active:
            return False
            
        self.stop_event.set()
        self.monitoring_active = False
        
        return True
    
    def _monitor_stocks(self, watchlist, indicator_settings, alert_phone, alert_frequency):
        """
        Internal method to continuously monitor stocks
        
        Args:
            watchlist (list): List of stock tickers to monitor
            indicator_settings (dict): Technical indicator settings
            alert_phone (str): Phone number to send alerts to
            alert_frequency (int): Minimum minutes between alerts for the same stock
        """
        while not self.stop_event.is_set():
            for ticker in watchlist:
                # Skip if the market is closed (simplified check for now)
                now = datetime.datetime.now()
                if now.hour < 9 or now.hour >= 16 or now.weekday() >= 5:  # Outside 9AM-4PM or weekend
                    continue
                    
                # Analyze the stock
                analysis = self.analyze_stock(ticker, indicator_settings)
                
                if analysis:
                    signal = analysis['signal']
                    
                    # Check if this is a significant signal that needs an alert
                    if signal['type'] in ['BUY', 'SELL', 'SHORT', 'COVER'] and signal['strength'] > 0.65:
                        # Check if we've recently sent an alert for this stock
                        can_send_alert = True
                        
                        if ticker in self.last_signal_time:
                            time_since_last = (datetime.datetime.now() - self.last_signal_time[ticker]).total_seconds() / 60
                            if time_since_last < alert_frequency:
                                can_send_alert = False
                        
                        if can_send_alert:
                            # Update the last signal time
                            self.last_signal_time[ticker] = datetime.datetime.now()
                            
                            # Store alert in the app
                            notify_app_alert(
                                ticker, 
                                signal['type'], 
                                analysis['latest_data']['Close'], 
                                signal['score']
                            )
                            
                            # Send SMS alert if phone number is provided
                            if alert_phone:
                                send_trading_signal_alert(
                                    ticker,
                                    signal['type'],
                                    analysis['latest_data']['Close'],
                                    signal['score'],
                                    alert_phone
                                )
            
            # Sleep for a minute before checking again
            time.sleep(60)