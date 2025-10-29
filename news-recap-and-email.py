import os
import sys
import smtplib
import requests
import time
import openai  # Corrected import for openai

try:
    from dotenv import load_dotenv
except ImportError:
    print("Error: 'python-dotenv' library not found.", file=sys.stderr)
    print("Please install it with: pip install python-dotenv", file=sys.stderr)
    sys.exit(1)

try:
    # --- UPDATED IMPORTS ---
    # This is the new, correct import pattern for the unified SDK
    from google import genai
    from google.genai import types
    # --- END UPDATED IMPORTS ---
except ImportError:
    print("Error: 'google-genai' library not found.", file=sys.stderr)
    print("Please install it with: pip install google-genai", file=sys.stderr)
    sys.exit(1)

# --- NEW GLOBAL CLIENT ---
# We'll store the initialized client here to use in multiple functions
gemini_client = None
openai_client = None

def load_environment():
    """
    Loads API keys from .env file into environment variables.
    Returns True on success, False on failure.
    """
    load_dotenv()
    if "GEMINI_API_KEY" not in os.environ or "OPENAI_API_KEY" not in os.environ:
        print("Error: .env file not found or is missing GEMINI_API_KEY or OPENAI_API_KEY", file=sys.stderr)
        return False
    return True

def check_gemini():
    """
    Checks if the Gemini API key is valid using the new client model.
    """
    global gemini_client  # We are setting the global variable
    gemini_key = os.environ.get("GEMINI_API_KEY")
    
    if not gemini_key:
        print("Error: GEMINI_API_KEY not set.", file=sys.stderr)
        return False

    try:
        print("Authenticating with Gemini...")
        
        # --- NEW CLIENT INITIALIZATION ---
        gemini_client = genai.Client(api_key=gemini_key)
        
        # A simple "hello" test using the new client.models.generate_content
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents="Hello"
        )
        # --- END NEW CLIENT INITIALIZATION ---
        
        if response.text:
            print("Gemini API Check: SUCCESS")
            return True
        else:
            print("Gemini API Check: FAILED (No response text)", file=sys.stderr)
            return False
    except Exception as e:
        print(f"Gemini API Check FAILED: {e}", file=sys.stderr)
        return False

def check_openai():
    """
    Checks if the OpenAI API key is valid.
    """
    global openai_client
    openai_key = os.environ.get("OPENAI_API_KEY")
    
    if not openai_key:
        print("Error: OPENAI_API_KEY not set.", file=sys.stderr)
        return False

    try:
        print("Authenticating with OpenAI...")
        
        # --- CORRECTED OPENAI INITIALIZATION ---
        # The user's example was JavaScript, this is the Python equivalent
        openai_client = openai.OpenAI(api_key=openai_key)
        
        # A simple test using the chat completions endpoint
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo", # Using a standard, common model for the test
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=5
        )
        # --- END CORRECTED OPENAI INITIALIZATION ---

        if response.choices[0].message.content:
            print("OpenAI API Check: SUCCESS")
            return True
        else:
            print("OpenAI API Check: FAILED (No response text)", file=sys.stderr)
            return False
    except Exception as e:
        print(f"OpenAI API Check FAILED: {e}", file=sys.stderr)
        return False

def fetch_headlines_with_gemini():
    """
    Uses the Gemini API to fetch 5 recent news headlines.
    This function NOW EXPLICITLY enables the Google Search tool.
    """
    global gemini_client
    if not gemini_client:
        print("Error: Gemini client not initialized.", file=sys.stderr)
        return

    print("Attempting to fetch Google News headlines via Gemini...")
    try:
        # --- NEW CONFIGURATION ---
        # 1. Define the Google Search tool using the correct 'types' import
        grounding_tool = types.Tool(
            google_search=types.GoogleSearch()
        )
        
        # 2. Create a generation config that USES this tool
        generation_config = types.GenerateContentConfig(
            tools=[grounding_tool]
        )
        # --- END NEW CONFIGURATION ---

        # A specific prompt asking for a structured response
        prompt = """
        Act as a news aggregation assistant.
        Please find the top 5 most recent, major news headlines from Google News.
        
        For each headline, provide:
        1. The headline title
        2. The direct URL link to the article
        
        Format the output clearly, for example:
        1. [Headline Title] - [URL]
        2. [Headline Title] - [URL]
        ...and so on.
        """
        
        # --- UPDATED API CALL ---
        # Use the global client and pass the new 'config'
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=generation_config
        )
        # --- END UPDATED API CALL ---
        
        if response.text:
            print("\n--- Top 5 Google News Headlines ---")
            print(response.text)
            print("-------------------------------------\n")
        else:
            print("Gemini headline fetch FAILED: No text in response.", file=sys.stderr)
    except Exception as e:
        print(f"Gemini headline fetch FAILED: {e}", file=sys.stderr)

def main():
    if not load_environment():
        sys.exit(1)

    # Run API checks
    gemini_ok = check_gemini()
    openai_ok = check_openai()

    if gemini_ok and openai_ok:
        print("\nBoth APIs are working.")
        # Wait a second before the next request
        time.sleep(1)
        # Fetch headlines as requested
        fetch_headlines_with_gemini()
    else:
        print("\nOne or more API checks failed. Please check your keys and network.", file=sys.stderr)
        sys.exit(1)
    
    print("\nScript finished.")

if __name__ == "__main__":
    main()
