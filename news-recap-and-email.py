import os
import sys
import smtplib
import requests
import time
import openai
import re      # Keep re for finding the JSON
import json    # --- NEW IMPORT for parsing JSON

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

# NOTE: We are removing the 'beautifulsoup4' dependency
# as the new method will not require web scraping.

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
    as a JSON object.
    
    Returns the raw text response which should contain the JSON.
    """
    global gemini_client
    if not gemini_client:
        print("Error: Gemini client not initialized.", file=sys.stderr)
        return None

    print("Attempting to fetch Google News headlines and summaries via Gemini...")
    try:
        grounding_tool = types.Tool(
            google_search=types.GoogleSearch()
        )
        generation_config = types.GenerateContentConfig(
            tools=[grounding_tool]
        )

        # --- UPDATED PROMPT ---
        # Ask for title, summary, and url, formatted as JSON.
        prompt = """
        Act as a news aggregation assistant.
        Please find the top 5 most recent, major news headlines from Google News.
        
        For each headline, provide:
        1. The headline title
        2. A concise 1-2 sentence summary of the article's content.
        3. The direct URL link to the article.
        
        Format the output as a single, valid JSON array of objects.
        Each object must have a "title", "summary", and "url" key.
        
        Do NOT include any text before or after the JSON array (e.g., no "Here is the JSON:").
        Your entire response should be only the JSON array.
        
        Example:
        [
          {
            "title": "Example Headline 1",
            "summary": "This is a one-sentence summary of what happened in the first article.",
            "url": "https://example.com/article1"
          },
          {
            "title": "Example Headline 2",
            "summary": "This is a summary of the second article, explaining the key point.",
            "url": "https://example.com/article2"
          }
        ]
        """
        # --- END UPDATED PROMPT ---
        
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=generation_config
        )
        
        if response.text:
            print("Gemini headline fetch SUCCEEDED.")
            return response.text
        else:
            print("Gemini headline fetch FAILED: No text in response.", file=sys.stderr)
            return None
    except Exception as e:
        print(f"Gemini headline fetch FAILED: {e}", file=sys.stderr)
        return None

# --- UPDATED FUNCTION to parse JSON ---
def parse_headlines(gemini_output):
    """
    Parses the raw text output from Gemini to find and load the JSON data.
    Returns a list of dictionaries.
    """
    print("Parsing JSON from Gemini output...")
    try:
        # Find the JSON block. This regex finds the first '[' to the last ']'
        # This is robust against Gemini adding "Here's the JSON: \n [...] \n"
        match = re.search(r"\[.*\]", gemini_output, re.DOTALL)
        if not match:
            print("Error: No JSON array found in Gemini output.", file=sys.stderr)
            print("Raw output:", gemini_output, file=sys.stderr)
            return []
            
        json_string = match.group(0)
        
        # Parse the JSON string into a Python list
        headlines_list = json.loads(json_string)
        
        # Basic validation
        if not isinstance(headlines_list, list) or not headlines_list:
            print("Error: Parsed JSON is not a list or is empty.", file=sys.stderr)
            return []

        # Check for required keys in the first item
        if "title" not in headlines_list[0] or \
           "summary" not in headlines_list[0] or \
           "url" not in headlines_list[0]:
            print("Error: JSON objects are missing required keys (title, summary, url).", file=sys.stderr)
            return []

        return headlines_list

    except json.JSONDecodeError as e:
        print(f"Error: Failed to decode JSON from Gemini. {e}", file=sys.stderr)
        print("Raw output being parsed:", gemini_output, file=sys.stderr)
        return []
    except Exception as e:
        print(f"Error parsing headlines: {e}", file=sys.stderr)
        return []

# --- FUNCTION DELETED ---
# We no longer need fetch_article_text because Gemini provides the summary.

# --- UPDATED FUNCTION to use Gemini's summary ---
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
                {"role": "system", "content": "You are a news summarization assistant. You will be given a news headline and a summary from another AI. Your job is to rewrite that summary in your own words, maintaining a concise and strictly neutral, factual tone."},
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
        
        # --- UPDATED SCRIPT LOGIC ---
        raw_json_text = fetch_headlines_with_gemini()
        
        if raw_json_text:
            # headlines_list is now a list of dicts
            headlines_list = parse_headlines(raw_json_text)
            
            if headlines_list:
                print("\n--- Headlines & AI Summaries ---")
                
                # Loop through the list of dictionaries
                for article in headlines_list:
                    title = article.get('title', 'No Title Found')
                    url = article.get('url', 'No URL Found')
                    gemini_summary = article.get('summary', 'No Summary Found')

                    print(f"\n## {title}")
                    print(f"Link: {url}")
                    print(f"\nGemini Summary:\n{gemini_summary}")
                    
                    # Now, send Gemini's summary to OpenAI
                    openai_summary = get_openai_perspective(gemini_summary, title)
                    
                    if openai_summary:
                        print(f"\nOpenAI Summary:\n{openai_summary}")
                    else:
                        print("\nOpenAI Summary: Could not be generated.")
                        
                    print("-------------------------------------")
                    time.sleep(1) # Be respectful
            else:
                print("Could not parse headlines from Gemini output. Exiting.", file=sys.stderr)
        else:
            print("Could not fetch headlines from Gemini. Exiting.", file=sys.stderr)
        # --- END UPDATED SCRIPT LOGIC ---

    else:
        print("\nOne or more API checks failed. Please check your keys and network.", file=sys.stderr)
        sys.exit(1)
    
    print("\nScript finished.")

if __name__ == "__main__":
    main()