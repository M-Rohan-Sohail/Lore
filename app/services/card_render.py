import os
from playwright.async_api import async_playwright

CHROME_EXECUTABLE_PATH = os.getenv("CHROME_EXECUTABLE_PATH", "/usr/bin/google-chrome")

async def render_html_to_png(html_content: str) -> bytes:
    """
    Renders HTML content to a 1080x1920 PNG byte array using a headless Chromium browser.
    Launches the system chrome rather than downloading Playwright's own bundled version.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path=CHROME_EXECUTABLE_PATH,
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ]
        )
        # Using 1080x1920 (Standard vertical format for cards)
        page = await browser.new_page(viewport={"width": 1080, "height": 1920}, device_scale_factor=1)
        
        # Set content
        await page.set_content(html_content, wait_until="networkidle")
        
        # Take screenshot of the full page
        screenshot = await page.screenshot(
            type="png",
            clip={"x": 0, "y": 0, "width": 1080, "height": 1920}
        )
        
        await browser.close()
        return screenshot
