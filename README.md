# 🤖 AIUB Notice Bot

A serverless Python bot that monitors the [AIUB Noticeboard](https://www.aiub.edu/category/notices) every 30 minutes and sends new notices to your Telegram.

![Status](https://img.shields.io/github/actions/workflow/status/shafkat-raiyan/aiub_notice_bot/check_notice.yml?label=Status)

## How It Works
1. **GitHub Actions** runs the script every 30 minutes.
2. It scrapes the latest notice title.
3. If the title is different from the last saved one, it sends a **Telegram Alert**.
4. It updates the database (`last_notice.txt`) automatically.

## Setup (Run Your Own)
1. **Fork** this repository.
2. Get your **Telegram Bot Token** (@BotFather) and **Chat ID** (@userinfobot).
3. Go to **Settings > Secrets and variables > Actions** and add:
   - `BOT_TOKEN`
   - `CHAT_ID`
4. Go to the **Actions** tab and enable the workflow.

## Files
- `aiub_notice_bot.py`: The logic.
- `.github/workflows/check_notice.yml`: The automation timer.
- `last_notice.txt`: Memory file.
