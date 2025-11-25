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
    except Exception as e:
        print(f"[ERROR] Could not read file: {e}")
        return None
    return recipients

if __name__ == '__main__':
    # Default filename
    csv_file = 'recipients.csv'

    # Check for command line argument
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
        print(f"Targeting CSV file: {csv_file}")
    else:
        print(f"No file argument provided. Defaulting to '{csv_file}'")

    print(f"Reading {csv_file}...")
    
    data_source_list = get_csv_data_as_objects(csv_file)
    
    if data_source_list is None:
        print(f"[ERROR] {csv_file} not found.")
        print("Usage: python send_csv.py <filename.csv>")
        sys.exit(1)
    
    print(f"Found {len(data_source_list)} records. Starting process...")
    
    # Call the unified core processor
    results = process_bulk_email(data_source_list, daily_limit=DAILY_LIMIT)
    
    # Print logs
    for log in results:
        print(f"[{log['type'].upper()}] {log['msg']}")