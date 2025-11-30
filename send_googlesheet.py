import sys
import logging
from setup_logging import setup_logging
from gmail_core import get_sheets_service, process_bulk_email, get_credentials
from googleapiclient.discovery import build

def get_sheet_data(sheet_id, sheet_name=None):
    try:
        service = get_sheets_service()
        # If no sheet name provided, get the first one
        if not sheet_name:
            spreadsheet = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
            sheet_name = spreadsheet.get('sheets', [])[0]['properties']['title']
            logging.info(f"Auto-detected sheet: {sheet_name}")

        result = service.spreadsheets().values().get(spreadsheetId=sheet_id, range=sheet_name).execute()
        rows = result.get('values', [])
        
        if len(rows) < 2: return []
        headers = [h.strip().lower() for h in rows[0]]
        return [dict(zip(headers, row)) for row in rows[1:]]
    except Exception as e:
        logging.error(f"Sheet Read Error: {str(e)}")
        return None

def list_recent_sheets(limit=100):
    """Fetches recent Google Sheets using Drive API."""
    try:
        creds = get_credentials()
        service = build('drive', 'v3', credentials=creds, cache_discovery=False)
        
        query = "mimeType='application/vnd.google-apps.spreadsheet' and trashed=false"
        
        results = service.files().list(
            q=query,
            pageSize=limit,
            orderBy="modifiedTime desc",
            fields="files(id, name)"
        ).execute()
        
        return results.get('files', [])
        
    except Exception as e:
        logging.error(f"Error listing sheets: {str(e)}")
        return []

def interactive_mode():
    print("Fetching recent Google Sheets...")
    sheets = list_recent_sheets(50)
    
    if not sheets:
        print("No Google Sheets found in your Drive.")
        return

    # Print the list
    for i, sheet in enumerate(sheets):
        print(f"{i + 1}. {sheet['name']}")
    
    # Loop until valid input
    selected_sheet = None
    while True:
        try:
            val = input("Select spreadsheet? enter number: ")
            idx = int(val) - 1
            if 0 <= idx < len(sheets):
                selected_sheet = sheets[idx]
                break
            else:
                print("Invalid number. Try again.")
        except ValueError:
            print("Please enter a valid number.")

    # Optional Sheet Name
    sheet_name = input("Select sheet name? (blank for default): ").strip()
    if sheet_name == "":
        sheet_name = None

    print("\nSending...")
    
    # Process
    data = get_sheet_data(selected_sheet['id'], sheet_name)
    if data:
        process_bulk_email(data)

if __name__ == '__main__':
    setup_logging()
    
    # Check if running in CLI mode (with arguments) or Interactive mode
    if len(sys.argv) > 1:
        # CLI Mode: python3 send_googlesheet.py <ID> [NAME]
        s_id = sys.argv[1]
        s_name = sys.argv[2] if len(sys.argv) > 2 else None
        
        logging.info(f"Reading Sheet ID: {s_id}...")
        data = get_sheet_data(s_id, s_name)
        if data: process_bulk_email(data)
    else:
        # Interactive Mode
        interactive_mode()