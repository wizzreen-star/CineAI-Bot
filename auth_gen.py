from google_auth_oauthlib.flow import InstalledAppFlow
import os

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

flow = InstalledAppFlow.from_client_secrets_file(
    "client_secret_aoef7tuiefejflhshulgc4thmot5h1ev.apps.googleusercontent.com.json",
    SCOPES
)

# Generate a URL for authorization
auth_url, _ = flow.authorization_url(prompt='consent')

print("🔗 Go to this URL and authorize:")
print(auth_url)

code = input("👉 Paste the authorization code here: ")

flow.fetch_token(code=code)

creds = flow.credentials

with open("token.json", "w") as token_file:
    token_file.write(creds.to_json())

print("✅ token.json created successfully!")
