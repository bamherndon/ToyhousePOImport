#!/usr/bin/env python3
"""Generate a Purchase Order CSV from a Toyhouse invoice PDF and master data.

Usage:
    python generate_po.py <order_number> [location]
    python generate_po.py TH20003
    python generate_po.py TH20003 "My Store Name"

Outputs:
    invoices/<order>_PO.csv          — matched items, ready for import
    invoices/<order>_exceptions.csv  — items not found in master data
"""

import csv
import re
import sys
from datetime import datetime

import pdfplumber

PO_VENDOR = "ToyHouse"

PO_HEADERS = [
    "PO #", "PO Description", "PO Start Ship", "PO End Ship", "PO Vendor",
    "PO Received at location", "Item Description", "Item Default Cost",
    "Item Original Price", "Item Current Price",
    "Item Active?", "Item Long Description",
    "Item Primary Image", "Item Primary Vendor",
    "Item Taxable", "Item UPC", "Item Department", "Item Category",
    "Item Series", "Item bricklink_id", "Item Tags", "Item Sub Department",
    "Item BAM Category", "Item Theme", "Item Retired", "Item Retirement Date",
    "Item Launch Date", "Item Weight",
    "Item Weight Unit", "Item Width", "Item Width Unit", "Item Height",
    "Item Height Unit", "Item Depth", "Item Depth Unit", "Item #",
    "PO Line Unit Cost", "PO Line Qty", "Item Vendor Details Item #",
    "Item Vendor Details Default Cost", "Item Vendor Details #",
    "Item Images URL",
]

EXCEPTION_HEADERS = [
    "Item #", "Title", "UPC", "Pack Size", "Cases Ordered", "Total Qty",
    "Invoice Unit Cost", "Invoice Total Cost", "Reason",
]


def parse_invoice(pdf_path):
    """Parse a Toyhouse invoice PDF. Returns (invoice_no, invoice_date, items)."""
    items = []
    invoice_no = None
    invoice_date = None

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""

            if not invoice_no:
                m = re.search(r'#(TH\d+)', text)
                if m:
                    invoice_no = m.group(1)

            if not invoice_date:
                m = re.search(
                    r'(January|February|March|April|May|June|July|August|'
                    r'September|October|November|December)\s+\d+,\s+\d{4}', text
                )
                if m:
                    try:
                        dt = datetime.strptime(m.group(0), "%B %d, %Y")
                        invoice_date = dt.strftime("%m/%d/%Y")
                    except ValueError:
                        pass

            for table in page.extract_tables():
                for row in table:
                    if not row or len(row) < 5:
                        continue
                    title_raw = (row[0] or "").strip()
                    sku      = (row[1] or "").strip()
                    upc      = (row[2] or "").strip()
                    qty_str  = (row[3] or "").strip()
                    price_str = (row[4] or "").strip()

                    # Skip header rows
                    if title_raw.upper() == "TITLE" or not sku or not sku.isdigit():
                        continue

                    # Normalise multi-line title
                    title = title_raw.replace("\n", " ")

                    # Pack size from "CS PK N"
                    m = re.search(r'CS\s+PK\s+(\d+)', title, re.IGNORECASE)
                    pack_size = int(m.group(1)) if m else 1

                    try:
                        qty_cases = int(qty_str)
                        case_price = float(
                            price_str.replace("$", "").replace(",", "").strip()
                        )
                    except (ValueError, AttributeError):
                        continue

                    items.append({
                        "sku":        sku,
                        "upc":        upc,
                        "title":      title,
                        "pack_size":  pack_size,
                        "qty_cases":  qty_cases,
                        "case_price": case_price,
                    })

    return invoice_no, invoice_date, items


def load_master_data(path="ToyhousemasterData.csv"):
    data = {}
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        # Strip whitespace from header names to handle trailing spaces in sheet
        reader.fieldnames = [h.strip() for h in reader.fieldnames]
        for row in reader:
            row = {k.strip() if k else "": v for k, v in row.items()}
            key = str(row.get("Item #", "")).strip()
            if key:
                data[key] = row
    return data


def strip_currency(value):
    return value.replace("$", "").strip() if value else ""


def parse_retirement(s):
    """Returns (is_retired: bool, date_str: str)."""
    if not s or not s.strip():
        return False, ""
    s = s.strip()
    if s.lower() == "retired":
        return True, ""
    try:
        dt = datetime.strptime(s, "%m/%d/%Y")
        return dt < datetime.now(), s
    except ValueError:
        return False, s


DEFAULT_LOCATION = "Bricks and Minifigs Herndon"


