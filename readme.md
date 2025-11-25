
# Gmail Tracking & Sending System - Setup Guide

This system allows you to send bulk or transactional emails via the Gmail API (or Google Sheets) with open tracking capabilities. It includes a PHP script for the server side (tracking) and Python scripts for the client side (sending).

## Part 1: Apache Server Setup (Tracking)

This part sets up the "pixel" that tracks when emails are opened.

1.  **Upload the Script:**
    Upload `tracker.php` to your Apache server's public directory (e.g., `/var/www/html/`).

2.  **Permissions:**
    The script needs to write to a log file. You must create the file and give it write permissions for the web server user (usually `www-data`).
    Run these commands on your server terminal:

    ```bash
    cd /var/www/html
    touch opens.log
    chmod 666 opens.log
    ```

3.  **Test It:**

      * Visit `http://your-server-ip/tracker.php?user=test` in your browser.
      * You should see a 1x1 blank pixel (essentially a blank page).
      * Check the log on the server: `cat /var/www/html/opens.log`. You should see the entry.

## Part 2: Python Sender Setup (Local Computer)

*You must do this part on your local computer first to generate the authentication token.*

1.  **Create a Virtual Environment (Recommended):**
    It is best practice to run this in an isolated environment.

    ```bash
    # Create the venv
    python3 -m venv venv

    # Activate it (Mac/Linux)
    source venv/bin/activate

    # Activate it (Windows)
    # venv\Scripts\activate
    ```

2.  **Install Libraries:**
    With the venv activated:

    ```bash
    pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
    ```

3.  **Enable APIs in Google Cloud:**

      * Go to [Google Cloud Console](https://console.cloud.google.com/).
      * Create a project (or select one).
      * Enable **Gmail API**.
      * Enable **Google Sheets API**.

4.  **Configure OAuth Consent Screen (Crucial):**

      * Go to **APIs & Services** \> **OAuth consent screen**.
      * Select **External** (unless you are a G Suite admin) and click Create.
      * Fill in the App Name (e.g., "Python Sender") and User Support Email.
      * **Test Users (Fix for Error 403):**
          * Scroll to the **Test users** section (or click "Audience" in the menu).
          * Click **+ ADD USERS**.
          * **Enter your own email address** (the one you will use to send emails).
          * Click **Save**. *Without this, you will get an Access Denied error.*

5.  **Get Credentials:**

      * Go to **Credentials** \> **Create Credentials** \> **OAuth client ID**.
      * Application Type: **Desktop App** (Do *not* select Web Application).
      * Click Create.
      * Download the JSON file.
      * Rename it to `credentials.json`.
      * Place it in the same folder as your Python scripts.

6.  **Configure the Script:**

      * Open `gmail_core.py`.
      * Find `TRACKING_URL_BASE`.
      * Update it to your actual server URL (e.g., `http://your-server-ip/tracker.php`).

7.  **Run Once to Authenticate:**

      * **Important:** If you already have a `token.json` file from a previous attempt that didn't include Sheets permissions, **delete it**.
      * Run the sender script to trigger the login flow:

    <!-- end list -->

    ```bash
    python gmail_sender.py
    ```

      * A browser will open. Log in with your Google account.
      * **"Unverified App" Warning:** Since your app is in testing mode, Google will show a warning.
          * Click **Advanced** (or "Continue").
          * Click **"Go to [App Name] (unsafe)"**.
      * Allow the permissions. This generates a new file named `token.json`.

## Part 3: Deploying to Your Server

Since servers usually don't have web browsers, you transfer the credentials you just created.

1.  **Prepare Server Environment:**
    SSH into your server and set up the environment.

    ```bash
    sudo apt-get update
    sudo apt-get install python3 python3-pip python3-venv

    # Create folder for your scripts
    mkdir email-sender
    cd email-sender

    # Create and activate venv
    python3 -m venv venv
    source venv/bin/activate

    # Install libraries inside venv
    pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
    ```

2.  **Upload Files:**
    Upload **all 6 files** to the server folder (e.g., `email-sender`):

      * `gmail_core.py` (Core logic & Auth)
      * `gmail_sender.py` (CSV Bulk sender)
      * `sheet_sender.py` (Google Sheets sender)
      * `send_one.py` (Single sender for forms)
      * `credentials.json`
      * `token.json` (The file generated in Part 2)

3.  **Permissions:**
    If using a PHP form handler to trigger these scripts, the web server user (`www-data`) needs read access.

    ```bash
    chmod 644 gmail_core.py token.json credentials.json
    chmod 755 send_one.py sheet_sender.py gmail_sender.py
    ```

    **Important Note for PHP Integration:**
    When calling these scripts from PHP `shell_exec`, you must use the Python executable **inside the virtual environment**, not the system python.

    *Example PHP Command:*

    ```php
    $command = "/path/to/email-sender/venv/bin/python3 /path/to/email-sender/send_one.py ...";
    ```

## Part 4: Usage

### A. Bulk Sending from CSV

1.  Create a file named `recipients.csv` (see Data Format below).
2.  Run:
    ```bash
    # Ensure venv is active
    python gmail_sender.py
    ```
    *Note: The script respects the `DAILY_LIMIT` set in `gmail_sender.py`. Run it daily to process large lists in chunks.*

### B. Sending from Google Sheets

1.  Get your **Sheet ID** from the URL: `docs.google.com/spreadsheets/d/THIS_IS_THE_ID/edit`.
2.  Run:
    ```bash
    # Option 1: Auto-detect data in the first sheet
    python sheet_sender.py <SHEET_ID>

    # Option 2: Specify a specific sheet name
    python sheet_sender.py <SHEET_ID> "Sheet Name"
    ```

### C. Single Email (Programmatic Trigger)

Use this for website forms or system triggers.

```bash
python send_one.py recipient@example.com "Recipient Name"
```

## Advanced Data Format

You can use these column headers in your CSV or Google Sheet. Headers are **case-insensitive**.

| Header | Description |
| :--- | :--- |
| **Email** | **Required**. The primary recipient address. (Can also use "To"). |
| **CC** | Optional. CC recipient(s). |
| **BCC** | Optional. BCC recipient(s). |
| **Subject** | Optional. Overrides the default subject. Supports merge tags `{{ name }}`. |
| **Body** | Optional. Overrides the default HTML body. Supports merge tags. |
| **Attachment...** | Any column starting with `attachment` is treated as a file path. <br> *Examples:* `Attachment1`, `attachment_pdf`, `Attachment-A`. |
| **Name** | Custom variable for merge tags. |
| **Role** | Custom variable for merge tags. |

### Mail Merge Example

**Template (in Body column or script):**

> "Hi {{ Name }}, please review the attached {{ Document\_Type }}."

**Data Row:**

> Name: Alice | Document\_Type: Invoice | Attachment1: /var/www/files/inv\_101.pdf

**Result:**

> "Hi Alice, please review the attached Invoice." (With PDF attached)