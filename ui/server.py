import sys
import os
import threading
import logging
import json
import time
from flask import Flask, render_template_string, request, jsonify, redirect, url_for

# --- 1. SETUP PATHS ---
# Add parent directory to path so we can import gmail_core, etc.
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# Import your existing modules
import gmail_core
import list_sheets
import send_googlesheet
import send_csv

# --- 2. FLASK CONFIG ---
app = Flask(__name__)
app.secret_key = 'super-secret-key-change-this'

# Configuration
LOG_FILE = os.path.join(parent_dir, 'log', 'process.log')
TOKEN_PATH = os.path.join(parent_dir, 'token.json')
CREDENTIALS_PATH = os.path.join(parent_dir, 'credentials.json')

# --- 3. HTML TEMPLATE (Single File UI) ---
# Using a simple Bootstrap layout embedded here for ease of use
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gmail Python Sender</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background-color: #f8f9fa; }
        .card { box-shadow: 0 4px 6px rgba(0,0,0,0.1); border: none; }
        #log-window { 
            height: 400px; 
            overflow-y: scroll; 
            background: #1e1e1e; 
            color: #00ff00; 
            font-family: monospace; 
            padding: 15px;
            font-size: 0.9rem;
            border-radius: 5px;
        }
        .nav-tabs .nav-link.active { font-weight: bold; border-bottom: 3px solid #0d6efd; }
    </style>
</head>
<body class="py-4">

<div class="container">
    <div class="row mb-4">
        <div class="col">
            <h2 class="text-primary"><i class="bi bi-envelope-paper"></i> Gmail Python Sender</h2>
            <p class="text-muted">Secure Python-only Interface</p>
        </div>
        <div class="col-auto">
             <span class="badge bg-success" id="status-badge">System Ready</span>
        </div>
    </div>

    <div class="row">
        <!-- LEFT COLUMN: CONTROLS -->
        <div class="col-md-5">
            <div class="card mb-4">
                <div class="card-header bg-white">
                    <ul class="nav nav-tabs card-header-tabs" id="myTab" role="tablist">
                        <li class="nav-item">
                            <button class="nav-link active" id="sheets-tab" data-bs-toggle="tab" data-bs-target="#sheets" type="button">Google Sheets</button>
                        </li>
                        <li class="nav-item">
                            <button class="nav-link" id="csv-tab" data-bs-toggle="tab" data-bs-target="#csv" type="button">CSV Upload</button>
                        </li>
                        <li class="nav-item">
                            <button class="nav-link" id="auth-tab" data-bs-toggle="tab" data-bs-target="#auth" type="button">Auth</button>
                        </li>
                    </ul>
                </div>
                <div class="card-body">
                    <div class="tab-content" id="myTabContent">
                        
                        <!-- TAB: GOOGLE SHEETS -->
                        <div class="tab-pane fade show active" id="sheets" role="tabpanel">
                            <form id="sheet-form">
                                <div class="mb-3">
                                    <label class="form-label">Select Spreadsheet</label>
                                    <select class="form-select" id="sheet-select" required>
                                        <option value="" disabled selected>Loading sheets...</option>
                                    </select>
                                    <small class="text-muted"><a href="#" onclick="loadSheets(); return false;">Refresh List</a></small>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Sheet Name (Tab)</label>
                                    <input type="text" class="form-control" id="sheet-tab-name" placeholder="e.g. Sheet1 (Optional)">
                                </div>
                                <button type="submit" class="btn btn-primary w-100">Start Sending</button>
                            </form>
                        </div>

                        <!-- TAB: CSV -->
                        <div class="tab-pane fade" id="csv" role="tabpanel">
                            <form id="csv-form" enctype="multipart/form-data">
                                <div class="mb-3">
                                    <label class="form-label">Upload CSV File</label>
                                    <input type="file" class="form-control" id="csv-file" name="file" accept=".csv" required>
                                </div>
                                <button type="submit" class="btn btn-primary w-100">Upload & Send</button>
                            </form>
                        </div>

                        <!-- TAB: AUTH -->
                        <div class="tab-pane fade" id="auth" role="tabpanel">
                            <div class="alert alert-info">
                                <small>Upload <b>credentials.json</b> (from Google Cloud) or <b>token.json</b> (generated locally).</small>
                            </div>
                            <form action="/upload_auth" method="post" enctype="multipart/form-data" class="mb-2">
                                <div class="input-group">
                                    <input type="file" class="form-control" name="file">
                                    <button class="btn btn-outline-secondary" type="submit">Upload</button>
                                </div>
                            </form>
                            <hr>
                            <button onclick="deleteToken()" class="btn btn-danger btn-sm w-100">Delete Existing Token</button>
                        </div>

                    </div>
                </div>
            </div>
        </div>

        <!-- RIGHT COLUMN: LOGS -->
        <div class="col-md-7">
            <div class="card h-100">
                <div class="card-header bg-dark text-white d-flex justify-content-between align-items-center">
                    <span>Live Process Logs</span>
                    <button class="btn btn-sm btn-outline-light" onclick="clearLogDisplay()">Clear View</button>
                </div>
                <div id="log-window">Waiting for action...</div>
            </div>
        </div>
    </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script>
    // --- LOAD SHEETS ON START ---
    async function loadSheets() {
        const select = document.getElementById('sheet-select');
        select.innerHTML = '<option>Loading...</option>';
        try {
            const res = await fetch('/api/get_sheets');
            const data = await res.json();
            select.innerHTML = '<option value="" disabled selected>Select a Sheet</option>';
            
            if(data.error) {
                alert("Error loading sheets: " + data.error);
                return;
            }

            data.forEach(sheet => {
                const opt = document.createElement('option');
                opt.value = sheet.id;
                opt.text = sheet.name;
                select.appendChild(opt);
            });
        } catch (e) {
            select.innerHTML = '<option>Error loading sheets</option>';
            console.error(e);
        }
    }
    loadSheets();

    // --- LOG POLLING ---
    let lastLogPos = 0;
    async function pollLogs() {
        try {
            const res = await fetch('/api/logs?pos=' + lastLogPos);
            const data = await res.json();
            if (data.logs) {
                const logWin = document.getElementById('log-window');
                // Replace newlines with <br> and append
                const htmlLogs = data.logs.replace(/\\n/g, '<br>');
                logWin.innerHTML += htmlLogs;
                logWin.scrollTop = logWin.scrollHeight; // Auto scroll
                lastLogPos = data.pos;
            }
        } catch (e) { console.error(e); }
        setTimeout(pollLogs, 2000);
    }
    pollLogs();

    function clearLogDisplay() {
        document.getElementById('log-window').innerHTML = '';
    }

    // --- FORM HANDLERS ---
    document.getElementById('sheet-form').onsubmit = async (e) => {
        e.preventDefault();
        const sheetId = document.getElementById('sheet-select').value;
        const sheetName = document.getElementById('sheet-tab-name').value;
        
        if (!sheetId) return alert("Please select a sheet");

        if(!confirm("Start sending emails from this sheet?")) return;

        await fetch('/api/send_sheet', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ sheet_id: sheetId, sheet_name: sheetName })
        });
        alert("Process started in background. Check logs.");
    };

    document.getElementById('csv-form').onsubmit = async (e) => {
        e.preventDefault();
        if(!confirm("Start sending emails from this CSV?")) return;
        
        const formData = new FormData(document.getElementById('csv-form'));
        await fetch('/api/send_csv', { method: 'POST', body: formData });
        alert("Process started in background. Check logs.");
    };

    async function deleteToken() {
        if(confirm("Are you sure? You will need to re-authenticate.")) {
            await fetch('/api/delete_token', { method: 'POST' });
            alert("Token deleted.");
        }
    }
