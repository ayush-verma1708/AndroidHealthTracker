import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
import time
import threading
from utils.data_fetcher import fetch_stock_data, get_available_stocks, get_stock_suggestions, POPULAR_STOCKS
from utils.indicators import calculate_indicators
from utils.signal_generator import generate_signals, calculate_composite_score
from utils.risk_manager import calculate_risk_parameters
from utils.alert_manager import send_trading_signal_alert, notify_app_alert
from utils.real_time_analyzer import RealTimeAnalyzer

# Set page title and icon
st.set_page_config(
    page_title="Real-Time Stock Analysis",
    page_icon="📈",
    layout="wide"
)

# Initialize session state variables
if 'selected_stocks' not in st.session_state:
    st.session_state.selected_stocks = []
if 'current_stock' not in st.session_state:
    st.session_state.current_stock = None
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = {}  # Will store positions: {ticker: {'quantity': qty, 'avg_price': price, 'timestamp': purchase_time, 'position_type': 'LONG' or 'SHORT'}}
if 'trades' not in st.session_state:
    st.session_state.trades = []  # Will store trade history
if 'currency' not in st.session_state:
    st.session_state.currency = 'INR'  # Default to INR
if 'broker_fee_percent' not in st.session_state:
    st.session_state.broker_fee_percent = 0.05  # Default broker fee percentage
if 'overall_pnl' not in st.session_state:
    st.session_state.overall_pnl = 0.0  # Track overall profit/loss
if 'alert_log' not in st.session_state:
    st.session_state.alert_log = []  # Track alert history
if 'app_alerts' not in st.session_state:
    st.session_state.app_alerts = []  # Store in-app alerts
if 'real_time_analyzer' not in st.session_state:
    st.session_state.real_time_analyzer = RealTimeAnalyzer()
if 'monitoring_active' not in st.session_state:
    st.session_state.monitoring_active = False
if 'user_phone' not in st.session_state:
    st.session_state.user_phone = ""  # User phone number for alerts
if 'alert_frequency' not in st.session_state:
    st.session_state.alert_frequency = 15  # Minutes between alerts

# Header
st.title("Real-Time Intraday Stock Analysis")
st.markdown("""
This tool analyzes stock data in real-time, providing trading signals, key technical indicators, 
and risk management parameters to help with your trading decisions.
""")

# Add currency selector in main area
currency_col1, currency_col2, currency_col3, currency_col4 = st.columns([1, 1, 1, 1])
with currency_col1:
    st.session_state.currency = st.selectbox(
        "Select Currency", 
        options=["INR", "USD", "EUR", "GBP", "JPY"],
        index=0
    )
    currency_symbol = "₹" if st.session_state.currency == "INR" else "$" if st.session_state.currency == "USD" else "€" if st.session_state.currency == "EUR" else "£" if st.session_state.currency == "GBP" else "¥"

with currency_col2:
    # Phone number input for SMS alerts
    st.session_state.user_phone = st.text_input(
        "Phone Number for Alerts (E.164 format)", 
        value=st.session_state.user_phone,
        help="Enter your phone number in E.164 format (e.g., +919876543210) to receive SMS alerts"
    )

with currency_col3:
    # Alert frequency settings
    st.session_state.alert_frequency = st.number_input(
        "Alert Frequency (minutes)", 
        min_value=5, 
        max_value=60, 
        value=st.session_state.alert_frequency,
        help="Minimum time between alerts for the same stock"
    )

with currency_col4:
    # Real-time monitoring toggle
    if st.session_state.monitoring_active:
        if st.button("❌ Stop Real-Time Monitoring"):
            st.session_state.real_time_analyzer.stop_monitoring()
            st.session_state.monitoring_active = False
            st.success("Real-time monitoring stopped")
            st.rerun()
    else:
        if st.button("✅ Start Real-Time Monitoring"):
            if len(st.session_state.selected_stocks) > 0:
                # Collect indicator settings
                indicator_settings = {
                    'short_ma': 20,
                    'long_ma': 50,
                    'rsi_period': 14,
                    'rsi_overbought': 70,
                    'rsi_oversold': 30,
                    'macd_fast': 12,
                    'macd_slow': 26,
                    'macd_signal': 9,
                    'bb_period': 20,
                    'bb_std': 2.0,
                    'risk_percentage': 1.0
                }
                
                # Start monitoring
                success = st.session_state.real_time_analyzer.start_monitoring(
                    st.session_state.selected_stocks,
                    indicator_settings,
                    st.session_state.user_phone if st.session_state.user_phone else None,
                    st.session_state.alert_frequency
                )
                
                if success:
                    st.session_state.monitoring_active = True
                    st.success("Real-time monitoring started")
                    st.rerun()
                else:
                    st.error("Failed to start real-time monitoring")
            else:
                st.warning("Please add stocks to your watchlist first")

# Display any unread alerts
if st.session_state.app_alerts:
    unread_alerts = [a for a in st.session_state.app_alerts if not a.get('is_read', False)]
    if unread_alerts:
        st.sidebar.subheader(f"📣 New Alerts ({len(unread_alerts)})")
        for i, alert in enumerate(unread_alerts):
            alert_time = alert['timestamp'].strftime("%H:%M:%S")
            signal_type = alert['signal_type']
            ticker = alert['ticker']
            price = alert['price']
            
            # Set color based on signal type
            if signal_type == "BUY" or signal_type == "COVER":
                color = "green"
            elif signal_type == "SELL" or signal_type == "SHORT":
                color = "red"
            else:
                color = "orange"
                
            st.sidebar.markdown(f"<div style='padding:10px;margin-bottom:10px;border-left:4px solid {color};background-color:rgba(0,0,0,0.05);'>"
                              f"<b style='color:{color};'>{signal_type}</b> {ticker} @ {currency_symbol}{price:.2f} "
                              f"<span style='float:right;font-size:0.8em;color:gray;'>{alert_time}</span>"
                              f"</div>", unsafe_allow_html=True)
            
            # Mark alert as read
            st.session_state.app_alerts[len(st.session_state.app_alerts) - len(unread_alerts) + i]['is_read'] = True

# Main dashboard tabs
tabs = st.tabs(["Stock Analysis", "Portfolio", "Trade History", "Alerts & Signals", "Beginner's Guide"])

