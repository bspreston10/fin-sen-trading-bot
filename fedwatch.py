import yaml
from datetime import datetime
import os


def fedwatch_sentiment():
    # Get the absolute path of the current script directory
    current_dir = os.path.dirname(__file__)
    
    # Build the path to settings.yaml relative to the current script
    settings_path = os.path.join(current_dir, 'settings.yaml')
    
    with open(settings_path, 'r') as f:
        settings = yaml.safe_load(f)
    
    fedwatch_settings = settings['fedwatch_settings']
    sentiment = fedwatch_settings['sentiment']
    probability = fedwatch_settings['probability']
    fed_date = datetime.strptime(fedwatch_settings['fed_date'], "%Y-%m-%d").date()

    return sentiment, probability, fed_date