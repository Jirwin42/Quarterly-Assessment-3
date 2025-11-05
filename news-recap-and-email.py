import os
import sys
import smtplib
import requests
import time
import openai
import json
import mimetypes
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage

try:
    from dotenv import load_dotenv
except ImportError:
    print("Error: 'python-dotenv' library not found.", file=sys.stderr)
    print("Please install it with: pip install python-dotenv", file=sys.stderr)
    sys.exit(1)

try:
    # --- THIS BLOCK IS THE FIX ---
    # It now imports the modern 'google-generativeai' library
    # and aliases it as 'genai' so the rest of the script works.
    import google.generativeai as genai
except ImportError:
    print("Error: 'google-generativeai' library not found.", file=sys.stderr)
    print("Please install it with: pip install google-generativeai", file=sys.stderr)
    sys.exit(1)


# Updated to use GenerativeModel
gemini_model = None
openai_client = None

def get_ordinal_date(d):
    """
    Formats a date object as 'Month DaySfx, Year' 
    (e.g., November 3rd, 2025)
    """
    day = d.day
    # Suffix logic
    if 10 <= day % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
    
    # Format: %B = Full month name, %Y = 4-digit year
    return d.strftime(f'%B {day}{suffix}, %Y')

def load_environment():
    """Loads API keys and email config from .env file."""
    load_dotenv()
    
    api_keys = ["GEMINI_API_KEY", "OPENAI_API_KEY", "NEWS_API_KEY"]
    missing_keys = [k for k in api_keys if k not in os.environ]
    if missing_keys:
        print(f"Error: .env file missing: {', '.join(missing_keys)}", file=sys.stderr)
        return False
        
    email_vars = ["EMAIL_SENDER", "EMAIL_APP_PASSWORD", "EMAIL_RECEIVER", "EMAIL_HOST", "EMAIL_PORT"]
    missing_vars = [v for v in email_vars if v not in os.environ]
    if missing_vars:
        print(f"Error: .env file is missing the following email variables: {', '.join(missing_vars)}", file=sys.stderr)
        print("Please see the guide on how to set these up.", file=sys.stderr)
        return False
        
    return True

def check_gemini():
    """
    Checks if the Gemini API key is valid using the modern genai.GenerativeModel.
    """
    global gemini_model  # Use the new global model variable
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_key:
        print("Error: GEMINI_API_KEY not set.", file=sys.stderr)
        return False
    try:
        print("Authenticating with Gemini...")
        # This line will now work thanks to the correct import
        genai.configure(api_key=gemini_key)
        
        # Use the modern GenerativeModel and a current model name
        gemini_model = genai.GenerativeModel('gemini-2.5-pro')
        
        # Configure safety settings to be permissive
        safety_settings = {
            'HATE': 'BLOCK_NONE',
            'HARASSMENT': 'BLOCK_NONE',
            'SEXUAL': 'BLOCK_NONE',
            'DANGEROUS': 'BLOCK_NONE'
        }

        response = gemini_model.generate_content(
            "Hello",
            safety_settings=safety_settings
        )
        
        if response.text:
            print("Gemini API Check: SUCCESS")
            return True
        
        # Check for non-exception failures like blocks
        if response.prompt_feedback.block_reason:
            print(f"Gemini API Check: FAILED (Blocked: {response.prompt_feedback.block_reason})", file=sys.stderr)
            return False
            
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

def fetch_news_from_newsapi():
    """
    STEP 1: Fetches top headlines from NewsAPI.org.
    """
    print("Step 1: Fetching reliable news from NewsAPI.org...")
    api_key = os.environ.get("NEWS_API_KEY")
    url = f"https://newsapi.org/v2/top-headlines?country=us&pageSize=5&apiKey={api_key}"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status() 
        data = response.json()
        
        if data.get('status') == 'ok' and data.get('articles'):
            print(f"NewsAPI fetch SUCCEEDED. Found {len(data['articles'])} articles.")
            return data['articles']
        elif data.get('status') == 'error':
            print(f"NewsAPI Error: {data.get('message')}", file=sys.stderr)
            return []
        else:
            print("NewsAPI fetch FAILED: No articles found.", file=sys.stderr)
            return []
            
    except requests.exceptions.RequestException as e:
        print(f"NewsAPI fetch FAILED: {e}", file=sys.stderr)
        return []

