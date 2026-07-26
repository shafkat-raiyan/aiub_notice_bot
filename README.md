# AIUB Notice Bot

A serverless Python notification platform and automated academic assistant designed for students of American International University-Bangladesh (AIUB). The bot monitors the official [AIUB Noticeboard](https://www.aiub.edu/category/notices) and delivers real-time Telegram alerts, intelligent answers, and instant search capabilities without overloading university servers.

![Status](https://img.shields.io/github/actions/workflow/status/shafkat-raiyan/aiub_notice_bot/check_notice.yml?label=Status)

## Key Features & Architecture

- **Simple RAG System (Retrieval-Augmented Generation)**: The AI academic assistant operates on a simple, highly effective RAG architecture. When a student submits a question via `/ask`, the system retrieves relevant announcements from local storage and provides them as context to OpenRouter AI models. This grounds every answer in official university notices and prevents hallucinations.
- **Local Database Storage**: Keeps up to 200 historical notices (approx. 4 to 6 months of announcements) saved inside `notices_db.json`. When students interact with the bot, answers are delivered immediately from disk storage without making repetitive web requests to the university website.
- **High-Traffic Optimization**: To remain responsive during busy exam periods, the simple RAG system intelligently filters notices by keyword to keep AI processing speeds fast, and uses response caching to serve duplicate questions immediately.
- **Automated Alerts**: Runs every 30 minutes in the background via GitHub Actions to check for new notices and sends broadcast updates to Telegram.
- **Interactive Prompts**: When users click commands from mobile menus without typing additional arguments, the bot actively prompts them for input and clearly explains the timeframe of notices stored in memory.
- **Rich Announcement Details**: Captures the complete title, publication date, text description preview, and direct webpage link for every notice.

## Telegram Bot Commands

- `/notice` - Show the latest 5 campus notices with publication dates.
- `/latest` - Show the most recent notice complete with a summary preview and link.
- `/search <keyword>` - Search across all stored semester announcements (e.g., `/search exam` or `/search tuition`).
- `/ask <question>` - Ask the AI assistant questions using the simple RAG system.
- `/devinfo` - View developer contact information and profiles.
- `/help` - View available commands and database coverage details.
- `/start` - Start the bot and view usage guidance.

## How It Works

1. **Background Monitoring (GitHub Actions)**:
   - Every 30 minutes, an automated GitHub Action executes `aiub_notice_bot.py`.
   - The script checks the university webpage for new notices, records publication dates and description snippets, and updates `notices_db.json`.
   - If a new notice is identified, it broadcasts a formatted alert message to your Telegram chat or channel.
   - Any updates to the notice database are automatically saved back to this repository.

2. **Interactive Responses (Vercel Serverless Webhook)**:
   - When students send commands or ask questions on Telegram, Vercel instantly processes the message via `api/webhook.py`.
   - Search queries and notice listings are loaded directly from `notices_db.json`, ensuring instantaneous response times.
   - For `/ask` queries, the bot invokes the simple RAG pipeline to retrieve relevant notices and generate accurate, context-aware answers.

## Project Structure

- `aiub_notice_bot.py` - Core execution script run by GitHub Actions to monitor notices and send alerts.
- `notices_db.json` - Persistent storage file that retains up to 200 historical campus announcements.
- `api/webhook.py` - Webhook entry point configured for Telegram interactions via Vercel serverless deployment.
- `bot/scraper.py` - Web scraping helper that extracts announcement titles, dates, links, and text descriptions from the AIUB noticeboard.
- `bot/state.py` - Data persistence helper that manages reading and writing to `notices_db.json`.
- `bot/commands.py` - Telegram command processing module featuring interactive conversational input guidance.
- `bot/ai.py` - Implementation of the simple RAG system, keyword pre-filtering, automated model failover, and response caching.
- `bot/notifier.py` - Telegram notification formatting and sending helper with automatic network retry support.
- `bot/config.py` - Global settings and environment variable configurations.
- `.github/workflows/check_notice.yml` - Automation scheduling rule that runs the scraper every 30 minutes.

## Developer Information

Developed and maintained by Syed Shafkat Raiyan.
- GitHub: [shafkat-raiyan](https://github.com/shafkat-raiyan)
- LinkedIn: [Syed Shafkat Raiyan](https://www.linkedin.com/in/shafkat-raiyan)
