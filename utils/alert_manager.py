import os
import datetime
from twilio.rest import Client
import streamlit as st

# Initialize Twilio client with credentials from environment variables
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER")

def send_sms_alert(to_phone_number, message):
    """
    Send SMS alert using Twilio
    
    Args:
        to_phone_number (str): Recipient's phone number in E.164 format (e.g., +1XXXXXXXXXX)
        message (str): Alert message to send
    
    Returns:
        bool: True if message was sent successfully, False otherwise
    """
    try:
        if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN or not TWILIO_PHONE_NUMBER:
            st.warning("Twilio credentials not configured. SMS alerts disabled.")
            return False
            
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        # Send SMS
        message = client.messages.create(
            body=message,
            from_=TWILIO_PHONE_NUMBER,
            to=to_phone_number
        )
        
        # Log success
        st.session_state.alert_log.append({
            'timestamp': datetime.datetime.now(),
            'type': 'SMS',
            'recipient': to_phone_number,
            'message': message.body,
            'status': 'sent',
            'sid': message.sid
        })
        
        return True
    
    except Exception as e:
        # Log error
        st.session_state.alert_log.append({
            'timestamp': datetime.datetime.now(),
            'type': 'SMS',
            'recipient': to_phone_number,
            'message': message,
            'status': 'failed',
            'error': str(e)
        })
        
        return False

def send_trading_signal_alert(ticker, signal_type, price, score, user_phone):
    """
    Send a formatted trading signal alert
    
    Args:
        ticker (str): Stock ticker symbol
        signal_type (str): Signal type (BUY, SELL, SHORT, COVER)
        price (float): Current price
        score (float): Confidence score
        user_phone (str): User's phone number
        
    Returns:
        bool: True if alert was sent successfully, False otherwise
    """
    # Create timestamp
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Format the message based on signal type
    if signal_type == "BUY":
        message = f"⬆️ BUY ALERT for {ticker}\n"
        message += f"Price: ₹{price:.2f}\n"
        message += f"Confidence: {score:.2f}\n"
        message += f"Time: {now}"
    
    elif signal_type == "SELL":
        message = f"⬇️ SELL ALERT for {ticker}\n"
        message += f"Price: ₹{price:.2f}\n"
        message += f"Confidence: {score:.2f}\n"
        message += f"Time: {now}"
    
    elif signal_type == "SHORT":
        message = f"🔻 SHORT ALERT for {ticker}\n"
        message += f"Price: ₹{price:.2f}\n"
        message += f"Confidence: {score:.2f}\n"
        message += f"Time: {now}"
    
    elif signal_type == "COVER":
        message = f"🔺 COVER ALERT for {ticker}\n"
        message += f"Price: ₹{price:.2f}\n"
        message += f"Confidence: {score:.2f}\n"
        message += f"Time: {now}"
    
    else:
        message = f"ALERT for {ticker}: {signal_type}\n"
        message += f"Price: ₹{price:.2f}\n"
        message += f"Confidence: {score:.2f}\n"
        message += f"Time: {now}"
    
    # Send the alert
    return send_sms_alert(user_phone, message)

def notify_app_alert(ticker, signal_type, price, score):
    """
    Store an alert in the app's state for display
    
    Args:
        ticker (str): Stock ticker symbol
        signal_type (str): Signal type (BUY, SELL, SHORT, COVER)
        price (float): Current price
        score (float): Confidence score
        
    Returns:
        None
    """
    now = datetime.datetime.now()
    
    # Add alert to session state
    st.session_state.app_alerts.append({
        'timestamp': now,
        'ticker': ticker,
        'signal_type': signal_type,
        'price': price,
        'score': score,
        'is_read': False
    })
    
    # Keep only the most recent 50 alerts
    if len(st.session_state.app_alerts) > 50:
        st.session_state.app_alerts = st.session_state.app_alerts[-50:]