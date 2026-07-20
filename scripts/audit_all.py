#!/usr/bin/env python3
"""Screenshot each metaphor for visual audit"""
import asyncio
from playwright.async_api import async_playwright

METAPHORS = ['city', 'traffic_light', 'forest']
BASE_URL = 'http://localhost:8080'
SCREENSHOT_DIR = '/home/pascal/workspace/Metaphors/screenshots'

async def capture(metaphor_id):
    import os
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    output = f'{SCREENSHOT_DIR}/{metaphor_id}_audit.png'
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': 1200, 'height': 800})
        
        # Navigate and wait for WebSocket entities to load
        await page.goto(BASE_URL, wait_until='networkidle')
        await page.wait_for_timeout(2000)  # Let WS connect + render
        
        # Wait for canvas to have content (not all black)
        await page.wait_for_function("""() => {
            const canvas = document.getElementById('canvas');
            if (!canvas) return false;
            const ctx = canvas.getContext('2d');
            const data = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
            for (let i = 0; i < data.length; i += 4) {
                if (data[i] > 10 || data[i+1] > 10 || data[i+2] > 10) return true;
            }
            return false;
        }""", timeout=10000)
        
        # Switch metaphor via dropdown
        await page.select_option('#metaphor-select', metaphor_id)
        await page.wait_for_timeout(2000)  # Let new metaphor render
        
        await page.screenshot(path=output, full_page=False)
        await browser.close()
    
    return output

async def main():
    for m in METAPHORS:
        print(f'Auditing {m}...')
        try:
            path = await capture(m)
            print(f'  ✓ {path}')
        except Exception as e:
            print(f'  ✗ {e}')

asyncio.run(main())
