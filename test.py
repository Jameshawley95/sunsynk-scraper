# use this to check your sunsynk credentials are working

from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
import os

# Load env vars
load_dotenv()
email = os.getenv("SUNSYNK_USERNAME")
password = os.getenv("SUNSYNK_PASSWORD")
plant_url = os.getenv("PLANT_URL")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, slow_mo=200)
    page = browser.new_page()
    page.goto("https://www.sunsynk.net/")

    # Login
    page.locator('input[placeholder="Please input your E-mail"]').fill(email)
    page.locator('input[placeholder="Please re-enter password"]').fill(password)
    page.locator('button:has-text("Login")').click()

    # Navigate to plant overview
    page.wait_for_url("**/plants")
    page.goto(plant_url)
    page.wait_for_selector('.box.grid-box .power.f16 span', timeout=10000)

    # Scrape raw values
    pv_power = page.locator('.box.pv-box .power.f16').text_content()
    load_power = page.locator('.box.load-box .power.f16 span').text_content()
    grid_power = page.locator('.box.grid-box .power.f16 span').text_content()
    battery_power = page.locator('.bettey-box .power.f16 span').text_content()
    battery_soc = page.locator('.soc span').text_content()

    # Print results
    print(f"Solar:     {pv_power}")
    print(f"Load:      {load_power}")
    print(f"Grid:      {grid_power}")
    print(f"Battery:   {battery_power}")
    print(f"Battery %: {battery_soc}")
    
    browser.close()
