import sys
import logging
from setup_logging import setup_logging
from gmail_core import get_sheets_service, process_bulk_email

def get_sheet_data(sheet_id, sheet_name=None):
    try:
        service = get_sheets_service()
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

if __name__ == '__main__':
    setup_logging()
    if len(sys.argv) < 2:
        logging.error("Usage: python3 send_googlesheet.py <SHEET_ID> [SHEET_NAME]")
        sys.exit(1)
    
    s_id = sys.argv[1]
    s_name = sys.argv[2] if len(sys.argv) > 2 else None
    
    logging.info(f"Reading Sheet ID: {s_id}...")
    data = get_sheet_data(s_id, s_name)
    
    if data: process_bulk_email(data)