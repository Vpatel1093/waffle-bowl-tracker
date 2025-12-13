"""Initialize Yahoo OAuth tokens from environment variables."""
import os
import json
import time
from pathlib import Path

def init_tokens():
    """Create token file if it doesn't exist."""
    token_dir = Path.home() / '.yf_token_store'
    token_file = token_dir / 'oauth2.json'

    # Create directory if it doesn't exist
    token_dir.mkdir(parents=True, exist_ok=True)

    # Only create if file doesn't exist (don't overwrite refreshed tokens)
    if not token_file.exists():
        print("📝 Initializing Yahoo OAuth tokens from environment variables...")

        token_data = {
            'access_token': os.getenv('YAHOO_ACCESS_TOKEN', ''),
            'consumer_key': os.getenv('YAHOO_CLIENT_ID', ''),
            'consumer_secret': os.getenv('YAHOO_CLIENT_SECRET', ''),
            'refresh_token': os.getenv('YAHOO_REFRESH_TOKEN', ''),
            'token_time': time.time(),
            'token_type': 'bearer'
        }

        with open(token_file, 'w') as f:
            json.dump(token_data, f, indent=2)

        print(f"✅ Token file created at {token_file}")
    else:
        print(f"ℹ️  Token file already exists at {token_file} - using existing tokens")

if __name__ == '__main__':
    init_tokens()
