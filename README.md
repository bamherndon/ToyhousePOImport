# ToyhousePOImport

A toolchain for importing Toyhouse purchase orders into your store's inventory system. All scripts are automated with cached sessions — no repeated logins needed.

---

## Using with Claude Code (AI Agent)

The fastest way to use this toolchain is through [Claude Code](https://claude.ai/claude-code). Just open this project directory in Claude Code and give plain-English commands. Claude knows how to run each script automatically.

### Example prompts

```
download toyhouse master data
```
```
list my toyhouse orders
```
```
download the invoice for TH19087
```
```
generate a purchase order for TH19087
```
```
generate a purchase order for TH19087 for "My Store Name"
```

### Full workflow example

You can chain steps together in a single conversation:

```
download the invoice for TH19087 then generate a purchase order for it
```

Claude will download the invoice first, then generate the PO automatically.

---

## Manual Usage

If you prefer to run the scripts directly, use the commands below from the project root.

### Prerequisites

- Python virtualenv set up at `venv/`
- `token.json` — Google OAuth token for downloading master data (created on first auth)
- `toyhouse_session.json` — Toyhouse browser session (created on first login)

---

### 1. Download Master Data

Downloads the Toyhouse product master data from Google Sheets.

```bash
venv/bin/python download_sheet.py
```

**Output:** `ToyhousemasterData.csv`

> Required before generating purchase orders. Re-run periodically to get updated pricing and item data.

---

### 2. List Orders

Displays your Toyhouse orders with status and totals.

```bash
venv/bin/python list_orders.py
```

> Shows the first page of orders. Run when you need to look up an order number.

---

### 3. Download Invoice

Downloads the invoice PDF for a specific order.

```bash
venv/bin/python download_invoice.py <order_number>
```

**Example:**
```bash
venv/bin/python download_invoice.py TH19087
```

**Output:** `invoices/TH19087_invoice.pdf`

> Automatically searches through order pages to find the order and clicks "Download Your Invoice".

---

### 4. Generate Purchase Order

Parses the invoice and cross-references items against master data to produce import-ready CSVs.

```bash
venv/bin/python generate_po.py <order_number> [location]
```

**Examples:**
```bash
venv/bin/python generate_po.py TH19087
venv/bin/python generate_po.py TH19087 "My Store Name"
```

**Output:**
- `invoices/TH19087_PO.csv` — matched items, ready for import
- `invoices/TH19087_exceptions.csv` — items not found in master data

**Notes:**
- `location` defaults to `"Bricks and Minifigs Herndon"` if not provided
- Requires the invoice PDF and `ToyhousemasterData.csv` to be present first
- Unit costs = case pack price ÷ pack size
- Quantities = pack size × cases ordered

---

## Typical Workflow

```
1. download_sheet.py        → refresh master data
2. list_orders.py           → find your order number
3. download_invoice.py TH#  → download the invoice PDF
4. generate_po.py TH#       → generate PO and exceptions CSVs
5. Import PO.csv into your system
```
