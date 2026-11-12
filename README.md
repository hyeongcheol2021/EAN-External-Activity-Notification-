# EAN-External-Activity-Notification-
# Kumoh National Institute of Technology – New Post Notifier

A notification bot that sends alerts to **Discord** whenever new posts are published on Kumoh National Institute of Technology's **extracurricular program platform (BISKIT)** or **university announcement boards (Academic Notices, Events, and General News)**.

GitHub Actions automatically checks for new posts every 20 minutes, even when your PC is turned off. No server or paid service is required.

> This is an unofficial personal project and is not affiliated with Kumoh National Institute of Technology.

## Features

- **BISKIT Extracurricular Programs**: Sends notifications with the program title and application period whenever a new program is posted.
- **Three Announcement Boards**: Monitors Academic Notices, Events, and General News. Only posts containing keywords such as **competition, contest, hackathon, or ideathon** in their titles are reported.
- **Duplicate Prevention**: Previously reported posts are not notified again. On the first run, existing posts are recorded without sending notifications.
- **Partial Failure Handling**: If one source fails to load, results from the other sources are still saved. Failed sources are displayed in the GitHub Actions logs.
- **Results Page (Optional)**: View the list of detected posts on a web page using GitHub Pages.

## Notification Examples

```text
🔔 New Extracurricular Program

[2026 Internship Experience Essay Contest]
Application Period: 10/08 ~ 10/15
```

```text
🔔 New Announcement · Campus Events

Recruitment for the 5th National Hackathon Competition
2026-11-11
https://www.kumoh.ac.kr/ko/sub06_01_01_02.do?mode=view&articleNo=...
```

## How It Works

```text
GitHub Actions (Every 20 Minutes)
  → Run scrape.py
      ├ Fetch BISKIT main page (public page, no login required)
      └ Fetch latest posts from three announcement boards
          → Filter posts by keywords
  → Compare with existing records in docs/data.json
  → Send new posts to Discord via Webhook
  → Commit updated data.json to the repository
```

This project retrieves publicly available HTML pages instead of using APIs. Pages requiring authentication are not accessed.

## Project Structure

| File | Description |
|---|---|
| `scrape.py` | Fetches pages, detects new posts, and sends notifications |
| `.github/workflows/check.yml` | GitHub Actions workflow that runs `scrape.py` every 20 minutes |
| `docs/index.html` | Optional web page displaying detected posts |
| `docs/data.json` | Records of previously detected posts (automatically generated and updated) |

## Setup Guide

### 1. Create a Discord Webhook

1. In your Discord server, open the text channel where you want to receive notifications.
2. Go to **Edit Channel → Integrations → Webhooks → New Webhook**.
3. Click **Copy Webhook URL** to copy the URL.

> Treat your Webhook URL like a password. Never expose it in your code, issues, or public chats.

### 2. Set Up the Repository

1. Create a **Public** repository or fork this repository. (Public repositories receive free GitHub Actions usage.)
2. Navigate to **Settings → Secrets and variables → Actions → New repository secret** and add the following:

   - Name: `DISCORD_WEBHOOK`
   - Secret: Your copied Discord Webhook URL

3. Navigate to **Settings → Actions → General → Workflow permissions** and select **Read and write permissions**.

### 3. Verify the Workflow

1. Go to **Actions → check-biskit → Run workflow** to trigger a manual run.
2. If each source displays `Check completed (initial record)`, the setup is working correctly. No notifications are sent during the first run.
3. To test notifications, remove one entry from `docs/data.json`, commit the changes, and run the workflow again. The removed post will be detected as new and a notification will be sent.

After the initial setup, GitHub Actions will automatically run every 20 minutes.

### 4. Enable the Results Page (Optional)

Navigate to **Settings → Pages** and configure:

- Branch: `main`
- Folder: `/docs`

You can then access the detected post list through GitHub Pages.

Example: `https://<your-username>.github.io/<repository-name>/`

## Customization

All settings can be modified in `scrape.py` and `.github/workflows/check.yml`.

| What to Customize | Location |
|---|---|
| Check interval | `cron` in `check.yml` (`*/20 * * * *` = every 20 minutes; minimum interval: 5 minutes) |
| Notification keywords | `KEYWORD_RE` in `scrape.py` |
| Monitored announcement boards | `BOARDS` in `scrape.py` |
| Enable Telegram notifications | Add `TELEGRAM_TOKEN` and `TELEGRAM_CHAT_ID` as repository secrets |

## Notes and Limitations

- **Scheduled Workflows May Be Delayed**: GitHub Actions scheduled workflows are not guaranteed to run at the exact scheduled time. Delays of several minutes or even tens of minutes may occur, and some runs may be skipped.
- **60-Day Inactivity Rule**: GitHub may disable scheduled workflows if there is no repository activity for 60 days. Check the Actions tab periodically.
- **Website Structure Changes**: Changes to the university website or restrictions on GitHub server access may prevent the scraper from retrieving posts. Failed sources will be shown in the Actions logs.
- **Responsible Request Frequency**: The scraper accesses the university website periodically. Avoid setting an excessively short interval to minimize server load.
- **Data Collection**: Only post titles, dates, and URLs are stored. Full post contents are not collected.

## AI Assistance

Some parts of this project's code were developed with assistance from AI.

## License

[MIT](LICENSE)