def build_po_row(invoice_no, invoice_date, inv_item, master_item, location):
    sku       = inv_item["sku"]
    pack_size = inv_item["pack_size"]
    qty_cases = inv_item["qty_cases"]
    case_price = inv_item["case_price"]

    unit_cost = round(case_price / pack_size, 4)
    total_qty = pack_size * qty_cases

    is_retired, ret_date = parse_retirement(master_item.get("Retirement Date", ""))

    def val(key):
        return master_item.get(key, "")

    return {
        "PO #":                          invoice_no,
        "PO Description":                "",
        "PO Start Ship":                 invoice_date or "",
        "PO End Ship":                   "",
        "PO Vendor":                     PO_VENDOR,
        "PO Received at location":       location,
        "Item Description":              val("Description"),
        "Item Default Cost":             strip_currency(val("Default Cost")),
        "Item Original Price":           strip_currency(val("MSRP")),
        "Item Current Price":            strip_currency(val("Current price")),
        "Item Active?":                  val("Active?"),
        "Item Long Description":         val("Long Description"),
        "Item Primary Image":            val("Image 1"),
        "Item Primary Vendor":           val("Primary Vendor"),
        "Item Taxable":                  val("Taxable"),
        "Item UPC":                      val("UPC") or inv_item["upc"],
        "Item Department":               val("Department"),
        "Item Category":                 val("Theme"),
        "Item Series":                   val("Theme"),
        "Item bricklink_id":             val("Bricklink ID"),
        "Item Tags":                     val("Shopify Tags"),
        "Item Sub Department":           val("Sub Department"),
        "Item BAM Category":             val("BAM Category"),
        "Item Theme":                    val("Theme"),
        "Item Retired":                  "Yes" if is_retired else "",
        "Item Retirement Date":          ret_date,
        "Item Launch Date":              val("Launch"),
        "Item Weight":                   val("Weight in oz"),
        "Item Weight Unit":              "oz" if val("Weight in oz") else "",
        "Item Width":                    val("Width"),
        "Item Width Unit":               "in" if val("Width") else "",
        "Item Height":                   val("Height"),
        "Item Height Unit":              "in" if val("Height") else "",
        "Item Depth":                    val("Depth"),
        "Item Depth Unit":               "in" if val("Depth") else "",
        "Item #":                        sku,
        "PO Line Unit Cost":             unit_cost,
        "PO Line Qty":                   total_qty,
        "Item Vendor Details Item #":    sku,
        "Item Vendor Details Default Cost": strip_currency(val("Default Cost")),
        "Item Vendor Details #":         "",
        "Item Images URL":               val("Image 1"),
    }


def build_exception_row(inv_item, reason):
    unit_cost = round(inv_item["case_price"] / inv_item["pack_size"], 4)
    total_qty = inv_item["pack_size"] * inv_item["qty_cases"]
    total_cost = round(inv_item["case_price"] * inv_item["qty_cases"], 2)
    return {
        "Item #":             inv_item["sku"],
        "Title":              inv_item["title"],
        "UPC":                inv_item["upc"],
        "Pack Size":          inv_item["pack_size"],
        "Cases Ordered":      inv_item["qty_cases"],
        "Total Qty":          total_qty,
        "Invoice Unit Cost":  unit_cost,
        "Invoice Total Cost": total_cost,
        "Reason":             reason,
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_po.py <order_number> [location]")
        print("Example: python generate_po.py TH20003")
        sys.exit(1)

    order_number = sys.argv[1].upper()
    location = sys.argv[2] if len(sys.argv) >= 3 else DEFAULT_LOCATION
    pdf_path = f"invoices/{order_number}_invoice.pdf"

    print(f"Parsing invoice: {pdf_path}")
    invoice_no, invoice_date, inv_items = parse_invoice(pdf_path)
    print(f"  Invoice #: {invoice_no}, Date: {invoice_date}, Items: {len(inv_items)}")

    print("Loading master data...")
    master_data = load_master_data()
    print(f"  {len(master_data)} items loaded")

    po_rows = []
    exception_rows = []

    for item in inv_items:
        sku = item["sku"]
        master_item = master_data.get(sku)
        if master_item:
            po_rows.append(build_po_row(invoice_no, invoice_date, item, master_item, location))
        else:
            exception_rows.append(
                build_exception_row(item, "Item # not found in master data")
            )

    po_path = f"invoices/{order_number}_PO.csv"
    with open(po_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=PO_HEADERS)
        writer.writeheader()
        writer.writerows(po_rows)

    exc_path = f"invoices/{order_number}_exceptions.csv"
    with open(exc_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=EXCEPTION_HEADERS)
        writer.writeheader()
        writer.writerows(exception_rows)

    print(f"\nResults:")
    print(f"  Matched   → {po_path} ({len(po_rows)} items)")
    print(f"  Exceptions → {exc_path} ({len(exception_rows)} items)")


if __name__ == "__main__":
    main()
