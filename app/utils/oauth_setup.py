"""One-time OAuth setup utility to get Yahoo access tokens.

Run this script once to authenticate with Yahoo and get your access/refresh tokens.
Then add the tokens to your .env file.

Usage:
    python -m app.utils.oauth_setup
"""
import os
import sys
from pathlib import Path
from yahoo_oauth import OAuth2
from dotenv import load_dotenv, set_key

# Load environment variables
load_dotenv()


def setup_oauth():
    """Run OAuth flow and save tokens."""
    print("🧇 Waffle Bowl - Yahoo OAuth Setup")
    print("=" * 50)

    # Check for required environment variables
    client_id = os.getenv('YAHOO_CLIENT_ID')
    client_secret = os.getenv('YAHOO_CLIENT_SECRET')

    if not client_id or not client_secret:
        print("❌ Error: YAHOO_CLIENT_ID and YAHOO_CLIENT_SECRET must be set in .env file")
        print("\nPlease:")
        print("1. Copy .env.example to .env")
        print("2. Add your Yahoo Developer app credentials")
        print("3. Run this script again")
        sys.exit(1)

    print(f"\n✓ Found Yahoo Client ID: {client_id[:10]}...")
    print(f"✓ Found Yahoo Client Secret: {client_secret[:10]}...")

    # Create yahoo-oauth credentials file
    creds_file = Path.home() / '.yf_token_store' / 'private.json'
    creds_file.parent.mkdir(exist_ok=True)

    # Write credentials for yahoo-oauth
    import json
    creds = {
        "consumer_key": client_id,
        "consumer_secret": client_secret
    }

    with open(creds_file, 'w') as f:
        json.dump(creds, f)

    print("\n📝 Credentials file created at:", creds_file)
    print("\n🌐 Starting OAuth flow...")
    print("=" * 50)
    print("A browser window will open for you to authorize the app.")
    print("After authorizing, you'll be redirected. Copy the verification code.")
    print("=" * 50)

    try:
        # Initialize OAuth2 - this will open browser
        oauth = OAuth2(None, None, from_file=str(creds_file))

        # If we get here, OAuth was successful
        print("\n✅ OAuth successful!")
        print("\n🔑 Your tokens:")
        print("=" * 50)

        # Read the token file (OAuth2 updates it with tokens)
        with open(creds_file, 'r') as f:
            token_data = json.load(f)

        access_token = token_data.get('access_token')
        refresh_token = token_data.get('refresh_token')

        print(f"Access Token:  {access_token}")
        print(f"Refresh Token: {refresh_token}")
        print("=" * 50)

        # Update .env file
        env_path = Path('.env')
        if env_path.exists():
            print("\n💾 Updating .env file...")
            set_key(env_path, 'YAHOO_ACCESS_TOKEN', access_token)
            set_key(env_path, 'YAHOO_REFRESH_TOKEN', refresh_token)
            print("✅ .env file updated!")
        else:
            print("\n⚠️  .env file not found. Please manually add these to your .env file:")
            print(f"\nYAHOO_ACCESS_TOKEN={access_token}")
            print(f"YAHOO_REFRESH_TOKEN={refresh_token}")

        print("\n✨ Setup complete! You can now run the app:")
        print("   flask run --cert=adhoc")
        print("\n💡 These tokens will auto-refresh, so you shouldn't need to run this again.")

    except Exception as e:
        print(f"\n❌ OAuth failed: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure your YAHOO_REDIRECT_URI in .env matches Yahoo Developer settings")
        print("2. Check that you're running with HTTPS (use ngrok or flask run --cert=adhoc)")
        print("3. Verify your Client ID and Secret are correct")
        sys.exit(1)


if __name__ == '__main__':
    setup_oauth()
