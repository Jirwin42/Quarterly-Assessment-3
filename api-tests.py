#basic api testing setup.

import os
import sys

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
# Load API keys from environment variables for security
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") # For Gemini

def check_api_keys():
    """Checks if the required API keys are set in the environment."""
    if not OPENAI_API_KEY:
        print("Error: OPENAI_API_KEY environment variable not set.", file=sys.stderr)
        return False
    if not GEMINI_API_KEY:
        print("Error: GEMINI_API_KEY environment variable not set.", file=sys.stderr)
        return False
    return True

def check_gemini():
    """
    Performs a simple initialization check on the Google Gemini API.
    """
    print("Checking Google Gemini API...")
    try:
        # Configure the Gemini client
        genai.configure(api_key=GEMINI_API_KEY)
        
        # Use a fast and cost-effective model for the check
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Send a simple test prompt
        response = model.generate_content("Hello")
        
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
    """
    Performs a simple initialization check on the OpenAI API.
    
    """
    print("Checking OpenAI API...")
    try:
        # The client automatically picks up the OPENAI_API_KEY env var
        client = OpenAI()
        
        # Send a simple test prompt
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Using a standard, fast model for the check
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello"}
            ]
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

def main():
    """
    Main function to run the API checks.
    """
    print("Starting API initialization checks...")
    
    if not check_api_keys():
        print("\nPlease set the missing API keys as environment variables.", file=sys.stderr)
        sys.exit(1)
        
    print("-" * 30)
    gemini_ok = check_gemini()
    print("-" * 30)
    openai_ok = check_openai()
    print("-" * 30)

    if gemini_ok and openai_ok:
        print("\nSuccess: Both API checks passed.")
        print("Script is ready for news API logic.")
        # Future logic to query news APIs will go here.
    else:
        print("\nFailure: One or more API checks failed.", file=sys.stderr)
        print("Please check your API keys, network connection, and account status.", file=sys.stderr)
        sys.exit(1)

    print("Script finished.")

if __name__ == "__main__":
    main()
