from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
import os
import time
import math
from datetime import datetime
import requests
from solar_peak import track_solar_peak

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

def update_env_variable(key, value):
    lines = []
    found = False
    if os.path.exists(".env"):
        with open(".env", "r") as f:
            for line in f:
                if line.startswith(f"{key}="):
                    lines.append(f"{key}={value}\n")
                    found = True
                else:
                    lines.append(line)
    if not found:
        lines.append(f"{key}={value}\n")
    with open(".env", "w") as f:
        f.writelines(lines)

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
    filled = math.ceil((soc / 100) * length)
    filled = min(filled, length)
    empty = length - filled
    green = ''.join("\u001b[1;34;48m█\u001b[0m" for _ in range(filled))
    empty_part = '░' * empty
    return f"\u001b[0;1m🔋 Battery:\u001b[0m\u001b[1;37m{soc:>4}%\u001b[0m  {green}{empty_part}"

# Scrape and post loop
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
        # scrape values from the plant dashboard
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

        if grid_value == 0:
            grid_display = f"{grid_value} 👍"
        elif soc_value >= 99 and pv_value > load_value:
            grid_value = -abs(grid_value)
            grid_display = f"{grid_value}"
        else:
            grid_display = f"{grid_value}"

        grid_bar_blocks = max(1, abs(grid_value) // 100)
        grid_bar_visual = ''.join(f"\u001b[1;33;48m█\u001b[0m" for _ in range(grid_bar_blocks))
        grid_bar_emoji = " 🤑" if grid_value < 0 else ""

        if total_input > load_value:
            battery_direction = "charging"
        elif total_input < load_value:
            battery_direction = "discharging"
        else:
            battery_direction = "steady"

        timestamp = datetime.now().strftime("%H:%M %d/%m/%Y")

        solar_bar = build_coloured_bar("\u2600\ufe0f", "Solar:", pv_value, 100, "32")
        load_bar = build_coloured_bar("\ud83d\udca1", "Load:", load_value, 100, "31")
        grid_bar = f"\u001b[0;1m🔌 Grid: \u001b[1;37m{grid_value:>5}W \u001b[0m  {grid_bar_visual}{grid_bar_emoji}"
        battery_bar = f"{build_battery_bar(soc_value)} {battery_direction} @ \u001b[1;37m{battery_power}\u001b[0m"

        #discord message output
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

        edit_url = f"{discordWebHook}/messages/{message_id}"
        resp = requests.patch(edit_url, json={"content": message})
        # if message does not already exist create a new one and save the ID
        if not resp.ok:
            print(f"Patch failed → {resp.status_code} {resp.text}")
            print("Creating a new message instead...")
            webhook_base = discordWebHook.split("/messages")[0]
            post_resp = requests.post(f"{webhook_base}?wait=true", json={"content": message})

            if post_resp.ok:
                try:
                    new_message = post_resp.json()
                    new_message_id = new_message["id"]
                    print("Message created successfully.")
                    print(f"Updating .env with: MESSAGE_ID={new_message_id}")
                    update_env_variable("MESSAGE_ID", new_message_id)
                    message_id = new_message_id
                except ValueError:
                    print("Message sent but failed to parse JSON. Update .env manually.")
            else:
                print(f"Failed to send new message → {post_resp.status_code} {post_resp.text}")

        track_solar_peak(pv_value, timestamp)

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

        # Wait before the next scrape, value is in seconds
        time.sleep(60)