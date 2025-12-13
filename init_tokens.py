"""Initialize Yahoo OAuth tokens from environment variables."""
import os
import json
import time
from pathlib import Path

def init_tokens():
    """Create token files if they don't exist."""
    token_dir = Path.home() / '.yf_token_store'

    # Create directory if it doesn't exist
    token_dir.mkdir(parents=True, exist_ok=True)

    # Create private.json with consumer credentials (YFPY expects this)
    private_file = token_dir / 'private.json'
    if not private_file.exists():
        print("📝 Creating private.json with consumer credentials...")
        private_data = {
            'consumer_key': os.getenv('YAHOO_CLIENT_ID', ''),
            'consumer_secret': os.getenv('YAHOO_CLIENT_SECRET', '')
        }
        with open(private_file, 'w') as f:
            json.dump(private_data, f, indent=2)
        print(f"✅ Created {private_file}")

    # Create token.json with full token data (YFPY expects this filename!)
    token_file = token_dir / 'token.json'
    if not token_file.exists():
        print("📝 Initializing Yahoo OAuth tokens from environment variables...")

        token_data = {
            'access_token': os.getenv('YAHOO_ACCESS_TOKEN', ''),
            'consumer_key': os.getenv('YAHOO_CLIENT_ID', ''),
            'consumer_secret': os.getenv('YAHOO_CLIENT_SECRET', ''),
            'guid': None,
            'refresh_token': os.getenv('YAHOO_REFRESH_TOKEN', ''),
            'token_time': time.time(),
            'token_type': 'bearer'
        }

        with open(token_file, 'w') as f:
            json.dump(token_data, f, indent=4)

        print(f"✅ Token file created at {token_file}")
    else:
        print(f"ℹ️  Token file already exists at {token_file} - using existing tokens")

if __name__ == '__main__':
    init_tokens()
