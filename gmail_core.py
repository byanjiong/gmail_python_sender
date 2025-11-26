import os
import sys
import base64
import re
import time
import mimetypes
import random
import string
import logging
import datetime
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

SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/spreadsheets.readonly',
    'https://www.googleapis.com/auth/drive.metadata.readonly'
]

# Configs
ENABLE_TRACKING = True
TRACKING_URL_BASE = "https://your-domain.com/tracker/tracker.php" # CHANGE THIS
HISTORY_FILENAME = "sent_history.log"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_PATH = os.path.join(BASE_DIR, 'token.json')
CREDENTIALS_PATH = os.path.join(BASE_DIR, 'credentials.json')
HISTORY_PATH = os.path.join(BASE_DIR, 'log', HISTORY_FILENAME)

def get_credentials():
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
    if not text: return ""
    lower_data = {k.lower(): str(v) for k, v in data_dict.items() if v is not None}
    def replacer(match):
        key = match.group(1).strip().lower()
        return lower_data.get(key, match.group(0))
    return re.sub(r'\{\{(.*?)\}\}', replacer, text)

def validate_recipients(data_item):
    to = data_item.get('email') or data_item.get('to')
    cc = data_item.get('cc')
    bcc = data_item.get('bcc')
    return True if any([to, cc, bcc]) else False

def extract_attachments(data_item):
    files = []
    logs = []
    for key, value in data_item.items():
        if key.lower().startswith('attachment') and value:
            if os.path.exists(value):
                files.append(value)
            else:
                msg = f"Attachment skipped (not found): {value}"
                logging.warning(msg)
                logs.append({'type': 'warning', 'msg': msg})
    return files, logs

def create_message(sender, to, subject, body_html, cc=None, bcc=None, attachments=None):
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
            if not os.path.exists(filepath): continue
            ctype, encoding = mimetypes.guess_type(filepath)
            if ctype is None or encoding is not None: ctype = 'application/octet-stream'
            main_type, sub_type = ctype.split('/', 1)
            try:
                with open(filepath, 'rb') as f: file_data = f.read()
                if main_type == 'text': part = MIMEText(file_data.decode('utf-8'), _subtype=sub_type)
                elif main_type == 'image': part = MIMEImage(file_data, _subtype=sub_type)
                elif main_type == 'audio': part = MIMEAudio(file_data, _subtype=sub_type)
                else:
                    part = MIMEBase(main_type, sub_type)
                    part.set_payload(file_data)
                    encoders.encode_base64(part)
                part.add_header('Content-Disposition', 'attachment', filename=os.path.basename(filepath))
                message.attach(part)
            except Exception as e:
                logging.error(f"Error attaching {filepath}: {e}")

    return {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}

def load_sent_history():
    sent = set()
    if os.path.exists(HISTORY_PATH):
        try:
            with open(HISTORY_PATH, 'r', encoding='utf-8') as f:
                for line in f:
                    parts = line.strip().split('‡')
                    if len(parts) >= 3: sent.add(parts[2].strip()) # Index 2 is email
                    elif line.strip(): sent.add(line.strip()) # Fallback for old logs
        except Exception as e:
            logging.error(f"Error reading history file: {e}")
    return sent

def log_sent_email(data_source, body_content, attachment_count):
    try:
        os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        uid = data_source.get('__gmail_id', '')
        email = data_source.get('email') or data_source.get('to') or ''
        cc = data_source.get('cc') or ''
        bcc = data_source.get('bcc') or ''
        subject = data_source.get('subject') or ''
        
        clean_body = body_content.replace('\n', ' ').replace('\r', '')
        if len(clean_body) > 100: clean_body = clean_body[:97] + "..."
            
        entry = f"{now}‡{uid}‡{email}‡{cc}‡{bcc}‡{subject}‡{clean_body}‡{attachment_count}\n"
        with open(HISTORY_PATH, 'a', encoding='utf-8') as f:
            f.write(entry)
    except Exception as e:
        logging.error(f"Failed to write to sent history: {e}")

def process_bulk_email(data_source_list, daily_limit=450):
    logs = [] 
    if not data_source_list:
        logging.warning('No data provided to process.')
        return logs

    try:
        service = get_gmail_service()
    except Exception as e:
        logging.critical(f"Authentication failed: {str(e)}")
        return logs

    sent_history = load_sent_history()
    session_count = 0
    default_body = "<html><body><p>Hi {{ name }},</p><p>Update attached.</p></body></html>"

    for i, data in enumerate(data_source_list):
        data = {k.strip().lower(): v for k, v in data.items() if k}
        if not validate_recipients(data): continue

        primary_email = data.get('email') or data.get('to')
        # if primary_email and primary_email in sent_history: continue
        if session_count >= daily_limit:
            logging.warning(f"Daily limit of {daily_limit} reached.")
            break

        unique_id = data.get('__gmail_id')
        if not unique_id:
            unique_id = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
            data['__gmail_id'] = unique_id

        logging.info(f"Processing: {primary_email} (ID: {unique_id})...")

        raw_subject = data.get('subject', 'Update')
        raw_body = data.get('body', default_body)
        
        tracker = f"{TRACKING_URL_BASE}?id={unique_id}&user={primary_email or 'unknown'}"
        data['tracker_url'] = tracker

        final_subject = replace_placeholders(raw_subject, data)
        final_body = replace_placeholders(raw_body, data)
        
        if ENABLE_TRACKING and 'tracker.php' not in final_body:
            pixel = f'<img src="{tracker}" width="1" height="1"/>'
            final_body = final_body.replace('</body>', f'{pixel}</body>') if '</body>' in final_body else final_body + pixel

        files, _ = extract_attachments(data)
        msg = create_message("me", primary_email, final_subject, final_body, data.get('cc'), data.get('bcc'), files)
        
        try:
            service.users().messages().send(userId="me", body=msg).execute()
            log_sent_email(data, final_body, len(files))
            session_count += 1
            logging.info(f"SENT: {primary_email}")
            time.sleep(1.5)
        except HttpError as error:
            logging.error(f"Error sending to {primary_email}: {error}")

    logging.info(f"Batch complete. Sent {session_count} emails.")
    return logs