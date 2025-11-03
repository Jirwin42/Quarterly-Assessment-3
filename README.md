Quarterly-Assessment-3
======================

Overview
--------

This project contains Python scripts designed to interact with the Google Gemini and OpenAI APIs. The main application (`news-recap-and-email.py`) fetches current news headlines, generates summaries using both AI models, and sends a consolidated HTML email report. A utility script (`api-tests.py`) is also included to verify API key setup and connectivity.

🚀 Features
-----------

-   **Dual-AI Summaries:** Generates news summaries from both Google Gemini and OpenAI for comparison.

-   **News Fetching:** Uses Gemini's built-in Google Search tool to find recent, relevant news.

-   **Structured Data:** Leverages Gemini's JSON Mode to convert unstructured text into clean, parsable JSON.

-   **HTML Email Reports:** Creates a formatted HTML email with headlines, links, and both AI summaries.

-   **Secure Setup:** Uses a `.env` file to securely manage all API keys and email credentials.

* * * * *

📂 Scripts Included
-------------------

### 1\. `api-tests.py`

A simple utility script to test API keys and connectivity **before** running the main application.

**What it does:**

1.  Loads `OPENAI_API_KEY` and `GEMINI_API_KEY` from the `.env` file.

2.  Performs a basic "Hello" check against the OpenAI API (`gpt-3.5-turbo`).

3.  Performs a basic "Hello" check against the Google Gemini API (`gemini-2.5-flash`).

4.  Reports success or failure for each service.

### 2\. `news-recap-and-email.py`

This is the main application. It runs a multi-step process to fetch, analyze, and email a news briefing.

**What it does:**

1.  **Step 1: Fetch News (Gemini)**

    -   Uses the Gemini API and its **Google Search tool** to find the 5 most recent, major news headlines.

    -   The output is a single string of natural language text.

2.  **Step 2: Convert to JSON (Gemini)**

    -   Takes the raw text from Step 1 and sends it back to the Gemini API, but this time using **JSON Mode**.

    -   It prompts the model to parse the text into a structured JSON array, which is much easier and more reliable to work with in Python.

3.  **Step 3: Parse (Python)**

    -   Parses the guaranteed-valid JSON string from Step 2 into a Python list of dictionaries.

4.  **Step 4: Get Second Opinion (OpenAI)**

    -   Loops through each article in the list.

    -   For each article, it sends the headline and Gemini-generated summary to the **OpenAI API** (`gpt-3.5-turbo`).

    -   It asks OpenAI to provide its own neutral, one-paragraph summary of the event.

5.  **Step 5: Send Email (smtplib)**

    -   Compiles all the data (titles, links, Gemini summaries, OpenAI summaries) into a clean **HTML body**.

    -   Connects to an SMTP server (like Gmail) using credentials from the `.env` file.

    -   Sends the final HTML report to the specified recipient.

* * * * *

⚙️ Setup & Installation
-----------------------

### 1\. Install Dependencies

This project requires a few Python libraries. You can install them using pip:

Bash

```
pip install python-dotenv openai google-generativeai
```

### 2\. Create Environment File

You must create a file named `.env` in the same directory as the scripts. This file stores your secret keys and configuration.

Copy the example below into your `.env` file and fill in your own values.


```
# --- API Keys ---
OPENAI_API_KEY="sk-..."
GEMINI_API_KEY="AIza..."

# --- Email Configuration (Example for Gmail) ---
EMAIL_SENDER="your-email@gmail.com"
EMAIL_APP_PASSWORD="abcd efgh ijkl mnop"
EMAIL_RECEIVER="recipient-email@example.com"
EMAIL_HOST="smtp.gmail.com"
EMAIL_PORT=587
```

> **Important:** For `EMAIL_APP_PASSWORD`, do **not** use your regular email password. You must generate an "App Password" from your email provider's security settings (e.g., Google Account settings).

* * * * *

▶️ Usage
--------

### 1\. Test API Connectivity

Before running the main script, it's highly recommended to run the test script to ensure your API keys are correct.

Bash

```
python api-tests.py
```

**Expected Output:**

```
Starting API initialization checks...
------------------------------
Checking Google Gemini API...
Gemini API check successful.
------------------------------
Checking OpenAI API...
OpenAI API check successful.
------------------------------

Success: Both API checks passed.
Script is ready for news API logic.
Script finished.
```

### 2\. Run the Main Application

Once the tests pass, you can run the main script to fetch the news and send the email.

Bash

```
python news-recap-and-email.py
```

The script will print its progress to the console and, if successful, you will receive an HTML-formatted email at the `EMAIL_RECEIVER` address specified in your `.env` file.