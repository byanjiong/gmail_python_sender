import csv
import sys
import logging
from setup_logging import setup_logging
from gmail_core import process_bulk_email

DAILY_LIMIT = 450 

def get_csv_data_as_objects(filepath):
    try:
        with open(filepath, mode='r', encoding='utf-8') as file:
            return list(csv.DictReader(file))
    except Exception as e:
        logging.error(f"Could not read file: {e}")
        return None

if __name__ == '__main__':
    setup_logging()
    csv_file = sys.argv[1] if len(sys.argv) > 1 else 'recipients.csv'
    logging.info(f"Reading {csv_file}...")
    
    data = get_csv_data_as_objects(csv_file)
    if data:
        process_bulk_email(data, daily_limit=DAILY_LIMIT)
    else:
        sys.exit(1)