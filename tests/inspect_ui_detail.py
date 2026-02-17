import asyncio
from playwright.async_api import async_playwright
import json

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        try:
            print("Connecting to http://127.0.0.1:8189...")
            await page.goto("http://127.0.0.1:8189", timeout=60000)
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(5)  # Wait for UI to settle
            
            # Take a screenshot
            await page.screenshot(path="ui_layout.png")
            print("Screenshot saved to ui_layout.png")
            
            # Analyze Buttons
            buttons = await page.evaluate('''() => {
                return Array.from(document.querySelectorAll('button')).map(b => ({
                    text: b.innerText,
                    id: b.id,
                    className: b.className,
                    visible: b.offsetParent !== null
                }));
            }''')
            
            print(f"Found {len(buttons)} buttons:")
            for b in buttons:
                print(f"  - Text: '{b['text']}', ID: '{b['id']}', Class: '{b['className']}', Visible: {b['visible']}")

            # Try to find a settings button candidate
            settings_candidates = [b for b in buttons if 'Settings' in b['text'] or 'settings' in b['id'] or 'settings' in b['className']]
            print(f"\\nSettings candidates: {settings_candidates}")

        except Exception as e:
            print(f"Error during execution: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
