import os

email = os.getenv("SUNSYNK_USERNAME")
password = os.getenv("SUNSYNK_PASSWORD")
plant_url = os.getenv("PLANT_URL")

def login_to_sunsynk(browser):
    page = browser.new_page()
    page.goto("https://www.sunsynk.net/")

    # Login
    print("Attempting to log in...")
    page.locator('input[placeholder="Please input your E-mail"]').fill(email)
    page.locator('input[placeholder="Please re-enter password"]').fill(password)
    page.locator('button:has-text("Login")').click()

    try:
        page.wait_for_url("**/plants", timeout=10000)
        print("Login successful.")
    except Exception as e:
        print("Login failed or timed out.")
        print(f"Error: {e}")
        browser.close()
        exit(1)

    # Navigate to overview
    page.wait_for_url("**/plants")
    page.goto(plant_url)
    page.wait_for_selector('.box.grid-box .power.f16 span', timeout=10000)

    return page