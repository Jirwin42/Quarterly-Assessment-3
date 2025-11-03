Quarterly-Assessment-3
======================

Overview
--------

This project contains Python scripts designed to interact with the Google Gemini, OpenAI, and **NewsAPI** services. The main application (`news-recap-and-email.py`) fetches the top 4 current news headlines from NewsAPI, generates comparative summaries using both Gemini and OpenAI, and sends a consolidated HTML email report with embedded images. A utility script (`api-tests.py`) is also included to verify all API key setups and connectivity.

🚀 Features
-----------

-   **Reliable News Source:** Uses **NewsAPI.org** to get clean, structured JSON with stable article links and image URLs.

-   **Dual-AI Summaries:** Generates news summaries from both Google Gemini and OpenAI based on a common base summary for a true side-by-side comparison.

-   **Robust Image Embedding:** Downloads images and reliably embeds them in the email by checking the `Content-Type` header, not just the file extension.

-   **Formatted HTML Email:** Creates a clean, professional HTML email with formatted dates (e.g., "November 3rd, 2025"), clickable headlines, and embedded images.

-   **Secure Setup:** Uses a `.env` file to securely manage all API keys and email credentials.

-   **Pre-flight Check:** Includes a test script to validate all three API connections before running the main application.

* * * * *

📂 Scripts Included
-------------------

### 1\. `api-tests.py`

A simple utility script to test API keys and connectivity **before** running the main application.

**What it does:**

1.  Loads `OPENAI_API_KEY`, `GEMINI_API_KEY`, and `NEWS_API_KEY` from the `.env` file.

2.  Performs a basic "Hello" check against the OpenAI API (`gpt-3.5-turbo`).

3.  Performs a basic "Hello" check against the Google Gemini API (`gemini-2.5-pro`).

4.  Performs a basic headline fetch against **NewsAPI** to ensure the key is valid.

5.  Reports success or failure for each of the three services.

### 2\. `news-recap-and-email.py`

This is the main application. It runs a multi-step process to fetch, analyze, and email a news briefing.

**What it does:**

1.  **Step 1: Fetch News (NewsAPI)**

    -   Connects to **NewsAPI.org** and fetches the top 5 current headlines for the US.

    -   This provides a reliable JSON list of articles, each with a stable title, author, URL, base summary (description), and image URL.

2.  **Step 2: Get AI Perspectives (Gemini & OpenAI)**

    -   Loops through each article from NewsAPI.

    -   Sends the `base_summary` and `title` to the **Gemini API** for its rewritten summary.

    -   Sends the same `base_summary` and `title` to the **OpenAI API** for its rewritten summary.

3.  **Step 3: Send Email (smtplib)**

    -   Generates a formatted date string (e.g., "November 3rd, 2025").

    -   For each article, it attempts to download the provided image. It **reliably detects the image type** by reading the server's `Content-Type` header.

    -   Compiles all data (titles, links, summaries, and embedded images) into a clean **HTML body**.

    -   Connects to an SMTP server (like Gmail) using credentials from the `.env` file and sends the final report.

* * * * *

⚙️ Setup & Installation
-----------------------

### 1\. Install Dependencies

This project requires a few Python libraries. You can install them using pip:

Bash

```
pip install python-dotenv openai google-generativeai requests
```

### 2\. Create Environment File

You must create a file named `.env` in the same directory as the scripts. This file stores your secret keys and configuration.

Copy the example below into your `.env` file and fill in your own values.


```
# --- API Keys ---
OPENAI_API_KEY="sk-..."
GEMINI_API_KEY="AIza..."
NEWS_API_KEY="YOUR_API_KEY_FROM_NEWSAPI.ORG"

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
Checking NewsAPI...
NewsAPI check successful.
------------------------------

Success: All API checks passed.
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