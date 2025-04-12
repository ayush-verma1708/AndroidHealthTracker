import os
import datetime
import json
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import JSONB

# Get database connection string from environment variables
DATABASE_URL = os.environ.get('DATABASE_URL')

# Create SQLAlchemy engine and session factory
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for SQLAlchemy models
Base = declarative_base()

# Define database models
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True)
    phone_number = Column(String)  # For Twilio alerts
    created_at = Column(DateTime, default=datetime.datetime.now)
    
class Portfolio(Base):
    __tablename__ = "portfolios"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    ticker = Column(String, index=True)
    quantity = Column(Float)
    avg_price = Column(Float)
    position_type = Column(String)  # 'LONG' or 'SHORT'
    timestamp = Column(DateTime, default=datetime.datetime.now)
    confidence_score = Column(Float)
    
class Trade(Base):
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    ticker = Column(String, index=True)
    action = Column(String)  # 'BUY', 'SELL', 'SHORT', 'COVER'
    position_type = Column(String)  # 'LONG' or 'SHORT'
    quantity = Column(Float)
    price = Column(Float)
    value = Column(Float)
    fee = Column(Float)
    pnl = Column(Float, nullable=True)
    pnl_percent = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.now)
    confidence_score = Column(Float)
    
class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    ticker = Column(String, index=True)
    signal_type = Column(String)  # 'BUY', 'SELL', 'SHORT', 'COVER'
    price = Column(Float)
    score = Column(Float)
    is_read = Column(Boolean, default=False)
    is_sent = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=datetime.datetime.now)
    
class AlertLog(Base):
    __tablename__ = "alert_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    type = Column(String)  # 'SMS', 'EMAIL', etc.
    recipient = Column(String)
    message = Column(Text)
    status = Column(String)
    error = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.now)
    sid = Column(String, nullable=True)  # Twilio message SID
    
class UserSettings(Base):
    __tablename__ = "user_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, unique=True, index=True)
    currency = Column(String, default="INR")
    broker_fee_percent = Column(Float, default=0.05)
    alert_frequency = Column(Integer, default=15)  # Minutes between alerts
    indicator_settings = Column(JSONB)
    strategy_type = Column(String, default="Balanced")
    
class WatchList(Base):
    __tablename__ = "watchlists"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    ticker = Column(String)
    added_at = Column(DateTime, default=datetime.datetime.now)

# Create all tables in the database
Base.metadata.create_all(bind=engine)

# Helper functions for database operations
def get_db():
    """Get a database session."""
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()

def create_default_user(db=None):
    """Create a default user if no users exist."""
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    
    try:
        user_count = db.query(User).count()
        if user_count == 0:
            default_user = User(
                username="default_user",
                email="default@example.com",
                phone_number=""
            )
            db.add(default_user)
            db.commit()
            
            # Add default settings
            default_settings = UserSettings(
                user_id=default_user.id,
                currency="INR",
                broker_fee_percent=0.05,
                alert_frequency=15,
                indicator_settings=json.dumps({
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
                }),
                strategy_type="Balanced"
            )
            db.add(default_settings)
            db.commit()
            
            return default_user
    finally:
        if close_db:
            db.close()

def get_default_user_id(db=None):
    """Get the ID of the default user, creating one if needed."""
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    
    try:
        user = db.query(User).first()
        if not user:
            user = create_default_user(db)
        return user.id
    finally:
        if close_db:
            db.close()

def load_portfolio(user_id=None, db=None):
    """Load portfolio data from database."""
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    
    try:
        if user_id is None:
            user_id = get_default_user_id(db)
        
        portfolio = {}
        portfolio_items = db.query(Portfolio).filter(Portfolio.user_id == user_id).all()
        
        for item in portfolio_items:
            portfolio[item.ticker] = {
                'quantity': item.quantity,
                'avg_price': item.avg_price,
                'position_type': item.position_type,
                'timestamp': item.timestamp,
                'confidence_score': item.confidence_score
            }
        
        return portfolio
    finally:
        if close_db:
            db.close()

def save_portfolio(portfolio, user_id=None, db=None):
    """Save portfolio data to database."""
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    
    try:
        if user_id is None:
            user_id = get_default_user_id(db)
        
        # Delete existing portfolio items
        db.query(Portfolio).filter(Portfolio.user_id == user_id).delete()
        
        # Add new portfolio items
        for ticker, position in portfolio.items():
            portfolio_item = Portfolio(
                user_id=user_id,
                ticker=ticker,
                quantity=position['quantity'],
                avg_price=position['avg_price'],
                position_type=position.get('position_type', 'LONG'),
                timestamp=position['timestamp'],
                confidence_score=position['confidence_score']
            )
            db.add(portfolio_item)
        
        db.commit()
    finally:
        if close_db:
            db.close()

