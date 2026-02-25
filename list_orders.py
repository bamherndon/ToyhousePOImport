import os
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

ORDERS_URL = "https://account.toyhousellc.com/orders"
SESSION_FILE = "toyhouse_session.json"


def parse_orders(html):
    soup = BeautifulSoup(html, "html.parser")
    orders = []

    for row in soup.find_all("div", role="row"):
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
    print(f"{'Order':<12} {'Status':<20} {'Total'}")
    print("-" * 50)
    for o in orders:
        print(f"{o['order_number']:<12} {o['status']:<20} {o['total']}")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)

        if os.path.exists(SESSION_FILE):
            context = browser.new_context(storage_state=SESSION_FILE)
        else:
            context = browser.new_context()

        page = context.new_page()

        print(f"Navigating to {ORDERS_URL}...")
        page.goto(ORDERS_URL)
        page.wait_for_load_state("networkidle")

        if "authentication" in page.url.lower():
            print("\nNot logged in. Please log in in the browser.")
            print("Waiting until you reach the orders page...")
            page.wait_for_url(ORDERS_URL, timeout=300000)
            page.wait_for_load_state("networkidle")

        context.storage_state(path=SESSION_FILE)

        orders = parse_orders(page.content())
        if not orders:
            print("No orders found.")
            browser.close()
            return

        display_orders(orders)

        has_more = page.locator("button", has_text="Load more").count() > 0
        if has_more:
            print(f"\n({len(orders)} orders shown — run again with --more to load the next page)")

        browser.close()


if __name__ == "__main__":
    main()
