import os
import sys
import base64
import re
import time
import mimetypes
import random
import string
from email.message import EmailMessage
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from email import encoders

# --- CONFIGURATION ---
SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/spreadsheets.readonly'
]

# Default Configs (Can be overridden by arguments)
TRACKING_URL_BASE = "https://your-domain.com/tracker/tracker.php"
HISTORY_FILE = "sent_history.log"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_PATH = os.path.join(BASE_DIR, 'token.json')
CREDENTIALS_PATH = os.path.join(BASE_DIR, 'credentials.json')
HISTORY_PATH = os.path.join(BASE_DIR, HISTORY_FILE)

def get_credentials():
    """Handles the OAuth2 login process."""
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_PATH):
                raise FileNotFoundError(f"credentials.json not found at {CREDENTIALS_PATH}")
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
            
        try:
            with open(TOKEN_PATH, 'w') as token:
                token.write(creds.to_json())
        except PermissionError:
            pass 
    return creds

def get_gmail_service():
    return build('gmail', 'v1', credentials=get_credentials())

def get_sheets_service():
    return build('sheets', 'v4', credentials=get_credentials())

def replace_placeholders(text, data_dict):
    """Replaces {{ key }} in text with values from data_dict."""
    if not text:
        return ""
    
    lower_data = {k.lower(): str(v) for k, v in data_dict.items() if v is not None}

    def replacer(match):
        key = match.group(1).strip().lower()
        return lower_data.get(key, match.group(0))

    return re.sub(r'\{\{(.*?)\}\}', replacer, text)

def validate_recipients(data_item):
    """Returns True if at least one recipient field (email/to, cc, bcc) is present."""
    to = data_item.get('email') or data_item.get('to')
    cc = data_item.get('cc')
    bcc = data_item.get('bcc')
    if not any([to, cc, bcc]):
        return False
    return True

def extract_attachments(data_item):
    """
    Finds keys starting with 'attachment'.
    Returns:
        files: List of valid file paths.
        logs: List of warning dicts for missing files.
    """
    files = []
    logs = []
    for key, value in data_item.items():
        if key.lower().startswith('attachment') and value:
            if os.path.exists(value):
                files.append(value)
            else:
                logs.append({
                    'type': 'warning', 
                    'msg': f"Attachment skipped (not found): {value}"
                })
    return files, logs

def create_message(sender, to, subject, body_html, cc=None, bcc=None, attachments=None):
    """Creates a complex MIME message."""
    message = MIMEMultipart()
    message['from'] = sender
    message['subject'] = subject
    
    if to: message['to'] = to
    if cc: message['cc'] = cc
    if bcc: message['bcc'] = bcc 
    
    msg = MIMEText(body_html, 'html')
    message.attach(msg)

    if attachments:
        for filepath in attachments:
            if not os.path.exists(filepath):
                continue
                
            content_type, encoding = mimetypes.guess_type(filepath)
            if content_type is None or encoding is not None:
                content_type = 'application/octet-stream'
            
            main_type, sub_type = content_type.split('/', 1)
            
            try:
                with open(filepath, 'rb') as f:
                    file_data = f.read()
                
                if main_type == 'text':
                    part = MIMEText(file_data.decode('utf-8'), _subtype=sub_type)
                elif main_type == 'image':
                    part = MIMEImage(file_data, _subtype=sub_type)
                elif main_type == 'audio':
                    part = MIMEAudio(file_data, _subtype=sub_type)
                else:
                    part = MIMEBase(main_type, sub_type)
                    part.set_payload(file_data)
                    encoders.encode_base64(part)
                
                filename = os.path.basename(filepath)
                part.add_header('Content-Disposition', 'attachment', filename=filename)
                message.attach(part)
                
            except Exception as e:
                print(f"Error attaching {filepath}: {e}")

    return {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}

def load_sent_history():
    sent = set()
    if os.path.exists(HISTORY_PATH):
        with open(HISTORY_PATH, 'r') as f:
            for line in f: sent.add(line.strip())
    return sent

def log_sent_email(email):
    if email:
        with open(HISTORY_PATH, 'a') as f: f.write(f"{email}\n")

def process_bulk_email(data_source_list, daily_limit=450):
    """
    Core function to process a list of email data objects.
    Args:
        data_source_list: List of dicts [{email:..., subject:..., body:...}, ...]
        daily_limit: Int, max emails to send in this batch.
    Returns: 
        logs: List of dicts [{'type': '...', 'msg': '...'}]
    """
    logs = []
    
    if not data_source_list:
        logs.append({'type': 'warning', 'msg': 'No data provided to process.'})
        logs.append({'type': 'finish', 'msg': 'Process finished empty'})
        return logs

    try:
        service = get_gmail_service()
    except Exception as e:
        logs.append({'type': 'error', 'msg': f"Authentication failed: {str(e)}"})
        logs.append({'type': 'finish', 'msg': 'Process terminated early'})
        return logs

    sent_history = load_sent_history()
    session_count = 0
    
    # Default fallbacks
    default_subject = "Update"
    default_body = "<html><body><p>Hi {{ name }},</p><p>Update attached.</p></body></html>"

    for i, data in enumerate(data_source_list):
        # Normalize keys
        data = {k.strip().lower(): v for k, v in data.items() if k}

        if not validate_recipients(data):
            continue

        # Robustly get primary email
        primary_email = data.get('email') or data.get('to')
        
        if primary_email and primary_email in sent_history:
            continue
            
        if session_count >= daily_limit:
            logs.append({'type': 'warning', 'msg': f"Daily limit of {daily_limit} reached."})
            break

        # --- UPDATED: Get or Generate Random ID ---
        # If the data source already has an ID, use it. Otherwise, generate one.
        unique_id = data.get('__gmail_id')
        if not unique_id:
            unique_id = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
            data['__gmail_id'] = unique_id

        logs.append({'type': 'info', 'msg': f"Processing: {primary_email} (ID: {unique_id})..."})

        # Prepare Data
        raw_subject = data.get('subject', default_subject)
        raw_body = data.get('body', default_body)
        
        # --- UPDATED: Tracker URL with ID ---
        # Format: tracker.php?id=XYZ&user=abc@example.com
        tracker = f"{TRACKING_URL_BASE}?id={unique_id}&user={primary_email or 'unknown'}"
        data['tracker_url'] = tracker

        final_subject = replace_placeholders(raw_subject, data)
        final_body = replace_placeholders(raw_body, data)
        
        # Inject Tracker
        if 'tracker.php' not in final_body:
            pixel_html = f'<img src="{tracker}" width="1" height="1" style="display:none;" />'
            if '</body>' in final_body:
                final_body = final_body.replace('</body>', f'{pixel_html}</body>')
            else:
                final_body += pixel_html

        # Handle Attachments
        files, attachment_logs = extract_attachments(data)
        logs.extend(attachment_logs)

        # Create & Send
        msg = create_message(
            "me", 
            to=primary_email, 
            subject=final_subject, 
            body_html=final_body,
            cc=data.get('cc'),
            bcc=data.get('bcc'),
            attachments=files
        )
        
        try:
            service.users().messages().send(userId="me", body=msg).execute()
            log_sent_email(primary_email)
            session_count += 1
            # Rate limit
            time.sleep(1.5)
        except HttpError as error:
            logs.append({'type': 'error', 'msg': f"Error sending to {primary_email}: {error}"})

    logs.append({'type': 'finish', 'msg': f"Batch complete. Sent {session_count} emails."})
    return logs