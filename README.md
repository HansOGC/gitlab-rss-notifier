# GitLab RSS Notifier

-----

## 🚀 Overview

The GitLab RSS Notifier is an automated solution designed to keep you informed about the latest GitLab Security and General Releases. It periodically checks the official GitLab RSS feeds and, if new updates are found, sends an email notification to a configurable list of recipients.

This project leverages **GitHub Actions** for daily automation, ensuring you receive timely alerts without manual intervention.

## ✨ Features

  * **Automated RSS Feed Monitoring:** Regularly checks GitLab's Security and General Release RSS feeds.
  * **Email Notifications:** Sends rich HTML emails for new releases, including the title, link, published date, and full content.
  * **Prevent Duplicate Notifications:** Tracks previously sent entries to avoid sending repeated emails for the same release.
  * **Secure Credential Handling:** Utilizes GitHub Secrets and Variables for safe storage and access of sensitive information (email credentials, recipient lists).
  * **Clean Template Separation:** Email layouts are managed in external HTML template files, making them easy to customize.
  * **Daily Scheduling & Manual Trigger:** Runs automatically on a daily schedule and can be triggered manually for testing or immediate checks.

## 🛠️ How It Works

1.  **Scheduled Execution:** A GitHub Actions workflow is triggered daily (or manually via `workflow_dispatch`).
2.  **Repository Checkout:** The workflow checks out your project's code.
3.  **Python Environment Setup:** Sets up a Python environment and installs necessary dependencies (`feedparser`).
4.  **Feed Fetching & Comparison:** The `rss_reader.py` script:
      * Reads the `last_sent_guids.json` file to determine the last known entries for both GitLab Security and General Release feeds.
      * Fetches the latest entries from the configured RSS feeds.
      * Compares the fetched entries with the last sent GUIDs.
5.  **Email Generation & Sending:**
      * If a new entry is detected, it loads the appropriate HTML email template (`security_email_template.html` or `release_email_template.html`).
      * Populates the template with the new release's details (title, link, content, published date).
      * Sends an email via Gmail's SMTP server to all configured recipient addresses.
6.  **GUID Update & Commit:** After successfully sending an email for a new entry, the script updates the `last_sent_guids.json` file with the GUID of the newly processed entry. This file is then committed back to the repository by the GitHub Actions bot to persist the state for future runs.

## 🚀 Getting Started

Follow these steps to set up and deploy your GitLab RSS Notifier.

### Prerequisites

  * A GitHub account.
  * A Gmail account (or any email service that supports SMTP and app passwords/tokens).
      * **For Gmail:** You'll need to generate an **App Password** as Google's "less secure apps" option is being phased out. Go to your Google Account \> Security \> How you sign in to Google \> App passwords.

### 1\. Repository Setup

1.  **Fork this repository** (or create a new one and copy the files).
2.  **Clone your forked repository** to your local machine:
    ```bash
    git clone https://github.com/YOUR_USERNAME/gitlab-rss-notifier.git
    cd gitlab-rss-notifier
    ```

### 2\. File Structure

Ensure your project has the following file structure:

```
gitlab-rss-notifier/
├── .github/
│   └── workflows/
│       └── rss-notifier.yml  # GitHub Actions workflow definition
├── rss_reader.py             # Main Python script
├── security_email_template.html  # HTML template for security release emails
├── release_email_template.html   # HTML template for general release emails
└── .gitignore                # Specifies files to ignore in Git
└── last_sent_guids.json      # (Will be created/updated by the workflow) Tracks last sent entries
└── README.md                 # This file!
```

### 3\. Configure GitHub Secrets & Variables

For security reasons, your email credentials and recipient list should be stored as **GitHub Secrets** and **GitHub Variables**, not directly in the code.

1.  Go to your repository on GitHub.

2.  Navigate to **Settings** \> **Secrets and variables** \> **Actions**.

      * **Secrets (for sensitive data):**

          * Click "New repository secret".
          * **Name:** `GMAIL_USERNAME`
              * **Value:** Your Gmail address (e.g., `your.email@gmail.com`)
          * Click "New repository secret".
          * **Name:** `GMAIL_APP_PASSWORD`
              * **Value:** The App Password you generated for your Gmail account.
              * *(Note: If you use a different SMTP service, you might need different secret names and values based on its authentication method.)*

      * **Variables (for non-sensitive configuration that can change):**

          * Click "New repository variable".
          * **Name:** `RECEIVER_EMAIL_ADDRESS`
              * **Value:** A semicolon-separated string of recipient email addresses (e.g., `email1@example.com;email2@example.com;myteam@mycompany.com`).
              * **Important:** Ensure no spaces around the semicolons unless they are part of the email address.

### 4\. Install Dependencies (Local Development - Optional)

If you plan to run or test the script locally, it's recommended to use a **virtual environment**:

```bash
# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate  # On Windows: .\venv\Scripts\activate

# Install dependencies (feedparser is the main one)
pip install feedparser
```

### 5\. Manual Workflow Dispatch (First Run / Testing)

You can manually trigger the workflow to test your setup and ensure emails are sent correctly.

1.  Go to your repository on GitHub.
2.  Click on the **Actions** tab.
3.  In the left sidebar, click on "Daily GitLab RSS Notifier".
4.  On the right side, click the "Run workflow" dropdown.
5.  Click the green "Run workflow" button.

Monitor the workflow run under the "Actions" tab. If successful, you should receive an email with the latest GitLab releases. The `last_sent_guids.json` file will also be updated and committed to your repository.

## ⚙️ Configuration

All configuration is managed via GitHub Actions:

  * **RSS Feed URLs:** Defined directly in `rss_reader.py`. Modify `GITLAB_SECURITY_FEED` and `GITLAB_RELEASES_FEED` if GitLab changes its feed URLs, or if you wish to monitor other RSS feeds (ensure the parsing logic in `rss_reader.py` still extracts the `title`, `link`, `published`, and `content` fields correctly).
  * **Email Sender Credentials:** Configured via GitHub Secrets (`GMAIL_USERNAME`, `GMAIL_APP_PASSWORD`).
  * **Recipient Email Addresses:** Configured via GitHub Variable (`RECEIVER_EMAIL_ADDRESS`). Use semicolons (`;`) to separate multiple addresses.
  * **SMTP Server & Port:** Defined in `rss_reader.py` (`SMTP_SERVER`, `SMTP_PORT`). Default to Gmail's SMTP settings.
  * **Scheduling:** Defined in `.github/workflows/rss-notifier.yml` under the `cron:` schedule. The current setting `0 0 * * *` means it runs daily at 00:00 UTC (which is 08:00 AM HKT). Adjust the cron expression as needed for different timings.

## 🤝 Contributing

Contributions are welcome\! If you have ideas for improvements or new features, feel free to:

1.  Fork the repository.
2.  Create a new branch (`git checkout -b feature/your-feature`).
3.  Make your changes.
4.  Commit your changes (`git commit -m 'Add new feature'`).
5.  Push to the branch (`git push origin feature/your-feature`).
6.  Open a Pull Request.

## 📄 License

This project is open-sourced under the [MIT License](https://www.google.com/search?q=LICENSE).

## ✉️ Contact

For questions or feedback, please open an issue in this repository.