with tabs[0]:  # Stock Analysis Tab
    # Sidebar for inputs and filters
    with st.sidebar:
        st.header("Stock Selection")
        
        # Time period selection
        time_period = st.selectbox(
            "Select time period",
            options=["1d", "5d", "1mo", "3mo", "6mo", "1y"],
            index=1
        )
        
        # Interval selection
        interval_options = ["1m", "2m", "5m", "15m", "30m", "60m", "1h", "1d"]
        default_interval = "15m" if time_period in ["1d", "5d"] else "1d"
        interval_index = interval_options.index(default_interval) if default_interval in interval_options else 0
        interval = st.selectbox(
            "Select interval",
            options=interval_options,
            index=interval_index
        )
        
        # Improved stock search and selection with suggestions
        stock_search = st.text_input("Search for stocks (e.g., AAPL, MSFT)")
        
        # Show popular suggestions if no search term
        if not stock_search:
            st.write("Popular stocks:")
            suggestion_cols = st.columns(2)
            popular_stocks = list(POPULAR_STOCKS.items())[:10]  # Show first 10 popular stocks
            
            with suggestion_cols[0]:
                for i in range(0, len(popular_stocks), 2):
                    if i < len(popular_stocks):
                        ticker, name = popular_stocks[i]
                        if st.button(f"{ticker}: {name}", key=f"popular_{i}"):
                            if ticker not in st.session_state.selected_stocks:
                                st.session_state.selected_stocks.append(ticker)
                                st.session_state.current_stock = ticker
                                st.success(f"Added {ticker} to your watchlist!")
                                st.rerun()
                            else:
                                st.warning(f"{ticker} is already in your watchlist!")
            
            with suggestion_cols[1]:
                for i in range(1, len(popular_stocks), 2):
                    if i < len(popular_stocks):
                        ticker, name = popular_stocks[i]
                        if st.button(f"{ticker}: {name}", key=f"popular_{i}"):
                            if ticker not in st.session_state.selected_stocks:
                                st.session_state.selected_stocks.append(ticker)
                                st.session_state.current_stock = ticker
                                st.success(f"Added {ticker} to your watchlist!")
                                st.rerun()
                            else:
                                st.warning(f"{ticker} is already in your watchlist!")
        
        # Search for specific stocks
        if stock_search:
            # Get suggestions with company names
            suggestions = get_stock_suggestions(stock_search)
            
            if suggestions:
                # Convert to options list with ticker and company name
                options = [f"{ticker}: {name}" for ticker, name in suggestions.items()]
                selected_option = st.selectbox("Select a stock", options=options)
                
                # Extract ticker from selected option
                selected_ticker = selected_option.split(':')[0].strip()
                
                if st.button("Add Stock"):
                    if selected_ticker not in st.session_state.selected_stocks:
                        st.session_state.selected_stocks.append(selected_ticker)
                        st.session_state.current_stock = selected_ticker
                        st.success(f"Added {selected_ticker} to your watchlist!")
                        st.rerun()
                    else:
                        st.warning(f"{selected_ticker} is already in your watchlist!")
            else:
                # Fallback to original search method
                matches = get_available_stocks(stock_search)
                if matches:
                    selected_stock = st.selectbox("Select a stock", options=matches)
                    if st.button("Add Stock"):
                        if selected_stock not in st.session_state.selected_stocks:
                            st.session_state.selected_stocks.append(selected_stock)
                            st.session_state.current_stock = selected_stock
                            st.success(f"Added {selected_stock} to your watchlist!")
                            st.rerun()
                        else:
                            st.warning(f"{selected_stock} is already in your watchlist!")
                else:
                    st.warning("No matching stocks found.")
        
        # Display and manage watchlist
        st.header("Your Watchlist")
        if not st.session_state.selected_stocks:
            st.info("Add stocks to your watchlist to begin analysis.")
        else:
            current_stock = st.radio(
                "Select stock to analyze",
                options=st.session_state.selected_stocks,
                index=st.session_state.selected_stocks.index(st.session_state.current_stock) if st.session_state.current_stock in st.session_state.selected_stocks else 0
            )
            st.session_state.current_stock = current_stock
            
            if st.button("Remove from Watchlist"):
                st.session_state.selected_stocks.remove(current_stock)
                if st.session_state.selected_stocks:
                    st.session_state.current_stock = st.session_state.selected_stocks[0]
                else:
                    st.session_state.current_stock = None
                st.success(f"Removed {current_stock} from your watchlist!")
                st.rerun()
        
        # Technical indicator parameters
        st.header("Indicator Settings")
        
        # Moving Average parameters
        st.subheader("Moving Averages")
        short_ma = st.slider("Short MA Period", min_value=5, max_value=50, value=20)
        long_ma = st.slider("Long MA Period", min_value=20, max_value=200, value=50)
        
        # RSI parameters
        st.subheader("RSI")
        rsi_period = st.slider("RSI Period", min_value=7, max_value=21, value=14)
        rsi_overbought = st.slider("RSI Overbought Threshold", min_value=65, max_value=85, value=70)
        rsi_oversold = st.slider("RSI Oversold Threshold", min_value=15, max_value=35, value=30)
        
        # MACD parameters
        st.subheader("MACD")
        macd_fast = st.slider("MACD Fast Period", min_value=8, max_value=20, value=12)
        macd_slow = st.slider("MACD Slow Period", min_value=20, max_value=40, value=26)
        macd_signal = st.slider("MACD Signal Period", min_value=5, max_value=15, value=9)
        
        # Bollinger Bands parameters
        st.subheader("Bollinger Bands")
        bb_period = st.slider("Bollinger Bands Period", min_value=10, max_value=50, value=20)
        bb_std = st.slider("Bollinger Bands Standard Deviation", min_value=1.0, max_value=3.0, value=2.0, step=0.1)
        
        # Risk parameters
        st.header("Risk Management")
        risk_percentage = st.slider("Risk Percentage per Trade", min_value=0.5, max_value=5.0, value=1.0, step=0.1)
        
        # Broker settings
        st.header("Broker Settings")
        broker_fee = st.slider("Broker Fee Percentage", min_value=0.01, max_value=1.0, value=0.05, step=0.01)
        st.session_state.broker_fee_percent = broker_fee
        
        # Auto-refresh
        st.header("Auto Refresh")
        auto_refresh = st.checkbox("Enable auto refresh", value=False)
        refresh_interval = st.slider("Refresh interval (seconds)", min_value=10, max_value=300, value=60) if auto_refresh else 60
    
    # Main content area for stock analysis
    if st.session_state.current_stock:
        # Display current stock info and last update time
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            st.subheader(f"Analysis for {st.session_state.current_stock}")
        with col2:
            last_update = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            st.write(f"Last Updated: {last_update}")
        with col3:
            if st.button("Refresh Data"):
                st.rerun()
        
        # Display loading message
        with st.spinner(f"Fetching and analyzing data for {st.session_state.current_stock}..."):
            # Fetch stock data
            try:
                df = fetch_stock_data(
                    st.session_state.current_stock, 
                    period=time_period,
                    interval=interval
                )
                
                if df is None or df.empty:
                    st.error(f"No data available for {st.session_state.current_stock}. Please try another stock or time period.")
                else:
                    # Calculate indicators
                    df = calculate_indicators(
                        df, 
                        short_ma=short_ma, 
                        long_ma=long_ma,
                        rsi_period=rsi_period,
                        macd_fast=macd_fast,
                        macd_slow=macd_slow,
                        macd_signal=macd_signal,
                        bb_period=bb_period,
                        bb_std=bb_std
                    )
                    
                    # Generate signals
                    df = generate_signals(
                        df,
                        rsi_overbought=rsi_overbought,
                        rsi_oversold=rsi_oversold
                    )
                    
                    # Calculate composite score
                    df = calculate_composite_score(df)
                    
                    # Calculate risk parameters for the latest data point
                    latest_data = df.iloc[-1]
                    risk_params = calculate_risk_parameters(
                        latest_data,
                        df,
                        risk_percentage=risk_percentage
                    )
                    
                    # Check if the current stock is in portfolio to determine actual signal text
                    last_price = latest_data['Close']
                    last_score = latest_data['composite_score']
                    
                    # Use real-time analyzer to determine signal
                    indicator_settings = {
                        'short_ma': short_ma,
                        'long_ma': long_ma,
                        'rsi_period': rsi_period,
                        'rsi_overbought': rsi_overbought,
                        'rsi_oversold': rsi_oversold,
                        'macd_fast': macd_fast,
                        'macd_slow': macd_slow,
                        'macd_signal': macd_signal,
                        'bb_period': bb_period,
                        'bb_std': bb_std,
                        'risk_percentage': risk_percentage
                    }
                    
                    analysis = st.session_state.real_time_analyzer.analyze_stock(
                        st.session_state.current_stock,
                        indicator_settings
                    )
                    
                    if analysis:
                        signal = analysis['signal']
                        signal_text = signal['type']
                        signal_strength = signal['strength']
                        signal_desc = signal['desc']
                        
                        # Determine color based on signal type
                        if signal_text in ['BUY', 'COVER']:
                            signal_color = "green"
                        elif signal_text in ['SELL', 'SHORT']:
                            signal_color = "red"
                        else:
                            signal_color = "orange"
                            
                        # Get P&L if in portfolio
                        if st.session_state.current_stock in st.session_state.portfolio:
                            position = st.session_state.portfolio[st.session_state.current_stock]
                            position_type = position.get('position_type', 'LONG')
                            avg_price = position['avg_price']
                            
                            if position_type == 'LONG':
                                current_pnl = (last_price - avg_price) / avg_price * 100
                                pnl_text = f"P&L: {current_pnl:.2f}%"
                            else:  # SHORT position
                                current_pnl = (avg_price - last_price) / avg_price * 100
                                pnl_text = f"P&L: {current_pnl:.2f}%"
                        else:
                            pnl_text = ""
                    else:
                        # Fallback if real-time analyzer fails
                        if st.session_state.current_stock in st.session_state.portfolio:
                            position = st.session_state.portfolio[st.session_state.current_stock]
                            position_type = position.get('position_type', 'LONG')
                            avg_price = position['avg_price']
                            
                            if position_type == 'LONG':
                                if last_score < 0.4:
                                    signal_text = "SELL"
                                    signal_color = "red"
                                    signal_desc = "Consider selling based on bearish indicators."
                                else:
                                    signal_text = "HOLD"
                                    signal_color = "orange"
                                    signal_desc = "Continue holding the long position."
                                    
                                current_pnl = (last_price - avg_price) / avg_price * 100
                                pnl_text = f"P&L: {current_pnl:.2f}%"
                            else:  # SHORT position
                                if last_score > 0.6:
                                    signal_text = "COVER"
                                    signal_color = "green"
                                    signal_desc = "Consider covering short position based on bullish indicators."
                                else:
                                    signal_text = "HOLD"
                                    signal_color = "orange"
                                    signal_desc = "Continue holding the short position."
                                    
                                current_pnl = (avg_price - last_price) / avg_price * 100
                                pnl_text = f"P&L: {current_pnl:.2f}%"
                        else:
                            if last_score > 0.6:
                                signal_text = "BUY"
                                signal_color = "green"
                                signal_desc = "Consider buying based on bullish indicators."
                            elif last_score < 0.4:
                                signal_text = "SHORT"
                                signal_color = "red"
                                signal_desc = "Consider shorting based on bearish indicators."
                            else:
                                signal_text = "WAIT"
                                signal_color = "orange"
                                signal_desc = "No clear signal. Wait for more definitive movement."
                                
                            pnl_text = ""
                            signal_strength = max(0, min(1, abs(last_score - 0.5) * 2))  # Convert 0-1 score to 0-1 strength, capped between 0-1
                    
                    # Display trading signal and recommendations
                    st.subheader("Trading Signal")
                    signal_cols = st.columns([1, 1, 1, 1])
                    with signal_cols[0]:
                        st.markdown(f"<h2 style='color:{signal_color};text-align:center;'>{signal_text}</h2>", unsafe_allow_html=True)
                        if pnl_text:
                            st.markdown(f"<p style='text-align:center;'>{pnl_text}</p>", unsafe_allow_html=True)
                    with signal_cols[1]:
                        st.metric("Current Price", f"{currency_symbol}{last_price:.2f}", f"{latest_data['Close_pct_change']:.2f}%" if 'Close_pct_change' in latest_data else None)
                    with signal_cols[2]:
                        st.metric("Confidence", f"{signal_strength:.2f}", None)
                        st.progress(signal_strength)
                    with signal_cols[3]:
                        st.markdown(f"<p><strong>Signal:</strong> {signal_desc}</p>", unsafe_allow_html=True)
                    
                    # Action buttons for trading
                    trade_cols = st.columns(4)
                    with trade_cols[0]:
                        # Define trade quantity input
                        quantity = st.number_input("Quantity", min_value=1, value=1, step=1)
                        
                    with trade_cols[1]:
                        # Calculate approx. trade value and fees
                        trade_value = quantity * last_price
                        broker_fee = trade_value * st.session_state.broker_fee_percent / 100
                        st.write(f"Est. Trade Value: {currency_symbol}{trade_value:.2f}")
                        st.write(f"Est. Broker Fee: {currency_symbol}{broker_fee:.2f}")
                        
                    # Display appropriate action buttons based on current portfolio
                    stock_in_portfolio = st.session_state.current_stock in st.session_state.portfolio
                    
                    if stock_in_portfolio:
                        position = st.session_state.portfolio[st.session_state.current_stock]
                        position_type = position.get('position_type', 'LONG')
                        
                        with trade_cols[2]:
                            if position_type == 'LONG':
                                if st.button("📈 SELL LONG"):
                                    # Record the sell transaction
                                    buy_price = position['avg_price']
                                    sell_price = last_price
                                    
                                    # Calculate P&L including broker fees
                                    buy_value = buy_price * quantity
                                    sell_value = sell_price * quantity
                                    buy_fee = buy_value * st.session_state.broker_fee_percent / 100
                                    sell_fee = sell_value * st.session_state.broker_fee_percent / 100
                                    
                                    pnl = sell_value - buy_value - buy_fee - sell_fee
                                    pnl_percent = (pnl / buy_value) * 100
                                    
                                    # Record the trade
                                    st.session_state.trades.append({
                                        'ticker': st.session_state.current_stock,
                                        'action': 'SELL',
                                        'position_type': 'LONG',
                                        'quantity': quantity,
                                        'price': sell_price,
                                        'value': sell_value,
                                        'fee': sell_fee,
                                        'pnl': pnl,
                                        'pnl_percent': pnl_percent,
                                        'timestamp': datetime.datetime.now(),
                                        'confidence_score': last_score
                                    })
                                    
                                    # Update overall P&L
                                    st.session_state.overall_pnl += pnl
                                    
                                    # Remove from portfolio if all shares sold
                                    if quantity >= position['quantity']:
                                        del st.session_state.portfolio[st.session_state.current_stock]
                                    else:
                                        position['quantity'] -= quantity
                                    
                                    st.success(f"Sold {quantity} shares of {st.session_state.current_stock} at {currency_symbol}{sell_price:.2f}")
                                    st.rerun()
                            else:  # SHORT position
                                if st.button("📈 COVER SHORT"):
                                    # Record the cover transaction
                                    short_price = position['avg_price']
                                    cover_price = last_price
                                    
                                    # Calculate P&L including broker fees
                                    short_value = short_price * quantity
                                    cover_value = cover_price * quantity
                                    short_fee = short_value * st.session_state.broker_fee_percent / 100
                                    cover_fee = cover_value * st.session_state.broker_fee_percent / 100
                                    
                                    pnl = short_value - cover_value - short_fee - cover_fee
                                    pnl_percent = (pnl / short_value) * 100
                                    
                                    # Record the trade
                                    st.session_state.trades.append({
                                        'ticker': st.session_state.current_stock,
                                        'action': 'COVER',
                                        'position_type': 'SHORT',
                                        'quantity': quantity,
                                        'price': cover_price,
                                        'value': cover_value,
                                        'fee': cover_fee,
                                        'pnl': pnl,
                                        'pnl_percent': pnl_percent,
                                        'timestamp': datetime.datetime.now(),
                                        'confidence_score': last_score
                                    })
                                    
                                    # Update overall P&L
                                    st.session_state.overall_pnl += pnl
                                    
                                    # Remove from portfolio if all shares covered
                                    if quantity >= position['quantity']:
                                        del st.session_state.portfolio[st.session_state.current_stock]
                                    else:
                                        position['quantity'] -= quantity
                                    
                                    st.success(f"Covered {quantity} shares of {st.session_state.current_stock} at {currency_symbol}{cover_price:.2f}")
                                    st.rerun()
                    else:
                        with trade_cols[2]:
                            if st.button("📉 BUY LONG"):
                                # Record the buy transaction
                                buy_price = last_price
                                buy_value = buy_price * quantity
                                buy_fee = buy_value * st.session_state.broker_fee_percent / 100
                                
                                # Add to portfolio
                                st.session_state.portfolio[st.session_state.current_stock] = {
                                    'quantity': quantity,
                                    'avg_price': buy_price,
                                    'timestamp': datetime.datetime.now(),
                                    'confidence_score': last_score,
                                    'position_type': 'LONG'
                                }
                                
                                # Record the trade
                                st.session_state.trades.append({
                                    'ticker': st.session_state.current_stock,
                                    'action': 'BUY',
                                    'position_type': 'LONG',
                                    'quantity': quantity,
                                    'price': buy_price,
                                    'value': buy_value,
                                    'fee': buy_fee,
                                    'timestamp': datetime.datetime.now(),
                                    'confidence_score': last_score
                                })
                                
                                st.success(f"Bought {quantity} shares of {st.session_state.current_stock} at {currency_symbol}{buy_price:.2f}")
                                st.rerun()
                    
                    with trade_cols[3]:
                        if not stock_in_portfolio:
                            if st.button("📈 SHORT SELL"):
                                # Record the short transaction
                                short_price = last_price
                                short_value = short_price * quantity
                                short_fee = short_value * st.session_state.broker_fee_percent / 100
                                
                                # Add to portfolio
                                st.session_state.portfolio[st.session_state.current_stock] = {
                                    'quantity': quantity,
                                    'avg_price': short_price,
                                    'timestamp': datetime.datetime.now(),
                                    'confidence_score': last_score,
                                    'position_type': 'SHORT'
                                }
                                
                                # Record the trade
                                st.session_state.trades.append({
                                    'ticker': st.session_state.current_stock,
                                    'action': 'SHORT',
                                    'position_type': 'SHORT',
                                    'quantity': quantity,
                                    'price': short_price,
                                    'value': short_value,
                                    'fee': short_fee,
                                    'timestamp': datetime.datetime.now(),
                                    'confidence_score': last_score
                                })
                                
                                st.success(f"Shorted {quantity} shares of {st.session_state.current_stock} at {currency_symbol}{short_price:.2f}")
                                st.rerun()
                    
                    # Risk management parameters
                    st.subheader("Risk Management Parameters")
                    risk_cols = st.columns(4)
                    with risk_cols[0]:
                        st.metric("Suggested Entry Price", f"{currency_symbol}{risk_params['entry_price']:.2f}")
                    with risk_cols[1]:
                        st.metric("Suggested Stop Loss", f"{currency_symbol}{risk_params['stop_loss']:.2f}")
                    with risk_cols[2]:
                        st.metric("Suggested Take Profit", f"{currency_symbol}{risk_params['take_profit']:.2f}")
                    
                    # Estimated Hold Time
                    with risk_cols[3]:
                        hold_time_mins = int(20 / (latest_data['Close_pct_change'] if 'Close_pct_change' in latest_data and abs(latest_data['Close_pct_change']) > 0 else 0.5) * 60)
                        if hold_time_mins > 360:  # Cap at 6 hours for readability
                            hold_time_mins = 360
                            
                        hours = hold_time_mins // 60
                        minutes = hold_time_mins % 60
                        
                        if hours > 0:
                            hold_time_text = f"{hours}h {minutes}m"
                        else:
                            hold_time_text = f"{minutes}m"
                            
                        st.metric("Est. Hold Time", hold_time_text)
                    
                    # Create main price chart with indicators
                    st.subheader("Price Chart with Indicators")
                    
                    # Create subplot with shared x-axis
                    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                                       row_heights=[0.6, 0.2, 0.2],
                                       vertical_spacing=0.05)
                    
                    # Add candlestick chart
                    fig.add_trace(
                        go.Candlestick(
                            x=df.index,
                            open=df['Open'],
                            high=df['High'],
                            low=df['Low'],
                            close=df['Close'],
                            name="Price"
                        ),
                        row=1, col=1
                    )
                    
                    # Add moving averages
                    fig.add_trace(
                        go.Scatter(x=df.index, y=df[f'MA_{short_ma}'], name=f"{short_ma}-period MA", line=dict(color='blue')),
                        row=1, col=1
                    )
                    fig.add_trace(
                        go.Scatter(x=df.index, y=df[f'MA_{long_ma}'], name=f"{long_ma}-period MA", line=dict(color='orange')),
                        row=1, col=1
                    )
                    
                    # Add Bollinger Bands
                    fig.add_trace(
                        go.Scatter(x=df.index, y=df['BB_upper'], name='BB Upper', line=dict(color='rgba(0,128,0,0.3)')),
                        row=1, col=1
                    )
                    fig.add_trace(
                        go.Scatter(x=df.index, y=df['BB_middle'], name='BB Middle', line=dict(color='rgba(0,128,0,0.5)')),
                        row=1, col=1
                    )
                    fig.add_trace(
                        go.Scatter(x=df.index, y=df['BB_lower'], name='BB Lower', line=dict(color='rgba(0,128,0,0.3)')),
                        row=1, col=1
                    )
                    
                    # Add trade positions if in portfolio
                    if st.session_state.current_stock in st.session_state.portfolio:
                        position = st.session_state.portfolio[st.session_state.current_stock]
                        position_type = position.get('position_type', 'LONG')
                        position_price = position['avg_price']
                        position_quantity = position['quantity']
                        
                        # Add horizontal line at position price
                        fig.add_trace(
                            go.Scatter(
                                x=[df.index[0], df.index[-1]],
                                y=[position_price, position_price],
                                mode='lines',
                                line=dict(color='purple', width=2, dash='dash'),
                                name=f"{position_type} Position ({position_quantity} shares)"
                            ),
                            row=1, col=1
                        )
                    
                    # Add buy/sell signals if available
                    buy_signals = df[df['signal'] == 1]
                    sell_signals = df[df['signal'] == -1]
                    
                    if not buy_signals.empty:
                        fig.add_trace(
                            go.Scatter(
                                x=buy_signals.index,
                                y=buy_signals['Low'] * 0.99,  # Position slightly below the low price
                                mode='markers',
                                marker=dict(symbol='triangle-up', size=15, color='green'),
                                name='Buy Signal'
                            ),
                            row=1, col=1
                        )
                    
                    if not sell_signals.empty:
                        fig.add_trace(
                            go.Scatter(
                                x=sell_signals.index,
                                y=sell_signals['High'] * 1.01,  # Position slightly above the high price
                                mode='markers',
                                marker=dict(symbol='triangle-down', size=15, color='red'),
                                name='Sell Signal'
                            ),
                            row=1, col=1
                        )
                    
                    # Add RSI
                    fig.add_trace(
                        go.Scatter(x=df.index, y=df['RSI'], name='RSI', line=dict(color='purple')),
                        row=2, col=1
                    )
                    
                    # Add RSI overbought/oversold lines
                    fig.add_trace(
                        go.Scatter(x=df.index, y=[rsi_overbought] * len(df), name='Overbought', 
                                  line=dict(color='red', dash='dash')),
                        row=2, col=1
                    )
                    fig.add_trace(
                        go.Scatter(x=df.index, y=[rsi_oversold] * len(df), name='Oversold', 
                                  line=dict(color='green', dash='dash')),
                        row=2, col=1
                    )
                    
                    # Add MACD
                    fig.add_trace(
                        go.Scatter(x=df.index, y=df['MACD'], name='MACD', line=dict(color='blue')),
                        row=3, col=1
                    )
                    fig.add_trace(
                        go.Scatter(x=df.index, y=df['MACD_signal'], name='MACD Signal', line=dict(color='red')),
                        row=3, col=1
                    )
                    fig.add_trace(
                        go.Bar(x=df.index, y=df['MACD_hist'], name='MACD Histogram', marker=dict(color='gray')),
                        row=3, col=1
                    )
                    
                    # Update layout
                    fig.update_layout(
                        title=f"{st.session_state.current_stock} - {interval} interval",
                        xaxis_title="Date",
                        yaxis_title=f"Price ({currency_symbol})",
                        height=800,
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=1.02,
                            xanchor="right",
                            x=1
                        )
                    )
                    
                    # Update y-axis titles for subplots
                    fig.update_yaxes(title_text=f"Price ({currency_symbol})", row=1, col=1)
                    fig.update_yaxes(title_text="RSI", row=2, col=1)
                    fig.update_yaxes(title_text="MACD", row=3, col=1)
                    
                    # Show figure
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Display indicator values table
                    st.subheader("Current Technical Indicators")
                    indicator_df = pd.DataFrame({
                        'Indicator': ['Price', f'{short_ma}-MA', f'{long_ma}-MA', 'RSI', 'MACD', 'MACD Signal', 'BB Upper', 'BB Middle', 'BB Lower'],
                        'Value': [
                            f"{currency_symbol}{latest_data['Close']:.2f}",
                            f"{currency_symbol}{latest_data[f'MA_{short_ma}']:.2f}",
                            f"{currency_symbol}{latest_data[f'MA_{long_ma}']:.2f}",
                            f"{latest_data['RSI']:.2f}",
                            f"{latest_data['MACD']:.4f}",
                            f"{latest_data['MACD_signal']:.4f}",
                            f"{currency_symbol}{latest_data['BB_upper']:.2f}",
                            f"{currency_symbol}{latest_data['BB_middle']:.2f}",
                            f"{currency_symbol}{latest_data['BB_lower']:.2f}"
                        ],
                        'Status': [
                            '',
                            'Above Price' if latest_data[f'MA_{short_ma}'] > latest_data['Close'] else 'Below Price',
                            'Above Price' if latest_data[f'MA_{long_ma}'] > latest_data['Close'] else 'Below Price',
                            'Overbought' if latest_data['RSI'] > rsi_overbought else 'Oversold' if latest_data['RSI'] < rsi_oversold else 'Neutral',
                            'Bullish' if latest_data['MACD'] > latest_data['MACD_signal'] else 'Bearish',
                            '',
                            'Resistance' if latest_data['Close'] < latest_data['BB_upper'] else 'Broken Upper',
                            '',
                            'Support' if latest_data['Close'] > latest_data['BB_lower'] else 'Broken Lower'
                        ]
                    })
                    
                    st.table(indicator_df)
                    
                    # Explain the signals in human language
                    st.subheader("Signal Explanation")
                    explanation = """
                    <div style="background-color: #f0f2f6; padding: 15px; border-radius: 10px;">
                    """
                    
                    # Personalized commentary based on indicators
                    if latest_data['RSI'] > rsi_overbought:
                        explanation += f"<p>The stock appears <strong>overbought</strong> with RSI at {latest_data['RSI']:.2f}, suggesting a potential pullback or correction.</p>"
                    elif latest_data['RSI'] < rsi_oversold:
                        explanation += f"<p>The stock appears <strong>oversold</strong> with RSI at {latest_data['RSI']:.2f}, suggesting a potential bounce or recovery.</p>"
                    
                    # Moving average explanation
                    if latest_data[f'MA_{short_ma}'] > latest_data[f'MA_{long_ma}']:
                        explanation += f"<p>The short-term ({short_ma}-period) moving average is above the long-term ({long_ma}-period) moving average, suggesting an <strong>upward trend</strong>.</p>"
                    else:
                        explanation += f"<p>The short-term ({short_ma}-period) moving average is below the long-term ({long_ma}-period) moving average, suggesting a <strong>downward trend</strong>.</p>"
                    
                    # MACD explanation
                    if latest_data['MACD'] > latest_data['MACD_signal']:
                        explanation += "<p>MACD is above the signal line, indicating <strong>bullish momentum</strong>.</p>"
                    else:
                        explanation += "<p>MACD is below the signal line, indicating <strong>bearish momentum</strong>.</p>"
                    
                    # Bollinger Bands explanation
                    if latest_data['Close'] > latest_data['BB_upper']:
                        explanation += "<p>Price is above the upper Bollinger Band, suggesting <strong>strong upward momentum</strong> but possibly overbought.</p>"
                    elif latest_data['Close'] < latest_data['BB_lower']:
                        explanation += "<p>Price is below the lower Bollinger Band, suggesting <strong>strong downward momentum</strong> but possibly oversold.</p>"
                    else:
                        explanation += "<p>Price is within the Bollinger Bands, suggesting <strong>normal volatility</strong>.</p>"
                    
                    # Final recommendation
                    explanation += f"<p><strong>Overall recommendation:</strong> {signal_desc}</p>"
                    
                    explanation += "</div>"
                    st.markdown(explanation, unsafe_allow_html=True)
                    
                    # Historical Performance Analysis
                    st.subheader("Strategy Performance Metrics")
                    
                    # Count buy/sell signals
                    buy_count = len(buy_signals)
                    sell_count = len(sell_signals)
                    
                    # Simple backtest for educational purposes
                    if 'signal' in df.columns:
                        # Calculate returns
                        df['signal_shift'] = df['signal'].shift(1)  # Shift signals so we trade on the next bar
                        df['strategy_returns'] = df['Close_pct_change'] * df['signal_shift']
                        
                        # Calculate cumulative returns
                        df['cumulative_returns'] = (1 + df['Close_pct_change'] / 100).cumprod() - 1
                        df['strategy_cumulative_returns'] = (1 + df['strategy_returns'] / 100).cumprod() - 1
                        
                        # Calculate win rate and other metrics
                        winning_trades = df[df['strategy_returns'] > 0]['strategy_returns'].count()
                        losing_trades = df[df['strategy_returns'] < 0]['strategy_returns'].count()
                        total_trades = winning_trades + losing_trades
                        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
                        
                        # Calculate Sharpe ratio (simplified)
                        risk_free_rate = 0.0  # Assume 0% risk-free rate for simplicity
                        strategy_return = df['strategy_cumulative_returns'].iloc[-1] * 100 if len(df) > 0 else 0
                        strategy_volatility = df['strategy_returns'].std() if len(df) > 0 else 0
                        sharpe_ratio = (strategy_return - risk_free_rate) / strategy_volatility if strategy_volatility > 0 else 0
                        
                        # Display metrics
                        metric_cols = st.columns(4)
                        with metric_cols[0]:
                            st.metric("Total Signals", f"{buy_count + sell_count}")
                        with metric_cols[1]:
                            st.metric("Win Rate", f"{win_rate:.2f}%")
                        with metric_cols[2]:
                            st.metric("Strategy Return", f"{strategy_return:.2f}%")
                        with metric_cols[3]:
                            st.metric("Sharpe Ratio", f"{sharpe_ratio:.2f}")
                        
                        # Plot cumulative returns
                        st.subheader("Cumulative Returns Comparison")
                        returns_fig = go.Figure()
                        returns_fig.add_trace(go.Scatter(
                            x=df.index,
                            y=df['cumulative_returns'] * 100,
                            mode='lines',
                            name='Buy & Hold',
                            line=dict(color='blue')
                        ))
                        returns_fig.add_trace(go.Scatter(
                            x=df.index,
                            y=df['strategy_cumulative_returns'] * 100,
                            mode='lines',
                            name='Strategy',
                            line=dict(color='green')
                        ))
                        returns_fig.update_layout(
                            title="Strategy vs Buy & Hold Performance",
                            xaxis_title="Date",
                            yaxis_title="Cumulative Return (%)",
                            height=400,
                            legend=dict(
                                orientation="h",
                                yanchor="bottom",
                                y=1.02,
                                xanchor="right",
                                x=1
                            )
                        )
                        st.plotly_chart(returns_fig, use_container_width=True)
                    
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
    
    else:
        # No stock selected yet
        st.info("Please select a stock from the sidebar to begin analysis.")
        
        # Show a demo image or explanation
        st.subheader("How to use this tool:")
        
        st.markdown("""
        1. **Add stocks** to your watchlist using the sidebar
        2. **Select a stock** from your watchlist to analyze
        3. **Customize indicators** by adjusting parameters in the sidebar
        4. **Analyze the charts** and trading signals
        5. **Set risk parameters** to suit your trading style
        6. **Start real-time monitoring** to receive alerts when signals change
        
        The tool will provide:
        - Real-time stock data visualization
        - Technical indicator calculations
        - Buy/sell/short/cover signals based on indicators
        - Composite scoring for trade recommendations
        - Risk management parameters (stop-loss and take-profit levels)
        """)

