import os
import sys
import smtplib
import requests
import time
import openai
import json    # Keep json import
import re      # No longer needed for parsing, but not harmful

try:
    from dotenv import load_dotenv
except ImportError:
    print("Error: 'python-dotenv' library not found.", file=sys.stderr)
    print("Please install it with: pip install python-dotenv", file=sys.stderr)
    sys.exit(1)

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("Error: 'google-genai' library not found.", file=sys.stderr)
    print("Please install it with: pip install google-genai", file=sys.stderr)
    sys.exit(1)


gemini_client = None
openai_client = None

def load_environment():
    """Loads API keys from .env file."""
    load_dotenv()
    if "GEMINI_API_KEY" not in os.environ or "OPENAI_API_KEY" not in os.environ:
        print("Error: .env file missing GEMINI_API_KEY or OPENAI_API_KEY", file=sys.stderr)
        return False
    return True

def check_gemini():
    """Checks if the Gemini API key is valid."""
    global gemini_client
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_key:
        print("Error: GEMINI_API_KEY not set.", file=sys.stderr)
        return False
    try:
        print("Authenticating with Gemini...")
        gemini_client = genai.Client(api_key=gemini_key)
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents="Hello"
        )
        if response.text:
            print("Gemini API Check: SUCCESS")
            return True
        print("Gemini API Check: FAILED (No response text)", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Gemini API Check FAILED: {e}", file=sys.stderr)
        return False

def check_openai():
    """Checks if the OpenAI API key is valid."""
    global openai_client
    openai_key = os.environ.get("OPENAI_API_KEY")
    if not openai_key:
        print("Error: OPENAI_API_KEY not set.", file=sys.stderr)
        return False
    try:
        print("Authenticating with OpenAI...")
        openai_client = openai.OpenAI(api_key=openai_key)
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=5
        )
        if response.choices[0].message.content:
            print("OpenAI API Check: SUCCESS")
            return True
        print("OpenAI API Check: FAILED (No response text)", file=sys.stderr)
        return False
    except Exception as e:
        print(f"OpenAI API Check FAILED: {e}", file=sys.stderr)
        return False

def fetch_headlines_with_gemini():
    """
    Uses Gemini API to fetch 5 recent news headlines, summaries, and URLs
    as a JSON object, using JSON Mode for reliable output.
    """
    global gemini_client
    if not gemini_client:
        print("Error: Gemini client not initialized.", file=sys.stderr)
        return None

    print("Attempting to fetch Google News (in JSON Mode) via Gemini...")
    try:
        grounding_tool = types.Tool(
            google_search=types.GoogleSearch()
        )
        
        # --- UPDATED: Use JSON Mode ---
        generation_config = types.GenerateContentConfig(
            tools=[grounding_tool],
            response_mime_type="application/json" # This forces JSON output
        )
        # --- END UPDATED ---

        # --- UPDATED PROMPT for JSON Mode ---
        # We must explicitly describe the JSON schema for the model.
        prompt = """
        Use the Google Search tool to find 5 recent, major news headlines.
        
        Return your response as a valid JSON array of objects.
        
        The JSON schema must be:
        [
          {
            "title": "string (The headline of the article)",
            "summary": "string (A concise 1-2 sentence summary of the article)",
            "url": "string (The direct URL to the article)"
          }
        ]
        
        Your entire response must be *only* this JSON array.
        Do not add any text before or after the array.
        """
        # --- END UPDATED PROMPT ---
        
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=generation_config
        )
        
        if response.text:
            print("Gemini headline fetch SUCCEEDED (Raw JSON received).")
            return response.text
        else:
            print("Gemini headline fetch FAILED: No text in response.", file=sys.stderr)
            return None
    except Exception as e:
        # This will now catch errors if the model *can't* create JSON
        print(f"Gemini headline fetch FAILED with exception: {e}", file=sys.stderr)
        return None

# --- UPDATED FUNCTION to parse JSON ---
def parse_headlines(gemini_json_output):
    """
    Parses the raw JSON string output from Gemini.
    Returns a list of dictionaries.
    """
    print("Parsing JSON from Gemini output...")
    try:
        # With JSON mode, the output *is* the JSON string. No regex needed.
        headlines_list = json.loads(gemini_json_output)
        
        if not isinstance(headlines_list, list) or not headlines_list:
            print("Error: Parsed JSON is not a list or is empty.", file=sys.stderr)
            return []

        # Validate keys in the first item
        if "title" not in headlines_list[0] or \
           "summary" not in headlines_list[0] or \
           "url" not in headlines_list[0]:
            print("Error: JSON objects are missing required keys (title, summary, url).", file=sys.stderr)
            return []

        return headlines_list

    except json.JSONDecodeError as e:
        print(f"Error: Failed to decode JSON from Gemini. {e}", file=sys.stderr)
        print("Raw output (which should be JSON):", gemini_json_output, file=sys.stderr)
        return []
    except Exception as e:
        print(f"An unexpected error occurred during parsing: {e}", file=sys.stderr)
        return []

def get_openai_perspective(gemini_summary, article_title):
    """
    Uses the OpenAI API to provide a "second opinion" or alternative
    summary based on the summary from Gemini.
    """
    global openai_client
    if not openai_client:
        print("Error: OpenAI client not initialized.", file=sys.stderr)
        return None
        
    print(f"Sending summary for '{article_title}' to OpenAI for analysis...")
    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a news summarization assistant. You will be given a news headline and a summary. Rewrite that summary in your own words, maintaining a concise and strictly neutral, factual tone."},
                {"role": "user", "content": f"Please provide a one-paragraph, neutral summary based on the following information:\n\nHeadline: {article_title}\n\nSummary: {gemini_summary}"}
            ],
            max_tokens=150,
            temperature=0.5
        )
        
        if response.choices[0].message.content:
            return response.choices[0].message.content.strip()
        else:
            print("OpenAI summary FAILED: No content in response.", file=sys.stderr)
            return None
    except Exception as e:
        print(f"OpenAI summary FAILED: {e}", file=sys.stderr)
        return None

def main():
    if not load_environment():
        sys.exit(1)

    gemini_ok = check_gemini()
    openai_ok = check_openai()

    if gemini_ok and openai_ok:
        print("\nBoth APIs are working.")
        time.sleep(1)
        
        raw_json_text = fetch_headlines_with_gemini()
        
        if raw_json_text:
            headlines_list = parse_headlines(raw_json_text)
            
            if headlines_list:
                print("\n--- Headlines & AI Summaries ---")
                
                for article in headlines_list:
                    title = article.get('title', 'No Title Found')
                    url = article.get('url', 'No URL Found')
                    gemini_summary = article.get('summary', 'No Summary Found')

                    print(f"\n## {title}")
                    print(f"Link: {url}")
                    print(f"\nGemini Summary:\n{gemini_summary}")
                    
                    openai_summary = get_openai_perspective(gemini_summary, title)
                    
                    if openai_summary:
                        print(f"\nOpenAI Summary:\n{openai_summary}")
                    else:
                        print("\nOpenAI Summary: Could not be generated.")
                        
                    print("-------------------------------------")
                    time.sleep(1) 
            else:
                print("Could not parse headlines from Gemini output. Exiting.", file=sys.stderr)
        else:
            print("Could not fetch headlines from Gemini. Exiting.", file=sys.stderr)

    else:
        print("\nOne or more API checks failed. Please check your keys and network.", file=sys.stderr)
        sys.exit(1)
    
    print("\nScript finished.")

if __name__ == "__main__":
    main()