from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
from datetime import datetime
from solar_peak import track_solar_peak
from solar_visuals import build_coloured_bar, build_battery_bar, build_grid_bar, calculate_grid_flow
from login import login_to_sunsynk
import os
import time
import requests
import threading
import signal
import sys

# Load environment variables
load_dotenv()

discordWebHook = os.getenv("DISCORD_WEBHOOK_URL")
solar_role = os.getenv("SOLAR_ROLE")
message_id = os.getenv("MESSAGE_ID")
start_time = time.time()
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

def print_uptime():
    while True:
        elapsed = int(time.time() - start_time)
        days, remainder = divmod(elapsed, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        print(f"\rBot Uptime: {days}d {hours:02}:{minutes:02}:{seconds:02} ", end="")
        time.sleep(1)

def clean_exit(signum, frame):
    print("\n🔌 Shutting down... Closing browser and exiting.")
    try:
        browser.close()
    except Exception:
        pass
    sys.exit(0)

# Battery alerts
def send_discord_alert_1(soc, battery_power):
    requests.post(discordWebHook, json={
        "content": f"<@&{solar_role}>\n🔋 Battery is almost full! {soc}⚡"
    })

def send_discord_alert_2(soc, battery_power):
    requests.post(discordWebHook, json={
        "content": f"<@&{solar_role}>\n🔋 LOW BATTERY!!! {soc}⚠️"
    })

# Scrape and post loop
with sync_playwright() as p:
    signal.signal(signal.SIGINT, clean_exit)   # Ctrl+C
    signal.signal(signal.SIGTERM, clean_exit)  # kill signal from OS

    browser = p.chromium.launch(headless=True, slow_mo=200)

    page = login_to_sunsynk(browser)

    threading.Thread(target=print_uptime, daemon=True).start()

    while True:
        try:
            # scrape values from the plant dashboard
            time.sleep(5)  # Ensure page is fully loaded
            grid_power = page.locator('.box.grid-box .power.f16 span').text_content()
            load_power = page.locator('.box.load-box .power.f16 span').text_content()
            battery_power = page.locator('.bettey-box .power.f16 span').text_content()
            battery_soc = page.locator('.soc span').text_content()
            pv_power = page.locator('.box.pv-box .power.f16').text_content()

        except Exception as e:
            print(f"\nScrape failed: {e}")
            print("Attempting to re-login...\n")

            try:
                login_to_sunsynk(browser)
            except Exception as login_err:
                print(f"Re-login also failed: {login_err}")
                print("Waiting 60 seconds before trying again...\n")
                time.sleep(55)

        pv_value = int(pv_power.replace("W", "").strip())
        load_value = int(load_power.replace("W", "").strip())
        grid_value = int(grid_power.replace("W", "").strip())
        soc_value = int(battery_soc.strip().replace("%", ""))
        battery_watts = int(battery_power.replace("W", "").replace("-", "").strip())
        total_input = pv_value + grid_value

        if pv_value == 0 and load_value == 0 and grid_value == 0 and soc_value == 0:
            print("Skipping invalid data — all values are 0")
            time.sleep(55)
            continue

        if total_input > load_value:
            battery_direction = "charging"
        else:
            battery_direction = "discharging"

        timestamp = datetime.now().strftime("%H:%M %d/%m/%Y")
    
        solar_bar = build_coloured_bar("\u2600\ufe0f", "Solar:", pv_value, 100, "32")
        load_bar = build_coloured_bar("\ud83d\udca1", "Load:", load_value, 100, "31")
        grid_bar = build_grid_bar(calculate_grid_flow(pv_value, load_value, battery_watts, grid_value))
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
        time.sleep(55)