import os
import sys
import smtplib
import requests
import time
import openai
import json
from datetime import datetime  # --- NEW IMPORT for date
from email.mime.text import MIMEText  # --- NEW IMPORTS for email formatting
from email.mime.multipart import MIMEMultipart

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
    """Loads API keys and email config from .env file."""
    load_dotenv()
    
    # Check for API keys
    if "GEMINI_API_KEY" not in os.environ or "OPENAI_API_KEY" not in os.environ:
        print("Error: .env file missing GEMINI_API_KEY or OPENAI_API_KEY", file=sys.stderr)
        return False
        
    # --- NEW: Check for Email variables ---
    email_vars = ["EMAIL_SENDER", "EMAIL_APP_PASSWORD", "EMAIL_RECEIVER", "EMAIL_HOST", "EMAIL_PORT"]
    missing_vars = [v for v in email_vars if v not in os.environ]
    if missing_vars:
        print(f"Error: .env file is missing the following email variables: {', '.join(missing_vars)}", file=sys.stderr)
        print("Please see the guide on how to set these up.", file=sys.stderr)
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

# --- STEP 1: Get the news as messy text ---
def fetch_headlines_as_text_with_gemini():
    """
    STEP 1: Uses Gemini API + Google Search tool to fetch news.
    Output is a natural language string.
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
        generation_config = types.GenerateContentConfig(
            tools=[grounding_tool]
        )

        # --- UPDATED PROMPT: Added 'author' ---
        prompt = """
        Use the Google Search tool to find the 5 most recent, major news headlines.
        
        For each headline, provide:
        1. The headline title
        2. The author (if available, otherwise "N/A")
        3. A concise 1-2 sentence summary of the article's content.
        4. The direct URL link to the article.
        
        Format this as a simple, human-readable, numbered list.
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

# --- STEP 2: Convert text to clean JSON ---
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
        generation_config = types.GenerateContentConfig(
            response_mime_type="application/json"
        )
        
        # --- UPDATED PROMPT: Added 'author' to the schema ---
        prompt = f"""
        Please parse the following text and convert it into a valid JSON array.
        
        The JSON schema must be:
        [
          {{
            "title": "string (The headline of the article)",
            "summary": "string (The concise summary of the article)",
            "url": "string (The direct URL to the article)",
            "author": "string (The author's name, or 'N/A' if not found)"
          }}
        ]
        
        Your entire response must be *only* this JSON array.
        Ignore any conversational text or non-headline content.
        
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
    Step 3: Parses the raw JSON string output from Step 2.
    """
    print("Step 3: Parsing the guaranteed JSON output...")
    try:
        headlines_list = json.loads(gemini_json_output)
        
        if not isinstance(headlines_list, list) or not headlines_list:
            print("Error: Parsed JSON is not a list or is empty.", file=sys.stderr)
            return []

        # --- UPDATED VALIDATION: 'author' is optional, so we don't check for it ---
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
    Step 4: Uses OpenAI to provide a "second opinion" summary.
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

# --- NEW FUNCTION: Step 5 ---
def send_email(subject, body, to_email):
    """
    Step 5: Sends the email using smtplib.
    """
    print("Step 5: Preparing to send email...")
    
    # Get credentials from environment
    sender_email = os.environ.get("EMAIL_SENDER")
    sender_password = os.environ.get("EMAIL_APP_PASSWORD")
    host = os.environ.get("EMAIL_HOST")
    port = int(os.environ.get("EMAIL_PORT", 587)) # Default to 587

    # Create the email message
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = to_email
    msg['Subject'] = subject
    
    # Attach the body as plain text
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        print(f"Connecting to email server {host}:{port}...")
        # Connect to the SMTP server
        server = smtplib.SMTP(host, port)
        server.ehlo()  # Identify ourselves to the server
        server.starttls()  # Secure the connection
        server.ehlo()  # Re-identify ourselves over the secure connection
        
        print("Logging in to email server...")
        server.login(sender_email, sender_password)
        
        print(f"Sending email to {to_email}...")
        server.send_message(msg)
        
        print("Email sent successfully!")
        
    except smtplib.SMTPAuthenticationError:
        print("Email FAILED: Authentication error.", file=sys.stderr)
        print("Check your EMAIL_SENDER and EMAIL_APP_PASSWORD.", file=sys.stderr)
    except Exception as e:
        print(f"Email FAILED: An error occurred: {e}", file=sys.stderr)
    finally:
        if 'server' in locals():
            server.quit() # Always close the connection


def main():
    if not load_environment():
        sys.exit(1)

    gemini_ok = check_gemini()
    openai_ok = check_openai()

    if gemini_ok and openai_ok:
        print("\nBoth APIs are working.")
        time.sleep(1)
        
        raw_text = fetch_headlines_as_text_with_gemini()
        
        if raw_text:
            json_text = convert_text_to_json_with_gemini(raw_text)
            
            if json_text:
                headlines_list = parse_headlines(json_text)
                
                if headlines_list:
                    print("\n--- Headlines & AI Summaries ---")
                    
                    # --- NEW: Prepare email content ---
                    today_date = datetime.now().strftime("%m/%d/%Y")
                    email_subject = f"News Summary for {today_date}"
                    
                    # This list will hold the formatted string for each article
                    email_body_parts = []
                    email_body_parts.append(f"News Summary for {today_date}, top {len(headlines_list)} stories.\n")
                    
                    # Use enumerate to get a counter (1, 2, 3...)
                    for i, article in enumerate(headlines_list, 1):
                        title = article.get('title', 'No Title Found')
                        url = article.get('url', 'No URL Found')
                        gemini_summary = article.get('summary', 'No Summary Found')
                        
                        # Use .get() for 'author' as it's optional
                        author = article.get('author', 'N/A')
                        
                        # --- 4. Get OpenAI summary ---
                        openai_summary = get_openai_perspective(gemini_summary, title)
                        if not openai_summary:
                            openai_summary = "Summary could not be generated by OpenAI."

                        # --- Print to console ---
                        print(f"\n## {title}")
                        print(f"Link: {url}")
                        print(f"Author: {author}")
                        print(f"\nGemini Summary:\n{gemini_summary}")
                        print(f"\nOpenAI Summary:\n{openai_summary}")
                        print("-------------------------------------")
                        
                        # --- Build the email string for this article ---
                        
                        # Only include author if it's not "N/A"
                        author_part = f"{author} - " if author and author.lower() != 'n/a' else ""
                        
                        line_1 = f"{i}. {title} - {author_part}{url}"
                        
                        article_string = (
                            f"{line_1}\n\n"
                            f"Summary by Gemini:\n{gemini_summary}\n\n"
                            f"Summary by OpenAI:\n{openai_summary}"
                        )
                        email_body_parts.append(article_string)
                        
                        time.sleep(1)
                    
                    # --- 5. Send the email ---
                    
                    # Join all the parts with two newlines
                    final_email_body = "\n\n".join(email_body_parts)
                    receiver_email = os.environ.get("EMAIL_RECEIVER")
                    
                    send_email(email_subject, final_email_body, receiver_email)
                    
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