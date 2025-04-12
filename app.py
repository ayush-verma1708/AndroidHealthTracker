import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
from utils.data_fetcher import fetch_stock_data, get_available_stocks
from utils.indicators import calculate_indicators
from utils.signal_generator import generate_signals, calculate_composite_score
from utils.risk_manager import calculate_risk_parameters

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

# Header
st.title("Real-Time Intraday Stock Analysis")
st.markdown("""
This tool analyzes stock data in real-time, providing trading signals, key technical indicators, 
and risk management parameters to help with your trading decisions.
""")

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
    
    # Stock search and selection
    stock_search = st.text_input("Search for stocks (e.g., AAPL, MSFT)")
    if stock_search:
        matches = get_available_stocks(stock_search)
        if matches:
            selected_stock = st.selectbox("Select a stock", options=matches)
            if st.button("Add Stock"):
                if selected_stock not in st.session_state.selected_stocks:
                    st.session_state.selected_stocks.append(selected_stock)
                    st.session_state.current_stock = selected_stock
                    st.success(f"Added {selected_stock} to your watchlist!")
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
    
    # Auto-refresh
    st.header("Auto Refresh")
    auto_refresh = st.checkbox("Enable auto refresh", value=False)
    refresh_interval = st.slider("Refresh interval (seconds)", min_value=30, max_value=300, value=60) if auto_refresh else 60

# Main content area
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
                
                # Display trading signal and recommendations
                last_price = latest_data['Close']
                last_score = latest_data['composite_score']
                signal_color = "green" if last_score > 0.6 else "red" if last_score < 0.4 else "orange"
                signal_text = "BUY" if last_score > 0.6 else "SELL" if last_score < 0.4 else "HOLD"
                
                st.subheader("Trading Signal")
                signal_cols = st.columns([1, 2, 2])
                with signal_cols[0]:
                    st.markdown(f"<h2 style='color:{signal_color};text-align:center;'>{signal_text}</h2>", unsafe_allow_html=True)
                with signal_cols[1]:
                    st.metric("Current Price", f"${last_price:.2f}", f"{latest_data['Close_pct_change']:.2f}%" if 'Close_pct_change' in latest_data else None)
                with signal_cols[2]:
                    st.metric("Confidence Score", f"{last_score:.2f}", None)
                
                # Risk management parameters
                st.subheader("Risk Management Parameters")
                risk_cols = st.columns(3)
                with risk_cols[0]:
                    st.metric("Suggested Entry Price", f"${risk_params['entry_price']:.2f}")
                with risk_cols[1]:
                    st.metric("Suggested Stop Loss", f"${risk_params['stop_loss']:.2f}")
                with risk_cols[2]:
                    st.metric("Suggested Take Profit", f"${risk_params['take_profit']:.2f}")
                
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
                    yaxis_title="Price ($)",
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
                fig.update_yaxes(title_text="Price ($)", row=1, col=1)
                fig.update_yaxes(title_text="RSI", row=2, col=1)
                fig.update_yaxes(title_text="MACD", row=3, col=1)
                
                # Show figure
                st.plotly_chart(fig, use_container_width=True)
                
                # Display indicator values table
                st.subheader("Current Technical Indicators")
                indicator_df = pd.DataFrame({
                    'Indicator': ['Price', f'{short_ma}-MA', f'{long_ma}-MA', 'RSI', 'MACD', 'MACD Signal', 'BB Upper', 'BB Middle', 'BB Lower'],
                    'Value': [
                        f"${latest_data['Close']:.2f}",
                        f"${latest_data[f'MA_{short_ma}']:.2f}",
                        f"${latest_data[f'MA_{long_ma}']:.2f}",
                        f"{latest_data['RSI']:.2f}",
                        f"{latest_data['MACD']:.4f}",
                        f"{latest_data['MACD_signal']:.4f}",
                        f"${latest_data['BB_upper']:.2f}",
                        f"${latest_data['BB_middle']:.2f}",
                        f"${latest_data['BB_lower']:.2f}"
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
    
    The tool will provide:
    - Real-time stock data visualization
    - Technical indicator calculations
    - Buy/sell signals based on indicator thresholds
    - Composite scoring for trade recommendations
    - Risk management parameters (stop-loss and take-profit levels)
    """)

# Auto-refresh functionality
if auto_refresh:
    st.markdown(f"<meta http-equiv='refresh' content='{refresh_interval}'>", unsafe_allow_html=True)
