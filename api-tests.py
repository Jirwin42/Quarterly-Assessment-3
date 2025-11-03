#basic api testing setup.

import os
import sys
import requests # --- NEW: Added for NewsAPI check ---

try:
    from dotenv import load_dotenv
except ImportError:
    print("Error: 'python-dotenv' library not found. Please install it with 'pip install python-dotenv'", file=sys.stderr)
    sys.exit(1)

try:
    from openai import OpenAI
except ImportError:
    print("Error: 'openai' library not found. Please install it with 'pip install openai'", file=sys.stderr)
    sys.exit(1)

try:
    import google.generativeai as genai
except ImportError:
    print("Error: 'google-generativeai' library not found. Please install it with 'pip install google-generativeai'", file=sys.stderr)
    sys.exit(1)
    
load_dotenv()

# --- API Key Configuration ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY") # --- NEW ---

def check_api_keys():
    """Checks if the required API keys are set in the environment."""
    if not OPENAI_API_KEY:
        print("Error: OPENAI_API_KEY environment variable not set.", file=sys.stderr)
        return False
    if not GEMINI_API_KEY:
        print("Error: GEMINI_API_KEY environment variable not set.", file=sys.stderr)
        return False
    # --- NEW CHECK ---
    if not NEWS_API_KEY:
        print("Error: NEWS_API_KEY environment variable not set.", file=sys.stderr)
        return False
    return True

def check_gemini():
    """Performs a simple initialization check on the Google Gemini API."""
    print("Checking Google Gemini API...")
    try:
        # Using the Client method from your script
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model='gemini-2.5-pro', 
            contents="Hello"
        )
        
        if response.text and len(response.text) > 0:
            print("Gemini API check successful.")
            return True
        else:
            print("Gemini API check FAILED: Received an empty response.", file=sys.stderr)
            return False
            
    except Exception as e:
        print(f"Gemini API check FAILED: {e}", file=sys.stderr)
        return False

def check_openai():
    """Performs a simple initialization check on the OpenAI API."""
    print("Checking OpenAI API...")
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=5
        )
        
        if response.choices[0].message.content and len(response.choices[0].message.content) > 0:
            print("OpenAI API check successful.")
            return True
        else:
            print("OpenAI API check FAILED: Received an empty response.", file=sys.stderr)
            return False

    except Exception as e:
        print(f"OpenAI API check FAILED: {e}", file=sys.stderr)
        return False

# --- NEW FUNCTION ---
def check_newsapi():
    """Performs a simple check on the NewsAPI."""
    print("Checking NewsAPI...")
    try:
        # Make a simple request for 1 article
        url = f"https://newsapi.org/v2/top-headlines?country=us&pageSize=1&apiKey={NEWS_API_KEY}"
        response = requests.get(url, timeout=10)
        
        # Check for HTTP error
        response.raise_for_status() 
        
        data = response.json()
        
        # Check for API error
        if data.get('status') == 'ok':
            print("NewsAPI check successful.")
            return True
        else:
            print(f"NewsAPI check FAILED: {data.get('message')}", file=sys.stderr)
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"NewsAPI check FAILED: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"NewsAPI check FAILED: An unexpected error occurred: {e}", file=sys.stderr)
        return False

def main():
    """Main function to run the API checks."""
    print("Starting API initialization checks...")
    
    if not check_api_keys():
        print("\nPlease set the missing API keys as environment variables.", file=sys.stderr)
        sys.exit(1)
        
    print("-" * 30)
    gemini_ok = check_gemini()
    print("-" * 30)
    openai_ok = check_openai()
    print("-" * 30)
    # --- NEW CHECK ---
    newsapi_ok = check_newsapi()
    print("-" * 30)

    # --- UPDATED SUCCESS MESSAGE ---
    if gemini_ok and openai_ok and newsapi_ok:
        print("\nSuccess: All API checks passed.")
        print("Script is ready for news API logic.")
    else:
        print("\nFailure: One or more API checks failed.", file=sys.stderr)
        print("Please check your API keys, network connection, and account status.", file=sys.stderr)
        sys.exit(1)

    print("Script finished.")

if __name__ == "__main__":
    main()