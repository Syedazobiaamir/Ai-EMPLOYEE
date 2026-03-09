#!/usr/bin/env python3
"""Quick connection test for Odoo MCP server."""
import json, sys, xmlrpc.client
from pathlib import Path

CONFIG = Path(__file__).parent / "config.json"

def test():
    if not CONFIG.exists():
        print("ERROR: config.json not found. Copy config.example.json and fill in credentials.")
        sys.exit(1)

    cfg = json.loads(CONFIG.read_text())
    url, db = cfg["odoo_url"], cfg["odoo_db"]
    user, pwd = cfg["odoo_username"], cfg["odoo_password"]

    print(f"Testing Odoo connection: {url}")
    common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")

    try:
        version = common.version()
        print(f"  Odoo version: {version['server_version']}")
    except Exception as e:
        print(f"ERROR: Cannot reach Odoo at {url}: {e}")
        sys.exit(1)

    uid = common.authenticate(db, user, pwd, {})
    if not uid:
        print(f"ERROR: Authentication failed for user '{user}' on db '{db}'")
        sys.exit(1)
    print(f"  Authenticated as UID: {uid}")

    models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")
    try:
        inv_count = models.execute_kw(db, uid, pwd, "account.move", "search_count",
                                      [[["move_type", "in", ["out_invoice", "in_invoice"]]]])
        cust_count = models.execute_kw(db, uid, pwd, "res.partner", "search_count",
                                       [[["customer_rank", ">", 0]]])
        prod_count = models.execute_kw(db, uid, pwd, "product.product", "search_count",
                                       [[["active", "=", True]]])
        print(f"  Invoices: {inv_count}")
        print(f"  Customers: {cust_count}")
        print(f"  Products: {prod_count}")
        print(f"\nOdoo MCP connection: OK")
    except Exception as e:
        print(f"ERROR: Could not query data: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test()
