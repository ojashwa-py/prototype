# Deploying to Render

This project is ready to be deployed to Render as a Web Service.

## Prerequisites
1. You must have a **Render account**.
2. You must have your **Google Service Account Credentials** (the content of `credentials.json`).

## Steps

1. **Push your code to GitHub/GitLab**.
   - Ensure `app.py` is deleted (it was redundant).
   - Ensure `requirements.txt` is updated.

2. **Create a New Web Service on Render**:
   - Connect your repository.
   - **Name**: `idecor-chat` (or anything you like).
   - **Runtime**: `Python 3`.
   - **Build Command**: `pip install -r requirements.txt` (Default).
   - **Start Command**: `gunicorn -b 0.0.0.0:$PORT whatsapp_bot:app` (This is set in `Procfile` automatically, but important to know).

3. **Set Environment Variables**:
   - Scroll down to the **Environment Variables** section.
   - Add a new variable:
     - **Key**: `GOOGLE_CREDENTIALS`
     - **Value**: Paste the *entire content* of your `credentials.json` file here. 
       - Ensure you copy it exactly, including `{` and `}`.

4. **Deploy**:
   - Click "Create Web Service".
   - Watch the logs. It should say "Starting Flask connection for iDecor Chat..." (or similar from gunicorn workers).

## Troubleshooting
- If the bot replies "System Error: Database not connected", check your `GOOGLE_CREDENTIALS` variable.
- Ensure the Google Sheet is shared with the `client_email` found in your credentials.
