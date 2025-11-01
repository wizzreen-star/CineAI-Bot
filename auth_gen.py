# ===========================================================
# 🎥 YouTube OAuth Token Generator
# ===========================================================
# This script helps you create a "token.json" file
# that allows your bot or app to upload videos to YouTube.
#
# ✅ Before running this script:
# 1️⃣ Make sure you have a Google Cloud project.
# 2️⃣ Enable the "YouTube Data API v3".
# 3️⃣ Create OAuth 2.0 credentials (Desktop type).
# 4️⃣ Download or copy your client_secret JSON details below.
#
# After you run this, it will open a URL.
# Visit that URL, sign in, copy the code, and paste it back here.
# Then it will create a "token.json" file automatically.
# ===========================================================

from google_auth_oauthlib.flow import InstalledAppFlow
import os
import json

# ===========================================================
# STEP 1: Define the Google API permission scope
# ===========================================================
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

# ===========================================================
# STEP 2: Create the client secret JSON dynamically
# ===========================================================
# If you don’t have a downloaded file, this code will generate it.
# Replace "YOUR_CLIENT_SECRET_HERE" with your actual secret key
# from Google Cloud Console → Credentials → OAuth 2.0 Client IDs.
# ===========================================================

CLIENT_SECRET_FILENAME = "client_secret_aoef7tuiefejflhshulgc4thmot5h1ev.apps.googleusercontent.com.json"

CLIENT_SECRET_DATA = {
    "installed": {
        "client_id": "295897014801-aoef7tuiefejflhshulgc4thmot5h1ev.apps.googleusercontent.com",
        "project_id": "planar-spring-476816-c4",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_secret": "YOUR_CLIENT_SECRET_HERE",
        "redirect_uris": ["http://localhost"]
    }
}

# ===========================================================
# STEP 3: Save the client secret file (if not already there)
# ===========================================================
if not os.path.exists(CLIENT_SECRET_FILENAME):
    with open(CLIENT_SECRET_FILENAME, "w") as f:
        json.dump(CLIENT_SECRET_DATA, f, indent=2)
    print(f"📁 Created {CLIENT_SECRET_FILENAME}")
else:
    print(f"📁 {CLIENT_SECRET_FILENAME} already exists, skipping creation.")

# ===========================================================
# STEP 4: Run OAuth flow to generate token.json
# ===========================================================
try:
    # Load OAuth flow
    flow = InstalledAppFlow.from_client_secrets_file(
        CLIENT_SECRET_FILENAME,
        SCOPES
    )

    # Generate URL for authorization
    auth_url, _ = flow.authorization_url(prompt='consent')

    print("\n🔗 Go to this URL and authorize access:\n")
    print(auth_url)
    print("\nAfter you authorize, copy the code Google gives you and paste it below.\n")

    # Get authorization code
    code = input("👉 Paste the authorization code here: ")

    # Fetch token from Google
    flow.fetch_token(code=code)
    creds = flow.credentials

    # Save the credentials as token.json
    with open("token.json", "w") as token_file:
        token_file.write(creds.to_json())

    print("\n✅ token.json created successfully!")
    print("➡️  Upload this file to Render → Environment → Secret Files → token.json")

except Exception as e:
    print("❌ Something went wrong while generating token.json:")
    print(e)

# ===========================================================
# END OF FILE
# ===========================================================
