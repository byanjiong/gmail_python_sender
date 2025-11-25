import sys
from gmail_core import get_sheets_service, process_bulk_email

def get_first_sheet_name(service, sheet_id):
    spreadsheet = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
    sheets = spreadsheet.get('sheets', [])
    return sheets[0]['properties']['title'] if sheets else 'Sheet1'

def get_sheet_data_as_objects(sheet_id, sheet_name=None):
    """
    Extracts data from Google Sheet and returns a list of data_source dicts.
    Returns None on error.
    """
    try:
        service = get_sheets_service()
        if not sheet_name:
            sheet_name = get_first_sheet_name(service, sheet_id)
            print(f"Auto-detected sheet: {sheet_name}")

        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=sheet_id, range=sheet_name).execute()
        rows = result.get('values', [])
        
        if len(rows) < 2:
            return []

        headers = [h.strip().lower() for h in rows[0]]
        data_objects = []

        for row_values in rows[1:]:
            row_dict = {}
            for i, val in enumerate(row_values):
                if i < len(headers):
                    row_dict[headers[i]] = val
            data_objects.append(row_dict)
            
        return data_objects
    except Exception as e:
        print(f"[ERROR] Sheet Read Error: {str(e)}")
        return None

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 sheet_sender.py <SHEET_ID> [SHEET_NAME]")
        sys.exit(1)
    
    s_id = sys.argv[1]
    s_name = sys.argv[2] if len(sys.argv) > 2 else None
    
    print(f"Reading Sheet ID: {s_id}...")
    
    # 1. Extract
    data_source_list = get_sheet_data_as_objects(s_id, s_name)
    
    if data_source_list is None:
        sys.exit(1)
        
    # 2. Send (Using Unified Core)
    results = process_bulk_email(data_source_list)
    
    for log in results:
        print(f"[{log['type'].upper()}] {log['msg']}")