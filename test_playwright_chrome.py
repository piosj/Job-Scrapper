from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    try:
        browser = p.chromium.launch(headless=True, channel="chrome")
        print("Success! Chrome launched.")
        browser.close()
    except Exception as e:
        print("Failed:", type(e).__name__, e)