with tabs[1]:  # Portfolio Tab
    st.header("Your Portfolio")
    
    if not st.session_state.portfolio:
        st.info("You don't have any positions yet. Go to the Stock Analysis tab to buy stocks.")
    else:
        # Portfolio summary
        total_value = 0
        portfolio_data = []
        
        for ticker, position in st.session_state.portfolio.items():
            # Get current price
            try:
                current_data = fetch_stock_data(ticker, period="1d", interval="1m")
                if current_data is not None and not current_data.empty:
                    current_price = current_data['Close'].iloc[-1]
                else:
                    current_price = position['avg_price']  # Use purchase price if current price not available
            except:
                current_price = position['avg_price']  # Fallback to purchase price
                
            # Calculate position value and P&L
            quantity = position['quantity']
            avg_price = position['avg_price']
            position_type = position.get('position_type', 'LONG')
            
            if position_type == 'LONG':
                position_value = quantity * current_price
                cost_basis = quantity * avg_price
                pnl = position_value - cost_basis
                pnl_percent = (pnl / cost_basis) * 100
            else:  # SHORT position
                position_value = quantity * current_price  # Current liability
                cost_basis = quantity * avg_price  # Initial credit received
                pnl = cost_basis - position_value  # Profit if current price < avg price
                pnl_percent = (pnl / cost_basis) * 100
            
            # Add to total portfolio value
            total_value += (cost_basis + pnl)
            
            # Add to portfolio data for display
            portfolio_data.append({
                'Ticker': ticker,
                'Type': position_type,
                'Quantity': quantity,
                'Avg. Price': f"{currency_symbol}{avg_price:.2f}",
                'Current Price': f"{currency_symbol}{current_price:.2f}",
                'Value': f"{currency_symbol}{abs(position_value):.2f}",
                'P&L': f"{currency_symbol}{pnl:.2f} ({pnl_percent:.2f}%)",
                'Purchase Date': position['timestamp'].strftime("%Y-%m-%d %H:%M"),
                'Confidence Score': f"{position['confidence_score']:.2f}"
            })
        
        # Display portfolio summary
        st.subheader(f"Total Portfolio Value: {currency_symbol}{total_value:.2f}")
        st.subheader(f"Overall P&L: {currency_symbol}{st.session_state.overall_pnl:.2f}")
        
        # Display portfolio table
        st.dataframe(portfolio_data)
        
        # Portfolio visualization - pie chart of positions
        if portfolio_data:
            # Group by position type
            long_positions = [d for d in portfolio_data if d['Type'] == 'LONG']
            short_positions = [d for d in portfolio_data if d['Type'] == 'SHORT']
            
            # Create columns for long and short positions
            portfolio_cols = st.columns(2)
            
            with portfolio_cols[0]:
                if long_positions:
                    st.subheader("Long Positions")
                    labels = [d['Ticker'] for d in long_positions]
                    values = [float(d['Value'].replace(currency_symbol, '')) for d in long_positions]
                    
                    fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.3)])
                    fig.update_layout(title_text="Long Position Allocation")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No long positions in portfolio")
            
            with portfolio_cols[1]:
                if short_positions:
                    st.subheader("Short Positions")
                    labels = [d['Ticker'] for d in short_positions]
                    values = [float(d['Value'].replace(currency_symbol, '')) for d in short_positions]
                    
                    fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.3)])
                    fig.update_layout(title_text="Short Position Allocation")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No short positions in portfolio")

