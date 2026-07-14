#!/usr/bin/env python3
"""Screenshot all 3D metaphors using Playwright."""
import asyncio
from pathlib import Path

WORKSPACE = Path("/home/pascal/workspace/Metaphors")
SCREENSHOTS_DIR = WORKSPACE / "screenshots"
URL = "http://localhost:8080/3d"

METAPHORS = ['city', 'solar', 'forest', 'traffic_light', 'space']


async def capture_all():
    from playwright.async_api import async_playwright

    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-gpu']
        )
        page = await browser.new_page(viewport={"width": 1200, "height": 800})

        # Navigate to the 3D page
        print(f"Navigating to {URL}...")
        await page.goto(URL, wait_until="networkidle", timeout=15000)
        await page.wait_for_timeout(2000)

        # Check for JS errors
        errors = []
        page.on("pageerror", lambda err: errors.append(str(err)))

        # Wait for Three.js to initialize
        await page.wait_for_timeout(3000)

        # Check if loading overlay is gone
        loading_hidden = await page.evaluate("""() => {
            const el = document.getElementById('loading');
            return el ? el.style.display === 'none' : true;
        }""")
        print(f"Loading overlay hidden: {loading_hidden}")

        # Try switching via keyboard numbers 1-5
        for i, metaphor in enumerate(METAPHORS):
            key = str(i + 1)
            print(f"\nSwitching to metaphor: {metaphor} (key={key})")

            # Press the number key
            await page.keyboard.press(key)
            await page.wait_for_timeout(2000)  # Wait for fade transition + render

            # Take screenshot
            output_path = SCREENSHOTS_DIR / f"3d_{metaphor}.png"
            await page.screenshot(path=str(output_path), full_page=False)
            print(f"✓ Screenshot saved: {output_path}")

        if errors:
            print(f"\n⚠ JS errors encountered: {errors}")
        else:
            print("\n✓ No JS errors detected")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(capture_all())
