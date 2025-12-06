from pyngrok import ngrok, conf
import sys
import time
import re

def start_tunnel():
    try:
        # Attempt to open tunnel
        # If token is missing, this usually prints an error but might not raise immediately in some versions of pyngrok wrapper, 
        # but typically it raises PyngrokNgrokError.
        
        # We need to catch the specific error or generic one
        try:
            public_url = ngrok.connect(8000).public_url
        except Exception as e:
            error_msg = str(e)
            if "ERR_NGROK_4018" in error_msg or "authentication failed" in error_msg.lower():
                print("\n" + "!"*60)
                print("NGROK AUTHENTICATION REQUIRED")
                print("!"*60)
                print("Visit: https://dashboard.ngrok.com/get-started/your-authtoken")
                token = input("Please paste your Ngrok Authtoken here: ").strip()
                
                if token:
                    print("Setting token...")
                    ngrok.set_auth_token(token)
                    # Retry
                    public_url = ngrok.connect(8000).public_url
                else:
                    print("No token provided. Exiting.")
                    return
            else:
                raise e

        print("\n" + "="*60)
        print(f"NGROK TUNNEL STARTED SUCCESSFULLY")
        print("="*60)
        print(f"Public URL: {public_url}")
        print("-" * 60)
        print("FOR EXOTEL SETUP:")
        # Convert https -> wss
        wss_url = public_url.replace("https://", "wss://").replace("http://", "ws://")
        print(f"WebSocket URL: {wss_url}/stream/call1")
        print("="*60)
        
        # Keep process alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Shutting down tunnel...")
            ngrok.kill()

    except Exception as e:
        print(f"\nError starting ngrok: {e}")
        print("-" * 60)
        print("MANUAL FIX:")
        print("1. Get token from: https://dashboard.ngrok.com/get-started/your-authtoken")
        print("2. Run command: ngrok config add-authtoken <YOUR_TOKEN>")

if __name__ == "__main__":
    start_tunnel()
