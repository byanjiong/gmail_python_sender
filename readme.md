# **Gmail Tracking & Sending System \- Setup Guide**

This system allows you to send bulk or transactional emails via the Gmail API (or Google Sheets) with open tracking capabilities. It includes a PHP script for the server side (tracking) and Python scripts for the client side (sending).

## **Part 1: Apache Server Setup (Tracking)**

This part sets up the "pixel" that tracks when emails are opened.

1. Create Folder Structure:  
   On your server (e.g., inside /var/www/html/), you need 3 specific folders:  
   * ui/ (User Interface)  
   * log/ (For storing logs)  
   * tracker/ (For the PHP script)  
2. Upload the Script:  
   Upload tracker.php inside the tracker/ folder.  
3. Permissions (CRITICAL):  
   The script needs to write to the log folder (which is one level up from the tracker). You must give write permissions to the web server user (usually www-data) for the log directory.  
   Run these commands on your server terminal:  
   cd /var/www/html

   \# 1\. Create the structure  
   mkdir \-p ui log tracker

   \# 2\. Set ownership to the Apache user (usually www-data)  
   sudo chown \-R www-data:www-data log

   \# 3\. Grant write permissions  
   sudo chmod \-R 775 log

4. **Test It:**  
   * Visit http://your-server-ip/tracker/tracker.php?user=test in your browser.  
   * You should see a 1x1 blank pixel (essentially a blank page).  
   * Check the log on the server: cat /var/www/html/log/opens.log. You should see the entry.

## **Part 2: Python Sender Setup (Local Computer)**

*You must do this part on your local computer first to generate the authentication token.*

1. Create a Virtual Environment (Recommended):  
   It is best practice to run this in an isolated environment.  
   \# Create the venv  
   python3 \-m venv venv

   \# Activate it (Mac/Linux)  
   source venv/bin/activate

   \# Activate it (Windows)  
   \# venv\\Scripts\\activate

2. Install Libraries:  
   With the venv activated:  
   pip install \--upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib

3. **Enable APIs in Google Cloud:**  
   * Go to [Google Cloud Console](https://console.cloud.google.com/).  
   * Create a project (or select one).  
   * Enable **Gmail API**.  
   * Enable **Google Sheets API**.  
4. **Configure OAuth Consent Screen (Crucial):**  
   * Go to **APIs & Services** \> **OAuth consent screen**.  
   * Select **External** (unless you are a G Suite admin) and click Create.  
   * Fill in the App Name (e.g., "Python Sender") and User Support Email.  
   * **Test Users (Fix for Error 403):**  
     * Scroll to the **Test users** section (or click "Audience" in the menu).  
     * Click **\+ ADD USERS**.  
     * **Enter your own email address** (the one you will use to send emails).  
     * Click **Save**. *Without this, you will get an Access Denied error.*  
5. **Get Credentials:**  
   * Go to **Credentials** \> **Create Credentials** \> **OAuth client ID**.  
   * Application Type: **Desktop App** (Do *not* select Web Application).  
   * Click Create.  
   * Download the JSON file.  
   * Rename it to credentials.json.  
   * Place it in the same folder as your Python scripts.  
6. **Configure the Script:**  
   * Open gmail\_core.py.  
   * Find TRACKING\_URL\_BASE.  
   * Update it to your actual server URL (e.g., http://your-server-ip/tracker/tracker.php).  
7. **Run Once to Authenticate:**  
   * Run the dedicated authentication script to generate your token.

   python auth.py

   * A browser will open. Log in with your Google account.  
   * **"Unverified App" Warning:** Since your app is in testing mode, Google will show a warning.  
     * Click **Advanced** (or "Continue").  
     * Click **"Go to \[App Name\] (unsafe)"**.  
   * Allow the permissions. This generates a new file named token.json.

## **Part 3: Deploying to Your Server**

Since servers usually don't have web browsers, you transfer the credentials you just created.

1. Prepare Server Environment:  
   SSH into your server and set up the environment.  
   sudo apt-get update  
   sudo apt-get install python3 python3-pip python3-venv

   \# Create folder for your scripts  
   mkdir email-sender  
   cd email-sender

   \# Create and activate venv  
   python3 \-m venv venv  
   source venv/bin/activate

   \# Install libraries inside venv  
   pip install \--upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib

2. Upload Files:  
   Upload all 7 files to the server folder (e.g., email-sender):  
   * gmail\_core.py (Core logic & Auth)  
   * auth.py (Authentication helper)  
   * send\_csv.py (CSV Bulk sender)  
   * sheet\_sender.py (Google Sheets sender)  
   * send\_one.py (Single sender for forms)  
   * credentials.json  
   * token.json (The file generated in Part 2\)  
3. Permissions:  
   If using a PHP form handler to trigger these scripts, the web server user (www-data) needs read access.  
   chmod 644 gmail\_core.py token.json credentials.json  
   chmod 755 send\_one.py sheet\_sender.py send\_csv.py auth.py

   Important Note for PHP Integration:  
   When calling these scripts from PHP shell\_exec, you must use the Python executable inside the virtual environment, not the system python.  
   *Example PHP Command:*  
   $command \= "/path/to/email-sender/venv/bin/python3 /path/to/email-sender/send\_one.py ...";

## **Part 4: Usage**

### **A. Bulk Sending from CSV**

1. Create a file named recipients.csv (see Data Format below).  
2. Run:  
   \# Option 1: Default (looks for 'recipients.csv')  
   python send\_csv.py

   \# Option 2: Specify a custom CSV file  
   python send\_csv.py my\_list\_may.csv

   *Note:* The script respects the DAILY\_LIMIT set *in send\_csv.py. Run it daily to process large lists in chunks.*

### **B. Sending from Google Sheets**

1. Get your **Sheet ID** from the URL: docs.google.com/spreadsheets/d/THIS\_IS\_THE\_ID/edit.  
2. Run:  
   \# Option 1: Auto-detect data in the first sheet  
   python sheet\_sender.py \<SHEET\_ID\>

   \# Option 2: Specify a specific sheet name  
   python sheet\_sender.py \<SHEET\_ID\> "Sheet Name"

### **C. Single Email (Programmatic Trigger)**

Use this for website forms or system triggers.

python send\_one.py recipient@example.com "Recipient Name"

## **Advanced Data Format**

You can use these column headers in your CSV or Google Sheet. Headers are **case-insensitive**.

| Header | Description |
| :---- | :---- |
| **Email** | **Required**. The primary recipient address. (Can also use "To"). |
| **CC** | Optional. CC recipient(s). |
| **BCC** | Optional. BCC recipient(s). |
| **Subject** | Optional. Overrides the default subject. Supports merge tags {{ name }}. |
| **Body** | Optional. Overrides the default HTML body. Supports merge tags. |

