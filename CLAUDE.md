# ToyhousePOImport

## Download Toyhouse Master Data
When asked to download toyhouse master data, run:
```bash
cd /home/heman/ToyhousePOImport && venv/bin/python download_sheet.py
```

- Script: `download_sheet.py`
- Google Sheet ID: `1CN4a9mvQ-Suyi_dceUZ7miHyB4omrvOVK1QvuOvx-ME`
- Output: `ToyhousemasterData.csv`
- Auth token is cached in `token.json` — no browser login needed
- Dependencies installed in `venv/`

## List Toyhouse Orders
When asked to list toyhouse orders, run:
```bash
cd /home/heman/ToyhousePOImport && venv/bin/python list_orders.py
```

- Script: `list_orders.py`
- Opens a browser, loads saved session, displays orders with status and total
- Session cached in `toyhouse_session.json` — no login needed after first run
- Shows first page of orders; note if more pages are available

## Download Toyhouse Invoice
When asked to download a toyhouse invoice, run:
```bash
cd /home/heman/ToyhousePOImport && venv/bin/python download_invoice.py <order_number>
```

Example:
```bash
cd /home/heman/ToyhousePOImport && venv/bin/python download_invoice.py TH19087
```

- Script: `download_invoice.py`
- Takes a Toyhouse order number (e.g. TH19087) as argument
- Automatically searches through order pages to find the order
- Clicks "Download Your Invoice" and saves PDF to `invoices/<order_number>_invoice.pdf`
- Session cached in `toyhouse_session.json` — no login needed after first run

## Generate Purchase Order
When asked to generate a purchase order, run:
```bash
cd /home/heman/ToyhousePOImport && venv/bin/python generate_po.py <order_number> [location]
```

Example:
```bash
cd /home/heman/ToyhousePOImport && venv/bin/python generate_po.py TH19087
cd /home/heman/ToyhousePOImport && venv/bin/python generate_po.py TH19087 "My Store Name"
```

- Script: `generate_po.py`
- Requires invoice PDF at `invoices/<order_number>_invoice.pdf` — download it first if needed
- Requires `ToyhousemasterData.csv` — download master data first if needed
- Parses the invoice PDF and cross-references each item against master data by Item #
- `location` defaults to `"Bricks and Minifigs Herndon"` if not provided
- Outputs:
  - `invoices/<order_number>_PO.csv` — matched items, ready for import
  - `invoices/<order_number>_exceptions.csv` — items not found in master data
- Unit costs are calculated per individual item (case pack price ÷ pack size)
- Quantities are individual item counts (pack size × cases ordered)
