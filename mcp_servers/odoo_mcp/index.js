#!/usr/bin/env node
/**
 * Odoo MCP Server — Gold Tier
 * Connects Claude Code to Odoo Community via XML-RPC
 *
 * Tools: create_invoice, list_invoices, get_invoice, create_customer,
 *        list_customers, create_product, list_products, get_financial_summary, create_payment
 */

const xmlrpc = require("xmlrpc");
const path = require("path");
const fs = require("fs");
const readline = require("readline");

// ── Config ────────────────────────────────────────────────────────────────────

const CONFIG_PATH =
  process.env.ODOO_CONFIG ||
  path.join(__dirname, "config.json");

function loadConfig() {
  const env = {
    url: process.env.ODOO_URL,
    db: process.env.ODOO_DB,
    username: process.env.ODOO_USER || process.env.ODOO_USERNAME,
    password: process.env.ODOO_PASSWORD,
  };
  if (env.url && env.db && env.username && env.password) return env;

  if (fs.existsSync(CONFIG_PATH)) {
    const cfg = JSON.parse(fs.readFileSync(CONFIG_PATH, "utf8"));
    return {
      url: cfg.odoo_url,
      db: cfg.odoo_db,
      username: cfg.odoo_username,
      password: cfg.odoo_password,
    };
  }
  return {
    url: "http://localhost:8069",
    db: "ai_employee",
    username: "admin",
    password: "admin123",
  };
}

// ── XML-RPC Helpers ───────────────────────────────────────────────────────────

function makeClient(config, path) {
  const url = new URL(config.url);
  const opts = {
    host: url.hostname,
    port: parseInt(url.port) || (url.protocol === "https:" ? 443 : 80),
    path: path,
  };
  return url.protocol === "https:"
    ? xmlrpc.createSecureClient(opts)
    : xmlrpc.createClient(opts);
}

function callRpc(client, method, params) {
  return new Promise((resolve, reject) => {
    client.methodCall(method, params, (err, result) => {
      if (err) reject(err);
      else resolve(result);
    });
  });
}

async function getUid(config) {
  const common = makeClient(config, "/xmlrpc/2/common");
  return await callRpc(common, "authenticate", [
    config.db,
    config.username,
    config.password,
    {},
  ]);
}

async function odooCall(config, uid, model, method, args, kwargs = {}) {
  const obj = makeClient(config, "/xmlrpc/2/object");
  return await callRpc(obj, "execute_kw", [
    config.db,
    uid,
    config.password,
    model,
    method,
    args,
    kwargs,
  ]);
}

// ── MCP Protocol ─────────────────────────────────────────────────────────────

const tools = [
  {
    name: "list_invoices",
    description: "List invoices from Odoo with optional filters",
    inputSchema: {
      type: "object",
      properties: {
        state: {
          type: "string",
          description: "Invoice state: draft, posted, cancel",
        },
        payment_state: {
          type: "string",
          description: "Payment state: not_paid, in_payment, paid",
        },
        limit: { type: "number", description: "Max results (default 10)" },
      },
    },
  },
  {
    name: "create_invoice",
    description: "Create a new customer invoice in Odoo",
    inputSchema: {
      type: "object",
      required: ["partner_name", "amount", "description"],
      properties: {
        partner_name: {
          type: "string",
          description: "Customer name",
        },
        amount: { type: "number", description: "Invoice amount" },
        description: {
          type: "string",
          description: "Line item description",
        },
        currency: {
          type: "string",
          description: "Currency code (default PKR)",
        },
      },
    },
  },
  {
    name: "get_invoice",
    description: "Get details of a specific invoice by ID or name",
    inputSchema: {
      type: "object",
      required: ["invoice_id"],
      properties: {
        invoice_id: {
          type: "number",
          description: "Odoo invoice ID",
        },
      },
    },
  },
  {
    name: "list_customers",
    description: "List customers from Odoo",
    inputSchema: {
      type: "object",
      properties: {
        limit: { type: "number", description: "Max results (default 10)" },
        order: {
          type: "string",
          description: "Sort order e.g. create_date desc",
        },
      },
    },
  },
  {
    name: "create_customer",
    description: "Create a new customer/partner in Odoo",
    inputSchema: {
      type: "object",
      required: ["name"],
      properties: {
        name: { type: "string", description: "Customer name" },
        email: { type: "string", description: "Email address" },
        phone: { type: "string", description: "Phone number" },
      },
    },
  },
  {
    name: "list_products",
    description: "List products from Odoo",
    inputSchema: {
      type: "object",
      properties: {
        limit: { type: "number", description: "Max results (default 20)" },
      },
    },
  },
  {
    name: "create_product",
    description: "Create a new product in Odoo",
    inputSchema: {
      type: "object",
      required: ["name", "price"],
      properties: {
        name: { type: "string", description: "Product name" },
        price: { type: "number", description: "Sales price" },
        description: { type: "string", description: "Product description" },
      },
    },
  },
  {
    name: "get_financial_summary",
    description: "Get revenue, expenses, and outstanding invoices summary",
    inputSchema: {
      type: "object",
      properties: {
        period: {
          type: "string",
          description: "Period: this_month, this_year, all",
        },
      },
    },
  },
  {
    name: "create_payment",
    description: "Register a payment against an invoice",
    inputSchema: {
      type: "object",
      required: ["invoice_id", "amount"],
      properties: {
        invoice_id: { type: "number", description: "Invoice ID to pay" },
        amount: { type: "number", description: "Payment amount" },
        memo: { type: "string", description: "Payment reference" },
      },
    },
  },
];