def load_trades(user_id=None, db=None):
    """Load trade history from database."""
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    
    try:
        if user_id is None:
            user_id = get_default_user_id(db)
        
        trades = []
        trade_items = db.query(Trade).filter(Trade.user_id == user_id).order_by(Trade.timestamp.desc()).all()
        
        for item in trade_items:
            trade = {
                'ticker': item.ticker,
                'action': item.action,
                'position_type': item.position_type,
                'quantity': item.quantity,
                'price': item.price,
                'value': item.value,
                'fee': item.fee,
                'timestamp': item.timestamp,
                'confidence_score': item.confidence_score
            }
            
            if item.pnl is not None:
                trade['pnl'] = item.pnl
            
            if item.pnl_percent is not None:
                trade['pnl_percent'] = item.pnl_percent
            
            trades.append(trade)
        
        return trades
    finally:
        if close_db:
            db.close()

def save_trade(trade, user_id=None, db=None):
    """Save a trade to database."""
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    
    try:
        if user_id is None:
            user_id = get_default_user_id(db)
        
        trade_item = Trade(
            user_id=user_id,
            ticker=trade['ticker'],
            action=trade['action'],
            position_type=trade.get('position_type', 'LONG'),
            quantity=trade['quantity'],
            price=trade['price'],
            value=trade['value'],
            fee=trade['fee'],
            timestamp=trade['timestamp'],
            confidence_score=trade['confidence_score']
        )
        
        if 'pnl' in trade:
            trade_item.pnl = trade['pnl']
        
        if 'pnl_percent' in trade:
            trade_item.pnl_percent = trade['pnl_percent']
        
        db.add(trade_item)
        db.commit()
    finally:
        if close_db:
            db.close()

def load_alerts(user_id=None, db=None):
    """Load app alerts from database."""
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    
    try:
        if user_id is None:
            user_id = get_default_user_id(db)
        
        alerts = []
        alert_items = db.query(Alert).filter(Alert.user_id == user_id).order_by(Alert.timestamp.desc()).all()
        
        for item in alert_items:
            alerts.append({
                'timestamp': item.timestamp,
                'ticker': item.ticker,
                'signal_type': item.signal_type,
                'price': item.price,
                'score': item.score,
                'is_read': item.is_read
            })
        
        return alerts
    finally:
        if close_db:
            db.close()

def save_alert(alert, user_id=None, db=None):
    """Save an alert to database."""
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    
    try:
        if user_id is None:
            user_id = get_default_user_id(db)
        
        alert_item = Alert(
            user_id=user_id,
            ticker=alert['ticker'],
            signal_type=alert['signal_type'],
            price=alert['price'],
            score=alert['score'],
            is_read=alert.get('is_read', False),
            is_sent=alert.get('is_sent', False),
            timestamp=alert['timestamp']
        )
        
        db.add(alert_item)
        db.commit()
    finally:
        if close_db:
            db.close()

def load_alert_logs(user_id=None, db=None):
    """Load alert logs from database."""
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    
    try:
        if user_id is None:
            user_id = get_default_user_id(db)
        
        logs = []
        log_items = db.query(AlertLog).filter(AlertLog.user_id == user_id).order_by(AlertLog.timestamp.desc()).all()
        
        for item in log_items:
            log = {
                'timestamp': item.timestamp,
                'type': item.type,
                'recipient': item.recipient,
                'message': item.message,
                'status': item.status
            }
            
            if item.error:
                log['error'] = item.error
            
            if item.sid:
                log['sid'] = item.sid
            
            logs.append(log)
        
        return logs
    finally:
        if close_db:
            db.close()

def save_alert_log(log, user_id=None, db=None):
    """Save an alert log to database."""
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    
    try:
        if user_id is None:
            user_id = get_default_user_id(db)
        
        log_item = AlertLog(
            user_id=user_id,
            type=log['type'],
            recipient=log['recipient'],
            message=log['message'],
            status=log['status'],
            timestamp=log['timestamp']
        )
        
        if 'error' in log:
            log_item.error = log['error']
        
        if 'sid' in log:
            log_item.sid = log['sid']
        
        db.add(log_item)
        db.commit()
    finally:
        if close_db:
            db.close()

