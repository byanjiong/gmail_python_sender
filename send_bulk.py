import csv
import sys
from gmail_core import process_bulk_email

# --- CONFIGURATION ---
DAILY_LIMIT = 450 

def get_csv_data_as_objects(filepath):
    """Reads CSV and returns a list of data_source dicts."""
    recipients = []
    try:
        with open(filepath, mode='r', encoding='utf-8') as file:
            # DictReader uses the first row as headers automatically
            reader = csv.DictReader(file)
            recipients = list(reader)
    except FileNotFoundError:
        return None
    return recipients

if __name__ == '__main__':
    csv_file = 'recipients.csv'
    print(f"Reading {csv_file}...")
    
    data_source_list = get_csv_data_as_objects(csv_file)
    
    if data_source_list is None:
        print(f"[ERROR] {csv_file} not found.")
        sys.exit(1)
    
    print(f"Found {len(data_source_list)} records. Starting process...")
    
    # Call the unified core processor
    results = process_bulk_email(data_source_list, daily_limit=DAILY_LIMIT)
    
    # Print logs
    for log in results:
        print(f"[{log['type'].upper()}] {log['msg']}")