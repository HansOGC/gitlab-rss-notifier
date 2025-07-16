# rss_reader.py

import feedparser
import os
import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# --- Configuration ---
# RSS Feed URLs
GITLAB_SECURITY_FEED = "https://about.gitlab.com/security-releases.xml"
GITLAB_RELEASES_FEED = "https://about.gitlab.com/releases.xml"

# Email Configuration (these will be loaded from GitHub Secrets as environment variables)
SENDER_EMAIL = os.environ.get('GMAIL_USERNAME')
SENDER_PASSWORD = os.environ.get('GMAIL_APP_PASSWORD')
RECEIVER_EMAIL = os.environ.get('RECEIVER_EMAIL_ADDRESS')

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587 # For TLS

# File to store the last sent entry GUIDs (this file will be committed and updated)
LAST_SENT_FILE = "last_sent_guids.json"

# --- Common Email HTML Styles ---
# Basic inline styles for email client compatibility
# These styles are embedded directly into the HTML email for maximum compatibility.
EMAIL_STYLES = """
    <style>
        /* General body styles for readability */
        body { 
            font-family: Arial, sans-serif; 
            font-size: 14px; 
            line-height: 1.6; 
            color: #333; 
            margin: 0; 
            padding: 0; 
            background-color: #f4f4f4; 
        }
        /* Main container for the email content */
        .container { 
            max-width: 600px; 
            margin: 20px auto; 
            padding: 20px; 
            border: 1px solid #eee; 
            border-radius: 8px; /* Slightly more rounded corners */
            background-color: #fff; 
            box-shadow: 0 2px 5px rgba(0,0,0,0.1); /* Subtle shadow for depth */
        }
        /* Heading styles */
        h2 { 
            color: #0056b3; 
            font-size: 20px; 
            margin-top: 0; 
            margin-bottom: 15px; 
            border-bottom: 2px solid #0056b3; /* Underline for headings */
            padding-bottom: 5px;
        }
        /* Paragraph spacing */
        p { 
            margin-bottom: 10px; 
        }
        /* Link styles */
        a { 
            color: #007bff; 
            text-decoration: none; 
        }
        a:hover { 
            text-decoration: underline; 
        }
        /* Date specific styling */
        .date { 
            font-size: 12px; 
            color: #777; 
            margin-bottom: 15px;
            display: block; /* Ensures it takes its own line */
        }
        /* Content description area */
        .description-content { 
            margin-top: 20px; 
            padding: 15px; 
            background-color: #f9f9f9; 
            border: 1px solid #ddd; 
            border-radius: 4px; 
            line-height: 1.5; /* Improve readability of main content */
        }
        /* Footer styling */
        .footer { 
            font-size: 12px; 
            color: #555; 
            margin-top: 25px; 
            border-top: 1px solid #eee; 
            padding-top: 15px; 
            text-align: center; /* Center footer text */
        }
    </style>
"""

# --- Helper Functions ---
def get_last_sent_data():
    """
    Reads the last sent GUIDs from the JSON file.
    Returns a dictionary like {"security": "last_guid", "releases": "last_guid"}
    """
    if os.path.exists(LAST_SENT_FILE):
        with open(LAST_SENT_FILE, "r") as f:
            try:
                data = json.load(f)
                # Ensure keys exist, default to None if not
                return {
                    "security": data.get("security"),
                    "releases": data.get("releases")
                }
            except json.JSONDecodeError:
                print(f"Warning: Could not decode {LAST_SENT_FILE}. Starting fresh.")
                return {"security": None, "releases": None} # Handle empty or malformed JSON
    print(f"Info: {LAST_SENT_FILE} not found. Starting fresh.")
    return {"security": None, "releases": None}

def save_last_sent_data(data):
    """
    Saves the current GUIDs to the JSON file.
    """
    with open(LAST_SENT_FILE, "w") as f:
        json.dump(data, f, indent=4)
    print(f"Saved updated GUIDs to {LAST_SENT_FILE}.")

def fetch_latest_entry_if_new(feed_url, last_sent_guid_for_feed):
    """
    Fetches the RSS feed, finds the latest entry, and checks if it's new.
    Returns (latest_entry_object, current_guid) if new, otherwise (None, None).
    """
    try:
        feed = feedparser.parse(feed_url)
        if not feed.entries:
            print(f"No entries found in feed: {feed_url}")
            return None, None

        # Sort entries by published date to get the absolute latest
        # feedparser entry.published_parsed is a time.struct_time object
        sorted_entries = sorted(feed.entries, key=lambda entry: entry.published_parsed, reverse=True)

        latest_entry = sorted_entries[0]
        # Use 'guid' if available, otherwise fallback to 'link' as a unique identifier
        current_guid = latest_entry.get('guid', latest_entry.link)

        print(f"Checking feed: {feed_url}")
        print(f"  Latest entry GUID: {current_guid}")
        print(f"  Last sent GUID for this feed: {last_sent_guid_for_feed}")

        if current_guid != last_sent_guid_for_feed:
            print(f"New entry found for {feed_url}: '{latest_entry.title}'")
            return latest_entry, current_guid
        else:
            print(f"No new entry for {feed_url}. Already processed.")
            return None, None
    except Exception as e:
        print(f"Error fetching or parsing feed {feed_url}: {e}")
        return None, None