with tabs[2]:  # Trade History Tab
    st.header("Trade History")
    
    if not st.session_state.trades:
        st.info("You haven't made any trades yet.")
    else:
        # Prepare trade history data
        trade_history = []
        for trade in st.session_state.trades:
            position_type = trade.get('position_type', 'LONG')
            action = trade['action']
            
            # Format action for display
            if position_type == 'LONG' and action == 'BUY':
                display_action = "BUY LONG"
            elif position_type == 'LONG' and action == 'SELL':
                display_action = "SELL LONG"
            elif position_type == 'SHORT' and action == 'SHORT':
                display_action = "SHORT SELL"
            elif position_type == 'SHORT' and action == 'COVER':
                display_action = "COVER SHORT"
            else:
                display_action = action
            
            trade_history.append({
                'Ticker': trade['ticker'],
                'Action': display_action,
                'Quantity': trade['quantity'],
                'Price': f"{currency_symbol}{trade['price']:.2f}",
                'Value': f"{currency_symbol}{trade['value']:.2f}",
                'Fee': f"{currency_symbol}{trade['fee']:.2f}",
                'Date': trade['timestamp'].strftime("%Y-%m-%d %H:%M"),
                'P&L': f"{currency_symbol}{trade.get('pnl', 0):.2f} ({trade.get('pnl_percent', 0):.2f}%)" if action in ['SELL', 'COVER'] else '-',
                'Confidence': f"{trade['confidence_score']:.2f}"
            })
        
        # Display trade history table
        st.dataframe(trade_history)
        
        # Performance visualization
        closed_trades = [t for t in st.session_state.trades if t['action'] in ['SELL', 'COVER']]
        if closed_trades:
            # Create win/loss chart
            win_trades = [t for t in closed_trades if t.get('pnl', 0) > 0]
            loss_trades = [t for t in closed_trades if t.get('pnl', 0) <= 0]
            
            win_pnl = sum(t.get('pnl', 0) for t in win_trades)
            loss_pnl = sum(t.get('pnl', 0) for t in loss_trades)
            
            # Win/loss metrics
            win_rate = len(win_trades) / len(closed_trades) * 100 if len(closed_trades) > 0 else 0
            
            # Display metrics
            metrics_cols = st.columns(4)
            with metrics_cols[0]:
                st.metric("Win Rate", f"{win_rate:.2f}%")
            with metrics_cols[1]:
                st.metric("Winning Trades", f"{len(win_trades)}")
            with metrics_cols[2]:
                st.metric("Losing Trades", f"{len(loss_trades)}")
            with metrics_cols[3]:
                st.metric("Net P&L", f"{currency_symbol}{st.session_state.overall_pnl:.2f}")
            
            # Chart showing P&L over time
            if closed_trades:
                pnl_df = pd.DataFrame({
                    'Date': [t['timestamp'] for t in closed_trades],
                    'P&L': [t.get('pnl', 0) for t in closed_trades],
                    'Ticker': [t['ticker'] for t in closed_trades],
                    'Type': [t.get('position_type', 'LONG') for t in closed_trades]
                })
                pnl_df = pnl_df.sort_values('Date')
                pnl_df['Cumulative P&L'] = pnl_df['P&L'].cumsum()
                
                # Create performance charts
                perf_cols = st.columns(2)
                
                with perf_cols[0]:
                    # Cumulative P&L chart
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=pnl_df['Date'],
                        y=pnl_df['Cumulative P&L'],
                        mode='lines+markers',
                        name='Cumulative P&L',
                        line=dict(color='green' if pnl_df['Cumulative P&L'].iloc[-1] > 0 else 'red')
                    ))
                    
                    fig.update_layout(
                        title="Cumulative P&L Over Time",
                        xaxis_title="Date",
                        yaxis_title=f"P&L ({currency_symbol})",
                        height=400
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                
                with perf_cols[1]:
                    # P&L by position type
                    long_pnl = pnl_df[pnl_df['Type'] == 'LONG']['P&L'].sum()
                    short_pnl = pnl_df[pnl_df['Type'] == 'SHORT']['P&L'].sum()
                    
                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        x=['Long Positions', 'Short Positions'],
                        y=[long_pnl, short_pnl],
                        marker_color=['blue', 'red']
                    ))
                    
                    fig.update_layout(
                        title="P&L by Position Type",
                        xaxis_title="Position Type",
                        yaxis_title=f"P&L ({currency_symbol})",
                        height=400
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)

