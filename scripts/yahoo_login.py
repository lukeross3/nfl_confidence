import argparse
import os
import time
from urllib.parse import quote

from loguru import logger
from playwright.sync_api import sync_playwright

from nfl_confidence.yahoo import (
    LOGGED_OUT_TITLE,
    PICKEM_BASE_URL,
    add_yahoo_args,
    group_picks_url,
)

# Setup and parse script args
parser = argparse.ArgumentParser(
    description="Open Chrome to log in to Yahoo and save the session cookies for scraping"
)
add_yahoo_args(parser)
parser.add_argument(
    "--profile_dir",
    type=str,
    default="secrets/yahoo_chrome_profile",
    help="Chrome profile dir, kept between runs so re-logging in is usually automatic",
)
parser.add_argument("--timeout", type=int, default=600, help="Seconds to wait for login")
args = parser.parse_args()

# Land on the group page after login, so we can tell when login succeeded
target_url = group_picks_url(args.group_id)
login_url = f"https://login.yahoo.com/?.done={quote(target_url, safe='')}"

with sync_playwright() as p:
    # Drive the real Chrome install rather than bundled Chromium, which Yahoo login may flag
    context = p.chromium.launch_persistent_context(
        os.path.abspath(args.profile_dir),
        channel="chrome",
        headless=False,
        chromium_sandbox=True,
    )
    # Close Chrome however this ends, so the profile is saved cleanly
    try:
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(login_url)
        logger.info("Log in to Yahoo in the Chrome window that just opened")

        deadline = time.time() + args.timeout
        last_seen = None
        while True:
            # Watch the most recently opened tab, in case login opens a new one
            page = context.pages[-1]
            try:
                title = page.title()
            except Exception:
                title = None  # Page is mid-navigation; check again next loop
            if (page.url, title) != last_seen:
                last_seen = (page.url, title)
                logger.info(f"At {page.url} ({title!r})")
            on_pickem = page.url.startswith(f"{PICKEM_BASE_URL}/pickem")
            if on_pickem and title is not None and LOGGED_OUT_TITLE not in title:
                break
            if time.time() > deadline:
                raise TimeoutError(f"Login not completed within {args.timeout}s")
            time.sleep(1)

        context.storage_state(path=args.state_path)
        logger.info(f"Logged in as of {page.url}; saved session to {args.state_path}")
    finally:
        context.close()