def send_email(subject, body):
    """
    Sends an email using Gmail's SMTP server.
    Returns True if successful, False otherwise.
    """
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        print("Email credentials (GMAIL_USERNAME or GMAIL_APP_PASSWORD) not set as environment variables.")
        print("Please ensure they are configured as GitHub Secrets.")
        return False

    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html')) # Use 'html' for rich text, 'plain' for simple text

    try:
        print(f"Attempting to send email with subject: '{subject}' to {RECEIVER_EMAIL}")
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls() # Secure the connection with TLS
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        text = msg.as_string()
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, text)
        server.quit()
        print(f"Email sent successfully: '{subject}'")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

# --- Main Logic ---
def main():
    print(f"Starting RSS Reader at {datetime.now().strftime('%Y-%m-%d %H:%M:%S HKT')}")

    last_sent_data = get_last_sent_data()
    updated_data = dict(last_sent_data) # Create a mutable copy to track changes

    new_emails_sent_count = 0

    # --- Process GitLab Security Releases Feed ---
    print("\n--- Checking GitLab Security Releases ---")
    latest_security_entry, new_security_guid = fetch_latest_entry_if_new(
        GITLAB_SECURITY_FEED, last_sent_data.get("security")
    )

    if latest_security_entry:
        subject = f"[GitLab Security] {latest_security_entry.title}"
        # *** IMPORTANT CHANGE HERE: Using latest_security_entry.content[0].value ***
        body = f"""
      <!DOCTYPE html>
      <html>
      <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <title>GitLab Security Release Notification</title>
          {EMAIL_STYLES}
      </head>
      <body>
          <div class="container">
              <h2>New GitLab Security Release:</h2>
              <p><strong><a href='{latest_security_entry.link}'>{latest_security_entry.title}</a></strong></p>
              <p class="date">Published: {latest_security_entry.published}</p>

              <div class="description-content">
                  {latest_security_entry.content[0].value if latest_security_entry.content else 'No detailed content available.'}
              </div>

              <p>Read more: <a href='{latest_security_entry.link}'>{latest_security_entry.link}</a></p>

              <p class="footer">This email was sent by your GitLab RSS Notifier via GitHub Actions.</p>
          </div>
      </body>
      </html>
        """
        if send_email(subject, body):
            updated_data["security"] = new_security_guid
            new_emails_sent_count += 1
    else:
        print("No new GitLab Security Release found.")


    # --- Process GitLab General Releases Feed ---
    print("\n--- Checking GitLab General Releases ---")
    latest_release_entry, new_release_guid = fetch_latest_entry_if_new(
        GITLAB_RELEASES_FEED, last_sent_data.get("releases")
    )

    if latest_release_entry:
        subject = f"[GitLab Release] {latest_release_entry.title}"
        # *** IMPORTANT CHANGE HERE: Using latest_release_entry.content[0].value ***
        body = f"""
      <!DOCTYPE html>
      <html>
      <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <title>GitLab General Release Notification</title>
          {EMAIL_STYLES}
      </head>
      <body>
          <div class="container">
              <h2>New GitLab Release:</h2>
              <p><strong><a href='{latest_release_entry.link}'>{latest_release_entry.title}</a></strong></p>
              <p class="date">Published: {latest_release_entry.published}</p>

              <div class="description-content">
                  {latest_release_entry.content[0].value if latest_release_entry.content else 'No detailed content available.'}
              </div>

              <p>Read more: <a href='{latest_release_entry.link}'>{latest_release_entry.link}</a></p>

              <p class="footer">This email was sent by your GitLab RSS Notifier via GitHub Actions.</p>
          </div>
      </body>
      </html>
        """
        if send_email(subject, body):
            updated_data["releases"] = new_release_guid
            new_emails_sent_count += 1
    else:
        print("No new GitLab General Release found.")

    # --- Save Updated GUIDs if Changes Occurred ---
    if updated_data != last_sent_data:
        save_last_sent_data(updated_data)
        print(f"\nSuccessfully processed and sent {new_emails_sent_count} new email(s).")
    else:
        print("\nNo new entries found across all feeds. No emails sent and no changes to save.")

    print(f"RSS Reader finished at {datetime.now().strftime('%Y-%m-%d %H:%M:%S HKT')}")

if __name__ == "__main__":
    main()
