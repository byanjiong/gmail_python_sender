import sys
from gmail_core import process_bulk_email

def send_one_email(data_source):
    """
    Sends a single email using the unified core processor.
    Args:
        data_source: Dict containing {email, name, subject, body, ...}
    Returns:
        List of log objects.
    """
    # Wrap the single item in a list to use the batch processor
    batch_list = [data_source]
    
    # Process with limit 1
    logs = process_bulk_email(batch_list, daily_limit=1)
    return logs

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python3 send_one.py <email> <name>")
        sys.exit(1)
    
    # Construct data_source from CLI args
    data = {
        'email': sys.argv[1],
        'name': sys.argv[2],
        'subject': 'We received your form', # Default subject
        'body': """
        <html><body>
        <p>Hi {{ name }},</p>
        <p>Thanks for your submission.</p>
        </body></html>
        """
    }
    
    results = send_one_email(data)
    
    for log in results:
        print(f"[{log['type'].upper()}] {log['msg']}")