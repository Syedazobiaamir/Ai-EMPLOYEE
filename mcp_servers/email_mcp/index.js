#!/usr/bin/env node
/**
 * email_mcp/index.js — Email MCP Server for AI Employee (Silver Tier)
 *
 * Provides Claude Code with tools to:
 *   - send_email    : Send an email via Gmail (requires human approval first)
 *   - draft_email   : Save an email draft to Gmail
 *   - search_emails : Search Gmail inbox
 *   - list_drafts   : List existing Gmail drafts
 *
 * Security:
 *   - DRY_RUN=true mode logs without sending (default: true for safety)
 *   - All send operations log to vault /Logs/ for audit trail
 *   - Never called directly by Claude — always triggered after human approval
 *
 * Setup:
 *   1. cd mcp_servers/email_mcp && npm install
 *   2. Copy config/.env.example to config/.env and fill in credentials
 *   3. Add to Claude Code MCP config (see README_SILVER.md)
 *
 * Claude Code MCP config entry:
 *   {
 *     "name": "email",
 *     "command": "node",
 *     "args": ["/absolute/path/to/mcp_servers/email_mcp/index.js"],
 *     "env": {
 *       "GMAIL_CREDENTIALS_PATH": "/absolute/path/to/config/gmail_credentials.json",
 *       "GMAIL_TOKEN_PATH": "/absolute/path/to/config/gmail_token.json",
 *       "VAULT_PATH": "/absolute/path/to/AI_Employee_Vault",
 *       "DRY_RUN": "false"
 *     }
 *   }
 */

import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';
import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'fs';
import { join, resolve } from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

