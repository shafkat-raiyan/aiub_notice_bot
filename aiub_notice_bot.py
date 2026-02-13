import requests
from bs4 import BeautifulSoup
import os
from urllib.parse import urljoin

# CONFIGURATION
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
URL = "https://www.aiub.edu/category/notices"

def send_telegram_msg(message):
    send_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    requests.post(send_url, data=data)

def get_latest_notice():
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        page = requests.get(URL, headers=headers)
        soup = BeautifulSoup(page.content, "html.parser")
        title_element = soup.select_one("h2.title")
        
        if title_element:
            title = title_element.get_text().strip()
            link = title_element.find_parent('a')['href']
            return title, urljoin("https://www.aiub.edu", link)
        return None, None
    except:
        return None, None

# Read last saved notice
try:
    with open("last_notice.txt", "r") as f:
        saved_title = f.read().strip()
except FileNotFoundError:
    saved_title = "init"

current_title, current_link = get_latest_notice()

if current_title and current_title != saved_title:
    print(f"New Notice: {current_title}")
    send_telegram_msg(f"🚨 **New AIUB Notice!**\n\n*{current_title}*\n\n[Click to Read]({current_link})")
    
    # Save the new title to file
    with open("last_notice.txt", "w") as f:
        f.write(current_title)
else:
    print("No new notices.")
