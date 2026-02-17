import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        try:
            print("Connecting to http://127.0.0.1:8189...")
            await page.goto("http://127.0.0.1:8189", timeout=60000)
            await asyncio.sleep(5)  # Wait for UI to load
            
            # Take a screenshot
            await page.screenshot(path="ui_debug.png")
            print("Screenshot saved to ui_debug.png")
            
            # Print some info about the buttons
            buttons = await page.query_selector_all("button")
            print(f"Found {len(buttons)} buttons.")
            for btn in buttons:
                text = await btn.inner_text()
                if text:
                    print(f"Button text: {text}")
            
            # Check for settings button specifically
            settings_btn = await page.query_selector("button:has-text('Settings'), .comfy-settings-btn, #comfy-settings-button")
            if settings_btn:
                print("Settings button found!")
                await settings_btn.click()
                await asyncio.sleep(2)
                await page.screenshot(path="settings_open.png")
                print("Screenshot with settings open saved to settings_open.png")
            else:
                print("Settings button NOT found with common selectors.")
                
        except Exception as e:
            print(f"Error during browser execution: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
