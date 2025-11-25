import os
import sys
import logging
from gmail_core import get_credentials, TOKEN_PATH
from log import setup_logging

# --- INITIALIZATION ---
# This sets up the logging to log/process.log
setup_logging()

def remove_token():
    """
    Removes the existing token.json file.
    """
    if os.path.exists(TOKEN_PATH):
        try:
            os.remove(TOKEN_PATH)
            logging.info("Token removed successfully by user request.")
            print("Token removed.") # minimal feedback
        except OSError as e:
            logging.error(f"Failed to remove token: {e}")
            print(f"Error: {e}")
    else:
        logging.warning("Attempted to remove token, but none was found.")
        print("No token found to remove.")

def authenticate_only():
    """
    Runs the authentication flow. Fails if token already exists.
    """
    logging.info("Starting authentication process...")
    
    # 1. Check if token already exists
    if os.path.exists(TOKEN_PATH):
        msg = "Authentication aborted: 'token.json' already exists. Please remove the previous token first or contact admin."
        logging.error(msg)
        print("FAILED: Token exists.") # minimal feedback
        sys.exit(1)

    # 2. Attempt Authentication
    try:
        # get_credentials() will trigger the local server flow
        creds = get_credentials()
        
        if creds and creds.valid:
            logging.info("Authentication successful. New token.json generated.")
            print("SUCCESS: Authenticated.")
        else:
            logging.error("Authentication failed: Credentials invalid.")
            print("FAILED: Invalid credentials.")
            
    except Exception as e:
        logging.error(f"Authentication Process Error: {str(e)}")
        print(f"ERROR: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    # usage: python auth.py [remove]
    if len(sys.argv) > 1 and sys.argv[1].lower() == 'remove':
        remove_token()
    else:
        authenticate_only()