// ── Tool Handlers ─────────────────────────────────────────────────────────────

async function handleTool(name, args) {
  const config = loadConfig();
  const uid = await getUid(config);

  if (!uid) {
    return { error: "Odoo authentication failed. Check config.json credentials." };
  }

  switch (name) {
    case "list_invoices": {
      const domain = [["move_type", "in", ["out_invoice", "in_invoice"]]];
      if (args.state) domain.push(["state", "=", args.state]);
      if (args.payment_state)
        domain.push(["payment_state", "=", args.payment_state]);

      const invoices = await odooCall(
        config, uid, "account.move", "search_read",
        [domain],
        {
          fields: ["name", "partner_id", "amount_total", "state", "payment_state", "invoice_date", "invoice_date_due"],
          limit: args.limit || 10,
          order: "invoice_date desc",
        }
      );
      return { invoices, count: invoices.length };
    }

    case "create_invoice": {
      // Find or create partner
      let partnerIds = await odooCall(config, uid, "res.partner", "search", [
        [["name", "ilike", args.partner_name]],
      ]);
      let partnerId;
      if (partnerIds.length > 0) {
        partnerId = partnerIds[0];
      } else {
        partnerId = await odooCall(config, uid, "res.partner", "create", [
          { name: args.partner_name, customer_rank: 1 },
        ]);
      }

      const invoiceId = await odooCall(config, uid, "account.move", "create", [
        {
          move_type: "out_invoice",
          partner_id: partnerId,
          invoice_line_ids: [
            [
              0,
              0,
              {
                name: args.description,
                quantity: 1,
                price_unit: args.amount,
              },
            ],
          ],
        },
      ]);
      return { invoice_id: invoiceId, partner_id: partnerId, status: "draft" };
    }

    case "get_invoice": {
      const invoices = await odooCall(
        config, uid, "account.move", "read",
        [[args.invoice_id]],
        {
          fields: ["name", "partner_id", "amount_total", "state", "payment_state", "invoice_date", "invoice_date_due", "invoice_line_ids"],
        }
      );
      return invoices[0] || { error: "Invoice not found" };
    }

    case "list_customers": {
      const customers = await odooCall(
        config, uid, "res.partner", "search_read",
        [[["customer_rank", ">", 0]]],
        {
          fields: ["name", "email", "phone", "create_date"],
          limit: args.limit || 10,
          order: args.order || "create_date desc",
        }
      );
      return { customers, count: customers.length };
    }

    case "create_customer": {
      const partnerId = await odooCall(config, uid, "res.partner", "create", [
        {
          name: args.name,
          email: args.email || false,
          phone: args.phone || false,
          customer_rank: 1,
        },
      ]);
      return { partner_id: partnerId, name: args.name, status: "created" };
    }

    case "list_products": {
      const products = await odooCall(
        config, uid, "product.product", "search_read",
        [[["active", "=", true]]],
        {
          fields: ["name", "list_price", "description_sale"],
          limit: args.limit || 20,
        }
      );
      return { products, count: products.length };
    }

    case "create_product": {
      const productId = await odooCall(
        config, uid, "product.product", "create",
        [
          {
            name: args.name,
            list_price: args.price,
            description_sale: args.description || "",
          },
        ]
      );
      return { product_id: productId, name: args.name, status: "created" };
    }

    case "get_financial_summary": {
      const domain = [
        ["move_type", "in", ["out_invoice"]],
        ["state", "=", "posted"],
      ];

      const now = new Date();
      if (args.period === "this_month") {
        const start = new Date(now.getFullYear(), now.getMonth(), 1)
          .toISOString()
          .split("T")[0];
        domain.push(["invoice_date", ">=", start]);
      } else if (args.period === "this_year") {
        domain.push([
          "invoice_date",
          ">=",
          `${now.getFullYear()}-01-01`,
        ]);
      }

      const invoices = await odooCall(
        config, uid, "account.move", "search_read",
        [domain],
        { fields: ["name", "amount_total", "payment_state", "partner_id"] }
      );

      const totalRevenue = invoices.reduce((s, i) => s + i.amount_total, 0);
      const paid = invoices.filter((i) => i.payment_state === "paid");
      const unpaid = invoices.filter((i) =>
        ["not_paid", "partial"].includes(i.payment_state)
      );

      return {
        period: args.period || "all",
        total_invoiced: totalRevenue,
        total_paid: paid.reduce((s, i) => s + i.amount_total, 0),
        total_outstanding: unpaid.reduce((s, i) => s + i.amount_total, 0),
        invoice_count: invoices.length,
        paid_count: paid.length,
        unpaid_count: unpaid.length,
        currency: loadConfig().currency || "PKR",
      };
    }

    case "create_payment": {
      // Post the invoice first if it's still draft
      try {
        await odooCall(config, uid, "account.move", "action_post", [
          [args.invoice_id],
        ]);
      } catch (_) {}

      // Find default bank journal
      const journals = await odooCall(config, uid, "account.journal", "search_read",
        [[["type", "in", ["bank", "cash"]]]],
        { fields: ["id", "name"], limit: 1 }
      );
      const journalId = journals.length > 0 ? journals[0].id : false;

      const paymentId = await odooCall(
        config, uid, "account.payment", "create",
        [
          {
            amount: args.amount,
            payment_type: "inbound",
            partner_type: "customer",
            journal_id: journalId,
            ref: args.memo || `Payment for invoice ${args.invoice_id}`,
          },
        ]
      );
      return {
        payment_id: paymentId,
        invoice_id: args.invoice_id,
        amount: args.amount,
        journal: journals.length > 0 ? journals[0].name : "unknown",
        status: "created",
      };
    }

    default:
      return { error: `Unknown tool: ${name}` };
  }
}

