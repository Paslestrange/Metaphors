#!/usr/bin/env python3
"""Metaphors — Screenshot export.

Captures a PNG screenshot of the running application.
Usage:
    python3 scripts/screenshot.py                    # Default: 1200x800
    python3 scripts/screenshot.py --width 1920 --height 1080
    python3 scripts/screenshot.py --output /tmp/city.png
    python3 scripts/screenshot.py --metaphor space    # Switch metaphor first
"""
import argparse
import asyncio
import sys
from pathlib import Path

WORKSPACE = Path("/home/pascal/workspace/Metaphors")
DEFAULT_OUTPUT = WORKSPACE / "screenshots"


async def capture_screenshot(url: str, output: Path, width: int, height: int, wait_sec: int = 3, metaphor: str = None):
    """Capture a screenshot of the running app."""
    from playwright.async_api import async_playwright

    output.parent.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": width, "height": height})

        # Navigate and wait for canvas to render
        await page.goto(url, wait_until="networkidle")
        await page.wait_for_timeout(2000)  # Let WebSocket entities load

        # Switch metaphor if specified
        if metaphor:
            await page.evaluate(f"""() => {{
                const select = document.getElementById('metaphor-select');
                if (select) {{
                    select.value = '{metaphor}';
                    select.dispatchEvent(new Event('change'));
                }}
            }}""")
            await page.wait_for_timeout(wait_sec * 1000)  # Let 3D initialize

        # Take screenshot
        await page.screenshot(path=str(output), full_page=False)
        await browser.close()

    return output


def main():
    parser = argparse.ArgumentParser(description="Capture Metaphors screenshot")
    parser.add_argument("--url", default="http://localhost:8080", help="App URL")
    parser.add_argument("--output", "-o", type=str, help="Output file path")
    parser.add_argument("--width", type=int, default=1200, help="Viewport width")
    parser.add_argument("--height", type=int, default=800, help="Viewport height")
    parser.add_argument("--wait", type=int, default=3, help="Seconds to wait for render")
    parser.add_argument("--metaphor", type=str, help="Metaphor to switch to before screenshot")
    args = parser.parse_args()

    if args.output:
        output = Path(args.output)
    else:
        import time
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output = DEFAULT_OUTPUT / f"screenshot_{timestamp}.png"

    print(f"Capturing screenshot: {args.width}x{args.height} from {args.url}")
    print(f"Output: {output}")

    try:
        result = asyncio.run(capture_screenshot(args.url, output, args.width, args.height, args.wait, args.metaphor))
        print(f"✓ Screenshot saved: {result}")
    except Exception as e:
        print(f"✗ Failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
