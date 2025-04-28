import time
import subprocess  # To call another Python file for trading logic

# Set the polling interval (4 hours)
POLL_INTERVAL = 14400  # 4 hours in seconds

while True:
    try:
        # Run the live trading logic
        print("Running trading strategy...")
        subprocess.run(['python', 'live_trading/live_ibkr.py'])

        # Sleep for the polling interval (4 hours)
        print(f"Sleeping for {POLL_INTERVAL} seconds...")
        time.sleep(POLL_INTERVAL)

    except Exception as e:
        print(f"Error while running trading logic: {e}")
        break