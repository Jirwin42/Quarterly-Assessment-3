import os
import sys
import smtplib
import requests
import time
import openai
import json

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
            model='gemini-2.5-pro',
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

# --- STEP 1: Get the news as messy text ---
def fetch_headlines_as_text_with_gemini():
    """
    STEP 1: Uses Gemini API + Google Search tool to fetch news.
    The output is expected to be a messy, natural language string.
    """
    global gemini_client
    if not gemini_client:
        print("Error: Gemini client not initialized.", file=sys.stderr)
        return None

    print("Step 1: Fetching news as text using Google Search tool...")
    try:
        grounding_tool = types.Tool(
            google_search=types.GoogleSearch()
        )
        
        # We ARE using a tool, so we CANNOT use JSON mode.
        generation_config = types.GenerateContentConfig(
            tools=[grounding_tool]
        )

        prompt = """
        Use the Google Search tool to find the 5 most recent, major news headlines.
        
        For each headline, provide:
        1. The headline title
        2. A concise 1-2 sentence summary of the article's content.
        3. The direct URL link to the article.
        
        Format this as a simple, human-readable, numbered list.
        Do not worry about JSON. Just list the 5 findings.
        """
        
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=generation_config
        )
        
        if response.text:
            print("Gemini text fetch SUCCEEDED.")
            return response.text
        else:
            print("Gemini text fetch FAILED: No text in response.", file=sys.stderr)
            return None
    except Exception as e:
        print(f"Gemini text fetch FAILED: {e}", file=sys.stderr)
        return None

# --- NEW FUNCTION (STEP 2): Convert text to clean JSON ---
def convert_text_to_json_with_gemini(raw_text):
    """
    STEP 2: Uses Gemini API in JSON Mode to parse the messy text
    from Step 1 into a clean, guaranteed JSON output.
    """
    global gemini_client
    if not gemini_client:
        print("Error: Gemini client not initialized.", file=sys.stderr)
        return None

    print("Step 2: Converting raw text to JSON using JSON Mode...")
    try:
        # We are NOT using a tool, so we CAN use JSON mode.
        generation_config = types.GenerateContentConfig(
            response_mime_type="application/json"
        )
        
        # Prompt to define the schema and provide the messy text
        prompt = f"""
        Please parse the following text and convert it into a valid JSON array.
        
        The JSON schema must be:
        [
          {{
            "title": "string (The headline of the article)",
            "summary": "string (The concise summary of the article)",
            "url": "string (The direct URL to the article)"
          }}
        ]
        
        Your entire response must be *only* this JSON array.
        Ignore any conversational text, apologies, or non-headline content
        in the input text. Just extract the articles.
        
        Here is the text to parse:
        ---
        {raw_text}
        ---
        """
        
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=generation_config
        )
        
        if response.text:
            print("Gemini JSON conversion SUCCEEDED.")
            return response.text
        else:
            print("Gemini JSON conversion FAILED: No text in response.", file=sys.stderr)
            return None
    except Exception as e:
        print(f"Gemini JSON conversion FAILED: {e}", file=sys.stderr)
        return None

def parse_headlines(gemini_json_output):
    """
    Parses the raw JSON string output from Step 2.
    Returns a list of dictionaries.
    """
    print("Step 3: Parsing the guaranteed JSON output...")
    try:
        # The output from step 2 should be a perfect JSON string
        headlines_list = json.loads(gemini_json_output)
        
        if not isinstance(headlines_list, list) or not headlines_list:
            print("Error: Parsed JSON is not a list or is empty.", file=sys.stderr)
            return []

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
    Uses OpenAI to provide a "second opinion" summary.
    """
    global openai_client
    if not openai_client:
        print("Error: OpenAI client not initialized.", file=sys.stderr)
        return None
        
    print(f"Step 4: Sending summary for '{article_title}' to OpenAI...")
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
        
        # --- UPDATED 3-STEP LOGIC ---
        
        # 1. Get raw text
        raw_text = fetch_headlines_as_text_with_gemini()
        
        if raw_text:
            # 2. Convert raw text to clean JSON
            json_text = convert_text_to_json_with_gemini(raw_text)
            
            if json_text:
                # 3. Parse the clean JSON
                headlines_list = parse_headlines(json_text)
                
                if headlines_list:
                    print("\n--- Headlines & AI Summaries ---")
                    
                    for article in headlines_list:
                        title = article.get('title', 'No Title Found')
                        url = article.get('url', 'No URL Found')
                        gemini_summary = article.get('summary', 'No Summary Found')

                        print(f"\n## {title}")
                        print(f"Link: {url}")
                        print(f"\nGemini Summary:\n{gemini_summary}")
                        
                        # 4. Send to OpenAI
                        openai_summary = get_openai_perspective(gemini_summary, title)
                        
                        if openai_summary:
                            print(f"\nOpenAI Summary:\n{openai_summary}")
                        else:
                            print("\nOpenAI Summary: Could not be generated.")
                            
                        print("-------------------------------------")
                        time.sleep(1) 
                else:
                    print("Could not parse the JSON output from Gemini. Exiting.", file=sys.stderr)
            else:
                print("Could not convert Gemini's text output to JSON. Exiting.", file=sys.stderr)
        else:
            print("Could not fetch raw headlines from Gemini. Exiting.", file=sys.stderr)

    else:
        print("\nOne or more API checks failed. Please check your keys and network.", file=sys.stderr)
        sys.exit(1)
    
    print("\nScript finished.")

if __name__ == "__main__":
    main()