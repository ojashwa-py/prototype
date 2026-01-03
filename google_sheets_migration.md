Overview: Migrating from Local Excel to Google Sheets
This workflow outlines the necessary steps to switch your chatbot's database from a local Excel file to a Google Sheet.

Prerequisites:
1. Google Cloud Console Account
2. Enabled APIs (Google Sheets API, Google Drive API)
3. Service Account Credentials (JSON file)

Step 1: Get Google Cloud Credentials
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project or select an existing one.
3. Search for "Google Sheets API" and enable it.
4. Search for "Google Drive API" and enable it.
5. Go to "Credentials" > "Create Credentials" > "Service Account".
6. Give it a name and click "Create".
7. Click on the newly created Service Account > "Keys" tab > "Add Key" > "Create new key" > "JSON".
8. A file will download. Rename it to `credentials.json` and place it in your project folder (`f:\New folder\`).

Step 2: Create the Google Sheet
1. Create a new Google Sheet at [sheets.google.com](https://sheets.google.com).
2. Name it `iDecor Orders` (or similar).
3. In the header row (Row 1), add these exact column names:
   - Order ID
   - Customer Name
   - Product Name
   - Product Type
   - Size
   - Quantity
   - Order Date
   - address
   - Contact no.
   - another contact no.
   - Payment Verified
   - Confirmation Sent
4. **Cruciale "Share" button in the top right.
5. Open your `credentials.json` file, find the `"client_email"`, copy it, and paste it into the "Share" dialog of your Google Sheet. Give it "Editor" access.

Step 3: Update Requirements
You need to install `gspread` and `oauth2client`.
Command: `pip install gspread oauth2client`

Step 4: Update Code (`whatsapp_bot.py`)
I will handle this part for y:** Click thou. The code needs to be refactored to use the `gspread` library instead of `pandas`/`openpyxl`.

Key Changes in Code:
- Remove `pandas` and `openpyxl` dependencies for file I/O.
- Initialize `gspread` client using `credentials.json`.
- Update `save_order` to append rows to the sheet.
- Update `get_order_status` to search calls in the sheet.
- Update `check_for_notifications` to read/update the sheet cells.
