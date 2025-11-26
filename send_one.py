import sys
import logging
from setup_logging import setup_logging
from gmail_core import process_bulk_email

if __name__ == '__main__':
    setup_logging()
    if len(sys.argv) < 3:
        logging.error("Usage: python3 send_one.py <email> <name>")
        sys.exit(1)
    
    data = {
        'email': sys.argv[1],
        'name': sys.argv[2],
        'subject': 'We received your form',
        'body': "<html><body><p>Hi {{ name }},</p><p>Thanks for your submission.</p></body></html>"
    }
    process_bulk_email([data], daily_limit=1)