def load_user_settings(user_id=None, db=None):
    """Load user settings from database."""
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    
    try:
        if user_id is None:
            user_id = get_default_user_id(db)
        
        settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
        
        if not settings:
            # Create default settings
            settings = UserSettings(
                user_id=user_id,
                currency="INR",
                broker_fee_percent=0.05,
                alert_frequency=15,
                indicator_settings=json.dumps({
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
                }),
                strategy_type="Balanced"
            )
            db.add(settings)
            db.commit()
        
        # Parse indicator settings JSON if needed
        indicator_settings = settings.indicator_settings
        if isinstance(indicator_settings, str):
            indicator_settings = json.loads(indicator_settings)
        
        # Return as dictionary
        return {
            'currency': settings.currency,
            'broker_fee_percent': settings.broker_fee_percent,
            'alert_frequency': settings.alert_frequency,
            'indicator_settings': indicator_settings,
            'strategy_type': settings.strategy_type
        }
    finally:
        if close_db:
            db.close()

def save_user_settings(settings, user_id=None, db=None):
    """Save user settings to database."""
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    
    try:
        if user_id is None:
            user_id = get_default_user_id(db)
        
        user_settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
        
        if not user_settings:
            user_settings = UserSettings(user_id=user_id)
            db.add(user_settings)
        
        # Update settings
        if 'currency' in settings:
            user_settings.currency = settings['currency']
        
        if 'broker_fee_percent' in settings:
            user_settings.broker_fee_percent = settings['broker_fee_percent']
        
        if 'alert_frequency' in settings:
            user_settings.alert_frequency = settings['alert_frequency']
        
        if 'indicator_settings' in settings:
            # Convert to JSON string if needed
            indicator_settings = settings['indicator_settings']
            if not isinstance(indicator_settings, str):
                indicator_settings = json.dumps(indicator_settings)
            user_settings.indicator_settings = indicator_settings
        
        if 'strategy_type' in settings:
            user_settings.strategy_type = settings['strategy_type']
        
        db.commit()
    finally:
        if close_db:
            db.close()

def load_watchlist(user_id=None, db=None):
    """Load watchlist from database."""
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    
    try:
        if user_id is None:
            user_id = get_default_user_id(db)
        
        watchlist = []
        watchlist_items = db.query(WatchList).filter(WatchList.user_id == user_id).order_by(WatchList.added_at).all()
        
        for item in watchlist_items:
            watchlist.append(item.ticker)
        
        return watchlist
    finally:
        if close_db:
            db.close()

def save_watchlist(tickers, user_id=None, db=None):
    """Save watchlist to database."""
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    
    try:
        if user_id is None:
            user_id = get_default_user_id(db)
        
        # Delete existing watchlist
        db.query(WatchList).filter(WatchList.user_id == user_id).delete()
        
        # Add new watchlist items
        for ticker in tickers:
            watchlist_item = WatchList(
                user_id=user_id,
                ticker=ticker
            )
            db.add(watchlist_item)
        
        db.commit()
    finally:
        if close_db:
            db.close()

def add_to_watchlist(ticker, user_id=None, db=None):
    """Add a ticker to watchlist."""
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    
    try:
        if user_id is None:
            user_id = get_default_user_id(db)
        
        # Check if ticker already exists
        existing = db.query(WatchList).filter(
            WatchList.user_id == user_id,
            WatchList.ticker == ticker
        ).first()
        
        if not existing:
            watchlist_item = WatchList(
                user_id=user_id,
                ticker=ticker
            )
            db.add(watchlist_item)
            db.commit()
            return True
        
        return False
    finally:
        if close_db:
            db.close()

def remove_from_watchlist(ticker, user_id=None, db=None):
    """Remove a ticker from watchlist."""
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    
    try:
        if user_id is None:
            user_id = get_default_user_id(db)
        
        db.query(WatchList).filter(
            WatchList.user_id == user_id,
            WatchList.ticker == ticker
        ).delete()
        
        db.commit()
        return True
    finally:
        if close_db:
            db.close()

def get_overall_pnl(user_id=None, db=None):
    """Calculate overall P&L from trades."""
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    
    try:
        if user_id is None:
            user_id = get_default_user_id(db)
        
        pnl_sum = db.query(db.func.sum(Trade.pnl)).filter(
            Trade.user_id == user_id,
            Trade.pnl.isnot(None)
        ).scalar()
        
        return pnl_sum or 0.0
    finally:
        if close_db:
            db.close()

def initialize_db():
    """Initialize database with default user if needed."""
    db = SessionLocal()
    try:
        create_default_user(db)
    finally:
        db.close()

# Initialize database when module is imported
initialize_db()