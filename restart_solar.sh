#!/bin/bash
echo "🔄 Restarting solar bot..."
pkill -f solar_bot.py
sleep 1
cd ~/sunsynk-scraper
nohup python3 solar_bot.py > solar.log 2>&1 &
echo "✅ Solar bot restarted."