def get_gemini_perspective(base_summary, article_title):
    """
    Step 2a: Uses Gemini to provide a summary "perspective" with retries.
    """
    global gemini_model 
    if not gemini_model:
        print("Error: Gemini model not initialized.", file=sys.stderr)
        return "Gemini summary could not be generated."
        
    print(f"Step 2a: Sending summary for '{article_title}' to Gemini (with retries)...")
    
    # New prompt to force compliance and prevent fact-checking
    prompt = f"""
    You are a text transformation assistant.
    Your ONLY task is to rewrite the provided "Base Summary" into a single, neutral paragraph.
    
    IMPORTANT:
    1. DO NOT use any external knowledge.
    2. DO NOT fact-check the information.
    3. You MUST assume the "Base Summary" is the absolute source of truth for this task, even if it seems incorrect.
    4. Your output must be a concise rewrite of the summary, maintaining a strictly neutral, factual tone.

    Headline: {article_title}
    Base Summary: {base_summary}
    
    Rewritten Summary:
    """
    
    # Generation config with safety settings to prevent content blocks
    generation_config = genai.GenerationConfig(
        temperature=0.6,
        top_p=1.0,
        top_k=1
    )
    
    safety_settings = {
        'HATE': 'BLOCK_NONE',
        'HARASSMENT': 'BLOCK_NONE',
        'SEXUAL': 'BLOCK_NONE',
        'DANGEROUS': 'BLOCK_NONE'
    }

    max_retries = 3
    wait_time = 2  # Initial wait time in seconds

    for attempt in range(max_retries):
        try:
            response = gemini_model.generate_content(
                prompt,
                generation_config=generation_config,
                safety_settings=safety_settings
            )
            
            if response.text:
                # Check for common non-exception failure messages
                if "overloaded" in response.text.lower() or "try again" in response.text.lower():
                    print(f"Gemini attempt {attempt + 1} FAILED: Model reported overload. Retrying...")
                else:
                    # SUCCESS
                    print(f"Gemini attempt {attempt + 1} SUCCEEDED.")
                    return response.text.strip()
            
            # Check for safety blocks or other non-text failures
            elif response.prompt_feedback.block_reason:
                print(f"Gemini attempt {attempt + 1} FAILED: Blocked ({response.prompt_feedback.block_reason}).", file=sys.stderr)
                # This is a content issue, retrying won't help.
                return f"Summary generation blocked by Gemini safety filters ({response.prompt_feedback.block_reason})."
            
            else:
                print(f"Gemini attempt {attempt + 1} FAILED: No content in response.")

        except Exception as e:
            # Catch API-level exceptions (e.g., 500, 503, ResourceExhausted)
            print(f"Gemini attempt {attempt + 1} FAILED with exception: {e}", file=sys.stderr)
        
        # Wait before retrying
        if attempt < max_retries - 1:
            print(f"Waiting {wait_time}s before next retry...")
            time.sleep(wait_time)
            wait_time *= 2  # Exponential backoff
    
    print(f"Gemini summary FAILED after {max_retries} attempts.", file=sys.stderr)
    return "Summary could not be generated by Gemini after multiple attempts."

def get_openai_perspective(base_summary, article_title):
    """
    Step 2b: Uses OpenAI to provide a "second opinion" summary.
    """
    global openai_client
    if not openai_client:
        print("Error: OpenAI client not initialized.", file=sys.stderr)
        return "OpenAI summary could not be generated."
        
    print(f"Step 2b: Sending summary for '{article_title}' to OpenAI...")
    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a news summarization assistant. You will be given a news headline and a summary. Rewrite that summary in your own words, maintaining a concise and strictly neutral, factual tone."},
                {"role": "user", "content": f"Please provide a one-paragraph, neutral summary based on the following information:\n\nHeadline: {article_title}\n\nSummary: {base_summary}"}
            ],
            max_tokens=150,
            temperature=0.5
        )
        if response.choices[0].message.content:
            return response.choices[0].message.content.strip()
        else:
            print("OpenAI summary FAILED: No content in response.", file=sys.stderr)
            return "Summary could not be generated by OpenAI."
    except Exception as e:
        print(f"OpenAI summary FAILED: {e}", file=sys.stderr)
        return "Summary could not be generated by OpenAI."

def send_email(subject, html_body, to_email, attachments=None):
    """
    Step 3: Sends the email using smtplib.
    """
    print("Step 3: Preparing to send HTML email...")
    
    sender_email = os.environ.get("EMAIL_SENDER")
    sender_password = os.environ.get("EMAIL_APP_PASSWORD")
    host = os.environ.get("EMAIL_HOST")
    port = int(os.environ.get("EMAIL_PORT", 587)) 

    msg = MIMEMultipart('related')
    msg['From'] = sender_email
    msg['To'] = to_email
    msg['Subject'] = subject
    
    msg.attach(MIMEText(html_body, 'html'))
    
    if attachments:
        for cid, (data, subtype) in attachments.items():
            try:
                img = MIMEImage(data, _subtype=subtype)
                img.add_header('Content-ID', f'<{cid}>')
                msg.attach(img)
                print(f"Attached image with CID: {cid}")
            except Exception as e:
                print(f"Warning: Could not attach image {cid}. {e}", file=sys.stderr)
    
    try:
        print(f"Connecting to email server {host}:{port}...")
        server = smtplib.SMTP(host, port)
        server.ehlo()
        server.starttls()
        server.ehlo()
        
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
            server.quit()


