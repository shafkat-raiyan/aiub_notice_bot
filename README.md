# AIUB Notice Bot

A serverless Python bot that monitors the [AIUB Noticeboard](https://www.aiub.edu/category/notices) every 30 minutes and sends new notices to your Telegram.

![Status](https://img.shields.io/github/actions/workflow/status/shafkat-raiyan/aiub_notice_bot/check_notice.yml?label=Status)

## Features
- **Auto notifications** - Get alerted when new notices are posted (via GitHub Actions)
- **On-demand commands** - Ask the bot for notices anytime (via Vercel webhook)

## Bot Commands
- `/start` - Welcome message
- `/notice` - Show latest 5 notices with dates
- `/latest` - Show the most recent notice with link preview
- `/search <keyword>` - Search notices (e.g., `/search exam`)
- `/help` - Show available commands

## How It Works
1. **GitHub Actions** runs the script every 30 minutes
2. It scrapes all notices from the AIUB page
3. Compares against previously seen notices
4. Sends Telegram alerts for any new ones
5. Updates `last_notice.txt` to remember what's been sent

## Setup (Run Your Own)
1. **Fork** this repository
2. Get your **Telegram Bot Token** (@BotFather) and **Chat ID** (@userinfobot)
3. Go to **Settings > Secrets and variables > Actions** and add:
   - `BOT_TOKEN`
   - `CHAT_ID`
4. Go to the **Actions** tab and enable the workflow

### Optional: Enable Bot Commands
1. Deploy to **Vercel** and add `BOT_TOKEN` environment variable
2. Set webhook: `https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://<your-app>.vercel.app/api/webhook`

## Files
- `aiub_notice_bot.py` - Main bot logic (GitHub Actions)
- `api/webhook.py` - Telegram commands handler (Vercel)
- `.github/workflows/check_notice.yml` - Automation timer
- `last_notice.txt` - Memory file (stores seen notices)
