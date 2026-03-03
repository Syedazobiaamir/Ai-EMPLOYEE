# Odoo MCP Server — Gold Tier

Integrates Claude Code with Odoo Community (self-hosted) via JSON-RPC APIs.

## Prerequisites

1. **Odoo Community 19+** installed locally:
   - Download: https://www.odoo.com/page/download
   - Or Docker: `docker run -p 8069:8069 odoo:17`

2. **MCP Server** (uses mcp-odoo-adv):
   ```bash
   git clone https://github.com/AlanOgic/mcp-odoo-adv
   cd mcp-odoo-adv
   npm install
   ```

## Configuration

Copy `config.example.json` to `config.json` and fill in your Odoo credentials:

```json
{
  "odoo_url": "http://localhost:8069",
  "odoo_db": "your_database_name",
  "odoo_username": "admin",
  "odoo_password": "your_password"
}
```

## Add to Claude Code Settings

Add to `.claude/settings.json`:

```json
{
  "mcpServers": {
    "odoo": {
      "command": "node",
      "args": ["mcp_servers/odoo_mcp/index.js"],
      "env": {
        "ODOO_URL": "http://localhost:8069",
        "ODOO_DB": "your_db",
        "ODOO_USER": "admin",
        "ODOO_PASSWORD": "your_password"
      }
    }
  }
}
```

## Available Tools (via mcp-odoo-adv)

| Tool | Description |
|------|-------------|
| `create_invoice` | Create customer/vendor invoice |
| `list_invoices` | List invoices with filters |
| `get_invoice` | Get invoice details |
| `create_customer` | Add new customer |
| `list_customers` | List customers |
| `create_product` | Add product to catalog |
| `list_products` | List products with prices |
| `get_financial_summary` | Revenue, expenses, profit summary |
| `create_payment` | Register payment against invoice |

## Usage with /weekly-audit

The `/weekly-audit` skill automatically queries Odoo for:
- Monthly revenue from paid invoices
- Outstanding invoices (overdue)
- New customers added this week
- Product inventory levels

## Manual Testing

```bash
# Test connection
python mcp_servers/odoo_mcp/test_connection.py

# List recent invoices
# (via Claude Code after MCP server is running)
```