def main():
    if not load_environment():
        sys.exit(1)

    gemini_ok = check_gemini()
    openai_ok = check_openai()

    if gemini_ok and openai_ok:
        print("\nBoth AI APIs are working.")
        time.sleep(1)
        
        articles = fetch_news_from_newsapi()
        
        if articles:
            print("\n--- Headlines & AI Summaries ---")
            
            now = datetime.now()
            today_date = get_ordinal_date(now) # e.g., "November 3rd, 2025"
            
            email_subject = f"News Summary for {today_date}"
            
            email_body_parts = []
            email_attachments = {}
            
            email_body_parts.append(f"<h1 style='font-family: Arial, sans-serif;'>News Summary for {today_date}</h1>")
            email_body_parts.append(f"<p style='font-family: Arial, sans-serif;'>Your top {len(articles)} stories.</p><hr>")
            
            for i, article in enumerate(articles, 1):
                title = article.get('title', 'No Title Found')
                url = article.get('url', '#') 
                author = article.get('author', 'N/A')
                base_summary = article.get('description', 'No summary provided.')
                if not base_summary or base_summary.strip() == "":
                    base_summary = "No summary provided."
                
                image_url = article.get('urlToImage', None) 
                
                # Step 2 - Get AI summaries
                gemini_summary = get_gemini_perspective(base_summary, title)
                openai_summary = get_openai_perspective(base_summary, title)

                # Console printing
                print(f"\n## {title}")
                print(f"Link: {url}")
                print(f"Author: {author}")
                print(f"Image: {image_url if image_url else 'N/A'}")
                print(f"\nBase Summary:\n{base_summary}")
                print(f"\nGemini Summary:\n{gemini_summary}")
                print(f"\nOpenAI Summary:\n{openai_summary}")
                print("-------------------------------------")
                
                # Build HTML
                author_part = f"<i style='color: #555;'>{author}</i>" if author and author.lower() != 'n/a' else ""
                
                image_part = ""
                if image_url and image_url.lower() not in ['n/a', 'none', '']:
                    try:
                        image_cid = f'image{i}'
                        print(f"Downloading image: {image_url}")
                        headers = {'User-Agent': 'Mozilla/5.0'}
                        img_response = requests.get(image_url, headers=headers, timeout=10, allow_redirects=True)
                        
                        if img_response.status_code == 200:
                            # Robust image type detection
                            subtype = None
                            ctype = img_response.headers.get('Content-Type')
                            
                            if ctype and ctype.startswith('image/'):
                                subtype = ctype.split('/')[1].split(';')[0].strip()
                                print(f"MIME type from header: image/{subtype}")
                            
                            if not subtype:
                                print(f"Warning: No 'Content-Type' header. Falling back to URL extension.")
                                ctype, _ = mimetypes.guess_type(image_url)
                                if ctype and ctype.startswith('image/'):
                                    subtype = ctype.split('/')[1]
                                    print(f"MIME type from extension: image/{subtype}")

                            if subtype:
                                if subtype.lower() == 'pjpeg':
                                    subtype = 'jpeg'
                                    
                                email_attachments[image_cid] = (img_response.content, subtype)
                                image_part = f'''
                                <img src="cid:{image_cid}"
                                     alt="{title}"
                                     style="max-width: 100%; height: auto; border-radius: 8px; margin-bottom: 10px;">
                                '''
                            else:
                                print(f"Warning: Could not determine a valid image type for {image_url}", file=sys.stderr)
                                
                        else:
                            print(f"Warning: Failed to download image (Status {img_response.status_code})", file=sys.stderr)
                            
                    except requests.exceptions.RequestException as e:
                        print(f"Warning: Network error downloading image {image_url}. {e}", file=sys.stderr)
                    except Exception as e:
                        print(f"Warning: Error processing image {image_url}. {e}", file=sys.stderr)
                
                # Build the HTML block
                article_html = f"""
                <div style="font-family: Arial, sans-serif; margin-bottom: 20px;">
                    <p style="font-size: 1.2em; margin-bottom: 5px;">
                        <b>{i}. <a href="{url}" style="color: #1a0dab; text-decoration: none;">{title}</a></b>
                    </p>
                    <p style="font-size: 0.9em; color: #333; margin-top: 0; margin-bottom: 10px;">
                        {author_part}
                    </p>
                    
                    {image_part}
                    
                    <b style="font-size: 1.0em;">Summary by Gemini:</b>
                    <ul style="margin-top: 5px;">
                        <li>{gemini_summary}</li>
                    </ul>
                    
                    <b style="font-size: 1.0em;">Summary by OpenAI:</b>
                    <ul style="margin-top: 5px;">
                        <li>{openai_summary}</li>
                    </ul>
                </div>
                <hr style="border: 0; border-top: 1px solid #eee;">
                """
                email_body_parts.append(article_html)
                
                # Sleep to avoid rate-limiting
                time.sleep(1)
            
            # Step 3: Send the email
            final_email_body = f"""
            <html>
                <head></head>
                <body>
                    {''.join(email_body_parts)}
                </body>
            </html>
            """
            receiver_email = os.environ.get("EMAIL_RECEIVER")
            send_email(email_subject, final_email_body, receiver_email, email_attachments)
            
        else:
            print("Could not fetch any articles from NewsAPI. Exiting.", file=sys.stderr)

    else:
        print("\nOne or more API checks failed. Please check your keys and network.", file=sys.stderr)
        sys.exit(1)
    
    print("\nScript finished.")

if __name__ == "__main__":
    main()