// ── MCP Server (stdio) ────────────────────────────────────────────────────────

const rl = readline.createInterface({ input: process.stdin });

function sendMessage(msg) {
  const json = JSON.stringify(msg);
  process.stdout.write(`Content-Length: ${Buffer.byteLength(json)}\r\n\r\n${json}`);
}

let buffer = "";
process.stdin.on("data", (chunk) => {
  buffer += chunk.toString();
  while (true) {
    const headerEnd = buffer.indexOf("\r\n\r\n");
    if (headerEnd === -1) break;
    const header = buffer.slice(0, headerEnd);
    const lenMatch = header.match(/Content-Length:\s*(\d+)/i);
    if (!lenMatch) { buffer = buffer.slice(headerEnd + 4); continue; }
    const len = parseInt(lenMatch[1]);
    const bodyStart = headerEnd + 4;
    if (buffer.length < bodyStart + len) break;
    const body = buffer.slice(bodyStart, bodyStart + len);
    buffer = buffer.slice(bodyStart + len);
    handleMessage(body);
  }
});

async function handleMessage(raw) {
  let msg;
  try { msg = JSON.parse(raw); } catch { return; }

  if (msg.method === "initialize") {
    sendMessage({
      jsonrpc: "2.0",
      id: msg.id,
      result: {
        protocolVersion: "2024-11-05",
        capabilities: { tools: {} },
        serverInfo: { name: "odoo-mcp", version: "1.0.0" },
      },
    });
  } else if (msg.method === "tools/list") {
    sendMessage({ jsonrpc: "2.0", id: msg.id, result: { tools } });
  } else if (msg.method === "tools/call") {
    const { name, arguments: args } = msg.params;
    try {
      const result = await handleTool(name, args || {});
      sendMessage({
        jsonrpc: "2.0",
        id: msg.id,
        result: {
          content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
        },
      });
    } catch (e) {
      sendMessage({
        jsonrpc: "2.0",
        id: msg.id,
        result: {
          content: [{ type: "text", text: `Error: ${e.message}` }],
          isError: true,
        },
      });
    }
  } else if (msg.method === "notifications/initialized") {
    // no-op
  } else if (msg.id !== undefined) {
    sendMessage({ jsonrpc: "2.0", id: msg.id, result: {} });
  }
}
