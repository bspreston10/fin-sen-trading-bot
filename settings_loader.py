import os
import yaml
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


settings_path = os.path.join(os.path.dirname(__file__), 'settings.yaml')

# Open and read the settings file
with open(settings_path, 'r') as f:
    settings = yaml.safe_load(f)

# IBKR
HOST = settings['ibkr_connection']['host']
PORT = settings['ibkr_connection']['port']
CLIENT_ID = settings['ibkr_connection']['client_id']

# Contract
SYMBOL = settings['contract_settings']['symbol']
SEC_TYPE = settings['contract_settings']['secType']
EXCHANGE = settings['contract_settings']['exchange']
CURRENCY = settings['contract_settings']['currency']

# Historical Data
DURATION = settings['historical_data']['duration']
BAR_SIZE = settings['historical_data']['bar_size']

# Risk
DRAW_DOWN_ALERT = settings['risk_management']['drawdown_alert_threshold']
RISK_PER_TRADE = settings['risk_management']['risk_per_trade']

# Streamlit
REFRESH_SECONDS = settings['streamlit_settings']['refresh_seconds']
LOG_FILE_PATH = settings['streamlit_settings']['log_file_path']

# Polling
POLL_INTERVAL = settings['polling']['interval_seconds']

# Alerts
TELEGRAM_API_KEY = os.getenv('TELEGRAM_API_KEY')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')