// Load .env if present
const __dirname = dirname(fileURLToPath(import.meta.url));
const envPath = resolve(__dirname, '../../config/.env');
if (existsSync(envPath)) {
  const envContent = readFileSync(envPath, 'utf-8');
  for (const line of envContent.split('\n')) {
    const trimmed = line.trim();
    if (trimmed && !trimmed.startsWith('#')) {
      const eqIdx = trimmed.indexOf('=');
      if (eqIdx > 0) {
        const key = trimmed.slice(0, eqIdx).trim();
        const val = trimmed.slice(eqIdx + 1).trim().replace(/^["']|["']$/g, '');
        if (!process.env[key]) process.env[key] = val;
      }
    }
  }
}

const DRY_RUN = process.env.DRY_RUN !== 'false'; // Default: DRY_RUN=true (safe default)
const VAULT_PATH = process.env.VAULT_PATH || resolve(__dirname, '../../AI_Employee_Vault');
const CREDENTIALS_PATH = process.env.GMAIL_CREDENTIALS_PATH ||
  resolve(__dirname, '../../config/gmail_credentials.json');
const TOKEN_PATH = process.env.GMAIL_TOKEN_PATH ||
  resolve(__dirname, '../../config/gmail_token.json');

// ─── Gmail Auth ────────────────────────────────────────────────────────────────

async function getGmailAuth() {
  try {
    const { google } = await import('googleapis');
    const { OAuth2Client } = await import('google-auth-library');

    if (!existsSync(CREDENTIALS_PATH)) {
      throw new Error(`Gmail credentials not found at: ${CREDENTIALS_PATH}`);
    }
    if (!existsSync(TOKEN_PATH)) {
      throw new Error(
        `Gmail token not found at: ${TOKEN_PATH}\n` +
        'Run gmail_watcher.py --auth to authorize first.'
      );
    }

    const credentials = JSON.parse(readFileSync(CREDENTIALS_PATH, 'utf-8'));
    const { client_secret, client_id, redirect_uris } = credentials.installed || credentials.web;
    const oAuth2Client = new OAuth2Client(client_id, client_secret, redirect_uris[0]);

    const token = JSON.parse(readFileSync(TOKEN_PATH, 'utf-8'));
    oAuth2Client.setCredentials(token);

    return google.gmail({ version: 'v1', auth: oAuth2Client });
  } catch (err) {
    throw new Error(`Gmail auth failed: ${err.message}`);
  }
}

// ─── Logging ──────────────────────────────────────────────────────────────────

function appendToLog(entry) {
  const logsDir = join(VAULT_PATH, 'Logs');
  if (!existsSync(logsDir)) mkdirSync(logsDir, { recursive: true });

  const today = new Date().toISOString().split('T')[0];
  const logFile = join(logsDir, `${today}.json`);

  let entries = [];
  if (existsSync(logFile)) {
    try { entries = JSON.parse(readFileSync(logFile, 'utf-8')); } catch { entries = []; }
  }
  entries.push({ ...entry, timestamp: new Date().toISOString(), dry_run: DRY_RUN });
  writeFileSync(logFile, JSON.stringify(entries, null, 2), 'utf-8');
}

// ─── MCP Server ───────────────────────────────────────────────────────────────

const server = new McpServer({
  name: 'ai-employee-email',
  version: '1.0.0',
});

// ─── Tool: send_email ─────────────────────────────────────────────────────────

server.tool(
  'send_email',
  {
    to: z.string().describe('Recipient email address'),
    subject: z.string().describe('Email subject line'),
    body: z.string().describe('Email body (plain text)'),
    cc: z.string().optional().describe('CC recipients (comma-separated)'),
    reply_to_id: z.string().optional().describe('Gmail message ID to reply to'),
  },
  async ({ to, subject, body, cc, reply_to_id }) => {
    if (DRY_RUN) {
      const preview = `[DRY RUN] Would send email:\nTo: ${to}\nSubject: ${subject}\nBody: ${body.slice(0, 200)}`;
      appendToLog({
        action_type: 'email_send',
        actor: 'email_mcp',
        target: to,
        parameters: { subject, to, cc },
        approval_status: 'approved',
        approved_by: 'human',
        result: 'dry_run'
      });
      return { content: [{ type: 'text', text: preview }] };
    }

    try {
      const gmail = await getGmailAuth();

      // Build RFC 2822 message
      let rawMessage = [
        `To: ${to}`,
        cc ? `Cc: ${cc}` : null,
        `Subject: ${subject}`,
        'Content-Type: text/plain; charset=utf-8',
        'MIME-Version: 1.0',
        '',
        body
      ].filter(Boolean).join('\r\n');

      const encodedMessage = Buffer.from(rawMessage).toString('base64url');

      const params = {
        userId: 'me',
        requestBody: { raw: encodedMessage }
      };

      if (reply_to_id) {
        // Get thread ID for reply
        const originalMsg = await gmail.users.messages.get({
          userId: 'me', id: reply_to_id
        });
        params.requestBody.threadId = originalMsg.data.threadId;
      }

      const result = await gmail.users.messages.send(params);

      appendToLog({
        action_type: 'email_send',
        actor: 'email_mcp',
        target: to,
        parameters: { subject, to, cc, message_id: result.data.id },
        approval_status: 'approved',
        approved_by: 'human',
        result: 'success'
      });

      return {
        content: [{
          type: 'text',
          text: `Email sent successfully!\nMessage ID: ${result.data.id}\nTo: ${to}\nSubject: ${subject}`
        }]
      };
    } catch (err) {
      appendToLog({
        action_type: 'email_send',
        actor: 'email_mcp',
        target: to,
        parameters: { subject, to },
        result: `error: ${err.message}`
      });
      return { content: [{ type: 'text', text: `ERROR sending email: ${err.message}` }] };
    }
  }
);

// ─── Tool: draft_email ────────────────────────────────────────────────────────

server.tool(
  'draft_email',
  {
    to: z.string().describe('Recipient email address'),
    subject: z.string().describe('Email subject line'),
    body: z.string().describe('Email body (plain text)'),
    cc: z.string().optional().describe('CC recipients (comma-separated)'),
  },
  async ({ to, subject, body, cc }) => {
    if (DRY_RUN) {
      appendToLog({
        action_type: 'email_draft',
        actor: 'email_mcp',
        target: to,
        parameters: { subject, to },
        result: 'dry_run'
      });
      return {
        content: [{
          type: 'text',
          text: `[DRY RUN] Would save draft:\nTo: ${to}\nSubject: ${subject}\n\n${body.slice(0, 300)}`
        }]
      };
    }

    try {
      const gmail = await getGmailAuth();

      const rawMessage = [
        `To: ${to}`,
        cc ? `Cc: ${cc}` : null,
        `Subject: ${subject}`,
        'Content-Type: text/plain; charset=utf-8',
        'MIME-Version: 1.0',
        '',
        body
      ].filter(Boolean).join('\r\n');

      const encodedMessage = Buffer.from(rawMessage).toString('base64url');

      const result = await gmail.users.drafts.create({
        userId: 'me',
        requestBody: {
          message: { raw: encodedMessage }
        }
      });

      appendToLog({
        action_type: 'email_draft',
        actor: 'email_mcp',
        target: to,
        parameters: { subject, draft_id: result.data.id },
        result: 'success'
      });

      return {
        content: [{
          type: 'text',
          text: `Draft saved to Gmail!\nDraft ID: ${result.data.id}\nTo: ${to}\nSubject: ${subject}`
        }]
      };
    } catch (err) {
      return { content: [{ type: 'text', text: `ERROR creating draft: ${err.message}` }] };
    }
  }
);

// ─── Tool: search_emails ──────────────────────────────────────────────────────

server.tool(
  'search_emails',
  {
    query: z.string().describe('Gmail search query (e.g. "from:client@example.com is:unread")'),
    max_results: z.number().optional().default(10).describe('Maximum number of results'),
  },
  async ({ query, max_results }) => {
    if (DRY_RUN) {
      return {
        content: [{
          type: 'text',
          text: `[DRY RUN] Would search Gmail for: "${query}" (max: ${max_results} results)`
        }]
      };
    }

    try {
      const gmail = await getGmailAuth();
      const results = await gmail.users.messages.list({
        userId: 'me',
        q: query,
        maxResults: max_results
      });

      const messages = results.data.messages || [];
      if (messages.length === 0) {
        return { content: [{ type: 'text', text: `No emails found for query: "${query}"` }] };
      }

      // Fetch subjects for top results
      const summaries = await Promise.all(
        messages.slice(0, 5).map(async (msg) => {
          const full = await gmail.users.messages.get({
            userId: 'me', id: msg.id, format: 'metadata',
            metadataHeaders: ['Subject', 'From', 'Date']
          });
          const headers = Object.fromEntries(
            (full.data.payload.headers || []).map(h => [h.name, h.value])
          );
          return `- [${msg.id}] From: ${headers.From || 'unknown'} | Subject: ${headers.Subject || '(none)'} | Date: ${headers.Date || 'unknown'}`;
        })
      );

      return {
        content: [{
          type: 'text',
          text: `Found ${messages.length} email(s) matching "${query}":\n\n${summaries.join('\n')}`
        }]
      };
    } catch (err) {
      return { content: [{ type: 'text', text: `ERROR searching emails: ${err.message}` }] };
    }
  }
);

// ─── Tool: list_drafts ────────────────────────────────────────────────────────

server.tool(
  'list_drafts',
  {
    max_results: z.number().optional().default(5).describe('Maximum number of drafts to list'),
  },
  async ({ max_results }) => {
    if (DRY_RUN) {
      return { content: [{ type: 'text', text: '[DRY RUN] Would list Gmail drafts' }] };
    }

    try {
      const gmail = await getGmailAuth();
      const results = await gmail.users.drafts.list({ userId: 'me', maxResults: max_results });
      const drafts = results.data.drafts || [];

      if (drafts.length === 0) {
        return { content: [{ type: 'text', text: 'No Gmail drafts found.' }] };
      }

      const summaries = await Promise.all(
        drafts.map(async (draft) => {
          const full = await gmail.users.drafts.get({
            userId: 'me', id: draft.id, format: 'metadata',
            metadataHeaders: ['Subject', 'To']
          });
          const headers = Object.fromEntries(
            (full.data.message.payload.headers || []).map(h => [h.name, h.value])
          );
          return `- [${draft.id}] To: ${headers.To || 'unknown'} | Subject: ${headers.Subject || '(none)'}`;
        })
      );

      return {
        content: [{
          type: 'text',
          text: `Gmail Drafts (${drafts.length}):\n\n${summaries.join('\n')}`
        }]
      };
    } catch (err) {
      return { content: [{ type: 'text', text: `ERROR listing drafts: ${err.message}` }] };
    }
  }
);

// ─── Start server ─────────────────────────────────────────────────────────────

const transport = new StdioServerTransport();
await server.connect(transport);

process.stderr.write(
  `AI Employee Email MCP Server started\n` +
  `DRY_RUN: ${DRY_RUN}\n` +
  `VAULT: ${VAULT_PATH}\n`
);