</script>
</body>
</html>
"""

# --- 4. BACKEND LOGIC ---

def run_async_process(target_func, args=()):
    """Helper to run email sending in a background thread."""
    thread = threading.Thread(target=target_func, args=args)
    thread.daemon = True
    thread.start()

def task_send_sheet(sheet_id, sheet_name):
    """Wrapper to call send_googlesheet logic."""
    logging.info(f"--- Starting Batch from Sheet: {sheet_id} ---")
    try:
        data = send_googlesheet.get_sheet_data(sheet_id, sheet_name)
        if data:
            gmail_core.process_bulk_email(data)
        else:
            logging.error("No data found in sheet.")
    except Exception as e:
        logging.error(f"Task Failed: {e}")

def task_send_csv(filepath):
    """Wrapper to call send_csv logic."""
    logging.info(f"--- Starting Batch from CSV: {filepath} ---")
    try:
        data = send_csv.get_csv_data_as_objects(filepath)
        if data:
            gmail_core.process_bulk_email(data)
        else:
            logging.error("No data found in CSV.")
    except Exception as e:
        logging.error(f"Task Failed: {e}")
    finally:
        # Clean up temp file
        if os.path.exists(filepath):
            os.remove(filepath)

# --- 5. ROUTES ---

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/get_sheets')
def api_get_sheets():
    # Reuse the list_spreadsheets function directly
    # Note: list_spreadsheets returns a JSON string, so we load it to return clean JSON
    try:
        json_str = list_sheets.list_spreadsheets()
        return jsonify(json.loads(json_str))
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/logs')
def api_logs():
    """Returns content of log file starting from 'pos' byte."""
    pos = int(request.args.get('pos', 0))
    if not os.path.exists(LOG_FILE):
        return jsonify({"logs": "", "pos": 0})
    
    with open(LOG_FILE, 'r') as f:
        f.seek(pos)
        content = f.read()
        new_pos = f.tell()
    
    return jsonify({"logs": content, "pos": new_pos})

@app.route('/api/send_sheet', methods=['POST'])
def api_send_sheet():
    data = request.json
    sheet_id = data.get('sheet_id')
    sheet_name = data.get('sheet_name')
    
    # Run in background
    run_async_process(task_send_sheet, (sheet_id, sheet_name))
    
    return jsonify({"status": "started", "message": "Background task initiated"})

@app.route('/api/send_csv', methods=['POST'])
def api_send_csv():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    # Save to a temp location
    temp_path = os.path.join(parent_dir, 'temp_upload.csv')
    file.save(temp_path)
    
    # Run in background
    run_async_process(task_send_csv, (temp_path,))
    
    return jsonify({"status": "started", "message": "CSV processing initiated"})

@app.route('/upload_auth', methods=['POST'])
def upload_auth():
    if 'file' not in request.files:
        return "No file", 400
    
    file = request.files['file']
    if file.filename in ['credentials.json', 'token.json']:
        file.save(os.path.join(parent_dir, file.filename))
        return redirect('/')
    else:
        return "Invalid filename. Must be credentials.json or token.json", 400

@app.route('/api/delete_token', methods=['POST'])
def delete_token():
    if os.path.exists(TOKEN_PATH):
        os.remove(TOKEN_PATH)
        return jsonify({"status": "deleted"})
    return jsonify({"status": "not_found"})

# --- 6. RUNNER ---
if __name__ == '__main__':
    # Ensure log directory exists
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    
    print(f"Starting Server at http://localhost:5000")
    print(f"Working Directory: {parent_dir}")
    
    app.run(host='0.0.0.0', port=5000, debug=True)