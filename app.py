import os
import time
import logging
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # Output to container logs
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

TAAPI_API_KEY = os.getenv('TAAPI_API_KEY')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
EXCHANGE = os.getenv('EXCHANGE', 'BINANCE')  # Default to BINANCE
INTERVAL = os.getenv('INTERVAL', '24h')  # Default to 24 hours
WATCH_LIST = os.getenv('WATCH_LIST', 'BTC/USDT,ETH/USDT').split(',')  # Comma-separated list

# Check if required environment variables are set
if not all([TAAPI_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID]):
    logger.error("Required environment variables are missing: TAAPI_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID")
    raise ValueError("Required environment variables are missing")

def get_mfi(symbol):
    url = f"https://api.taapi.io/mfi?secret={TAAPI_API_KEY}&exchange={EXCHANGE}&symbol={symbol}&interval={INTERVAL}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            mfi = data.get('value')
            logger.info(f"MFI for {symbol}: {mfi}")
            return mfi
        else:
            logger.error(f"Error fetching MFI for {symbol}: {response.text}")
            return None
    except Exception as e:
        logger.error(f"Exception while fetching MFI for {symbol}: {str(e)}")
        return None

def send_telegram_notification(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message
    }
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            logger.info(f"Notification sent: {message}")
        else:
            logger.error(f"Error sending notification: {response.text}")
    except Exception as e:
        logger.error(f"Exception while sending notification: {str(e)}")

def check_watch_list():
    logger.info(f"Checking watch list at {datetime.now()}")
    for symbol in WATCH_LIST:
        mfi = get_mfi(symbol)
        if mfi is not None:
            if mfi < 30:
                message = f"Alert! {symbol} is oversold: MFI = {mfi} (below 30)"
                send_telegram_notification(message)
            elif mfi > 70:
                message = f"Alert! {symbol} is overbought: MFI = {mfi} (above 70)"
                send_telegram_notification(message)
        # Add 5-minute delay between API requests (300 seconds)
        logger.info("Waiting 5 minutes before next API request")
        time.sleep(300)

# Scheduler setup
scheduler = BackgroundScheduler()
scheduler.add_job(check_watch_list, 'interval', hours=4)  # Every 4 hours

# Run the first check immediately
logger.info("Performing initial watch list check")
check_watch_list()

# Start the scheduler
scheduler.start()

logger.info("Application started. Waiting for scheduled checks...")
try:
    while True:
        time.sleep(1)  # Keep the program running
except (KeyboardInterrupt, SystemExit):
    logger.info("Shutting down scheduler")
    scheduler.shutdown()