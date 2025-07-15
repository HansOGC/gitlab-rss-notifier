import feedparser
import os
import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# RSS Feed URLs
GITLAB_SECURITY_FEED = "https://about.gitlab.com/security-releases.xml"
GITLAB_RELEASES_FEED = "https://about.gitlab.com/releases.xml"

# Email Configuration
SENDER_EMAIL = os.environ.get('GMAIL_USERNAME')
SENDER_PASSWORD = os.environ.get('GMAIL_APP_PASSWORD')
RECEIVER_EMAIL = SENDER_EMAIL # Set this to your preferred receiver email, can be different from sender

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587 # For TLS

# File to store the last sent entry GUIDs (this file will be committed and updated)
LAST_SENT_FILE = "last_sent_guids.json"

def get_last_sent_data():
    if os.path.exists(LAST_SENT_FILE):
        with open(LAST_SENT_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {"security": None, "releases": None} # Handle empty or malformed JSON
    return {"security": None, "releases": None}

def save_last_sent_data(data):
    with open(LAST_SENT_FILE, "w") as f:
        json.dump(data, f, indent=4)

def fetch_latest_entry_if_new(feed_url, last_sent_guid):
    try:
        feed = feedparser.parse(feed_url)
        if not feed.entries:
            print(f"No entries found in feed: {feed_url}")
            return None, None

        # Sort entries by published date to get the absolute latest
        # feedparser entry.published_parsed is a time.struct_time object
        sorted_entries = sorted(feed.entries, key=lambda entry: entry.published_parsed, reverse=True)

        latest_entry = sorted_entries[0]
        current_guid = latest_entry.get('guid', latest_entry.link) # Use guid or link as a unique identifier

        if current_guid != last_sent_guid:
            print(f"New entry found for {feed_url}: {latest_entry.title}")
            return latest_entry, current_guid
        else:
            print(f"No new entry for {feed_url}. Last sent GUID: {last_sent_guid}")
            return None, None
    except Exception as e:
        print(f"Error fetching or parsing feed {feed_url}: {e}")
        return None, None

def send_email(subject, body):
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html')) # Can be 'plain' or 'html'

    try:
        print(f"Attempting to send email: {subject}")
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls() # Secure the connection
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        text = msg.as_string()
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, text)
        server.quit()
        print(f"Email sent successfully: {subject}")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

def main():
    last_sent_data = get_last_sent_data()
    updated_data = dict(last_sent_data) # Create a mutable copy

    print(f"Current last sent data: {last_sent_data}")

    # Check GitLab Security Releases
    latest_security_entry, new_security_guid = fetch_latest_entry_if_new(
        GITLAB_SECURITY_FEED, last_sent_data.get("security")
    )

    if latest_security_entry:
        subject = f"[GitLab Security] {latest_security_entry.title}"
        body = f"""
        <html>
        <body>
            <p><strong>New GitLab Security Release:</strong></p>
            <p><a href='{latest_security_entry.link}'>{latest_security_entry.title}</a></p>
            <p>Published: {latest_security_entry.published}</p>
            <hr>
            <div>{latest_security_entry.summary}</div>
        </body>
        </html>
        """
        if send_email(subject, body):
            updated_data["security"] = new_security_guid

    # Check GitLab General Releases
    latest_release_entry, new_release_guid = fetch_latest_entry_if_new(
        GITLAB_RELEASES_FEED, last_sent_data.get("releases")
    )

    if latest_release_entry:
        subject = f"[GitLab Release] {latest_release_entry.title}"
        body = f"""
        <html>
        <body>
            <p><strong>New GitLab Release:</strong></p>
            <p><a href='{latest_release_entry.link}'>{latest_release_entry.title}</a></p>
            <p>Published: {latest_release_entry.published}</p>
            <hr>
            <div>{latest_release_entry.summary}</div>
        </body>
        </html>
        """
        if send_email(subject, body):
            updated_data["releases"] = new_release_guid

    if updated_data != last_sent_data:
        save_last_sent_data(updated_data)
        print("Updated last_sent_guids.json with new GUIDs.")
    else:
        print("No new GUIDs to save.")

if __name__ == "__main__":
    main()
