import os
import requests
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

discordWebHook = os.getenv("DISCORD_WEBHOOK_URL")
peak_message_id = os.getenv("PEAK_MESSAGE_ID")

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

def extract_peak_from_message(message_content):
    lines = message_content.splitlines()
    for line in lines:
        if line.lower().startswith("🌞 solar peak:"):
            try:
                parts = line.split(":")[1].strip().split("W")[0].strip()
                return int(parts)
            except:
                return 0
    return 0

def track_solar_peak(pv_value: int, timestamp: str):
    global peak_message_id
    if not discordWebHook:
        print("No DISCORD_WEBHOOK_URL found in .env")
        return

    if not peak_message_id:
        peak_message_id = ""

    peak_url = f"{discordWebHook}/messages/{peak_message_id}" if peak_message_id else None

    current_peak = 0
    if peak_message_id:
        resp = requests.get(peak_url)
        if resp.ok:
            content = resp.json().get("content", "")
            current_peak = extract_peak_from_message(content)
        else:
            print("Couldn't fetch peak message, assuming 0W")

    if pv_value > current_peak:
        message = f"🌞 Solar Peak: {pv_value}W\n{timestamp}"
        if peak_message_id:
            patch = requests.patch(peak_url, json={"content": message})
            if patch.ok:
                print(f"🔁 Updated peak to {pv_value}W")
            else:
                print("Patch failed, trying to create new message")
                peak_message_id = ""
        if not peak_message_id:
            webhook_base = discordWebHook.split("/messages")[0]
            post = requests.post(f"{webhook_base}?wait=true", json={"content": message})
            if post.ok:
                try:
                    new_id = post.json()["id"]
                    update_env_variable("PEAK_MESSAGE_ID", new_id)
                    peak_message_id = new_id
                    print(f"✅ New peak message created: {new_id}")
                except:
                    print("Message sent, but failed to parse response.")
            else:
                print(f"Failed to send new peak message → {post.status_code}")
