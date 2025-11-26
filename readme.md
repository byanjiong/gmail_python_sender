# **Gmail Tracking & Sending System**

This system allows you to send bulk, personalized emails via the Gmail API with open tracking capabilities. It features a **Web Dashboard** for easy management, log viewing, and token handling, alongside robust Python backend scripts.

## **📂 Project Structure**

Ensure your server folder looks like this:

```text
/your-project-folder/
├── credentials.json       (Uploaded via UI)
├── token.json             (Uploaded via UI)
├── logger_config.py       (Global logging setup)
├── gmail_core.py          (Main logic & API handling)
├── auth.py                (Local auth tool)
├── list_sheets.py         (Helper for UI dropdown)
├── send_csv.py            (CLI: Send from CSV)
├── send_googlesheet.py    (CLI: Send from Sheets)
├── send_one.py            (CLI: Send single email)
├── .gitignore
├── log/                   (Writable by Web Server)
│   ├── process.log
│   ├── sent_history.log
│   └── track_history.log
├── tracker/
│   └── tracker.php        (The tracking pixel)
└── ui/
    └── index.php          (The Dashboard)
````

## **Part 1: Google Cloud Setup (Critical)**

Before installing the software, you must set up your Google Cloud Project correctly to avoid token expiration issues.

1.  **Create Project:** Go to [Google Cloud Console](https://console.cloud.google.com/) and create a project.
2.  **Enable APIs:** Enable **Gmail API**, **Google Sheets API**, and **Google Drive API**.
3.  **Configure OAuth Consent Screen:**
      * User Type: **External**.
      * **IMPORTANT - PUBLISH YOUR APP:**
          * By default, your app is in **"Testing"** mode. Tokens generated in Testing mode **expire after 7 days**.
          * To fix this: Go to **OAuth consent screen** \> Click **PUBLISH APP** (Push to Production).
          * *Note:* You do not need to submit for verification. Just publishing it is enough to make the token permanent.
4.  **Create Credentials:**
      * Go to **Credentials** \> **Create Credentials** \> **OAuth Client ID**.
      * Type: **Desktop App**.
      * Download the JSON file and rename it to `credentials.json`.

## **Part 2: Server Installation**

1.  **Install Requirements:**

    ```bash
    sudo apt-get update
    sudo apt-get install python3 python3-pip
    pip3 install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
    ```

2.  **Upload Files:** Upload the scripts to your web server (e.g., `/var/www/html/gmail-sender/`).

3.  **Set Permissions (Crucial):**
    The web server (usually `www-data`) needs to write to the `log` folder and upload JSON files.

    ```bash
    cd /var/www/html/gmail-sender

    # Create folders if they don't exist
    mkdir -p log

    # Grant ownership to web server
    sudo chown -R www-data:www-data log
    sudo chown www-data:www-data credentials.json token.json 2>/dev/null

    # Grant write permissions
    sudo chmod -R 775 log
    sudo chmod 664 credentials.json token.json 2>/dev/null
    ```

## **Part 3: Authentication (The "Upload" Workflow)**

Since servers usually don't have browsers, we generate the token locally and upload it.

1.  **On your Local Computer:**

      * Install Python and the libraries (`pip install google-api-python-client...`).
      * Place `auth.py` and `credentials.json` in a folder.
      * Run: `python auth.py`
      * A browser will open. **Login** with the Gmail account you want to send from.
      * *Warning:* Since your app is unverified, Google will show a "This app isn't verified" warning. Click **Advanced** -\> **Go to [App Name] (unsafe)** to proceed.
      * This generates a `token.json` file.

2.  **On the Web Dashboard:**

      * Open `http://your-server/gmail-sender/ui/`
      * Enter the password (Default: `123`).
      * Go to the **Auth Setup** tab.
      * Upload `credentials.json` (from Google Cloud).
      * Upload `token.json` (generated from your computer).
      * You are now ready to send\!

## **Part 4: Usage**

### **Web Dashboard (Recommended)**

1.  **Select Sheet:** The UI automatically lists Google Sheets from your Drive (requires the `token.json` to have Drive permissions).
2.  **Select Tab:** Optional. Defaults to the first tab.
3.  **Start Sending:** The process runs in the background. You can see real-time logs and download a CSV report of sent emails.

### **Command Line (Advanced/Cron)**

You can run these scripts manually via SSH:

```bash
# Send from Google Sheet
python3 send_googlesheet.py <SHEET_ID> [SHEET_NAME]

# Send from CSV file
python3 send_csv.py recipients.csv

# Send Single Email (Testing)
python3 send_one.py recipient@example.com "John Doe"
```

## **Part 5: Tracking**

1.  **The Pixel:** The script automatically injects a 1x1 invisible image into every email body.
2.  **Tracker Script:** Ensure `tracker/tracker.php` is accessible from the public internet (e.g., `https://your-domain.com/tracker/tracker.php`).
3.  **Config:** Update `TRACKING_URL_BASE` in `gmail_core.py` to point to your actual domain.

## **Troubleshooting**

### **Token Expired / Auth Errors**

  * **Symptom:** Logs show "invalid\_grant" or authentication failures after a week.
  * **Cause:** Your Google Cloud App is likely still in **"Testing"** mode.
  * **Fix:**
    1.  Go to Google Cloud Console \> OAuth Consent Screen.
    2.  Click **PUBLISH APP**.
    3.  Delete old `token.json` on your computer.
    4.  Run `python auth.py` again to generate a new token.
    5.  Upload the new token via the Web UI.

### **PHP Timeouts**

  * **Symptom:** Sending stops after exactly 30 seconds or \~20-30 emails.
  * **Fix:** The `ui/index.php` script includes `set_time_limit(0)` to prevent this. Ensure your server allows this override (check `php.ini` for `disable_functions`).

<!-- end list -->

```