with tabs[3]:  # Alerts & Signals Tab
    st.header("Real-Time Alerts & Signals")
    
    # SMS notification setup
    st.subheader("SMS Notification Settings")
    
    alert_cols = st.columns(2)
    
    with alert_cols[0]:
        st.write("Current phone number for alerts:")
        if st.session_state.user_phone:
            st.code(st.session_state.user_phone)
        else:
            st.warning("No phone number set. Add one at the top of the page to receive SMS alerts.")
    
    with alert_cols[1]:
        if st.session_state.monitoring_active:
            st.success("Real-time monitoring is active")
            st.write(f"Alert frequency: {st.session_state.alert_frequency} minutes between alerts")
        else:
            st.warning("Real-time monitoring is not active. Start it at the top of the page.")
    
    # Real-time alerts history
    st.subheader("Recent Alerts")
    
    if not st.session_state.app_alerts:
        st.info("No alerts generated yet. Start real-time monitoring to receive alerts.")
    else:
        # Reverse order to show most recent first
        alerts = list(reversed(st.session_state.app_alerts))
        
        alert_df = pd.DataFrame({
            'Time': [a['timestamp'].strftime("%Y-%m-%d %H:%M:%S") for a in alerts],
            'Ticker': [a['ticker'] for a in alerts],
            'Signal': [a['signal_type'] for a in alerts],
            'Price': [f"{currency_symbol}{a['price']:.2f}" for a in alerts],
            'Confidence': [f"{a['score']:.2f}" for a in alerts]
        })
        
        st.dataframe(alert_df)
    
    # SMS log
    st.subheader("SMS Alert Log")
    
    if not st.session_state.alert_log:
        st.info("No SMS alerts have been sent yet.")
    else:
        # Show SMS alert history
        sms_log = list(reversed(st.session_state.alert_log))
        
        sms_df = pd.DataFrame({
            'Time': [a['timestamp'].strftime("%Y-%m-%d %H:%M:%S") for a in sms_log],
            'Type': [a['type'] for a in sms_log],
            'Recipient': [a['recipient'] for a in sms_log],
            'Status': [a['status'] for a in sms_log],
            'Message': [a['message'] for a in sms_log]
        })
        
        st.dataframe(sms_df)
    
    # Test SMS alert
    st.subheader("Test SMS Alert")
    
    test_cols = st.columns(2)
    
    with test_cols[0]:
        test_phone = st.text_input("Test Phone Number (E.164 format)", value=st.session_state.user_phone, placeholder="+919876543210")
    
    with test_cols[1]:
        if st.button("Send Test SMS"):
            if test_phone:
                from utils.alert_manager import send_sms_alert
                success = send_sms_alert(test_phone, "This is a test alert from your Stock Analysis App!")
                
                if success:
                    st.success("Test SMS sent successfully!")
                else:
                    st.error("Failed to send test SMS. Check your Twilio credentials and phone number format.")
            else:
                st.warning("Please enter a phone number first.")

