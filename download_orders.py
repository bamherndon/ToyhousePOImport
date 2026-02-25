import os
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

ORDERS_URL = "https://account.toyhousellc.com/orders"
SESSION_FILE = "toyhouse_session.json"
INVOICES_DIR = "invoices"



def parse_orders(html):
    """Parse order rows from HTML into a list of dicts."""
    soup = BeautifulSoup(html, "html.parser")
    orders = []

    for row in soup.find_all("div", role="row"):
        # Skip header rows
        if row.find(attrs={"role": "columnheader"}):
            continue

        link = row.find("a", href=lambda h: h and "/orders/" in h)
        if not link:
            continue

        order_id = link["href"].split("/orders/")[1].split("?")[0]
        order_number = link.get_text(strip=True)

        cells = row.find_all("div", role="cell")

        status = ""
        if len(cells) >= 3:
            strong = cells[2].find("strong")
            if strong:
                status = strong.get_text(strip=True)

        total = ""
        if len(cells) >= 5:
            total = cells[4].get_text(strip=True)

        orders.append({
            "order_id": order_id,
            "order_number": order_number,
            "status": status,
            "total": total,
        })

    return orders


def display_orders(orders):
    print()
    print(f"{'#':<4} {'Order':<12} {'Status':<20} {'Total'}")
    print("-" * 55)
    for i, o in enumerate(orders, 1):
        print(f"{i:<4} {o['order_number']:<12} {o['status']:<20} {o['total']}")


def download_invoice(page, order):
    """Navigate to the order page and click Download Your Invoice."""
    order_url = f"https://account.toyhousellc.com/orders/{order['order_id']}"
    print(f"\nOpening order {order['order_number']}...")
    page.goto(order_url)
    page.wait_for_load_state("networkidle")

    os.makedirs(INVOICES_DIR, exist_ok=True)

    btn = page.locator("button", has_text="Download Your Invoice")
    if btn.count() == 0:
        # Try link variant too
        btn = page.locator("a", has_text="Download Your Invoice")
    if btn.count() == 0:
        print("ERROR: 'Download Your Invoice' button not found on this order page.")
        return None

    filename = f"{order['order_number'].lstrip('#')}_invoice.pdf"
    filepath = os.path.join(INVOICES_DIR, filename)

    print("Clicking 'Download Your Invoice'...")
    with page.expect_download() as dl_info:
        btn.first.click()

    download = dl_info.value
    download.save_as(filepath)
    print(f"Saved: {filepath}")
    return filepath


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)

        if os.path.exists(SESSION_FILE):
            print(f"Loading saved session from {SESSION_FILE}...")
            context = browser.new_context(
                storage_state=SESSION_FILE,
                accept_downloads=True,
            )
        else:
            context = browser.new_context(accept_downloads=True)

        page = context.new_page()

        # --- Navigate to orders ---
        print(f"Navigating to {ORDERS_URL}...")
        page.goto(ORDERS_URL)
        page.wait_for_load_state("networkidle")

        if "authentication" in page.url.lower():
            print("\nNot logged in. Please log in in the browser.")
            print("Waiting until you reach the orders page...")
            page.wait_for_url(ORDERS_URL, timeout=300000)
            page.wait_for_load_state("networkidle")

        context.storage_state(path=SESSION_FILE)

        # --- Show orders and let user load more pages as needed ---
        while True:
            orders = parse_orders(page.content())
            if not orders:
                print("No orders found.")
                browser.close()
                return

            display_orders(orders)

            has_more = page.locator("button", has_text="Load more").count() > 0

            if has_more:
                raw = input(f"\nShowing {len(orders)} orders. Enter order # to download, 'm' to load more, or 'q' to quit: ").strip().lower()
            else:
                raw = input(f"\nShowing all {len(orders)} orders. Enter order # to download invoice, or 'q' to quit: ").strip().lower()

            if raw == "q":
                print("Exiting.")
                browser.close()
                return
            elif raw == "m" and has_more:
                print("Loading more orders...")
                page.locator("button", has_text="Load more").first.click()
                page.wait_for_load_state("networkidle")
                continue

            try:
                choice = int(raw)
                if 1 <= choice <= len(orders):
                    break
                print(f"Please enter a number between 1 and {len(orders)}.")
            except ValueError:
                print("Invalid input.")

        selected = orders[choice - 1]
        print(f"\nSelected: {selected['order_number']}  {selected['status']}  {selected['total']}")

        # --- Download invoice ---
        filepath = download_invoice(page, selected)
        if filepath:
            print(f"\nDone! Invoice saved to: {os.path.abspath(filepath)}")

        browser.close()


if __name__ == "__main__":
    main()
