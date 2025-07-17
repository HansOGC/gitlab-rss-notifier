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

# Email Configuration (these will be loaded from GitHub Secrets/Variables as environment variables)
SENDER_EMAIL = os.environ.get('GMAIL_USERNAME')
SENDER_PASSWORD = os.environ.get('GMAIL_APP_PASSWORD')

# Get receiver emails from environment variable string
# This variable should be set in GitHub Variables (e.g., RECEIVER_EMAIL_ADDRESS: "email1@example.com; email2@example.com")
RECEIVER_EMAILS_STR = os.environ.get('RECEIVER_EMAIL_ADDRESS')

# Convert the semicolon-separated string into a list of email addresses
if RECEIVER_EMAILS_STR:
    RECEIVER_EMAILS = [email.strip() for email in RECEIVER_EMAILS_STR.split(';') if email.strip()]
else:
    RECEIVER_EMAILS = [] # Empty list if variable is not set or empty

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587 # For TLS

# File to store the last sent entry GUIDs (this file will be committed and updated by the workflow)
LAST_SENT_FILE = "last_sent_guids.json"

# --- Template Configuration ---
SECURITY_EMAIL_TEMPLATE = "security_email_template.html"
RELEASE_EMAIL_TEMPLATE = "release_email_template.html"

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

def load_email_template(template_file):
    """
    Loads an HTML email template from a file.
    """
    try:
        with open(template_file, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"Error: Email template file '{template_file}' not found.")
        return None

def send_email(subject, body):
    """
    Sends an email using Gmail's SMTP server.
    Returns True if successful, False otherwise.
    """
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        print("Email credentials (GMAIL_USERNAME or GMAIL_APP_PASSWORD) not set as environment variables.")
        print("Please ensure they are configured as GitHub Secrets.")
        return False
    # Check if there are any receiver emails configured
    if not RECEIVER_EMAILS:
        print("No RECEIVER_EMAIL_ADDRESSes configured. Skipping email send.")
        return False

    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    # Join the list of emails for the 'To' header
    msg['To'] = ", ".join(RECEIVER_EMAILS)
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html')) # Use 'html' for rich text

    try:
        print(f"Attempting to send email with subject: '{subject}' to {', '.join(RECEIVER_EMAILS)}")
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls() # Secure the connection with TLS
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        text = msg.as_string()
        # Pass the list of recipients to sendmail
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAILS, text)
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

    # Load templates once
    security_template = load_email_template(SECURITY_EMAIL_TEMPLATE)
    release_template = load_email_template(RELEASE_EMAIL_TEMPLATE)

    if not security_template or not release_template:
        print("Could not load one or more email templates. Exiting.")
        return

    # --- Process GitLab Security Releases Feed ---
    print("\n--- Checking GitLab Security Releases ---")
    latest_security_entry, new_security_guid = fetch_latest_entry_if_new(
        GITLAB_SECURITY_FEED, last_sent_data.get("security")
    )

    if latest_security_entry:
        subject = f"[GitLab Security] {latest_security_entry.title}"
        html_content = latest_security_entry.content[0].value if latest_security_entry.content else 'No detailed content available.'

        # Populate the template
        body = security_template.replace('{{TITLE}}', latest_security_entry.title) \
                                .replace('{{LINK}}', latest_security_entry.link) \
                                .replace('{{PUBLISHED_DATE}}', latest_security_entry.published) \
                                .replace('{{CONTENT}}', html_content)

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
        html_content = latest_release_entry.content[0].value if latest_release_entry.content else 'No detailed content available.'

        # Populate the template
        body = release_template.replace('{{TITLE}}', latest_release_entry.title) \
                               .replace('{{LINK}}', latest_release_entry.link) \
                               .replace('{{PUBLISHED_DATE}}', latest_release_entry.published) \
                               .replace('{{CONTENT}}', html_content)

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
