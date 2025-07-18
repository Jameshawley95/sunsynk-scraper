# 🌞 Sunsynk Discord Bot (not official)

![Bot Preview](solarbot-discord.png)

A Python bot that scrapes live solar stats from the Sunsynk web portal and updates a message in Discord with realtime solar, battery, and grid info.

## Features

- Scrapes data using Playwright
- Formats it with coloured ANSI bars
- Sends live updates to Discord using webhooks
- Alerts when battery is low or nearly full

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   playwright install

2. Create a .env file:

SUNSYNK_USERNAME=your@email.com
SUNSYNK_PASSWORD=yourpassword
DISCORD_WEBHOOK_URL=your_discord_webhook_url
SOLAR_ROLE=123456789012345678 #discord role id which will be sent notifications
MESSAGE_ID=123456789012345678 #discord message id which will be updated every minute

3. run start.bat

### Disclaimer

This project is an independent tool developed for personal and educational use.  
It is **not affiliated with, endorsed by, or supported by Sunsynk** in any way.

All data scraping is done via publicly accessible user portals with user-provided credentials.  
Use this tool at your own risk. Respect Sunsynk's Terms of Service when using this bot.