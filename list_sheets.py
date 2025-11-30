import json
import logging
from googleapiclient.discovery import build
from gmail_core import get_credentials

def list_spreadsheets():
    """
    Returns a JSON string of spreadsheets found in the user's Drive.
    """
    try:
        creds = get_credentials()
        if not creds:
            return json.dumps({"error": "No credentials found"})

        service = build('drive', 'v3', credentials=creds, cache_discovery=False)
        
        # Query for Google Sheets mimeType and not in trash
        query = "mimeType='application/vnd.google-apps.spreadsheet' and trashed=false"
        
        results = service.files().list(
            q=query,
            pageSize=30, # Limit to 30 recent sheets
            orderBy="modifiedTime desc",
            fields="files(id, name)"
        ).execute()
        
        items = results.get('files', [])
        return json.dumps(items)
        
    except Exception as e:
        return json.dumps({"error": str(e)})

if __name__ == '__main__':
    # Print to stdout so PHP can read it
    print(list_spreadsheets())