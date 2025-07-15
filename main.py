from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
import os
import time
from datetime import datetime
import requests

# Load environment variables
load_dotenv()
email = os.getenv("SUNSYNK_USERNAME")
password = os.getenv("SUNSYNK_PASSWORD")
discordWebHook = os.getenv("DISCORD_WEBHOOK_URL")
solar_role = os.getenv("SOLAR_ROLE")
message_id = os.getenv("MESSAGE_ID")
plant_url = os.getenv("PLANT_URL")

full_alert_sent = False
low_alert_sent = False

# Battery alerts
def send_discord_alert_1(soc, battery_power):
    requests.post(discordWebHook, json={
        "content": f"<@&{solar_role}>\n🔋 Battery is almost full! {soc}⚡"
    })

def send_discord_alert_2(soc, battery_power):
    requests.post(discordWebHook, json={
        "content": f"<@&{solar_role}>\n🔋 LOW BATTERY!!! {soc}⚠️"
    })

# Simple coloured block bar per 100W
def build_coloured_bar(icon, label, value, unit, colour_code):
    blocks = max(1, value // unit)
    bar = ''.join(f"\u001b[1;{colour_code};48m█\u001b[0m" for _ in range(blocks))
    return f"\u001b[0;1m{icon} {label:<7}\u001b[1;37m{value:>4}W \u001b[0m  {bar}"

# Battery bar by % with green blocks and remaining light grey
def build_battery_bar(soc, length=15):
    filled = int((soc / 100) * length)
    empty = length - filled
    green = ''.join("\u001b[1;34;48m█\u001b[0m" for _ in range(filled))
    empty_part = '░' * empty
    return f"\u001b[0;1m🔋 Battery:\u001b[0m\u001b[1;37m{soc:>4}%\u001b[0m  {green}{empty_part}"

# 🕸 Scrape and post loop
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, slow_mo=200)
    page = browser.new_page()
    page.goto("https://www.sunsynk.net/")

    # Login
    page.locator('input[placeholder="Please input your E-mail"]').fill(email)
    page.locator('input[placeholder="Please re-enter password"]').fill(password)
    page.locator('button:has-text("Login")').click()

    # Navigate to overview
    page.wait_for_url("**/plants")
    page.goto(plant_url)
    page.wait_for_selector('.box.grid-box .power.f16 span', timeout=10000)

    while True:
        # 📊 Scrape values
        grid_power = page.locator('.box.grid-box .power.f16 span').text_content()
        load_power = page.locator('.box.load-box .power.f16 span').text_content()
        battery_power = page.locator('.bettey-box .power.f16 span').text_content()
        battery_soc = page.locator('.soc span').text_content()
        pv_power = page.locator('.box.pv-box .power.f16').text_content()

        pv_value = int(pv_power.replace("W", "").strip())
        load_value = int(load_power.replace("W", "").strip())
        grid_value = int(grid_power.replace("W", "").strip())
        soc_value = int(battery_soc.strip().replace("%", ""))
        total_input = pv_value + grid_value

        selling_to_grid = soc_value >= 99 and pv_value > load_value
        if grid_value == 0:
            grid_display = f"{grid_power} 👍"
        elif selling_to_grid:
            grid_display = f"-{grid_power} 🤑"
        else:
            grid_display = grid_power

        if total_input > load_value:
            battery_direction = "charging"
        elif total_input < load_value:
            battery_direction = "discharging"
        else:
            battery_direction = "steady"

        # ⌚ Format timestamp
        timestamp = datetime.now().strftime("%H:%M %d/%m/%Y")

        # 🔧 Build bars
        solar_bar = build_coloured_bar("☀️", "Solar:", pv_value, 100, "32")
        load_bar = build_coloured_bar("💡", "Load:", load_value, 100, "31")
        grid_bar = build_coloured_bar("🔌", "Grid:", grid_value, 100, "33")
        battery_bar = f"{build_battery_bar(soc_value)} {battery_direction} @ \u001b[1;37m{battery_power}\u001b[0m"

        # 📨 Final message
        message = (
            f"<@&{solar_role}>\n"
            f"```ansi\n"
            f"{solar_bar}\n"
            f"{load_bar}\n"
            f"{grid_bar}\n"
            f"{battery_bar}\n"
            f"\u001b[2mLast Updated: {timestamp}\u001b[0m\n"
            f"```"
        )

        # 🛠 Update Discord message
        edit_url = f"{discordWebHook}/messages/{message_id}"
        resp = requests.patch(edit_url, json={"content": message})
        if not resp.ok:
            print(f"❌ Patch failed → {resp.status_code} {resp.text}")

        # 🚨 Alert logic
        if soc_value >= 95 and not full_alert_sent:
            send_discord_alert_1(battery_soc, battery_power)
            full_alert_sent = True
        elif soc_value < 95:
            full_alert_sent = False

        if soc_value <= 20 and not low_alert_sent:
            send_discord_alert_2(battery_soc, battery_power)
            low_alert_sent = True
        elif soc_value > 20:
            low_alert_sent = False

        time.sleep(60)