with tabs[4]:  # Beginner's Guide Tab
    st.header("Beginner's Guide to Stock Trading")
    
    st.subheader("What are Technical Indicators?")
    st.markdown("""
    Technical indicators are mathematical calculations based on price, volume, or open interest of a security. They help traders identify patterns and predict future price movements.
    
    This tool uses several common indicators:
    
    **Moving Averages (MA)** - Average price over a specific time period, helping to identify trends.
    
    **Relative Strength Index (RSI)** - Measures the speed and change of price movements on a scale of 0-100.
    - Above 70: Potentially overbought (price may drop)
    - Below 30: Potentially oversold (price may rise)
    
    **Moving Average Convergence Divergence (MACD)** - Shows the relationship between two moving averages.
    - MACD above signal line: Bullish signal
    - MACD below signal line: Bearish signal
    
    **Bollinger Bands** - Three lines showing price volatility.
    - Price near upper band: Potentially overbought
    - Price near lower band: Potentially oversold
    """)
    
    st.subheader("Understanding Trade Signals")
    st.markdown("""
    Our app generates different types of trade signals:
    
    **BUY LONG** - Strong positive signal suggesting you should purchase the stock expecting its price to increase.
    
    **SELL LONG** - Signal to sell a stock you own to take profits or cut losses.
    
    **SHORT SELL** - Signal to borrow and sell a stock expecting its price to decrease.
    
    **COVER SHORT** - Signal to buy back borrowed shares to close a short position.
    
    **HOLD** - Neutral signal suggesting you should maintain your current position.
    
    **WAIT** - Neutral signal suggesting you should wait for a clearer trend before taking any position.
    
    Remember that no signal is 100% accurate. Always combine technical analysis with fundamental research and risk management.
    """)
    
    st.subheader("How Short Selling Works")
    st.markdown("""
    Short selling is a trading strategy used when you expect a stock's price to fall:
    
    1. **Borrow shares** - You borrow shares from a broker (this happens automatically when you short sell)
    2. **Sell the borrowed shares** - The proceeds from the sale are credited to your account
    3. **Wait for price to fall** - If the price falls as expected, you profit
    4. **Buy back shares to "cover" your position** - You buy the shares at the lower price
    5. **Return the borrowed shares** - The borrowed shares are returned to the lender
    
    Your profit is the difference between your short sell price and cover price, minus any fees or interest.
    
    **Risks of Short Selling:**
    - **Unlimited loss potential** - Unlike buying stocks (where your maximum loss is your investment), short selling has theoretically unlimited loss potential if the stock price rises significantly
    - **Margin requirements** - Short selling requires a margin account and is subject to margin calls
    - **Short squeeze** - When a heavily shorted stock rises, short sellers may rush to cover, driving the price even higher
    """)
    
    st.subheader("Risk Management")
    st.markdown("""
    Risk management is crucial for successful trading. Our app provides these key risk parameters:
    
    **Entry Price** - The optimal price to enter a trade.
    
    **Stop Loss** - The price at which you should exit to minimize losses.
    
    **Take Profit** - The price at which you should consider taking profits.
    
    **Hold Time** - Suggested duration for an intraday trade.
    
    As a beginner, consider these guidelines:
    1. Never risk more than 1-2% of your capital on a single trade
    2. Always use stop losses to protect your capital
    3. Don't chase losses - stick to your strategy
    4. Be aware of broker fees and taxes, which can impact overall profitability
    """)
    
    st.subheader("Emotional Barriers to Trading")
    st.markdown("""
    Trading psychology is often overlooked but extremely important:
    
    **Fear** - May cause you to exit profitable trades too early or avoid good opportunities.
    
    **Greed** - May cause you to hold losing positions too long or take excessive risks.
    
    **Overconfidence** - May lead to overtrading or ignoring risk management rules.
    
    **Impatience** - May cause you to enter trades without proper analysis.
    
    Tips for emotional control:
    1. Follow your trading plan and stick to your rules
    2. Keep a trading journal to review decisions objectively
    3. Take breaks when feeling emotionally overwhelmed
    4. Focus on the process, not just the outcomes
    5. Start with small positions until you build confidence
    """)

# Auto-refresh functionality
if auto_refresh:
    st.markdown(f"<meta http-equiv='refresh' content='{refresh_interval}'>", unsafe_allow_html=True)