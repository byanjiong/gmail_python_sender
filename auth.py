import os
import sys
import logging
from gmail_core import get_credentials, TOKEN_PATH
from setup_logging import setup_logging

setup_logging()

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1].lower() == 'remove':
        if os.path.exists(TOKEN_PATH):
            os.remove(TOKEN_PATH)
            logging.info("Token removed.")
        else:
            logging.info("No token found.")
    else:
        logging.info("Starting authentication...")
        if os.path.exists(TOKEN_PATH):
            logging.error("Token exists. Remove it first.")
        else:
            try:
                creds = get_credentials()
                if creds and creds.valid: logging.info("Authentication successful.")
            except Exception as e:
                logging.error(f"Auth Error: {e}")