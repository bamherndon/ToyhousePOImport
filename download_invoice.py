import os
import sys
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

ORDERS_URL = "https://account.toyhousellc.com/orders"
SESSION_FILE = "toyhouse_session.json"
INVOICES_DIR = "invoices"


def find_order_id(page, order_number):
    """Find the numeric order ID for a given TH order number by scraping the orders list."""
    from bs4 import BeautifulSoup

    normalized = order_number.upper().lstrip("#")

    soup = BeautifulSoup(page.content(), "html.parser")
    for link in soup.find_all("a", href=lambda h: h and "/orders/" in h):
        text = link.get_text(strip=True).lstrip("#").upper()
        if text == normalized:
            return link["href"].split("/orders/")[1].split("?")[0]

    return None


def download_invoice(order_number):
    normalized = order_number.upper()
    if not normalized.startswith("#"):
        normalized = "#" + normalized

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)

        if os.path.exists(SESSION_FILE):
            context = browser.new_context(
                storage_state=SESSION_FILE,
                accept_downloads=True,
            )
        else:
            context = browser.new_context(accept_downloads=True)

        page = context.new_page()

        # Navigate to orders list to find the numeric ID for this order number
        print(f"Looking up order {normalized}...")
        page.goto(ORDERS_URL)
        page.wait_for_load_state("networkidle")

        if "authentication" in page.url.lower():
            print("\nNot logged in. Please log in in the browser.")
            print("Waiting until you reach the orders page...")
            page.wait_for_url(ORDERS_URL, timeout=300000)
            page.wait_for_load_state("networkidle")

        context.storage_state(path=SESSION_FILE)

        order_id = find_order_id(page, normalized)

        # If not found on the first page, keep loading more
        while order_id is None:
            btn = page.locator("button", has_text="Load more")
            if btn.count() == 0:
                break
            print("Order not found yet, loading more orders...")
            btn.first.click()
            page.wait_for_load_state("networkidle")
            order_id = find_order_id(page, normalized)

        if order_id is None:
            print(f"ERROR: Order {normalized} not found.")
            browser.close()
            return

        # Navigate to the order detail page
        order_url = f"https://account.toyhousellc.com/orders/{order_id}"
        print(f"Opening {order_url}...")
        page.goto(order_url)
        page.wait_for_load_state("networkidle")

        # Find the Download Your Invoice button
        btn = page.locator("button", has_text="Download Your Invoice")
        if btn.count() == 0:
            btn = page.locator("a", has_text="Download Your Invoice")
        if btn.count() == 0:
            print("ERROR: 'Download Your Invoice' button not found on this order page.")
            browser.close()
            return

        os.makedirs(INVOICES_DIR, exist_ok=True)
        filename = f"{normalized.lstrip('#')}_invoice.pdf"
        filepath = os.path.join(INVOICES_DIR, filename)

        print("Clicking 'Download Your Invoice'...")
        with page.expect_download() as dl_info:
            btn.first.click()

        dl_info.value.save_as(filepath)
        print(f"\nDone! Invoice saved to: {os.path.abspath(filepath)}")

        browser.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python download_invoice.py <order_number>")
        print("Example: python download_invoice.py TH19087")
        sys.exit(1)

    download_invoice(sys.argv[1])
